from configuration import simulation_config as cg
from cases.case1.experiment.ids import ids_heuristic
from cases.case1.experiment.ids import ids_signature
from src.tools.config_loader import load_configuration


if not hasattr(cg, "CASE_DL_THRESHOLD"):
    cg = load_configuration("cases/case1/src")


IDS_MODE_WITHOUT_DETECTION = "without_detection"
IDS_MODE_SIGNATURE = "signature"
IDS_MODE_HEURISTIC = "heuristic"
IDS_MODE_DL = "dl"


class SatelliteIDSEngine:
    _dl_model = None

    def __init__(self, ids_mode=None):
        self.ids_mode = normalize_ids_mode(ids_mode or cg.IDS_MODE)
        self.dl_threshold = cg.CASE_DL_THRESHOLD
        if self.ids_mode == IDS_MODE_DL:
            self._load_dl_model()

    def inspect(self, payload, context=None):
        if self.ids_mode == IDS_MODE_WITHOUT_DETECTION:
            return build_result(ids_mode=self.ids_mode, detected=False, detail="without detection")

        if self.ids_mode == IDS_MODE_SIGNATURE:
            detected, matched_rule = ids_signature.detect(payload)
            return build_result(ids_mode=self.ids_mode, detected=detected, detail=matched_rule)

        if self.ids_mode == IDS_MODE_HEURISTIC:
            detected, similarity, matched_reasons, base_code = ids_heuristic.detect(payload)
            return build_result(ids_mode=self.ids_mode,
                                detected=detected,
                                score=similarity,
                                detail={
                                    "matched_reasons": matched_reasons,
                                    "base_code": base_code,
                                })

        if self.ids_mode == IDS_MODE_DL:
            from cases.case1.experiment.ids import ids_deep_learning
            model = self._load_dl_model()
            detected, score = ids_deep_learning.detect(payload,
                                                       model=model,
                                                       threshold=self.dl_threshold)
            return build_result(ids_mode=self.ids_mode, detected=detected, score=score, detail="dl_score")

        raise ValueError(f"Unsupported IDS mode: {self.ids_mode}")

    @classmethod
    def _load_dl_model(cls):
        if cls._dl_model is None:
            from cases.case1.experiment.ids import ids_deep_learning
            cls._dl_model = ids_deep_learning.get_runtime_model()
        return cls._dl_model


def normalize_ids_mode(ids_mode):
    mode = str(ids_mode).strip().lower().replace("-", "_")

    if mode in ("none", "off", "without", "without_detection", "no_detection"):
        return IDS_MODE_WITHOUT_DETECTION
    if mode in ("signature", "s_ids", "sids"):
        return IDS_MODE_SIGNATURE
    if mode in ("heuristic", "hr_ids", "hrids"):
        return IDS_MODE_HEURISTIC
    if mode in ("dl", "deep_learning", "dl_ids", "dlids"):
        return IDS_MODE_DL

    raise ValueError(
        "IDS_MODE only supports: without_detection, signature, heuristic, dl. "
        f"Current value: {ids_mode}"
    )


def build_result(ids_mode, detected, score=None, detail=None):
    return {
        "ids_mode": ids_mode,
        "detected": bool(detected),
        "score": score,
        "detail": detail,
    }


def install_satellite_ids(satellites, ids_mode=None):
    ids_mode = normalize_ids_mode(ids_mode or cg.IDS_MODE)
    for satellite in satellites:
        satellite.ids_engine = SatelliteIDSEngine(ids_mode=ids_mode)
    print(f"[Case1 IDS] Installed {ids_mode} IDS on {len(satellites)} satellites.")
    return
