from collections import deque

import numpy as np

from src.tools.config_loader import load_configuration


load_configuration("cases/case3/src")

from configuration import simulation_config as cg
from cases.case3.experiment.data.centralized_route_tables import ROUTE_TABLE_FILE
from src.tools.calculation import find_valid_directions


NO_ROUTE = -1


def main():
    normal = _build_normal_table()
    failed = _build_failed_table(cg.CASE3_FAILED_SATELLITE_ID)
    _validate_tables(normal, failed)
    np.savez_compressed(
        ROUTE_TABLE_FILE,
        normal=normal,
        s377_failed=failed,
        orbit_number=np.int64(cg.ORBIT_NUMBER),
        satellites_per_orbit=np.int64(cg.SATELLITE_NUMBER_PRE_ORBIT),
        failed_satellite_id=np.int64(cg.CASE3_FAILED_SATELLITE_ID),
    )
    print(f"[Case 3 route tables] Saved: {ROUTE_TABLE_FILE}")
    print(f"[Case 3 route tables] Shape: {normal.shape}")
    print("[Case 3 route tables] Unique topology states: normal, S377 failed")
    print("[Case 3 route tables] Deployment sequence: normal, normal, normal, S377 failed")


def _build_normal_table():
    total = cg.TOTAL_SATELLITE_NUMBER
    table = np.full((total, total), NO_ROUTE, dtype=np.int16)
    for source_id in range(total):
        source = _satellite_grid(source_id)
        for destination_id in range(total):
            if source_id == destination_id:
                continue
            _directions, next_hop_id = find_valid_directions(
                origin=source,
                target=_satellite_grid(destination_id),
                N=cg.ORBIT_NUMBER,
                M=cg.SATELLITE_NUMBER_PRE_ORBIT,
            )
            if next_hop_id is not None:
                table[source_id, destination_id] = next_hop_id
    return table


def _build_failed_table(failed_satellite_id):
    total = cg.TOTAL_SATELLITE_NUMBER
    table = np.full((total, total), NO_ROUTE, dtype=np.int16)
    available = set(range(total)) - {failed_satellite_id}
    for source_id in sorted(available):
        first_hops = _shortest_first_hops(source_id, available)
        for destination_id, next_hop_id in first_hops.items():
            table[source_id, destination_id] = next_hop_id
    return table


def _shortest_first_hops(source_id, available):
    first_hops = {}
    visited = {source_id}
    queue = deque()
    for neighbor_id in _neighbor_ids(source_id):
        if neighbor_id not in available:
            continue
        visited.add(neighbor_id)
        first_hops[neighbor_id] = neighbor_id
        queue.append(neighbor_id)

    while queue:
        current_id = queue.popleft()
        current_first_hop = first_hops[current_id]
        for neighbor_id in _neighbor_ids(current_id):
            if neighbor_id not in available or neighbor_id in visited:
                continue
            visited.add(neighbor_id)
            first_hops[neighbor_id] = current_first_hop
            queue.append(neighbor_id)
    return first_hops


def _neighbor_ids(satellite_id):
    orbit_id, in_orbit_id = _satellite_grid(satellite_id)
    candidates = (
        ((orbit_id - 1) % cg.ORBIT_NUMBER, in_orbit_id),
        ((orbit_id + 1) % cg.ORBIT_NUMBER, in_orbit_id),
        (orbit_id, (in_orbit_id - 1) % cg.SATELLITE_NUMBER_PRE_ORBIT),
        (orbit_id, (in_orbit_id + 1) % cg.SATELLITE_NUMBER_PRE_ORBIT),
    )
    return [
        orbit * cg.SATELLITE_NUMBER_PRE_ORBIT + satellite
        for orbit, satellite in candidates
    ]


def _satellite_grid(satellite_id):
    return (
        satellite_id // cg.SATELLITE_NUMBER_PRE_ORBIT,
        satellite_id % cg.SATELLITE_NUMBER_PRE_ORBIT,
    )


def _validate_tables(normal, failed):
    total = cg.TOTAL_SATELLITE_NUMBER
    failed_id = cg.CASE3_FAILED_SATELLITE_ID
    expected_routes = total * (total - 1)
    if np.count_nonzero(normal != NO_ROUTE) != expected_routes:
        raise ValueError("Normal route table is incomplete.")
    expected_failed_routes = (total - 1) * (total - 2)
    if np.count_nonzero(failed != NO_ROUTE) != expected_failed_routes:
        raise ValueError("S377-failed route table is incomplete.")
    if np.any(failed[failed_id, :] != NO_ROUTE):
        raise ValueError("Failed satellite unexpectedly has outgoing routes.")
    if np.any(failed[:, failed_id] != NO_ROUTE):
        raise ValueError("Failed satellite unexpectedly has incoming routes.")
    if np.any(failed == failed_id):
        raise ValueError("A failed-state route still selects S377 as its next hop.")


if __name__ == "__main__":
    main()
