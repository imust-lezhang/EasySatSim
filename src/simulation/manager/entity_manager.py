from src.abstract.manager.entity_manager import AbstractEntityManager
from src.simulation.entity.satellite import Satellite
from src.simulation.entity.user import User
from src.simulation.entity.constellation import Constellation
from src.simulation.entity.ground import Ground
from configuration import simulation_config as cg
import numpy as np
from src.simulation.variable import constant as ct
from src.tools import file_operations
from multiprocessing import shared_memory
from src.tools import calculation



class EntityManager(AbstractEntityManager):
    def __init__(self):
        super().__init__()
        self._shm_user_position_3d = shared_memory.SharedMemory(name=ct.SHM_USER_POSITION_3D)
        self.user_position_3d = np.ndarray((cg.USER_NUMBER, 3), dtype=np.float64
                                           , buffer=self._shm_user_position_3d.buf)
        self.total_id = 0

    def create_satellites(self):
        satellites = []
        entity_id = 0
        for orbit_id in range(cg.ORBIT_NUMBER):
            for satellite_id in range(cg.SATELLITE_NUMBER_PRE_ORBIT):
                satellite = Satellite(entity_category="satellite", entity_id=entity_id, orbit_id=orbit_id
                                      , satellite_id=satellite_id)
                satellites.append(satellite)
                entity_id += 1
                self.total_id += 1
        self.add_entity(entity_category="satellite", entity_list=satellites)
        return

    def create_users(self):
        population_array = file_operations.load_npy_to_array(cg.POPULATION_PATH)
        users = []
        for entity_id in range(cg.USER_NUMBER):
            user = User(entity_category="user", entity_id=entity_id
                        , population_array=population_array)
            users.append(user)
            self.user_position_3d[entity_id] = user.position_3D
            self.total_id += 1
        self.add_entity(entity_category="user", entity_list=users)
        return

    def test_mode_create_users(self, user1_position, user2_position):
        population_array = file_operations.load_npy_to_array(cg.POPULATION_PATH)
        u1_position_array = np.array(user1_position)
        u2_position_array = np.array(user2_position)
        user1 = User(entity_category="user", entity_id=0
                    , population_array=population_array)
        user2 = User(entity_category="user", entity_id=1
                     , population_array=population_array)
        user1.position_2D = u1_position_array
        user2.position_2D = u2_position_array
        user1.position_3D = calculation.position_2D_to_3D(lat=u1_position_array[0], lon=u1_position_array[1], h=0)
        user2.position_3D = calculation.position_2D_to_3D(lat=u2_position_array[0], lon=u2_position_array[1], h=0)
        self.user_position_3d[0] = user1.position_3D
        self.user_position_3d[1] = user2.position_3D
        users = [user1, user2]

        for entity_id in range(2, cg.USER_NUMBER):
            user = User(entity_category="user", entity_id=entity_id
                        , population_array=population_array)
            users.append(user)
        self.add_entity(entity_category="user", entity_list=users)
        return


    def create_constellation(self):
        constellation = Constellation(cluster_category="constellation")
        self.add_entity_cluster(entity_cluster_category="constellation", entity_cluster=constellation)
        return

    def create_ground(self):
        ground = Ground(cluster_category="ground")
        self.add_entity_cluster(entity_cluster_category="ground", entity_cluster=ground)
        return


