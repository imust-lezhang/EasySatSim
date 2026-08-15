from src.simulation.manager.plotter_manager import PlotterManager


class PlotterController:
    @staticmethod
    def plot_3d(shared_metric, test_mode):
        return PlotterController._start_canvas_manager(shared_metric=shared_metric, test_mode=test_mode)

    @staticmethod
    def _start_canvas_manager(shared_metric, test_mode):
        plotter_controller = PlotterManager(shared_metric, test_mode)
        plotter_controller.create_simulation_scene()
        plotter_controller._already_run()
        return plotter_controller
