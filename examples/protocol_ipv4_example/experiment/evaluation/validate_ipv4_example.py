"""End-to-end validation and JSON reporting for the IPv4/UDP example."""

import csv
import json
import sys
from pathlib import Path

from scapy.data import DLT_RAW
from scapy.layers.inet import IP, UDP
from scapy.packet import Raw
from scapy.utils import RawPcapReader, checksum, rdpcap

from configuration import simulation_config as cg
from src.tools.config_loader import load_configuration
from examples.protocol_ipv4_example.experiment.integration.ipv4_trace_logger import (
    TRACE_FIELDS,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]


if not hasattr(cg, "IPV4_EXAMPLE_VALIDATION_SUMMARY_PATH"):
    cg = load_configuration("examples/protocol_ipv4_example/src")


def _project_relative_path(path):
    """Return a portable repository-relative path for report serialization."""
    resolved_path = Path(path).resolve()
    try:
        return resolved_path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved_path.as_posix()


class ValidationReport:
    def __init__(self):
        self.assertions = {}

    def add(self, name, *, expected, observed, passed, details=None):
        item = {
            "expected": expected,
            "observed": observed,
            "status": "PASS" if passed else "FAIL",
        }
        if details is not None:
            item["details"] = details
        self.assertions[name] = item
        return passed

    def summary(self):
        failed = [
            name
            for name, result in self.assertions.items()
            if result["status"] != "PASS"
        ]
        return {
            "status": "PASS" if not failed else "FAIL",
            "forwarding_event_definition": (
                "One event for each non-destination satellite that executes "
                "IPv4 forwarding; destination-user delivery is not counted."
            ),
            "artifacts": {
                "delivery_result": _project_relative_path(
                    cg.IPV4_EXAMPLE_RESULT_FILE_PATH
                ),
                "hop_trace": _project_relative_path(
                    cg.IPV4_EXAMPLE_TRACE_FILE_PATH
                ),
                "source_pcap": _project_relative_path(
                    cg.IPV4_EXAMPLE_SOURCE_PCAP_PATH
                ),
                "destination_pcap": _project_relative_path(
                    cg.IPV4_EXAMPLE_DESTINATION_PCAP_PATH
                ),
            },
            "assertion_count": len(self.assertions),
            "passed_assertion_count": len(self.assertions) - len(failed),
            "failed_assertion_count": len(failed),
            "failed_assertions": failed,
            "assertions": self.assertions,
        }


def validate_ipv4_example(summary_path=None):
    report = ValidationReport()
    artifacts = _load_artifacts(report)

    if artifacts is not None:
        try:
            _validate_loaded_artifacts(report, **artifacts)
        except Exception as error:
            report.add(
                "validation_execution",
                expected="all end-to-end validation checks execute without error",
                observed=f"{type(error).__name__}: {error}",
                passed=False,
            )

    summary = report.summary()
    output_path = Path(summary_path or cg.IPV4_EXAMPLE_VALIDATION_SUMMARY_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_path.replace(output_path)
    summary["summary_file"] = _project_relative_path(output_path)
    return summary


def _load_artifacts(report):
    delivery_result = _load_json_artifact(
        report,
        name="delivery_result_readable",
        path=cg.IPV4_EXAMPLE_RESULT_FILE_PATH,
    )
    trace_rows = _load_trace_artifact(report)
    source_capture = _load_pcap_artifact(
        report,
        name="source_pcap_readable",
        path=cg.IPV4_EXAMPLE_SOURCE_PCAP_PATH,
    )
    destination_capture = _load_pcap_artifact(
        report,
        name="destination_pcap_readable",
        path=cg.IPV4_EXAMPLE_DESTINATION_PCAP_PATH,
    )
    if any(
        artifact is None
        for artifact in (
            delivery_result,
            trace_rows,
            source_capture,
            destination_capture,
        )
    ):
        return None
    return {
        "delivery_result": delivery_result,
        "trace_rows": trace_rows,
        "source_capture": source_capture,
        "destination_capture": destination_capture,
    }


def _load_json_artifact(report, *, name, path):
    artifact_path = Path(path)
    try:
        value = json.loads(artifact_path.read_text(encoding="utf-8"))
    except Exception as error:
        report.add(
            name,
            expected="existing readable JSON object",
            observed=f"{type(error).__name__}: {error}",
            passed=False,
        )
        return None
    report.add(
        name,
        expected="existing readable JSON object",
        observed=f"read {_project_relative_path(artifact_path)}",
        passed=isinstance(value, dict),
    )
    return value if isinstance(value, dict) else None


def _load_trace_artifact(report):
    trace_path = Path(cg.IPV4_EXAMPLE_TRACE_FILE_PATH)
    try:
        with trace_path.open("r", newline="", encoding="utf-8") as trace_file:
            reader = csv.DictReader(trace_file)
            fieldnames = tuple(reader.fieldnames or ())
            rows = list(reader)
    except Exception as error:
        report.add(
            "hop_trace_readable",
            expected="existing non-empty CSV trace",
            observed=f"{type(error).__name__}: {error}",
            passed=False,
        )
        return None
    passed = bool(rows) and fieldnames == TRACE_FIELDS
    report.add(
        "hop_trace_readable",
        expected="existing non-empty CSV trace with the documented schema",
        observed={
            "path": _project_relative_path(trace_path),
            "event_rows": len(rows),
            "fieldnames": list(fieldnames),
        },
        passed=passed,
    )
    return rows if passed else None


def _load_pcap_artifact(report, *, name, path):
    pcap_path = Path(path)
    try:
        raw_reader = RawPcapReader(str(pcap_path))
        try:
            linktype = raw_reader.linktype
            records = list(raw_reader)
        finally:
            raw_reader.close()
        packets = rdpcap(str(pcap_path))
        if len(records) != 1 or len(packets) != 1 or IP not in packets[0]:
            raise ValueError(
                f"records={len(records)}, parsed_packets={len(packets)}, "
                f"contains_ipv4={bool(packets and IP in packets[0])}"
            )
        raw_bytes, metadata = records[0]
        packet = packets[0][IP]
        if bytes(packet) != bytes(raw_bytes):
            raise ValueError("Scapy-parsed bytes differ from the PCAP record bytes")
        timestamp = float(metadata.sec) + float(metadata.usec) / 1_000_000
        if abs(float(packet.time) - timestamp) > 1e-6:
            raise ValueError("Scapy packet timestamp differs from PCAP metadata")
    except Exception as error:
        report.add(
            name,
            expected="one readable DLT_RAW IPv4 packet",
            observed=f"{type(error).__name__}: {error}",
            passed=False,
        )
        return None

    passed = linktype == DLT_RAW
    report.add(
        name,
        expected=f"one readable DLT_RAW({DLT_RAW}) IPv4 packet",
        observed={
            "path": _project_relative_path(pcap_path),
            "packet_count": len(records),
            "linktype": linktype,
        },
        passed=passed,
    )
    return {
        "path": str(pcap_path),
        "packet": packet,
        "raw_bytes": bytes(raw_bytes),
        "timestamp": timestamp,
        "linktype": linktype,
    }


def _validate_loaded_artifacts(
    report,
    *,
    delivery_result,
    trace_rows,
    source_capture,
    destination_capture,
):
    source_packet = source_capture["packet"]
    destination_packet = destination_capture["packet"]
    message_rows = [
        row
        for row in trace_rows
        if row.get("message_id") == cg.IPV4_EXAMPLE_MESSAGE_ID
    ]
    forwarding_rows = [row for row in message_rows if row.get("action") == "forward"]
    delivery_rows = [row for row in message_rows if row.get("action") == "deliver"]

    _add_delivery_result_assertions(report, delivery_result)
    _add_packet_format_assertions(report, source_packet, destination_packet)
    _add_udp_assertions(report, source_packet, destination_packet, delivery_result)
    _add_address_assertions(report, source_packet, destination_packet, delivery_result)
    _add_routing_assertions(report, forwarding_rows, delivery_rows)
    _add_ttl_assertions(
        report,
        source_packet,
        destination_packet,
        forwarding_rows,
        delivery_rows,
        delivery_result,
    )
    _add_checksum_assertion(
        report,
        source_capture["raw_bytes"],
        destination_capture["raw_bytes"],
        forwarding_rows,
    )
    _add_pcap_timestamp_assertion(report, source_capture, destination_capture)


def _add_delivery_result_assertions(report, delivery_result):
    expected_identity = {
        "status": "DELIVERED",
        "message_id": cg.IPV4_EXAMPLE_MESSAGE_ID,
        "source_user_id": cg.IPV4_EXAMPLE_SOURCE_USER_ID,
        "destination_user_id": cg.IPV4_EXAMPLE_DESTINATION_USER_ID,
        "source_access_satellite_id": (
            cg.IPV4_EXAMPLE_EXPECTED_SOURCE_ACCESS_SATELLITE_ID
        ),
        "destination_access_satellite_id": (
            cg.IPV4_EXAMPLE_EXPECTED_DESTINATION_ACCESS_SATELLITE_ID
        ),
    }
    observed_identity = {
        name: delivery_result.get(name) for name in expected_identity
    }
    report.add(
        "delivery_identity",
        expected=expected_identity,
        observed=observed_identity,
        passed=observed_identity == expected_identity,
    )


def _add_packet_format_assertions(report, source_packet, destination_packet):
    versions = [int(source_packet.version), int(destination_packet.version)]
    report.add(
        "ipv4_version",
        expected=[4, 4],
        observed=versions,
        passed=versions == [4, 4],
    )
    ihls = [int(source_packet.ihl), int(destination_packet.ihl)]
    report.add(
        "ipv4_ihl",
        expected="source and destination IHL >= 5",
        observed=ihls,
        passed=all(ihl >= 5 for ihl in ihls),
    )
    total_lengths = [int(source_packet.len), int(destination_packet.len)]
    serialized_lengths = [len(bytes(source_packet)), len(bytes(destination_packet))]
    report.add(
        "ipv4_total_length",
        expected=serialized_lengths,
        observed=total_lengths,
        passed=total_lengths == serialized_lengths,
    )
    protocols = [int(source_packet.proto), int(destination_packet.proto)]
    report.add(
        "ipv4_protocol",
        expected=[17, 17],
        observed=protocols,
        passed=protocols == [17, 17],
    )


def _add_udp_assertions(report, source_packet, destination_packet, delivery_result):
    ports = {
        "source_pcap": [int(source_packet[UDP].sport), int(source_packet[UDP].dport)],
        "destination_pcap": [
            int(destination_packet[UDP].sport),
            int(destination_packet[UDP].dport),
        ],
        "delivery_result": [
            delivery_result.get("source_port"),
            delivery_result.get("destination_port"),
        ],
    }
    expected_ports = [cg.IPV4_EXAMPLE_APPLICATION_PORT] * 2
    report.add(
        "udp_ports",
        expected={key: expected_ports for key in ports},
        observed=ports,
        passed=all(value == expected_ports for value in ports.values()),
    )
    source_payload = bytes(source_packet[Raw].load) if Raw in source_packet else b""
    destination_payload = (
        bytes(destination_packet[Raw].load) if Raw in destination_packet else b""
    )
    observed_payloads = {
        "source_pcap": source_payload.decode("utf-8", errors="replace"),
        "destination_pcap": destination_payload.decode("utf-8", errors="replace"),
        "delivery_result": delivery_result.get("payload"),
    }
    report.add(
        "payload_end_to_end",
        expected=cg.IPV4_EXAMPLE_PAYLOAD,
        observed=observed_payloads,
        passed=all(
            payload == cg.IPV4_EXAMPLE_PAYLOAD
            for payload in observed_payloads.values()
        ),
    )
    report.add(
        "udp_datagram_preserved",
        expected="identical serialized UDP bytes at source and destination",
        observed={
            "source_length": len(bytes(source_packet[UDP])),
            "destination_length": len(bytes(destination_packet[UDP])),
        },
        passed=bytes(source_packet[UDP]) == bytes(destination_packet[UDP]),
    )


def _add_address_assertions(report, source_packet, destination_packet, delivery_result):
    source_addresses = {
        "source_pcap": source_packet.src,
        "destination_pcap": destination_packet.src,
        "delivery_result": delivery_result.get("source_ip"),
    }
    report.add(
        "source_ip_unchanged",
        expected=source_packet.src,
        observed=source_addresses,
        passed=len(set(source_addresses.values())) == 1,
    )
    destination_addresses = {
        "source_pcap": source_packet.dst,
        "destination_pcap": destination_packet.dst,
        "delivery_result": delivery_result.get("destination_ip"),
    }
    report.add(
        "destination_ip_unchanged",
        expected=source_packet.dst,
        observed=destination_addresses,
        passed=len(set(destination_addresses.values())) == 1,
    )


def _add_routing_assertions(report, forwarding_rows, delivery_rows):
    entity_types = [row.get("entity_type") for row in forwarding_rows]
    report.add(
        "satellite_forwarding_event_count",
        expected=">= 2 satellite forwarding events",
        observed={
            "count": len(forwarding_rows),
            "satellite_path": [int(row["entity_id"]) for row in forwarding_rows],
            "entity_types": entity_types,
        },
        passed=len(forwarding_rows) >= 2
        and all(entity_type == "satellite" for entity_type in entity_types),
    )
    report.add(
        "destination_delivery_event_count",
        expected="exactly 1 user delivery event",
        observed={
            "count": len(delivery_rows),
            "entities": [
                f"{row.get('entity_type')}:{row.get('entity_id')}"
                for row in delivery_rows
            ],
        },
        passed=len(delivery_rows) == 1
        and delivery_rows[0].get("entity_type") == "user",
    )
    continuity = []
    all_rows = forwarding_rows + delivery_rows
    for previous, current in zip(all_rows, all_rows[1:]):
        expected_next = f"{current.get('entity_type')}:{current.get('entity_id')}"
        continuity.append(
            {
                "from": f"{previous.get('entity_type')}:{previous.get('entity_id')}",
                "recorded_next": previous.get("next_hop_entity"),
                "expected_next": expected_next,
                "status": (
                    "PASS"
                    if previous.get("next_hop_entity") == expected_next
                    else "FAIL"
                ),
            }
        )
    report.add(
        "next_hop_continuity",
        expected="each next_hop_entity equals the following processing entity",
        observed=continuity,
        passed=bool(continuity)
        and all(item["status"] == "PASS" for item in continuity),
    )
    path = [int(row["entity_id"]) for row in forwarding_rows]
    expected_endpoints = [
        cg.IPV4_EXAMPLE_EXPECTED_SOURCE_ACCESS_SATELLITE_ID,
        cg.IPV4_EXAMPLE_EXPECTED_DESTINATION_ACCESS_SATELLITE_ID,
    ]
    report.add(
        "satellite_path_endpoints",
        expected=expected_endpoints,
        observed=[path[0], path[-1]] if path else [],
        passed=bool(path)
        and path[0] == expected_endpoints[0]
        and path[-1] == expected_endpoints[1],
    )
    trace_semantics = [
        {
            "entity": f"{row.get('entity_type')}:{row.get('entity_id')}",
            "protocol": row.get("protocol"),
            "simulation_time": row.get("simulation_time"),
        }
        for row in all_rows
    ]
    times = [float(row["simulation_time"]) for row in all_rows]
    report.add(
        "trace_event_semantics",
        expected=(
            "satellite forward rows followed by one user delivery row, all "
            "using protocol 17 in nondecreasing simulation-time order"
        ),
        observed=trace_semantics,
        passed=bool(forwarding_rows)
        and len(delivery_rows) == 1
        and all(row.get("entity_type") == "satellite" for row in forwarding_rows)
        and delivery_rows[0].get("entity_type") == "user"
        and all(int(row["protocol"]) == 17 for row in all_rows)
        and times == sorted(times),
    )


def _add_ttl_assertions(
    report,
    source_packet,
    destination_packet,
    forwarding_rows,
    delivery_rows,
    delivery_result,
):
    transitions = [
        {
            "entity_id": int(row["entity_id"]),
            "ttl_before": int(row["ttl_before"]),
            "ttl_after": int(row["ttl_after"]),
        }
        for row in forwarding_rows
    ]
    report.add(
        "per_hop_ttl_decrement",
        expected="ttl_after = ttl_before - 1 at every satellite forwarding event",
        observed=transitions,
        passed=bool(transitions)
        and all(
            item["ttl_after"] == item["ttl_before"] - 1 for item in transitions
        ),
    )
    delivery_transition = (
        {
            "ttl_before": int(delivery_rows[0]["ttl_before"]),
            "ttl_after": int(delivery_rows[0]["ttl_after"]),
        }
        if len(delivery_rows) == 1
        else None
    )
    report.add(
        "destination_does_not_decrement_ttl",
        expected="delivery ttl_before == ttl_after",
        observed=delivery_transition,
        passed=delivery_transition is not None
        and delivery_transition["ttl_before"] == delivery_transition["ttl_after"],
    )
    forwarding_count = len(forwarding_rows)
    ttl_observation = {
        "initial_ttl_source_pcap": int(source_packet.ttl),
        "final_ttl_destination_pcap": int(destination_packet.ttl),
        "final_ttl_delivery_result": delivery_result.get("final_ttl"),
        "forwarding_event_count": forwarding_count,
    }
    report.add(
        "ttl_matches_forwarding_count",
        expected=(
            "initial_ttl - final_ttl == forwarding_event_count and delivery "
            "result final TTL matches destination PCAP"
        ),
        observed=ttl_observation,
        passed=(
            int(source_packet.ttl) - int(destination_packet.ttl)
            == forwarding_count
            and delivery_result.get("final_ttl") == int(destination_packet.ttl)
            and delivery_result.get("forwarding_count") == forwarding_count
        ),
    )


def _add_checksum_assertion(
    report,
    source_raw_bytes,
    destination_raw_bytes,
    forwarding_rows,
):
    packet = IP(source_raw_bytes)
    hop_results = []
    for row in forwarding_rows:
        expected_before = int(packet.chksum)
        ttl_before = int(packet.ttl)
        header_valid_before = _ipv4_header_checksum_valid(packet)

        packet.ttl = ttl_before - 1
        del packet.chksum
        recalculated_packet = IP(bytes(packet))
        expected_after = int(recalculated_packet.chksum)
        header_valid_after = _ipv4_header_checksum_valid(recalculated_packet)

        recorded_before = int(row["checksum_before"], 16)
        recorded_after = int(row["checksum_after"], 16)
        hop_passed = (
            int(row["ttl_before"]) == ttl_before
            and int(row["ttl_after"]) == int(recalculated_packet.ttl)
            and recorded_before == expected_before
            and recorded_after == expected_after
            and header_valid_before
            and header_valid_after
        )
        hop_results.append(
            {
                "entity_id": int(row["entity_id"]),
                "ttl_before": ttl_before,
                "ttl_after": int(recalculated_packet.ttl),
                "recorded_checksum_before": f"0x{recorded_before:04x}",
                "scapy_expected_checksum_before": f"0x{expected_before:04x}",
                "recorded_checksum_after": f"0x{recorded_after:04x}",
                "scapy_recalculated_checksum_after": f"0x{expected_after:04x}",
                "header_checksum_valid_before": header_valid_before,
                "header_checksum_valid_after": header_valid_after,
                "status": "PASS" if hop_passed else "FAIL",
            }
        )
        packet = recalculated_packet

    final_bytes_match = bytes(packet) == bytes(destination_raw_bytes)
    report.add(
        "per_hop_ipv4_checksum_recalculation",
        expected=(
            "each recorded checksum equals an independent Scapy recalculation, "
            "each IPv4 header checksum verifies, and the rebuilt final packet "
            "equals the destination PCAP"
        ),
        observed={
            "hops": hop_results,
            "rebuilt_final_packet_matches_destination_pcap": final_bytes_match,
        },
        passed=bool(hop_results)
        and all(item["status"] == "PASS" for item in hop_results)
        and final_bytes_match,
    )


def _ipv4_header_checksum_valid(packet):
    raw_bytes = bytes(packet)
    header_length = int(packet.ihl) * 4
    return checksum(raw_bytes[:header_length]) == 0


def _add_pcap_timestamp_assertion(report, source_capture, destination_capture):
    source_simulation_time = (
        source_capture["timestamp"] - cg.IPV4_EXAMPLE_PCAP_BASE_EPOCH
    )
    destination_simulation_time = (
        destination_capture["timestamp"] - cg.IPV4_EXAMPLE_PCAP_BASE_EPOCH
    )
    observed = {
        "base_epoch": cg.IPV4_EXAMPLE_PCAP_BASE_EPOCH,
        "source_pcap_timestamp": source_capture["timestamp"],
        "source_simulation_time": source_simulation_time,
        "destination_pcap_timestamp": destination_capture["timestamp"],
        "destination_simulation_time": destination_simulation_time,
    }
    report.add(
        "pcap_timestamp_mapping",
        expected=(
            "pcap_timestamp = BASE_EPOCH + non-negative simulation_time; "
            "destination timestamp >= source timestamp"
        ),
        observed=observed,
        passed=source_simulation_time >= 0
        and destination_simulation_time >= source_simulation_time,
    )


def main():
    summary = validate_ipv4_example()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
