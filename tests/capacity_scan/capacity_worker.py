from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import traceback
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT_TEXT = str(PROJECT_ROOT)
while PROJECT_ROOT_TEXT in sys.path:
    sys.path.remove(PROJECT_ROOT_TEXT)
sys.path.insert(0, PROJECT_ROOT_TEXT)

CONFIG_ROOT_ENV = "EASYSATSIM_CAPACITY_CONFIG_ROOT"
SEED_ENV = "EASYSATSIM_CAPACITY_SEED"
ROUTE_GUARD_ENV = "EASYSATSIM_CAPACITY_ROUTE_GUARD"
LEGACY_CONFIG_ROOT_ENV = "EASYSATSIM_BENCHMARK_CONFIG_ROOT"
LEGACY_SEED_ENV = "EASYSATSIM_BENCHMARK_SEED"
LEGACY_ROUTE_GUARD_ENV = "EASYSATSIM_BENCHMARK_ROUTE_GUARD"


def _install_capacity_route_display_guard() -> None:
    if (
        os.environ.get(ROUTE_GUARD_ENV) != "1"
        and os.environ.get(LEGACY_ROUTE_GUARD_ENV) != "1"
    ):
        return

    import numpy as np

    from src.simulation.entity.user import User

    original = User.set_routing_path
    if getattr(original, "_easysatsim_capacity_guard", False):
        return

    def guarded_set_routing_path(self, path_list):
        path_array = np.asarray(path_list)
        if path_array.ndim != 2 or path_array.shape[1] != 3:
            raise ValueError(
                "Benchmark routing path must have shape (n, 3); "
                f"received {path_array.shape}."
            )
        capacity = int(self.routing_path.shape[0])
        if path_array.shape[0] <= capacity:
            return original(self, path_list)

        sample_indices = np.linspace(
            0,
            path_array.shape[0] - 1,
            num=capacity,
            dtype=np.int64,
        )
        return original(self, path_array[sample_indices])

    guarded_set_routing_path._easysatsim_capacity_guard = True
    User.set_routing_path = guarded_set_routing_path


def _bootstrap_configuration() -> None:
    config_root = os.environ.get(CONFIG_ROOT_ENV) or os.environ.get(
        LEGACY_CONFIG_ROOT_ENV
    )
    if not config_root:
        return

    from src.tools.config_loader import load_configuration

    load_configuration(config_root)
    seed = int(
        os.environ.get(SEED_ENV)
        or os.environ.get(LEGACY_SEED_ENV, "2026")
    )
    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass
    _install_capacity_route_display_guard()


_bootstrap_configuration()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one isolated EasySatSim local-capacity measurement."
    )
    parser.add_argument("--config-root", required=True, type=Path)
    parser.add_argument("--result-json", required=True, type=Path)
    parser.add_argument("--warmup-seconds", required=True, type=float)
    parser.add_argument("--measurement-seconds", required=True, type=float)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--satellites", required=True, type=int)
    parser.add_argument("--planes", required=True, type=int)
    parser.add_argument("--satellites-per-plane", required=True, type=int)
    parser.add_argument("--repeat", required=True, type=int)
    return parser.parse_args()


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary_path.replace(path)


def metric_snapshot(scene_controller) -> dict:
    shared = scene_controller.shared_metric
    return {
        "wall_monotonic_s": time.monotonic(),
        "simulation_time_s": float(scene_controller.shared_value.current_time[0]),
        "generated_packets": float(shared.global_generate_packets_number.value),
        "arrived_packets": float(shared.global_arrive_packets_number.value),
        "lost_packets": float(shared.global_loss_packets_number.value),
        "generated_bytes": float(shared.global_generate_packets_byte.value),
        "arrived_bytes": float(shared.global_arrive_packets_byte.value),
        "lost_bytes": float(shared.global_loss_packets_byte.value),
        "covered_users": float(shared.global_user_cover_number.value),
        "operational_satellites": float(shared.global_normal_satellite_number.value),
    }


def positive_delta(end: dict, start: dict, key: str) -> float:
    return max(0.0, float(end[key]) - float(start[key]))


def child_process_health(runtime) -> dict:
    health = {}
    for label, process in (
        ("entity", runtime.process_entity),
        ("timer", runtime.process_timer),
    ):
        if process is None:
            health[label] = {"created": False, "alive": False, "exitcode": None}
            continue
        try:
            alive = bool(process.is_alive())
        except (AssertionError, OSError, ValueError):
            alive = False
        try:
            exitcode = process.exitcode
        except (AssertionError, OSError, ValueError):
            exitcode = None
        health[label] = {"created": True, "alive": alive, "exitcode": exitcode}
    health["healthy"] = bool(
        health["entity"]["alive"] and health["timer"]["alive"]
    )
    return health


def run_worker(args: argparse.Namespace) -> int:
    from PyQt5.QtCore import QTimer
    from PyQt5.QtWidgets import QApplication

    from configuration import simulation_config as cg
    from src.simulation.visualization.simulation_control_window import SimulationControlWindow

    result = {
        "status": "starting",
        "satellites": args.satellites,
        "planes": args.planes,
        "satellites_per_plane": args.satellites_per_plane,
        "repeat": args.repeat,
        "seed": args.seed,
        "warmup_seconds": args.warmup_seconds,
        "measurement_seconds": args.measurement_seconds,
        "traffic": "bidirectional Beijing-Tokyo test-mode traffic",
        "physical_layer_enabled": True,
        "satellite_cone_angle_degrees": float(cg.SATELLITE_CONE_ANGLE),
        "coverage_radius_km": float(cg.COVER_RADIUS),
        "isl_min_snr_db": float(cg.ISL_MIN_SNR_DB),
        "capacity_route_display_guard": True,
        "capacity_route_display_capacity": 100,
        "capacity_route_display_policy": (
            "Routes longer than the existing visualization buffer are evenly "
            "sampled for display only; network metrics retain the complete path."
        ),
    }
    atomic_write_json(args.result_json, result)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("EasySatSim Local Capacity Scan")

    scene_options = {
        "test_mode": True,
        "user1_latitude": 39.916668,
        "user1_longtitude": 116.383331,
        "user2_latitude": 35.652832,
        "user2_longtitude": 139.839478,
        "direct_connection_mode": False,
    }
    window = SimulationControlWindow(
        output_console=False,
        auto_start=False,
        running_time=None,
        scene_options=scene_options,
        config_root=args.config_root,
    )
    window.show()

    state: dict[str, object] = {
        "samples": [],
        "measurement_start": None,
        "measurement_end": None,
        "finished": False,
    }

    original_runtime_start = window.runtime.start

    def timed_runtime_start(*runtime_args, **runtime_kwargs):
        started = time.perf_counter()
        value = original_runtime_start(*runtime_args, **runtime_kwargs)
        result["scene_initialization_time_s"] = time.perf_counter() - started
        return value

    window.runtime.start = timed_runtime_start

    sample_timer = QTimer(window)
    sample_timer.setInterval(1000)

    def capture_periodic_sample() -> None:
        controller = window.runtime.scene_controller
        if controller is None:
            return
        health = child_process_health(window.runtime)
        state["last_child_process_health"] = health
        if not health["healthy"]:
            fail(
                "A simulation child process exited before the measurement completed.",
                json.dumps(health, indent=2),
            )
            return
        try:
            state["samples"].append(metric_snapshot(controller))
        except Exception:
            return

    sample_timer.timeout.connect(capture_periodic_sample)

    def stop_and_exit(exit_code: int) -> None:
        if state["finished"]:
            return
        state["finished"] = True
        sample_timer.stop()
        try:
            if window.state == window.STATE_RUNNING:
                window._stop_simulation()
        finally:
            window.close()
            app.exit(exit_code)

    def fail(message: str, details: str | None = None) -> None:
        result["status"] = "failed"
        result["error"] = message
        result["child_process_health"] = child_process_health(window.runtime)
        if details:
            result["traceback"] = details
        result["finished_monotonic_s"] = time.monotonic()
        atomic_write_json(args.result_json, result)
        stop_and_exit(1)

    def capture_measurement_start() -> None:
        try:
            health = child_process_health(window.runtime)
            if not health["healthy"]:
                fail(
                    "A simulation child process exited during warm-up.",
                    json.dumps(health, indent=2),
                )
                return
            state["measurement_start"] = metric_snapshot(window.runtime.scene_controller)
            result["measurement_start_monotonic_s"] = state["measurement_start"]["wall_monotonic_s"]
        except Exception as exc:
            fail(f"Could not capture the measurement baseline: {exc}", traceback.format_exc())

    def finish_measurement() -> None:
        try:
            health = child_process_health(window.runtime)
            if not health["healthy"]:
                fail(
                    "A simulation child process exited before finalization.",
                    json.dumps(health, indent=2),
                )
                return
            measurement_start = state["measurement_start"]
            if measurement_start is None:
                raise RuntimeError("The warm-up baseline was not captured.")

            measurement_end = metric_snapshot(window.runtime.scene_controller)
            state["measurement_end"] = measurement_end
            generated = positive_delta(measurement_end, measurement_start, "generated_packets")
            arrived = positive_delta(measurement_end, measurement_start, "arrived_packets")
            lost = positive_delta(measurement_end, measurement_start, "lost_packets")
            generated_bytes = positive_delta(measurement_end, measurement_start, "generated_bytes")
            arrived_bytes = positive_delta(measurement_end, measurement_start, "arrived_bytes")
            lost_bytes = positive_delta(measurement_end, measurement_start, "lost_bytes")
            wall_delta = positive_delta(measurement_end, measurement_start, "wall_monotonic_s")
            simulation_delta = positive_delta(measurement_end, measurement_start, "simulation_time_s")
            cumulative_generated = max(0.0, measurement_end["generated_packets"])
            cumulative_arrived = max(0.0, measurement_end["arrived_packets"])
            cumulative_lost = max(0.0, measurement_end["lost_packets"])
            cumulative_generated_bytes = max(0.0, measurement_end["generated_bytes"])
            cumulative_arrived_bytes = max(0.0, measurement_end["arrived_bytes"])
            cumulative_lost_bytes = max(0.0, measurement_end["lost_bytes"])
            delivery_ratio = (
                cumulative_arrived / cumulative_generated * 100.0
                if cumulative_generated > 0
                else 0.0
            )
            loss_ratio = (
                cumulative_lost / cumulative_generated * 100.0
                if cumulative_generated > 0
                else 0.0
            )
            window_arrival_to_generation_ratio = (
                arrived / generated * 100.0 if generated > 0 else 0.0
            )
            in_flight_packets = max(
                0.0,
                cumulative_generated - cumulative_arrived - cumulative_lost,
            )
            simulation_speed_ratio = (simulation_delta / wall_delta) if wall_delta > 0 else 0.0
            generated_packet_rate = (generated / wall_delta) if wall_delta > 0 else 0.0
            arrived_packet_rate = (arrived / wall_delta) if wall_delta > 0 else 0.0
            lost_packet_rate = (lost / wall_delta) if wall_delta > 0 else 0.0

            result.update(
                {
                    "status": "success",
                    "measurement_start_monotonic_s": measurement_start["wall_monotonic_s"],
                    "measurement_end_monotonic_s": measurement_end["wall_monotonic_s"],
                    "measurement_wall_time_s": wall_delta,
                    "measurement_simulation_time_s": simulation_delta,
                    "simulation_speed_ratio": simulation_speed_ratio,
                    "generated_packets": generated,
                    "arrived_packets": arrived,
                    "lost_packets": lost,
                    "generated_bytes": generated_bytes,
                    "arrived_bytes": arrived_bytes,
                    "lost_bytes": lost_bytes,
                    "cumulative_generated_packets_at_end": cumulative_generated,
                    "cumulative_arrived_packets_at_end": cumulative_arrived,
                    "cumulative_lost_packets_at_end": cumulative_lost,
                    "cumulative_generated_bytes_at_end": cumulative_generated_bytes,
                    "cumulative_arrived_bytes_at_end": cumulative_arrived_bytes,
                    "cumulative_lost_bytes_at_end": cumulative_lost_bytes,
                    "delivery_ratio_percent": delivery_ratio,
                    "explicit_loss_ratio_percent": loss_ratio,
                    "window_arrival_to_generation_percent": window_arrival_to_generation_ratio,
                    "in_flight_packets_at_end": in_flight_packets,
                    "generated_packet_rate_per_s": generated_packet_rate,
                    "arrived_packet_rate_per_s": arrived_packet_rate,
                    "lost_packet_rate_per_s": lost_packet_rate,
                    "covered_users_at_end": measurement_end["covered_users"],
                    "operational_satellites_at_end": measurement_end["operational_satellites"],
                    "realtime_reception_pass": bool(
                        generated > 0
                        and delivery_ratio >= 95.0
                        and simulation_speed_ratio >= 0.95
                    ),
                    "delivery_ratio_definition": (
                        "cumulative arrived packets divided by cumulative generated "
                        "packets at measurement end"
                    ),
                    "window_rate_definition": (
                        "counter deltas during the post-warm-up measurement window"
                    ),
                    "realtime_criteria": (
                        "measurement-window generated packets > 0; cumulative delivery "
                        "ratio >= 95%; simulation/wall time >= 0.95"
                    ),
                    "metric_sample_count": len(state["samples"]),
                    "child_process_health": health,
                    "finished_monotonic_s": time.monotonic(),
                }
            )
            atomic_write_json(args.result_json, result)
            stop_and_exit(0)
        except Exception as exc:
            fail(f"Could not finalize the measurement: {exc}", traceback.format_exc())

    def start_simulation() -> None:
        try:
            visual_started = time.perf_counter()
            window._start_simulation()
            result["visualization_ready_time_s"] = time.perf_counter() - visual_started
            if window.state != window.STATE_RUNNING:
                fail("The simulation did not enter the running state. Check the run log.")
                return

            health = child_process_health(window.runtime)
            if not health["healthy"]:
                fail(
                    "The simulation child processes did not both start successfully.",
                    json.dumps(health, indent=2),
                )
                return

            result["simulation_started_monotonic_s"] = time.monotonic()
            sample_timer.start()
            capture_periodic_sample()
            QTimer.singleShot(max(1, int(args.warmup_seconds * 1000)), capture_measurement_start)
            total_ms = max(2, int((args.warmup_seconds + args.measurement_seconds) * 1000))
            QTimer.singleShot(total_ms, finish_measurement)
        except Exception as exc:
            fail(f"Could not start the simulation: {exc}", traceback.format_exc())

    QTimer.singleShot(0, start_simulation)
    exit_code = app.exec_()
    return int(exit_code)


def main() -> int:
    args = parse_args()
    args.config_root = args.config_root.resolve()
    args.result_json = args.result_json.resolve()
    try:
        return run_worker(args)
    except Exception as exc:
        payload = {
            "status": "failed",
            "satellites": args.satellites,
            "planes": args.planes,
            "satellites_per_plane": args.satellites_per_plane,
            "repeat": args.repeat,
            "seed": args.seed,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "finished_monotonic_s": time.monotonic(),
        }
        atomic_write_json(args.result_json, payload)
        print(payload["traceback"], file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
