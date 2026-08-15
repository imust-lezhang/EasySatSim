from tests.diagnostics.common import create_qapplication, process_events, run_step


def check():
    from PyQt5.QtCore import QTimer
    from PyQt5.QtWidgets import QApplication

    app = create_qapplication()
    fired = []
    QTimer.singleShot(25, lambda: fired.append(True))
    process_events(app, 150)
    if not fired:
        raise RuntimeError("Qt event loop did not dispatch the timer.")
    screens = app.screens()
    return {
        "summary": "QApplication and Qt event dispatch work.",
        "platform_name": QApplication.platformName(),
        "screen_count": len(screens),
        "screens": [
            {
                "name": screen.name(),
                "size": [screen.size().width(), screen.size().height()],
                "device_pixel_ratio": screen.devicePixelRatio(),
            }
            for screen in screens
        ],
    }


if __name__ == "__main__":
    run_step(3, check)
