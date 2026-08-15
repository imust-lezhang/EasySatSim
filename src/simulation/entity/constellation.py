import numpy as np
from src.abstract.entity.entity_cluster import AbstractEntityCluster
from src.simulation.variable import constant as ct
from configuration import simulation_config as cg
from multiprocessing import shared_memory
import time
import asyncio
from src.tools import calculation


class Constellation(AbstractEntityCluster):
    def __init__(self, cluster_category):
        super().__init__(cluster_category)


        # Orbit related parameters
        self.orbit_number = cg.ORBIT_NUMBER  # Number of orbits
        self.satellite_number_pre_orbit = cg.SATELLITE_NUMBER_PRE_ORBIT  # Number of satellites per orbit
        self.orbit_interpolations = 100  # Number of orbit interpolations, used for plotting
        self.orbit_inclination = np.radians(cg.ORBIT_INCLINATION)  # Orbit inclination, convert angle to radians
        self.orbit_height = cg.ORBIT_HEIGHT  # Orbit height in km
        earth_radius = 6371
        self.semi_major_axis = self.orbit_height + earth_radius  # Semi-major axis
        self.eccentricity = 0
        self.orbit_omega = cg.ORBIT_OMEGA
        # Period related parameters
        mu_earth = 3.986e14  # Earth's standard gravitational parameter mu in m^3/s^2
        a_meters = self.semi_major_axis * 1000  # Convert semi-major axis to meters
        self.orbit_period_seconds = 2 * np.pi * np.sqrt(a_meters ** 3 / mu_earth)  # Satellite orbit period in seconds
        self.earth_period_hours = 2 * np.pi / 24  # Earth's running time
        # Store satellites and their positions, orbit updates
        self.M_init = None
        self.R3_Omega = None
        self.R1_i_R3_omega = None
        self.position_2D_GCS = None  # Geographic coordinate system latitude/longitude/altitude
        self.position_3D_ECI = None  # Earth-centered inertial coordinate system x/y/z in km
        self.delta_f = None


        self.bind_shared_memory_views()


        self._init_constellation_position_paramteres()
        self._init_orbit_position()


    async def start_behaviors(self):
        await asyncio.gather(
            self.common_behavior(),
        )

    def bind_shared_memory_views(self):
        self._shm_current_time = shared_memory.SharedMemory(name=ct.SHM_CURRENT_TIME)
        self._shm_satellite_position_3d = shared_memory.SharedMemory(name=ct.SHM_SATELLITE_POSITION_3D)
        self._shm_satellite_position_2d = shared_memory.SharedMemory(name=ct.SHM_SATELLITE_POSITION_2D)
        self._shm_orbit_position_3d = shared_memory.SharedMemory(name=ct.SHM_ORBIT_POSITION_3D)
        self.current_time = np.ndarray((1,), dtype=np.float64, buffer=self._shm_current_time.buf)
        self.satellite_position_3d = np.ndarray((cg.TOTAL_SATELLITE_NUMBER, 3), dtype=np.float64
                                          , buffer=self._shm_satellite_position_3d.buf)
        self.satellite_position_2d = np.ndarray((cg.TOTAL_SATELLITE_NUMBER, 3), dtype=np.float64
                                          , buffer=self._shm_satellite_position_2d.buf)
        self.orbit_position_3d = np.ndarray((cg.ORBIT_NUMBER * 100, 3), dtype=np.float64
                                      , buffer=self._shm_orbit_position_3d.buf)
        return


    async def common_behavior(self):
        sleep_time = 0.1
        while True:
            current_time = time.time()
            common_behaviors = self.get_common_behaviors()
            for name, details in common_behaviors.items():
                func = details['behavior_func']
                interval = details['interval']
                is_async = details['is_async']
                data = details['data']
                last_run = details['last_run']
                if last_run is None or (current_time - last_run >= interval):
                    if is_async:
                        await func(entity=self, data=None)
                    else:
                        func(entity=self, data=None)
                    common_behaviors[name]['last_run'] = current_time


            await asyncio.sleep(sleep_time)


    # Initialize the position of the constellation
    def _init_constellation_position_paramteres(self):
        # Calculate Omega and nu
        orbit_ids = np.arange(self.orbit_number)
        satellite_ids = np.arange(self.satellite_number_pre_orbit)
        Omega = np.radians(orbit_ids[:, None] * (360 / self.orbit_number))  # (10, 1) shape
        self.M_init = np.radians(satellite_ids * (360 / self.satellite_number_pre_orbit))  # (12,) shape
        delta_f = (2 * np.pi / (self.orbit_number * self.satellite_number_pre_orbit)) * orbit_ids[:,
                                                                           None]  # (10, 1) shape
        self.delta_f = delta_f
        nu = self.M_init[None, :] + delta_f  # (10, 12) shape
        r = self.semi_major_axis * (1 - self.eccentricity ** 2) / (
                1 + self.eccentricity * np.cos(nu))  # (10, 12) shape


        # Generate orbit matrix
        cos_Omega = np.cos(Omega)
        sin_Omega = np.sin(Omega)
        self.R3_Omega = np.array([
            [cos_Omega, -sin_Omega, np.zeros_like(cos_Omega)],
            [sin_Omega, cos_Omega, np.zeros_like(cos_Omega)],
            [np.zeros_like(cos_Omega), np.zeros_like(cos_Omega), np.ones_like(cos_Omega)]
        ]).transpose(2, 3, 0, 1)  # (10, 12, 3, 3)


        # Generate R1_i and R3_omega rotation matrices
        cos_incl = np.cos(self.orbit_inclination)
        sin_incl = np.sin(self.orbit_inclination)
        R1_i = np.array([
            [1, 0, 0],
            [0, cos_incl, -sin_incl],
            [0, sin_incl, cos_incl]
        ])


        cos_omega = np.cos(self.orbit_omega)
        sin_omega = np.sin(self.orbit_omega)
        R3_omega = np.array([
            [cos_omega, -sin_omega, 0],
            [sin_omega, cos_omega, 0],
            [0, 0, 1]
        ])


        # Calculate the combined R1_i @ R3_omega
        self.R1_i_R3_omega = np.dot(R1_i, R3_omega)


        # Calculate position vector
        x_prime = r * np.cos(nu)
        y_prime = r * np.sin(nu)
        zero_np = np.zeros_like(x_prime)
        position_vector_orbital_plane = np.stack([x_prime, y_prime, zero_np], axis=-1)[..., np.newaxis]


        # Perform matrix multiplication
        position_3D_ECI = self.R3_Omega @ self.R1_i_R3_omega @ position_vector_orbital_plane
        self.position_3D_ECI = np.transpose(position_3D_ECI, (0, 1, 3, 2)).reshape(-1, 3)
        self.satellite_position_3d[:] = self.position_3D_ECI
        self.satellite_position_2d[:] = calculation.position_3D_to_2D_array(self.position_3D_ECI)
        # self.global_variables.update_satellites_position(satellite_position_3d=self.position_3D_ECI)
        # self.redis_conn.set(constans.SATELLITE_POSITION_3D, self.position_3D_ECI.tobytes())
        return


    def _init_orbit_position(self):
        # Calculate Omega and nu
        orbit_ids = np.arange(self.orbit_number)
        satellite_ids = np.arange(self.orbit_interpolations)
        Omega = np.radians(orbit_ids[:, None] * (360 / self.orbit_number))  # (10, 1) shape
        M_init = np.radians(satellite_ids * (360 / self.orbit_interpolations))  # (12,) shape
        delta_f = (2 * np.pi / (self.orbit_number * self.orbit_interpolations)) * orbit_ids[:,
                                                                       None]  # (10, 1) shape
        nu = M_init[None, :] + delta_f  # (10, 12) shape
        r = self.semi_major_axis * (1 - self.eccentricity ** 2) / (
                1 + self.eccentricity * np.cos(nu))  # (10, 12) shape


        # Generate orbit matrix
        cos_Omega = np.cos(Omega)
        sin_Omega = np.sin(Omega)
        R3_Omega = np.array([
            [cos_Omega, -sin_Omega, np.zeros_like(cos_Omega)],
            [sin_Omega, cos_Omega, np.zeros_like(cos_Omega)],
            [np.zeros_like(cos_Omega), np.zeros_like(cos_Omega), np.ones_like(cos_Omega)]
        ]).transpose(2, 3, 0, 1)  # (10, 12, 3, 3)


        # Generate R1_i and R3_omega rotation matrices
        cos_incl = np.cos(self.orbit_inclination)
        sin_incl = np.sin(self.orbit_inclination)
        R1_i = np.array([
            [1, 0, 0],
            [0, cos_incl, -sin_incl],
            [0, sin_incl, cos_incl]
        ])


        cos_omega = np.cos(self.orbit_omega)
        sin_omega = np.sin(self.orbit_omega)
        R3_omega = np.array([
            [cos_omega, -sin_omega, 0],
            [sin_omega, cos_omega, 0],
            [0, 0, 1]
        ])


        # Calculate the combined R1_i @ R3_omega
        R1_i_R3_omega = np.dot(R1_i, R3_omega)


        # Calculate position vector
        x_prime = r * np.cos(nu)
        y_prime = r * np.sin(nu)
        zero_np = np.zeros_like(x_prime)
        position_vector_orbital_plane = np.stack([x_prime, y_prime, zero_np], axis=-1)[..., np.newaxis]


        # Perform matrix multiplication
        position_3D_ECI = R3_Omega @ R1_i_R3_omega @ position_vector_orbital_plane
        position_3D_ECI = np.transpose(position_3D_ECI, (0, 1, 3, 2)).reshape(-1, 3)
        self.orbit_position_3d[:] = position_3D_ECI
        return
