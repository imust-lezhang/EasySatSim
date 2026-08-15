import csv
import threading

from cases.case3.experiment.integration.paths import resolve_project_path


EVENT_LOG_HEADER = [
    "event_type",
    "simulation_time",
    "message_id",
    "pair_id",
    "direction",
    "source_user_id",
    "target_user_id",
    "source_access_satellite_id",
    "target_access_satellite_id",
    "delay_ms",
    "hop_count",
    "path_length",
    "path_satellite_ids",
    "note",
]

_EVENT_LOG_LOCK = threading.Lock()


def prepare_event_log(path):
    output_path = resolve_project_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(EVENT_LOG_HEADER)
    return output_path


def append_event(
        path,
        event_type,
        simulation_time,
        message_id="",
        pair_id="",
        direction="",
        source_user_id="",
        target_user_id="",
        source_access_satellite_id="",
        target_access_satellite_id="",
        delay_ms="",
        hop_count="",
        path_length="",
        path_satellite_ids="",
        note=""):
    output_path = resolve_project_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    row = [
        event_type,
        f"{float(simulation_time):.3f}",
        message_id,
        pair_id,
        direction,
        source_user_id,
        target_user_id,
        _format_optional(source_access_satellite_id),
        _format_optional(target_access_satellite_id),
        _format_optional(delay_ms),
        _format_optional(hop_count),
        _format_optional(path_length),
        path_satellite_ids,
        note,
    ]
    with _EVENT_LOG_LOCK:
        with output_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(row)


def _format_optional(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    return value
