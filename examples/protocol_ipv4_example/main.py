"""Run the deterministic Scapy IPv4/UDP multi-hop example."""

import random
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.config_loader import load_configuration

load_configuration("examples/protocol_ipv4_example/src")

from configuration import simulation_config as cg
from examples.protocol_ipv4_example.example_setup import configure_scene
from examples.protocol_ipv4_example.experiment.evaluation.validate_ipv4_example import (
    validate_ipv4_example,
)
from examples.protocol_ipv4_example.experiment.integration.ipv4_trace_logger import (
    prepare_ipv4_trace,
)
from examples.protocol_ipv4_example.experiment.integration.pcap_writer import (
    prepare_ipv4_pcaps,
)
from src.simulation.controller.scene_controller import SceneController


def main():
    from src.simulation.visualization.simulation_control_window import (
        cleanup_stale_shared_memory,
    )

    cleanup_stale_shared_memory()
    random.seed(8001)
    np.random.seed(8001)
    _prepare_output_artifacts()

    scene_controller = None
    try:
        scene_controller = SceneController(
            test_mode=True,
            user1_latitude=cg.IPV4_EXAMPLE_SOURCE_POSITION[0],
            user1_longtitude=cg.IPV4_EXAMPLE_SOURCE_POSITION[1],
            user2_latitude=cg.IPV4_EXAMPLE_DESTINATION_POSITION[0],
            user2_longtitude=cg.IPV4_EXAMPLE_DESTINATION_POSITION[1],
        )
        scene_controller.create_scene()
        scene_controller.default_behavior()
        scene_controller.default_stack()
        configure_scene(scene_controller)
        scene_controller.configuration_complete()
        scene_controller.run_simulation(
            plotter=False,
            running_time=cg.IPV4_EXAMPLE_RUNNING_TIME_REAL_SECONDS,
            output=False,
        )
        validation_summary = validate_ipv4_example()
        if validation_summary["status"] != "PASS":
            raise RuntimeError(
                "IPv4 example validation failed: "
                + ", ".join(validation_summary["failed_assertions"])
            )
        ttl_result = validation_summary["assertions"][
            "ttl_matches_forwarding_count"
        ]["observed"]
        print(
            "[IPv4 Example] PASS: "
            f"{validation_summary['passed_assertion_count']}/"
            f"{validation_summary['assertion_count']} required assertions "
            "passed; "
            f"initial TTL {ttl_result['initial_ttl_source_pcap']}, "
            f"final TTL {ttl_result['final_ttl_destination_pcap']}, "
            f"forwarding events {ttl_result['forwarding_event_count']}."
        )
    finally:
        if scene_controller is not None:
            scene_controller.release_shared_memory()
        cleanup_stale_shared_memory()


def _prepare_output_artifacts():
    for path in (
        cg.IPV4_EXAMPLE_RESULT_FILE_PATH,
        cg.IPV4_EXAMPLE_VALIDATION_SUMMARY_PATH,
    ):
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.unlink(missing_ok=True)
        output_path.with_suffix(output_path.suffix + ".tmp").unlink(missing_ok=True)
    prepare_ipv4_trace(cg.IPV4_EXAMPLE_TRACE_FILE_PATH)
    prepare_ipv4_pcaps(
        cg.IPV4_EXAMPLE_SOURCE_PCAP_PATH,
        cg.IPV4_EXAMPLE_DESTINATION_PCAP_PATH,
    )


if __name__ == "__main__":
    main()
