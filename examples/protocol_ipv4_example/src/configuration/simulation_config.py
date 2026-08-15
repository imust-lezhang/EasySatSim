"""Deterministic configuration for the Scapy IPv4/UDP multi-hop example."""

from pathlib import Path

import numpy as np


# A compact Walker-style topology.  User locations below coincide with the
# initial sub-satellite points of satellites 0 and 40, whose toroidal grid
# distance is seven ISL moves in this 8 x 12 constellation.
ORBIT_NUMBER = 8
SATELLITE_NUMBER_PRE_ORBIT = 12
ORBIT_INCLINATION = 53
ORBIT_HEIGHT = 1150
ORBIT_OMEGA = 0
TOTAL_SATELLITE_NUMBER = ORBIT_NUMBER * SATELLITE_NUMBER_PRE_ORBIT

# Fixed endpoint and packet settings.
USER_NUMBER = 2
IPV4_EXAMPLE_SOURCE_USER_ID = 0
IPV4_EXAMPLE_DESTINATION_USER_ID = 1
IPV4_EXAMPLE_SOURCE_POSITION = (0.0, 0.0)
IPV4_EXAMPLE_DESTINATION_POSITION = (36.901843657, -79.459413647)
IPV4_EXAMPLE_EXPECTED_SOURCE_ACCESS_SATELLITE_ID = 0
IPV4_EXAMPLE_EXPECTED_DESTINATION_ACCESS_SATELLITE_ID = 40
IPV4_EXAMPLE_APPLICATION_PORT = 18080
IPV4_EXAMPLE_PAYLOAD = "EASYSATSIM_STANDARD_IPV4_UDP_TEST"
IPV4_EXAMPLE_PACKET_SIZE_BYTE = len(IPV4_EXAMPLE_PAYLOAD.encode("utf-8"))
IPV4_EXAMPLE_INITIAL_TTL = 64
IPV4_EXAMPLE_IDENTIFICATION = 8001
IPV4_EXAMPLE_MESSAGE_ID = "ipv4-step8-0001"
IPV4_EXAMPLE_TRAFFIC_START_TIME = 3.0
IPV4_EXAMPLE_BEHAVIOR_INTERVAL = 0.1

# Existing EasySatSim entity, buffer, routing, and link settings.
BUFFER_MAX_BYTE = 1e20
SATELLITE_ROUTING_UPDATE_TIME = 5
SATELLITE_NEIGHBOR_UPDATE_TIME = 1
MAX_NEIGHBOR_UPDATE_TIME = 10
USER_LATITUDE_MIN = -60
USER_LATITUDE_MAX = 60
USER_DATA_RATE_MIN = IPV4_EXAMPLE_PACKET_SIZE_BYTE
USER_DATA_RATE_MAX = IPV4_EXAMPLE_PACKET_SIZE_BYTE
DATA_SCALING = 1
USER_ROUTING_UPDATE_TIME = 9999
LINK_TRANSMIT_RATE = 1e7
SERVICE_RATE = 1e7
PROCESSING_TIME = 1

# Keep the existing physical-layer approximation enabled.  The limits support
# the 8 x 12 neighbor geometry without suppressing the selected multi-hop path.
PHYSICAL_LAYER_ENABLE = True
PHYSICAL_LAYER_ENABLE_DOPPLER = True
PHYSICAL_LAYER_ENABLE_DYNAMIC_RATE = True
PHYSICAL_LAYER_UPDATE_INTERVAL = 0.5
PHYSICAL_LAYER_USE_CACHE = True
PHYSICAL_LAYER_DEFAULT_PROCESSING_TIME = PROCESSING_TIME

ISL_CARRIER_FREQUENCY_HZ = 23e9
ISL_BANDWIDTH_HZ = 150e6
ISL_TX_POWER_DBM = 37.0
ISL_TX_ANTENNA_GAIN_DBI = 38.0
ISL_RX_ANTENNA_GAIN_DBI = 38.0
ISL_SYSTEM_LOSS_DB = 3.0
ISL_ATMOSPHERIC_LOSS_DB = 0.5
ISL_NOISE_FIGURE_DB = 3.0
ISL_MIN_SNR_DB = -5.0
ISL_MAX_DISTANCE_M = 6000000.0
ISL_DOPPLER_COMPENSATION_HZ = 1500000.0
ISL_RESIDUAL_DOPPLER_LOSS_PER_KHZ_DB = 0.001
ISL_STATIC_RATE_BPS = LINK_TRANSMIT_RATE
ISL_MIN_EFFECTIVE_RATE_BPS = 1e5
ISL_SPECTRAL_EFFICIENCY = 0.65
ISL_RATE_MAPPING_MODE = "discrete"
ISL_DROP_LINK_IF_DOPPLER_EXCEEDED = False
ISL_DISCRETE_RATE_TABLE = (
    (-5.0, 1e5),
    (0.0, 1e6),
    (5.0, 5e6),
    (10.0, 1e7),
    (15.0, 5e7),
    (20.0, 1e8),
    (25.0, 2e8),
)

SGL_CARRIER_FREQUENCY_HZ = 14e9
SGL_BANDWIDTH_HZ = 100e6
SGL_TX_POWER_DBM = 42.0
SGL_TX_ANTENNA_GAIN_DBI = 34.0
SGL_RX_ANTENNA_GAIN_DBI = 35.0
SGL_SYSTEM_LOSS_DB = 3.0
SGL_ATMOSPHERIC_LOSS_DB = 2.0
SGL_NOISE_FIGURE_DB = 5.0
SGL_MIN_SNR_DB = -5.0
SGL_MAX_DISTANCE_M = 3000000.0
SGL_DOPPLER_COMPENSATION_HZ = 500000.0
SGL_RESIDUAL_DOPPLER_LOSS_PER_KHZ_DB = 0.003
SGL_STATIC_RATE_BPS = LINK_TRANSMIT_RATE
SGL_MIN_EFFECTIVE_RATE_BPS = 1e5
SGL_SPECTRAL_EFFICIENCY = 0.60
SGL_RATE_MAPPING_MODE = "discrete"
SGL_DROP_LINK_IF_DOPPLER_EXCEEDED = False
SGL_DISCRETE_RATE_TABLE = (
    (-5.0, 1e5),
    (0.0, 1e6),
    (5.0, 5e6),
    (10.0, 1e7),
    (15.0, 5e7),
    (20.0, 1e8),
)

# A faster simulation clock keeps this integration example lightweight.
NETWORK_RUNNING_STEP_SECOND = 0.2
IPV4_EXAMPLE_RUNNING_TIME_REAL_SECONDS = 5.0

example_directory = Path(__file__).resolve().parents[2]
IPV4_EXAMPLE_RESULT_FILE_PATH = str(
    example_directory / "experiment" / "output" / "step8_delivery.json"
)
IPV4_EXAMPLE_TRACE_FILE_PATH = str(
    example_directory / "experiment" / "output" / "ipv4_hop_trace.csv"
)
IPV4_EXAMPLE_SOURCE_PCAP_PATH = str(
    example_directory / "experiment" / "output" / "source_ipv4_udp.pcap"
)
IPV4_EXAMPLE_DESTINATION_PCAP_PATH = str(
    example_directory / "experiment" / "output" / "destination_ipv4_udp.pcap"
)
# Offline-capture convention: pcap_timestamp = BASE_EPOCH + simulation_time.
IPV4_EXAMPLE_PCAP_BASE_EPOCH = 1700000000.0
IPV4_EXAMPLE_VALIDATION_SUMMARY_PATH = str(
    example_directory / "experiment" / "output" / "ipv4_validation_summary.json"
)
SAVE_FILE_PATH = (
    "../examples/protocol_ipv4_example/experiment/output/step8_network_metrics.csv"
)
POPULATION_PATH = "../resource/population_matrix.npy"

# The access behavior consumes this surface-distance threshold.  With endpoints
# fixed at their expected initial sub-satellite points, 40 degrees provides a
# strict and reproducible nearest-satellite selection.
EARTH_RADIUS_KM = 6371.0
MIN_ELEVATION_ANGLE_DEG = 40.0
minimum_elevation_angle_rad = np.radians(MIN_ELEVATION_ANGLE_DEG)
coverage_central_angle_rad = (
    np.arccos(
        (EARTH_RADIUS_KM / (EARTH_RADIUS_KM + ORBIT_HEIGHT))
        * np.cos(minimum_elevation_angle_rad)
    )
    - minimum_elevation_angle_rad
)
COVER_RADIUS = EARTH_RADIUS_KM * coverage_central_angle_rad
SATELLITE_CONE_HALF_ANGLE_DEG = (
    90.0 - MIN_ELEVATION_ANGLE_DEG - np.degrees(coverage_central_angle_rad)
)
SATELLITE_CONE_ANGLE = 2.0 * SATELLITE_CONE_HALF_ANGLE_DEG
