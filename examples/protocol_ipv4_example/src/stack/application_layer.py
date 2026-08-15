"""Application endpoint for the standards-formatted IPv4/UDP example."""

import json
from pathlib import Path

from configuration import simulation_config as cg
from src.abstract.stack.protocol_func import AbstractProtocolFunc
from src.simulation.stack.cross_layer_message.cross_layer_message import (
    ActionType,
    CrossLayerMessage,
)
from src.simulation.stack.protocol_data.application_data import DataMessage
from src.simulation.variable.performance import NetworkPerformance
from src.simulation.variable.virtual_store import VirtualStore


DEMO_APPLICATION_PORT = 18080
UDP_PROTOCOL_NUMBER = 17


class IPv4DemoApplicationPort(AbstractProtocolFunc):
    """Send and receive the recognizable payload used by the example."""

    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage):
        data_message = cross_layer_message.data
        if not isinstance(data_message, DataMessage):
            raise TypeError("IPv4DemoApplicationPort expects DataMessage while parsing.")

        forwarding_count = int(
            cross_layer_message.data_others.get("ipv4_forwarding_count", 0)
        )
        path_satellite_ids = _satellite_ids_from_ip_list(
            cross_layer_message.data_others.get("ip_list")
        )
        is_scenario_delivery = "message_id" in cross_layer_message.data_others
        if is_scenario_delivery:
            NetworkPerformance.packet_arrive(
                data_size_byte=cross_layer_message.data_others["data_size_byte"],
                total_delay=cross_layer_message.data_others["delay"],
                hop_count=forwarding_count,
            )
        result = {
            "status": "DELIVERED",
            "message_id": cross_layer_message.data_others.get("message_id"),
            "source_user_id": cross_layer_message.data_others.get("source_user_id"),
            "destination_user_id": getattr(entity, "entity_id", None),
            "source_access_satellite_id": cross_layer_message.data_others.get(
                "source_access_satellite_id"
            ),
            "destination_access_satellite_id": getattr(
                entity, "access_satellite", None
            ),
            "path_satellite_ids": path_satellite_ids,
            "forwarding_count": forwarding_count,
            "initial_ttl": cross_layer_message.data_others.get("ipv4_initial_ttl"),
            "final_ttl": cross_layer_message.data_others.get("ipv4_delivery_ttl"),
            "source_ip": cross_layer_message.data_others.get("ipv4_source_ip"),
            "destination_ip": cross_layer_message.data_others.get(
                "ipv4_destination_ip"
            ),
            "protocol": cross_layer_message.data_others.get("ipv4_protocol"),
            "source_port": cross_layer_message.data_others.get("udp_source_port"),
            "destination_port": cross_layer_message.data_others.get(
                "udp_destination_port"
            ),
            "payload": data_message.message,
            "delay_ms": cross_layer_message.data_others.get("delay"),
        }
        if is_scenario_delivery:
            _write_step8_delivery_result(result)
            print(
                "[IPv4 Example] Delivered "
                f"message_id={result['message_id']}, "
                f"satellite_path={path_satellite_ids}, "
                f"forwarding_count={forwarding_count}, "
                f"final_ttl={result['final_ttl']}."
            )

        cross_layer_message.action = ActionType.STOP
        return cross_layer_message

    @staticmethod
    def encapsulate_func(entity, cross_layer_message: CrossLayerMessage):
        if not isinstance(cross_layer_message.data, DataMessage):
            raise TypeError(
                "IPv4DemoApplicationPort expects DataMessage while encapsulating."
            )
        cross_layer_message.cross_layer_interface = UDP_PROTOCOL_NUMBER
        cross_layer_message.action = ActionType.ENCAPSULATE
        return cross_layer_message


def _satellite_ids_from_ip_list(ip_list):
    if ip_list is None:
        return []
    return [
        VirtualStore.satellite_ip_to_id_table[ip_address]
        for ip_address in ip_list
        if ip_address in VirtualStore.satellite_ip_to_id_table
    ]


def _write_step8_delivery_result(result):
    output_path = Path(cg.IPV4_EXAMPLE_RESULT_FILE_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_path.replace(output_path)
