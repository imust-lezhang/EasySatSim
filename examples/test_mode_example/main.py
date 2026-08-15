import os
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
project_root_text = str(PROJECT_ROOT)
while project_root_text in sys.path:
    sys.path.remove(project_root_text)
sys.path.insert(0, project_root_text)

EXAMPLE_ROOT = Path(__file__).resolve().parent
OUTPUT_ID_ENV = "EASYSATSIM_TEST_MODE_OUTPUT_ID"
os.environ.setdefault(
    OUTPUT_ID_ENV,
    datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
)

from src.tools.config_loader import load_configuration


# Windows starts simulation workers with the spawn method. Loading the local
# configuration at module import time ensures every worker reconstructs the
# same satellite and user dimensions before it imports simulation modules.
load_configuration(EXAMPLE_ROOT / "src")


def main():
    # Import after the module-level configuration bootstrap so every simulation
    # component uses the dedicated two-user settings.
    from src.simulation.controller.scene_controller import SceneController

    scene_controller = SceneController(
        test_mode=True,
        user1_latitude=39.916668,
        user1_longtitude=116.383331,
        user2_latitude=35.652832,
        user2_longtitude=139.839478,
        direct_connection_mode=False,
    )
    scene_controller.create_scene()
    scene_controller.default_behavior()
    scene_controller.default_stack()
    scene_controller.configuration_complete()
    scene_controller.run_simulation(plotter=True)


if __name__ == "__main__":
    main()
