"""Scapy-based standard IPv4 encapsulation and forwarding logic."""

from collections import deque

from scapy.layers.inet import IP

from configuration import simulation_config as cg
from examples.protocol_ipv4_example.experiment.integration.ipv4_trace_logger import (
    append_ipv4_trace,
)
from examples.protocol_ipv4_example.experiment.integration.pcap_writer import (
    write_raw_ipv4_pcap,
)
from examples.protocol_ipv4_example.src.stack.scapy_ipv4_data import ScapyIPv4Data
from examples.protocol_ipv4_example.src.stack.scapy_udp_protocol import (
    IPV4_ETHERTYPE,
    UDP_PROTOCOL_NUMBER,
)
from src.abstract.stack.protocol_func import AbstractProtocolFunc
from src.simulation.stack.cross_layer_message.cross_layer_message import (
    ActionType,
    CrossLayerMessage,
)
from src.simulation.stack.protocol_func.network_func import Type0x0800
from src.simulation.variable.performance import NetworkPerformance
from src.simulation.variable.virtual_store import VirtualStore


DEFAULT_INITIAL_TTL = 64
DEFAULT_IDENTIFICATION = 1
LINK_LAYER_INTERFACE = "Ethernet"


class ScapyIPv4Protocol(AbstractProtocolFunc):
    """Process standard IPv4 bytes while reusing EasySatSim forwarding state."""

    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage):
        ipv4_data = cross_layer_message.data
        if not isinstance(ipv4_data, ScapyIPv4Data):
            raise TypeError("ScapyIPv4Protocol expects ScapyIPv4Data while parsing.")

        packet = IP(ipv4_data.raw_bytes)
        _record_ipv4_identity(cross_layer_message, packet)

        if packet.dst == entity.ip_address:
            _write_scenario_pcap(
                path=getattr(cg, "IPV4_EXAMPLE_DESTINATION_PCAP_PATH", None),
                entity=entity,
                cross_layer_message=cross_layer_message,
                raw_bytes=ipv4_data.raw_bytes,
            )
            delivery_checksum = int(packet.chksum)
            _append_scenario_trace(
                entity=entity,
                cross_layer_message=cross_layer_message,
                packet=packet,
                ttl_before=int(packet.ttl),
                ttl_after=int(packet.ttl),
                checksum_before=delivery_checksum,
                checksum_after=delivery_checksum,
                action="deliver",
            )
            cross_layer_message.data = bytes(packet.payload)
            cross_layer_message.cross_layer_interface = int(packet.proto)
            cross_layer_message.action = ActionType.PARSE
            cross_layer_message.data_others["ipv4_delivery_ttl"] = int(packet.ttl)
            return cross_layer_message

        if _is_forwarding_loop(entity, cross_layer_message):
            _trace_drop(
                entity=entity,
                cross_layer_message=cross_layer_message,
                packet=packet,
                action="drop_loop",
            )
            return _drop_packet(
                cross_layer_message,
                reason="ipv4 forwarding loop detected",
            )

        ttl_before = int(packet.ttl)
        if ttl_before <= 1:
            _trace_drop(
                entity=entity,
                cross_layer_message=cross_layer_message,
                packet=packet,
                action="drop_ttl_expired",
                ttl_after=None,
                checksum_after=None,
            )
            return _drop_packet(
                cross_layer_message,
                reason="ipv4 ttl expired",
            )

        checksum_before = int(packet.chksum)
        packet.ttl = ttl_before - 1
        del packet.chksum
        forwarded_raw_bytes = bytes(packet)
        forwarded_packet = IP(forwarded_raw_bytes)
        forwarded_data = ScapyIPv4Data.to_data(forwarded_raw_bytes)

        cross_layer_message.data = forwarded_data
        next_hop_ip = _resolve_next_hop(
            entity=entity,
            cross_layer_message=cross_layer_message,
            destination_ip=forwarded_packet.dst,
        )
        if next_hop_ip is None:
            return cross_layer_message

        _append_scenario_trace(
            entity=entity,
            cross_layer_message=cross_layer_message,
            packet=forwarded_packet,
            ttl_before=ttl_before,
            ttl_after=int(forwarded_packet.ttl),
            checksum_before=checksum_before,
            checksum_after=int(forwarded_packet.chksum),
            next_hop_ip=next_hop_ip,
            action="forward",
        )

        cross_layer_message.data_others["ipv4_forwarding_count"] = (
            int(cross_layer_message.data_others.get("ipv4_forwarding_count", 0)) + 1
        )
        cross_layer_message.data_others["next_hop_ip"] = next_hop_ip
        cross_layer_message.data_others["type"] = IPV4_ETHERTYPE
        cross_layer_message.cross_layer_interface = LINK_LAYER_INTERFACE
        cross_layer_message.action = ActionType.ENCAPSULATE
        return cross_layer_message

    @staticmethod
    def encapsulate_func(entity, cross_layer_message: CrossLayerMessage):
        udp_payload = cross_layer_message.data
        if not isinstance(udp_payload, (bytes, bytearray, memoryview)):
            raise TypeError("ScapyIPv4Protocol expects serialized UDP bytes.")

        source_ip = cross_layer_message.data_others["source_ip"]
        destination_ip = cross_layer_message.data_others["target_ip"]
        protocol = int(cross_layer_message.data_others["protocol"])
        if protocol != UDP_PROTOCOL_NUMBER:
            raise ValueError(
                f"This example expects IPv4 protocol 17 (UDP), received {protocol}."
            )

        initial_ttl = int(
            cross_layer_message.data_others.pop(
                "ipv4_initial_ttl",
                DEFAULT_INITIAL_TTL,
            )
        )
        if not 1 <= initial_ttl <= 255:
            raise ValueError(f"Invalid IPv4 initial TTL: {initial_ttl}")
        identification = int(
            cross_layer_message.data_others.pop(
                "ipv4_identification",
                DEFAULT_IDENTIFICATION,
            )
        )
        if not 0 <= identification <= 65535:
            raise ValueError(f"Invalid IPv4 identification: {identification}")

        packet = IP(
            version=4,
            ihl=5,
            src=source_ip,
            dst=destination_ip,
            ttl=initial_ttl,
            id=identification,
            proto=protocol,
        ) / bytes(udp_payload)
        ipv4_data = ScapyIPv4Data.to_data(bytes(packet))
        parsed_packet = IP(ipv4_data.raw_bytes)

        _write_scenario_pcap(
            path=getattr(cg, "IPV4_EXAMPLE_SOURCE_PCAP_PATH", None),
            entity=entity,
            cross_layer_message=cross_layer_message,
            raw_bytes=ipv4_data.raw_bytes,
        )

        del cross_layer_message.data_others["source_ip"]
        del cross_layer_message.data_others["target_ip"]
        del cross_layer_message.data_others["protocol"]
        cross_layer_message.data = ipv4_data
        cross_layer_message.data_others["type"] = IPV4_ETHERTYPE
        cross_layer_message.data_others["ipv4_initial_ttl"] = int(parsed_packet.ttl)
        cross_layer_message.data_others["ipv4_forwarding_count"] = 0
        cross_layer_message.cross_layer_interface = LINK_LAYER_INTERFACE
        cross_layer_message.action = ActionType.ENCAPSULATE
        return cross_layer_message


def _record_ipv4_identity(cross_layer_message, packet):
    cross_layer_message.data_others["ipv4_source_ip"] = packet.src
    cross_layer_message.data_others["ipv4_destination_ip"] = packet.dst
    cross_layer_message.data_others["ipv4_protocol"] = int(packet.proto)


def _is_forwarding_loop(entity, cross_layer_message):
    ip_list = cross_layer_message.data_others.get("ip_list")
    if ip_list is None:
        ip_list = deque()
        cross_layer_message.data_others["ip_list"] = ip_list
    if entity.ip_address in ip_list:
        return True
    ip_list.append(entity.ip_address)
    return False


def _resolve_next_hop(entity, cross_layer_message, destination_ip):
    route_entry = entity.routing_table.get(destination_ip)
    if route_entry is not None:
        return route_entry["next_hop_ip"]

    destination_satellite_ip = _resolve_destination_satellite_ip(
        cross_layer_message=cross_layer_message,
        destination_ip=destination_ip,
    )
    if destination_satellite_ip is None:
        return None

    destination_satellite_id = VirtualStore.satellite_ip_to_id_table.get(
        destination_satellite_ip
    )
    if destination_satellite_id is None:
        return _drop_and_return_none(
            cross_layer_message,
            reason="ipv4 destination satellite has no id mapping",
        )

    next_satellite_id = Type0x0800.routing_algorithm_func(
        entity=entity,
        cross_layer_message=cross_layer_message,
        src_satellite_id=entity.entity_id,
        dst_satellite_id=destination_satellite_id,
    )
    if next_satellite_id is None:
        return _drop_and_return_none(
            cross_layer_message,
            reason="ipv4 routing returned no next satellite",
        )

    next_hop_ip = VirtualStore.satellite_id_to_ip_table.get(next_satellite_id)
    if next_hop_ip is None:
        return _drop_and_return_none(
            cross_layer_message,
            reason="ipv4 next satellite has no ip mapping",
        )

    entity.update_routing_table(
        destination_ip=destination_ip,
        next_hop_ip=next_hop_ip,
    )
    return next_hop_ip


def _resolve_destination_satellite_ip(cross_layer_message, destination_ip):
    user_ips = VirtualStore.set_user_ip or set()
    satellite_ips = VirtualStore.set_satellite_ip or set()

    if destination_ip in user_ips:
        destination_satellite_ip = VirtualStore.user_access_table.get(destination_ip)
        if destination_satellite_ip is None:
            return _drop_and_return_none(
                cross_layer_message,
                reason="ipv4 destination user has no access satellite",
            )
        return destination_satellite_ip

    if destination_ip in satellite_ips:
        return destination_ip

    return _drop_and_return_none(
        cross_layer_message,
        reason="ipv4 destination address is unknown to EasySatSim",
    )


def _drop_and_return_none(cross_layer_message, reason):
    _drop_packet(cross_layer_message, reason=reason)
    return None


def _drop_packet(cross_layer_message, reason):
    cross_layer_message.action = ActionType.STOP
    cross_layer_message.data_others["ipv4_drop_reason"] = reason
    NetworkPerformance.packet_loss(
        data_size_byte=cross_layer_message.data_others.get("data_size_byte", 0),
        reason=reason,
    )
    return cross_layer_message


def _trace_drop(
    *,
    entity,
    cross_layer_message,
    packet,
    action,
    ttl_after=None,
    checksum_after=None,
):
    _append_scenario_trace(
        entity=entity,
        cross_layer_message=cross_layer_message,
        packet=packet,
        ttl_before=int(packet.ttl),
        ttl_after=ttl_after,
        checksum_before=int(packet.chksum),
        checksum_after=checksum_after,
        action=action,
    )


def _append_scenario_trace(*, entity, cross_layer_message, packet, **event):
    message_id = cross_layer_message.data_others.get("message_id", "")
    trace_path = getattr(cg, "IPV4_EXAMPLE_TRACE_FILE_PATH", None)
    if not message_id or not trace_path:
        return None
    return append_ipv4_trace(
        path=trace_path,
        entity=entity,
        packet=packet,
        message_id=message_id,
        **event,
    )


def _write_scenario_pcap(*, path, entity, cross_layer_message, raw_bytes):
    message_id = cross_layer_message.data_others.get("message_id", "")
    base_epoch = getattr(cg, "IPV4_EXAMPLE_PCAP_BASE_EPOCH", None)
    if not message_id or not path or base_epoch is None:
        return None
    current_time = getattr(entity, "current_time", None)
    simulation_time = float(current_time[0]) if current_time is not None else 0.0
    return write_raw_ipv4_pcap(
        path=path,
        raw_bytes=raw_bytes,
        simulation_time=simulation_time,
        base_epoch=base_epoch,
    )
