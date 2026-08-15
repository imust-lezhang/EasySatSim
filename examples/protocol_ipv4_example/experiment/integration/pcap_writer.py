"""Offline raw-IPv4 PCAP export for the protocol integration example."""

import math
import threading
from pathlib import Path

from scapy.data import DLT_RAW
from scapy.layers.inet import IP
from scapy.utils import RawPcapWriter


PCAP_LINKTYPE = DLT_RAW
PCAP_LINKTYPE_NAME = "DLT_RAW"
_PCAP_LOCK = threading.Lock()


def prepare_ipv4_pcaps(*paths):
    """Remove artifacts from a previous run without creating empty PCAPs."""
    prepared_paths = []
    for path in paths:
        pcap_path = Path(path)
        pcap_path.parent.mkdir(parents=True, exist_ok=True)
        pcap_path.unlink(missing_ok=True)
        prepared_paths.append(pcap_path)
    return tuple(prepared_paths)


def write_raw_ipv4_pcap(*, path, raw_bytes, simulation_time, base_epoch):
    """Write one raw IPv4 packet with BASE_EPOCH + simulation time."""
    packet_bytes = bytes(raw_bytes)
    packet = IP(packet_bytes)
    if int(packet.version) != 4:
        raise ValueError("PCAP export expects a standards-formatted IPv4 packet.")
    if bytes(packet) != packet_bytes:
        raise ValueError("IPv4 bytes changed during PCAP export validation.")

    timestamp = float(base_epoch) + float(simulation_time)
    seconds = math.floor(timestamp)
    microseconds = round((timestamp - seconds) * 1_000_000)
    if microseconds == 1_000_000:
        seconds += 1
        microseconds = 0

    pcap_path = Path(path)
    pcap_path.parent.mkdir(parents=True, exist_ok=True)
    with _PCAP_LOCK:
        writer = RawPcapWriter(
            str(pcap_path),
            linktype=PCAP_LINKTYPE,
            sync=True,
        )
        try:
            writer.write_header(packet_bytes)
            writer.write_packet(
                packet_bytes,
                sec=seconds,
                usec=microseconds,
                caplen=len(packet_bytes),
                wirelen=len(packet_bytes),
            )
        finally:
            writer.close()
    return {
        "path": str(pcap_path),
        "linktype": PCAP_LINKTYPE,
        "linktype_name": PCAP_LINKTYPE_NAME,
        "simulation_time": float(simulation_time),
        "base_epoch": float(base_epoch),
        "pcap_timestamp": timestamp,
        "packet_length": len(packet_bytes),
    }
