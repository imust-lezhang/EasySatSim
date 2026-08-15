import csv
import time
from pathlib import Path

from tests.diagnostics.common import (
    PROJECT_ROOT,
    TEST_CONFIG_ROOT,
    cleanup_shared_memory,
    create_qapplication,
    process_events,
    run_step,
    save_widget,
)


def check():
    cleanup_shared_memory()
    from src.tools.config_loader import load_configuration

    cg = load_configuration(TEST_CONFIG_ROOT)
    from src.simulation.visualization.simulation_control_window import SimulationRuntime
    from src.simulation.visualization.qt_dashboard_window import QtDashboardWindow

    output_path = (PROJECT_ROOT / "src" / cg.SAVE_FILE_PATH).resolve()
    if output_path.exists():
        output_path.unlink()

    app = create_qapplication()
    runtime = SimulationRuntime(config_root=TEST_CONFIG_ROOT, output_console=False)
    dashboard = None
    try:
        runtime.start()
        process_events(app, 800)
        process_states = {
            "timer_alive": bool(runtime.process_timer and runtime.process_timer.is_alive()),
            "entity_alive": bool(runtime.process_entity and runtime.process_entity.is_alive()),
        }
        if not all(process_states.values()):
            raise RuntimeError(f"A simulation worker exited during startup: {process_states}")

        dashboard = QtDashboardWindow(
            shared_metric=runtime.scene_controller.shared_metric,
            test_mode=False,
        )
        dashboard.create_simulation_scene()
        dashboard.start()
        dashboard.resize(1280, 800)
        dashboard.show()

        deadline = time.monotonic() + 3.2
        while time.monotonic() < deadline:
            process_events(app, 100)
            if not runtime.is_running():
                raise RuntimeError("Simulation workers exited before the short diagnostic completed.")
        screenshot = save_widget(dashboard, "step_11_short_simulation.png")
    finally:
        if dashboard is not None:
            for timer_name in ("active_timer", "metric_timer"):
                timer = getattr(dashboard, timer_name, None)
                if timer is not None:
                    timer.stop()
            dashboard.close()
        runtime.stop()
        if runtime.scene_controller is not None:
            runtime.scene_controller.release_shared_memory()
        cleanup_shared_memory()

    if not output_path.is_file():
        raise FileNotFoundError(f"Short simulation did not produce its CSV: {output_path}")
    with output_path.open("r", newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))
    if len(rows) < 2 or not rows[0] or rows[0][0] != "Time":
        raise RuntimeError(f"Short simulation CSV is invalid ({len(rows)} rows).")
    return {
        "summary": "A small isolated simulation ran with live Dashboard refresh and wrote a valid CSV.",
        "processes_during_run": process_states,
        "result_csv": str(output_path),
        "result_row_count": len(rows),
        "screenshot": str(screenshot),
    }


if __name__ == "__main__":
    run_step(11, check)
