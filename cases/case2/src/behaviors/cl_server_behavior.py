from collections import deque

from src.abstract.behavior.behavior import AbstractBehavior
from src.simulation.behavior.user_active_behavior import UserActiveBehavior
from src.simulation.stack.protocol_data.application_data import AccessActionType
from src.simulation.stack.protocol_data.application_data import AccessMessage
from src.simulation.stack.cross_layer_message.cross_layer_message import ActionType
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage
from src.simulation.stack.stack_func import StackFunc
from src.simulation.variable.virtual_store import VirtualStore


class ClServerBehavior(AbstractBehavior):
    @staticmethod
    async def access_satellite(entity, data):
        covered_satellite_ids, _ = UserActiveBehavior._find_satellites_in_los(
            entity=entity,
            data=None,
        )
        satellite_id = select_first_available_satellite(covered_satellite_ids)
        if satellite_id is None:
            await disconnect_server_from_satellite(entity=entity)
            return

        if satellite_id == entity.access_satellite:
            return

        if entity.access_satellite is not None:
            await notify_server_quit_current_satellite(entity=entity)

        entity.access_satellite = satellite_id
        satellite_ip, satellite_mac, satellite_buffers = (
            VirtualStore.get_satellite_info_from_id(satellite_id=satellite_id)
        )
        entity.access_update_tables(
            next_hop_ip=satellite_ip,
            mac=satellite_mac,
            buffer=satellite_buffers,
        )
        VirtualStore.user_access_table[entity.ip_address] = satellite_ip
        await send_server_access_message(
            entity=entity,
            satellite_ip=satellite_ip,
            satellite_buffer=satellite_buffers,
        )
        return

    @staticmethod
    def train_model(entity, data):
        trigger_sample_count = data["trigger_sample_count"]
        entity.train_cl_round_if_ready(
            trigger_sample_count=trigger_sample_count,
        )
        return


def select_first_available_satellite(covered_satellite_ids):
    for satellite_id in covered_satellite_ids:
        satellite_id = int(satellite_id)
        if VirtualStore.satellite_survival_state[satellite_id]:
            return satellite_id
    return None


async def disconnect_server_from_satellite(entity):
    if entity.access_satellite is None:
        return

    await notify_server_quit_current_satellite(entity=entity)
    entity.access_satellite = None
    entity.access_remove_tables()
    if entity.ip_address in VirtualStore.user_access_table:
        del VirtualStore.user_access_table[entity.ip_address]
    return


async def notify_server_quit_current_satellite(entity):
    satellite_ip, _, satellite_buffers = VirtualStore.get_satellite_info_from_id(
        satellite_id=entity.access_satellite,
    )
    await send_server_quit_message(
        entity=entity,
        satellite_ip=satellite_ip,
        satellite_buffer=satellite_buffers,
    )
    return


async def send_server_access_message(entity, satellite_ip, satellite_buffer):
    await send_server_access_control_message(
        entity=entity,
        satellite_ip=satellite_ip,
        satellite_buffer=satellite_buffer,
        access_action=AccessActionType.ACCESS,
    )
    return


async def send_server_quit_message(entity, satellite_ip, satellite_buffer):
    await send_server_access_control_message(
        entity=entity,
        satellite_ip=satellite_ip,
        satellite_buffer=satellite_buffer,
        access_action=AccessActionType.QUIT,
    )
    return


async def send_server_access_control_message(entity, satellite_ip,
                                             satellite_buffer, access_action):
    message = AccessMessage(
        user_id=entity.entity_id,
        user_ip=entity.ip_address,
        user_mac=entity.mac_address,
        access_action=access_action,
    )
    data_others = {
        "source_port": 10001,
        "target_port": 10001,
        "source_ip": entity.ip_address,
        "target_ip": satellite_ip,
        "next_hop_ip": satellite_ip,
        "data_size_byte": 0,
        "delay": 0,
        "path": None,
        "ip_list": deque(),
    }
    cross_layer_message = CrossLayerMessage(
        action=ActionType.ENCAPSULATE,
        cross_layer_interface=10001,
        data=message,
        data_others=data_others,
    )
    cross_layer_message = StackFunc.encapsulate_message_to_signal(
        entity=entity,
        cross_layer_message=cross_layer_message,
    )
    await satellite_buffer["Default"].put(cross_layer_message)
    return
