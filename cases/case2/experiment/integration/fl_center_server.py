import asyncio
from collections import deque
import time

import numpy as np

from configuration import simulation_config as cg
from src.abstract.entity.entity_single import AbstractEntity
from src.simulation.entity.default_buffer import DefaultBuffer
from src.simulation.stack.cross_layer_message.cross_layer_message import ActionType
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage
from src.simulation.stack.stack_func import StackFunc
from src.simulation.variable import constant as ct
from src.simulation.variable.performance import NetworkPerformance
from src.simulation.variable.virtual_store import VirtualStore
from src.tools import calculation
from src.tools import random_generator

from cases.case2.experiment.integration.case2_event_logger import (
    log_fl_communication_event,
    log_fl_learning_metric,
)
from cases.case2.experiment.learning.cnn_model import build_simple_cnn
from cases.case2.experiment.learning.cnn_model import require_torch
from cases.case2.src.stack.fl_application import FL_MESSAGE_TYPE_GLOBAL
from cases.case2.src.stack.fl_application import FlModelMessage
from cases.case2.src.stack.fl_application import build_fl_model_messages
from cases.case2.src.stack.fl_application import state_dict_to_bytes


class FlCenterServer(AbstractEntity):
    def __init__(self, entity_category, entity_id, latitude, longtitude,
                 ip_address, test_dataset):
        super().__init__(entity_category, entity_id)
        self.ip_address = ip_address
        self.mac_address = random_generator.generate_random_mac()
        self.latitude = latitude
        self.longtitude = longtitude
        self.position_2D = np.array([latitude, longtitude, 0])
        self.position_3D = calculation.position_2D_to_3D(
            lat=latitude,
            lon=longtitude,
            h=0,
        )
        self.access_satellite = None
        self.routing_table = {}
        self.arp_table = {}
        self.mac_table = {}
        self.buffers = {
            "Default": DefaultBuffer(interface="Default", max_byte=1e30)
        }
        self.is_survival = True
        self.test_dataset = test_dataset
        self.global_model = None
        self.device = None
        self.test_loader = None
        self.fl_current_round = 0
        self.fl_round_active = False
        self.fl_selected_user_ids = []
        self.fl_received_updates = {}
        self.fl_expected_updates = 0
        self.fl_round_start_time = 0.0
        self.bind_shared_memory_views()

    async def active_behavior(self):
        sleep_time = 0.1
        active_behaviors = self.get_active_behaviors()
        while True:
            current_time = time.time()
            for details in active_behaviors.values():
                func = details["behavior_func"]
                interval = details["interval"]
                is_async = details["is_async"]
                data = details["data"]
                last_run = details["last_run"]
                if last_run is None or current_time - last_run >= interval:
                    if is_async:
                        await func(entity=self, data=data)
                    else:
                        func(entity=self, data=data)
                    details["last_run"] = current_time
            await asyncio.sleep(sleep_time)

    async def passive_behavior(self):
        passive_behaviors = self.get_passive_behaviors()
        while True:
            cross_layer_data = await self.buffers["Default"].get()
            for details in passive_behaviors.values():
                func = details["behavior_func"]
                is_async = details["is_async"]
                if is_async:
                    await func(entity=self, data=cross_layer_data)
                else:
                    func(entity=self, data=cross_layer_data)
            self.buffers["Default"].task_done()

    def bind_shared_memory_views(self):
        self._shm_satellite_position_3d = shared_memory_view(
            ct.SHM_SATELLITE_POSITION_3D
        )
        self._shm_satellite_position_2d = shared_memory_view(
            ct.SHM_SATELLITE_POSITION_2D
        )
        self._shm_routing_path = shared_memory_view(ct.SHM_ROUTING_PATH)
        self.shm_current_time = shared_memory_view(ct.SHM_CURRENT_TIME)
        self.satellite_position_3d = np.ndarray(
            (cg.TOTAL_SATELLITE_NUMBER, 3),
            dtype=np.float64,
            buffer=self._shm_satellite_position_3d.buf,
        )
        self.satellite_position_2d = np.ndarray(
            (cg.TOTAL_SATELLITE_NUMBER, 3),
            dtype=np.float64,
            buffer=self._shm_satellite_position_2d.buf,
        )
        self.routing_path = np.ndarray(
            (100, 3),
            dtype=np.float64,
            buffer=self._shm_routing_path.buf,
        )
        self.current_time = np.ndarray(
            (1,),
            dtype=np.float64,
            buffer=self.shm_current_time.buf,
        )
        return

    def set_info(self):
        VirtualStore.user_id_to_ip_table[self.entity_id] = self.ip_address
        VirtualStore.user_ip_to_id_table[self.ip_address] = self.entity_id
        VirtualStore.ip_to_mac_table[self.ip_address] = self.mac_address
        VirtualStore.mac_to_buffer_table[self.mac_address] = self.buffers
        self.initialize_model()
        return

    def initialize_model(self):
        if self.global_model is not None:
            return
        torch, _ = require_torch()
        from torch.utils.data import DataLoader

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.global_model = build_simple_cnn(device=self.device)
        self.test_loader = DataLoader(
            self.test_dataset,
            batch_size=cg.ML_BATCH_SIZE,
            shuffle=False,
        )
        return

    def access_update_tables(self, next_hop_ip, mac, buffer):
        self.routing_table["*"] = {
            "next_hop_ip": next_hop_ip,
            "update_interval": cg.USER_ROUTING_UPDATE_TIME,
            "last_update_time": 0,
        }
        self.arp_table["*"] = mac
        self.mac_table["*"] = buffer
        return

    def access_remove_tables(self):
        self.routing_table = {}
        self.arp_table = {}
        self.mac_table = {}
        return

    def set_routing_path(self, path_list):
        path_array = np.array(path_list)
        n = path_array.shape[0]
        self.routing_path[:n] = path_array
        self.routing_path[n:] = -1
        return

    async def manage_fl_round(self):
        if self.access_satellite is None or "*" not in self.mac_table:
            return
        self.initialize_model()

        if not self.fl_round_active:
            await self.start_fl_round()
            return

        if self.should_aggregate_current_round():
            reason = self.get_aggregation_reason()
            self.aggregate_current_round(aggregation_reason=reason)
            return

        if self.is_round_timed_out():
            self.skip_current_round()
        return

    async def start_fl_round(self):
        available_user_ids = get_available_user_ids()
        if len(available_user_ids) < cg.FL_CLIENTS_PER_ROUND:
            return

        self.fl_current_round += 1
        self.fl_selected_user_ids = select_round_users(
            available_user_ids=available_user_ids,
            round_id=self.fl_current_round,
            count=cg.FL_CLIENTS_PER_ROUND,
        )
        self.fl_expected_updates = min(
            cg.FL_UPDATES_PER_ROUND,
            len(self.fl_selected_user_ids),
        )
        self.fl_received_updates = {}
        self.fl_round_active = True
        self.fl_round_start_time = self.get_current_time()
        await self.broadcast_global_model_to_selected_users()
        return

    async def broadcast_global_model_to_selected_users(self):
        if not cg.FL_ENABLE_GLOBAL_MODEL_DOWNLINK:
            return

        state_dict_bytes = state_dict_to_bytes(self.global_model.state_dict())
        for user_id in self.fl_selected_user_ids:
            target_ip = VirtualStore.user_id_to_ip_table.get(user_id)
            if not target_ip:
                continue
            await self.send_global_model_to_user(
                user_id=user_id,
                target_ip=target_ip,
                state_dict_bytes=state_dict_bytes,
            )
        return

    async def send_global_model_to_user(self, user_id, target_ip,
                                        state_dict_bytes):
        model_messages = build_fl_model_messages(
            parameters=state_dict_bytes,
            user_id=user_id,
            round_id=self.fl_current_round,
            message_type=FL_MESSAGE_TYPE_GLOBAL,
            chunk_payload_byte=cg.FL_CHUNK_PAYLOAD_BYTE,
        )
        total_network_counted_byte = 0
        next_hop_ip = VirtualStore.satellite_id_to_ip_table[self.access_satellite]
        buffer = self.mac_table["*"]["Default"]

        for model_message in model_messages:
            payload_byte = len(FlModelMessage.data_to(model_message))
            network_counted_byte = int(round(
                payload_byte * cg.ML_DATA_SIZE_SCALING
            ))
            data_others = {
                "source_port": cg.CASE2_APPLICATION_PORT,
                "target_port": cg.CASE2_APPLICATION_PORT,
                "source_ip": self.ip_address,
                "target_ip": target_ip,
                "next_hop_ip": next_hop_ip,
                "data_size_byte": network_counted_byte,
                "delay": 0,
                "path": None,
                "ip_list": None,
            }
            cross_layer_message = CrossLayerMessage(
                action=ActionType.ENCAPSULATE,
                cross_layer_interface=cg.CASE2_APPLICATION_PORT,
                data=model_message,
                data_others=data_others,
            )
            cross_layer_message = StackFunc.encapsulate_message_to_signal(
                entity=self,
                cross_layer_message=cross_layer_message,
            )
            if cross_layer_message is None:
                continue

            cross_layer_message.data_others["path"] = deque()
            cross_layer_message.data_others["path"].append(self.position_3D)
            cross_layer_message.data_others["ip_list"] = deque()
            cross_layer_message.data_others["ip_list"].append(self.ip_address)
            await buffer.put(cross_layer_message)
            NetworkPerformance.packet_generate(data_size_byte=network_counted_byte)
            total_network_counted_byte += network_counted_byte

        if total_network_counted_byte <= 0:
            return

        log_fl_communication_event(
            simulation_time=self.get_current_time(),
            event_type="global_model_sent",
            round_id=self.fl_current_round,
            user_id=user_id,
            source_ip=self.ip_address,
            target_ip=target_ip,
            payload_byte=len(state_dict_bytes),
            network_counted_byte=total_network_counted_byte,
        )
        return

    def receive_fl_model_update(self, state_dict, user_id, round_id,
                                source_ip, target_ip, payload_byte,
                                network_counted_byte):
        if not self.fl_round_active:
            return
        if round_id != self.fl_current_round:
            return
        if user_id not in self.fl_selected_user_ids:
            return
        if user_id in self.fl_received_updates:
            return

        self.fl_received_updates[user_id] = state_dict
        log_fl_communication_event(
            simulation_time=self.get_current_time(),
            event_type="local_update_received",
            round_id=round_id,
            user_id=user_id,
            source_ip=source_ip,
            target_ip=target_ip,
            payload_byte=payload_byte,
            network_counted_byte=network_counted_byte,
        )
        return

    def should_aggregate_current_round(self):
        received_count = len(self.fl_received_updates)
        if received_count >= self.fl_expected_updates:
            return True
        if not self.is_round_timed_out():
            return False
        return received_count >= cg.FL_MIN_UPDATES_PER_ROUND

    def get_aggregation_reason(self):
        if len(self.fl_received_updates) >= self.fl_expected_updates:
            return "target_updates_reached"
        return "round_timeout"

    def is_round_timed_out(self):
        elapsed_time = self.get_current_time() - self.fl_round_start_time
        return elapsed_time >= cg.FL_ROUND_TIMEOUT_SECONDS

    def aggregate_current_round(self, aggregation_reason):
        state_dicts = list(self.fl_received_updates.values())
        averaged_state_dict = average_state_dicts(state_dicts=state_dicts)
        self.global_model.load_state_dict(averaged_state_dict)
        test_accuracy = self.evaluate()
        log_fl_learning_metric(
            simulation_time=self.get_current_time(),
            round_id=self.fl_current_round,
            selected_clients=len(self.fl_selected_user_ids),
            received_updates=len(self.fl_received_updates),
            aggregation_reason=aggregation_reason,
            test_accuracy=test_accuracy,
        )
        print(
            "[Case2 FL] "
            f"round={self.fl_current_round}, "
            f"updates={len(self.fl_received_updates)}, "
            f"accuracy={test_accuracy:.2f}%, "
            f"reason={aggregation_reason}, "
            f"time={self.get_current_time():.2f}s"
        )
        self.fl_round_active = False
        self.fl_selected_user_ids = []
        self.fl_received_updates = {}
        self.fl_expected_updates = 0
        return test_accuracy

    def skip_current_round(self):
        received_count = len(self.fl_received_updates)
        log_fl_communication_event(
            simulation_time=self.get_current_time(),
            event_type="round_skipped",
            round_id=self.fl_current_round,
            user_id="",
            source_ip=self.ip_address,
            target_ip="",
            payload_byte=0,
            network_counted_byte=0,
        )
        print(
            "[Case2 FL] "
            f"round={self.fl_current_round}, "
            f"updates={received_count}, "
            "reason=round_timeout_insufficient_updates, "
            f"time={self.get_current_time():.2f}s"
        )
        self.fl_round_active = False
        self.fl_selected_user_ids = []
        self.fl_received_updates = {}
        self.fl_expected_updates = 0
        return

    def evaluate(self):
        torch, _ = require_torch()

        self.global_model.eval()
        total = 0
        correct = 0
        with torch.no_grad():
            for batch_data, batch_target in self.test_loader:
                batch_data = batch_data.to(self.device)
                batch_target = batch_target.to(self.device)
                output = self.global_model(batch_data)
                _, predicted = torch.max(output.data, 1)
                total += batch_target.size(0)
                correct += (predicted == batch_target).sum().item()
        if total == 0:
            return 0.0
        return 100.0 * correct / total

    def get_current_time(self):
        if hasattr(self, "current_time"):
            return float(self.current_time[0])
        return 0.0


def average_state_dicts(state_dicts):
    if not state_dicts:
        raise ValueError("Cannot average an empty list of state_dicts.")

    torch, _ = require_torch()
    averaged_state_dict = {}
    first_state_dict = state_dicts[0]
    for key, value in first_state_dict.items():
        if not torch.is_floating_point(value):
            averaged_state_dict[key] = value
            continue
        averaged_state_dict[key] = torch.mean(
            torch.stack([
                state_dict[key].float()
                for state_dict in state_dicts
            ]),
            dim=0,
        )
    return averaged_state_dict


def get_available_user_ids():
    available_user_ids = []
    for user_id in range(cg.USER_NUMBER):
        user_ip = VirtualStore.user_id_to_ip_table.get(user_id)
        if user_ip in VirtualStore.user_access_table:
            available_user_ids.append(user_id)
    return available_user_ids


def select_round_users(available_user_ids, round_id, count):
    rng = np.random.default_rng(cg.CASE_RANDOM_SEED + round_id)
    selected_count = min(count, len(available_user_ids))
    selected = rng.choice(
        np.asarray(available_user_ids, dtype=np.int64),
        size=selected_count,
        replace=False,
    )
    return [int(user_id) for user_id in selected]


def shared_memory_view(name):
    from multiprocessing import shared_memory

    return shared_memory.SharedMemory(name=name)
