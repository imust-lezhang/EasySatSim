from pathlib import Path
from multiprocessing import shared_memory

import numpy as np
import pyqtgraph as pg
import vispy
vispy.use(app="pyqt5")
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow
from PyQt5.QtWidgets import QMdiArea, QMdiSubWindow, QPlainTextEdit, QPushButton, QSizePolicy
from PyQt5.QtWidgets import QSpinBox, QTabWidget, QVBoxLayout, QWidget
from vispy import scene
from vispy.scene import visuals

from configuration import simulation_config as cg
from src.simulation.variable import constant as ct
from src.tools import calculation
from src.simulation.visualization.constellation_2d_plotter import Constellation2DPlotter
from src.simulation.visualization.constellation_plotter import ConstellationPlotter
from src.simulation.visualization.earth_plotter import EarthPlotter
from src.simulation.visualization.ground_plotter import GroundPlotter
from src.simulation.visualization.routing_path_plotter import RoutingPathPlotter
from src.simulation.visualization.satellite_ground_connect_plotter import SatelliteGroundConnectPlotter

pg.setConfigOptions(antialias=True)


class PreviewSubWindow(QMdiSubWindow):
    def __init__(self):
        super().__init__()
        self.allow_close = False


    def closeEvent(self, event):
        if self.allow_close:
            super().closeEvent(event)
        else:
            event.ignore()
            self.hide()
        return


class MetricChart(QFrame):
    def __init__(self, title, color, metric_name, unit=""):
        super().__init__()
        self.title = title
        self.color = color
        self.metric_name = metric_name
        self.unit = unit
        self.data_capacity = 1024
        self.data_count = 0
        self.data = np.zeros((self.data_capacity, 2), dtype=np.float64)
        self.x_min = None
        self.x_max = None
        self.y_min = None
        self.y_max = None
        self.alert_level = None
        self.recent_window_enabled = False
        self.recent_window_seconds = 60

        self.setObjectName("MetricChart")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(150, 105)

        self.value_label = QLabel(f"{title}: 0")
        self.value_label.setObjectName("MetricValue")

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_widget.setMinimumHeight(66)
        self.plot_widget.setBackground("#FFFFFF")
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.18)
        self.plot_widget.hideButtons()
        self._style_axis()
        self.line = self.plot_widget.plot([], [], pen=pg.mkPen(color, width=2))
        self.marker = pg.ScatterPlotItem(size=7,
                                         pen=pg.mkPen(color, width=1.3),
                                         brush=pg.mkBrush("#FFFFFF"))
        self.plot_widget.addItem(self.marker)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 7, 9, 8)
        layout.setSpacing(4)
        layout.addWidget(self.value_label)
        layout.addWidget(self.plot_widget, 1)
        self._apply_alert_style("normal")


    def update_value(self, x_value, y_value):
        if self.data_count >= self.data_capacity:
            self.data_capacity = self.data_capacity * 2
            new_data = np.zeros((self.data_capacity, 2), dtype=np.float64)
            new_data[:self.data_count] = self.data
            self.data = new_data

        self.data[self.data_count] = [x_value, y_value]
        if self.data_count == 0:
            self.x_min = x_value
            self.x_max = x_value
            self.y_min = y_value
            self.y_max = y_value
        else:
            self.x_min = min(self.x_min, x_value)
            self.x_max = max(self.x_max, x_value)
            self.y_min = min(self.y_min, y_value)
            self.y_max = max(self.y_max, y_value)
        self.data_count += 1

        data_array = self._visible_data()
        self.line.setData(data_array[:, 0], data_array[:, 1])
        self.marker.setData([x_value], [y_value])
        self.plot_widget.setXRange(*self._get_range(np.min(data_array[:, 0]), np.max(data_array[:, 0])), padding=0)
        self.plot_widget.setYRange(*self._get_range(np.min(data_array[:, 1]), np.max(data_array[:, 1])), padding=0)
        self.value_label.setText(f"{self.title}: {self._format_value(y_value)}")
        self._apply_alert_style(self._alert_level(y_value))
        return


    def set_recent_window(self, enabled, seconds=60):
        self.recent_window_enabled = enabled
        self.recent_window_seconds = seconds
        if self.data_count == 0:
            return
        data_array = self._visible_data()
        self.line.setData(data_array[:, 0], data_array[:, 1])
        self.plot_widget.setXRange(*self._get_range(np.min(data_array[:, 0]), np.max(data_array[:, 0])), padding=0)
        self.plot_widget.setYRange(*self._get_range(np.min(data_array[:, 1]), np.max(data_array[:, 1])), padding=0)
        return


    def _visible_data(self):
        data_array = self.data[:self.data_count]
        if not self.recent_window_enabled or self.data_count == 0:
            return data_array
        latest_x = data_array[-1, 0]
        visible = data_array[data_array[:, 0] >= latest_x - self.recent_window_seconds]
        if len(visible) == 0:
            return data_array[-1:]
        return visible


    def _alert_level(self, value):
        if self.metric_name == "loss_packets_number":
            if value >= 10:
                return "critical"
            if value > 0:
                return "warning"
        elif self.metric_name == "delay":
            if value >= 300:
                return "critical"
            if value >= 120:
                return "warning"
        elif self.metric_name == "load_deviation":
            if value >= 2:
                return "critical"
            if value >= 1:
                return "warning"
        return "normal"


    def _apply_alert_style(self, level):
        if level == self.alert_level:
            return
        styles = {
            "normal": ("#FFFFFF", "#D8DEE9", "#111827"),
            "warning": ("#FFF7ED", "#FB923C", "#9A3412"),
            "critical": ("#FEF2F2", "#EF4444", "#991B1B"),
        }
        background, border, label_color = styles[level]
        self.setStyleSheet(
            f"QFrame#MetricChart {{ background: {background}; border: 1px solid {border}; border-radius: 1px; }}"
        )
        self.value_label.setStyleSheet(
            f"color: {label_color}; font-size: 15px; font-weight: 700;"
        )
        self.alert_level = level
        return


    def _style_axis(self):
        for axis_name in ("left", "bottom"):
            axis = self.plot_widget.getAxis(axis_name)
            axis.setPen(pg.mkPen("#CBD5E1", width=1))
            axis.setTextPen(pg.mkPen("#64748B"))
            axis.setStyle(tickFont=None)
        self.plot_widget.getAxis("top").setPen(pg.mkPen("#E2E8F0"))
        self.plot_widget.getAxis("right").setPen(pg.mkPen("#E2E8F0"))
        return


    def _format_value(self, value):
        if abs(value) >= 10000:
            value_text = f"{value:,.0f}"
        elif abs(value) >= 100:
            value_text = f"{value:.1f}"
        else:
            value_text = f"{value:.2f}"
        if self.unit:
            return f"{value_text} {self.unit}"
        return value_text


    @staticmethod
    def _get_range(min_value, max_value):
        if min_value == max_value:
            margin = abs(min_value) * 0.05
            if margin == 0:
                margin = 1
            return min_value - margin, max_value + margin
        margin = (max_value - min_value) * 0.05
        return min_value - margin, max_value + margin


class ObjectDetailPanel(QFrame):
    def __init__(self, total_satellites, total_users):
        super().__init__()
        self.total_satellites = total_satellites
        self.total_users = total_users
        self.request_callback = None
        self._create_layout()
        return


    def _create_layout(self):
        self.setObjectName("MetricPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(7)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._create_overview_tab(), "Overview")
        self.tabs.addTab(self._create_selected_object_tab(), "Selected Object")
        layout.addWidget(self.tabs, 1)
        return


    def _create_overview_tab(self):
        overview = QWidget()
        overview_layout = QGridLayout(overview)
        overview_layout.setContentsMargins(12, 10, 12, 10)
        overview_layout.setHorizontalSpacing(28)
        overview_layout.setVerticalSpacing(8)

        title = QLabel("Constellation Overview")
        title.setStyleSheet("font-size: 17px; font-weight: 700; color: #202020;")
        overview_layout.addWidget(title, 0, 0, 1, 4)

        entries = [
            ("Orbital planes", cg.ORBIT_NUMBER),
            ("Satellites per plane", cg.SATELLITE_NUMBER_PRE_ORBIT),
            ("Total satellites", cg.TOTAL_SATELLITE_NUMBER),
            ("Users", cg.USER_NUMBER),
            ("Network step", f"{cg.NETWORK_RUNNING_STEP_SECOND} s"),
        ]
        for index, (name, value) in enumerate(entries):
            row = index // 2 + 1
            column = (index % 2) * 2
            name_label = QLabel(name)
            name_label.setStyleSheet("color: #555555;")
            value_label = QLabel(str(value))
            value_label.setStyleSheet("font-weight: 600; color: #202020;")
            overview_layout.addWidget(name_label, row, column)
            overview_layout.addWidget(value_label, row, column + 1)
        overview_layout.setRowStretch(4, 1)
        return overview


    def _create_selected_object_tab(self):
        selected_object = QWidget()
        layout = QVBoxLayout(selected_object)
        layout.setContentsMargins(4, 6, 4, 4)
        layout.setSpacing(7)

        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(8)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Satellite", "User"])
        self.id_spin = QSpinBox()
        self.id_spin.setMinimum(0)
        self.id_spin.setMaximum(max(self.total_satellites - 1, 0))
        self.show_button = QPushButton("Show")
        self.title_label = QLabel("No object selected")
        self.title_label.setStyleSheet("font-size: 17px; font-weight: 700; color: #202020;")

        self.type_combo.currentTextChanged.connect(self._update_id_range)
        self.show_button.clicked.connect(self._request_current)
        self.id_spin.editingFinished.connect(self._request_current)

        control_layout.addWidget(self.type_combo)
        control_layout.addWidget(self.id_spin)
        control_layout.addWidget(self.show_button)
        control_layout.addSpacing(10)
        control_layout.addWidget(self.title_label)
        control_layout.addStretch(1)

        self.detail_view = QPlainTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setStyleSheet("""
            QPlainTextEdit {
                background: #FAFAFA;
                border: 1px solid #8E8E8E;
                border-radius: 1px;
                color: #202020;
                font-family: Consolas, "Courier New", monospace;
                font-size: 16px;
                padding: 5px;
            }
        """)
        self.detail_view.setPlainText("Select an object on the 2D map or enter an ID.")

        layout.addLayout(control_layout)
        layout.addWidget(self.detail_view, 1)
        return selected_object


    def set_request_callback(self, callback):
        self.request_callback = callback
        return


    def set_selection(self, object_type, object_id):
        self.type_combo.blockSignals(True)
        self.id_spin.blockSignals(True)
        self.type_combo.setCurrentText("Satellite" if object_type == "satellite" else "User")
        self._update_id_range()
        self.id_spin.setValue(object_id)
        self.type_combo.blockSignals(False)
        self.id_spin.blockSignals(False)
        return


    def set_details(self, title, lines, activate=False):
        self.title_label.setText(title)
        self.detail_view.setPlainText("\n".join(lines))
        if activate:
            self.tabs.setCurrentIndex(1)
        return


    def _update_id_range(self, *_args):
        if self.type_combo.currentText() == "User":
            maximum = self.total_users - 1
            has_object = self.total_users > 0
        else:
            maximum = self.total_satellites - 1
            has_object = self.total_satellites > 0
        maximum = max(maximum, 0)
        self.id_spin.setMaximum(maximum)
        self.id_spin.setEnabled(has_object)
        self.show_button.setEnabled(has_object)
        if not has_object:
            self.id_spin.setValue(0)
        return


    def _request_current(self):
        if self.request_callback is None:
            return
        object_type = "satellite" if self.type_combo.currentText() == "Satellite" else "user"
        self.request_callback(object_type, self.id_spin.value())
        return


class QtDashboardWindow(QMainWindow):
    def __init__(self, shared_metric, test_mode):
        super().__init__()
        self.test_mode = test_mode
        self.shared_metric = shared_metric
        self.orbit_number = cg.ORBIT_NUMBER
        self.satellites_number = cg.SATELLITE_NUMBER_PRE_ORBIT
        self.scale_factor = 1 / 6371
        self.count = 0
        self.project_root = Path(__file__).resolve().parents[3]
        self.texture_path = self.project_root / "resource" / "clean_2d_world_map.png"
        self.selected_object_type = None
        self.selected_object_id = None
        self.selection_marker_2d = None
        self.selection_marker_3d = None

        self._bind_shared_memory_views()
        self._create_window()
        self._create_plotters()
        return


    def _bind_shared_memory_views(self):
        self._shm_satellite_position_3d = shared_memory.SharedMemory(name=ct.SHM_SATELLITE_POSITION_3D)
        self.satellite_position_3d = np.ndarray((cg.TOTAL_SATELLITE_NUMBER, 3), dtype=np.float64,
                                                buffer=self._shm_satellite_position_3d.buf)
        self._shm_satellite_position_2d = shared_memory.SharedMemory(name=ct.SHM_SATELLITE_POSITION_2D)
        self.satellite_position_2d = np.ndarray((cg.TOTAL_SATELLITE_NUMBER, 3), dtype=np.float64,
                                                buffer=self._shm_satellite_position_2d.buf)
        self._shm_orbit_position_3d = shared_memory.SharedMemory(name=ct.SHM_ORBIT_POSITION_3D)
        self.orbit_position_3d = np.ndarray((cg.ORBIT_NUMBER * 100, 3), dtype=np.float64,
                                            buffer=self._shm_orbit_position_3d.buf)
        self._shm_user_position_3d = shared_memory.SharedMemory(name=ct.SHM_USER_POSITION_3D)
        self.user_position_3d = np.ndarray((cg.USER_NUMBER, 3), dtype=np.float64,
                                           buffer=self._shm_user_position_3d.buf)
        self._shm_access_relationship = shared_memory.SharedMemory(name=ct.SHM_ACCESS_RELATIONSHIP)
        self.access_relationship = np.ndarray((cg.USER_NUMBER,), dtype=np.int64,
                                              buffer=self._shm_access_relationship.buf)
        self._shm_routing_path = shared_memory.SharedMemory(name=ct.SHM_ROUTING_PATH)
        self.routing_path = np.ndarray((100, 3,), dtype=np.float64,
                                       buffer=self._shm_routing_path.buf)
        self._shm_satellite_load_deviation = shared_memory.SharedMemory(name=ct.SHM_SATELLITE_LOAD_DEVIATION)
        self.satellite_load_deviation = np.ndarray((cg.ORBIT_NUMBER, cg.SATELLITE_NUMBER_PRE_ORBIT,), dtype=np.float64,
                                                   buffer=self._shm_satellite_load_deviation.buf)
        return


    def _create_window(self):
        self.setWindowTitle("EasySatSim")
        self.setWindowIcon(QIcon(str(self.project_root / "resource" / "logo.png")))
        self.resize(1920, 1080)
        self.setStyleSheet("""
            QMainWindow {
                background: #F3F6FA;
            }
            QWidget {
                background: #F3F6FA;
                color: #202020;
                font-family: Segoe UI, Arial;
                font-size: 16px;
            }
            QFrame#ScenePanel, QFrame#MetricChart, QFrame#MetricPanel {
                background: #FFFFFF;
                border: 1px solid #858585;
                border-radius: 1px;
            }
            QLabel#MetricValue {
                color: #202020;
                font-size: 16px;
                font-weight: 700;
            }
            QMdiArea {
                background: #F3F6FA;
                border: 1px solid #8A8A8A;
            }
            QMdiSubWindow {
                background: #D6D6D6;
                border: 1px solid #777777;
            }
            QTabWidget::pane {
                background: #FFFFFF;
                border: 1px solid #8F8F8F;
                top: -1px;
            }
            QTabBar::tab {
                background: #D5D5D5;
                border: 1px solid #969696;
                border-bottom: 0;
                border-radius: 0;
                min-width: 105px;
                padding: 5px 10px;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background: #E3E3E3;
            }
            QPushButton, QComboBox, QSpinBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                             stop:0 #FCFCFC, stop:1 #DEDEDE);
                border: 1px solid #858585;
                border-radius: 1px;
                padding: 4px 7px;
            }
            QPushButton:hover, QComboBox:hover, QSpinBox:hover {
                border-color: #4F6F91;
            }
            QPushButton:pressed {
                background: #D1D1D1;
            }
            QPushButton:disabled, QComboBox:disabled, QSpinBox:disabled {
                background: #D8D8D8;
                border-color: #AFAFAF;
                color: #8F8F8F;
            }
        """)

        self.mdi_area = QMdiArea()
        self.mdi_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mdi_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setCentralWidget(self.mdi_area)

        self.canvas_3d = scene.SceneCanvas(keys="interactive", show=False, bgcolor="#FFFFFF")
        self.view_3d = self.canvas_3d.central_widget.add_view()
        self.view_3d.camera = "turntable"
        self.view_3d.camera.fov = 80
        self.view_3d.camera.distance = 2.5

        self.canvas_2d = scene.SceneCanvas(keys="interactive", show=False, bgcolor="#FFFFFF")
        self.view_2d = self.canvas_2d.central_widget.add_view()
        self.view_2d.camera = "panzoom"
        self.view_2d.camera.set_range(x=(-180, 180), y=(-90, 90), margin=0)

        self.subwindow_3d = self._create_subwindow("3D View",
                                                   self._create_scene_panel(self.canvas_3d.native),
                                                   10, 10, 1100, 670)
        self.object_detail_panel = self._create_object_detail_panel()
        self.subwindow_details = self._create_subwindow("Object Details",
                                                        self.object_detail_panel,
                                                        10, 690, 1100, 250)
        self.subwindow_2d = self._create_subwindow("2D View",
                                                   self._create_scene_panel(self.canvas_2d.native),
                                                   1120, 10, 760, 390)
        self.subwindow_metrics = self._create_subwindow("Performance Metrics",
                                                        self._create_metric_panel(),
                                                        1120, 410, 760, 590)

        self.canvas_2d.events.mouse_press.connect(self._handle_2d_mouse_press)
        return


    def _create_subwindow(self, title, widget, x, y, width, height):
        subwindow = PreviewSubWindow()
        subwindow.setWidget(widget)
        self.mdi_area.addSubWindow(subwindow)
        subwindow.setWindowTitle(title)
        subwindow.setAttribute(Qt.WA_DeleteOnClose, False)
        subwindow.setGeometry(x, y, width, height)
        subwindow.show()
        return subwindow


    @staticmethod
    def _show_subwindow(subwindow):
        subwindow.showNormal()
        subwindow.raise_()
        subwindow.activateWindow()
        return


    def show_panel(self, panel_name):
        panels = {
            "3d": self.subwindow_3d,
            "details": self.subwindow_details,
            "2d": self.subwindow_2d,
            "metrics": self.subwindow_metrics,
        }
        subwindow = panels.get(panel_name)
        if subwindow is not None:
            self._show_subwindow(subwindow)
        return


    def _create_scene_panel(self, widget):
        panel = QFrame()
        panel.setObjectName("ScenePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)
        layout.addWidget(widget, 1)
        return panel


    def _create_metric_panel(self):
        panel = QFrame()
        panel.setObjectName("MetricPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(6)

        chart_grid = QGridLayout()
        chart_grid.setContentsMargins(0, 0, 0, 0)
        chart_grid.setHorizontalSpacing(8)
        chart_grid.setVerticalSpacing(8)

        self.metric_charts = []
        chart_specs = [
            ("Generated Packets", "#7DD3FC", "global_generate_packets_number", ""),
            ("Arrived Packets", "#86EFAC", "arrive_packets_number", ""),
            ("Lost Packets", "#FDA4AF", "loss_packets_number", ""),
            ("Throughput", "#C4B5FD", "arrive_packets_byte", "bytes"),
            ("Latency", "#FBBF24", "delay", "ms"),
            ("Load Deviation", "#F472B6", "load_deviation", ""),
            ("Operational Sats", "#67E8F9", "normal_satellite_number", ""),
            ("Covered Users", "#A7F3D0", "user_cover_number", ""),
            ("Average Hop Count", "#FDBA74", "hop_count", "hop"),
        ]
        for index, chart_spec in enumerate(chart_specs):
            title_text, color, metric_name, unit = chart_spec
            chart = MetricChart(title=title_text, color=color, metric_name=metric_name, unit=unit)
            chart_grid.addWidget(chart, index // 3, index % 3)
            self.metric_charts.append(chart)

        layout.addLayout(chart_grid, 1)
        return panel


    def _create_object_detail_panel(self):
        panel = ObjectDetailPanel(total_satellites=cg.TOTAL_SATELLITE_NUMBER,
                                  total_users=cg.USER_NUMBER)
        panel.set_request_callback(self.select_object)
        return panel


    def _create_plotters(self):
        self.earth_plotter = EarthPlotter()
        self.constellation_plotter = ConstellationPlotter(color_survival="purple",
                                                          size_survival=10,
                                                          color_failure="#FF8247",
                                                          size_failure=10,
                                                          scale_factor=self.scale_factor)
        self.ground_plotter = GroundPlotter(color="red", size=5, scale_factor=self.scale_factor)
        self.sat_user_conn_plotter = SatelliteGroundConnectPlotter(color="blue",
                                                                    width=1.5,
                                                                    scale_factor=self.scale_factor)
        self.routing_path_plotter = RoutingPathPlotter(scale_factor=self.scale_factor,
                                                       color="yellow",
                                                       width=3.5)
        self.constellation_2d_plotter = Constellation2DPlotter(normal_color="purple",
                                                               failure_color="#FF8247",
                                                               user_color="red",
                                                               connect_color="blue",
                                                               routing_color="yellow")
        return


    def create_simulation_scene(self):
        satellite_load_deviation = self.satellite_load_deviation.reshape(self.orbit_number * self.satellites_number)
        index_survival = np.where(satellite_load_deviation >= 0)[0]
        index_failure = np.where(satellite_load_deviation < 0)[0]
        survival_position_3d = self.satellite_position_3d[index_survival]
        failure_position_3d = self.satellite_position_3d[index_failure]

        self.earth_plotter.create_earth(view=self.view_3d, texture_path=str(self.texture_path))
        self.constellation_plotter.create_survival_satellites(view=self.view_3d, position_3d=survival_position_3d)
        self.constellation_plotter.create_failure_satellites(view=self.view_3d, position_3d=failure_position_3d)
        self.ground_plotter.create_users(view=self.view_3d, position_3d=self.user_position_3d)

        orbit_position_3d = np.zeros(shape=(cg.ORBIT_NUMBER * 100, 3))
        orbit_position_3d[:] = self.orbit_position_3d
        orbit_position_3d = orbit_position_3d.reshape(cg.ORBIT_NUMBER, 100, 3)
        self.constellation_plotter.create_orbits(view=self.view_3d, position_3d=orbit_position_3d)
        self.sat_user_conn_plotter.create_connect(view=self.view_3d)
        self.routing_path_plotter.create_path(view=self.view_3d)

        self.constellation_2d_plotter.create_scene(view=self.view_2d,
                                                   texture_path=str(self.texture_path),
                                                   satellite_position_2d=self.satellite_position_2d,
                                                   user_position_3d=self.user_position_3d,
                                                   access_relationship=self.access_relationship,
                                                   satellite_load_deviation=self.satellite_load_deviation,
                                                   orbit_position_3d=self.orbit_position_3d,
                                                   routing_path=self.routing_path,
                                                   test_mode=self.test_mode)
        self._create_selection_markers()
        if cg.TOTAL_SATELLITE_NUMBER > 0:
            self.select_object("satellite", 0)
        return


    def start(self):
        self.active_timer = QTimer(self)
        self.active_timer.timeout.connect(self.update_active_simulation_scene)
        self.active_timer.start(50)

        self.metric_timer = QTimer(self)
        self.metric_timer.timeout.connect(self.update_line_chart)
        self.metric_timer.start(1000)
        return


    def update_active_simulation_scene(self):
        satellite_load_deviation = self.satellite_load_deviation.reshape(self.orbit_number * self.satellites_number)
        index_survival = np.where(satellite_load_deviation >= 0)[0]
        index_failure = np.where(satellite_load_deviation < 0)[0]
        survival_position_3d = self.satellite_position_3d[index_survival]
        failure_position_3d = self.satellite_position_3d[index_failure]

        self.constellation_plotter.update_survival_constellation(position_3d=survival_position_3d)
        self.constellation_plotter.update_failure_constellation(position_3d=failure_position_3d)
        user_satellite_connection = get_connect_relationship(user_position_3d=self.user_position_3d,
                                                             satellite_position_3d=self.satellite_position_3d,
                                                             access_relationship=self.access_relationship)
        self.sat_user_conn_plotter.update_connect(position_pair_3d=user_satellite_connection)

        if self.test_mode:
            mask = np.any(self.routing_path != -1, axis=1)
            self.routing_path_plotter.update_routing_path(position_3d=self.routing_path[mask])

        self.constellation_2d_plotter.update_scene(satellite_position_2d=self.satellite_position_2d,
                                                   user_position_3d=self.user_position_3d,
                                                   access_relationship=self.access_relationship,
                                                   satellite_load_deviation=self.satellite_load_deviation,
                                                   routing_path=self.routing_path,
                                                   test_mode=self.test_mode)
        self._update_selection_markers()
        return


    def update_line_chart(self):
        for chart in self.metric_charts:
            metric_value = getattr(self.shared_metric, chart.metric_name).value
            chart.update_value(self.count, metric_value)
        self.count += 1
        self._refresh_object_details()
        return


    def set_recent_metric_window(self, enabled, seconds=60):
        for chart in self.metric_charts:
            chart.set_recent_window(enabled=enabled, seconds=seconds)
        return


    def select_object(self, object_type, object_id):
        if object_type == "satellite":
            if cg.TOTAL_SATELLITE_NUMBER <= 0:
                return
            object_id = int(np.clip(object_id, 0, cg.TOTAL_SATELLITE_NUMBER - 1))
        else:
            if cg.USER_NUMBER <= 0:
                return
            object_id = int(np.clip(object_id, 0, cg.USER_NUMBER - 1))
        self.selected_object_type = object_type
        self.selected_object_id = object_id
        self.object_detail_panel.set_selection(object_type, object_id)
        self._refresh_object_details(activate=True)
        self._update_selection_markers()
        return


    def _refresh_object_details(self, activate=False):
        if self.selected_object_type is None or self.selected_object_id is None:
            return
        if self.selected_object_type == "satellite":
            title, lines = self._satellite_detail_lines(self.selected_object_id)
        else:
            title, lines = self._user_detail_lines(self.selected_object_id)
        self.object_detail_panel.set_details(title, lines, activate=activate)
        return


    def _satellite_detail_lines(self, satellite_id):
        position_3d = self.satellite_position_3d[satellite_id]
        position_2d = self.satellite_position_2d[satellite_id]
        load_deviation = self.satellite_load_deviation.reshape(-1)[satellite_id]
        connected_users = np.where(self.access_relationship == satellite_id)[0]
        orbit_id = satellite_id // self.satellites_number
        slot_id = satellite_id % self.satellites_number
        status = "failed" if load_deviation < 0 else "normal"
        routing_role = self._routing_role(position_3d)

        lines = [
            "type              : satellite",
            f"id                : {satellite_id}",
            f"orbit / slot      : {orbit_id} / {slot_id}",
            f"status            : {status}",
            f"3d position (km)  : x={position_3d[0]:.3f}, y={position_3d[1]:.3f}, z={position_3d[2]:.3f}",
            f"lat / lon (deg)   : lat={position_2d[0]:.3f}, lon={position_2d[1]:.3f}",
            f"load deviation    : {load_deviation:.6f}",
            f"connected users   : {len(connected_users)}",
            f"routing path role : {routing_role}",
        ]
        if len(connected_users) > 0:
            preview = ", ".join(str(int(item)) for item in connected_users[:12])
            if len(connected_users) > 12:
                preview += ", ..."
            lines.append(f"user ids          : {preview}")
        return f"Satellite {satellite_id}", lines


    def _user_detail_lines(self, user_id):
        position_3d = self.user_position_3d[user_id]
        position_2d = calculation.position_3D_to_2D_array(self.user_position_3d[user_id:user_id + 1])[0]
        satellite_id = int(self.access_relationship[user_id])
        lines = [
            "type              : user",
            f"id                : {user_id}",
            f"3d position (km)  : x={position_3d[0]:.3f}, y={position_3d[1]:.3f}, z={position_3d[2]:.3f}",
            f"lat / lon (deg)   : lat={position_2d[0]:.3f}, lon={position_2d[1]:.3f}",
        ]
        if satellite_id < 0:
            lines.extend([
                "access satellite  : none",
                "access distance   : n/a",
            ])
        else:
            satellite_position_3d = self.satellite_position_3d[satellite_id]
            satellite_position_2d = self.satellite_position_2d[satellite_id]
            distance_km = float(np.linalg.norm(position_3d - satellite_position_3d))
            orbit_id = satellite_id // self.satellites_number
            slot_id = satellite_id % self.satellites_number
            lines.extend([
                f"access satellite  : {satellite_id}",
                f"sat orbit / slot  : {orbit_id} / {slot_id}",
                f"sat lat/lon (deg) : lat={satellite_position_2d[0]:.3f}, lon={satellite_position_2d[1]:.3f}",
                f"access distance   : {distance_km:.3f} km",
            ])
        return f"User {user_id}", lines


    def _routing_role(self, satellite_position_3d):
        if not self.test_mode:
            return "not available"
        mask = np.any(self.routing_path != -1, axis=1)
        active_path = self.routing_path[mask]
        if len(active_path) == 0:
            return "not on path"
        distances = np.linalg.norm(active_path - satellite_position_3d, axis=1)
        nearest_index = int(np.argmin(distances))
        if distances[nearest_index] > 1e-6:
            return "not on path"
        if nearest_index == 0:
            return "source"
        if nearest_index == len(active_path) - 1:
            return "destination"
        return f"hop {nearest_index}"


    def _create_selection_markers(self):
        self.selection_marker_2d = visuals.Markers()
        self.selection_marker_2d.set_data(np.empty((0, 2)),
                                          edge_color="#111827",
                                          face_color=(1, 1, 1, 0),
                                          size=13,
                                          edge_width=2)
        self.selection_marker_2d.order = 60
        self.view_2d.add(self.selection_marker_2d)

        self.selection_marker_3d = visuals.Markers()
        self.selection_marker_3d.set_data(np.empty((0, 3)),
                                          edge_color="#111827",
                                          face_color=(1, 1, 1, 0),
                                          size=16,
                                          edge_width=2)
        self.view_3d.add(self.selection_marker_3d)
        return


    def _update_selection_markers(self):
        if self.selection_marker_2d is None or self.selected_object_type is None:
            return
        if self.selected_object_type == "satellite":
            position_2d = self.satellite_position_2d[self.selected_object_id:self.selected_object_id + 1]
            position_3d = self.satellite_position_3d[self.selected_object_id:self.selected_object_id + 1]
            xy = self._position_2d_to_xy(position_2d)
            size_2d = 13
            size_3d = 16
        else:
            position_3d = self.user_position_3d[self.selected_object_id:self.selected_object_id + 1]
            position_2d = calculation.position_3D_to_2D_array(position_3d)
            xy = self._position_2d_to_xy(position_2d)
            size_2d = 11
            size_3d = 14

        self.selection_marker_2d.set_data(xy,
                                          edge_color="#111827",
                                          face_color=(1, 1, 1, 0),
                                          size=size_2d,
                                          edge_width=2)
        if self.selection_marker_3d is not None:
            self.selection_marker_3d.set_data(position_3d * self.scale_factor,
                                              edge_color="#111827",
                                              face_color=(1, 1, 1, 0),
                                              size=size_3d,
                                              edge_width=2)
        return


    def _handle_2d_mouse_press(self, event):
        if event.button != 1:
            return
        world_position = self._map_2d_event_to_world(event.pos)
        if world_position is None:
            return
        selection = self._nearest_object_on_2d_map(world_position)
        if selection is None:
            return
        object_type, object_id = selection
        self.select_object(object_type, object_id)
        return


    def _nearest_object_on_2d_map(self, xy):
        candidates = []
        satellite_xy = self._position_2d_to_xy(self.satellite_position_2d)
        if len(satellite_xy) > 0:
            satellite_distances = self._wrapped_xy_distance(satellite_xy, xy)
            satellite_id = int(np.argmin(satellite_distances))
            candidates.append(("satellite", satellite_id, float(satellite_distances[satellite_id])))

        if cg.USER_NUMBER > 0:
            user_position_2d = calculation.position_3D_to_2D_array(self.user_position_3d)
            user_xy = self._position_2d_to_xy(user_position_2d)
            user_distances = self._wrapped_xy_distance(user_xy, xy)
            user_id = int(np.argmin(user_distances))
            candidates.append(("user", user_id, float(user_distances[user_id]) * 1.4))

        if not candidates:
            return None
        object_type, object_id, distance = min(candidates, key=lambda item: item[2])
        if distance > 5.0:
            return None
        return object_type, object_id


    def _map_2d_event_to_world(self, event_position):
        try:
            mapped = self.view_2d.scene.transform.imap(event_position)
            return np.array(mapped[:2], dtype=np.float64)
        except Exception:
            # VisPy can reject transient or out-of-canvas mouse positions. An
            # invalid click means "no selection" and must not close the UI.
            return None


    @staticmethod
    def _position_2d_to_xy(position_2d):
        return np.column_stack((position_2d[:, 1], position_2d[:, 0]))


    @staticmethod
    def _wrapped_xy_distance(points, xy):
        delta_x = np.abs(points[:, 0] - xy[0])
        delta_x = np.minimum(delta_x, 360.0 - delta_x)
        delta_y = points[:, 1] - xy[1]
        return np.sqrt(delta_x ** 2 + delta_y ** 2)


    def closeEvent(self, event):
        for subwindow in self.mdi_area.subWindowList():
            if hasattr(subwindow, "allow_close"):
                subwindow.allow_close = True
        super().closeEvent(event)
        return


def get_connect_relationship(user_position_3d, satellite_position_3d, access_relationship):
    valid_user_indices = np.where(access_relationship >= 0)[0]
    valid_user_positions = user_position_3d[valid_user_indices]
    satellite_indices = access_relationship[valid_user_indices]
    valid_satellite_positions = satellite_position_3d[satellite_indices]
    paired_positions = np.zeros((len(valid_user_indices) * 2, 3))
    paired_positions[0::2] = valid_user_positions
    paired_positions[1::2] = valid_satellite_positions
    return paired_positions
