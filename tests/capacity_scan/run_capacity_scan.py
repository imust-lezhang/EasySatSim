from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import psutil
except ImportError as exc:
    raise SystemExit(
        "psutil is required for the capacity scan. Install it with:\n"
        "python -m pip install -r tests/capacity_scan/requirements-capacity.txt"
    ) from exc


CAPACITY_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = CAPACITY_ROOT.parents[1]
WORKER_PATH = CAPACITY_ROOT / "capacity_worker.py"
BASE_CONFIG_PATH = (
    PROJECT_ROOT
    / "examples"
    / "test_mode_example"
    / "src"
    / "configuration"
    / "simulation_config.py"
)
OUTPUT_ROOT = CAPACITY_ROOT / "output"
LOCK_PATH = CAPACITY_ROOT / ".capacity_scan.lock"

CAPACITY_SATELLITE_CONE_ANGLE_DEG = 70.0
CAPACITY_ISL_MIN_SNR_DB = -5.0


def replace_assignments(text: str, replacements: dict[str, str]) -> str:
    tree = ast.parse(text)
    lines = text.splitlines()
    nodes = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id in replacements:
            nodes[target.id] = node

    missing = sorted(set(replacements) - set(nodes))
    if missing:
        raise ValueError(
            "Base configuration is missing assignments: " + ", ".join(missing)
        )

    for name, node in sorted(
        nodes.items(), key=lambda item: item[1].lineno, reverse=True
    ):
        start = node.lineno - 1
        end = getattr(node, "end_lineno", node.lineno)
        lines[start:end] = [f"{name} = {replacements[name]}"]
    return "\n".join(lines) + "\n"


def create_run_configuration(
    run_dir: Path,
    satellites: int,
    planes: int,
    satellites_per_plane: int,
    network_result_path: Path,
) -> Path:
    config_root = run_dir / "config_root"
    config_dir = config_root / "configuration"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "__init__.py").write_text("", encoding="utf-8")
    base_text = BASE_CONFIG_PATH.read_text(encoding="utf-8")
    config_text = replace_assignments(
        base_text,
        {
            "ORBIT_NUMBER": str(planes),
            "SATELLITE_NUMBER_PRE_ORBIT": str(satellites_per_plane),
            "SATELLITE_CONE_ANGLE": repr(CAPACITY_SATELLITE_CONE_ANGLE_DEG),
            "ISL_MIN_SNR_DB": repr(CAPACITY_ISL_MIN_SNR_DB),
            "USER_NUMBER": "2",
            "TEST_MODE_OUTPUT_ID": repr(f"capacity_{satellites}"),
            "AUTO_ASSIGN_SAVE_FILE_PATH": "False",
            "SAVE_FILE_PATH": repr(str(network_result_path.resolve())),
            "TOTAL_SATELLITE_NUMBER": "ORBIT_NUMBER * SATELLITE_NUMBER_PRE_ORBIT",
        },
    )
    (config_dir / "simulation_config.py").write_text(
        config_text,
        encoding="utf-8",
    )
    return config_root


class ProcessTreeSampler:
    def __init__(self, pid: int):
        self.pid = pid
        self.processes: dict[int, psutil.Process] = {}
        self.logical_cpu_count = max(1, psutil.cpu_count(logical=True) or 1)
        self.samples: list[dict] = []
        psutil.cpu_percent(interval=None)

    def _discover(self) -> list[psutil.Process]:
        try:
            root = psutil.Process(self.pid)
            return [root, *root.children(recursive=True)]
        except (psutil.Error, OSError):
            return []

    def sample(self) -> dict:
        processes = self._discover()
        process_cpu_sum = 0.0
        process_cpu_ready = False
        rss_bytes = 0
        process_count = 0
        active_pids = set()

        for discovered in processes:
            active_pids.add(discovered.pid)
            process = self.processes.get(discovered.pid)
            if process is None:
                process = discovered
                self.processes[discovered.pid] = process
                try:
                    process.cpu_percent(interval=None)
                except (psutil.Error, OSError):
                    pass
            else:
                try:
                    process_cpu_sum += float(process.cpu_percent(interval=None))
                    process_cpu_ready = True
                except (psutil.Error, OSError):
                    pass
            try:
                rss_bytes += int(process.memory_info().rss)
                process_count += 1
            except (psutil.Error, OSError):
                pass

        for stale_pid in set(self.processes) - active_pids:
            self.processes.pop(stale_pid, None)

        memory = psutil.virtual_memory()
        record = {
            "wall_monotonic_s": time.monotonic(),
            "system_cpu_percent": float(psutil.cpu_percent(interval=None)),
            "system_ram_percent": float(memory.percent),
            "system_ram_used_bytes": int(memory.used),
            "process_tree_cpu_percent_raw": (
                process_cpu_sum if process_cpu_ready else None
            ),
            "process_tree_cpu_percent_host_capacity": (
                process_cpu_sum / self.logical_cpu_count
                if process_cpu_ready
                else None
            ),
            "process_tree_rss_bytes": rss_bytes,
            "process_count": process_count,
        }
        self.samples.append(record)
        return record


def terminate_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        root = psutil.Process(process.pid)
        targets = [*root.children(recursive=True), root]
    except (psutil.Error, OSError):
        targets = []

    for target in targets:
        try:
            target.terminate()
        except (psutil.Error, OSError):
            pass
    _, alive = psutil.wait_procs(targets, timeout=5) if targets else ([], [])
    for target in alive:
        try:
            target.kill()
        except (psutil.Error, OSError):
            pass
    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass


def write_csv(path: Path, rows: list[dict], fieldnames) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _mean_or_none(values) -> float | None:
    cleaned = [float(value) for value in values if value not in (None, "")]
    return sum(cleaned) / len(cleaned) if cleaned else None


def _maximum_or_none(values) -> float | None:
    cleaned = [float(value) for value in values if value not in (None, "")]
    return max(cleaned) if cleaned else None


def summarize_resource_samples(samples: list[dict], worker_result: dict) -> dict:
    start = worker_result.get("measurement_start_monotonic_s")
    end = worker_result.get("measurement_end_monotonic_s")
    if start is not None and end is not None:
        selected = [
            sample
            for sample in samples
            if float(start) <= sample["wall_monotonic_s"] <= float(end)
        ]
    else:
        selected = []
    if not selected:
        selected = samples

    gib = 1024.0 ** 3
    rss_mean = _mean_or_none(
        sample["process_tree_rss_bytes"] for sample in selected
    )
    rss_peak = _maximum_or_none(
        sample["process_tree_rss_bytes"] for sample in selected
    )
    return {
        "system_ram_peak_percent": _maximum_or_none(
            sample["system_ram_percent"] for sample in selected
        ),
        "process_tree_cpu_mean_percent_host_capacity": _mean_or_none(
            sample["process_tree_cpu_percent_host_capacity"]
            for sample in selected
        ),
        "process_tree_rss_mean_gib": (
            rss_mean / gib if rss_mean is not None else None
        ),
        "process_tree_rss_peak_gib": (
            rss_peak / gib if rss_peak is not None else None
        ),
        "measurement_resource_samples": len(selected),
    }
RESOURCE_FIELDS = (
    "wall_monotonic_s",
    "system_cpu_percent",
    "system_ram_percent",
    "system_ram_used_bytes",
    "process_tree_cpu_percent_raw",
    "process_tree_cpu_percent_host_capacity",
    "process_tree_rss_bytes",
    "process_count",
)
RUN_FIELDS = (
    "satellites",
    "planes",
    "satellites_per_plane",
    "constellation",
    "repeat",
    "seed",
    "status",
    "scene_initialization_time_s",
    "system_ram_before_percent",
    "system_available_before_gib",
    "process_tree_rss_overall_peak_gib",
    "system_ram_overall_peak_percent",
    "process_tree_cpu_mean_percent_host_capacity",
    "process_tree_rss_measurement_peak_gib",
    "system_ram_measurement_peak_percent",
    "generated_packet_rate_per_s",
    "arrived_packet_rate_per_s",
    "delivery_ratio_percent",
    "window_arrival_to_generation_percent",
    "in_flight_packets_at_end",
    "simulation_speed_ratio",
    "workload_retention_percent",
    "workflow_completed_pass",
    "timer_realtime_pass",
    "communication_pass",
    "workload_retention_pass",
    "normal_workflow_pass",
    "failure_reasons",
    "safety_reason",
    "error",
    "worker_result_json",
    "worker_log",
    "network_result_csv",
    "resource_samples_csv",
)


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return number


def positive_float(value: str) -> float:
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return number


def percentage(value: str) -> float:
    number = float(value)
    if not 0.0 < number <= 100.0:
        raise argparse.ArgumentTypeError("percentage must be in the range (0, 100]")
    return number


def ratio(value: str) -> float:
    number = float(value)
    if not 0.0 < number <= 1.0:
        raise argparse.ArgumentTypeError("ratio must be in the range (0, 1]")
    return number


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Estimate local EasySatSim capacity by running isolated live "
            "workflows in fixed satellite-count increments."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--start-satellites", type=positive_int, default=500)
    parser.add_argument("--step", type=positive_int, default=500)
    parser.add_argument("--max-satellites", type=positive_int, default=15000)
    parser.add_argument(
        "--scales",
        nargs="+",
        type=positive_int,
        help=(
            "Run these exact satellite counts instead of the start/step/max range. "
            "The baseline scale is added automatically when absent."
        ),
    )
    parser.add_argument(
        "--baseline-satellites",
        type=positive_int,
        default=500,
        help="Scale used to establish the generated-workload baseline.",
    )
    parser.add_argument("--repeats", type=positive_int, default=1)
    parser.add_argument("--warmup-seconds", type=positive_float, default=5.0)
    parser.add_argument("--measurement-seconds", type=positive_float, default=20.0)
    parser.add_argument("--sample-interval", type=positive_float, default=1.0)
    parser.add_argument(
        "--safety-poll-interval",
        type=positive_float,
        default=0.1,
        help=(
            "Memory-safety polling interval. This is independent of the less "
            "frequent resource-sample interval."
        ),
    )
    parser.add_argument("--minimum-speed-ratio", type=ratio, default=0.95)
    parser.add_argument("--minimum-delivery-percent", type=percentage, default=95.0)
    parser.add_argument("--minimum-workload-retention", type=ratio, default=0.80)
    parser.add_argument("--max-system-memory-percent", type=percentage, default=85.0)
    parser.add_argument("--minimum-available-memory-gib", type=positive_float, default=2.0)
    parser.add_argument(
        "--timeout-seconds",
        type=positive_float,
        help="Per-scale timeout. The default adds 300 seconds to warm-up and measurement time.",
    )
    parser.add_argument(
        "--offscreen",
        action="store_true",
        help="Use Qt offscreen mode. Omit this option for the normal live visualization workflow.",
    )
    parser.add_argument(
        "--continue-after-failure",
        action="store_true",
        help="Continue to larger scales after a worker failure. Memory safety stops always end the scan.",
    )
    parser.add_argument(
        "--summarize-existing",
        type=Path,
        help=(
            "Regenerate capacity_report.md and capacity_runs.csv from an existing "
            "capacity_scan directory without starting a simulation."
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def selected_scales(args: argparse.Namespace) -> list[int]:
    if args.scales:
        scales = sorted(set(args.scales))
        if args.baseline_satellites not in scales:
            scales.insert(0, args.baseline_satellites)
        return sorted(set(scales))
    if args.start_satellites > args.max_satellites:
        raise ValueError("--start-satellites must not exceed --max-satellites.")
    scales = list(range(args.start_satellites, args.max_satellites + 1, args.step))
    if args.baseline_satellites not in scales:
        scales.append(args.baseline_satellites)
    return sorted(set(scales))


def balanced_factorization(total: int) -> tuple[int, int]:
    for planes in range(math.isqrt(total), 0, -1):
        if total % planes == 0:
            return planes, total // planes
    raise ValueError(f"Could not factor satellite count {total}.")


def acquire_lock() -> None:
    if LOCK_PATH.exists():
        try:
            payload = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
            owner_pid = int(payload.get("pid", -1))
        except (OSError, ValueError, json.JSONDecodeError):
            owner_pid = -1
        if owner_pid > 0 and psutil.pid_exists(owner_pid):
            raise RuntimeError(
                "Another capacity scan may still be active. "
                f"PID={owner_pid}, lock={LOCK_PATH}"
            )
        LOCK_PATH.unlink(missing_ok=True)

    payload = {
        "pid": os.getpid(),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "command": sys.argv,
    }
    descriptor = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(descriptor, "w", encoding="utf-8") as lock_file:
        json.dump(payload, lock_file, indent=2)


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def detect_cpu_name() -> str:
    if sys.platform == "win32":
        try:
            import winreg

            key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            if str(name).strip():
                return str(name).strip()
        except (OSError, ImportError):
            pass
    return platform.processor() or "unknown"


def overall_resource_summary(samples: list[dict]) -> dict:
    if not samples:
        return {
            "process_tree_rss_overall_peak_gib": "",
            "system_ram_overall_peak_percent": "",
        }
    gib = 1024.0 ** 3
    rss_values = [
        float(sample["process_tree_rss_bytes"])
        for sample in samples
        if sample.get("process_tree_rss_bytes") not in (None, "")
    ]
    ram_values = [
        float(sample["system_ram_percent"])
        for sample in samples
        if sample.get("system_ram_percent") not in (None, "")
    ]
    return {
        "process_tree_rss_overall_peak_gib": max(rss_values) / gib if rss_values else "",
        "system_ram_overall_peak_percent": max(ram_values) if ram_values else "",
    }


def run_one(
    args: argparse.Namespace,
    session_dir: Path,
    satellites: int,
    planes: int,
    satellites_per_plane: int,
    repeat: int,
) -> dict:
    seed = 3030000 + satellites + repeat
    run_dir = session_dir / f"scale_{satellites}" / f"repeat_{repeat:02d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    network_csv = run_dir / "network_metrics.csv"
    resource_csv = run_dir / "resource_samples.csv"
    worker_json = run_dir / "worker_result.json"
    worker_log = run_dir / "worker.log"
    config_root = create_run_configuration(
        run_dir,
        satellites,
        planes,
        satellites_per_plane,
        network_csv,
    )

    command = [
        sys.executable,
        str(WORKER_PATH),
        "--config-root",
        str(config_root),
        "--result-json",
        str(worker_json),
        "--warmup-seconds",
        str(args.warmup_seconds),
        "--measurement-seconds",
        str(args.measurement_seconds),
        "--seed",
        str(seed),
        "--satellites",
        str(satellites),
        "--planes",
        str(planes),
        "--satellites-per-plane",
        str(satellites_per_plane),
        "--repeat",
        str(repeat),
    ]
    environment = os.environ.copy()
    environment["EASYSATSIM_CAPACITY_CONFIG_ROOT"] = str(config_root)
    environment["EASYSATSIM_CAPACITY_SEED"] = str(seed)
    environment["EASYSATSIM_CAPACITY_ROUTE_GUARD"] = "1"
    environment["EASYSATSIM_CONFIG_ROOT"] = str(config_root)
    environment["PYTHONUNBUFFERED"] = "1"
    if args.offscreen:
        environment["QT_QPA_PLATFORM"] = "offscreen"

    timeout_seconds = args.timeout_seconds or (
        args.warmup_seconds + args.measurement_seconds + 300.0
    )
    memory_before = psutil.virtual_memory()
    system_ram_before_percent = float(memory_before.percent)
    system_available_before_gib = memory_before.available / (1024.0 ** 3)
    safety_reason = ""
    timed_out = False
    started = time.monotonic()
    with worker_log.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        sampler = ProcessTreeSampler(process.pid)
        sampler.sample()
        last_resource_sample = time.monotonic()
        try:
            while process.poll() is None:
                time.sleep(args.safety_poll_interval)
                now = time.monotonic()
                if now - last_resource_sample >= args.sample_interval:
                    sampler.sample()
                    last_resource_sample = now
                memory = psutil.virtual_memory()
                available_gib = memory.available / (1024.0 ** 3)
                if memory.percent >= args.max_system_memory_percent:
                    sampler.sample()
                    safety_reason = (
                        f"System memory reached {memory.percent:.1f}%, at or above "
                        f"the {args.max_system_memory_percent:.1f}% safety limit."
                    )
                    terminate_process_tree(process)
                    break
                if available_gib <= args.minimum_available_memory_gib:
                    sampler.sample()
                    safety_reason = (
                        f"Available memory fell to {available_gib:.2f} GiB, at or below "
                        f"the {args.minimum_available_memory_gib:.2f} GiB safety limit."
                    )
                    terminate_process_tree(process)
                    break
                if now - started > timeout_seconds:
                    timed_out = True
                    terminate_process_tree(process)
                    break
        except KeyboardInterrupt:
            terminate_process_tree(process)
            raise
        try:
            exit_code = process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            terminate_process_tree(process)
            exit_code = process.wait(timeout=10)
    sampler.sample()
    write_csv(resource_csv, sampler.samples, RESOURCE_FIELDS)

    worker_result = read_json(worker_json)
    status = worker_result.get("status", "failed")
    error = worker_result.get("error", "")
    if safety_reason:
        status = "safety_stopped"
        error = safety_reason
    elif timed_out:
        status = "timeout"
        error = f"Worker exceeded the {timeout_seconds:.0f}-second timeout."
    elif exit_code != 0 and status != "failed":
        status = "failed"
        error = f"Worker exited with code {exit_code}."

    measurement_available = bool(
        worker_result.get("measurement_start_monotonic_s") is not None
        and worker_result.get("measurement_end_monotonic_s") is not None
    )
    measurement_resources = (
        summarize_resource_samples(sampler.samples, worker_result)
        if measurement_available
        else {}
    )
    overall_resources = overall_resource_summary(sampler.samples)
    row = {
        "satellites": satellites,
        "planes": planes,
        "satellites_per_plane": satellites_per_plane,
        "constellation": f"{planes} x {satellites_per_plane}",
        "repeat": repeat,
        "seed": seed,
        "status": status,
        "scene_initialization_time_s": worker_result.get("scene_initialization_time_s", ""),
        "system_ram_before_percent": system_ram_before_percent,
        "system_available_before_gib": system_available_before_gib,
        "process_tree_rss_overall_peak_gib": overall_resources.get(
            "process_tree_rss_overall_peak_gib", ""
        ),
        "system_ram_overall_peak_percent": overall_resources.get(
            "system_ram_overall_peak_percent", ""
        ),
        "process_tree_cpu_mean_percent_host_capacity": measurement_resources.get(
            "process_tree_cpu_mean_percent_host_capacity", ""
        ),
        "process_tree_rss_measurement_peak_gib": measurement_resources.get(
            "process_tree_rss_peak_gib", ""
        ),
        "system_ram_measurement_peak_percent": measurement_resources.get(
            "system_ram_peak_percent", ""
        ),
        "generated_packet_rate_per_s": worker_result.get("generated_packet_rate_per_s", ""),
        "arrived_packet_rate_per_s": worker_result.get("arrived_packet_rate_per_s", ""),
        "delivery_ratio_percent": worker_result.get("delivery_ratio_percent", ""),
        "window_arrival_to_generation_percent": worker_result.get(
            "window_arrival_to_generation_percent", ""
        ),
        "in_flight_packets_at_end": worker_result.get("in_flight_packets_at_end", ""),
        "simulation_speed_ratio": worker_result.get("simulation_speed_ratio", ""),
        "workload_retention_percent": "",
        "workflow_completed_pass": status == "success",
        "timer_realtime_pass": False,
        "communication_pass": False,
        "workload_retention_pass": False,
        "normal_workflow_pass": False,
        "failure_reasons": "",
        "safety_reason": safety_reason,
        "error": error,
        "worker_result_json": str(worker_json),
        "worker_log": str(worker_log),
        "network_result_csv": str(network_csv),
        "resource_samples_csv": str(resource_csv),
    }
    return row


def apply_capacity_criteria(rows: list[dict], args: argparse.Namespace) -> float | None:
    baseline_rates = [
        float(row["generated_packet_rate_per_s"])
        for row in rows
        if row["status"] == "success"
        and int(row["satellites"]) == args.baseline_satellites
        and row["generated_packet_rate_per_s"] not in ("", None)
    ]
    baseline_rate = sum(baseline_rates) / len(baseline_rates) if baseline_rates else None
    for row in rows:
        reasons: list[str] = []
        row["workflow_completed_pass"] = row["status"] == "success"
        row["timer_realtime_pass"] = False
        row["communication_pass"] = False
        row["workload_retention_pass"] = False
        row["normal_workflow_pass"] = False
        if row["status"] != "success":
            reasons.append(row.get("error") or f"worker status is {row['status']}")
            row["failure_reasons"] = "; ".join(reasons)
            continue
        required = (
            "generated_packet_rate_per_s",
            "delivery_ratio_percent",
            "simulation_speed_ratio",
        )
        missing = [name for name in required if row.get(name) in ("", None)]
        if missing:
            reasons.append("missing metrics: " + ", ".join(missing))
            row["failure_reasons"] = "; ".join(reasons)
            continue
        generated_rate = float(row["generated_packet_rate_per_s"])
        delivery = float(row["delivery_ratio_percent"])
        speed = float(row["simulation_speed_ratio"])
        row["timer_realtime_pass"] = speed >= args.minimum_speed_ratio
        row["communication_pass"] = bool(
            generated_rate > 0.0 and delivery >= args.minimum_delivery_percent
        )
        if not row["timer_realtime_pass"]:
            reasons.append(
                f"simulation/wall ratio {speed:.3f} < {args.minimum_speed_ratio:.3f}"
            )
        if generated_rate <= 0.0:
            reasons.append("no packets were generated during the measurement window")
        if delivery < args.minimum_delivery_percent:
            reasons.append(
                f"cumulative delivery {delivery:.2f}% < "
                f"{args.minimum_delivery_percent:.2f}%"
            )
        if baseline_rate is None or baseline_rate <= 0.0:
            reasons.append(
                f"no successful {args.baseline_satellites}-satellite baseline is available"
            )
            row["failure_reasons"] = "; ".join(reasons)
            continue
        retention = generated_rate / baseline_rate
        row["workload_retention_percent"] = retention * 100.0
        row["workload_retention_pass"] = retention >= args.minimum_workload_retention
        if not row["workload_retention_pass"]:
            reasons.append(
                f"workload retention {retention * 100.0:.2f}% < "
                f"{args.minimum_workload_retention * 100.0:.2f}%"
            )
        row["normal_workflow_pass"] = bool(
            row["workflow_completed_pass"]
            and row["timer_realtime_pass"]
            and row["communication_pass"]
            and row["workload_retention_pass"]
        )
        row["failure_reasons"] = "; ".join(reasons)
    return baseline_rate


def numeric_values(rows: list[dict], field: str) -> list[float]:
    return [
        float(row[field])
        for row in rows
        if row.get(field) not in ("", None)
    ]


def mean_value(rows: list[dict], field: str) -> float | None:
    values = numeric_values(rows, field)
    return sum(values) / len(values) if values else None


def min_value(rows: list[dict], field: str) -> float | None:
    values = numeric_values(rows, field)
    return min(values) if values else None


def max_value(rows: list[dict], field: str) -> float | None:
    values = numeric_values(rows, field)
    return max(values) if values else None


def summarize_scales(rows: list[dict], args: argparse.Namespace) -> list[dict]:
    summaries: list[dict] = []
    for satellites in sorted({int(row["satellites"]) for row in rows}):
        scale_rows = [row for row in rows if int(row["satellites"]) == satellites]
        successful = [row for row in scale_rows if row["status"] == "success"]
        unsuccessful = [row for row in scale_rows if row["status"] != "success"]
        delivery_mean = mean_value(successful, "delivery_ratio_percent")
        speed_mean = mean_value(successful, "simulation_speed_ratio")
        retention_mean = mean_value(successful, "workload_retention_percent")
        reasons: list[str] = []
        if len(successful) != args.repeats:
            reasons.append(f"completed runs {len(successful)}/{args.repeats}")
            for row in unsuccessful:
                detail = row.get("error") or row.get("failure_reasons") or "no details"
                reasons.append(
                    f"repeat {row['repeat']} {row['status']}: {detail}"
                )
        if successful:
            if speed_mean is None:
                reasons.append("mean simulation/wall ratio unavailable")
            elif speed_mean < args.minimum_speed_ratio:
                reasons.append(
                    f"mean simulation/wall ratio {speed_mean:.3f} < "
                    f"{args.minimum_speed_ratio:.3f}"
                )
            if delivery_mean is None:
                reasons.append("mean cumulative delivery unavailable")
            elif delivery_mean < args.minimum_delivery_percent:
                reasons.append(
                    f"mean cumulative delivery {delivery_mean:.2f}% < "
                    f"{args.minimum_delivery_percent:.2f}%"
                )
            if retention_mean is None:
                reasons.append("mean workload retention unavailable")
            elif retention_mean < args.minimum_workload_retention * 100.0:
                reasons.append(
                    f"mean workload retention {retention_mean:.2f}% < "
                    f"{args.minimum_workload_retention * 100.0:.2f}%"
                )
        aggregate_pass = not reasons
        summaries.append(
            {
                "satellites": satellites,
                "constellation": scale_rows[0]["constellation"],
                "completed_runs": len(successful),
                "planned_runs": args.repeats,
                "scene_initialization_time_mean_s": mean_value(
                    successful, "scene_initialization_time_s"
                ),
                "cpu_mean_percent_host_capacity": mean_value(
                    successful, "process_tree_cpu_mean_percent_host_capacity"
                ),
                "overall_rss_peak_max_gib": max_value(
                    scale_rows, "process_tree_rss_overall_peak_gib"
                ),
                "overall_system_ram_peak_max_percent": max_value(
                    scale_rows, "system_ram_overall_peak_percent"
                ),
                "generated_rate_mean_per_s": mean_value(
                    successful, "generated_packet_rate_per_s"
                ),
                "arrived_rate_mean_per_s": mean_value(
                    successful, "arrived_packet_rate_per_s"
                ),
                "delivery_mean_percent": delivery_mean,
                "delivery_min_percent": min_value(successful, "delivery_ratio_percent"),
                "simulation_speed_mean": speed_mean,
                "retention_mean_percent": retention_mean,
                "normal_pass_runs": sum(
                    bool(row.get("normal_workflow_pass")) for row in scale_rows
                ),
                "all_runs_normal_pass": bool(scale_rows)
                and len(scale_rows) == args.repeats
                and all(bool(row.get("normal_workflow_pass")) for row in scale_rows),
                "aggregate_normal_pass": aggregate_pass,
                "aggregate_failure_reasons": "; ".join(reasons),
            }
        )
    return summaries


def continuous_summary_limit(summaries: list[dict], field: str) -> int | None:
    limit = None
    for summary in summaries:
        if not bool(summary.get(field)):
            break
        limit = int(summary["satellites"])
    return limit


def maximum_completed_scale(summaries: list[dict]) -> int | None:
    completed = [
        int(summary["satellites"])
        for summary in summaries
        if summary["completed_runs"] == summary["planned_runs"]
    ]
    return max(completed) if completed else None


def value_text(value, digits: int = 2) -> str:
    if value in ("", None):
        return "n/a"
    return f"{float(value):.{digits}f}"


def duration_text(total_seconds: float) -> str:
    seconds = max(0, int(round(total_seconds)))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours} h {minutes} min {seconds} s"
    if minutes:
        return f"{minutes} min {seconds} s"
    return f"{seconds} s"


def print_scan_header(
    args: argparse.Namespace,
    scales: list[int],
    planned: list[tuple[int, int, int]],
) -> None:
    memory = psutil.virtual_memory()
    estimated_seconds = (
        len(planned)
        * args.repeats
        * (args.warmup_seconds + args.measurement_seconds)
    )
    layouts = ", ".join(
        f"{satellites}={planes}x{slots}"
        for satellites, planes, slots in planned
    )
    print("EasySatSim local capacity scan")
    print("\nHardware information")
    print(f"  CPU             : {detect_cpu_name()}")
    print(
        f"  CPU cores       : {psutil.cpu_count(logical=False)} physical / "
        f"{psutil.cpu_count(logical=True)} logical"
    )
    print(f"  Total RAM       : {memory.total / (1024.0 ** 3):.2f} GiB")
    print(
        f"  Current RAM     : {memory.percent:.1f}% used / "
        f"{memory.available / (1024.0 ** 3):.2f} GiB available"
    )
    print("\nTime information")
    print(f"  Started         : {datetime.now().isoformat(timespec='seconds')}")
    print(f"  Warm-up         : {args.warmup_seconds:.1f} s per run")
    print(f"  Measurement     : {args.measurement_seconds:.1f} s per run")
    print(f"  Repetitions     : {args.repeats} per scale")
    print(
        "  Scheduled time  : at least "
        f"{duration_text(estimated_seconds)} plus initialization"
    )
    print("\nTest plan")
    print(f"  Satellite scales: {', '.join(str(scale) for scale in scales)}")
    print(f"  Constellations  : {layouts}")
    print(f"  Baseline scale  : {args.baseline_satellites} satellites")
    print("\nPass requirements")
    print(f"  Simulation/wall : >= {args.minimum_speed_ratio:.2f}")
    print(f"  Delivery ratio  : >= {args.minimum_delivery_percent:.1f}%")
    print(
        f"  Workload retained: >= "
        f"{args.minimum_workload_retention * 100.0:.1f}% of baseline"
    )
    print("\nSafety limits")
    print(f"  System RAM used : stop at >= {args.max_system_memory_percent:.1f}%")
    print(
        f"  Available RAM   : stop at <= "
        f"{args.minimum_available_memory_gib:.2f} GiB"
    )
    print(f"  Safety polling  : every {args.safety_poll_interval:.2f} s")


def write_report(path: Path, rows: list[dict], metadata: dict, args: argparse.Namespace) -> None:
    scale_summaries = summarize_scales(rows, args)
    recommended_capacity = continuous_summary_limit(
        scale_summaries,
        "aggregate_normal_pass",
    )
    maximum_supported = maximum_completed_scale(scale_summaries)
    try:
        started = datetime.fromisoformat(metadata["started_at"])
        finished = datetime.fromisoformat(metadata["finished_at"])
        elapsed_seconds = max(0, int((finished - started).total_seconds()))
        elapsed_text = f"{elapsed_seconds // 60} min {elapsed_seconds % 60} s"
    except (KeyError, TypeError, ValueError):
        elapsed_text = "n/a"

    lines = [
        "# EasySatSim Local Capacity Scan",
        "",
        "## Run and hardware",
        "",
        f"- Started: {metadata['started_at']}",
        f"- Finished: {metadata.get('finished_at', 'n/a')}",
        f"- Total elapsed time: {elapsed_text}",
        f"- CPU: `{metadata['processor']}`",
        f"- CPU cores: {metadata['physical_cpu_count']} physical / {metadata['logical_cpu_count']} logical",
        f"- Total RAM: {metadata['total_memory_gib']:.2f} GiB",
        f"- RAM before scan: {metadata['system_ram_before_scan_percent']:.1f}% used / {metadata['system_available_before_scan_gib']:.2f} GiB available",
        f"- Run mode: {metadata['qt_mode']}; {args.repeats} run(s) per scale; {args.warmup_seconds:.0f} s warm-up + {args.measurement_seconds:.0f} s measurement",
        f"- Tested scales: {', '.join(str(item['satellites']) for item in scale_summaries)} satellites",
        "",
        "## Pass requirements",
        "",
        f"- All {args.repeats} planned run(s) complete successfully;",
        f"- mean simulation/wall-time ratio >= {args.minimum_speed_ratio:.2f};",
        f"- mean cumulative delivery ratio >= {args.minimum_delivery_percent:.1f}%;",
        f"- mean generated-workload retention >= {args.minimum_workload_retention * 100.0:.1f}% of the {args.baseline_satellites}-satellite baseline.",
        "",
        "## Results",
        "",
        "| Satellites | Constellation | Completed | Init mean (s) | CPU mean (% host) | RSS max (GiB) | System RAM max (%) | Generated mean (/s) | Delivery mean / min (%) | Sim/wall mean | Retention mean (%) | Passes | Result |",
        "|---:|:---:|:---:|---:|---:|---:|---:|---:|:---:|---:|---:|:---:|:---:|",
    ]
    for summary in scale_summaries:
        lines.append(
            "| {satellites} | {constellation} | {completed}/{planned} | {init} | {cpu} | "
            "{rss} | {system_ram} | {generated} | {delivery_mean} / {delivery_min} | {speed} | "
            "{retention} | {passes}/{planned} | {aggregate} |".format(
                satellites=summary["satellites"],
                constellation=summary["constellation"],
                completed=summary["completed_runs"],
                planned=summary["planned_runs"],
                init=value_text(summary["scene_initialization_time_mean_s"]),
                cpu=value_text(summary["cpu_mean_percent_host_capacity"]),
                rss=value_text(summary["overall_rss_peak_max_gib"]),
                system_ram=value_text(summary["overall_system_ram_peak_max_percent"]),
                generated=value_text(summary["generated_rate_mean_per_s"]),
                delivery_mean=value_text(summary["delivery_mean_percent"]),
                delivery_min=value_text(summary["delivery_min_percent"]),
                speed=value_text(summary["simulation_speed_mean"], 3),
                retention=value_text(summary["retention_mean_percent"]),
                passes=summary["normal_pass_runs"],
                aggregate="pass" if summary["aggregate_normal_pass"] else "fail",
            )
        )

    lines.extend(["", "## Unmet requirements", ""])
    unmet_lines: list[str] = []
    for summary in scale_summaries:
        if not summary["aggregate_normal_pass"]:
            reason = (summary["aggregate_failure_reasons"] or "not classified").rstrip(".")
            unmet_lines.append(
                f"- {summary['satellites']} satellites: "
                f"{reason}."
            )
        elif summary["normal_pass_runs"] < summary["planned_runs"]:
            failed_repeats = [
                row
                for row in rows
                if int(row["satellites"]) == summary["satellites"]
                and not row["normal_workflow_pass"]
            ]
            details = "; ".join(
                f"repeat {row['repeat']}: {row.get('failure_reasons') or 'not classified'}"
                for row in failed_repeats
            )
            unmet_lines.append(
                f"- {summary['satellites']} satellites passed in aggregate, but "
                f"{summary['normal_pass_runs']}/{summary['planned_runs']} individual runs passed"
                + (f" ({details})." if details else ".")
            )
    lines.extend(unmet_lines or ["- None."])
    lines.extend(
        [
            "",
            "## Capacity recommendation",
            "",
            f"- Recommended satellite count among the tested scales under the configured requirements: **{recommended_capacity if recommended_capacity is not None else 'none'}**.",
            f"- Maximum supported satellite count among the tested scales: **{maximum_supported if maximum_supported is not None else 'none'}** (all planned runs completed successfully).",
            f"- Baseline generated workload: {value_text(metadata.get('baseline_generated_packet_rate_per_s'))} packets/s at {args.baseline_satellites} satellites.",
            "- Complete per-run values are retained in `capacity_runs.csv`.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def summarize_existing(args: argparse.Namespace) -> int:
    session_dir = args.summarize_existing.resolve()
    if session_dir.is_file():
        session_dir = session_dir.parent
    csv_path = session_dir / "capacity_runs.csv"
    metadata_path = session_dir / "capacity_metadata.json"
    if not csv_path.is_file() or not metadata_path.is_file():
        raise FileNotFoundError(
            "The existing scan directory must contain capacity_runs.csv and "
            f"capacity_metadata.json: {session_dir}"
        )
    metadata = read_json(metadata_path)
    if not metadata:
        raise ValueError(f"Could not read capacity metadata: {metadata_path}")
    with csv_path.open("r", newline="", encoding="utf-8-sig") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise ValueError(f"No capacity rows were found: {csv_path}")
    missing_fields = [field for field in RUN_FIELDS if field not in rows[0]]
    if missing_fields:
        raise ValueError(
            "This scan predates the current capacity schema and cannot be "
            "regenerated directly. Missing fields: " + ", ".join(missing_fields)
        )

    args.repeats = int(metadata["repeats"])
    args.warmup_seconds = float(metadata["warmup_seconds"])
    args.measurement_seconds = float(metadata["measurement_seconds"])
    args.minimum_speed_ratio = float(metadata["minimum_speed_ratio"])
    args.minimum_delivery_percent = float(metadata["minimum_delivery_percent"])
    args.minimum_workload_retention = float(metadata["minimum_workload_retention"])
    args.baseline_satellites = int(metadata["baseline_satellites"])
    args.safety_poll_interval = float(
        metadata.get("safety_poll_interval", args.safety_poll_interval)
    )
    metadata["processor"] = detect_cpu_name()
    baseline_rate = apply_capacity_criteria(rows, args)
    metadata["baseline_generated_packet_rate_per_s"] = baseline_rate
    metadata["report_regenerated_at"] = datetime.now().isoformat(timespec="seconds")
    write_csv(csv_path, rows, RUN_FIELDS)
    atomic_json(metadata_path, metadata)
    report_path = session_dir / "capacity_report.md"
    write_report(report_path, rows, metadata, args)
    scale_summaries = summarize_scales(rows, args)
    recommended_capacity = continuous_summary_limit(
        scale_summaries,
        "aggregate_normal_pass",
    )
    maximum_supported = maximum_completed_scale(scale_summaries)
    print("Existing capacity scan summarized; no simulation was started.")
    print(
        "Recommended satellite count among tested scales: "
        f"{recommended_capacity if recommended_capacity is not None else 'none'}"
    )
    print(
        "Maximum supported satellite count among tested scales: "
        f"{maximum_supported if maximum_supported is not None else 'none'}"
    )
    print(f"Read the complete result: {report_path}")
    return 0


def main() -> int:
    args = parse_args()
    if args.summarize_existing is not None:
        return summarize_existing(args)
    scales = selected_scales(args)
    planned = [(scale, *balanced_factorization(scale)) for scale in scales]
    print_scan_header(args, scales, planned)
    if args.dry_run:
        print("\nDry run complete; no simulation was started.")
        return 0

    acquire_lock()
    run_id = datetime.now().strftime("capacity_scan_%Y%m%d_%H%M%S")
    session_dir = OUTPUT_ROOT / run_id
    session_dir.mkdir(parents=True, exist_ok=False)
    memory_before_scan = psutil.virtual_memory()
    metadata = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "python": sys.version,
        "platform": platform.platform(),
        "processor": detect_cpu_name(),
        "logical_cpu_count": psutil.cpu_count(logical=True),
        "physical_cpu_count": psutil.cpu_count(logical=False),
        "total_memory_gib": memory_before_scan.total / (1024.0 ** 3),
        "system_ram_before_scan_percent": float(memory_before_scan.percent),
        "system_available_before_scan_gib": memory_before_scan.available / (1024.0 ** 3),
        "qt_mode": "offscreen" if args.offscreen else "live",
        "scales": scales,
        "requested_scales": args.scales,
        "baseline_satellites": args.baseline_satellites,
        "repeats": args.repeats,
        "warmup_seconds": args.warmup_seconds,
        "measurement_seconds": args.measurement_seconds,
        "minimum_speed_ratio": args.minimum_speed_ratio,
        "minimum_delivery_percent": args.minimum_delivery_percent,
        "minimum_workload_retention": args.minimum_workload_retention,
        "max_system_memory_percent": args.max_system_memory_percent,
        "minimum_available_memory_gib": args.minimum_available_memory_gib,
        "safety_poll_interval": args.safety_poll_interval,
        "connectivity": {
            "satellite_cone_angle_degrees": CAPACITY_SATELLITE_CONE_ANGLE_DEG,
            "isl_min_snr_db": CAPACITY_ISL_MIN_SNR_DB,
        },
    }
    metadata_path = session_dir / "capacity_metadata.json"
    rows: list[dict] = []
    interrupted = False
    safety_stopped = False
    try:
        for satellites, planes, slots in planned:
            for repeat in range(1, args.repeats + 1):
                print(
                    f"\n[{satellites} satellites, {planes} x {slots}, "
                    f"repeat {repeat}/{args.repeats}]",
                    flush=True,
                )
                row = run_one(
                    args,
                    session_dir,
                    satellites,
                    planes,
                    slots,
                    repeat,
                )
                rows.append(row)
                baseline_rate = apply_capacity_criteria(rows, args)
                metadata["baseline_generated_packet_rate_per_s"] = baseline_rate
                write_csv(session_dir / "capacity_runs.csv", rows, RUN_FIELDS)
                if row["status"] == "success":
                    classification = "NORMAL" if row["normal_workflow_pass"] else "DEGRADED"
                    print(
                        "  COMPLETE ({}): init={} s, overall peak RSS={} GiB, "
                        "generated={}/s, cumulative delivery={}%, speed={}".format(
                            classification,
                            value_text(row["scene_initialization_time_s"]),
                            value_text(row["process_tree_rss_overall_peak_gib"]),
                            value_text(row["generated_packet_rate_per_s"]),
                            value_text(row["delivery_ratio_percent"]),
                            value_text(row["simulation_speed_ratio"], 3),
                        ),
                        flush=True,
                    )
                else:
                    print(f"  STOP/FAIL: {row['error']}", flush=True)
                    if row["status"] == "safety_stopped":
                        safety_stopped = True
                        break
                    if not args.continue_after_failure:
                        break
            if safety_stopped:
                break
            if rows and rows[-1]["status"] != "success" and not args.continue_after_failure:
                break
    except KeyboardInterrupt:
        interrupted = True
        print("\nCapacity scan interrupted. Completed rows will be preserved.", flush=True)
    finally:
        baseline_rate = apply_capacity_criteria(rows, args)
        metadata["baseline_generated_packet_rate_per_s"] = baseline_rate
        write_csv(session_dir / "capacity_runs.csv", rows, RUN_FIELDS)
        metadata["finished_at"] = datetime.now().isoformat(timespec="seconds")
        metadata["completed_runs"] = len(rows)
        metadata["interrupted"] = interrupted
        metadata["safety_stopped"] = safety_stopped
        atomic_json(metadata_path, metadata)
        write_report(session_dir / "capacity_report.md", rows, metadata, args)
        LOCK_PATH.unlink(missing_ok=True)

    scale_summaries = summarize_scales(rows, args)
    recommended_capacity = continuous_summary_limit(
        scale_summaries,
        "aggregate_normal_pass",
    )
    maximum_supported = maximum_completed_scale(scale_summaries)
    print("\nCapacity scan complete")
    print(
        "Recommended satellite count among tested scales: "
        f"{recommended_capacity if recommended_capacity is not None else 'none'}"
    )
    print(
        "Maximum supported satellite count among tested scales: "
        f"{maximum_supported if maximum_supported is not None else 'none'}"
    )
    print(f"Read the complete result: {session_dir / 'capacity_report.md'}")
    if interrupted:
        return 130
    if rows and any(row["status"] not in ("success", "safety_stopped") for row in rows):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
