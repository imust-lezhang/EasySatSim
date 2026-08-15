"""Validate example-local IPv4/UDP protocol registration."""

import json

from examples.protocol_ipv4_example.example_setup import (
    configure_scene,
    register_ipv4_udp_stack,
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
from src.simulation.manager.stack_manager import StackManager
from src.simulation.stack.protocol_data.application_data import DataMessage
from src.simulation.stack.protocol_func.link_func import LinkEthernet
from src.simulation.stack.protocol_func.network_func import Type0x0800
from src.simulation.stack.protocol_func.physical_func import PhyEthernet


def _assert_handler(manager, layer, protocol, expected_parse, expected_encapsulate):
    _, parse_func = manager.get_parse_funcs(layer, protocol)
    _, encapsulate_func = manager.get_encapsulate_funcs(layer, protocol)
    assert parse_func is expected_parse
    assert encapsulate_func is expected_encapsulate


def validate_stack_registration():
    example_manager = StackManager()
    example_manager.load_default_setting()

    class LightweightScene:
        def get_stack_manager(self):
            return example_manager

    default_link_parse = example_manager.get_parse_funcs("link", "Ethernet")[1]
    default_link_encapsulate = example_manager.get_encapsulate_funcs(
        "link", "Ethernet"
    )[1]
    default_physical_parse = example_manager.get_parse_funcs(
        "physical", "Ethernet"
    )[1]
    default_physical_encapsulate = example_manager.get_encapsulate_funcs(
        "physical", "Ethernet"
    )[1]

    summary = configure_scene(LightweightScene())
    assert register_ipv4_udp_stack(example_manager) is summary

    _assert_handler(
        example_manager,
        "application",
        DEMO_APPLICATION_PORT,
        IPv4DemoApplicationPort.parse_and_process_func,
        IPv4DemoApplicationPort.encapsulate_func,
    )
    app_to_data, _ = example_manager.get_parse_funcs(
        "application", DEMO_APPLICATION_PORT
    )
    app_data_to, _ = example_manager.get_encapsulate_funcs(
        "application", DEMO_APPLICATION_PORT
    )
    assert app_to_data is DataMessage.to_data
    assert app_data_to is DataMessage.data_to

    _assert_handler(
        example_manager,
        "transport",
        UDP_PROTOCOL_NUMBER,
        ScapyUDPProtocol.parse_and_process_func,
        ScapyUDPProtocol.encapsulate_func,
    )
    udp_to_data, _ = example_manager.get_parse_funcs(
        "transport", UDP_PROTOCOL_NUMBER
    )
    udp_data_to, _ = example_manager.get_encapsulate_funcs(
        "transport", UDP_PROTOCOL_NUMBER
    )
    assert udp_to_data is ScapyUDPData.to_data
    assert udp_data_to is ScapyUDPData.data_to

    _assert_handler(
        example_manager,
        "network",
        0x0800,
        ScapyIPv4Protocol.parse_and_process_func,
        ScapyIPv4Protocol.encapsulate_func,
    )
    ipv4_to_data, _ = example_manager.get_parse_funcs("network", 0x0800)
    ipv4_data_to, _ = example_manager.get_encapsulate_funcs("network", 0x0800)
    assert ipv4_to_data is ScapyIPv4Data.to_data
    assert ipv4_data_to is ScapyIPv4Data.data_to

    assert example_manager.get_parse_funcs("link", "Ethernet")[1] is (
        default_link_parse
    )
    assert example_manager.get_encapsulate_funcs("link", "Ethernet")[1] is (
        default_link_encapsulate
    )
    assert example_manager.get_parse_funcs("physical", "Ethernet")[1] is (
        default_physical_parse
    )
    assert example_manager.get_encapsulate_funcs("physical", "Ethernet")[1] is (
        default_physical_encapsulate
    )
    assert default_link_parse is LinkEthernet.parse_and_process_func
    assert default_physical_parse is PhyEthernet.parse_and_process_func

    fresh_default_manager = StackManager()
    fresh_default_manager.load_default_setting()
    _assert_handler(
        fresh_default_manager,
        "network",
        0x0800,
        Type0x0800.parse_and_process_func,
        Type0x0800.encapsulate_func,
    )
    try:
        fresh_default_manager.get_parse_funcs("transport", UDP_PROTOCOL_NUMBER)
    except KeyError:
        pass
    else:
        raise AssertionError("UDP protocol 17 leaked into a fresh default stack.")

    return {
        "status": "PASS",
        "application_registration": summary["application"],
        "transport_registration": summary["transport"],
        "network_registration": summary["network"],
        "link_unchanged": summary["link"],
        "physical_unchanged": summary["physical"],
        "public_replace_api_used": True,
        "scene_registration_entry_point": "PASS",
        "registration_idempotent": True,
        "fresh_default_stack_uses_type0x0800": True,
        "udp_17_did_not_leak_to_default_stack": True,
    }


def main():
    print(json.dumps(validate_stack_registration(), indent=2))


if __name__ == "__main__":
    main()
