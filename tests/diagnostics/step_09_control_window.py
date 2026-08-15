from tests.diagnostics.common import (
    TEST_CONFIG_ROOT,
    create_qapplication,
    process_events,
    run_step,
    save_widget,
)


def check():
    from src.tools.config_loader import load_configuration

    load_configuration(TEST_CONFIG_ROOT)
    from src.simulation.visualization.simulation_control_window import SimulationControlWindow

    app = create_qapplication()
    window = SimulationControlWindow(config_root=TEST_CONFIG_ROOT)
    window.resize(1100, 720)
    window.show()
    window._show_notification(
        "Long diagnostic notification",
        "D:/EasySatSim/tests/artifacts/a_long_configuration_and_visualization_message_"
        "that_must_wrap_without_leaving_the_window.csv",
    )
    process_events(app, 400)
    if window.state != window.STATE_INITIAL:
        raise RuntimeError(f"Unexpected control-window state: {window.state}")
    if not window.start_action.isEnabled() or window.stop_action.isEnabled():
        raise RuntimeError("Initial Start/Stop enabled states are incorrect.")
    if not window.notification_stack.has_notifications():
        raise RuntimeError("Persistent notification was not created.")
    toast = window.notification_stack.notifications[-1]
    if toast.x() < 0 or toast.x() + toast.width() > window.centralWidget().width():
        raise RuntimeError("Notification exceeds the control window width.")
    screenshot = save_widget(window, "step_09_control_window.png")
    menus = [action.text() for action in window.menuBar().actions()]
    window.close()
    return {
        "summary": "Control window, initial state, menus, and persistent notification work.",
        "menus": menus,
        "notification_size": [toast.width(), toast.height()],
        "screenshot": str(screenshot),
    }


if __name__ == "__main__":
    run_step(9, check)
