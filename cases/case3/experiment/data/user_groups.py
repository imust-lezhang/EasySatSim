import math

import numpy as np

from configuration import simulation_config as cg


COORDINATE_MODEL = "seeded_uniform_disks"
CLUSTER_RADIUS_DEG = 1.0
GROUP_A_SUBCENTERS = (
    (33.6, -7.4),
    (36.0, -3.6),
    (38.2, -6.0),
    (34.7, -1.6),
)
GROUP_B_SUBCENTERS = (
    (32.8, 111.5),
    (35.7, 116.8),
    (38.5, 113.6),
    (34.4, 120.2),
)


def build_case3_user_locations():
    """Return a reproducible random deployment for the configured seed."""
    rng = np.random.default_rng(cg.CASE3_RANDOM_SEED)
    group_a = _build_cluster_locations(
        rng=rng,
        subcenters=GROUP_A_SUBCENTERS,
        count=cg.CASE3_PAIR_COUNT,
    )
    group_b = _build_cluster_locations(
        rng=rng,
        subcenters=GROUP_B_SUBCENTERS,
        count=cg.CASE3_PAIR_COUNT,
    )
    return group_a + group_b


def get_pair_for_user(user_id):
    group_a_start = cg.CASE3_GROUP_A_START_ID
    group_b_start = cg.CASE3_GROUP_B_START_ID
    pair_count = cg.CASE3_PAIR_COUNT

    if group_a_start <= user_id < group_a_start + pair_count:
        pair_id = user_id - group_a_start
        return {
            "pair_id": pair_id,
            "target_user_id": group_b_start + pair_id,
            "direction": "A_to_B",
        }
    if group_b_start <= user_id < group_b_start + pair_count:
        pair_id = user_id - group_b_start
        return {
            "pair_id": pair_id,
            "target_user_id": group_a_start + pair_id,
            "direction": "B_to_A",
        }
    return None


def _build_cluster_locations(rng, subcenters, count):
    locations = []
    for index in range(count):
        center_latitude, center_longitude = subcenters[index % len(subcenters)]

        # sqrt(U) gives a spatially uniform distribution over a disk rather
        # than concentrating users near its center.
        radius_deg = CLUSTER_RADIUS_DEG * math.sqrt(rng.random())
        angle_rad = rng.uniform(0.0, 2.0 * math.pi)
        latitude_offset = radius_deg * math.cos(angle_rad)
        longitude_scale = max(math.cos(math.radians(center_latitude)), 0.55)
        longitude_offset = radius_deg * math.sin(angle_rad) / longitude_scale
        locations.append((
            round(center_latitude + latitude_offset, 6),
            round(center_longitude + longitude_offset, 6),
        ))
    return locations
