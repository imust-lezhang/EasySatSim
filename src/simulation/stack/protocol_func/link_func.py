from src.abstract.stack.protocol_func import AbstractProtocolFunc
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage, ActionType
from src.simulation.stack.protocol_data.link_data import DataFrame
from src.simulation.variable.performance import NetworkPerformance

class LinkEthernet(AbstractProtocolFunc):
    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage):
        data_frame: DataFrame = cross_layer_message.data
        if data_frame.destination_mac == entity.mac_address:
            cross_layer_message.action = ActionType.PARSE
            cross_layer_message.cross_layer_interface = data_frame.type
        else:
            # entity.global_variables.record_packet_loss(data_size_byte=cross_layer_message.data_others["data_size_byte"], reason="link layer parse")
            # entity.queue_manager.packet_loss(reason="link layer parse")
            NetworkPerformance.packet_loss(data_size_byte=cross_layer_message.data_others["data_size_byte"], reason="link layer parse")
            cross_layer_message.action = ActionType.STOP
        return cross_layer_message

    @staticmethod
    def encapsulate_func(entity, cross_layer_message: CrossLayerMessage):
        source_mac = entity.mac_address
        next_hop_ip = cross_layer_message.data_others["next_hop_ip"]
        del cross_layer_message.data_others["next_hop_ip"]
        if next_hop_ip in entity.arp_table:  # If the mac table can find the ip
            destination_mac = entity.arp_table[next_hop_ip]
        elif "*" in entity.arp_table:  # *Indicates that any packet needs to go through this mac.
            destination_mac = entity.arp_table["*"]
        else:  # If the mac can't be found, the packet will be lost directly.
            NetworkPerformance.packet_loss(data_size_byte=cross_layer_message.data_others["data_size_byte"], reason="link layer encapsulate")
            cross_layer_message.action = ActionType.STOP
            return cross_layer_message
        data_frame = DataFrame(source_mac=source_mac, destination_mac=destination_mac,
                               type=cross_layer_message.data_others["type"]
                               , checksum=1234, payload=cross_layer_message.data)
        del cross_layer_message.data_others["type"]
        cross_layer_message.action = ActionType.ENCAPSULATE
        cross_layer_message.data = data_frame
        cross_layer_message.data_others["target_mac"] = destination_mac
        return cross_layer_message
