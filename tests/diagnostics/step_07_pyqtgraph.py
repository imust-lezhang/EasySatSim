from tests.diagnostics.common import create_qapplication, process_events, run_step, save_widget


def check():
    import numpy as np
    import pyqtgraph as pg

    app = create_qapplication()
    widget = pg.PlotWidget(title="EasySatSim PyQtGraph diagnostic")
    widget.resize(720, 420)
    widget.setBackground("w")
    curve = widget.plot(pen=pg.mkPen("#2563EB", width=3))
    updates = 6
    for index in range(updates):
        x = np.arange(index + 2, dtype=float)
        curve.setData(x, np.sin(x / 2.0) + index * 0.1)
        process_events(app, 60)
    widget.show()
    process_events(app, 250)
    x_data, y_data = curve.getData()
    if len(x_data) != updates + 1 or len(y_data) != updates + 1:
        raise RuntimeError("PyQtGraph curve did not retain the latest update.")
    screenshot = save_widget(widget, "step_07_pyqtgraph.png")
    widget.close()
    return {
        "summary": "PyQtGraph displayed and updated a live curve.",
        "update_count": updates,
        "point_count": len(x_data),
        "screenshot": str(screenshot),
    }


if __name__ == "__main__":
    run_step(7, check)
