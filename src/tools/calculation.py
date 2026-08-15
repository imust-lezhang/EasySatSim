import numpy as np
import time
import math
from dataclasses import dataclass, replace
from numba import jit
from configuration import simulation_config as cg


LIGHT_SPEED_MPS = 299792458.0


@jit(nopython=True)
def get_distance_3D(position_3D_1, position_3D_2):
    return np.linalg.norm(position_3D_1 - position_3D_2)


def get_current_timestamp_ms():
    # Get the timestamp of the current time (in seconds)
    timestamp_sec = time.time()
    # Convert to milliseconds
    timestamp_ms = int(timestamp_sec * 1000)
    return timestamp_ms


def position_3D_to_2D_array(positions_3D):
    coords = positions_3D.reshape(-1, 3)
    # Earth parameters
    R_earth = 6371  # Earth radius in meters (WGS-84)


    x = coords[:, 0]
    y = coords[:, 1]
    z = coords[:, 2]


    # Longitude
    longitude = np.arctan2(y, x)


    # Hypotenuse from x and y
    hyp = np.sqrt(x**2 + y**2)


    # Latitude
    latitude = np.arctan2(z, hyp)


    # Altitude
    altitude = np.sqrt(x**2 + y**2 + z**2) - R_earth


    # Convert radians to degrees
    longitude = np.degrees(longitude)
    latitude = np.degrees(latitude)


    return np.vstack((latitude, longitude, altitude)).T


def position_3D_to_2D_signal(position_3D):
    # Earth radius (in meters)
    earth_radius = 6378137.0
    # Decompose x, y, z
    x, y, z = position_3D
    # Calculate the distance from the center of the earth
    r = np.sqrt(x ** 2 + y ** 2 + z ** 2)
    # Calculate longitude
    longitude = np.arctan2(y, x)
    # Calculate latitude
    latitude = np.arcsin(z / r)
    # Calculate altitude
    height = r - earth_radius
    # Convert longitude and latitude from radians to degrees
    longitude_deg = np.degrees(longitude)
    latitude_deg = np.degrees(latitude)
    # Create an array containing latitude, longitude, and altitude
    geodetic_coords = np.array([latitude_deg, longitude_deg, height])
    return geodetic_coords


# h is the height relative to the Earth's surface, not the Earth's origin
def position_2D_to_3D(lat, lon, h=0):
    # Earth radius (in kilometers)
    R = 6371.0
    # Convert latitude and longitude from degrees to radians
    lat = np.radians(lat)
    lon = np.radians(lon)
    # XYZ coordinates
    x = (R + h) * np.cos(lat) * np.cos(lon)
    y = (R + h) * np.cos(lat) * np.sin(lon)
    z = (R + h) * np.sin(lat)
    return np.array([x, y, z])


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in kilometers
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    a = np.sin(delta_phi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c


def get_propagation_delay(position_3d_1, position_3d_2):
    return np.linalg.norm(position_3d_1 - position_3d_2) / 299792 * 1000


def calculate_latency_ms(position_3d_1, position_3d_2, data_size_byte):
    transmission_delay = data_size_byte / cg.LINK_TRANSMIT_RATE  # The amount of bits the link can handle 100Mbps
    propagation_delay = get_propagation_delay(position_3d_1, position_3d_2)  # Propagation delay
    processing_delay = cg.PROCESSING_TIME  # Processing delay  1e4byte/s
    return transmission_delay + processing_delay + propagation_delay


@jit(nopython=True)
def heuristic(current, goal, cols):
    # Calculate the Manhattan distance, considering a cyclic grid
    current_row, current_col = divmod(current, cols)
    goal_row, goal_col = divmod(goal, cols)
    # Consider cyclic conditions and calculate the minimum distance
    row_diff = min(abs(current_row - goal_row), cols - abs(current_row - goal_row))
    col_diff = min(abs(current_col - goal_col), cols - abs(current_col - goal_col))
    return row_diff + col_diff


def _calculate_vector(src, dst, N, M):
    dx = (dst[0] - src[0] + N) % N
    dx = dx if dx <= N // 2 else dx - N
    dy = (dst[1] - src[1] + M) % M
    dy = dy if dy <= M // 2 else dy - M
    return np.array([dx, dy])


def _calculate_angle(v1, v2):
    dot_product = np.dot(v1, v2)
    norms_product = np.linalg.norm(v1) * np.linalg.norm(v2)
    if np.isclose(norms_product, 0):
        cos_theta = 0
    else:
        cos_theta = dot_product / norms_product
    angle = np.arccos(cos_theta) * 180 / np.pi
    return angle


def find_valid_directions(origin, target, N, M):
    min_angle = 999
    next_point_id = None
    directions = (
         (origin[0] - 1, origin[1]),
         (origin[0] + 1, origin[1]),
        (origin[0], origin[1] - 1),
         (origin[0], origin[1] + 1)
    )
    target_vector = _calculate_vector(origin, target, N, M)
    valid_directions = {}
    for point in directions:
        next_point = ((point[0] % N), (point[1] % M))
        move_vector = _calculate_vector(origin, next_point, N, M)
        angle = _calculate_angle(target_vector, move_vector)
        if angle <= 90:
            if angle < min_angle:
                min_angle = angle
                next_point_id = next_point[0] * M + next_point[1]
            valid_directions[next_point[0] * M + next_point[1]] = angle
    return valid_directions, next_point_id


@dataclass
class LinkPhysicalState:
    link_type: str
    distance_m: float
    propagation_delay_ms: float
    radial_velocity_mps: float
    doppler_shift_hz: float
    path_loss_db: float
    received_power_dbm: float
    noise_power_dbm: float
    snr_db: float
    effective_rate_bps: float
    transmission_delay_ms: float
    processing_delay_ms: float
    total_link_delay_ms: float
    is_available: bool
    updated_at: float
    reason: str = ""


class PhysicalLayerModel:
    """
    Network-level physical-layer approximation.
    """
    dict_link_state = {}
    dict_position_cache = {}
    update_count = 0

    @staticmethod
    def reset_cache():
        PhysicalLayerModel.dict_link_state = {}
        PhysicalLayerModel.dict_position_cache = {}
        PhysicalLayerModel.update_count = 0
        return

    @staticmethod
    def validate_config():
        for link_type in ("isl", "sgl"):
            link_config = PhysicalLayerModel.get_link_config(link_type)
            if link_config["carrier_frequency_hz"] <= 0:
                raise ValueError(link_type + ": carrier_frequency_hz must be positive.")
            if link_config["bandwidth_hz"] <= 0:
                raise ValueError(link_type + ": bandwidth_hz must be positive.")
            if link_config["max_distance_m"] <= 0:
                raise ValueError(link_type + ": max_distance_m must be positive.")
            if link_config["static_rate_bps"] <= 0:
                raise ValueError(link_type + ": static_rate_bps must be positive.")
            if link_config["min_effective_rate_bps"] < 0:
                raise ValueError(link_type + ": min_effective_rate_bps must not be negative.")
            if link_config["rate_mapping_mode"] not in ("discrete", "shannon", "static"):
                raise ValueError(link_type + ": rate_mapping_mode must be discrete, shannon, or static.")
            if not link_config["discrete_rate_table"]:
                raise ValueError(link_type + ": discrete_rate_table must not be empty.")
        return

    @staticmethod
    def get_link_config(link_type):
        if link_type == "isl":
            return {
                "carrier_frequency_hz": cg.ISL_CARRIER_FREQUENCY_HZ,
                "bandwidth_hz": cg.ISL_BANDWIDTH_HZ,
                "tx_power_dbm": cg.ISL_TX_POWER_DBM,
                "tx_antenna_gain_dbi": cg.ISL_TX_ANTENNA_GAIN_DBI,
                "rx_antenna_gain_dbi": cg.ISL_RX_ANTENNA_GAIN_DBI,
                "system_loss_db": cg.ISL_SYSTEM_LOSS_DB,
                "atmospheric_loss_db": cg.ISL_ATMOSPHERIC_LOSS_DB,
                "noise_figure_db": cg.ISL_NOISE_FIGURE_DB,
                "min_snr_db": cg.ISL_MIN_SNR_DB,
                "max_distance_m": cg.ISL_MAX_DISTANCE_M,
                "doppler_compensation_hz": cg.ISL_DOPPLER_COMPENSATION_HZ,
                "residual_doppler_loss_per_khz_db": cg.ISL_RESIDUAL_DOPPLER_LOSS_PER_KHZ_DB,
                "static_rate_bps": cg.ISL_STATIC_RATE_BPS,
                "min_effective_rate_bps": cg.ISL_MIN_EFFECTIVE_RATE_BPS,
                "spectral_efficiency": cg.ISL_SPECTRAL_EFFICIENCY,
                "rate_mapping_mode": cg.ISL_RATE_MAPPING_MODE,
                "drop_link_if_doppler_exceeded": cg.ISL_DROP_LINK_IF_DOPPLER_EXCEEDED,
                "discrete_rate_table": cg.ISL_DISCRETE_RATE_TABLE,
            }
        if link_type == "sgl":
            return {
                "carrier_frequency_hz": cg.SGL_CARRIER_FREQUENCY_HZ,
                "bandwidth_hz": cg.SGL_BANDWIDTH_HZ,
                "tx_power_dbm": cg.SGL_TX_POWER_DBM,
                "tx_antenna_gain_dbi": cg.SGL_TX_ANTENNA_GAIN_DBI,
                "rx_antenna_gain_dbi": cg.SGL_RX_ANTENNA_GAIN_DBI,
                "system_loss_db": cg.SGL_SYSTEM_LOSS_DB,
                "atmospheric_loss_db": cg.SGL_ATMOSPHERIC_LOSS_DB,
                "noise_figure_db": cg.SGL_NOISE_FIGURE_DB,
                "min_snr_db": cg.SGL_MIN_SNR_DB,
                "max_distance_m": cg.SGL_MAX_DISTANCE_M,
                "doppler_compensation_hz": cg.SGL_DOPPLER_COMPENSATION_HZ,
                "residual_doppler_loss_per_khz_db": cg.SGL_RESIDUAL_DOPPLER_LOSS_PER_KHZ_DB,
                "static_rate_bps": cg.SGL_STATIC_RATE_BPS,
                "min_effective_rate_bps": cg.SGL_MIN_EFFECTIVE_RATE_BPS,
                "spectral_efficiency": cg.SGL_SPECTRAL_EFFICIENCY,
                "rate_mapping_mode": cg.SGL_RATE_MAPPING_MODE,
                "drop_link_if_doppler_exceeded": cg.SGL_DROP_LINK_IF_DOPPLER_EXCEEDED,
                "discrete_rate_table": cg.SGL_DISCRETE_RATE_TABLE,
            }
        raise ValueError("link_type must be isl or sgl.")

    @staticmethod
    def infer_link_type(source_category, target_category):
        if source_category == "satellite" and target_category == "satellite":
            return "isl"
        return "sgl"

    @staticmethod
    def calculate_distance_m(position_3d_1, position_3d_2):
        position_1_m = np.asarray(position_3d_1, dtype=np.float64) * 1000.0
        position_2_m = np.asarray(position_3d_2, dtype=np.float64) * 1000.0
        return float(np.linalg.norm(position_1_m - position_2_m))

    @staticmethod
    def calculate_propagation_delay_ms(distance_m):
        return distance_m / LIGHT_SPEED_MPS * 1000.0

    @staticmethod
    def calculate_doppler_shift_hz(radial_velocity_mps, carrier_frequency_hz):
        return -(radial_velocity_mps / LIGHT_SPEED_MPS) * carrier_frequency_hz

    @staticmethod
    def calculate_path_loss_db(distance_m, carrier_frequency_hz):
        if distance_m <= 0:
            distance_m = 1.0
        value = 4.0 * math.pi * carrier_frequency_hz * distance_m / LIGHT_SPEED_MPS
        return 20.0 * math.log10(value)

    @staticmethod
    def calculate_noise_power_dbm(bandwidth_hz, noise_figure_db):
        return -174.0 + 10.0 * math.log10(bandwidth_hz) + noise_figure_db

    @staticmethod
    def calculate_rate_bps(snr_db, link_config):
        if link_config["rate_mapping_mode"] == "static":
            return link_config["static_rate_bps"]

        if link_config["rate_mapping_mode"] == "shannon":
            snr_linear = 10.0 ** (snr_db / 10.0)
            rate_bps = link_config["spectral_efficiency"] * link_config["bandwidth_hz"] * math.log2(1.0 + snr_linear)
            return max(0.0, rate_bps)

        rate_bps = 0.0
        for threshold_db, candidate_rate_bps in sorted(link_config["discrete_rate_table"]):
            if snr_db >= threshold_db:
                rate_bps = candidate_rate_bps
        return rate_bps

    @staticmethod
    def calculate_radial_velocity_mps(link_key, source_position_3d, target_position_3d, current_time):
        source_position_m = np.asarray(source_position_3d, dtype=np.float64) * 1000.0
        target_position_m = np.asarray(target_position_3d, dtype=np.float64) * 1000.0
        vector = source_position_m - target_position_m
        distance_m = np.linalg.norm(vector)
        if distance_m <= 0:
            return 0.0

        if link_key not in PhysicalLayerModel.dict_position_cache:
            PhysicalLayerModel.dict_position_cache[link_key] = {
                "source_position_m": source_position_m.copy(),
                "target_position_m": target_position_m.copy(),
                "time": current_time,
            }
            return 0.0

        cache = PhysicalLayerModel.dict_position_cache[link_key]
        delta_time = current_time - cache["time"]
        if delta_time <= 0:
            return 0.0

        source_velocity = (source_position_m - cache["source_position_m"]) / delta_time
        target_velocity = (target_position_m - cache["target_position_m"]) / delta_time
        unit_vector = vector / distance_m
        radial_velocity = float(np.dot(source_velocity - target_velocity, unit_vector))

        cache["source_position_m"] = source_position_m.copy()
        cache["target_position_m"] = target_position_m.copy()
        cache["time"] = current_time
        return radial_velocity

    @staticmethod
    def get_link_state(source_position_3d, target_position_3d, data_size_byte,
                       source_id, target_id, source_category, target_category,
                       current_time, processing_time_ms=None):
        PhysicalLayerModel.validate_config()
        link_type = PhysicalLayerModel.infer_link_type(source_category, target_category)
        link_config = PhysicalLayerModel.get_link_config(link_type)
        if processing_time_ms is None:
            processing_time_ms = cg.PHYSICAL_LAYER_DEFAULT_PROCESSING_TIME
        link_key = (source_category, source_id, target_category, target_id, link_type)

        if not cg.PHYSICAL_LAYER_ENABLE:
            return PhysicalLayerModel._build_static_state(
                link_type=link_type,
                source_position_3d=source_position_3d,
                target_position_3d=target_position_3d,
                data_size_byte=data_size_byte,
                current_time=current_time,
                processing_time_ms=processing_time_ms,
                static_rate_bps=link_config["static_rate_bps"],
            )

        cached_state = PhysicalLayerModel.dict_link_state.get(link_key)
        if cg.PHYSICAL_LAYER_USE_CACHE and cached_state is not None:
            if current_time - cached_state.updated_at < cg.PHYSICAL_LAYER_UPDATE_INTERVAL:
                return PhysicalLayerModel._update_packet_delay(cached_state, data_size_byte, processing_time_ms)

        state = PhysicalLayerModel._calculate_dynamic_state(
            link_key=link_key,
            link_type=link_type,
            link_config=link_config,
            source_position_3d=source_position_3d,
            target_position_3d=target_position_3d,
            data_size_byte=data_size_byte,
            current_time=current_time,
            processing_time_ms=processing_time_ms,
        )
        PhysicalLayerModel.dict_link_state[link_key] = state
        PhysicalLayerModel.update_count += 1
        return state

    @staticmethod
    def _build_static_state(link_type, source_position_3d, target_position_3d, data_size_byte,
                            current_time, processing_time_ms, static_rate_bps):
        distance_m = PhysicalLayerModel.calculate_distance_m(source_position_3d, target_position_3d)
        propagation_delay_ms = PhysicalLayerModel.calculate_propagation_delay_ms(distance_m)
        transmission_delay_ms = PhysicalLayerModel._calculate_transmission_delay_ms(data_size_byte, static_rate_bps)
        return LinkPhysicalState(
            link_type=link_type,
            distance_m=distance_m,
            propagation_delay_ms=propagation_delay_ms,
            radial_velocity_mps=0.0,
            doppler_shift_hz=0.0,
            path_loss_db=0.0,
            received_power_dbm=0.0,
            noise_power_dbm=0.0,
            snr_db=999.0,
            effective_rate_bps=static_rate_bps,
            transmission_delay_ms=transmission_delay_ms,
            processing_delay_ms=processing_time_ms,
            total_link_delay_ms=propagation_delay_ms + transmission_delay_ms + processing_time_ms,
            is_available=True,
            updated_at=current_time,
            reason="static compatible mode",
        )

    @staticmethod
    def _calculate_dynamic_state(link_key, link_type, link_config, source_position_3d, target_position_3d,
                                 data_size_byte, current_time, processing_time_ms):
        distance_m = PhysicalLayerModel.calculate_distance_m(source_position_3d, target_position_3d)
        propagation_delay_ms = PhysicalLayerModel.calculate_propagation_delay_ms(distance_m)
        radial_velocity_mps = PhysicalLayerModel.calculate_radial_velocity_mps(
            link_key=link_key,
            source_position_3d=source_position_3d,
            target_position_3d=target_position_3d,
            current_time=current_time,
        )
        doppler_shift_hz = PhysicalLayerModel.calculate_doppler_shift_hz(
            radial_velocity_mps=radial_velocity_mps,
            carrier_frequency_hz=link_config["carrier_frequency_hz"],
        )
        path_loss_db = PhysicalLayerModel.calculate_path_loss_db(
            distance_m=distance_m,
            carrier_frequency_hz=link_config["carrier_frequency_hz"],
        )
        received_power_dbm = (link_config["tx_power_dbm"]
                              + link_config["tx_antenna_gain_dbi"]
                              + link_config["rx_antenna_gain_dbi"]
                              - path_loss_db
                              - link_config["system_loss_db"]
                              - link_config["atmospheric_loss_db"])
        noise_power_dbm = PhysicalLayerModel.calculate_noise_power_dbm(
            bandwidth_hz=link_config["bandwidth_hz"],
            noise_figure_db=link_config["noise_figure_db"],
        )
        snr_db = received_power_dbm - noise_power_dbm
        reason = ""

        if cg.PHYSICAL_LAYER_ENABLE_DOPPLER:
            doppler_excess_hz = abs(doppler_shift_hz) - link_config["doppler_compensation_hz"]
            if doppler_excess_hz > 0:
                if link_config["drop_link_if_doppler_exceeded"]:
                    reason = "doppler shift exceeds compensation range"
                else:
                    snr_db -= doppler_excess_hz / 1000.0 * link_config["residual_doppler_loss_per_khz_db"]
                    reason = "residual doppler loss applied"

        effective_rate_bps = link_config["static_rate_bps"]
        if cg.PHYSICAL_LAYER_ENABLE_DYNAMIC_RATE:
            effective_rate_bps = PhysicalLayerModel.calculate_rate_bps(snr_db=snr_db, link_config=link_config)

        is_available = True
        if distance_m > link_config["max_distance_m"]:
            is_available = False
            reason = "distance exceeds maximum link range"
        if snr_db < link_config["min_snr_db"]:
            is_available = False
            reason = "snr below threshold"
        if effective_rate_bps < link_config["min_effective_rate_bps"]:
            is_available = False
            reason = "effective rate below threshold"
        if reason == "doppler shift exceeds compensation range":
            is_available = False

        if not is_available:
            effective_rate_bps = 0.0

        transmission_delay_ms = PhysicalLayerModel._calculate_transmission_delay_ms(data_size_byte, effective_rate_bps)
        total_link_delay_ms = propagation_delay_ms + transmission_delay_ms + processing_time_ms
        return LinkPhysicalState(
            link_type=link_type,
            distance_m=distance_m,
            propagation_delay_ms=propagation_delay_ms,
            radial_velocity_mps=radial_velocity_mps,
            doppler_shift_hz=doppler_shift_hz,
            path_loss_db=path_loss_db,
            received_power_dbm=received_power_dbm,
            noise_power_dbm=noise_power_dbm,
            snr_db=snr_db,
            effective_rate_bps=effective_rate_bps,
            transmission_delay_ms=transmission_delay_ms,
            processing_delay_ms=processing_time_ms,
            total_link_delay_ms=total_link_delay_ms,
            is_available=is_available,
            updated_at=current_time,
            reason=reason,
        )

    @staticmethod
    def _update_packet_delay(state, data_size_byte, processing_time_ms):
        transmission_delay_ms = PhysicalLayerModel._calculate_transmission_delay_ms(
            data_size_byte=data_size_byte,
            effective_rate_bps=state.effective_rate_bps,
        )
        return replace(
            state,
            transmission_delay_ms=transmission_delay_ms,
            processing_delay_ms=processing_time_ms,
            total_link_delay_ms=state.propagation_delay_ms + transmission_delay_ms + processing_time_ms,
        )

    @staticmethod
    def _calculate_transmission_delay_ms(data_size_byte, effective_rate_bps):
        if data_size_byte <= 0:
            return 0.0
        if effective_rate_bps <= 0:
            return float("inf")
        return data_size_byte * 8.0 / effective_rate_bps * 1000.0

    @staticmethod
    def state_to_dict(state):
        return {
            "link_type": state.link_type,
            "distance_m": state.distance_m,
            "propagation_delay_ms": state.propagation_delay_ms,
            "radial_velocity_mps": state.radial_velocity_mps,
            "doppler_shift_hz": state.doppler_shift_hz,
            "path_loss_db": state.path_loss_db,
            "received_power_dbm": state.received_power_dbm,
            "noise_power_dbm": state.noise_power_dbm,
            "snr_db": state.snr_db,
            "effective_rate_bps": state.effective_rate_bps,
            "transmission_delay_ms": state.transmission_delay_ms,
            "processing_delay_ms": state.processing_delay_ms,
            "total_link_delay_ms": state.total_link_delay_ms,
            "is_available": state.is_available,
            "updated_at": state.updated_at,
            "reason": state.reason,
        }
