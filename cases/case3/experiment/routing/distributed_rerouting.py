from configuration import simulation_config as cg
from src.simulation.stack.protocol_func.network_func import MinHopRouting
from src.simulation.variable.virtual_store import VirtualStore


class DistributedLocalRerouting:
    @staticmethod
    def routing_algorithm(entity, cross_layer_message, src_satellite_id, dst_satellite_id):
        default_next_hop_id = MinHopRouting.routing_algorithm(
            entity=entity,
            cross_layer_message=cross_layer_message,
            src_satellite_id=src_satellite_id,
            dst_satellite_id=dst_satellite_id,
        )
        visited_satellite_ids = _visited_satellite_ids(cross_layer_message)
        is_default_available = _is_valid_next_hop(
            entity=entity,
            next_hop_id=default_next_hop_id,
            visited_satellite_ids=visited_satellite_ids,
        )
        if is_default_available:
            return default_next_hop_id

        selected_next_hop_id = _select_local_bypass_next_hop(
            entity=entity,
            src_satellite_id=src_satellite_id,
            dst_satellite_id=dst_satellite_id,
            visited_satellite_ids=visited_satellite_ids,
        )
        return selected_next_hop_id


def _select_local_bypass_next_hop(
        entity,
        src_satellite_id,
        dst_satellite_id,
        visited_satellite_ids):
    candidates = []
    for neighbor_id in _neighbor_ids(src_satellite_id):
        is_available = _is_valid_next_hop(
            entity=entity,
            next_hop_id=neighbor_id,
            visited_satellite_ids=visited_satellite_ids,
        )
        if not is_available:
            continue
        candidates.append((
            _torus_distance(neighbor_id, dst_satellite_id),
            _neighbor_delay(entity, neighbor_id),
            neighbor_id,
        ))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][2]


def _is_valid_next_hop(entity, next_hop_id, visited_satellite_ids):
    if next_hop_id is None:
        return False
    if next_hop_id in visited_satellite_ids:
        return False
    if not VirtualStore.satellite_survival_state.get(next_hop_id, True):
        return False
    return True


def _neighbor_entry(entity, satellite_id):
    return entity.neighbor_table.get(satellite_id)


def _neighbor_delay(entity, satellite_id):
    entry = _neighbor_entry(entity=entity, satellite_id=satellite_id)
    if not entry:
        return 0.0
    return float(entry.get("delay", 0.0))


def _visited_satellite_ids(cross_layer_message):
    ip_list = cross_layer_message.data_others.get("ip_list") or []
    visited = set()
    for ip_address in ip_list:
        satellite_id = VirtualStore.satellite_ip_to_id_table.get(ip_address)
        if satellite_id is not None:
            visited.add(satellite_id)
    return visited


def _neighbor_ids(satellite_id):
    orbit_id = satellite_id // cg.SATELLITE_NUMBER_PRE_ORBIT
    in_orbit_id = satellite_id % cg.SATELLITE_NUMBER_PRE_ORBIT
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


def _torus_distance(src_satellite_id, dst_satellite_id):
    src_orbit_id, src_in_orbit_id = _satellite_grid(src_satellite_id)
    dst_orbit_id, dst_in_orbit_id = _satellite_grid(dst_satellite_id)
    orbit_distance = min(
        (src_orbit_id - dst_orbit_id) % cg.ORBIT_NUMBER,
        (dst_orbit_id - src_orbit_id) % cg.ORBIT_NUMBER,
    )
    in_orbit_distance = min(
        (src_in_orbit_id - dst_in_orbit_id) % cg.SATELLITE_NUMBER_PRE_ORBIT,
        (dst_in_orbit_id - src_in_orbit_id) % cg.SATELLITE_NUMBER_PRE_ORBIT,
    )
    return orbit_distance + in_orbit_distance


def _satellite_grid(satellite_id):
    return (
        satellite_id // cg.SATELLITE_NUMBER_PRE_ORBIT,
        satellite_id % cg.SATELLITE_NUMBER_PRE_ORBIT,
    )

