import os
from pathlib import Path

from tests.diagnostics.common import PROJECT_ROOT, TEST_CONFIG_ROOT, run_step


def check():
    from src.tools.config_loader import load_configuration

    cg = load_configuration(TEST_CONFIG_ROOT)
    required_resources = (
        PROJECT_ROOT / "resource" / "clean_2d_world_map.png",
        PROJECT_ROOT / "resource" / "logo.png",
        PROJECT_ROOT / "resource" / "population_matrix.npy",
    )
    missing = [str(path) for path in required_resources if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing visualization resources: " + ", ".join(missing))
    if cg.TOTAL_SATELLITE_NUMBER != cg.ORBIT_NUMBER * cg.SATELLITE_NUMBER_PRE_ORBIT:
        raise ValueError("TOTAL_SATELLITE_NUMBER is inconsistent.")
    if not 0 < cg.SATELLITE_CONE_ANGLE < 180:
        raise ValueError("SATELLITE_CONE_ANGLE must be in (0, 180).")

    output = PROJECT_ROOT / "tests" / "artifacts" / ".write_probe"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("ok", encoding="utf-8")
    output.unlink()
    return {
        "summary": "Isolated small configuration and visualization resources are valid.",
        "config_root": str(TEST_CONFIG_ROOT),
        "satellites": cg.TOTAL_SATELLITE_NUMBER,
        "users": cg.USER_NUMBER,
        "resources": [str(path) for path in required_resources],
        "output_writable": True,
        "environment_config_root": os.environ.get("EASYSATSIM_CONFIG_ROOT"),
    }


if __name__ == "__main__":
    run_step(2, check)
