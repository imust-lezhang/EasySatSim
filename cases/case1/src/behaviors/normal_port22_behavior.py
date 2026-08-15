import random
from collections import deque

import numpy as np

from configuration import simulation_config as cg
from cases.case1.experiment.data.normal_payload_library import normal_port22_payload_library
from cases.case1.experiment.integration.ids_event_log import GROUND_TRUTH_BENIGN
from src.abstract.behavior.behavior import AbstractBehavior
from src.simulation.stack.cross_layer_message.cross_layer_message import ActionType
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage
from src.simulation.stack.protocol_data.application_data import DataMessage
from src.simulation.stack.stack_func import StackFunc
from src.simulation.variable.performance import NetworkPerformance
from src.simulation.variable.virtual_store import VirtualStore


NORMAL_PORT22_BEHAVIOR_NAME = "normal_user_send_port22_data"


class NormalPort22ActiveBehavior(AbstractBehavior):
    @staticmethod
    async def send_normal_port22_data(entity, data):
        current_time = np.ndarray((1,), dtype=np.float64, buffer=entity.shm_current_time.buf)
        if current_time[0] < cg.CASE_NORMAL_PORT22_START_TIME:
            return
        if current_time[0] > cg.CASE_NORMAL_PORT22_END_TIME:
            return

        send_probability = cg.CASE_NORMAL_PORT22_PROBABILITY if data is None else data
        if random.random() > send_probability:
            return

        if entity.access_satellite is None:
            return
        if "*" not in entity.mac_table:
            return

        source_ip = entity.ip_address
        source_port = 22
        target_ip = VirtualStore.satellite_id_to_ip_table[entity.access_satellite]
        target_port = 22
        next_hop_ip = target_ip
        message = random.choice(normal_port22_payload_library)
        data_size_byte = len(message) * cg.DATA_SCALING

        data_message = DataMessage(message=message)
        data_others = {
            "source_port": source_port,
            "target_port": target_port,
            "source_ip": source_ip,
            "target_ip": target_ip,
            "next_hop_ip": next_hop_ip,
            "data_size_byte": data_size_byte,
            "delay": 0,
            "path": None,
            "ip_list": None,
            "ground_truth": GROUND_TRUTH_BENIGN,
        }
        cross_layer_message = CrossLayerMessage(
            action=ActionType.ENCAPSULATE,
            cross_layer_interface=80,
            data=data_message,
            data_others=data_others,
        )
        cross_layer_message = StackFunc.encapsulate_message_to_signal(
            entity=entity,
            cross_layer_message=cross_layer_message,
        )
        if cross_layer_message is None:
            return

        interface = "Default"
        cross_layer_message.data_others["path"] = deque()
        cross_layer_message.data_others["path"].append(entity.position_3D)
        cross_layer_message.data_others["ip_list"] = deque()
        cross_layer_message.data_others["ip_list"].append(entity.ip_address)
        buffer = entity.mac_table["*"][interface]

        await buffer.put(cross_layer_message)
        NetworkPerformance.packet_generate(data_size_byte=data_size_byte)
        return


def register_normal_port22_behavior(behavior_manager):
    if not cg.CASE_ENABLE_NORMAL_PORT22_TRAFFIC:
        return
    behavior_manager.add_active_behavior(
        behavior_name=NORMAL_PORT22_BEHAVIOR_NAME,
        behavior_func=NormalPort22ActiveBehavior.send_normal_port22_data,
        interval=cg.CASE_NORMAL_PORT22_BEHAVIOR_INTERVAL,
        is_async=True,
        data=cg.CASE_NORMAL_PORT22_PROBABILITY,
        last_run=None,
    )
    return


def bind_normal_port22_behavior(entity_manager, behavior_manager, normal_users):
    if not cg.CASE_ENABLE_NORMAL_PORT22_TRAFFIC:
        return
    for normal_user in normal_users:
        entity_manager.bind_active_behavior(
            behavior_manager=behavior_manager,
            entity=normal_user,
            behavior_name=NORMAL_PORT22_BEHAVIOR_NAME,
        )
    return
