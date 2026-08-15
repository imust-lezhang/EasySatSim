import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from cases.case3.experiment.integration.paths import normalize_recorded_path
from cases.case3.experiment.integration.paths import resolve_recorded_path
from cases.case3.experiment.integration.paths import to_project_relative_path


CASE3_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = CASE3_ROOT / "experiment" / "output"
MODES = ("centralized", "distributed")
BIN_SECONDS = 5.0


def main():
    runs, candidate_count = _select_latest_paired_runs()
    _validate_comparable_runs(runs)
    paired_seeds = sorted({int(run["random_seed"]) for run in runs})
    print(f"[Case 3 metrics] Metadata files discovered: {candidate_count}")
    print(
        f"[Case 3 metrics] Selected runs: {len(runs)} "
        f"({len(paired_seeds)} paired seeds x {len(MODES)} modes)"
    )
    print(f"[Case 3 metrics] Seeds: {', '.join(map(str, paired_seeds))}")
    print("[Case 3 metrics] Input files:")
    for index, metadata in enumerate(runs, start=1):
        print(
            f"  {index:02d}. mode={metadata['routing_mode']}, "
            f"seed={metadata['random_seed']}"
        )
        print(f"      metadata: {metadata['_metadata_path']}")
        print(f"      events:   {metadata['event_log_path']}")
    print(
        "[Case 3 metrics] Network result CSV files are retained for the raw "
        "simulation record but are not used by these two metrics."
    )

    bin_rows = []
    phase_rows = []
    manifest_rows = []
    for metadata in runs:
        run_bins, run_phases = _process_run(metadata)
        bin_rows.extend(run_bins)
        phase_rows.extend(run_phases)
        manifest_rows.append({
            "mode": metadata["routing_mode"],
            "seed": metadata["random_seed"],
            "metadata_path": metadata["_metadata_path"],
            "event_log_path": metadata["event_log_path"],
            "network_log_path": metadata.get("network_log_path", ""),
        })

    bin_frame = pd.DataFrame(bin_rows)
    phase_frame = pd.DataFrame(phase_rows)
    manifest_frame = pd.DataFrame(manifest_rows)
    bin_path = OUTPUT_DIR / "CASE3_TIME_BIN_METRICS.csv"
    phase_path = OUTPUT_DIR / "CASE3_PHASE_SUMMARY.csv"
    manifest_path = OUTPUT_DIR / "CASE3_RUN_MANIFEST.csv"
    report_path = OUTPUT_DIR / "CASE3_FINAL_RESULTS_REPORT.md"
    bin_frame.to_csv(bin_path, index=False)
    _aggregate_phases(phase_frame).to_csv(phase_path, index=False)
    manifest_frame.to_csv(manifest_path, index=False)
    _write_report(phase_frame, manifest_frame, report_path)

    print(
        f"[Case 3 metrics] Completed: {len(runs)} runs, "
        f"{len(paired_seeds)} paired seeds, {len(bin_frame)} time-bin rows."
    )
    print(f"Time-bin metrics: {bin_path}")
    print(f"Phase summary: {phase_path}")
    print(f"Run manifest: {manifest_path}")
    print(f"Report: {report_path}")


def _select_latest_paired_runs():
    candidates = []
    for path in OUTPUT_DIR.glob("case3_run_metadata_*.json"):
        metadata = json.loads(path.read_text(encoding="utf-8-sig"))
        mode = metadata.get("routing_mode")
        seed = metadata.get("random_seed")
        if mode in MODES and seed is not None:
            metadata["_metadata_file_path"] = path.resolve()
            metadata["_metadata_path"] = to_project_relative_path(path)
            metadata["event_log_path"] = normalize_recorded_path(
                metadata["event_log_path"], reference_path=path
            )
            if metadata.get("network_log_path"):
                metadata["network_log_path"] = normalize_recorded_path(
                    metadata["network_log_path"], reference_path=path
                )
            metadata["_mtime"] = path.stat().st_mtime
            candidates.append(metadata)

    latest = {}
    for metadata in candidates:
        key = (metadata["routing_mode"], int(metadata["random_seed"]))
        if key not in latest or metadata["_mtime"] > latest[key]["_mtime"]:
            latest[key] = metadata
    paired_seeds = sorted(
        seed for seed in {key[1] for key in latest}
        if all((mode, seed) in latest for mode in MODES)
    )
    if not paired_seeds:
        raise FileNotFoundError(
            "No paired centralized/distributed runs were found in "
            f"{OUTPUT_DIR}. Run main.py once for each mode using the same seed."
        )
    selected = [latest[(mode, seed)] for seed in paired_seeds for mode in MODES]
    return selected, len(candidates)


def _validate_comparable_runs(runs):
    reference = runs[0]
    fields = (
        "running_time",
        "failed_satellite_id",
        "failure_time",
        "centralized_route_refresh_interval",
    )
    nested_fields = (
        ("constellation", "total_satellites"),
        ("users_and_traffic", "user_number"),
        ("users_and_traffic", "pair_count"),
        ("users_and_traffic", "coordinate_model"),
        ("users_and_traffic", "cluster_radius_deg"),
        ("users_and_traffic", "group_a_subcenters"),
        ("users_and_traffic", "group_b_subcenters"),
        ("physical_layer", "PHYSICAL_LAYER_ENABLE"),
    )
    errors = []
    for run in runs[1:]:
        for field in fields:
            if run.get(field) != reference.get(field):
                errors.append(f"{field}: {reference.get(field)} != {run.get(field)}")
        for parent, field in nested_fields:
            if run.get(parent, {}).get(field) != reference.get(parent, {}).get(field):
                errors.append(f"{parent}.{field} differs")

    for seed in sorted({int(run["random_seed"]) for run in runs}):
        pair = [run for run in runs if int(run["random_seed"]) == seed]
        hashes = {
            run.get("users_and_traffic", {}).get("coordinate_sha256")
            for run in pair
        }
        coordinate_seeds = {
            run.get("users_and_traffic", {}).get("coordinate_seed")
            for run in pair
        }
        if len(hashes) != 1 or None in hashes:
            errors.append(
                f"seed {seed}: centralized/distributed coordinate hashes differ"
            )
        if coordinate_seeds != {seed}:
            errors.append(
                f"seed {seed}: coordinate_seed does not match random_seed"
            )
    if errors:
        raise ValueError("Runs are not comparable:\n- " + "\n- ".join(sorted(set(errors))))


def _process_run(metadata):
    event_path = resolve_recorded_path(
        metadata["event_log_path"],
        reference_path=metadata.get("_metadata_file_path"),
    )
    if not event_path.is_file():
        raise FileNotFoundError(f"Missing event log: {event_path}")
    events = pd.read_csv(event_path)
    events["simulation_time"] = pd.to_numeric(events["simulation_time"], errors="coerce")
    generated = events[events["event_type"] == "generate"].copy()
    arrivals = events[events["event_type"] == "arrival"].copy()
    if generated.empty:
        raise ValueError(
            "Selected event log contains no generate events; refusing to create "
            f"an incomplete comparison: {event_path}"
        )
    if arrivals.empty:
        raise ValueError(
            "Selected event log contains no arrival events; refusing to create "
            f"an incomplete comparison: {event_path}"
        )
    arrivals["hop_count"] = pd.to_numeric(arrivals["hop_count"], errors="coerce")
    arrival_by_id = (
        arrivals.dropna(subset=["message_id"])
        .drop_duplicates("message_id", keep="first")
        .set_index("message_id")
    )

    duration = float(metadata["running_time"])
    common = {
        "mode": metadata["routing_mode"],
        "seed": int(metadata["random_seed"]),
    }
    bin_rows = []
    for start in np.arange(0.0, duration, BIN_SECONDS):
        end = min(start + BIN_SECONDS, duration)
        metrics = _cohort_metrics(generated, arrival_by_id, start, end)
        bin_rows.append({
            **common,
            "bin_start": start,
            "bin_end": end,
            "bin_center": (start + end) / 2.0,
            **metrics,
        })

    phase_rows = []
    for phase, start, end in _phase_definitions(metadata):
        phase_rows.append({
            **common,
            "phase": phase,
            "phase_start": start,
            "phase_end": end,
            **_cohort_metrics(generated, arrival_by_id, start, end),
        })
    return bin_rows, phase_rows


def _cohort_metrics(generated, arrival_by_id, start, end):
    cohort = generated[
        (generated["simulation_time"] >= start)
        & (generated["simulation_time"] < end)
    ]
    message_ids = cohort["message_id"].dropna().astype(str)
    delivered = arrival_by_id.reindex(message_ids).dropna(subset=["simulation_time"])
    generated_count = len(cohort)
    return {
        "generated_packets": generated_count,
        "delivered_packets": len(delivered),
        "delivery_ratio": len(delivered) / generated_count if generated_count else np.nan,
        "average_hop_count": delivered["hop_count"].mean(),
    }


def _phase_definitions(metadata):
    failure = float(metadata["failure_time"])
    interval = float(metadata["centralized_route_refresh_interval"])
    refresh = math.ceil((failure + 1e-12) / interval) * interval
    duration = float(metadata["running_time"])
    return (
        ("normal", 0.0, min(failure, duration)),
        ("failure_to_refresh", min(failure, duration), min(refresh, duration)),
        ("post_refresh", min(refresh, duration), duration),
    )


def _aggregate_phases(frame):
    metrics = ("delivery_ratio", "average_hop_count")
    aggregate = frame.groupby(["mode", "phase"], sort=False)[list(metrics)].agg(
        ["mean", "std"]
    )
    aggregate.columns = [f"{metric}_{stat}" for metric, stat in aggregate.columns]
    return aggregate.reset_index().fillna(0.0)


def _write_report(phase_frame, manifest_frame, path):
    lines = [
        "# Case 3 Final Results",
        "",
        f"Paired seeds: {', '.join(map(str, sorted(manifest_frame['seed'].unique())))}",
        "",
        "| Routing | Phase | Delivery ratio | Average hop count |",
        "|---|---|---:|---:|",
    ]
    for (mode, phase), rows in phase_frame.groupby(["mode", "phase"], sort=False):
        lines.append(
            f"| {mode} | {phase} | {rows['delivery_ratio'].mean():.4f} | "
            f"{rows['average_hop_count'].mean():.4f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
