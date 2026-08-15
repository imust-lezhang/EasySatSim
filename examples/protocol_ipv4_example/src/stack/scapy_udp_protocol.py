"""Scapy-based standard UDP encapsulation and parsing."""

from scapy.layers.inet import UDP
from scapy.packet import Raw

from examples.protocol_ipv4_example.src.stack.scapy_udp_data import ScapyUDPData
from src.abstract.stack.protocol_func import AbstractProtocolFunc
from src.simulation.stack.cross_layer_message.cross_layer_message import (
    ActionType,
    CrossLayerMessage,
)


UDP_PROTOCOL_NUMBER = 17
IPV4_ETHERTYPE = 0x0800


class ScapyUDPProtocol(AbstractProtocolFunc):
    """Convert application bytes to and from a standards-formatted UDP datagram."""

    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage):
        udp_data = cross_layer_message.data
        if not isinstance(udp_data, ScapyUDPData):
            raise TypeError("ScapyUDPProtocol expects ScapyUDPData while parsing.")

        packet = UDP(udp_data.raw_bytes)
        cross_layer_message.data_others["udp_source_port"] = int(packet.sport)
        cross_layer_message.data_others["udp_destination_port"] = int(packet.dport)
        cross_layer_message.data = bytes(packet.payload)
        cross_layer_message.cross_layer_interface = int(packet.dport)
        cross_layer_message.action = ActionType.PARSE
        return cross_layer_message

    @staticmethod
    def encapsulate_func(entity, cross_layer_message: CrossLayerMessage):
        payload = cross_layer_message.data
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise TypeError("ScapyUDPProtocol expects application payload bytes.")

        source_port = int(cross_layer_message.data_others["source_port"])
        destination_port = int(cross_layer_message.data_others["target_port"])
        if not 0 <= source_port <= 65535:
            raise ValueError(f"Invalid UDP source port: {source_port}")
        if not 0 <= destination_port <= 65535:
            raise ValueError(f"Invalid UDP destination port: {destination_port}")

        packet = UDP(sport=source_port, dport=destination_port) / Raw(bytes(payload))
        raw_bytes = bytes(packet)
        cross_layer_message.data = ScapyUDPData.to_data(raw_bytes)
        del cross_layer_message.data_others["source_port"]
        del cross_layer_message.data_others["target_port"]
        cross_layer_message.data_others["protocol"] = UDP_PROTOCOL_NUMBER
        cross_layer_message.cross_layer_interface = IPV4_ETHERTYPE
        cross_layer_message.action = ActionType.ENCAPSULATE
        return cross_layer_message
