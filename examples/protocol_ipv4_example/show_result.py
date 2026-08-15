"""Present the protocol-registration and end-to-end IPv4/UDP evidence."""

import csv
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.config_loader import load_configuration

load_configuration("examples/protocol_ipv4_example/src")

from configuration import simulation_config as cg
from examples.protocol_ipv4_example.example_setup import register_ipv4_udp_stack
from src.simulation.manager.stack_manager import StackManager


CASE_ROOT = Path(__file__).resolve().parent
FIGURE_PATH = CASE_ROOT / "experiment" / "output" / "PROTOCOL_IPV4_RESULT.png"


def main():
    delivery, trace_rows, source_packet, destination_packet = _load_evidence()
    default_stack, example_stack = _stack_snapshots()

    print("\n=== 1. Protocol Stack: Default vs IPv4 Example ===")
    _print_table(
        (
            "Layer",
            "Interface",
            "Default handler",
            "Default data",
            "Example handler",
            "Example data",
        ),
        (
            (
                "Application",
                "18080",
                *default_stack["application"],
                *example_stack["application"],
            ),
            (
                "Transport",
                "17",
                *default_stack["transport"],
                *example_stack["transport"],
            ),
            (
                "Network",
                "0x0800",
                *default_stack["network"],
                *example_stack["network"],
            ),
            (
                "Link",
                "Ethernet",
                *default_stack["link"],
                *example_stack["link"],
            ),
            (
                "Physical",
                "Ethernet",
                *default_stack["physical"],
                *example_stack["physical"],
            ),
        ),
    )
    print(
        "\nResult: UDP/17 and Scapy IPv4 are registered only in the example "
        "manager; the default manager remains unchanged."
    )

    print("\n=== 2. Standard IPv4/UDP Packet: Source vs Destination ===")
    packet_rows = _packet_rows(source_packet, destination_packet)
    _print_table(
        ("Field", "Source PCAP", "Destination PCAP", "Processing result"),
        packet_rows,
    )
    print(f"\nPayload content: {delivery['payload']}")

    print("\n=== 3. IPv4 Processing Along the Actual Satellite Path ===")
    message_rows = [
        row
        for row in trace_rows
        if row["message_id"] == delivery["message_id"]
    ]
    _print_table(
        (
            "Order",
            "Entity",
            "Action",
            "TTL before",
            "TTL after",
            "Checksum before",
            "Checksum after",
            "Next entity",
        ),
        tuple(
            _trace_display_row(order, row)
            for order, row in enumerate(message_rows, start=1)
        ),
    )
    entity_sequence = ["User 0"] + [
        f"S{row['entity_id']}"
        for row in message_rows
        if row["action"] == "forward"
    ] + ["User 1"]
    print("\nActual entity sequence:")
    for order, entity_name in enumerate(entity_sequence, start=1):
        print(f"  {order:02d}. {entity_name}")
    print(
        "\nThe packet underwent eight satellite forwarding events. Its TTL "
        "decreased from 64 at the source to 56 at the destination. "
        "Destination delivery did not perform an additional decrement."
    )

    figure_path = _plot_result(
        message_rows=message_rows,
        source_packet=source_packet,
        destination_packet=destination_packet,
    )
    print(f"\nResult figure saved to:\n  {figure_path.resolve()}")

    source_path = Path(cg.IPV4_EXAMPLE_SOURCE_PCAP_PATH).resolve()
    destination_path = Path(cg.IPV4_EXAMPLE_DESTINATION_PCAP_PATH).resolve()
    print("\n=== 4. Inspect with Wireshark ===")
    print("Wireshark-readable PCAP files")
    print(f"\nSource capture:\n  {source_path}")
    print(f"\nDestination capture:\n  {destination_path}")
    print("\nCapture format: standard libpcap")
    print("Link type: DLT_RAW (12)")
    print("Decoded layers: Internet Protocol Version 4, User Datagram Protocol, Data")
    print(
        "No live-capture provider is required to open these offline PCAP files."
    )
    return figure_path


def _load_evidence():
    required_paths = (
        Path(cg.IPV4_EXAMPLE_RESULT_FILE_PATH),
        Path(cg.IPV4_EXAMPLE_TRACE_FILE_PATH),
        Path(cg.IPV4_EXAMPLE_SOURCE_PCAP_PATH),
        Path(cg.IPV4_EXAMPLE_DESTINATION_PCAP_PATH),
        Path(cg.IPV4_EXAMPLE_VALIDATION_SUMMARY_PATH),
    )
    missing = [str(path.resolve()) for path in required_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "IPv4 example output is incomplete. Run "
            "`python examples/protocol_ipv4_example/main.py` first. Missing:\n  "
            + "\n  ".join(missing)
        )

    validation = json.loads(required_paths[4].read_text(encoding="utf-8"))
    if validation.get("status") != "PASS":
        raise RuntimeError(
            "The stored end-to-end validation is not PASS. Rerun main.py before "
            "presenting the result."
        )
    delivery = json.loads(required_paths[0].read_text(encoding="utf-8"))
    with required_paths[1].open("r", newline="", encoding="utf-8") as trace_file:
        trace_rows = list(csv.DictReader(trace_file))

    from scapy.layers.inet import IP
    from scapy.utils import rdpcap

    source_packets = rdpcap(str(required_paths[2]))
    destination_packets = rdpcap(str(required_paths[3]))
    if len(source_packets) != 1 or len(destination_packets) != 1:
        raise ValueError("Each example PCAP must contain exactly one packet.")
    return (
        delivery,
        trace_rows,
        source_packets[0][IP],
        destination_packets[0][IP],
    )


def _stack_snapshots():
    default_manager = StackManager()
    default_manager.load_default_setting()
    example_manager = StackManager()
    example_manager.load_default_setting()
    with redirect_stdout(io.StringIO()):
        register_ipv4_udp_stack(example_manager)
    return _snapshot(default_manager), _snapshot(example_manager)


def _snapshot(manager):
    return {
        "application": _registration_name(manager, "application", 18080),
        "transport": _registration_name(manager, "transport", 17),
        "network": _registration_name(manager, "network", 0x0800),
        "link": _registration_name(manager, "link", "Ethernet"),
        "physical": _registration_name(manager, "physical", "Ethernet"),
    }


def _registration_name(manager, layer, protocol):
    try:
        to_data, parse_func = manager.get_parse_funcs(layer, protocol)
    except KeyError:
        return "Not registered", "-"
    handler = _owner_name(parse_func)
    data_type = _owner_name(to_data)
    return handler, data_type


def _owner_name(function):
    return function.__qualname__.split(".", 1)[0]


def _packet_rows(source_packet, destination_packet):
    from scapy.layers.inet import UDP
    from scapy.packet import Raw

    source_payload = bytes(source_packet[Raw].load) if Raw in source_packet else b""
    destination_payload = (
        bytes(destination_packet[Raw].load) if Raw in destination_packet else b""
    )
    payload_status = "identical" if source_payload == destination_payload else "changed"
    return (
        ("IPv4 version", source_packet.version, destination_packet.version, "Preserved"),
        ("Header length", f"{source_packet.ihl * 4} bytes", f"{destination_packet.ihl * 4} bytes", "Preserved"),
        ("Protocol", f"UDP ({source_packet.proto})", f"UDP ({destination_packet.proto})", "Preserved"),
        ("Source IP", source_packet.src, destination_packet.src, "Preserved"),
        ("Destination IP", source_packet.dst, destination_packet.dst, "Preserved"),
        ("TTL", source_packet.ttl, destination_packet.ttl, "Updated during forwarding"),
        ("Header checksum", f"0x{int(source_packet.chksum):04x}", f"0x{int(destination_packet.chksum):04x}", "Recalculated"),
        ("UDP source port", source_packet[UDP].sport, destination_packet[UDP].sport, "Preserved"),
        ("UDP destination port", source_packet[UDP].dport, destination_packet[UDP].dport, "Preserved"),
        ("Payload", f"{len(source_payload)} bytes", f"{len(destination_payload)} bytes", payload_status.title()),
    )


def _trace_display_row(order, row):
    entity = (
        f"S{row['entity_id']}"
        if row["entity_type"] == "satellite"
        else f"User {row['entity_id']}"
    )
    next_entity = row["next_hop_entity"] or "application"
    return (
        order,
        entity,
        row["action"].title(),
        row["ttl_before"],
        row["ttl_after"],
        row["checksum_before"],
        row["checksum_after"],
        _format_entity_label(next_entity),
    )


def _format_entity_label(label):
    if label.startswith("satellite:"):
        return f"S{label.split(':', 1)[1]}"
    if label.startswith("user:"):
        return f"User {label.split(':', 1)[1]}"
    return label.title()


def _plot_result(*, message_rows, source_packet, destination_packet):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    forwarding_rows = [row for row in message_rows if row["action"] == "forward"]
    delivery_row = next(row for row in message_rows if row["action"] == "deliver")
    labels = ["Source"] + [f"S{row['entity_id']}" for row in forwarding_rows] + ["Destination"]
    ttl_values = (
        [int(forwarding_rows[0]["ttl_before"])]
        + [int(row["ttl_after"]) for row in forwarding_rows]
        + [int(delivery_row["ttl_after"])]
    )

    fig, ttl_axis = plt.subplots(figsize=(6, 5))
    x_values = list(range(len(labels)))
    ttl_axis.axvspan(0.5, len(labels) - 1.5, color="#CDC5BF", alpha=0.14, zorder=0)
    ttl_axis.plot(
        x_values,
        ttl_values,
        color="#1F77B4",
        marker="o",
        markerfacecolor="white",
        markeredgewidth=0.5,
        markersize=3.0,
        linewidth=0.9,
        label="IPv4 TTL",
        zorder=10,
    )
    for x_value, ttl in zip(x_values, ttl_values):
        ttl_axis.annotate(
            str(ttl),
            (x_value, ttl),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8,
        )
    ttl_axis.set_xticks(x_values, labels, rotation=30, ha="right")
    ttl_axis.set_ylabel("IPv4 TTL")
    ttl_axis.set_xlabel("Packet Processing Entity")
    ttl_axis.set_ylim(min(ttl_values) - 1, max(ttl_values) + 2)
    ttl_axis.yaxis.grid(True, color="gray", linewidth=0.5, alpha=0.7)
    ttl_axis.tick_params(axis="both", which="both", direction="out")
    legend = ttl_axis.legend(frameon=True, edgecolor="black", loc="best")
    legend.get_frame().set_alpha(None)
    FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE_PATH, bbox_inches="tight", dpi=400)
    plt.close(fig)
    return FIGURE_PATH


def _print_table(headers, rows):
    text_rows = [tuple(str(value) for value in row) for row in rows]
    widths = [
        max(len(str(headers[index])), *(len(row[index]) for row in text_rows))
        for index in range(len(headers))
    ]
    template = "  ".join(f"{{:<{width}}}" for width in widths)
    print(template.format(*headers))
    print(template.format(*(len(header) * "-" for header in headers)))
    for row in text_rows:
        print(template.format(*row))


if __name__ == "__main__":
    main()
