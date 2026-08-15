import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = PROJECT_ROOT / "tests" / "artifacts"
TEST_CONFIG_ROOT = PROJECT_ROOT / "tests" / "fixtures" / "small_config"


def prepare_imports():
    root_text = str(PROJECT_ROOT)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    os.environ["EASYSATSIM_CONFIG_ROOT"] = str(TEST_CONFIG_ROOT)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def mode():
    return os.environ.get("EASYSATSIM_TEST_MODE", "offscreen")


def artifact_path(name):
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACT_DIR / name


def pass_step(step, summary, details=None):
    _finish("PASS", step, summary, details or {})


def skip_step(step, summary, details=None):
    _finish("SKIP", step, summary, details or {}, exit_code=77)


def fail_step(step, summary, details=None):
    _finish("FAIL", step, summary, details or {}, exit_code=1)


def run_step(step, function):
    prepare_imports()
    try:
        result = function() or {}
        pass_step(step, result.pop("summary", "Diagnostic completed."), result)
    except Exception as exc:
        fail_step(
            step,
            str(exc),
            {"exception_type": type(exc).__name__, "traceback": traceback.format_exc()},
        )


def _finish(status, step, summary, details, exit_code=0):
    payload = {
        "status": status,
        "step": step,
        "summary": summary,
        "mode": mode(),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "details": details,
    }
    print("EASYSATSIM_DIAGNOSTIC=" + json.dumps(payload, ensure_ascii=False, default=str))
    raise SystemExit(exit_code)


def create_qapplication():
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(["EasySatSim diagnostics"])
    app.setApplicationName("EasySatSim diagnostics")
    return app


def process_events(app, milliseconds=300):
    from PyQt5.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec_()
    app.processEvents()


def save_widget(widget, filename):
    path = artifact_path(filename)
    pixmap = widget.grab()
    if pixmap.isNull() or not pixmap.save(str(path)):
        raise RuntimeError(f"Could not save widget screenshot: {path}")
    if path.stat().st_size <= 0:
        raise RuntimeError(f"Screenshot is empty: {path}")
    return path


def cleanup_shared_memory():
    prepare_imports()
    from multiprocessing import shared_memory
    from src.simulation.variable import constant as ct

    names = (
        ct.SHM_CURRENT_TIME,
        ct.SHM_SATELLITE_POSITION_3D,
        ct.SHM_SATELLITE_POSITION_2D,
        ct.SHM_ORBIT_POSITION_3D,
        ct.SHM_USER_POSITION_3D,
        ct.SHM_ACCESS_RELATIONSHIP,
        ct.SHM_ROUTING_PATH,
        ct.SHM_SATELLITE_LOAD_DEVIATION,
        ct.SHM_SATELLITE_LATENCY,
    )
    for name in names:
        try:
            shm = shared_memory.SharedMemory(name=name)
        except FileNotFoundError:
            continue
        try:
            shm.unlink()
        except FileNotFoundError:
            pass
        finally:
            shm.close()


def create_visualization_state():
    prepare_imports()
    cleanup_shared_memory()
    from src.tools.config_loader import load_configuration

    load_configuration(TEST_CONFIG_ROOT)
    from src.simulation.variable.shared_value import SharedValue
    from src.simulation.variable.performance import SharedNetworkMetrics
    from src.tools.calculation import position_2D_to_3D

    values = SharedValue()
    metrics = SharedNetworkMetrics()
    satellite_count = len(values.satellite_position_3d)
    for index in range(satellite_count):
        latitude = -20.0 + 40.0 * index / max(1, satellite_count - 1)
        longitude = -150.0 + 300.0 * index / max(1, satellite_count - 1)
        values.satellite_position_3d[index] = position_2D_to_3D(latitude, longitude, 550)
        values.satellite_position_2d[index] = (latitude, longitude, 550)
    for index in range(len(values.user_position_3d)):
        values.user_position_3d[index] = position_2D_to_3D(index * 10.0, index * 20.0, 0)
        values.access_relationship[index] = index % satellite_count
    values.orbit_position_3d[:] = values.satellite_position_3d[0]
    values.satellite_load_deviation[:] = 0.25
    values.routing_path[:] = -1
    values.routing_path[:2] = values.satellite_position_3d[:2]
    return values, metrics


def close_visualization_state(values):
    for value in vars(values).values():
        if value.__class__.__name__ == "SharedMemory" and hasattr(value, "close"):
            try:
                value.close()
            except Exception:
                pass
    cleanup_shared_memory()
