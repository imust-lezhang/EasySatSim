from tests.diagnostics.common import (
    close_visualization_state,
    create_qapplication,
    create_visualization_state,
    process_events,
    run_step,
    save_widget,
)


def check():
    import numpy as np

    values, metrics = create_visualization_state()
    window = None
    try:
        from src.simulation.visualization.qt_dashboard_window import QtDashboardWindow

        app = create_qapplication()
        window = QtDashboardWindow(shared_metric=metrics, test_mode=True)
        window.create_simulation_scene()
        window.resize(1280, 800)
        window.show()
        original_position = values.satellite_position_3d[0].copy()
        update_count = 6
        for index in range(update_count):
            values.satellite_position_3d[0, 1] += 2.0
            values.satellite_position_2d[0, 1] += 0.05
            metrics.global_generate_packets_number.value = index + 1
            metrics.global_arrive_packets_number.value = index
            metrics.global_loss_packets_number.value = 1
            metrics.global_arrive_packets_byte.value = (index + 1) * 1200
            metrics.global_delay.value = 10 + index
            metrics.global_load_deviation.value = 0.1 * index
            metrics.global_normal_satellite_number.value = len(values.satellite_position_3d)
            metrics.global_user_cover_number.value = len(values.user_position_3d)
            metrics.global_hop_count.value = 3 + index / 10.0
            window.update_active_simulation_scene()
            window.update_line_chart()
            process_events(app, 100)
        movement = float(np.linalg.norm(values.satellite_position_3d[0] - original_position))
        chart_counts = [chart.data_count for chart in window.metric_charts]
        if movement <= 0:
            raise RuntimeError("Shared satellite position did not change.")
        if any(count != update_count for count in chart_counts):
            raise RuntimeError(f"Metric charts did not receive all updates: {chart_counts}")
        generated = next(
            chart for chart in window.metric_charts
            if chart.metric_name == "global_generate_packets_number"
        )
        if generated.data[generated.data_count - 1, 1] != update_count:
            raise RuntimeError("Generated-packet chart does not contain the latest shared value.")
        screenshot = save_widget(window, "step_10_live_refresh.png")
        return {
            "summary": "Shared positions and all live metric charts refreshed repeatedly.",
            "refresh_count": update_count,
            "satellite_movement_km": movement,
            "metric_chart_data_counts": chart_counts,
            "screenshot": str(screenshot),
        }
    finally:
        if window is not None:
            window.close()
        close_visualization_state(values)


if __name__ == "__main__":
    run_step(10, check)
