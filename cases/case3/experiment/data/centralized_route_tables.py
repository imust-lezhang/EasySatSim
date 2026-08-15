from pathlib import Path

import numpy as np

from configuration import simulation_config as cg


ROUTE_TABLE_FILE = Path(__file__).with_name("centralized_route_tables.npz")
NORMAL_TABLE_NAME = "normal"
FAILED_TABLE_NAME = "s377_failed"
DEPLOYMENT_SEQUENCE = (
    NORMAL_TABLE_NAME,
    NORMAL_TABLE_NAME,
    NORMAL_TABLE_NAME,
    FAILED_TABLE_NAME,
)


def load_centralized_route_tables():
    if not ROUTE_TABLE_FILE.is_file():
        raise FileNotFoundError(
            f"Missing precomputed Case 3 route tables: {ROUTE_TABLE_FILE}. "
            "Run `python -m cases.case3.experiment.data."
            "generate_centralized_route_tables` first."
        )

    with np.load(ROUTE_TABLE_FILE, allow_pickle=False) as archive:
        _validate_archive(archive)
        return {
            NORMAL_TABLE_NAME: archive[NORMAL_TABLE_NAME].copy(),
            FAILED_TABLE_NAME: archive[FAILED_TABLE_NAME].copy(),
        }


def table_name_for_deployment(deployment_index):
    if deployment_index < 0:
        raise ValueError("Deployment index must not be negative.")
    if deployment_index >= len(DEPLOYMENT_SEQUENCE):
        return DEPLOYMENT_SEQUENCE[-1]
    return DEPLOYMENT_SEQUENCE[deployment_index]


def _validate_archive(archive):
    required = {
        NORMAL_TABLE_NAME,
        FAILED_TABLE_NAME,
        "orbit_number",
        "satellites_per_orbit",
        "failed_satellite_id",
    }
    missing = required - set(archive.files)
    if missing:
        raise ValueError(f"Route-table archive is incomplete: {sorted(missing)}")

    expected_shape = (cg.TOTAL_SATELLITE_NUMBER, cg.TOTAL_SATELLITE_NUMBER)
    for table_name in (NORMAL_TABLE_NAME, FAILED_TABLE_NAME):
        table = archive[table_name]
        if table.shape != expected_shape:
            raise ValueError(
                f"Route table {table_name!r} has shape {table.shape}; "
                f"expected {expected_shape}."
            )

    archive_values = {
        "orbit_number": int(archive["orbit_number"]),
        "satellites_per_orbit": int(archive["satellites_per_orbit"]),
        "failed_satellite_id": int(archive["failed_satellite_id"]),
    }
    expected_values = {
        "orbit_number": cg.ORBIT_NUMBER,
        "satellites_per_orbit": cg.SATELLITE_NUMBER_PRE_ORBIT,
        "failed_satellite_id": cg.CASE3_FAILED_SATELLITE_ID,
    }
    if archive_values != expected_values:
        raise ValueError(
            "Precomputed route tables do not match the active Case 3 "
            f"configuration: archive={archive_values}, expected={expected_values}."
        )
