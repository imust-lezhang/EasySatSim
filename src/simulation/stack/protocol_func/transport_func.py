from src.abstract.stack.protocol_func import AbstractProtocolFunc
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage, ActionType
from src.simulation.stack.protocol_data.transport_data import DataSegment


class Protocol0x0006(AbstractProtocolFunc):
    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage):
        # 计算指标
        data_segment: DataSegment = cross_layer_message.data
        cross_layer_message.action = ActionType.PARSE
        cross_layer_message.cross_layer_interface = data_segment.destination_port
        cross_layer_message.data = data_segment.payload
        return cross_layer_message

    @staticmethod
    def encapsulate_func(entity, cross_layer_message: CrossLayerMessage):
        source_port = cross_layer_message.data_others["source_port"]
        destination_port = cross_layer_message.data_others["target_port"]
        out_type = 0x0800
        data_segment = DataSegment(source_port=source_port, destination_port=destination_port, length=10, checksum=4321
                                   , payload=cross_layer_message.data)
        cross_layer_message.action = ActionType.ENCAPSULATE
        cross_layer_message.cross_layer_interface = out_type
        cross_layer_message.data = data_segment
        del cross_layer_message.data_others["source_port"]
        del cross_layer_message.data_others["target_port"]
        cross_layer_message.data_others["protocol"] = 0x0006
        return cross_layer_message
