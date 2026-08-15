import importlib
import importlib.metadata
import sys
from pathlib import Path

from tests.diagnostics.common import run_step


REQUIRED = {
    "numpy": "numpy",
    "numba": "numba",
    "colorama": "colorama",
    "Pillow": "PIL",
    "PyQt5": "PyQt5",
    "vispy": "vispy",
    "pyqtgraph": "pyqtgraph",
}


def package_version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def check():
    versions = {name: package_version(name) for name in REQUIRED}
    missing = [name for name, value in versions.items() if value is None]
    if missing:
        raise RuntimeError("Missing required packages: " + ", ".join(missing))
    for import_name in REQUIRED.values():
        importlib.import_module(import_name)

    from PyQt5.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, QLibraryInfo

    plugins_path = Path(QLibraryInfo.location(QLibraryInfo.PluginsPath))
    platform_plugins_path = plugins_path / "platforms"
    expected_plugin = {
        "win32": "qwindows.dll",
        "darwin": "libqcocoa.dylib",
    }.get(sys.platform, "libqxcb.so" if sys.platform.startswith("linux") else None)
    platform_plugins = sorted(
        path.name for path in platform_plugins_path.iterdir() if path.is_file()
    ) if platform_plugins_path.is_dir() else []
    if expected_plugin and expected_plugin not in platform_plugins:
        raise RuntimeError(
            f"Required Qt platform plugin is missing: {platform_plugins_path / expected_plugin}"
        )

    qt_bindings = {
        name: package_version(name)
        for name in ("PyQt5", "PyQt6", "PySide2", "PySide6")
        if package_version(name) is not None
    }
    warnings = []
    if any(name != "PyQt5" for name in qt_bindings):
        warnings.append(
            "Multiple Qt bindings are installed. EasySatSim explicitly uses PyQt5; "
            "mixed bindings can cause backend or plugin conflicts."
        )
    loaded_foreign = [
        name for name in sys.modules
        if name.startswith(("PyQt6", "PySide2", "PySide6"))
    ]
    if loaded_foreign:
        raise RuntimeError(f"A non-PyQt5 Qt binding is already loaded: {loaded_foreign[0]}")
    return {
        "summary": "Core runtime and visualization packages import successfully with PyQt5.",
        "versions": versions,
        "qt_bindings_installed": qt_bindings,
        "qt_runtime_version": QT_VERSION_STR,
        "pyqt_runtime_version": PYQT_VERSION_STR,
        "qt_plugins_path": str(plugins_path),
        "qt_platform_plugins_path": str(platform_plugins_path),
        "qt_platform_plugins": platform_plugins,
        "expected_qt_platform_plugin": expected_plugin,
        "warnings": warnings,
    }


if __name__ == "__main__":
    run_step(1, check)
