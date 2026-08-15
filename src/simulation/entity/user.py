from src.abstract.entity.entity_single import AbstractEntity
from src.simulation.entity.default_buffer import DefaultBuffer
from src.simulation.variable import constant as ct
from configuration import simulation_config as cg
from src.tools import random_generator, calculation
from multiprocessing import shared_memory
import numpy as np
import time
import asyncio
from src.simulation.variable.virtual_store import VirtualStore


class User(AbstractEntity):
    def __init__(self, entity_category, entity_id, population_array):
        """
        :param entity_category: Entity category
        :param entity_id: Entity ID
        :param population_array: Population matrix, used for population calculation
        """
        super().__init__(entity_category, entity_id)


        # User network identity
        self.ip_address = random_generator.generate_random_ipv4()
        self.mac_address = random_generator.generate_random_mac()
        self.username, self.password = random_generator.generate_random_credentials(username_length=8,
                                                                     password_length=16)


        # # User data rate for network transmission


        # User coordinates
        latitude, longtitude = random_generator.generate_random_user_position(
            population_array=population_array,
            latitude_min=cg.USER_LATITUDE_MIN,
            latitude_max=cg.USER_LATITUDE_MAX,
        )
        self.position_2D = np.array([latitude, longtitude, 0])  # Geographic coordinate system latitude/longitude/altitude
        self.position_3D = calculation.position_2D_to_3D(lat=latitude, lon=longtitude, h=0)  # Earth-centered inertial coordinate system


        # Accessed satellite
        self.access_satellite = None  # The actual accessed satellite


        # Tables required in the network
        self.routing_table = {}  # Destination ip: next hop ip
        self.arp_table = {}  # ip:mac
        self.mac_table = {}  # mac:interface


        # Buffer
        self.buffers = {
            "Default": DefaultBuffer(interface="Default", max_byte=1e30)
        }


        # Survival status
        self.is_survival = True


        # Define shared variables
        self.bind_shared_memory_views()


        self.state_dict = None
        self.is_train = False
        self.is_first = True
        self.local_state_dict = None
        self.global_state_dict = None
        self.round = 0


    async def active_behavior(self):
        sleep_time = 0.1
        active_behaviors = self.get_active_behaviors()
        while True:
            current_time = time.time()
            for name, details in active_behaviors.items():
                func = details['behavior_func']
                interval = details['interval']
                is_async = details['is_async']
                data = details['data']
                last_run = details['last_run']
                if last_run is None or (current_time - last_run >= interval):
                    if is_async:
                        await func(entity=self, data=data)
                    else:
                        func(entity=self, data=data)
                    active_behaviors[name]['last_run'] = current_time
            await asyncio.sleep(sleep_time)


    async def passive_behavior(self):
        passive_behaviors = self.get_passive_behaviors()
        while True:
            cross_layer_data = await self.buffers["Default"].get()
            for name, details in passive_behaviors.items():
                func = details["behavior_func"]
                is_async = details["is_async"]
                if is_async:
                    await func(entity=self, data=cross_layer_data)
                else:
                    func(entity=self, data=cross_layer_data)
            self.buffers["Default"].task_done()


    def bind_shared_memory_views(self):
        self._shm_satellite_position_3d = shared_memory.SharedMemory(name=ct.SHM_SATELLITE_POSITION_3D)
        self._shm_satellite_position_2d = shared_memory.SharedMemory(name=ct.SHM_SATELLITE_POSITION_2D)
        self._shm_access_relationship = shared_memory.SharedMemory(name=ct.SHM_ACCESS_RELATIONSHIP)
        self._shm_routing_path = shared_memory.SharedMemory(name=ct.SHM_ROUTING_PATH)
        self._shm_user_position_3d = shared_memory.SharedMemory(name=ct.SHM_USER_POSITION_3D)
        self.shm_current_time = shared_memory.SharedMemory(name=ct.SHM_CURRENT_TIME)
        self.satellite_position_3d = np.ndarray((cg.TOTAL_SATELLITE_NUMBER, 3), dtype=np.float64
                                     , buffer=self._shm_satellite_position_3d.buf)
        self.satellite_position_2d = np.ndarray((cg.TOTAL_SATELLITE_NUMBER, 3), dtype=np.float64
                                     , buffer=self._shm_satellite_position_2d.buf)
        self.access_relationship = np.ndarray((cg.USER_NUMBER, ), dtype=np.int64
                                     , buffer=self._shm_access_relationship.buf)
        self.routing_path = np.ndarray((100, 3,), dtype=np.float64
                                  , buffer=self._shm_routing_path.buf)
        self.user_position_3d = np.ndarray((cg.USER_NUMBER, 3), dtype=np.float64
                                     , buffer=self._shm_user_position_3d.buf)
        self.current_time = np.ndarray((1,), dtype=np.float64, buffer=self.shm_current_time.buf)
        return


    def set_info(self):
        # Store self information in virtual_store
        VirtualStore.user_id_to_ip_table[self.entity_id] = self.ip_address
        VirtualStore.user_ip_to_id_table[self.ip_address] = self.entity_id
        VirtualStore.ip_to_mac_table[self.ip_address] = self.mac_address
        VirtualStore.mac_to_buffer_table[self.mac_address] = self.buffers


    def access_update_tables(self, next_hop_ip, mac, buffer):
        self.routing_table['*'] = {"next_hop_ip": next_hop_ip
                             , "update_interval": cg.USER_ROUTING_UPDATE_TIME, "last_update_time": 0}
        self.arp_table['*'] = mac
        self.mac_table['*'] = buffer
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


    def set_position(self, latitude, longtitude):
        self.position_2D = np.array([latitude, longtitude, 0])  # Geographic coordinate system latitude/longitude/altitude
        self.position_3D = calculation.position_2D_to_3D(lat=latitude, lon=longtitude, h=0)  # Earth-centered inertial coordinate system
        self.user_position_3d[self.entity_id] = self.position_3D


    def load_model(self, model, data):
        import torch
        import torch.nn as nn
        import torch.optim as optim


        self.model = model
        self.data = data
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)


    def train(self, epochs=10):
        from torch.utils.data import DataLoader, Subset, random_split
        self.model.train()
        data_loader = DataLoader(self.data, batch_size=64, shuffle=True)
        for epoch in range(epochs):  # Outer loop controls training rounds
            for data, target in data_loader:
                data, target = data.to(self.device), target.to(self.device)
                self.optimizer.zero_grad()
                output = self.model(data)
                loss = self.criterion(output, target)
                loss.backward()
                self.optimizer.step()
        return self.model.state_dict()
