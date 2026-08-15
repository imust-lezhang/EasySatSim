from collections import deque

from configuration import simulation_config as cg
from cases.case3.experiment.data.user_groups import get_pair_for_user
from cases.case3.experiment.integration.event_logger import append_event
from src.abstract.behavior.behavior import AbstractBehavior
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage, ActionType
from src.simulation.stack.protocol_data.application_data import DataMessage
from src.simulation.stack.stack_func import StackFunc
from src.simulation.variable.performance import NetworkPerformance
from src.simulation.variable.virtual_store import VirtualStore


class ControlledPairTraffic(AbstractBehavior):
    @staticmethod
    async def send_case3_pair_data(entity, data):
        pair_info = get_pair_for_user(entity.entity_id)
        if pair_info is None:
            return

        current_time = float(entity.current_time[0])
        state = _get_or_create_state(entity)
        if current_time < state["next_send_time"]:
            return

        state["next_send_time"] += cg.CASE3_CONTROLLED_SEND_PERIOD
        if entity.access_satellite is None:
            return

        target_user_id = pair_info["target_user_id"]
        target_ip = VirtualStore.user_id_to_ip_table.get(target_user_id)
        if target_ip is None:
            return

        if "*" not in entity.mac_table:
            return

        message_id = _build_message_id(
            source_user_id=entity.entity_id,
            target_user_id=target_user_id,
            sequence_number=state["sequence_number"],
        )
        state["sequence_number"] += 1
        payload = _build_payload(
            message_id=message_id,
            pair_id=pair_info["pair_id"],
            direction=pair_info["direction"],
            source_user_id=entity.entity_id,
            target_user_id=target_user_id,
        )

        next_hop_ip = VirtualStore.satellite_id_to_ip_table[entity.access_satellite]
        data_message = DataMessage(message=payload)
        data_others = {
            "source_port": cg.CASE3_APPLICATION_PORT,
            "target_port": cg.CASE3_APPLICATION_PORT,
            "source_ip": entity.ip_address,
            "target_ip": target_ip,
            "next_hop_ip": next_hop_ip,
            "data_size_byte": cg.CASE3_CONTROLLED_PACKET_SIZE_BYTE,
            "delay": 0,
            "path": None,
            "ip_list": None,
        }
        cross_layer_message = CrossLayerMessage(
            action=ActionType.ENCAPSULATE,
            cross_layer_interface=cg.CASE3_APPLICATION_PORT,
            data=data_message,
            data_others=data_others,
        )
        cross_layer_message = StackFunc.encapsulate_message_to_signal(
            entity=entity,
            cross_layer_message=cross_layer_message,
        )
        if cross_layer_message is None:
            return

        cross_layer_message.data_others["path"] = deque()
        cross_layer_message.data_others["path"].append(entity.position_3D)
        cross_layer_message.data_others["ip_list"] = deque()
        cross_layer_message.data_others["ip_list"].append(entity.ip_address)

        await entity.mac_table["*"]["Default"].put(cross_layer_message)
        NetworkPerformance.packet_generate(data_size_byte=cg.CASE3_CONTROLLED_PACKET_SIZE_BYTE)
        append_event(
            path=cg.CASE3_EVENT_LOG_FILE_PATH,
            event_type="generate",
            simulation_time=current_time,
            message_id=message_id,
            pair_id=pair_info["pair_id"],
            direction=pair_info["direction"],
            source_user_id=entity.entity_id,
            target_user_id=target_user_id,
            source_access_satellite_id=entity.access_satellite,
            target_access_satellite_id=_get_target_access_satellite_id(target_ip),
        )


def _get_or_create_state(entity):
    state = getattr(entity, "_case3_controlled_flow_state", None)
    if state is None:
        slot_count = max(1, cg.CASE3_CONTROLLED_STAGGER_SLOT_COUNT)
        offset = (
            entity.entity_id % slot_count
        ) * cg.CASE3_CONTROLLED_SEND_PERIOD / slot_count
        state = {
            "next_send_time": cg.CASE3_TRAFFIC_START_TIME + offset,
            "sequence_number": 0,
        }
        entity._case3_controlled_flow_state = state
    return state


def _get_target_access_satellite_id(target_ip):
    satellite_ip = VirtualStore.user_access_table.get(target_ip)
    if satellite_ip is None:
        return None
    return VirtualStore.satellite_ip_to_id_table.get(satellite_ip)


def _build_message_id(source_user_id, target_user_id, sequence_number):
    return f"case3-{source_user_id}-{target_user_id}-{sequence_number}"


def _build_payload(message_id, pair_id, direction, source_user_id, target_user_id):
    payload = (
        f"case3|{message_id}|{pair_id}|{direction}|"
        f"{source_user_id}|{target_user_id}"
    )
    if len(payload) >= cg.CASE3_MESSAGE_CHAR_COUNT:
        return payload
    return payload + "|" + ("x" * (cg.CASE3_MESSAGE_CHAR_COUNT - len(payload)))
