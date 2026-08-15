from tests.diagnostics.common import create_qapplication, process_events, run_step, save_widget


def check():
    from PyQt5.QtWidgets import QLabel, QMainWindow

    app = create_qapplication()
    window = QMainWindow()
    window.setWindowTitle("EasySatSim Qt diagnostic")
    window.setCentralWidget(QLabel("PyQt5 window and event loop are operational."))
    window.resize(640, 360)
    window.show()
    process_events(app, 300)
    if not window.isVisible():
        raise RuntimeError("Qt test window did not become visible.")
    screenshot = save_widget(window, "step_04_qt_window.png")
    geometry = [window.x(), window.y(), window.width(), window.height()]
    window.close()
    return {
        "summary": "A visible Qt window was created and captured.",
        "geometry": geometry,
        "screenshot": str(screenshot),
    }


if __name__ == "__main__":
    run_step(4, check)
