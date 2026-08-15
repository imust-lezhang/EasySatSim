import csv
from pathlib import Path

from configuration import simulation_config as cg
from src.tools.config_loader import load_configuration


if not hasattr(cg, "IDS_MODE"):
    cg = load_configuration("cases/case1/src")


CASE_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = CASE_ROOT.parents[1]
EXPERIMENT_ROOT = CASE_ROOT / "experiment"
OUTPUT_DIR = EXPERIMENT_ROOT / "output"
GROUND_TRUTH_MALICIOUS = "malicious"
GROUND_TRUTH_BENIGN = "benign"

EVENT_FIELDNAMES = [
    "time",
    "ids",
    "ids_mode",
    "satellite_id",
    "source_ip",
    "target_ip",
    "target_port",
    "ground_truth",
    "detected",
    "action",
    "score",
    "detail",
]

_initialized_event_paths = set()


def record_ids_event(context, ids_result, action, event_log_path=None):
    event = build_ids_event(context=context, ids_result=ids_result, action=action)
    path = Path(event_log_path) if event_log_path is not None else get_event_log_path(event["ids_mode"])
    write_ids_event(event=event, path=path)
    return event


def build_ids_event(context, ids_result, action):
    ids_mode = ids_result["ids_mode"]
    return {
        "time": context.get("time", ""),
        "ids": ids_mode_to_label(ids_mode),
        "ids_mode": ids_mode,
        "satellite_id": context.get("satellite_id", ""),
        "source_ip": context.get("source_ip", ""),
        "target_ip": context.get("target_ip", ""),
        "target_port": context.get("target_port", ""),
        "ground_truth": context.get("ground_truth", GROUND_TRUTH_MALICIOUS),
        "detected": bool_to_text(ids_result.get("detected", False)),
        "action": action,
        "score": value_to_text(ids_result.get("score")),
        "detail": ascii(ids_result.get("detail")),
    }


def write_ids_event(event, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path = str(path.resolve())
    write_header = resolved_path not in _initialized_event_paths
    mode = "w" if write_header else "a"
    with path.open(mode, newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=EVENT_FIELDNAMES)
        if write_header:
            writer.writeheader()
            _initialized_event_paths.add(resolved_path)
        writer.writerow(event)
    return


def reset_ids_event_log(ids_mode=None, event_log_path=None):
    path = Path(event_log_path) if event_log_path is not None else get_event_log_path(ids_mode or cg.IDS_MODE)
    if path.exists():
        path.unlink()
    _initialized_event_paths.discard(str(path.resolve()))
    return path


def get_event_log_path(ids_mode=None):
    override_path = getattr(cg, "CASE_IDS_EVENT_LOG_PATH", None)
    if override_path:
        return resolve_runtime_path(override_path)
    ids_mode = normalize_ids_mode_text(ids_mode or cg.IDS_MODE)
    return OUTPUT_DIR / f"ids_events_{ids_mode}.csv"


def resolve_runtime_path(path_text):
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / "src" / path).resolve()


def normalize_ids_mode_text(ids_mode):
    return str(ids_mode).strip().lower().replace("-", "_")


def ids_mode_to_label(ids_mode):
    mode = normalize_ids_mode_text(ids_mode)
    if mode == "signature":
        return "S-IDS"
    if mode == "heuristic":
        return "HR-IDS"
    if mode == "dl":
        return "DL-IDS"
    if mode == "without_detection":
        return "WithoutDetection"
    return mode


def bool_to_text(value):
    return "1" if bool(value) else "0"


def text_to_bool(value):
    return str(value).strip().lower() in ("1", "true", "yes")


def value_to_text(value):
    if value is None:
        return ""
    return str(value)
