"""Example-local protocol registration for the Scapy IPv4/UDP workflow."""

from configuration import simulation_config as cg
from examples.protocol_ipv4_example.src.behaviors.ipv4_demo_traffic import (
    IPv4DemoTraffic,
)
from examples.protocol_ipv4_example.src.stack.application_layer import (
    DEMO_APPLICATION_PORT,
    IPv4DemoApplicationPort,
)
from examples.protocol_ipv4_example.src.stack.scapy_ipv4_data import ScapyIPv4Data
from examples.protocol_ipv4_example.src.stack.scapy_ipv4_protocol import (
    ScapyIPv4Protocol,
)
from examples.protocol_ipv4_example.src.stack.scapy_udp_data import ScapyUDPData
from examples.protocol_ipv4_example.src.stack.scapy_udp_protocol import (
    UDP_PROTOCOL_NUMBER,
    ScapyUDPProtocol,
)
from src.simulation.stack.protocol_data.application_data import DataMessage
from src.abstract.manager.entity_manager import AbstractEntityManager


IPV4_ETHERTYPE = 0x0800
APPLICATION_DATA_NAME = "data_message"
UDP_DATA_NAME = "scapy_udp_data"
IPV4_DATA_NAME = "scapy_ipv4_data"
REGISTRATION_FLAG = "_protocol_ipv4_example_stack_registered"
REGISTRATION_SUMMARY_ATTR = "_protocol_ipv4_example_registration_summary"
ACCESS_BEHAVIOR_NAME = "ipv4_example_deterministic_access"
TRAFFIC_BEHAVIOR_NAME = "ipv4_example_send_once"


def configure_scene(scene_controller):
    """Install the example stack into one already initialized scene."""
    summary = register_ipv4_udp_stack(scene_controller.get_stack_manager())
    if hasattr(scene_controller, "get_entity_manager") and hasattr(
        scene_controller, "get_behavior_manager"
    ):
        configure_deterministic_multihop_scenario(scene_controller)
    return summary
def register_ipv4_udp_stack(stack_manager):
    """Register application/UDP and replace IPv4 only in this manager instance."""
    if getattr(stack_manager, REGISTRATION_FLAG, False):
        return getattr(stack_manager, REGISTRATION_SUMMARY_ATTR)

    stack_manager.add_protocol_func(
        layer_name="application",
        protocol_name=DEMO_APPLICATION_PORT,
        parse_func=IPv4DemoApplicationPort.parse_and_process_func,
        encapsulate_func=IPv4DemoApplicationPort.encapsulate_func,
    )
    stack_manager.add_relationship(
        layer_name="application",
        protocol_name=DEMO_APPLICATION_PORT,
        data_name=APPLICATION_DATA_NAME,
    )

    stack_manager.add_protocol_data(
        layer_name="transport",
        data_name=UDP_DATA_NAME,
        data_type=ScapyUDPData,
        to_data_func=ScapyUDPData.to_data,
        data_to_func=ScapyUDPData.data_to,
    )
    stack_manager.add_protocol_func(
        layer_name="transport",
        protocol_name=UDP_PROTOCOL_NUMBER,
        parse_func=ScapyUDPProtocol.parse_and_process_func,
        encapsulate_func=ScapyUDPProtocol.encapsulate_func,
    )
    stack_manager.add_relationship(
        layer_name="transport",
        protocol_name=UDP_PROTOCOL_NUMBER,
        data_name=UDP_DATA_NAME,
    )

    stack_manager.add_protocol_data(
        layer_name="network",
        data_name=IPV4_DATA_NAME,
        data_type=ScapyIPv4Data,
        to_data_func=ScapyIPv4Data.to_data,
        data_to_func=ScapyIPv4Data.data_to,
    )
    stack_manager.replace_protocol_func(
        layer_name="network",
        protocol_name=IPV4_ETHERTYPE,
        parse_func=ScapyIPv4Protocol.parse_and_process_func,
        encapsulate_func=ScapyIPv4Protocol.encapsulate_func,
    )
    stack_manager.replace_relationship(
        layer_name="network",
        protocol_name=IPV4_ETHERTYPE,
        data_name=IPV4_DATA_NAME,
    )

    summary = build_registration_summary()
    setattr(stack_manager, REGISTRATION_FLAG, True)
    setattr(stack_manager, REGISTRATION_SUMMARY_ATTR, summary)
    print_registration_summary(summary)
    return summary


def configure_deterministic_multihop_scenario(scene_controller):
    """Replace random traffic/access signaling with the fixed Step 8 flow."""
    entity_manager = scene_controller.get_entity_manager()
    behavior_manager = scene_controller.get_behavior_manager()
    users = entity_manager.get_entity(entity_category="user")
    satellites = entity_manager.get_entity(entity_category="satellite")

    if len(users) != 2:
        raise ValueError(f"The IPv4 example requires 2 users, found {len(users)}.")
    _assert_fixed_user_positions(users)

    behavior_manager.add_active_behavior(
        behavior_name=ACCESS_BEHAVIOR_NAME,
        behavior_func=IPv4DemoTraffic.establish_deterministic_access,
        interval=cg.IPV4_EXAMPLE_BEHAVIOR_INTERVAL,
        is_async=True,
        data=satellites,
        last_run=None,
    )
    behavior_manager.add_active_behavior(
        behavior_name=TRAFFIC_BEHAVIOR_NAME,
        behavior_func=IPv4DemoTraffic.send_once,
        interval=cg.IPV4_EXAMPLE_BEHAVIOR_INTERVAL,
        is_async=True,
        data=None,
        last_run=None,
    )

    for user in users:
        user.get_active_behaviors().pop("simple_access_satellite", None)
        user.get_active_behaviors().pop("simple_send_data", None)
        AbstractEntityManager.bind_active_behavior(
            behavior_manager=behavior_manager,
            entity=user,
            behavior_name=ACCESS_BEHAVIOR_NAME,
        )
        AbstractEntityManager.bind_active_behavior(
            behavior_manager=behavior_manager,
            entity=user,
            behavior_name=TRAFFIC_BEHAVIOR_NAME,
        )

    print(
        "[IPv4 Example] Deterministic scene: users=2, satellites="
        f"{len(satellites)}, source=0, destination=1, random_traffic=off, "
        "failures=off."
    )


def _assert_fixed_user_positions(users):
    expected_positions = (
        cg.IPV4_EXAMPLE_SOURCE_POSITION,
        cg.IPV4_EXAMPLE_DESTINATION_POSITION,
    )
    for user, expected in zip(users, expected_positions):
        observed = tuple(float(value) for value in user.position_2D[:2])
        if any(abs(a - b) > 1e-6 for a, b in zip(observed, expected)):
            raise ValueError(
                f"User {user.entity_id} position is {observed}; expected {expected}."
            )


def build_registration_summary():
    return {
        "application": f"demo port {DEMO_APPLICATION_PORT}",
        "transport": f"UDP / protocol {UDP_PROTOCOL_NUMBER}",
        "network": f"IPv4 / 0x{IPV4_ETHERTYPE:04x}",
        "link": "existing EasySatSim link layer",
        "physical": "existing EasySatSim physical layer",
    }


def print_registration_summary(summary):
    print("[IPv4 Example] Protocol registration summary:")
    for layer_name in ("application", "transport", "network", "link", "physical"):
        print(f"  {layer_name}: {summary[layer_name]}")
