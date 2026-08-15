import hashlib
import json

from configuration import simulation_config as cg
from cases.case3.experiment.data.user_groups import (
    CLUSTER_RADIUS_DEG,
    COORDINATE_MODEL,
    GROUP_A_SUBCENTERS,
    GROUP_B_SUBCENTERS,
    build_case3_user_locations,
)
from cases.case3.experiment.integration.paths import resolve_project_path
from cases.case3.experiment.integration.paths import to_project_relative_path
from src.tools.file_operations import get_project_output_path


def write_run_metadata():
    output_path = resolve_project_path(cg.CASE3_METADATA_FILE_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "path_format": "project-relative-posix",
        "routing_mode": cg.CASE3_ROUTING_MODE,
        "random_seed": cg.CASE3_RANDOM_SEED,
        "output_timestamp": cg.CASE3_OUTPUT_TIMESTAMP,
        "running_time": cg.CASE_RUNNING_TIME_REAL_SECONDS,
        "failed_satellite_id": cg.CASE3_FAILED_SATELLITE_ID,
        "failure_time": cg.CASE3_FAILURE_TIME,
        "centralized_route_refresh_interval": (
            cg.CASE3_CENTRALIZED_ROUTE_REFRESH_INTERVAL
        ),
        "centralized_route_tables": {
            "storage": "experiment/data/centralized_route_tables.npz",
            "unique_states": ["normal", "s377_failed"],
            "deployment_sequence": [
                "normal",
                "normal",
                "normal",
                "s377_failed",
            ],
            "deployment_times": [0.0, 50.0, 100.0, 150.0],
        },
        "event_log_path": to_project_relative_path(
            resolve_project_path(cg.CASE3_EVENT_LOG_FILE_PATH)
        ),
        "network_log_path": to_project_relative_path(
            get_project_output_path(cg.SAVE_FILE_PATH)
        ),
        "constellation": {
            "orbit_number": cg.ORBIT_NUMBER,
            "satellites_per_orbit": cg.SATELLITE_NUMBER_PRE_ORBIT,
            "total_satellites": cg.TOTAL_SATELLITE_NUMBER,
            "inclination_deg": cg.ORBIT_INCLINATION,
            "height_km": cg.ORBIT_HEIGHT,
        },
        "users_and_traffic": {
            "user_number": cg.USER_NUMBER,
            "pair_count": cg.CASE3_PAIR_COUNT,
            "traffic_start_time": cg.CASE3_TRAFFIC_START_TIME,
            "send_period": cg.CASE3_CONTROLLED_SEND_PERIOD,
            "packet_size_byte": cg.CASE3_CONTROLLED_PACKET_SIZE_BYTE,
            "coordinate_model": COORDINATE_MODEL,
            "coordinate_seed": cg.CASE3_RANDOM_SEED,
            "cluster_radius_deg": CLUSTER_RADIUS_DEG,
            "group_a_subcenters": GROUP_A_SUBCENTERS,
            "group_b_subcenters": GROUP_B_SUBCENTERS,
            "coordinate_sha256": _coordinate_sha256(),
        },
        "physical_layer": _physical_layer_snapshot(),
    }
    output_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def _coordinate_sha256():
    serialized = json.dumps(
        build_case3_user_locations(),
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _physical_layer_snapshot():
    names = (
        "PHYSICAL_LAYER_ENABLE",
        "PHYSICAL_LAYER_ENABLE_DOPPLER",
        "PHYSICAL_LAYER_ENABLE_DYNAMIC_RATE",
        "PHYSICAL_LAYER_UPDATE_INTERVAL",
        "MIN_ELEVATION_ANGLE_DEG",
        "ISL_TX_POWER_DBM",
        "ISL_TX_ANTENNA_GAIN_DBI",
        "ISL_RX_ANTENNA_GAIN_DBI",
        "ISL_MIN_SNR_DB",
        "ISL_MAX_DISTANCE_M",
        "SGL_TX_POWER_DBM",
        "SGL_TX_ANTENNA_GAIN_DBI",
        "SGL_RX_ANTENNA_GAIN_DBI",
        "SGL_MIN_SNR_DB",
        "SGL_MAX_DISTANCE_M",
    )
    return {name: getattr(cg, name) for name in names}
