import numpy as np
from multiprocessing import shared_memory
from configuration import simulation_config as cg
from src.simulation.variable import constant as ct


class SharedValue:
    def __init__(self):
        # Current time variable
        self._shm_current_time = shared_memory.SharedMemory(create=True, size=16, name=ct.SHM_CURRENT_TIME)
        self.current_time = np.ndarray((1,), dtype=np.float64, buffer=self._shm_current_time.buf)
        self.current_time[:] = 0


        # Satellite 3D position
        self._shm_satellite_position_3d = shared_memory.SharedMemory(create=True, size=cg.TOTAL_SATELLITE_NUMBER * 3 * 9
                                                         , name=ct.SHM_SATELLITE_POSITION_3D)
        self.satellite_position_3d = np.ndarray((cg.TOTAL_SATELLITE_NUMBER, 3), dtype=np.float64
                                         , buffer=self._shm_satellite_position_3d.buf)
        self.satellite_position_3d[:] = 0


        # Satellite 2D position
        self._shm_satellite_position_2d = shared_memory.SharedMemory(create=True, size=cg.TOTAL_SATELLITE_NUMBER * 3 * 9
                                                         , name=ct.SHM_SATELLITE_POSITION_2D)
        self.satellite_position_2d = np.ndarray((cg.TOTAL_SATELLITE_NUMBER, 3), dtype=np.float64
                                         , buffer=self._shm_satellite_position_2d.buf)
        self.satellite_position_2d[:] = 0


        # Orbit 3D position
        self._shm_orbit_position_3d = shared_memory.SharedMemory(create=True, size=cg.ORBIT_NUMBER * 100 * 3 * 9
                                                     , name=ct.SHM_ORBIT_POSITION_3D)
        self.orbit_position_3d = np.ndarray((cg.ORBIT_NUMBER * 100, 3), dtype=np.float64
                                      , buffer=self._shm_orbit_position_3d.buf)
        self.orbit_position_3d[:] = 0


        # User 3D position
        self._shm_user_position_3d = shared_memory.SharedMemory(create=True, size=cg.USER_NUMBER * 3 * 9
                                                    , name=ct.SHM_USER_POSITION_3D)
        self.user_position_3d = np.ndarray((cg.USER_NUMBER, 3), dtype=np.float64
                                     , buffer=self._shm_user_position_3d.buf)
        self.user_position_3d[:] = 0


        # Access relationship
        self._shm_access_relationship = shared_memory.SharedMemory(create=True, size=cg.USER_NUMBER * 9
                                                        , name=ct.SHM_ACCESS_RELATIONSHIP)
        self.access_relationship = np.ndarray((cg.USER_NUMBER, ), dtype=np.int64
                                        , buffer=self._shm_access_relationship.buf)
        self.access_relationship[:] = -1


        # Access relationship
        self._shm_routing_path = shared_memory.SharedMemory(create=True, size=100 * 3 * 9
                                                  , name=ct.SHM_ROUTING_PATH)
        self.routing_path = np.ndarray((100, 3, ), dtype=np.float64
                                  , buffer=self._shm_routing_path.buf)
        self.routing_path[:] = -1


        self._shm_satellite_load_deviation = shared_memory.SharedMemory(create=True, size=cg.ORBIT_NUMBER * cg.SATELLITE_NUMBER_PRE_ORBIT * 9
                                                          , name=ct.SHM_SATELLITE_LOAD_DEVIATION)
        self.satellite_load_deviation = np.ndarray((cg.ORBIT_NUMBER, cg.SATELLITE_NUMBER_PRE_ORBIT,), dtype=np.float64
                                           , buffer=self._shm_satellite_load_deviation.buf)
        self.satellite_load_deviation[:] = 1


        self._shm_satellite_latency = shared_memory.SharedMemory(create=True, size=cg.ORBIT_NUMBER * cg.SATELLITE_NUMBER_PRE_ORBIT * 9
                                                     , name=ct.SHM_SATELLITE_LATENCY)
        self.satellite_latency = np.ndarray((cg.ORBIT_NUMBER, cg.SATELLITE_NUMBER_PRE_ORBIT,), dtype=np.float64
                                      , buffer=self._shm_satellite_latency.buf)
        self.satellite_latency[:] = 0.1
