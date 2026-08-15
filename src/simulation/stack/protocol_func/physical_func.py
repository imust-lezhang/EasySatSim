from src.abstract.stack.protocol_func import AbstractProtocolFunc
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage, ActionType
from src.simulation.stack.protocol_data.physical_data import DataBinary


class PhyEthernet(AbstractProtocolFunc):
    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage):
        data_binary = cross_layer_message.data
        cross_layer_message.action = ActionType.PARSE
        cross_layer_message.data = data_binary
        cross_layer_message.cross_layer_interface = "Ethernet"
        return cross_layer_message

    @staticmethod
    def encapsulate_func(entity, cross_layer_message: CrossLayerMessage):
        data_binary = DataBinary(payload=cross_layer_message.data)
        cross_layer_message.data = data_binary
        return cross_layer_message

