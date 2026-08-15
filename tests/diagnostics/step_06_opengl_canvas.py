from tests.diagnostics.common import (
    artifact_path,
    create_qapplication,
    mode,
    process_events,
    run_step,
    skip_step,
)


def readable_gl_value(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value) if value is not None else None


def check():
    import numpy as np
    import vispy

    vispy.use(app="pyqt5")
    from vispy import gloo, scene

    app = create_qapplication()
    qt_platform = app.platformName()
    if mode() == "live" and qt_platform.lower() in {"offscreen", "minimal"}:
        raise RuntimeError(
            f"Live diagnostics require a desktop Qt platform; loaded {qt_platform!r}."
        )
    canvas = scene.SceneCanvas(keys=None, show=True, size=(640, 360), bgcolor="#F8FAFC")
    view = canvas.central_widget.add_view()
    view.camera = "panzoom"
    scene.visuals.Line(
        pos=np.array([[-0.8, -0.5], [0.0, 0.8], [0.8, -0.2]], dtype=np.float32),
        color="#2563EB",
        width=4,
        parent=view.scene,
    )
    view.camera.set_range(x=(-1, 1), y=(-1, 1), margin=0.1)
    process_events(app, 500)

    context = canvas.context
    info = {}
    try:
        for key, gl_name in (
            ("vendor", "GL_VENDOR"),
            ("renderer", "GL_RENDERER"),
            ("version", "GL_VERSION"),
            ("glsl", "GL_SHADING_LANGUAGE_VERSION"),
        ):
            try:
                info[key] = readable_gl_value(
                    gloo.gl.glGetParameter(getattr(gloo.gl, gl_name))
                )
            except Exception as exc:
                info[key] = f"unavailable: {exc}"
        image = canvas.render(alpha=False)
    except Exception as exc:
        canvas.close()
        if mode() == "offscreen":
            skip_step(
                6,
                "The Qt offscreen platform does not provide an OpenGL context; run Step 6 in live mode.",
                {"offscreen_error": str(exc), "open_gl": info},
            )
        raise
    canvas.close()
    if image is None or image.size == 0:
        raise RuntimeError("VisPy canvas returned no rendered pixels.")
    variation = float(np.std(image.astype(np.float64)))
    if variation <= 0:
        raise RuntimeError("VisPy canvas rendered a uniform image; OpenGL drawing may have failed.")
    from PIL import Image

    screenshot = artifact_path("step_06_opengl_canvas.png")
    Image.fromarray(image).save(screenshot)
    if not screenshot.is_file() or screenshot.stat().st_size <= 0:
        raise RuntimeError("The OpenGL render evidence image was not written.")
    screen = app.primaryScreen()
    screen_details = None
    if screen is not None:
        geometry = screen.geometry()
        screen_details = {
            "name": screen.name(),
            "size": [geometry.width(), geometry.height()],
            "device_pixel_ratio": screen.devicePixelRatio(),
            "logical_dpi": screen.logicalDotsPerInch(),
        }
    return {
        "summary": "VisPy created an OpenGL canvas and rendered non-uniform pixels.",
        "mode": mode(),
        "qt_platform": qt_platform,
        "primary_screen": screen_details,
        "image_shape": list(image.shape),
        "pixel_standard_deviation": variation,
        "render_evidence": str(screenshot),
        "open_gl": info,
        "context": str(context),
    }


if __name__ == "__main__":
    run_step(6, check)
