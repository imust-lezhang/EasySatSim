import random
import numpy as np
from src.abstract.behavior.behavior import AbstractBehavior
from src.simulation.stack.stack_func import StackFunc
from src.simulation.stack.protocol_data.application_data import DataMessage, AccessMessage, AccessActionType
from src.simulation.variable.virtual_store import VirtualStore
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage, ActionType
from src.simulation.variable.performance import NetworkPerformance
from src.tools import calculation
from configuration import simulation_config as cg
from collections import deque


class UserActiveBehavior(AbstractBehavior):
    @staticmethod
    async def simple_access_satellite(entity, data):
        covered_satellites_ids, satellites_position_3d = UserActiveBehavior._find_satellites_in_los(entity=entity, data=None)
        # if entity.access_satellite in covered_satellites_ids:
        #     return


        if covered_satellites_ids.size > 0:  # If the number of satellites in the field of view is greater than 0
            # satellite_id = covered_satellites_ids[0]


            satellite_id = None
            for i in covered_satellites_ids:
                if VirtualStore.satellite_survival_state[i]:
                    satellite_id = i
                    break
            if satellite_id is None:
                return


            if satellite_id!= entity.access_satellite:  # Determine whether the current satellite and the accessed satellite are the same
                if entity.access_satellite is not None:  # If there is already an accessed satellite, a message needs to be sent to it to inform that I am about to exit
                    satellite_ip, satellite_mac, satellite_buffers = VirtualStore.get_satellite_info_from_id(
                        satellite_id=entity.access_satellite)
                    await UserActiveBehavior._send_quit_message(entity=entity, satellite_ip=satellite_ip
                                                        , satellite_buffer=satellite_buffers)


                    """Modified place"""
                    if entity.ip_address in VirtualStore.user_access_table:
                        del VirtualStore.user_access_table[entity.ip_address]


                entity.access_satellite = satellite_id
                entity.access_relationship[entity.entity_id] = satellite_id
                satellite_ip, satellite_mac, satellite_buffers = VirtualStore.get_satellite_info_from_id(satellite_id=satellite_id)
                entity.access_update_tables(next_hop_ip=satellite_ip, mac=satellite_mac, buffer=satellite_buffers)


                """Modified place"""
                VirtualStore.user_access_table[entity.ip_address] = satellite_ip


                await UserActiveBehavior._send_access_message(entity=entity, satellite_ip=satellite_ip
                                                      , satellite_buffer=satellite_buffers)
            else:  # Same as the currently accessed satellite, no need to do anything
                pass
        else:  # If there are no satellites in the field of view
            if entity.access_satellite is not None:
                satellite_ip, satellite_mac, satellite_buffers = VirtualStore.get_satellite_info_from_id(
                    satellite_id=entity.access_satellite)
                await UserActiveBehavior._send_quit_message(entity=entity, satellite_ip=satellite_ip
                                                    , satellite_buffer=satellite_buffers)
                entity.access_satellite = None
                entity.access_relationship[entity.entity_id] = -1
                entity.access_remove_tables()


                """Modified place"""
                if entity.ip_address in VirtualStore.user_access_table:
                    del VirtualStore.user_access_table[entity.ip_address]


        """


        There is a problem with the user access table, and the content of the table does not always match


        The current solution: putting the update of VirtualStore.user_access_table in this function can run normally


        But I don't know why, the application_func can initially update VirtualStore.user_access_table, but does not update it later


        There should be an order for deletion/insertion
        Currently, the order of QUIT and ACCESS is not necessarily fixed, so ACCESS may occur before QUIT, resulting in an incorrect access_table order.


        Therefore, a switch state should be added


        """
        return


    @staticmethod
    async def _send_access_message(entity, satellite_ip, satellite_buffer):
        message = AccessMessage(user_id=entity.entity_id, user_ip=entity.ip_address, user_mac=entity.mac_address,
                              access_action=AccessActionType.ACCESS)
        data_others = {"source_port": 10001, "target_port": 10001
                    , "source_ip": entity.ip_address, "target_ip": satellite_ip, "next_hop_ip": satellite_ip
                    , "data_size_byte": 0, "delay": 0, "path": None, "ip_list": deque()}
        cross_layer_message = CrossLayerMessage(action=ActionType.ENCAPSULATE, cross_layer_interface=10001,
                                          data=message, data_others=data_others)
        cross_layer_message = StackFunc.encapsulate_message_to_signal(entity=entity,
                                                           cross_layer_message=cross_layer_message)
        await satellite_buffer["Default"].put(cross_layer_message)


    @staticmethod
    async def _send_quit_message(entity, satellite_ip, satellite_buffer):
        message = AccessMessage(user_id=entity.entity_id, user_ip=entity.ip_address, user_mac=entity.mac_address,
                              access_action=AccessActionType.QUIT)
        data_others = {"source_port": 10001, "target_port": 10001
                    , "source_ip": entity.ip_address, "target_ip": satellite_ip, "next_hop_ip": satellite_ip
                    , "data_size_byte": 0, "delay": 0, "path": None, "ip_list": deque()}
        cross_layer_message = CrossLayerMessage(action=ActionType.ENCAPSULATE, cross_layer_interface=10001,
                                          data=message, data_others=data_others)
        cross_layer_message = StackFunc.encapsulate_message_to_signal(entity=entity,
                                                           cross_layer_message=cross_layer_message)
        await satellite_buffer["Default"].put(cross_layer_message)


    @staticmethod
    async def simple_user_send_data(entity, data):
        for i in range(1):
            if entity.access_satellite is not None:
                source_ip = entity.ip_address
                source_port = 80
                if cg.USER_NUMBER!= 2:
                    target_id = random.randint(0, cg.USER_NUMBER - 1)
                else:
                    target_id = entity.entity_id ^ 1


                target_ip = VirtualStore.user_id_to_ip_table[target_id]
                target_port = 80
                data_size_byte = random.randint(cg.USER_DATA_RATE_MIN, cg.USER_DATA_RATE_MAX)
                message = 'a' * data_size_byte  # Construct message field
                data_size_byte = data_size_byte * cg.DATA_SCALING  # Unit unified to: KB
                data_message = DataMessage(message=message)
                next_hop_ip = VirtualStore.satellite_id_to_ip_table[entity.access_satellite]
                data_others = {"source_port": source_port, "target_port": target_port
                            , "source_ip": source_ip, "target_ip": target_ip, "next_hop_ip": next_hop_ip
                            , "data_size_byte": data_size_byte, "delay": 0, "path": None, "ip_list": None}


                cross_layer_message = CrossLayerMessage(action=ActionType.ENCAPSULATE, cross_layer_interface=80,
                                                  data=data_message, data_others=data_others)
                cross_layer_message = StackFunc.encapsulate_message_to_signal(entity=entity, cross_layer_message=cross_layer_message)


                # Add metrics
                interface = "Default"
                cross_layer_message.data_others["path"] = deque()
                cross_layer_message.data_others["path"].append(entity.position_3D)
                cross_layer_message.data_others["ip_list"] = deque()
                cross_layer_message.data_others["ip_list"].append(entity.ip_address)
                buffer = entity.mac_table['*'][interface]


                await buffer.put(cross_layer_message)
                NetworkPerformance.packet_generate(data_size_byte=data_size_byte)


    @staticmethod
    def _find_satellites_in_los(entity, data):
        user_lat, user_lon = entity.position_2D[0], entity.position_2D[1]
        satellites_position_3d = entity.satellite_position_3d
        satellite_position_2d = entity.satellite_position_2d


        satellite_lats, satellite_lons = satellite_position_2d[:, 0], satellite_position_2d[:, 1]
        distances = calculation.haversine_distance(user_lat, user_lon, satellite_lats, satellite_lons)
        covered_satellites_ids = np.where(distances <= cg.COVER_RADIUS)[0]
        covered_satellites_ids = covered_satellites_ids[np.argsort(distances[covered_satellites_ids])]
        return covered_satellites_ids, satellites_position_3d
