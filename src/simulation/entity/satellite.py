from src.abstract.entity.entity_single import AbstractEntity
from src.tools import random_generator
from configuration import simulation_config as cg
from src.simulation.variable import constant as ct
from multiprocessing import shared_memory
from src.simulation.entity.default_buffer import DefaultBuffer
from src.simulation.variable.virtual_store import VirtualStore
from src.tools.calculation import PhysicalLayerModel
import time
import asyncio
import numpy as np
from src.simulation.variable.performance import NetworkPerformance


class Satellite(AbstractEntity):
    def __init__(self, entity_category, entity_id, orbit_id, satellite_id):
        super().__init__(entity_category, entity_id)
        # Satellite number
        self.orbit_id = orbit_id
        self.satellite_id = satellite_id


        # Satellite network identity
        self.ip_address = random_generator.generate_random_ipv4()
        self.mac_address = random_generator.generate_random_mac()


        # Parameters related to coverage


        # Satellite tables


        self.neighbor_table = {}  # id: {is_alive: bool, delay:float, load:float, "last_update_time":, }
        self.last_send_info_time = 0
        self.routing_table = {}  # Destination ip:{"next_hop_ip": ip, "last_update_time": self.global_variables.get_current_time()}
        self.arp_table = {}  # ip:mac
        self.mac_table = {}  # mac: buffer


        self.buffers = {
            "Default": DefaultBuffer(interface="Default", max_byte=cg.BUFFER_MAX_BYTE)
        }


        # Survival status
        self.is_survival = True
        self.is_permanent_failure = False


        self.bind_shared_memory_views()


    def get_position(self):
        return self.satellite_position_3d[self.entity_id]


    def bind_shared_memory_views(self):
        self._shm_current_time = shared_memory.SharedMemory(name=ct.SHM_CURRENT_TIME)
        self._shm_satellite_position_3d = shared_memory.SharedMemory(name=ct.SHM_SATELLITE_POSITION_3D)
        self._shm_satellite_load_deviation = shared_memory.SharedMemory(name=ct.SHM_SATELLITE_LOAD_DEVIATION)
        self._shm_access_relationship = shared_memory.SharedMemory(name=ct.SHM_ACCESS_RELATIONSHIP)
        self._shm_satellite_latency = shared_memory.SharedMemory(name=ct.SHM_SATELLITE_LATENCY)
        self.current_time = np.ndarray((1,), dtype=np.float64, buffer=self._shm_current_time.buf)
        self.satellite_position_3d = np.ndarray((cg.TOTAL_SATELLITE_NUMBER, 3), dtype=np.float64
                                          , buffer=self._shm_satellite_position_3d.buf)
        self.access_relationship = np.ndarray((cg.USER_NUMBER,), dtype=np.int64
                                     , buffer=self._shm_access_relationship.buf)
        self.satellite_load_deviation = np.ndarray((cg.ORBIT_NUMBER, cg.SATELLITE_NUMBER_PRE_ORBIT,), dtype=np.float64
                                             , buffer=self._shm_satellite_load_deviation.buf)
        self.satellite_latency = np.ndarray((cg.ORBIT_NUMBER, cg.SATELLITE_NUMBER_PRE_ORBIT,), dtype=np.float64
                                      , buffer=self._shm_satellite_latency.buf)
        return


    async def active_behavior(self):
        sleep_time = 0.1
        active_behaviors = self.get_active_behaviors()
        while True:
            if not self.is_survival:
                await asyncio.sleep(0.5)
                continue
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
            if not self.is_survival:
                self.buffers["Default"].task_done()
                NetworkPerformance.packet_loss(data_size_byte=cross_layer_data.data_others["data_size_byte"]
                                          , reason="satellite not alive")
                await asyncio.sleep(0.5)
                continue


            for name, details in passive_behaviors.items():
                func = details["behavior_func"]
                is_async = details["is_async"]
                if is_async:
                    await func(entity=self, data=cross_layer_data)
                else:
                    func(entity=self, data=cross_layer_data)
            self.buffers["Default"].task_done()


    def set_info(self):
        # Store self information in virtual_store
        VirtualStore.satellite_id_to_ip_table[self.entity_id] = self.ip_address
        VirtualStore.satellite_ip_to_id_table[self.ip_address] = self.entity_id
        VirtualStore.ip_to_mac_table[self.ip_address] = self.mac_address
        VirtualStore.mac_to_buffer_table[self.mac_address] = self.buffers
        VirtualStore.satellite_survival_state[self.entity_id] = self.is_survival


    def update_routing_table(self, destination_ip, next_hop_ip):
        self.routing_table[destination_ip] = {"next_hop_ip": next_hop_ip
                                      , "update_interval":cg.SATELLITE_ROUTING_UPDATE_TIME, "last_update_time": self.current_time[0]}
        return


    def access_update_tables(self, ip, mac, buffer):
        self.routing_table[ip] = {"next_hop_ip": ip
                             , "update_interval": 99999, "last_update_time": self.current_time[0]}
        self.arp_table[ip] = mac
        self.mac_table[mac] = buffer
        return


    def access_remove_tables(self, ip, mac):
        if ip in self.routing_table:
            del self.routing_table[ip]
        del self.arp_table[ip]
        del self.mac_table[mac]
        return


    def init_tables(self):
        orbit_number = cg.ORBIT_NUMBER
        satellite_number_pre_orbit = cg.SATELLITE_NUMBER_PRE_ORBIT
        # Find neighbor ids
        id_orbit_plus = ((self.orbit_id + 1) % orbit_number) * satellite_number_pre_orbit + self.satellite_id
        id_orbit_minus = ((self.orbit_id - 1) % orbit_number) * satellite_number_pre_orbit + self.satellite_id
        id_satellite_plus = self.orbit_id * satellite_number_pre_orbit + ((self.satellite_id + 1) % satellite_number_pre_orbit)
        id_satellite_minus = self.orbit_id * satellite_number_pre_orbit + ((self.satellite_id - 1) % satellite_number_pre_orbit)
        # Find neighbor satellites
        id_list = [id_orbit_plus, id_orbit_minus, id_satellite_plus, id_satellite_minus]
        my_position = self.satellite_position_3d[self.entity_id]
        for satellite_id in id_list:
            satellite_ip = VirtualStore.satellite_id_to_ip_table[satellite_id]
            satellite_mac = VirtualStore.ip_to_mac_table[satellite_ip]
            buffer = VirtualStore.mac_to_buffer_table[satellite_mac]
            self.mac_table[satellite_mac] = buffer
            self.arp_table[satellite_ip] = satellite_mac
            self.routing_table[satellite_ip] = {"next_hop_ip": satellite_ip
                                         , "update_interval": 999999, "last_update_time": 0}
            satellite_position = self.satellite_position_3d[satellite_id]
            link_state = PhysicalLayerModel.get_link_state(
                source_position_3d=my_position,
                target_position_3d=satellite_position,
                data_size_byte=0,
                source_id=self.entity_id,
                target_id=satellite_id,
                source_category="satellite",
                target_category="satellite",
                current_time=self.current_time[0],
                processing_time_ms=0,
            )
            self.neighbor_table[satellite_id] = {
                "is_alive": link_state.is_available,
                "delay": link_state.propagation_delay_ms,
                "load": 0.0,
                "last_update_time": 0.0,
                "distance_m": link_state.distance_m,
                "propagation_delay_ms": link_state.propagation_delay_ms,
                "doppler_shift_hz": link_state.doppler_shift_hz,
                "snr_db": link_state.snr_db,
                "effective_rate_bps": link_state.effective_rate_bps,
                "path_loss_db": link_state.path_loss_db,
                "physical_is_available": link_state.is_available,
                "physical_update_time": link_state.updated_at,
            }


    def set_dead(self):
        satellite_load_deviation = np.ndarray((cg.ORBIT_NUMBER, cg.SATELLITE_NUMBER_PRE_ORBIT,), dtype=np.int64
                                       , buffer=self._shm_satellite_load_deviation.buf)
        self.is_survival = False
        VirtualStore.satellite_survival_state[self.entity_id] = self.is_survival
        satellite_load_deviation[self.orbit_id][self.satellite_id] = -1


        satellite_latency = np.ndarray((cg.ORBIT_NUMBER, cg.SATELLITE_NUMBER_PRE_ORBIT,), dtype=np.float64
                                  , buffer=self._shm_satellite_latency.buf)
        satellite_latency[self.orbit_id][self.satellite_id] = -1
        self.disconnect_user()


    def set_alive(self):
        self.is_survival = True
        VirtualStore.satellite_survival_state[self.entity_id] = self.is_survival


        satellite_load_deviation = np.ndarray((cg.ORBIT_NUMBER, cg.SATELLITE_NUMBER_PRE_ORBIT,), dtype=np.int64
                                       , buffer=self._shm_satellite_load_deviation.buf)
        satellite_load_deviation[self.orbit_id][self.satellite_id] = 1
        satellite_latency = np.ndarray((cg.ORBIT_NUMBER, cg.SATELLITE_NUMBER_PRE_ORBIT,), dtype=np.float64
                                  , buffer=self._shm_satellite_latency.buf)
        satellite_latency[self.orbit_id][self.satellite_id] = 1


    def set_permanent_failure(self):
        self.is_permanent_failure = True
        self.set_dead()


    def disconnect_user(self):
        # Access issues
        # Need to handle operations such as making all connected users exit
        keys_to_remove = [key for key, value in VirtualStore.user_access_table.items() if value == self.ip_address]
        for key in keys_to_remove:
            del VirtualStore.user_access_table[key]
        self.access_relationship[self.access_relationship == self.entity_id] = -1
