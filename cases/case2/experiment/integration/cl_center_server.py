import asyncio
import time

import numpy as np

from configuration import simulation_config as cg
from src.abstract.entity.entity_single import AbstractEntity
from src.simulation.entity.default_buffer import DefaultBuffer
from src.simulation.variable import constant as ct
from src.simulation.variable.virtual_store import VirtualStore
from src.tools import calculation
from src.tools import random_generator

from cases.case2.experiment.integration.case2_event_logger import (
    log_cl_communication_event,
    log_cl_learning_metric,
)
from cases.case2.experiment.learning.cnn_model import build_simple_cnn
from cases.case2.experiment.learning.cnn_model import require_torch


class ClCenterServer(AbstractEntity):
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
        self.model = None
        self.device = None
        self.criterion = None
        self.optimizer = None
        self.test_loader = None
        self.cl_sample_images = []
        self.cl_sample_labels = []
        self.cl_received_sample_count = 0
        self.cl_train_round = 0
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
        if self.model is not None:
            return
        torch, nn = require_torch()
        import torch.optim as optim
        from torch.utils.data import DataLoader

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = build_simple_cnn(device=self.device)
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=cg.ML_LEARNING_RATE,
        )
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

    def receive_cl_sample(self, sample_message, source_user_id, source_ip,
                          target_ip, payload_byte, network_counted_byte):
        self.cl_sample_images.append(sample_message.image)
        self.cl_sample_labels.append(int(sample_message.label))
        self.cl_received_sample_count += 1

        if should_log_checkpoint(
                self.cl_received_sample_count,
                cg.CL_COMMUNICATION_LOG_INTERVAL):
            log_cl_communication_event(
                simulation_time=self.get_current_time(),
                event_type="sample_received_checkpoint",
                cumulative_samples=self.cl_received_sample_count,
                entity_id=source_user_id,
                source_ip=source_ip,
                target_ip=target_ip,
                sample_index=sample_message.index,
                label=sample_message.label,
                payload_byte=payload_byte,
                network_counted_byte=network_counted_byte,
            )
        return

    def train_cl_round_if_ready(self, trigger_sample_count):
        if len(self.cl_sample_images) < trigger_sample_count:
            return None

        self.initialize_model()
        torch, _ = require_torch()
        from torch.utils.data import DataLoader
        from torch.utils.data import TensorDataset

        used_images = self.cl_sample_images[:trigger_sample_count]
        used_labels = self.cl_sample_labels[:trigger_sample_count]
        train_dataset = TensorDataset(
            torch.stack(used_images),
            torch.tensor(used_labels, dtype=torch.long),
        )
        train_loader = DataLoader(
            train_dataset,
            batch_size=cg.ML_BATCH_SIZE,
            shuffle=True,
        )
        train_loss = self.train_on_loader(train_loader=train_loader)
        test_accuracy = self.evaluate()

        del self.cl_sample_images[:trigger_sample_count]
        del self.cl_sample_labels[:trigger_sample_count]
        self.cl_train_round += 1
        log_cl_learning_metric(
            simulation_time=self.get_current_time(),
            train_round=self.cl_train_round,
            received_samples_total=self.cl_received_sample_count,
            used_samples=trigger_sample_count,
            remaining_buffered_samples=len(self.cl_sample_images),
            train_loss=train_loss,
            test_accuracy=test_accuracy,
        )
        print(
            "[Case2 CL] "
            f"round={self.cl_train_round}, "
            f"used_samples={trigger_sample_count}, "
            f"accuracy={test_accuracy:.2f}%, "
            f"time={self.get_current_time():.2f}s"
        )
        return test_accuracy

    def train_on_loader(self, train_loader):
        self.model.train()
        total_loss = 0.0
        batch_count = 0
        for _ in range(cg.CL_SERVER_TRAIN_EPOCHS):
            for batch_data, batch_target in train_loader:
                batch_data = batch_data.to(self.device)
                batch_target = batch_target.to(self.device)
                self.optimizer.zero_grad()
                output = self.model(batch_data)
                loss = self.criterion(output, batch_target)
                loss.backward()
                self.optimizer.step()
                total_loss += float(loss.item())
                batch_count += 1
        if batch_count == 0:
            return 0.0
        return total_loss / batch_count

    def evaluate(self):
        torch, _ = require_torch()

        self.model.eval()
        total = 0
        correct = 0
        with torch.no_grad():
            for batch_data, batch_target in self.test_loader:
                batch_data = batch_data.to(self.device)
                batch_target = batch_target.to(self.device)
                output = self.model(batch_data)
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


def shared_memory_view(name):
    from multiprocessing import shared_memory

    return shared_memory.SharedMemory(name=name)


def should_log_checkpoint(count, interval):
    return count == 1 or (interval > 0 and count % interval == 0)
