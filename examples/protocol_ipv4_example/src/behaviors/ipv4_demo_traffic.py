"""Deterministic access and one-shot IPv4/UDP traffic for Step 8."""

from collections import deque

from configuration import simulation_config as cg
from src.abstract.behavior.behavior import AbstractBehavior
from src.simulation.behavior.user_active_behavior import UserActiveBehavior
from src.simulation.stack.cross_layer_message.cross_layer_message import (
    ActionType,
    CrossLayerMessage,
)
from src.simulation.stack.protocol_data.application_data import DataMessage
from src.simulation.stack.stack_func import StackFunc
from src.simulation.variable.performance import NetworkPerformance
from src.simulation.variable.virtual_store import VirtualStore


class IPv4DemoTraffic(AbstractBehavior):
    """Attach fixed endpoints and send exactly one recognizable datagram."""

    @staticmethod
    async def establish_deterministic_access(entity, data):
        satellites = data
        if entity.access_satellite is not None:
            return

        covered_satellite_ids, _ = UserActiveBehavior._find_satellites_in_los(
            entity=entity,
            data=None,
        )
        if covered_satellite_ids.size == 0:
            return

        satellite_id = int(covered_satellite_ids[0])
        expected_satellite_id = _expected_access_satellite_id(entity.entity_id)
        if satellite_id != expected_satellite_id:
            raise RuntimeError(
                f"User {entity.entity_id} selected access satellite {satellite_id}; "
                f"expected {expected_satellite_id}."
            )

        satellite = satellites[satellite_id]
        satellite_ip, satellite_mac, satellite_buffers = (
            VirtualStore.get_satellite_info_from_id(satellite_id=satellite_id)
        )
        entity.access_satellite = satellite_id
        entity.access_relationship[entity.entity_id] = satellite_id
        entity.access_update_tables(
            next_hop_ip=satellite_ip,
            mac=satellite_mac,
            buffer=satellite_buffers,
        )
        satellite.access_update_tables(
            ip=entity.ip_address,
            mac=entity.mac_address,
            buffer=entity.buffers,
        )
        VirtualStore.user_access_table[entity.ip_address] = satellite_ip
        print(
            f"[IPv4 Example] User {entity.entity_id} attached to satellite "
            f"{satellite_id}."
        )

    @staticmethod
    async def send_once(entity, data):
        if entity.entity_id != cg.IPV4_EXAMPLE_SOURCE_USER_ID:
            return
        if getattr(entity, "_ipv4_example_packet_sent", False):
            return
        if float(entity.current_time[0]) < cg.IPV4_EXAMPLE_TRAFFIC_START_TIME:
            return
        if entity.access_satellite is None:
            return

        destination_ip = VirtualStore.user_id_to_ip_table.get(
            cg.IPV4_EXAMPLE_DESTINATION_USER_ID
        )
        if destination_ip not in VirtualStore.user_access_table:
            return

        entity._ipv4_example_packet_sent = True
        next_hop_ip = VirtualStore.satellite_id_to_ip_table[entity.access_satellite]
        data_others = {
            "source_port": cg.IPV4_EXAMPLE_APPLICATION_PORT,
            "target_port": cg.IPV4_EXAMPLE_APPLICATION_PORT,
            "source_ip": entity.ip_address,
            "target_ip": destination_ip,
            "next_hop_ip": next_hop_ip,
            "data_size_byte": cg.IPV4_EXAMPLE_PACKET_SIZE_BYTE,
            "delay": 0.0,
            "path": None,
            "ip_list": None,
            "message_id": cg.IPV4_EXAMPLE_MESSAGE_ID,
            "source_user_id": cg.IPV4_EXAMPLE_SOURCE_USER_ID,
            "destination_user_id": cg.IPV4_EXAMPLE_DESTINATION_USER_ID,
            "source_access_satellite_id": entity.access_satellite,
            "ipv4_initial_ttl": cg.IPV4_EXAMPLE_INITIAL_TTL,
            "ipv4_identification": cg.IPV4_EXAMPLE_IDENTIFICATION,
        }
        cross_layer_message = CrossLayerMessage(
            action=ActionType.ENCAPSULATE,
            cross_layer_interface=cg.IPV4_EXAMPLE_APPLICATION_PORT,
            data=DataMessage(message=cg.IPV4_EXAMPLE_PAYLOAD),
            data_others=data_others,
        )
        cross_layer_message = StackFunc.encapsulate_message_to_signal(
            entity=entity,
            cross_layer_message=cross_layer_message,
        )
        if cross_layer_message is None:
            raise RuntimeError("The deterministic IPv4/UDP packet was dropped at source.")

        cross_layer_message.data_others["path"] = deque([entity.position_3D])
        cross_layer_message.data_others["ip_list"] = deque([entity.ip_address])
        await entity.mac_table["*"]["Default"].put(cross_layer_message)
        NetworkPerformance.packet_generate(
            data_size_byte=cg.IPV4_EXAMPLE_PACKET_SIZE_BYTE
        )
        print(
            "[IPv4 Example] Sent "
            f"message_id={cg.IPV4_EXAMPLE_MESSAGE_ID}, "
            f"payload={cg.IPV4_EXAMPLE_PAYLOAD}, "
            f"ttl={cg.IPV4_EXAMPLE_INITIAL_TTL}."
        )


def _expected_access_satellite_id(user_id):
    if user_id == cg.IPV4_EXAMPLE_SOURCE_USER_ID:
        return cg.IPV4_EXAMPLE_EXPECTED_SOURCE_ACCESS_SATELLITE_ID
    if user_id == cg.IPV4_EXAMPLE_DESTINATION_USER_ID:
        return cg.IPV4_EXAMPLE_EXPECTED_DESTINATION_ACCESS_SATELLITE_ID
    raise ValueError(f"Unexpected IPv4 example user id: {user_id}")
