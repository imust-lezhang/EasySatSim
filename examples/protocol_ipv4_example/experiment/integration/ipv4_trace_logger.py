"""CSV logger for actual Scapy IPv4 processing events in the simulator."""

import csv
import threading
from pathlib import Path

from src.simulation.variable.virtual_store import VirtualStore


TRACE_FIELDS = (
    "simulation_time",
    "entity_id",
    "entity_type",
    "src_ip",
    "dst_ip",
    "protocol",
    "ttl_before",
    "ttl_after",
    "checksum_before",
    "checksum_after",
    "next_hop_ip",
    "next_hop_entity",
    "action",
    "message_id",
)

_TRACE_LOCK = threading.Lock()


def prepare_ipv4_trace(path):
    """Create a fresh trace with the fixed Step 9 schema."""
    trace_path = Path(path)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with _TRACE_LOCK:
        with trace_path.open("w", newline="", encoding="utf-8") as trace_file:
            csv.DictWriter(trace_file, fieldnames=TRACE_FIELDS).writeheader()
    return trace_path


def append_ipv4_trace(
    *,
    path,
    entity,
    packet,
    ttl_before,
    ttl_after,
    checksum_before,
    checksum_after,
    next_hop_ip="",
    action,
    message_id,
):
    """Append one forwarding, delivery, or drop event."""
    row = {
        "simulation_time": _simulation_time(entity),
        "entity_id": getattr(entity, "entity_id", ""),
        "entity_type": getattr(entity, "entity_category", ""),
        "src_ip": packet.src,
        "dst_ip": packet.dst,
        "protocol": int(packet.proto),
        "ttl_before": _optional_integer(ttl_before),
        "ttl_after": _optional_integer(ttl_after),
        "checksum_before": _format_checksum(checksum_before),
        "checksum_after": _format_checksum(checksum_after),
        "next_hop_ip": next_hop_ip or "",
        "next_hop_entity": _entity_label_for_ip(next_hop_ip),
        "action": action,
        "message_id": message_id,
    }
    trace_path = Path(path)
    with _TRACE_LOCK:
        with trace_path.open("a", newline="", encoding="utf-8") as trace_file:
            writer = csv.DictWriter(trace_file, fieldnames=TRACE_FIELDS)
            writer.writerow(row)
            trace_file.flush()
    return row


def _simulation_time(entity):
    current_time = getattr(entity, "current_time", None)
    if current_time is None:
        return 0.0
    return round(float(current_time[0]), 6)


def _optional_integer(value):
    return "" if value is None else int(value)


def _format_checksum(value):
    return "" if value is None else f"0x{int(value):04x}"


def _entity_label_for_ip(ip_address):
    if not ip_address:
        return ""
    satellite_id = VirtualStore.satellite_ip_to_id_table.get(ip_address)
    if satellite_id is not None:
        return f"satellite:{satellite_id}"
    user_id = VirtualStore.user_ip_to_id_table.get(ip_address)
    if user_id is not None:
        return f"user:{user_id}"
    return "unknown"
