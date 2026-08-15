import argparse
import os
import random
import sys
from datetime import datetime
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))


def _parse_arguments():
    parser = argparse.ArgumentParser(description="Run one EasySatSim Case 3 scenario.")
    parser.add_argument(
        "--routing-mode",
        choices=("centralized", "distributed"),
        help="Override CASE3_ROUTING_MODE for this process only.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Override CASE3_RANDOM_SEED for this process only.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without the interactive plotter; used by the batch runner.",
    )
    return parser.parse_known_args()[0]


ARGS = _parse_arguments()
if ARGS.routing_mode:
    os.environ["EASYSATSIM_CASE3_ROUTING_MODE"] = ARGS.routing_mode
if ARGS.seed is not None:
    os.environ["EASYSATSIM_CASE3_RANDOM_SEED"] = str(ARGS.seed)
os.environ.setdefault(
    "EASYSATSIM_CASE3_OUTPUT_TIMESTAMP",
    datetime.now().strftime("%Y%m%d_%H%M%S"),
)

from src.tools.config_loader import load_configuration
load_configuration("cases/case3/src")

from configuration import simulation_config as cg
from cases.case3.case_setup import configure_case3_scene
from cases.case3.experiment.integration.run_metadata import write_run_metadata
from src.simulation.controller.scene_controller import SceneController


def main():
    from src.simulation.visualization.simulation_control_window import cleanup_stale_shared_memory

    cleanup_stale_shared_memory()
    random.seed(cg.CASE3_RANDOM_SEED)
    np.random.seed(cg.CASE3_RANDOM_SEED)

    scene_controller = SceneController()
    scene_controller.create_scene()
    scene_controller.default_behavior()
    scene_controller.default_stack()
    configure_case3_scene(scene_controller)
    scene_controller.configuration_complete()
    scene_controller.run_simulation(
        plotter=not ARGS.headless,
        running_time=cg.CASE_RUNNING_TIME_REAL_SECONDS,
        output=not ARGS.headless,
    )
    metadata_path = write_run_metadata()
    print(f"[Case 3] Run completed: {cg.CASE3_ROUTING_MODE}")
    print(f"[Case 3] Metadata: {metadata_path}")
    scene_controller.release_shared_memory()
    cleanup_stale_shared_memory()


if __name__ == "__main__":
    main()
