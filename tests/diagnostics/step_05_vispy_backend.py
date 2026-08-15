from tests.diagnostics.common import create_qapplication, run_step


def check():
    import vispy

    vispy.use(app="pyqt5")
    create_qapplication()
    from vispy import app

    application = app.use_app("pyqt5")
    backend_name = getattr(application, "backend_name", "")
    if "qt" not in backend_name.lower() and "pyqt5" not in backend_name.lower():
        raise RuntimeError(f"Unexpected VisPy backend: {backend_name}")
    return {
        "summary": "VisPy is explicitly bound to the PyQt5 backend.",
        "vispy_version": vispy.__version__,
        "backend_name": backend_name,
        "backend_module": getattr(application, "backend_module", None).__name__,
    }


if __name__ == "__main__":
    run_step(5, check)
