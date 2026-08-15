import ast
import ctypes
import importlib
import multiprocessing
import os
import re
import shutil
import sys
import zipfile
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from numbers import Integral, Real
from pathlib import Path
from multiprocessing import shared_memory

from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtWidgets import QAction, QApplication, QDialog, QDialogButtonBox, QFileDialog
from PyQt5.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea
from PyQt5.QtWidgets import QSizePolicy, QTextEdit, QVBoxLayout, QWidget

from src.tools.config_loader import get_active_config_root
from src.tools.config_loader import get_config_path, get_default_config_path
from src.tools.config_loader import load_configuration
from src.tools.config_loader import resolve_config_root
from src.simulation.variable import constant as ct
from src.simulation.controller.scene_controller import SceneController
from src.simulation.visualization.qt_dashboard_window import QtDashboardWindow


PROJECT_ROOT = Path(__file__).resolve().parents[3]
APP_ICON_PATH = PROJECT_ROOT / "resource" / "logo.png"
cg = load_configuration()


@dataclass
class ConfigEntry:
    name: str
    value: str
    start_line: int
    end_line: int
    is_multiline: bool


class SimulationConfigStore:
    def __init__(self, config_root=None):
        self.config_root = None
        self.config_path = None
        self.default_config_path = None
        self.set_config_root(config_root or get_active_config_root())


    def set_config_root(self, config_root):
        global cg
        cg = load_configuration(config_root)
        self.config_root = get_active_config_root()
        self.config_path = get_config_path(self.config_root)
        self.default_config_path = get_default_config_path(self.config_root)
        return


    def load_entries(self):
        text = self.config_path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        entries = []
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                continue
            name = node.targets[0].id
            if not name.isupper():
                continue
            value = ast.get_source_segment(text, node.value)
            if value is None:
                value = ""
            entries.append(ConfigEntry(name=name,
                                       value=value.strip(),
                                       start_line=node.lineno - 1,
                                       end_line=getattr(node, "end_lineno", node.lineno) - 1,
                                       is_multiline="\n" in value))
        return entries


    def save_values(self, values):
        old_text = self.config_path.read_text(encoding="utf-8")
        old_lines = old_text.splitlines()
        new_lines = list(old_lines)
        entries = self.load_entries()
        for entry in reversed(entries):
            value = values[entry.name].strip()
            if not value:
                raise ValueError(f"{entry.name} cannot be empty.")
            replacement = self._format_assignment(entry.name, value)
            new_lines[entry.start_line:entry.end_line + 1] = replacement

        new_text = "\n".join(new_lines)
        if old_text.endswith("\n"):
            new_text += "\n"
        self._validate_config_text(new_text)
        self.config_path.write_text(new_text, encoding="utf-8")
        self.reload_module()
        return


    def save_single_value(self, name, value):
        value = value.strip()
        if not value:
            raise ValueError(f"{name} cannot be empty.")

        old_text = self.config_path.read_text(encoding="utf-8")
        old_lines = old_text.splitlines()
        new_lines = list(old_lines)
        entries = self.load_entries()
        target_entry = None
        for entry in entries:
            if entry.name == name:
                target_entry = entry
                break
        if target_entry is None:
            raise ValueError(f"{name} was not found in {self.config_path}.")

        replacement = self._format_assignment(name, value)
        new_lines[target_entry.start_line:target_entry.end_line + 1] = replacement
        new_text = "\n".join(new_lines)
        if old_text.endswith("\n"):
            new_text += "\n"
        self._validate_config_text(new_text)
        self.config_path.write_text(new_text, encoding="utf-8")
        self.reload_module()
        return


    def assign_auto_save_file_path(self):
        output_dir = self.get_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_prefix = self._safe_output_prefix(getattr(cg, "OUTPUT_PREFIX", ""))
        index = 0
        while True:
            suffix = "" if index == 0 else f"_{index:02d}"
            if output_prefix:
                file_name = f"easysatsim_result_{output_prefix}_{timestamp}{suffix}.csv"
            else:
                file_name = f"easysatsim_result_{timestamp}{suffix}.csv"
            output_path = output_dir / file_name
            if not output_path.exists():
                break
            index += 1

        config_value = self._runtime_relative_path(output_path)
        self.save_single_value("SAVE_FILE_PATH", repr(config_value))
        return output_path.resolve()


    def validate_runtime_config(self):
        self.reload_module()
        errors = []
        warnings = []

        def has_number(name):
            value = getattr(cg, name, None)
            if isinstance(value, bool) or not isinstance(value, Real):
                errors.append(f"{name} must be a numeric value.")
                return None
            return value

        def require_int(name, minimum=1):
            value = getattr(cg, name, None)
            if isinstance(value, bool) or not isinstance(value, Integral):
                errors.append(f"{name} must be an integer.")
                return None
            if value < minimum:
                errors.append(f"{name} must be >= {minimum}.")
            return value

        def require_positive(name):
            value = has_number(name)
            if value is not None and value <= 0:
                errors.append(f"{name} must be > 0.")
            return value

        def require_non_negative(name):
            value = has_number(name)
            if value is not None and value < 0:
                errors.append(f"{name} must be >= 0.")
            return value

        orbit_number = require_int("ORBIT_NUMBER")
        satellite_per_orbit = require_int("SATELLITE_NUMBER_PRE_ORBIT")
        user_number = require_int("USER_NUMBER", minimum=0)
        user_latitude_min = has_number("USER_LATITUDE_MIN")
        user_latitude_max = has_number("USER_LATITUDE_MAX")
        if user_latitude_min is not None and not -90 <= user_latitude_min <= 90:
            errors.append("USER_LATITUDE_MIN must be in the range [-90, 90].")
        if user_latitude_max is not None and not -90 <= user_latitude_max <= 90:
            errors.append("USER_LATITUDE_MAX must be in the range [-90, 90].")
        if (user_latitude_min is not None and user_latitude_max is not None
                and user_latitude_min >= user_latitude_max):
            errors.append("USER_LATITUDE_MIN must be smaller than USER_LATITUDE_MAX.")
        inclination = has_number("ORBIT_INCLINATION")
        if inclination is not None and not 0 <= inclination <= 90:
            errors.append("ORBIT_INCLINATION must be in the range [0, 90].")

        require_positive("ORBIT_HEIGHT")
        cone_angle = has_number("SATELLITE_CONE_ANGLE")
        if cone_angle is not None and not 0 < cone_angle < 180:
            errors.append("SATELLITE_CONE_ANGLE must be in the range (0, 180).")

        positive_names = [
            "BUFFER_MAX_BYTE",
            "SATELLITE_ROUTING_UPDATE_TIME",
            "SATELLITE_NEIGHBOR_UPDATE_TIME",
            "MAX_NEIGHBOR_UPDATE_TIME",
            "USER_ROUTING_UPDATE_TIME",
            "USER_DATA_RATE_MIN",
            "USER_DATA_RATE_MAX",
            "DATA_SCALING",
            "LINK_TRANSMIT_RATE",
            "SERVICE_RATE",
            "PROCESSING_TIME",
            "NETWORK_RUNNING_STEP_SECOND",
            "PHYSICAL_LAYER_UPDATE_INTERVAL",
            "PHYSICAL_LAYER_DEFAULT_PROCESSING_TIME",
            "ISL_CARRIER_FREQUENCY_HZ",
            "ISL_BANDWIDTH_HZ",
            "ISL_MAX_DISTANCE_M",
            "ISL_STATIC_RATE_BPS",
            "ISL_SPECTRAL_EFFICIENCY",
            "SGL_CARRIER_FREQUENCY_HZ",
            "SGL_BANDWIDTH_HZ",
            "SGL_MAX_DISTANCE_M",
            "SGL_STATIC_RATE_BPS",
            "SGL_SPECTRAL_EFFICIENCY",
        ]
        for name in positive_names:
            require_positive(name)

        non_negative_names = [
            "ISL_MIN_EFFECTIVE_RATE_BPS",
            "ISL_SYSTEM_LOSS_DB",
            "ISL_ATMOSPHERIC_LOSS_DB",
            "ISL_NOISE_FIGURE_DB",
            "ISL_DOPPLER_COMPENSATION_HZ",
            "ISL_RESIDUAL_DOPPLER_LOSS_PER_KHZ_DB",
            "SGL_MIN_EFFECTIVE_RATE_BPS",
            "SGL_SYSTEM_LOSS_DB",
            "SGL_ATMOSPHERIC_LOSS_DB",
            "SGL_NOISE_FIGURE_DB",
            "SGL_DOPPLER_COMPENSATION_HZ",
            "SGL_RESIDUAL_DOPPLER_LOSS_PER_KHZ_DB",
        ]
        for name in non_negative_names:
            require_non_negative(name)

        if user_number == 0:
            warnings.append("USER_NUMBER is 0, so user traffic and access metrics will remain empty.")
        user_rate_min = getattr(cg, "USER_DATA_RATE_MIN", None)
        user_rate_max = getattr(cg, "USER_DATA_RATE_MAX", None)
        if self._is_number(user_rate_min) and self._is_number(user_rate_max) and user_rate_min > user_rate_max:
            errors.append("USER_DATA_RATE_MIN must be <= USER_DATA_RATE_MAX.")
        max_neighbor_update_time = getattr(cg, "MAX_NEIGHBOR_UPDATE_TIME", None)
        neighbor_update_time = getattr(cg, "SATELLITE_NEIGHBOR_UPDATE_TIME", None)
        if (self._is_number(max_neighbor_update_time) and self._is_number(neighbor_update_time)
                and max_neighbor_update_time < neighbor_update_time):
            warnings.append("MAX_NEIGHBOR_UPDATE_TIME is smaller than SATELLITE_NEIGHBOR_UPDATE_TIME.")

        if orbit_number is not None and satellite_per_orbit is not None:
            expected_total = orbit_number * satellite_per_orbit
            actual_total = getattr(cg, "TOTAL_SATELLITE_NUMBER", None)
            if actual_total != expected_total:
                errors.append(
                    f"TOTAL_SATELLITE_NUMBER must equal ORBIT_NUMBER * SATELLITE_NUMBER_PRE_ORBIT ({expected_total})."
                )

        cover_radius = has_number("COVER_RADIUS")
        if cover_radius is not None and cover_radius <= 0:
            errors.append("COVER_RADIUS must be > 0.")

        for name in ("PHYSICAL_LAYER_ENABLE",
                     "PHYSICAL_LAYER_ENABLE_DOPPLER",
                     "PHYSICAL_LAYER_ENABLE_DYNAMIC_RATE",
                     "PHYSICAL_LAYER_USE_CACHE",
                     "ISL_DROP_LINK_IF_DOPPLER_EXCEEDED",
                     "SGL_DROP_LINK_IF_DOPPLER_EXCEEDED"):
            if not isinstance(getattr(cg, name, None), bool):
                errors.append(f"{name} must be True or False.")

        for prefix in ("ISL", "SGL"):
            mode_name = f"{prefix}_RATE_MAPPING_MODE"
            mode_value = getattr(cg, mode_name, None)
            if mode_value not in ("discrete", "shannon", "static"):
                errors.append(f"{mode_name} must be one of: 'discrete', 'shannon', 'static'.")
            self._validate_rate_table(prefix, errors, warnings)

        save_file_path = getattr(cg, "SAVE_FILE_PATH", "")
        if not isinstance(save_file_path, str) or not save_file_path.strip():
            errors.append("SAVE_FILE_PATH must be a non-empty string.")
        else:
            result_path = self.resolve_config_path(save_file_path)
            if result_path.suffix.lower() != ".csv":
                warnings.append("SAVE_FILE_PATH does not end with .csv.")
            try:
                result_path.parent.mkdir(parents=True, exist_ok=True)
                probe_path = result_path.parent / f".easysatsim_write_test_{os.getpid()}"
                probe_path.write_text("", encoding="utf-8")
                if probe_path.exists():
                    probe_path.unlink()
            except Exception as exc:
                errors.append(f"SAVE_FILE_PATH parent directory is not writable: {exc}")

        population_path = getattr(cg, "POPULATION_PATH", "")
        if not isinstance(population_path, str) or not population_path.strip():
            errors.append("POPULATION_PATH must be a non-empty string.")
        else:
            resolved_population_path = self.resolve_config_path(population_path)
            if not resolved_population_path.exists():
                errors.append(f"POPULATION_PATH does not exist: {resolved_population_path}")

        return errors, warnings


    def restore_defaults(self):
        if self.default_config_path is None or not self.default_config_path.exists():
            raise FileNotFoundError(f"Default config file not found: {self.default_config_path}")
        self.apply_configuration_file(self.default_config_path)
        return


    def apply_configuration_file(self, source_path):
        source_path = Path(source_path).resolve()
        self._validate_configuration_filename(source_path)
        text = source_path.read_text(encoding="utf-8")
        self._validate_preset_text(text, source_path)
        self._atomic_write(self.config_path, text)
        self.reload_module()
        return


    def save_current_configuration(self, display_name, overwrite=False):
        preset_name = self._safe_preset_name(display_name)
        target_path = self.config_path.parent / f"simulation_config.{preset_name}.py"
        if target_path.exists() and not overwrite:
            raise FileExistsError(str(target_path))

        text = self.config_path.read_text(encoding="utf-8")
        self._validate_preset_text(text, self.config_path)
        self._atomic_write(target_path, text)
        return target_path


    def reload_module(self):
        global cg
        importlib.invalidate_caches()
        cg = load_configuration(self.config_root)
        return


    @staticmethod
    def _format_assignment(name, value):
        value_lines = value.splitlines()
        if len(value_lines) == 1:
            return [f"{name} = {value_lines[0]}"]
        return [f"{name} = {value_lines[0]}"] + value_lines[1:]


    def _validate_config_text(self, text):
        code = compile(text, str(self.config_path), "exec")
        namespace = {"__file__": str(self.config_path)}
        exec(code, namespace)
        return


    def _validate_preset_text(self, text, source_path):
        self._validate_config_text(text)
        reference_path = self.default_config_path or self.config_path
        reference_text = reference_path.read_text(encoding="utf-8")
        expected_names = self._configuration_names(reference_text)
        actual_names = self._configuration_names(text)
        if actual_names != expected_names:
            missing = [name for name in expected_names if name not in actual_names]
            extra = [name for name in actual_names if name not in expected_names]
            details = []
            if missing:
                details.append(f"missing: {', '.join(missing)}")
            if extra:
                details.append(f"unexpected: {', '.join(extra)}")
            if not details:
                details.append("parameter order differs from simulation_config.default.py")
            raise ValueError(
                f"Invalid configuration schema in {source_path.name} ({'; '.join(details)})."
            )
        return


    @staticmethod
    def _configuration_names(text):
        names = []
        for node in ast.parse(text).body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id.isupper():
                names.append(target.id)
        return names


    @staticmethod
    def _validate_configuration_filename(path):
        if not re.fullmatch(r"simulation_config[A-Za-z0-9_.-]*\.py", path.name):
            raise ValueError(
                "Configuration filename must match simulation_config*.py."
            )
        return


    @staticmethod
    def _safe_preset_name(display_name):
        name = display_name.strip()
        if not name:
            raise ValueError("Configuration name cannot be empty.")
        if name.startswith("simulation_config") or name.endswith(".py"):
            raise ValueError("Enter only the name between simulation_config. and .py.")
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_-").lower()
        if not safe_name:
            raise ValueError("Configuration name must contain a letter or number.")
        return safe_name


    @staticmethod
    def _atomic_write(target_path, text):
        target_path = Path(target_path)
        temporary_path = target_path.with_name(f".{target_path.name}.{os.getpid()}.tmp")
        try:
            temporary_path.write_text(text, encoding="utf-8")
            os.replace(temporary_path, target_path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
        return


    @staticmethod
    def resolve_config_path(path_text):
        path = Path(path_text)
        if path.is_absolute():
            return path
        return (PROJECT_ROOT / "src" / path).resolve()


    def get_output_dir(self):
        save_file_path = getattr(cg, "SAVE_FILE_PATH", "")
        if isinstance(save_file_path, str) and save_file_path.strip():
            return self.resolve_config_path(save_file_path).parent
        if self.config_root == PROJECT_ROOT:
            return PROJECT_ROOT / "output"
        return self.config_root / "output"


    @staticmethod
    def _runtime_relative_path(path):
        relative_path = os.path.relpath(path, PROJECT_ROOT / "src")
        return relative_path.replace(os.sep, "/")


    @staticmethod
    def _safe_output_prefix(value):
        text = str(value).strip()
        if not text:
            return ""
        safe_chars = []
        for char in text:
            if char.isalnum() or char in ("-", "_"):
                safe_chars.append(char)
            else:
                safe_chars.append("_")
        return "".join(safe_chars).strip("_").lower()


    @staticmethod
    def _validate_rate_table(prefix, errors, warnings):
        table_name = f"{prefix}_DISCRETE_RATE_TABLE"
        table_value = getattr(cg, table_name, None)
        if not isinstance(table_value, (list, tuple)) or not table_value:
            errors.append(f"{table_name} must be a non-empty list or tuple.")
            return

        previous_threshold = None
        previous_rate = None
        for index, row in enumerate(table_value):
            if not isinstance(row, (list, tuple)) or len(row) != 2:
                errors.append(f"{table_name}[{index}] must contain exactly two values: (snr_db, rate_bps).")
                continue
            threshold, rate = row
            if isinstance(threshold, bool) or not isinstance(threshold, Real):
                errors.append(f"{table_name}[{index}][0] must be numeric.")
            if isinstance(rate, bool) or not isinstance(rate, Real) or rate <= 0:
                errors.append(f"{table_name}[{index}][1] must be a positive numeric rate.")
            if previous_threshold is not None and isinstance(threshold, Real) and threshold < previous_threshold:
                warnings.append(f"{table_name} SNR thresholds are not sorted; runtime will sort them before use.")
            if previous_rate is not None and isinstance(rate, Real) and rate < previous_rate:
                warnings.append(f"{table_name} rates decrease at row {index}.")
            if isinstance(threshold, Real):
                previous_threshold = threshold
            if isinstance(rate, Real):
                previous_rate = rate
        return


    @staticmethod
    def _is_number(value):
        return not isinstance(value, bool) and isinstance(value, Real)


class ConfigDialog(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.editors = {}
        self.setWindowTitle("Simulation Configuration")
        self.resize(900, 700)
        self._create_layout()
        return


    def _create_layout(self):
        outer = QVBoxLayout(self)
        description = QLabel("Edit values before starting the simulation. Values are Python expressions.")
        description.setStyleSheet("color: #4A4A4A;")
        outer.addWidget(description)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        grid = QGridLayout(content)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        entries = self.store.load_entries()
        for row, entry in enumerate(entries):
            label = QLabel(entry.name)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            label.setStyleSheet("font-weight: 600; color: #202020;")
            if entry.is_multiline:
                editor = QTextEdit()
                editor.setPlainText(entry.value)
                editor.setMinimumHeight(88)
            else:
                editor = QLineEdit()
                editor.setText(entry.value)
            editor.setObjectName(entry.name)
            editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.editors[entry.name] = editor
            grid.addWidget(label, row, 0)
            grid.addWidget(editor, row, 1)

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        return


    def _save(self):
        values = {}
        for name, editor in self.editors.items():
            if isinstance(editor, QTextEdit):
                values[name] = editor.toPlainText()
            else:
                values[name] = editor.text()
        try:
            self.store.save_values(values)
        except Exception as exc:
            QMessageBox.critical(self, "Invalid Configuration", str(exc))
            return
        self.accept()
        return


class ConfigurationPresetDialog(QDialog):
    ACTIONS = (
        ("Default (Starlink Phase I-A)", "default"),
        ("Telesat T2", "telesat_t2"),
        ("Starlink S1", "starlink_s1"),
        ("Quarter-Starlink", "quarter_starlink"),
        ("Select Configuration File...", "select_file"),
        ("Save Current Configuration...", "save_current"),
        ("Cancel", "cancel"),
    )

    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self.selected_action = None
        self.setWindowTitle("Configuration Presets")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        description = QLabel("Select the configuration to use before starting the simulation.")
        description.setWordWrap(True)
        layout.addWidget(description)
        active_path = QLabel(f"Active file: {config_path}")
        active_path.setWordWrap(True)
        active_path.setStyleSheet("color: #555555;")
        layout.addWidget(active_path)
        layout.addSpacing(6)

        for label, action in self.ACTIONS:
            button = QPushButton(label)
            button.setMinimumHeight(34)
            button.clicked.connect(lambda _checked=False, value=action: self._choose(value))
            layout.addWidget(button)
        return


    def _choose(self, action):
        self.selected_action = action
        if action == "cancel":
            self.reject()
        else:
            self.accept()
        return


class RunLogWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EasySatSim Run Log")
        self.resize(760, 460)
        self._create_layout()
        return


    def _create_layout(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        self.log_view.setStyleSheet("""
            QPlainTextEdit {
                background: #FAFAFA;
                color: #202020;
                border: 1px solid #858585;
                border-radius: 1px;
                font-family: Consolas, "Courier New", monospace;
                font-size: 15px;
                padding: 5px;
            }
        """)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        self.clear_button = QPushButton("Clear")
        self.close_button = QPushButton("Close")
        self.clear_button.clicked.connect(self.log_view.clear)
        self.close_button.clicked.connect(self.hide)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.close_button)

        layout.addWidget(self.log_view, 1)
        layout.addLayout(button_layout)
        self.setCentralWidget(root)
        return


    def append_event(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_view.appendPlainText(f"[{timestamp}] [{level}] {message}")
        return


    def to_plain_text(self):
        return self.log_view.toPlainText()


    def closeEvent(self, event):
        event.ignore()
        self.hide()
        return


class ToastNotification(QFrame):
    COLORS = {
        "information": ("#F2F2F2", "#6683A3", "#202020"),
        "warning": ("#FFF4CE", "#B48A24", "#4A3A12"),
        "critical": ("#F8E2E2", "#A65353", "#521F1F"),
    }

    def __init__(self, parent, title, message, severity, close_callback):
        super().__init__(parent)
        self.setObjectName("ToastNotification")
        self.close_callback = close_callback

        self.toast_layout = QHBoxLayout(self)
        self.toast_layout.setContentsMargins(14, 11, 10, 11)
        self.toast_layout.setSpacing(10)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)
        self.title_label = QLabel(title)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-weight: 700; background: transparent;")
        self.time_label = QLabel(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.time_label.setStyleSheet("color: #5A5A5A; font-size: 13px; background: transparent;")
        self.message_label = QLabel(self._add_wrap_points(str(message)))
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("background: transparent;")
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.time_label)
        text_layout.addWidget(self.message_label)
        self.toast_layout.addLayout(text_layout, 1)

        close_button = QPushButton("×")
        close_button.setFixedSize(24, 24)
        close_button.setToolTip("Close notification")
        close_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 0;
                font-size: 21px;
                font-weight: 600;
                padding: 0;
            }
            QPushButton:hover { background: #D6D6D6; }
        """)
        close_button.clicked.connect(self.close_notification)
        self.toast_layout.addWidget(close_button, 0, Qt.AlignTop)

        background, border, text_color = self.COLORS.get(severity, self.COLORS["information"])
        self.setStyleSheet(
            f"QFrame#ToastNotification {{ background: {background}; border: 1px solid {border}; "
            f"border-radius: 2px; color: {text_color}; }}"
        )
        self.fit_to_parent()
        self.show()
        self.raise_()
        return


    def fit_to_parent(self):
        available_width = self.parentWidget().width() - 36
        toast_width = max(300, min(520, available_width))
        self.setFixedWidth(toast_width)

        left, _top, right, _bottom = self.toast_layout.getContentsMargins()
        text_width = toast_width - left - right - self.toast_layout.spacing() - 24
        for label in (self.title_label, self.time_label, self.message_label):
            label.setFixedWidth(text_width)
            wrapped_height = label.heightForWidth(text_width)
            label.setFixedHeight(max(label.fontMetrics().height(), wrapped_height))
        self.toast_layout.invalidate()
        self.toast_layout.activate()
        self.adjustSize()
        return


    @staticmethod
    def _add_wrap_points(text):
        wrapped = []
        run_length = 0
        for char in text:
            wrapped.append(char)
            if char.isspace():
                run_length = 0
                continue
            run_length += 1
            if char in ("/", "\\", ".", "_", "-") or run_length >= 36:
                wrapped.append("\u200b")
                run_length = 0
        return "".join(wrapped)


    def close_notification(self):
        self.close_callback(self)
        return


class ToastNotificationStack:
    def __init__(self, parent):
        self.parent = parent
        self.notifications = []
        self.margin = 18
        self.spacing = 8


    def add_notification(self, title, message, severity="information"):
        notification = ToastNotification(
            self.parent,
            title=title,
            message=message,
            severity=severity,
            close_callback=self.remove_notification,
        )
        self.notifications.append(notification)
        self.reposition()
        return notification


    def remove_notification(self, notification):
        if notification not in self.notifications:
            return
        self.notifications.remove(notification)
        notification.hide()
        notification.deleteLater()
        self.reposition()
        return


    def has_notifications(self):
        return bool(self.notifications)


    def reposition(self):
        if self.parent is None:
            return
        bottom = self.parent.height() - self.margin
        for notification in reversed(self.notifications):
            notification.fit_to_parent()
            bottom -= notification.height()
            x = max(self.margin, self.parent.width() - notification.width() - self.margin)
            notification.move(x, bottom)
            notification.raise_()
            bottom -= self.spacing
        return


class TerminalDashboard:
    def __init__(self):
        self.start_time = None
        self.events = deque(maxlen=6)
        self.ansi_enabled = self._supports_ansi()
        self.append_counter = 0


    def start(self):
        self.start_time = datetime.now()
        self.events.clear()
        self.append_counter = 0
        return


    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.events.append(f"{timestamp}  {message}")
        if not self.ansi_enabled:
            print(f"[{timestamp}] {message}", flush=True)
        return


    def render(self, state, shared_metric=None):
        if self.start_time is None:
            return
        if self.ansi_enabled:
            print("\033[2J\033[H" + self._build_screen(state, shared_metric), end="", flush=True)
        else:
            self.append_counter += 1
            print(self._build_status_line(state, shared_metric), flush=True)
        return


    def finish(self, state, shared_metric=None):
        self.render(state, shared_metric)
        if self.ansi_enabled:
            print("", flush=True)
        return


    def _build_screen(self, state, shared_metric):
        elapsed_seconds = self._elapsed_seconds()
        output_path = SimulationConfigStore.resolve_config_path(cg.SAVE_FILE_PATH)
        lines = [
            "",
            "======================================================================",
            "  EasySatSim Interactive Simulation",
            "======================================================================",
            f"  State        : {state.upper()}",
            f"  Wall elapsed : {elapsed_seconds:>6}s",
            f"  Satellites   : {cg.TOTAL_SATELLITE_NUMBER}",
            f"  Users        : {cg.USER_NUMBER}",
            f"  Orbits       : {cg.ORBIT_NUMBER} x {cg.SATELLITE_NUMBER_PRE_ORBIT}",
            f"  Physical PHY : {self._on_off(cg.PHYSICAL_LAYER_ENABLE)}",
            f"  Output CSV   : {output_path}",
        ]
        if state == "running" and elapsed_seconds < 10:
            lines.extend([
                "----------------------------------------------------------------------",
                "  Notice",
                "----------------------------------------------------------------------",
                "  The simulation has just started. Network metrics are still",
                "  initializing and may be unstable during the first 10 seconds.",
            ])
        lines.extend([
            "----------------------------------------------------------------------",
            "  Live Metrics",
            "----------------------------------------------------------------------",
        ])
        lines.extend(self._metric_lines(shared_metric))
        lines.extend([
            "----------------------------------------------------------------------",
            "  Recent Events",
            "----------------------------------------------------------------------",
        ])
        if self.events:
            lines.extend(f"  {event}" for event in self.events)
        else:
            lines.append("  No events yet.")
        lines.extend([
            "======================================================================",
            "  Controls: use the Qt window buttons for Stop and Export Result.",
            "======================================================================",
        ])
        return "\n".join(lines) + "\n"


    def _build_status_line(self, state, shared_metric):
        elapsed_seconds = self._elapsed_seconds()
        arrived = self._metric(shared_metric, "arrive_packets_number")
        lost = self._metric(shared_metric, "loss_packets_number")
        latency = self._metric(shared_metric, "delay")
        throughput = self._metric(shared_metric, "arrive_packets_byte")
        return (
            f"[EasySatSim] state={state.upper()} elapsed={elapsed_seconds}s "
            f"arrived={arrived:.2f} lost={lost:.2f} "
            f"throughput={self._format_bytes(throughput)}/s latency={latency:.2f}ms"
            f"{self._plain_notice(state, elapsed_seconds)}"
        )


    def _metric_lines(self, shared_metric):
        metric_specs = [
            ("Generated packets", "global_generate_packets_number", ""),
            ("Arrived packets", "arrive_packets_number", ""),
            ("Lost packets", "loss_packets_number", ""),
            ("Throughput", "arrive_packets_byte", "bytes/s"),
            ("Latency", "delay", "ms"),
            ("Load deviation", "load_deviation", ""),
            ("Operational satellites", "normal_satellite_number", ""),
            ("Covered users", "user_cover_number", ""),
            ("Average hop count", "hop_count", "hop"),
        ]
        lines = []
        for label, metric_name, unit in metric_specs:
            value = self._metric(shared_metric, metric_name)
            if metric_name == "arrive_packets_byte":
                value_text = f"{self._format_bytes(value)}/s"
            else:
                value_text = self._format_number(value)
                if unit:
                    value_text = f"{value_text} {unit}"
            lines.append(f"  {label:<24} {value_text:>18}")
        return lines


    def _elapsed_seconds(self):
        if self.start_time is None:
            return 0
        return int((datetime.now() - self.start_time).total_seconds())


    @staticmethod
    def _plain_notice(state, elapsed_seconds):
        if state == "running" and elapsed_seconds < 10:
            return " note=initializing_metrics_unstable"
        return ""


    @staticmethod
    def _metric(shared_metric, metric_name):
        if shared_metric is None:
            return 0.0
        metric = getattr(shared_metric, metric_name, None)
        if metric is None:
            return 0.0
        return float(metric.value)


    @staticmethod
    def _format_number(value):
        if abs(value) >= 10000:
            return f"{value:,.0f}"
        if abs(value) >= 100:
            return f"{value:,.1f}"
        return f"{value:,.2f}"


    @staticmethod
    def _format_bytes(value):
        units = ("B", "KB", "MB", "GB", "TB")
        value = float(value)
        index = 0
        while abs(value) >= 1024 and index < len(units) - 1:
            value = value / 1024
            index += 1
        if index == 0:
            return f"{value:.0f} {units[index]}"
        return f"{value:.2f} {units[index]}"


    @staticmethod
    def _on_off(value):
        return "ON" if value else "OFF"


    @staticmethod
    def _supports_ansi():
        if os.environ.get("EASYSATSIM_TERMINAL_REFRESH", "1") == "0":
            return False
        if os.environ.get("EASYSATSIM_TERMINAL_MODE", "").lower() == "ansi":
            return True
        if os.environ.get("EASYSATSIM_TERMINAL_MODE", "").lower() == "plain":
            return False
        if os.environ.get("PYCHARM_HOSTED") == "1":
            return True
        return bool(getattr(sys.stdout, "isatty", lambda: False)())


def apply_case_scene_configuration(scene_controller, config_root=None):
    setup = get_case_scene_setup(config_root=config_root)
    if setup is None:
        return None

    module, setup_func = setup
    summary = setup_func(scene_controller)
    return {
        "module": module.__name__,
        "function": setup_func.__name__,
        "summary": summary,
    }


def get_case_scene_setup(config_root=None):
    active_config_root = resolve_config_root(config_root or get_active_config_root())
    cases_root = (PROJECT_ROOT / "cases").resolve()
    try:
        relative_path = active_config_root.relative_to(cases_root)
    except ValueError:
        return None
    if not relative_path.parts:
        return None

    case_name = relative_path.parts[0]
    module_name = f"cases.{case_name}.case_setup"
    importlib.invalidate_caches()
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return None
        raise

    setup_func = getattr(module, "configure_scene", None)
    if setup_func is None:
        setup_func = getattr(module, f"configure_{case_name}_scene", None)
    if setup_func is None:
        return None
    return module, setup_func


class SimulationRuntime:
    def __init__(self, scene_controller=None, output_console=False, scene_options=None, config_root=None):
        self.scene_controller = scene_controller
        self.use_external_scene_controller = scene_controller is not None
        self.scene_options = scene_options or {}
        self.config_root = config_root
        self.process_entity = None
        self.process_timer = None
        self.output_console = output_console
        self.test_mode = False
        self.direct_connection_mode = False
        self.case_setup_info = None


    def set_config_root(self, config_root):
        self.config_root = config_root
        return


    def start(self, output_console=None):
        if self.is_running():
            return
        if output_console is not None:
            self.output_console = output_console
        self.case_setup_info = None
        if self.config_root is not None:
            load_configuration(self.config_root)
        if self.scene_controller is None:
            cleanup_stale_shared_memory()
            self.scene_controller = SceneController(**self.scene_options)
            self.scene_controller.create_scene()
            self.scene_controller.default_behavior()
            self.scene_controller.default_stack()
            self.case_setup_info = apply_case_scene_configuration(
                scene_controller=self.scene_controller,
                config_root=self.config_root,
            )
            self.scene_controller.configuration_complete()
        elif not getattr(self.scene_controller, "_is_completed", False):
            raise ValueError("SceneController configuration is not complete.")

        self.process_timer = multiprocessing.Process(target=self.scene_controller._create_timer, args=())
        self.process_entity = multiprocessing.Process(target=self.scene_controller._create_entity,
                                                      args=(self.output_console,))

        self.process_timer.start()
        self.process_entity.start()
        return


    def stop(self):
        warnings = []
        processes = (
            ("entity", self.process_entity),
            ("timer", self.process_timer),
        )
        for label, process in processes:
            if process is None:
                continue
            try:
                if process.is_alive():
                    process.terminate()
            except (AssertionError, OSError, ValueError) as exc:
                warnings.append(f"Could not terminate {label} process: {exc}")
        for label, process in processes:
            if process is None:
                continue
            try:
                process.join(timeout=3)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=3)
            except (AssertionError, OSError, ValueError) as exc:
                warnings.append(f"Could not finish stopping {label} process: {exc}")
        return warnings


    def is_running(self):
        processes = [process for process in (self.process_entity, self.process_timer) if process is not None]
        return any(process.is_alive() for process in processes)


class SimulationControlWindow(QMainWindow):
    STATE_INITIAL = "initial"
    STATE_RUNNING = "running"
    STATE_STOPPED = "stopped"

    def __init__(self, scene_controller=None, output_console=False, auto_start=False,
                 running_time=None, scene_options=None, config_root=None):
        super().__init__()
        self.config_store = SimulationConfigStore(config_root=config_root)
        self.runtime = SimulationRuntime(scene_controller=scene_controller,
                                         output_console=output_console,
                                         scene_options=scene_options,
                                         config_root=self.config_store.config_root)
        self.dashboard = None
        self.state = self.STATE_INITIAL
        self.auto_start = auto_start
        self.running_time = running_time
        self.auto_stop_timer = QTimer(self)
        self.auto_stop_timer.setSingleShot(True)
        self.auto_stop_timer.timeout.connect(self._stop_after_running_time)
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self._monitor_processes)
        self.terminal_dashboard = TerminalDashboard()
        self.run_log_window = RunLogWindow(self)
        self.terminal_timer = QTimer(self)
        self.terminal_timer.timeout.connect(self._render_terminal_dashboard)
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self._update_status_bar)

        self._create_window()
        self._set_state(self.STATE_INITIAL)
        self.ui_timer.start(1000)
        if self.runtime.use_external_scene_controller:
            self._log_event("SceneController received from script entry.")
        elif scene_options:
            self._log_event("Script entry mode is ready. Configure parameters before Start if needed.")
        if self.auto_start:
            QTimer.singleShot(0, self._start_simulation)
        return


    def _create_window(self):
        self.setWindowTitle("EasySatSim")
        self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.resize(1600, 960)
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #F3F6FA;
                color: #202020;
                font-family: Segoe UI, Arial;
                font-size: 16px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                             stop:0 #FCFCFC, stop:1 #DEDEDE);
                border: 1px solid #8B8B8B;
                border-radius: 2px;
                padding: 5px 11px;
            }
            QPushButton:hover {
                border-color: #4F6F91;
                background: #F7FAFD;
            }
            QPushButton:pressed {
                background: #D3D3D3;
                border-color: #666666;
            }
            QPushButton:disabled {
                color: #8F8F8F;
                background: #D8D8D8;
                border-color: #AFAFAF;
            }
            QMenuBar {
                background: #E7E7E7;
                border-bottom: 1px solid #999999;
                padding: 2px 4px;
                font-size: 16px;
            }
            QMenuBar::item {
                background: transparent;
                border-radius: 0;
                padding: 5px 11px;
            }
            QMenuBar::item:selected {
                background: #C9D7E6;
            }
            QMenu {
                background: #F2F2F2;
                border: 1px solid #868686;
                padding: 3px;
                font-size: 16px;
            }
            QMenu::item {
                border-radius: 0;
                padding: 6px 28px 6px 10px;
            }
            QMenu::item:selected {
                background: #315F8C;
                color: #FFFFFF;
            }
            QMenu::item:disabled {
                background: transparent;
                color: #969696;
            }
            QMenuBar::item:disabled {
                background: transparent;
                color: #969696;
            }
            QMenu::separator {
                height: 1px;
                background: #B7B7B7;
                margin: 4px 6px;
            }
            QStatusBar {
                background: #DDDDDD;
                border-top: 1px solid #969696;
                color: #333333;
                font-size: 16px;
            }
            QStatusBar::item {
                border-left: 1px solid #B4B4B4;
            }
            QLabel#RunState {
                font-weight: 700;
                padding: 2px 7px;
            }
            QLabel#ElapsedTime, QLabel#OutputSummary {
                color: #333333;
                padding: 2px 7px;
            }
            QFrame#DashboardHost {
                background: #FFFFFF;
                border: 1px solid #858585;
                border-radius: 2px;
            }
            QFrame#ConfigOverview {
                background: #F8FAFC;
                border: 1px solid #8E8E8E;
                border-radius: 2px;
            }
            QFrame#OverviewSection {
                background: #FFFFFF;
                border: 1px solid #9A9A9A;
                border-radius: 2px;
            }
            QLabel#OverviewTitle {
                color: #202020;
                font-size: 24px;
                font-weight: 700;
            }
            QLabel#SectionTitle {
                color: #202020;
                font-size: 17px;
                font-weight: 700;
            }
            QLabel#ConfigName {
                color: #555555;
            }
            QLabel#ConfigValue {
                color: #202020;
                font-weight: 600;
            }
            QLabel#ConfigReady {
                background: #E8F0E8;
                border: 1px solid #8DA38D;
                border-radius: 2px;
                color: #294529;
                font-weight: 600;
                padding: 6px 8px;
            }
        """)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(6)

        self._create_navigation()
        self._create_status_bar()

        self.dashboard_host = QFrame()
        self.dashboard_host.setObjectName("DashboardHost")
        self.dashboard_layout = QVBoxLayout(self.dashboard_host)
        self.dashboard_layout.setContentsMargins(6, 6, 6, 6)
        self.dashboard_layout.setSpacing(0)
        self.placeholder = self._create_pre_run_overview()
        self.dashboard_layout.addWidget(self.placeholder, 1)

        root_layout.addWidget(self.dashboard_host, 1)
        self.setCentralWidget(root)
        self.notification_stack = ToastNotificationStack(root)
        self._update_status_bar()
        return


    def _create_pre_run_overview(self):
        overview = QFrame()
        overview.setObjectName("ConfigOverview")
        outer = QVBoxLayout(overview)
        outer.setContentsMargins(28, 22, 28, 22)
        outer.setSpacing(12)

        title = QLabel("Configuration Overview")
        title.setObjectName("OverviewTitle")
        subtitle = QLabel("Review the active settings before starting the simulation.")
        subtitle.setStyleSheet("color: #555555; font-size: 16px;")
        outer.addWidget(title)
        outer.addWidget(subtitle)

        sections = QHBoxLayout()
        sections.setSpacing(12)
        constellation = self._create_overview_section("Constellation", [
            ("Orbital planes", "orbit_number"),
            ("Satellites per plane", "satellites_per_orbit"),
            ("Total satellites", "total_satellites"),
        ])
        simulation = self._create_overview_section("Simulation", [
            ("Users", "user_number"),
            ("Network step", "network_step"),
            ("Physical layer", "physical_layer"),
        ])
        sections.addWidget(constellation, 1)
        sections.addWidget(simulation, 1)
        outer.addLayout(sections)

        paths = self._create_overview_section("Active Files", [
            ("Configuration", "configuration_path"),
            ("Result output", "result_path"),
        ])
        outer.addWidget(paths)
        self.config_ready_label = QLabel()
        self.config_ready_label.setObjectName("ConfigReady")
        outer.addWidget(self.config_ready_label)
        outer.addStretch(1)
        self._refresh_pre_run_overview()
        return overview


    def _create_overview_section(self, title, fields):
        section = QFrame()
        section.setObjectName("OverviewSection")
        layout = QGridLayout(section)
        layout.setContentsMargins(14, 11, 14, 12)
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(7)
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        layout.addWidget(title_label, 0, 0, 1, 2)
        for row, (label_text, field_name) in enumerate(fields, start=1):
            name_label = QLabel(label_text)
            name_label.setObjectName("ConfigName")
            value_label = QLabel()
            value_label.setObjectName("ConfigValue")
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            value_label.setWordWrap(True)
            setattr(self, f"overview_{field_name}_label", value_label)
            layout.addWidget(name_label, row, 0)
            layout.addWidget(value_label, row, 1)
        layout.setColumnStretch(1, 1)
        return section


    def _refresh_pre_run_overview(self):
        if not hasattr(self, "overview_orbit_number_label"):
            return
        self.overview_orbit_number_label.setText(str(cg.ORBIT_NUMBER))
        self.overview_satellites_per_orbit_label.setText(str(cg.SATELLITE_NUMBER_PRE_ORBIT))
        self.overview_total_satellites_label.setText(str(cg.TOTAL_SATELLITE_NUMBER))
        self.overview_user_number_label.setText(str(cg.USER_NUMBER))
        self.overview_network_step_label.setText(f"{cg.NETWORK_RUNNING_STEP_SECOND} s")
        physical_layer = "Enabled" if getattr(cg, "PHYSICAL_LAYER_ENABLE", False) else "Disabled"
        self.overview_physical_layer_label.setText(physical_layer)
        self.overview_configuration_path_label.setText(str(self.config_store.config_path))
        output_path = self._resolve_output_path(cg.SAVE_FILE_PATH)
        self.overview_result_path_label.setText(str(output_path))
        if self.runtime.use_external_scene_controller:
            status_text = "Configuration loaded from the script entry. Ready to start."
        else:
            status_text = "Configuration loaded. Ready to start."
        self.config_ready_label.setText(status_text)
        return


    def _create_navigation(self):
        simulation_menu = self.menuBar().addMenu("Simulation")
        self.start_action = QAction("Start Simulation", self)
        self.stop_action = QAction("Stop Simulation", self)
        self.run_log_action = QAction("Run Log", self)
        simulation_menu.addAction(self.start_action)
        simulation_menu.addAction(self.stop_action)
        simulation_menu.addSeparator()
        simulation_menu.addAction(self.run_log_action)

        configuration_menu = self.menuBar().addMenu("Configuration")
        self.configure_action = QAction("Edit Configuration", self)
        self.preset_action = QAction("Configuration Presets", self)
        configuration_menu.addAction(self.configure_action)
        configuration_menu.addAction(self.preset_action)

        results_menu = self.menuBar().addMenu("Results")
        self.export_action = QAction("Export Result", self)
        self.package_action = QAction("Package Run", self)
        self.open_output_action = QAction("Open Output Folder", self)
        self.screenshot_action = QAction("Save Screenshot", self)
        results_menu.addAction(self.export_action)
        results_menu.addAction(self.package_action)
        results_menu.addSeparator()
        results_menu.addAction(self.open_output_action)
        results_menu.addAction(self.screenshot_action)

        view_menu = self.menuBar().addMenu("View")
        panels_menu = view_menu.addMenu("Show Panel")
        self.show_3d_action = QAction("3D View", self)
        self.show_details_action = QAction("Object Details", self)
        self.show_2d_action = QAction("2D View", self)
        self.show_metrics_action = QAction("Performance Metrics", self)
        self.panel_actions = [
            self.show_3d_action,
            self.show_details_action,
            self.show_2d_action,
            self.show_metrics_action,
        ]
        panels_menu.addActions(self.panel_actions)
        view_menu.addSeparator()
        self.recent_metrics_action = QAction("Show Recent 60 Seconds", self)
        self.recent_metrics_action.setCheckable(True)
        self.tile_action = QAction("Tile Panels", self)
        self.cascade_action = QAction("Cascade Panels", self)
        view_menu.addAction(self.recent_metrics_action)
        view_menu.addSeparator()
        view_menu.addAction(self.tile_action)
        view_menu.addAction(self.cascade_action)

        self.start_action.triggered.connect(self._start_simulation)
        self.stop_action.triggered.connect(self._stop_simulation)
        self.run_log_action.triggered.connect(self._show_run_log)
        self.configure_action.triggered.connect(self._configure)
        self.preset_action.triggered.connect(self._configure_presets)
        self.export_action.triggered.connect(self._export_result)
        self.package_action.triggered.connect(self._package_run_results)
        self.open_output_action.triggered.connect(self._open_output_folder)
        self.screenshot_action.triggered.connect(self._save_screenshot)
        self.show_3d_action.triggered.connect(lambda: self._show_dashboard_panel("3d"))
        self.show_details_action.triggered.connect(lambda: self._show_dashboard_panel("details"))
        self.show_2d_action.triggered.connect(lambda: self._show_dashboard_panel("2d"))
        self.show_metrics_action.triggered.connect(lambda: self._show_dashboard_panel("metrics"))
        self.recent_metrics_action.toggled.connect(self._toggle_recent_metrics)
        self.tile_action.triggered.connect(self._tile_panels)
        self.cascade_action.triggered.connect(self._cascade_panels)
        return


    def _create_status_bar(self):
        status_bar = self.statusBar()
        status_bar.setSizeGripEnabled(False)
        self.state_indicator = QLabel("● Ready")
        self.state_indicator.setObjectName("RunState")
        self.elapsed_label = QLabel("Elapsed 0s")
        self.elapsed_label.setObjectName("ElapsedTime")
        self.output_summary_label = QLabel()
        self.output_summary_label.setObjectName("OutputSummary")
        self.output_summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        status_bar.addWidget(self.state_indicator)
        status_bar.addWidget(self.elapsed_label)
        status_bar.addPermanentWidget(self.output_summary_label, 1)
        return


    def _set_state(self, state):
        self.state = state
        is_initial = state == self.STATE_INITIAL
        is_running = state == self.STATE_RUNNING
        is_stopped = state == self.STATE_STOPPED
        is_test_mode = bool(self.runtime.scene_options.get("test_mode"))
        can_configure = (
            is_initial
            and not self.runtime.use_external_scene_controller
            and not is_test_mode
        )
        self.start_action.setEnabled(is_initial)
        self.stop_action.setEnabled(is_running)
        self.configure_action.setEnabled(can_configure)
        self.preset_action.setEnabled(can_configure)
        self.export_action.setEnabled(is_stopped)
        self.package_action.setEnabled(is_stopped)
        self.open_output_action.setEnabled(is_stopped)
        dashboard_available = self.dashboard is not None
        self.screenshot_action.setEnabled(dashboard_available)
        self.recent_metrics_action.setEnabled(dashboard_available)
        self.tile_action.setEnabled(dashboard_available)
        self.cascade_action.setEnabled(dashboard_available)
        for action in self.panel_actions:
            action.setEnabled(dashboard_available)
        self._update_status_bar()
        return


    def _configure(self):
        dialog = ConfigDialog(self.config_store, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.config_store.reload_module()
            self._refresh_pre_run_overview()
            self._update_status_bar()
            self._log_event("Configuration saved.")
            self._show_notification(
                "Configuration saved",
                "The updated settings will be used when the simulation starts.",
            )
        return


    def _start_simulation(self):
        self.terminal_dashboard.start()
        self._log_event("Start requested.")
        try:
            self.config_store.reload_module()
            self.runtime.set_config_root(self.config_store.config_root)
            self._log_event("Configuration loaded.")
            if getattr(cg, "AUTO_ASSIGN_SAVE_FILE_PATH", True):
                output_path = self.config_store.assign_auto_save_file_path()
            else:
                output_path = self.config_store.resolve_config_path(cg.SAVE_FILE_PATH)
                output_path.parent.mkdir(parents=True, exist_ok=True)
            self._log_event(f"Run result file assigned: {output_path}")
            self._refresh_pre_run_overview()
            self._update_status_bar()

            validation_errors, validation_warnings = self.config_store.validate_runtime_config()
            if self.runtime.scene_options.get("test_mode") and cg.USER_NUMBER != 2:
                validation_errors.append("USER_NUMBER must be 2 when the script entry uses test_mode=True.")
            if self.runtime.scene_options.get("direct_connection_mode") and cg.USER_NUMBER != 2:
                validation_errors.append("USER_NUMBER must be 2 when direct_connection_mode=True.")
            if validation_warnings:
                for warning in validation_warnings:
                    self._log_event(f"Configuration warning: {warning}", level="WARN")
                self._show_notification(
                    "Configuration warnings",
                    f"{len(validation_warnings)} warning(s) found. Open Run Log for details.",
                    severity="warning",
                )
            if validation_errors:
                for error in validation_errors:
                    self._log_event(f"Configuration error: {error}", level="ERROR")
                self._show_notification(
                    "Configuration validation failed",
                    f"{len(validation_errors)} error(s) found. Open Run Log for details.",
                    severity="critical",
                )
                self.terminal_dashboard.finish(self.STATE_INITIAL, self._shared_metric())
                self._set_state(self.STATE_INITIAL)
                return
            self._log_event("Configuration validation passed.")

            self.runtime.start()
            if self.runtime.case_setup_info is not None:
                setup_info = self.runtime.case_setup_info
                self._log_event(
                    f"Case scene setup applied: {setup_info['module']}.{setup_info['function']}"
                )
            self._log_event("Simulation processes started.")
            self._attach_dashboard()
            self._log_event("Qt visualization attached.")
        except Exception as exc:
            self.terminal_timer.stop()
            self._log_event(f"Start failed: {exc}", level="ERROR")
            for warning in self.runtime.stop():
                self._log_event(warning, level="WARN")
            self._cleanup_shared_memory()
            self.terminal_dashboard.finish(self.STATE_INITIAL, self._shared_metric())
            self._show_notification("Simulation could not start", str(exc), severity="critical")
            self._set_state(self.STATE_INITIAL)
            return
        self.monitor_timer.start(1000)
        self.terminal_timer.start(1000)
        self._set_state(self.STATE_RUNNING)
        self._show_notification(
            "Simulation started",
            "Metrics are initializing and may be unstable during the first 10 seconds.",
            severity="warning",
        )
        if self.running_time is not None:
            self.auto_stop_timer.start(int(self.running_time * 1000))
            self._log_event(f"Automatic stop scheduled after {self.running_time} seconds.")
        self._render_terminal_dashboard()
        return


    def _attach_dashboard(self):
        if self.placeholder is not None:
            self.placeholder.hide()
            self.dashboard_layout.removeWidget(self.placeholder)
            self.placeholder.deleteLater()
            self.placeholder = None
        self.dashboard = QtDashboardWindow(shared_metric=self.runtime.scene_controller.shared_metric,
                                           test_mode=self.runtime.scene_controller.test_mode)
        self.dashboard.setParent(self.dashboard_host)
        self.dashboard.setWindowFlags(Qt.Widget)
        self.dashboard_layout.addWidget(self.dashboard, 1)
        self.dashboard.create_simulation_scene()
        self.dashboard.start()
        self.dashboard.set_recent_metric_window(self.recent_metrics_action.isChecked(), seconds=60)
        self.dashboard.show()
        return


    def _stop_simulation(self):
        self._log_event("Stop requested.")
        self.auto_stop_timer.stop()
        self.monitor_timer.stop()
        self.terminal_timer.stop()
        for warning in self.runtime.stop():
            self._log_event(warning, level="WARN")
        self._stop_dashboard_timers()
        self._set_state(self.STATE_STOPPED)
        self._log_event("Simulation stopped.")
        self._show_notification("Simulation stopped", "The simulation processes have been stopped.")
        self.terminal_dashboard.finish(self.state, self._shared_metric())
        return


    def _stop_after_running_time(self):
        if self.state != self.STATE_RUNNING:
            return
        self._log_event("Running time limit reached.")
        self._stop_simulation()
        return


    def _monitor_processes(self):
        if self.state == self.STATE_RUNNING and not self.runtime.is_running():
            self.monitor_timer.stop()
            self.terminal_timer.stop()
            self._stop_dashboard_timers()
            self._set_state(self.STATE_STOPPED)
            self._log_event("Simulation ended.")
            self.terminal_dashboard.finish(self.state, self._shared_metric())
            self._show_notification(
                "Simulation ended",
                "The simulation processes ended before Stop was requested.",
                severity="warning",
            )
        return


    def _render_terminal_dashboard(self):
        self.terminal_dashboard.render(self.state, self._shared_metric())
        return


    def _update_status_bar(self):
        elapsed_seconds = 0
        if self.terminal_dashboard.start_time is not None:
            elapsed_seconds = self.terminal_dashboard._elapsed_seconds()
        self.elapsed_label.setText(f"Elapsed {self._format_elapsed(elapsed_seconds)}")
        output_path = self._resolve_output_path(cg.SAVE_FILE_PATH)
        self.output_summary_label.setText(f"Output: {output_path.name}")
        self.output_summary_label.setToolTip(str(output_path))
        if self.state == self.STATE_INITIAL:
            self.state_indicator.setText("● Ready")
            self.state_indicator.setStyleSheet("color: #64748B;")
        elif self.state == self.STATE_RUNNING:
            self.state_indicator.setText("● Running")
            self.state_indicator.setStyleSheet("color: #15803D;")
        else:
            self.state_indicator.setText("● Stopped")
            self.state_indicator.setStyleSheet("color: #991B1B;")
        return


    def _shared_metric(self):
        if self.runtime.scene_controller is None:
            return None
        return self.runtime.scene_controller.shared_metric


    @staticmethod
    def _format_elapsed(seconds):
        minutes, sec = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes:02d}m {sec:02d}s"
        if minutes:
            return f"{minutes}m {sec:02d}s"
        return f"{sec}s"


    def _tile_panels(self):
        if self.dashboard is not None:
            self.dashboard.mdi_area.tileSubWindows()
        return


    def _cascade_panels(self):
        if self.dashboard is not None:
            self.dashboard.mdi_area.cascadeSubWindows()
        return


    def _show_dashboard_panel(self, panel_name):
        if self.dashboard is not None:
            self.dashboard.show_panel(panel_name)
        return


    def _toggle_recent_metrics(self, enabled):
        if self.dashboard is not None:
            self.dashboard.set_recent_metric_window(enabled, seconds=60)
        return


    def _configure_presets(self):
        dialog = ConfigurationPresetDialog(self.config_store.config_path, parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return

        action = dialog.selected_action
        if action == "select_file":
            self._select_configuration_file()
            return
        if action == "save_current":
            self._save_current_configuration()
            return

        preset_files = {
            "default": ("Default (Starlink Phase I-A)", "simulation_config.default.py"),
            "telesat_t2": ("Telesat T2", "simulation_config.telesat_t2.py"),
            "starlink_s1": ("Starlink S1", "simulation_config.starlink_s1.py"),
            "quarter_starlink": ("Quarter-Starlink", "simulation_config.quarter_starlink.py"),
        }
        if action in preset_files:
            label, file_name = preset_files[action]
            self._apply_configuration_file(
                self.config_store.config_path.parent / file_name,
                label,
            )
        return


    def _select_configuration_file(self):
        selected_file, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Select Configuration File",
            str(self.config_store.config_path.parent),
            "EasySatSim Configurations (simulation_config*.py)",
        )
        if not selected_file:
            return
        self._apply_configuration_file(Path(selected_file), Path(selected_file).name)
        return


    def _apply_configuration_file(self, source_path, display_name):
        try:
            self.config_store.apply_configuration_file(source_path)
            if not self.runtime.use_external_scene_controller:
                self.runtime.scene_controller = None
        except Exception as exc:
            self._log_event(f"Configuration could not be applied: {exc}", level="ERROR")
            self._show_notification("Configuration could not be applied", str(exc),
                                    severity="critical")
            return

        self._refresh_pre_run_overview()
        self._update_status_bar()
        self._log_event(f"Configuration applied: {source_path}")
        self._show_notification(
            "Configuration applied",
            f"{display_name} is now active.",
        )
        return


    def _save_current_configuration(self):
        name, accepted = QInputDialog.getText(
            self,
            "Save Current Configuration",
            "Configuration name:\nThe file will be saved as simulation_config.<name>.py",
        )
        if not accepted:
            return

        try:
            safe_name = self.config_store._safe_preset_name(name)
        except ValueError as exc:
            self._show_notification("Configuration was not saved", str(exc), severity="warning")
            return

        target_path = self.config_store.config_path.parent / f"simulation_config.{safe_name}.py"
        overwrite = False
        if target_path.exists():
            response = QMessageBox.question(
                self,
                "Replace Configuration",
                f"{target_path.name} already exists. Replace it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if response != QMessageBox.Yes:
                return
            overwrite = True

        try:
            saved_path = self.config_store.save_current_configuration(name, overwrite=overwrite)
        except Exception as exc:
            self._log_event(f"Configuration save failed: {exc}", level="ERROR")
            self._show_notification("Configuration was not saved", str(exc), severity="critical")
            return

        self._log_event(f"Configuration saved: {saved_path}")
        self._show_notification(
            "Configuration saved",
            f"Saved as {saved_path.name} in the configuration folder.",
        )
        return


    def _stop_dashboard_timers(self):
        if self.dashboard is None:
            return
        for timer_name in ("active_timer", "metric_timer"):
            timer = getattr(self.dashboard, timer_name, None)
            if timer is not None:
                timer.stop()
        return


    def _export_result(self):
        try:
            source_path = self._resolve_output_path(cg.SAVE_FILE_PATH)
        except Exception as exc:
            self._log_event(f"Export failed: {exc}", level="ERROR")
            self._show_notification("Result could not be exported", str(exc),
                                    severity="critical")
            return
        if not source_path.exists():
            self._log_event(f"Result file does not exist: {source_path}", level="WARN")
            self._show_notification("No result available", f"Result file does not exist: {source_path}",
                                    severity="warning")
            return

        default_path = self._next_available_export_path(source_path)
        target_path, _ = QFileDialog.getSaveFileName(self,
                                                     "Export Result",
                                                     str(default_path),
                                                     "CSV Files (*.csv);;All Files (*)")
        if not target_path:
            return
        target = Path(target_path)
        try:
            source_resolved = source_path.resolve()
            target_resolved = target.resolve()
            if source_resolved == target_resolved:
                self._log_event(f"Export skipped because the result is already located at: {source_path}")
                self._show_notification(
                    "Result already available",
                    f"The selected file is the original result file: {source_path}",
                    severity="warning",
                )
                return
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)
        except PermissionError as exc:
            message = (
                f"The destination file cannot be replaced because it is open or locked by another "
                f"program: {target}. Close the file in Excel, a text editor, or another application, "
                f"then try again, or export using a different filename."
            )
            self._log_event(f"Export failed: {message} ({exc})", level="ERROR")
            self._show_notification("Result could not be exported", message, severity="critical")
            return
        except OSError as exc:
            self._log_event(f"Export failed: {exc}", level="ERROR")
            self._show_notification("Result could not be exported", str(exc), severity="critical")
            return
        self._log_event(f"Result exported to: {target}")
        self.terminal_dashboard.finish(self.state, self._shared_metric())
        self._show_notification("Result exported", str(target))
        return


    def _package_run_results(self):
        self._log_event("Run package requested.")
        try:
            result_path = self._resolve_output_path(cg.SAVE_FILE_PATH)
        except Exception as exc:
            self._log_event(f"Package failed: {exc}", level="ERROR")
            self._show_notification("Run could not be packaged", str(exc),
                                    severity="critical")
            return
        if not result_path.exists():
            self._log_event(f"Cannot package run because result file does not exist: {result_path}", level="WARN")
            self._show_notification("No result available", f"Result file does not exist: {result_path}",
                                    severity="warning")
            return

        package_path = self._next_available_output_path("easysatsim_run_package", ".zip")
        screenshot_path = self._next_available_output_path(".easysatsim_package_screenshot", ".png")
        screenshot_saved = False
        try:
            package_path.parent.mkdir(parents=True, exist_ok=True)
            pixmap = self.grab()
            screenshot_saved = pixmap.save(str(screenshot_path))

            with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(result_path, arcname=f"results/{result_path.name}")
                archive.write(self.config_store.config_path, arcname="configuration/simulation_config.py")
                if self.config_store.default_config_path is not None:
                    archive.write(self.config_store.default_config_path,
                                  arcname="configuration/simulation_config.default.py")
                archive.writestr("logs/run_log.txt", self.run_log_window.to_plain_text())
                archive.writestr("manifest.txt", self._build_package_manifest(result_path, package_path))
                if screenshot_saved:
                    archive.write(screenshot_path, arcname="screenshots/main_window.png")
        except Exception as exc:
            self._log_event(f"Package failed: {exc}", level="ERROR")
            self._show_notification("Run could not be packaged", str(exc),
                                    severity="critical")
            return
        finally:
            try:
                if screenshot_path.exists():
                    screenshot_path.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                self._log_event(
                    f"Temporary package screenshot could not be removed: {screenshot_path} ({exc})",
                    level="WARN",
                )

        if not screenshot_saved:
            self._log_event("Package created without screenshot because the current window capture failed.", level="WARN")
        self._log_event(f"Run package created: {package_path}")
        self.terminal_dashboard.finish(self.state, self._shared_metric())
        self._show_notification("Run packaged", str(package_path))
        return


    def _save_screenshot(self):
        default_name = f"easysatsim_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        default_path = self.config_store.get_output_dir() / default_name
        target_path, _ = QFileDialog.getSaveFileName(self,
                                                     "Save Screenshot",
                                                     str(default_path),
                                                     "PNG Files (*.png);;All Files (*)")
        if not target_path:
            return
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        pixmap = self.grab()
        if not pixmap.save(str(target)):
            self._log_event(f"Screenshot save failed: {target}", level="ERROR")
            self._show_notification("Screenshot could not be saved", str(target),
                                    severity="critical")
            return
        self._log_event(f"Screenshot saved to: {target}")
        self._show_notification("Screenshot saved", str(target))
        return


    def _open_output_folder(self):
        folder = self._resolve_output_path(cg.SAVE_FILE_PATH).parent
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if not self._open_local_folder(folder):
                raise RuntimeError("The operating system did not accept the folder-open request.")
        except Exception as exc:
            self._log_event(f"Open output folder failed: {exc}", level="ERROR")
            self._show_notification("Output folder could not be opened", str(exc),
                                    severity="critical")
            return
        self._log_event(f"Output folder opened: {folder}")
        self._show_notification("Output folder opened", str(folder))
        return


    @staticmethod
    def _open_local_folder(folder):
        folder_url = QUrl.fromLocalFile(str(Path(folder).resolve()))
        return bool(QDesktopServices.openUrl(folder_url))


    def _show_run_log(self):
        self.run_log_window.show()
        self.run_log_window.raise_()
        self.run_log_window.activateWindow()
        return


    def _log_event(self, message, level="INFO"):
        self.run_log_window.append_event(message, level=level)
        self.terminal_dashboard.log(message)
        return


    def _show_notification(self, title, message, severity="information"):
        self.notification_stack.add_notification(title, message, severity=severity)
        return


    @staticmethod
    def _resolve_output_path(path_text):
        return SimulationConfigStore.resolve_config_path(path_text)


    def _next_available_output_path(self, prefix, suffix):
        output_dir = self.config_store.get_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        index = 0
        while True:
            index_suffix = "" if index == 0 else f"_{index:02d}"
            path = output_dir / f"{prefix}_{timestamp}{index_suffix}{suffix}"
            if not path.exists():
                return path
            index += 1


    @staticmethod
    def _next_available_export_path(source_path):
        source_path = Path(source_path)
        index = 0
        while True:
            index_suffix = "" if index == 0 else f"_{index:02d}"
            candidate = source_path.with_name(
                f"{source_path.stem}_export{index_suffix}{source_path.suffix}"
            )
            if not candidate.exists():
                return candidate
            index += 1


    def _build_package_manifest(self, result_path, package_path):
        elapsed_seconds = 0
        if self.terminal_dashboard.start_time is not None:
            elapsed_seconds = self.terminal_dashboard._elapsed_seconds()
        lines = [
            "EasySatSim run package",
            f"created_at          : {datetime.now().isoformat(timespec='seconds')}",
            f"package_path        : {package_path}",
            f"result_csv          : {result_path}",
            f"configuration_file  : {self.config_store.config_path}",
            f"elapsed_wall_time_s : {elapsed_seconds}",
            f"state               : {self.state}",
            f"satellites          : {cg.TOTAL_SATELLITE_NUMBER}",
            f"users               : {cg.USER_NUMBER}",
            f"orbits              : {cg.ORBIT_NUMBER} x {cg.SATELLITE_NUMBER_PRE_ORBIT}",
            f"physical_layer      : {cg.PHYSICAL_LAYER_ENABLE}",
        ]
        return "\n".join(lines) + "\n"


    def resizeEvent(self, event):
        super().resizeEvent(event)
        notification_stack = getattr(self, "notification_stack", None)
        if notification_stack is not None and notification_stack.has_notifications():
            notification_stack.reposition()
        return


    def closeEvent(self, event):
        if self.state == self.STATE_RUNNING:
            reply = QMessageBox.question(self,
                                         "Stop Simulation",
                                         "The simulation is running. Stop it and close the window?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                event.ignore()
                return
            self._stop_simulation()
        self._cleanup_shared_memory()
        super().closeEvent(event)
        return


    def _cleanup_shared_memory(self):
        if self.dashboard is not None:
            for name in dir(self.dashboard):
                if not name.startswith("_shm_"):
                    continue
                shm = getattr(self.dashboard, name)
                try:
                    shm.close()
                except (BufferError, OSError) as exc:
                    self._log_event(f"Shared memory close failed ({name}): {exc}", level="WARN")
        shared_value = None
        if self.runtime.scene_controller is not None:
            shared_value = getattr(self.runtime.scene_controller, "shared_value", None)
        if shared_value is None:
            return
        for name in dir(shared_value):
            if not name.startswith("_shm_"):
                continue
            shm = getattr(shared_value, name)
            try:
                shm.close()
            except (BufferError, OSError) as exc:
                self._log_event(f"Shared memory close failed ({name}): {exc}", level="WARN")
            try:
                shm.unlink()
            except FileNotFoundError:
                pass
            except (BufferError, OSError) as exc:
                self._log_event(f"Shared memory unlink failed ({name}): {exc}", level="WARN")
        return


def cleanup_stale_shared_memory():
    names = [
        ct.SHM_CURRENT_TIME,
        ct.SHM_SATELLITE_POSITION_3D,
        ct.SHM_SATELLITE_POSITION_2D,
        ct.SHM_ORBIT_POSITION_3D,
        ct.SHM_USER_POSITION_3D,
        ct.SHM_ACCESS_RELATIONSHIP,
        ct.SHM_ROUTING_PATH,
        ct.SHM_SATELLITE_LOAD_DEVIATION,
        ct.SHM_SATELLITE_LATENCY,
    ]
    for name in names:
        try:
            shm = shared_memory.SharedMemory(name=name)
        except FileNotFoundError:
            continue
        try:
            shm.unlink()
        except FileNotFoundError:
            pass
        except (BufferError, OSError) as exc:
            print(f"[Warning] Stale shared memory unlink failed ({name}): {exc}")
        try:
            shm.close()
        except (BufferError, OSError) as exc:
            print(f"[Warning] Stale shared memory close failed ({name}): {exc}")
    return


def run_control_window(scene_controller=None, output_console=False, auto_start=False,
                       running_time=None, scene_options=None, config_root=None):
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    if config_root is not None:
        load_configuration(config_root)
    os.chdir(PROJECT_ROOT / "src")
    print("======================================================================", flush=True)
    print("  EasySatSim", flush=True)
    print("======================================================================", flush=True)
    print(f"  Project root : {PROJECT_ROOT}", flush=True)
    print(f"  Config file  : {get_config_path(get_active_config_root())}", flush=True)
    if scene_controller is not None:
        print("  Entry mode   : script SceneController", flush=True)
    elif scene_options:
        print("  Entry mode   : script deferred configuration", flush=True)
    else:
        print("  Entry mode   : interactive configuration", flush=True)
    print("  Status       : Qt control window ready", flush=True)
    print("----------------------------------------------------------------------", flush=True)
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("EasySatSim.Visualization")
        except (AttributeError, OSError):
            pass
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setApplicationName("EasySatSim")
    app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    window = SimulationControlWindow(scene_controller=scene_controller,
                                     output_console=output_console,
                                     auto_start=auto_start,
                                     running_time=running_time,
                                     scene_options=scene_options,
                                     config_root=config_root)
    window.show()
    return app.exec_()


def main():
    return run_control_window()
