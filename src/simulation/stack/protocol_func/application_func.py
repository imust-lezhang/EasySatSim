from src.abstract.stack.protocol_func import AbstractProtocolFunc
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage, ActionType
from src.simulation.stack.protocol_data.application_data import AccessMessage, AccessActionType, DataMessage
from src.simulation.variable.virtual_store import VirtualStore
from src.simulation.variable.performance import NetworkPerformance
from collections import deque


class Port80(AbstractProtocolFunc):
    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage):
        data_message = cross_layer_message.data
        NetworkPerformance.packet_arrive(data_size_byte=cross_layer_message.data_others["data_size_byte"]
                                         , total_delay=cross_layer_message.data_others["delay"], hop_count=len(cross_layer_message.data_others["path"]) - 2)
        if entity.entity_id == 0:
            entity.set_routing_path(path_list=cross_layer_message.data_others["path"])
            # print(cross_layer_message.data_others["delay"])
        cross_layer_message.action = ActionType.STOP
        return cross_layer_message

    @staticmethod
    def encapsulate_func(entity, cross_layer_message: CrossLayerMessage):
        cross_layer_message.action = ActionType.ENCAPSULATE
        cross_layer_message.cross_layer_interface = 0x0006
        return cross_layer_message


class Port10001(AbstractProtocolFunc):
    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage):
        # Get the message
        access_message: AccessMessage = cross_layer_message.data
        # Judging the type of the access message
        if access_message.access_action == AccessActionType.ACCESS:  # 接入
            buffer = VirtualStore.mac_to_buffer_table[access_message.user_mac]  # 从全局变量中获得该用户的buffer
            # Update satellite table related information
            entity.access_update_tables(ip=access_message.user_ip, mac=access_message.user_mac, buffer=buffer)
        elif access_message.access_action == AccessActionType.QUIT:  # 退出
            # Remove satellite table related information.
            entity.access_remove_tables(ip=access_message.user_ip, mac=access_message.user_mac)
        # Do not continue
        cross_layer_message.action = ActionType.STOP
        return cross_layer_message

    @staticmethod
    def encapsulate_func(entity, cross_layer_message: CrossLayerMessage):
        # downward transfer
        cross_layer_message.action = ActionType.ENCAPSULATE
        cross_layer_message.cross_layer_interface = 0x0006
        return cross_layer_message


# Calculate RTT
class Port20000(AbstractProtocolFunc):
    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage):
        data_message: DataMessage = cross_layer_message.data
        if 'aaaaaaaaa' in data_message.message:
            pass
            data_message.message = 'ack'
            cross_layer_message.data = data_message
            cross_layer_message.action = ActionType.ENCAPSULATE
            cross_layer_message.cross_layer_interface = 0x0006

            target_id = entity.entity_id ^ 1
            target_ip = VirtualStore.user_id_to_ip_table[target_id]
            if entity.access_satellite is not None:
                next_hop_ip = VirtualStore.satellite_id_to_ip_table[entity.access_satellite]
            else:
                NetworkPerformance.packet_loss(data_size_byte=cross_layer_message.data_others["data_size_byte"], reason="port 20000 no access satellite")
                cross_layer_message.action = ActionType.STOP
                return cross_layer_message
            data_others = {"source_port": 20000, "target_port": 20000
                , "source_ip": entity.ip_address, "target_ip": target_ip, "next_hop_ip": next_hop_ip
                , "data_size_byte": cross_layer_message.data_others["data_size_byte"]
                , "delay": cross_layer_message.data_others["delay"], "path": cross_layer_message.data_others["path"], "ip_list": deque()}
            cross_layer_message.data_others = data_others
        elif 'ack' == data_message.message:
            NetworkPerformance.packet_arrive(data_size_byte=cross_layer_message.data_others["data_size_byte"]
                                             , total_delay=cross_layer_message.data_others["delay"], hop_count=len(cross_layer_message.data_others["path"]) - 1)
            if entity.entity_id == 0:
                entity.set_routing_path(path_list=cross_layer_message.data_others["path"])
                print("RTT is ", cross_layer_message.data_others["delay"], "ms")
            cross_layer_message.action = ActionType.STOP
        return cross_layer_message

    @staticmethod
    def encapsulate_func(entity, cross_layer_message: CrossLayerMessage):
        cross_layer_message.action = ActionType.ENCAPSULATE
        cross_layer_message.cross_layer_interface = 0x0006
        return cross_layer_message
