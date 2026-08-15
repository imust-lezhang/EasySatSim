import sys
from PyQt5.QtWidgets import QApplication
from src.simulation.visualization.qt_dashboard_window import QtDashboardWindow
from src.simulation.visualization.qt_dashboard_window import get_connect_relationship


class PlotterManager:
    def __init__(self, shared_metric, test_mode):
        self.shared_metric = shared_metric
        self.test_mode = test_mode
        self.qt_app = None
        self.window = None
        self.is_scene_created = False
        return


    def _create_qt_window(self):
        if self.qt_app is None:
            self.qt_app = QApplication.instance()
            if self.qt_app is None:
                self.qt_app = QApplication([sys.argv[0]])
        if self.window is None:
            self.window = QtDashboardWindow(shared_metric=self.shared_metric, test_mode=self.test_mode)
        return


    def create_simulation_scene(self):
        self._create_qt_window()
        if not self.is_scene_created:
            self.window.create_simulation_scene()
            self.is_scene_created = True
        return


    def update_active_simulation_scene(self, event=None):
        if self.window is not None:
            self.window.update_active_simulation_scene()
        return


    def update_line_chart(self, event=None):
        if self.window is not None:
            self.window.update_line_chart()
        return


    def run(self):
        self._already_run()
        return


    def _already_run(self):
        self._create_qt_window()
        if not self.is_scene_created:
            self.create_simulation_scene()
        self.window.start()
        self.window.show()
        self.qt_app.exec_()
        return
