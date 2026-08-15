import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from cases.case3.experiment.integration.paths import normalize_recorded_path
from cases.case3.experiment.integration.paths import resolve_recorded_path
from cases.case3.experiment.integration.paths import to_project_relative_path


MAIN_PATH = PROJECT_ROOT / "cases" / "case3" / "main.py"
OUTPUT_DIR = PROJECT_ROOT / "cases" / "case3" / "experiment" / "output"
MODES = ("centralized", "distributed")
SEED_START = 20260811
SEED_COUNT = 10  # Default number of paired seed groups; valid range: 1-20.


MIN_SEED_COUNT = 1
MAX_SEED_COUNT = 20


def main():
    parser = argparse.ArgumentParser(
        description="Run Case 3 for paired seeds and both routing modes."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned commands without running simulations.",
    )
    parser.add_argument(
        "--seed-count",
        type=int,
        default=SEED_COUNT,
        help=(
            "Number of paired seed groups to run "
            f"({MIN_SEED_COUNT}-{MAX_SEED_COUNT}, default: {SEED_COUNT})."
        ),
    )
    args = parser.parse_args()
    if not MIN_SEED_COUNT <= args.seed_count <= MAX_SEED_COUNT:
        parser.error(
            f"--seed-count must be between {MIN_SEED_COUNT} and {MAX_SEED_COUNT}."
        )

    seeds = tuple(range(SEED_START, SEED_START + args.seed_count))
    planned_runs = [(mode, seed) for seed in seeds for mode in MODES]
    print("[Case 3 batch] Simulation only; metrics and figures are not generated.")
    print(f"[Case 3 batch] Seeds: {', '.join(map(str, seeds))}")
    group_label = "paired seed group" if len(seeds) == 1 else "paired seed groups"
    print(
        f"[Case 3 batch] Planned runs: {len(planned_runs)} "
        f"({len(seeds)} {group_label} x {len(MODES)} routing modes)"
    )

    if args.dry_run:
        for index, (mode, seed) in enumerate(planned_runs, start=1):
            print(f"[{index:02d}/{len(planned_runs)}] {_command_text(mode, seed)}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    batch_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest_path = OUTPUT_DIR / f"case3_batch_manifest_{batch_timestamp}.json"
    manifest = {
        "path_format": "project-relative-posix",
        "batch_timestamp": batch_timestamp,
        "seeds": list(seeds),
        "routing_modes": list(MODES),
        "planned_run_count": len(planned_runs),
        "completed_run_count": 0,
        "status": "running",
        "runs": [],
    }
    _write_manifest(manifest_path, manifest)

    try:
        for index, (mode, seed) in enumerate(planned_runs, start=1):
            print("\n" + "=" * 72)
            print(
                f"[Case 3 batch] Run {index}/{len(planned_runs)}: "
                f"mode={mode}, seed={seed}"
            )
            print(f"[Case 3 batch] Command: {_command_text(mode, seed)}")
            started_at = datetime.now().isoformat(timespec="seconds")
            subprocess.run(
                [
                    sys.executable,
                    str(MAIN_PATH),
                    "--routing-mode",
                    mode,
                    "--seed",
                    str(seed),
                    "--headless",
                ],
                cwd=PROJECT_ROOT,
                env=_child_environment(seed),
                check=True,
            )
            metadata_path = _latest_metadata(mode, seed)
            metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
            _validate_run_outputs(metadata, metadata_path=metadata_path)
            manifest["runs"].append({
                "index": index,
                "routing_mode": mode,
                "seed": seed,
                "started_at": started_at,
                "finished_at": datetime.now().isoformat(timespec="seconds"),
                "metadata_path": to_project_relative_path(metadata_path),
                "event_log_path": normalize_recorded_path(
                    metadata["event_log_path"], reference_path=metadata_path
                ),
                "network_log_path": normalize_recorded_path(
                    metadata["network_log_path"], reference_path=metadata_path
                ),
            })
            manifest["completed_run_count"] = len(manifest["runs"])
            _write_manifest(manifest_path, manifest)
            print(f"[Case 3 batch] Saved metadata: {metadata_path.name}")
    except BaseException:
        manifest["status"] = "failed_or_interrupted"
        manifest["finished_at"] = datetime.now().isoformat(timespec="seconds")
        _write_manifest(manifest_path, manifest)
        print(f"[Case 3 batch] Partial manifest: {manifest_path}")
        raise

    manifest["status"] = "complete"
    manifest["finished_at"] = datetime.now().isoformat(timespec="seconds")
    _write_manifest(manifest_path, manifest)
    print("\n" + "=" * 72)
    print(f"[Case 3 batch] Completed all {len(planned_runs)} simulations.")
    print(f"[Case 3 batch] Batch manifest: {manifest_path}")
    print("[Case 3 batch] Metrics and figures have not been generated.")


def _child_environment(seed):
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = str(seed)
    environment["PYTHONUNBUFFERED"] = "1"
    return environment


def _latest_metadata(mode, seed):
    pattern = f"case3_run_metadata_{mode}_seed_{seed}_*.json"
    candidates = list(OUTPUT_DIR.glob(pattern))
    if not candidates:
        raise FileNotFoundError(f"Simulation completed without metadata matching {pattern}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _validate_run_outputs(metadata, metadata_path=None):
    event_path = resolve_recorded_path(
        metadata["event_log_path"], reference_path=metadata_path
    )
    network_path = resolve_recorded_path(
        metadata["network_log_path"], reference_path=metadata_path
    )
    if not event_path.is_file():
        raise FileNotFoundError(f"Missing event log declared by metadata: {event_path}")
    if not network_path.is_file():
        raise FileNotFoundError(f"Missing network result declared by metadata: {network_path}")

    event_types = set()
    with event_path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if "event_type" not in (reader.fieldnames or []):
            raise ValueError(f"Event log has no valid header: {event_path}")
        for row in reader:
            event_types.add(row.get("event_type", ""))
            if {"generate", "arrival"}.issubset(event_types):
                break
    missing = {"generate", "arrival"} - event_types
    if missing:
        raise ValueError(
            f"Event log contains no usable traffic events ({sorted(missing)} missing): "
            f"{event_path}"
        )
    print(f"[Case 3 batch] Output validation passed: {event_path.name}")


def _command_text(mode, seed):
    return (
        f'"{sys.executable}" "{MAIN_PATH}" --routing-mode {mode} '
        f"--seed {seed} --headless"
    )


def _write_manifest(path, manifest):
    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
