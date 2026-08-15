import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.config_loader import load_configuration
load_configuration("cases/case1/src")
from configuration import simulation_config as cg
from cases.case1.case_setup import configure_case1_scene
from src.simulation.controller.scene_controller import SceneController


def main():
    sc = SceneController()
    sc.create_scene()
    sc.default_behavior()
    sc.default_stack()
    configure_case1_scene(sc)
    sc.configuration_complete()
    sc.run_simulation(plotter=True, running_time=cg.CASE_RUNNING_TIME_REAL_SECONDS)


if __name__ == "__main__":
    main()
