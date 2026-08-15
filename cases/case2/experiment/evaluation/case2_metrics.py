import csv
from pathlib import Path


CASE2_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = CASE2_ROOT.parents[1]
OUTPUT_DIR = CASE2_ROOT / "experiment" / "output"
DEFAULT_WARMUP_SECONDS = 10


ARCHITECTURES = ("cl", "fl")


NETWORK_COLUMNS = [
    "Time",
    "Current_Generated_Packets_Number",
    "Current_Arrived_Packets_Number",
    "Current_Lost_Packets_Number",
    "Current_Generated_Packets_Byte",
    "Current_Arrived_Packets_Byte",
    "Current_Lost_Packets_Byte",
    "Current_Latency",
    "Current_Covered_Users_Number",
    "Current_Operational_Satellite_Number",
    "Current_Hop_Count",
    "Current_Load_Deviation",
    "Total_Generated_Packets_Number",
    "Total_Arrived_Packets_Number",
    "Total_Lost_Packets_Number",
    "Total_Generated_Packets_Byte",
    "Total_Arrived_Packets_Byte",
    "Total_Lost_Packets_Byte",
    "Total_Latency",
    "Total_Covered_Users_Number",
    "Total_Operational_Satellite_Number",
    "Total_Hop_Count",
    "Total_Load_Deviation",
]


def get_case2_output_path(filename):
    return OUTPUT_DIR / filename


def get_architecture_paths(architecture):
    return {
        "network": get_latest_network_path(architecture=architecture),
        "learning": get_case2_output_path(f"{architecture}_learning_metrics.csv"),
        "communication": get_case2_output_path(
            f"{architecture}_communication_events.csv"
        ),
    }


def get_latest_network_path(architecture):
    candidates = get_network_candidates(architecture=architecture)
    existing_candidates = [path for path in candidates if path.exists()]
    if not existing_candidates:
        return get_case2_output_path(f"{architecture}_network.csv")
    return max(existing_candidates, key=lambda path: path.stat().st_mtime)


def get_network_candidates(architecture):
    fixed_path = get_case2_output_path(f"{architecture}_network.csv")
    timestamp_paths = sorted(
        OUTPUT_DIR.glob(f"easysatsim_result_{architecture}_*.csv")
    )
    return [fixed_path] + timestamp_paths


def summarize_all_architectures(warmup_seconds=DEFAULT_WARMUP_SECONDS):
    rows = []
    for architecture in ARCHITECTURES:
        rows.append(summarize_architecture(
            architecture=architecture,
            warmup_seconds=warmup_seconds,
        ))
    return rows


def summarize_architecture(architecture, warmup_seconds=DEFAULT_WARMUP_SECONDS):
    paths = get_architecture_paths(architecture=architecture)
    network_rows = read_required_csv(paths["network"], run_hint(architecture))
    learning_rows = read_optional_csv(paths["learning"])
    communication_rows = read_optional_csv(paths["communication"])

    network_summary = summarize_network_rows(
        rows=network_rows,
        warmup_seconds=warmup_seconds,
    )
    learning_summary = summarize_learning_rows(
        architecture=architecture,
        rows=learning_rows,
    )
    communication_summary = summarize_communication_rows(
        rows=communication_rows,
    )

    summary = {
        "architecture": architecture.upper(),
        "network_file": to_project_relative_path(paths["network"]),
        "learning_file": to_project_relative_path(paths["learning"]),
        "communication_file": to_project_relative_path(paths["communication"]),
        "warmup_seconds": warmup_seconds,
    }
    summary.update(network_summary)
    summary.update(learning_summary)
    summary.update(communication_summary)
    return summary


def to_project_relative_path(path):
    path = Path(path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError as exc:
        raise ValueError(f"Path is outside the EasySatSim project: {resolved}") from exc


def summarize_network_rows(rows, warmup_seconds):
    if not rows:
        raise ValueError("Network CSV is empty.")

    rows = sorted(rows, key=lambda row: safe_float(row.get("Time")))
    baseline_row = select_warmup_baseline_row(
        rows=rows,
        warmup_seconds=warmup_seconds,
    )
    last_row = rows[-1]
    baseline_time = safe_float(baseline_row.get("Time"))
    final_time = safe_float(last_row.get("Time"))
    effective_duration = max(final_time - baseline_time, 1.0)

    generated_byte = metric_delta(
        first_row=baseline_row,
        last_row=last_row,
        key="Total_Generated_Packets_Byte",
    )
    arrived_byte = metric_delta(
        first_row=baseline_row,
        last_row=last_row,
        key="Total_Arrived_Packets_Byte",
    )
    lost_byte = metric_delta(
        first_row=baseline_row,
        last_row=last_row,
        key="Total_Lost_Packets_Byte",
    )
    generated_packets = metric_delta(
        first_row=baseline_row,
        last_row=last_row,
        key="Total_Generated_Packets_Number",
    )
    arrived_packets = metric_delta(
        first_row=baseline_row,
        last_row=last_row,
        key="Total_Arrived_Packets_Number",
    )
    lost_packets = metric_delta(
        first_row=baseline_row,
        last_row=last_row,
        key="Total_Lost_Packets_Number",
    )

    active_rows = [
        row for row in rows
        if safe_float(row.get("Time")) > baseline_time
    ]
    if not active_rows:
        active_rows = rows

    return {
        "warmup_baseline_time_second": baseline_time,
        "final_time_second": final_time,
        "effective_duration_second": effective_duration,
        "average_goodput_mbps": bytes_per_second_to_mbps(
            arrived_byte / effective_duration
        ),
        "average_arrived_throughput_mbps": bytes_per_second_to_mbps(
            arrived_byte / effective_duration
        ),
        "average_generated_throughput_mbps": bytes_per_second_to_mbps(
            generated_byte / effective_duration
        ),
        "final_average_latency_ms": safe_float(last_row.get("Total_Latency")),
        "mean_window_latency_ms": mean_positive(
            safe_float(row.get("Current_Latency"))
            for row in active_rows
        ),
        "packet_loss_rate": safe_rate(
            lost_packets,
            generated_packets,
        ),
        "resolved_packet_loss_rate": safe_rate(
            lost_packets,
            arrived_packets + lost_packets,
        ),
        "byte_loss_rate": safe_rate(
            lost_byte,
            generated_byte,
        ),
        "generated_packets_after_warmup": generated_packets,
        "arrived_packets_after_warmup": arrived_packets,
        "lost_packets_after_warmup": lost_packets,
        "generated_byte_after_warmup": generated_byte,
        "arrived_byte_after_warmup": arrived_byte,
        "lost_byte_after_warmup": lost_byte,
        "total_generated_packets": safe_float(
            last_row.get("Total_Generated_Packets_Number")
        ),
        "total_arrived_packets": safe_float(
            last_row.get("Total_Arrived_Packets_Number")
        ),
        "total_lost_packets": safe_float(
            last_row.get("Total_Lost_Packets_Number")
        ),
        "total_generated_byte": safe_float(
            last_row.get("Total_Generated_Packets_Byte")
        ),
        "total_arrived_byte": safe_float(
            last_row.get("Total_Arrived_Packets_Byte")
        ),
        "total_lost_byte": safe_float(
            last_row.get("Total_Lost_Packets_Byte")
        ),
        "mean_covered_users": mean_positive(
            safe_float(row.get("Current_Covered_Users_Number"))
            for row in active_rows
        ),
        "mean_operational_satellites": mean_positive(
            safe_float(row.get("Current_Operational_Satellite_Number"))
            for row in active_rows
        ),
    }


def select_warmup_baseline_row(rows, warmup_seconds):
    baseline_row = rows[0]
    for row in rows:
        if safe_float(row.get("Time")) > warmup_seconds:
            break
        baseline_row = row
    return baseline_row


def metric_delta(first_row, last_row, key):
    value = safe_float(last_row.get(key)) - safe_float(first_row.get(key))
    return max(value, 0.0)


def summarize_learning_rows(architecture, rows):
    if not rows:
        return {
            "learning_rounds": 0,
            "final_test_accuracy_percent": "",
            "best_test_accuracy_percent": "",
            "final_learning_time_second": "",
        }

    accuracy_key = "Test_Accuracy"
    time_key = "Simulation_Time"
    round_key = "Train_Round" if architecture == "cl" else "Round_ID"
    accuracies = [safe_float(row.get(accuracy_key)) for row in rows]
    return {
        "learning_rounds": len(rows),
        "final_test_accuracy_percent": accuracies[-1],
        "best_test_accuracy_percent": max(accuracies),
        "final_learning_time_second": safe_float(rows[-1].get(time_key)),
        "final_learning_round": rows[-1].get(round_key, ""),
    }


def summarize_communication_rows(rows):
    event_counts = {}
    for row in rows:
        event_type = row.get("Event_Type", "")
        if not event_type:
            continue
        event_counts[event_type] = event_counts.get(event_type, 0) + 1

    return {
        "communication_event_rows": len(rows),
        "communication_event_counts": encode_event_counts(event_counts),
    }


def write_summary_csv(rows, output_path=None):
    if output_path is None:
        output_path = get_case2_output_path("case2_summary_metrics.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = get_summary_fieldnames(rows)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return output_path


def get_summary_fieldnames(rows):
    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    return fieldnames


def read_required_csv(path, hint):
    if not path.exists():
        raise FileNotFoundError(
            f"Missing required file: {path}\n{hint}"
        )
    return read_csv(path)


def read_optional_csv(path):
    if not path.exists():
        return []
    return read_csv(path)


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def safe_float(value):
    if value in (None, ""):
        return 0.0
    return float(value)


def safe_rate(numerator, denominator):
    if denominator == 0:
        return 0.0
    return numerator / denominator


def mean_positive(values):
    numeric_values = [value for value in values if value > 0]
    if not numeric_values:
        return 0.0
    return sum(numeric_values) / len(numeric_values)


def bytes_per_second_to_mbps(value):
    return value * 8.0 / 1_000_000.0


def encode_event_counts(event_counts):
    if not event_counts:
        return ""
    return ";".join(
        f"{key}:{event_counts[key]}"
        for key in sorted(event_counts)
    )


def run_hint(architecture):
    if architecture == "cl":
        return (
            "Run CL first:\n"
            "$env:EASYSATSIM_LEARNING_ARCHITECTURE=\"cl\"\n"
            "python cases\\case2\\main.py"
        )
    return (
        "Run FL first:\n"
        "$env:EASYSATSIM_LEARNING_ARCHITECTURE=\"fl\"\n"
        "python cases\\case2\\main.py"
    )
