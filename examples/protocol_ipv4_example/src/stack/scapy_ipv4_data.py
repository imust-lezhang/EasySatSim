"""Standards-formatted IPv4 data carried between EasySatSim stack layers."""

from dataclasses import dataclass

from scapy.layers.inet import IP

from src.abstract.stack.protocol_data import AbstractProtocolData


IPV4_MIN_HEADER_LENGTH_BYTES = 20
IPV4_VERSION = 4


def _internet_checksum(data):
    """Return the 16-bit Internet checksum for an even- or odd-length buffer."""
    if len(data) % 2:
        data += b"\x00"
    total = 0
    for index in range(0, len(data), 2):
        total += (data[index] << 8) | data[index + 1]
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def _extract_ipv4_bytes(cross_layer_data):
    """Accept direct bytes or the payload of a lower-layer EasySatSim frame."""
    if isinstance(cross_layer_data, (bytes, bytearray, memoryview)):
        return bytes(cross_layer_data)

    payload = getattr(cross_layer_data, "payload", None)
    if isinstance(payload, (bytes, bytearray, memoryview)):
        return bytes(payload)
    raise TypeError(
        "ScapyIPv4Data expects serialized IPv4 bytes or a lower-layer object "
        "whose payload contains serialized IPv4 bytes."
    )


@dataclass
class ScapyIPv4Data(AbstractProtocolData):
    """Keep serialized IPv4 bytes as the authoritative representation."""

    raw_bytes: bytes

    @staticmethod
    def to_data(cross_layer_data):
        raw_bytes = _extract_ipv4_bytes(cross_layer_data)
        if len(raw_bytes) < IPV4_MIN_HEADER_LENGTH_BYTES:
            raise ValueError("Serialized IPv4 data is shorter than 20 bytes.")

        packet = IP(raw_bytes)
        if packet.version != IPV4_VERSION:
            raise ValueError(f"Expected IPv4 version 4, received {packet.version}.")
        if packet.ihl != 5:
            raise ValueError(
                f"This example supports IPv4 IHL 5 without options; received {packet.ihl}."
            )
        if int(packet.frag) != 0 or bool(packet.flags.MF):
            raise ValueError("IPv4 fragmentation/reassembly is not supported.")

        header_length = int(packet.ihl) * 4
        if header_length > len(raw_bytes):
            raise ValueError(
                f"IPv4 header requires {header_length} bytes, but only "
                f"{len(raw_bytes)} bytes were provided."
            )
        if packet.len != len(raw_bytes):
            raise ValueError(
                f"IPv4 total-length field is {packet.len}, but "
                f"{len(raw_bytes)} bytes were provided."
            )
        if packet.chksum is None:
            raise ValueError("IPv4 header checksum is missing.")
        if _internet_checksum(raw_bytes[:header_length]) != 0:
            raise ValueError("IPv4 header checksum validation failed.")

        return ScapyIPv4Data(raw_bytes=raw_bytes)

    @staticmethod
    def data_to(this_layer_data):
        if not isinstance(this_layer_data, ScapyIPv4Data):
            raise TypeError("Expected a ScapyIPv4Data instance.")
        return bytes(this_layer_data.raw_bytes)
