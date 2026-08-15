import importlib
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_CONFIG_ROOT = "EASYSATSIM_CONFIG_ROOT"
CONFIG_PACKAGE = "configuration"
CONFIG_MODULE = "configuration.simulation_config"

_active_config_root = None


def resolve_config_root(config_root=None):
    if config_root is None:
        config_root = os.environ.get(ENV_CONFIG_ROOT) or PROJECT_ROOT

    path = Path(config_root).expanduser()
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    else:
        path = path.resolve()

    if path.is_file():
        if path.name != "simulation_config.py":
            raise ValueError(f"Config file must be named simulation_config.py: {path}")
        if path.parent.name != CONFIG_PACKAGE:
            raise ValueError(f"Config file must be inside a '{CONFIG_PACKAGE}' folder: {path}")
        config_root = path.parent.parent
    elif (path / "simulation_config.py").is_file():
        if path.name != CONFIG_PACKAGE:
            raise ValueError(f"Config folder must be named '{CONFIG_PACKAGE}': {path}")
        config_root = path.parent
    elif (path / CONFIG_PACKAGE / "simulation_config.py").is_file():
        config_root = path
    else:
        raise FileNotFoundError(
            f"Cannot find {CONFIG_PACKAGE}/simulation_config.py under: {path}"
        )

    return config_root.resolve()


def get_active_config_root():
    if _active_config_root is not None:
        return _active_config_root
    return resolve_config_root(None)


def get_config_path(config_root=None):
    return resolve_config_root(config_root) / CONFIG_PACKAGE / "simulation_config.py"


def get_default_config_path(config_root=None):
    config_root = resolve_config_root(config_root)
    local_default_path = config_root / CONFIG_PACKAGE / "simulation_config.default.py"
    if local_default_path.exists():
        return local_default_path
    return None


def load_configuration(config_root=None):
    config_root = resolve_config_root(config_root)
    _activate_import_path(config_root)
    os.environ[ENV_CONFIG_ROOT] = str(config_root)

    config_path = get_config_path(config_root)
    _retarget_configuration_package(config_root)
    module = _load_config_module(config_path)

    global _active_config_root
    _active_config_root = config_root
    return module


def _activate_import_path(config_root):
    project_root = PROJECT_ROOT.resolve()
    config_root = config_root.resolve()
    _remove_sys_path(config_root)
    _remove_sys_path(project_root)
    if config_root != project_root:
        sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(config_root))
    return


def _remove_sys_path(target_path):
    for item in list(sys.path):
        try:
            current_path = Path(item).resolve()
        except (TypeError, ValueError, OSError):
            continue
        if current_path == target_path:
            sys.path.remove(item)
    return


def _retarget_configuration_package(config_root):
    package = sys.modules.get(CONFIG_PACKAGE)
    if package is None:
        return

    config_dir = config_root / CONFIG_PACKAGE
    init_path = config_dir / "__init__.py"
    package.__file__ = str(init_path) if init_path.exists() else None
    package.__path__ = [str(config_dir)]
    return


def _load_config_module(config_path):
    importlib.invalidate_caches()
    module = sys.modules.get(CONFIG_MODULE)
    if module is None:
        return importlib.import_module(CONFIG_MODULE)

    module_dict = module.__dict__
    for name in list(module_dict):
        if name.isupper():
            del module_dict[name]

    module_dict["__file__"] = str(config_path)
    module_dict["__package__"] = CONFIG_PACKAGE
    module_dict["__name__"] = CONFIG_MODULE
    module_dict["__cached__"] = None

    text = config_path.read_text(encoding="utf-8")
    code = compile(text, str(config_path), "exec")
    exec(code, module_dict)
    return module
