from src.abstract.stack.protocol_data import AbstractProtocolData
from dataclasses import dataclass
import struct
import socket


@dataclass
class DataPacket(AbstractProtocolData):
    version: int
    header_length: int
    total_length: int
    identification: int
    ttl: int
    protocol: int
    header_checksum: int
    source_ip: str
    destination_ip: str
    payload: bytes


    @staticmethod
    def to_data(cross_layer_data):
        data_bytes = cross_layer_data.payload
        # Unpack the header
        unpacked_data = struct.unpack('>IIIIIIII4s4s', data_bytes[:40])
        version, header_length, total_length, identification, ttl, protocol, header_checksum, payload_length, source_ip, destination_ip = unpacked_data
        # Decode the IP address
        source_ip_decoded = socket.inet_ntoa(source_ip)
        destination_ip_decoded = socket.inet_ntoa(destination_ip)
        # Extract the payload
        payload = data_bytes[40:40 + payload_length]
        return DataPacket(version, header_length, total_length, identification, ttl, protocol, header_checksum,
                        source_ip_decoded, destination_ip_decoded, payload)


    @staticmethod
    def data_to(this_layer_data):
        # Encode the IP address as an integer in network byte order
        source_ip_encoded = socket.inet_aton(this_layer_data.source_ip)
        destination_ip_encoded = socket.inet_aton(this_layer_data.destination_ip)
        # Pack the data packet header
        header = struct.pack('>IIIIIIII4s4s', this_layer_data.version, this_layer_data.header_length,
                           this_layer_data.total_length, this_layer_data.identification, this_layer_data.ttl,
                           this_layer_data.protocol, this_layer_data.header_checksum, len(this_layer_data.payload),
                           source_ip_encoded, destination_ip_encoded)
        # Return the combination of header and payload
        return header + this_layer_data.payload



@dataclass
class NeighborInfo:
    satellite_id: int
    is_alive: bool
    delay: float
    load: float
    last_update_time: float
    source_ip: str
    destination_ip: str


    @staticmethod
    def data_to(this_layer_data):
        # Convert is_alive from boolean to integer
        is_alive_int = 1 if this_layer_data.is_alive else 0
        # Encode the IP address
        source_ip_encoded = socket.inet_aton(this_layer_data.source_ip)
        destination_ip_encoded = socket.inet_aton(this_layer_data.destination_ip)
        # Pack the data
        packed_data = struct.pack('>IIfff4s4s', this_layer_data.satellite_id, is_alive_int,
                              this_layer_data.delay, this_layer_data.load,
                              this_layer_data.last_update_time,
                              source_ip_encoded, destination_ip_encoded)
        return packed_data


    @staticmethod
    def to_data(cross_layer_data):
        data_bytes = cross_layer_data.payload
        # Unpack the data
        unpacked_data = struct.unpack('>IIfff4s4s', data_bytes)
        satellite_id = unpacked_data[0]
        is_alive = True if unpacked_data[1] == 1 else False
        delay = unpacked_data[2]
        load = unpacked_data[3]
        last_update_time = unpacked_data[4]
        source_ip = socket.inet_ntoa(unpacked_data[5])
        destination_ip = socket.inet_ntoa(unpacked_data[6])
        return NeighborInfo(satellite_id, is_alive, delay, load, last_update_time, source_ip, destination_ip)