"""Standards-formatted UDP data carried between EasySatSim stack layers."""

from dataclasses import dataclass

from scapy.layers.inet import UDP

from src.abstract.stack.protocol_data import AbstractProtocolData


UDP_HEADER_LENGTH = 8


@dataclass
class ScapyUDPData(AbstractProtocolData):
    """Keep serialized UDP bytes as the authoritative representation."""

    raw_bytes: bytes

    @staticmethod
    def to_data(cross_layer_data):
        if not isinstance(cross_layer_data, (bytes, bytearray, memoryview)):
            raise TypeError("ScapyUDPData expects serialized UDP bytes.")

        raw_bytes = bytes(cross_layer_data)
        if len(raw_bytes) < UDP_HEADER_LENGTH:
            raise ValueError("Serialized UDP data is shorter than the 8-byte header.")

        packet = UDP(raw_bytes)
        if packet.len != len(raw_bytes):
            raise ValueError(
                f"UDP length field is {packet.len}, but {len(raw_bytes)} bytes were provided."
            )
        return ScapyUDPData(raw_bytes=raw_bytes)

    @staticmethod
    def data_to(this_layer_data):
        if not isinstance(this_layer_data, ScapyUDPData):
            raise TypeError("Expected a ScapyUDPData instance.")
        return bytes(this_layer_data.raw_bytes)
