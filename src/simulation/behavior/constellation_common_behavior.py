from src.abstract.behavior.behavior import AbstractBehavior
from configuration import simulation_config as cg
import numpy as np
from src.tools import calculation


class ConstellationCommonBehavior(AbstractBehavior):
    # Coroutine to update the position of the constellation
    @staticmethod
    async def update_constellation_position_async(entity, data):

        M = entity.M_init + (2 * np.pi / entity.orbit_period_seconds) * entity.current_time[0]
        M = M % (2 * np.pi)
        nu = M[None, :] + entity.delta_f  # (10, 12) shape
        r = entity.semi_major_axis * (1 - entity.eccentricity ** 2) / (1 + entity.eccentricity * np.cos(nu))
        x_prime = r * np.cos(nu)
        y_prime = r * np.sin(nu)
        zero_np = np.zeros_like(x_prime)
        position_vector_orbital_plane = np.stack([x_prime, y_prime, zero_np], axis=-1)[..., np.newaxis]
        position_3D_ECI = entity.R3_Omega @ entity.R1_i_R3_omega @ position_vector_orbital_plane
        entity.position_3D_ECI = np.transpose(position_3D_ECI, (0, 1, 3, 2)).reshape(-1, 3)
        entity.satellite_position_3d[:] = entity.position_3D_ECI
        entity.satellite_position_2d[:] = calculation.position_3D_to_2D_array(entity.position_3D_ECI)
