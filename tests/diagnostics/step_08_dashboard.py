from tests.diagnostics.common import (
    close_visualization_state,
    create_qapplication,
    create_visualization_state,
    process_events,
    run_step,
    save_widget,
)


def check():
    values, metrics = create_visualization_state()
    window = None
    try:
        from src.simulation.visualization.qt_dashboard_window import QtDashboardWindow

        app = create_qapplication()
        window = QtDashboardWindow(shared_metric=metrics, test_mode=True)
        window.create_simulation_scene()
        window.resize(1280, 800)
        window.show()
        process_events(app, 700)
        subwindows = window.mdi_area.subWindowList()
        titles = sorted(item.windowTitle() for item in subwindows)
        expected = sorted(("3D View", "2D View", "Object Details", "Performance Metrics"))
        if titles != expected:
            raise RuntimeError(f"Dashboard panels differ: expected {expected}, got {titles}")
        if len(window.metric_charts) != 9:
            raise RuntimeError(f"Expected 9 metric charts, got {len(window.metric_charts)}")
        screenshot = save_widget(window, "step_08_dashboard.png")
        return {
            "summary": "EasySatSim Dashboard created all four panels and nine metric charts.",
            "panels": titles,
            "metric_chart_count": len(window.metric_charts),
            "screenshot": str(screenshot),
        }
    finally:
        if window is not None:
            window.close()
        close_visualization_state(values)


if __name__ == "__main__":
    run_step(8, check)
