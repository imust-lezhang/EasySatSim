from src.abstract.stack.protocol_data import AbstractProtocolData
from dataclasses import dataclass
import struct


@dataclass
class DataSegment(AbstractProtocolData):
    source_port: int
    destination_port: int
    length: int
    checksum: int
    payload: bytes


    @staticmethod
    def to_data(cross_layer_data):
        data_bytes = cross_layer_data.payload
        source_port, destination_port, length, checksum = struct.unpack('!HHHH', data_bytes[:8])
        # Extract the data part
        udp_data = data_bytes[8:]
        return DataSegment(source_port, destination_port, length, checksum, udp_data)


    @staticmethod
    def data_to(this_layer_data):
        header = struct.pack('!HHHH', this_layer_data.source_port, this_layer_data.destination_port, this_layer_data.length,
                           this_layer_data.checksum)
        # Combine the header and data
        return header + this_layer_data.payload