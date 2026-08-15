from src.simulation.manager.entity_manager import EntityManager
from src.abstract.manager.behavior_manager import AbstractBehaviorManager
from src.simulation.behavior.constellation_common_behavior import ConstellationCommonBehavior
from src.simulation.behavior.user_active_behavior import UserActiveBehavior
from src.simulation.behavior.satellite_passive_behavior import SatellitePassiveBehavior
from src.simulation.behavior.user_passive_behavior import UserPassiveBehavior
from src.simulation.behavior.satellite_active_behavior import SatelliteActiveBehavior
from src.simulation.behavior.test_user_behavior import TESTUserActiveBehavior


class BehaviorManager(AbstractBehaviorManager):
    def __init__(self):
        super().__init__()

    def load_default_behaviors(self):
        self.add_common_behavior(behavior_name="update_constellation_position_async",
                                 behavior_func=ConstellationCommonBehavior.update_constellation_position_async
                                 , data=None, interval=0.1, is_async=True, last_run=None)
        self.add_active_behavior(behavior_name="simple_access_satellite"
                                 , behavior_func=UserActiveBehavior.simple_access_satellite
                                 , interval=0.3, is_async=True, data=None, last_run=None)
        self.add_active_behavior(behavior_name="simple_send_data"
                                 , behavior_func=UserActiveBehavior.simple_user_send_data
                                 , interval=0.01, is_async=True, data=None, last_run=None)
        self.add_active_behavior(behavior_name="update_routing_table"
                                 , behavior_func=SatelliteActiveBehavior.update_routing_table
                                 , interval=0.5, is_async=True, data=None, last_run=None)
        self.add_active_behavior(behavior_name="update_satellite_load_deviation"
                                 , behavior_func=SatelliteActiveBehavior.update_load_deivation
                                 , interval=0.1, is_async=False, data=None, last_run=None)
        self.add_passive_behavior(behavior_name="satellite_stack_processing"
                                  , behavior_func=SatellitePassiveBehavior.stack_processing
                                  , is_async=True, data=None)
        self.add_passive_behavior(behavior_name="user_stack_processing"
                                  , behavior_func=UserPassiveBehavior.stack_processing, is_async=True, data=None)



    def bind_default_common_behaviors(self, constellation):
        EntityManager.bind_common_behavior(behavior_manager=self
                                                 , entity_cluster=constellation
                                                 , behavior_name="update_constellation_position_async")
        return

    def bind_default_user_active_behaviors(self, user):
        EntityManager.bind_active_behavior(behavior_manager=self, entity=user, behavior_name="simple_access_satellite")
        EntityManager.bind_active_behavior(behavior_manager=self, entity=user, behavior_name="simple_send_data")
        return

    def bind_default_satellite_active_behaviors(self, satellite):
        EntityManager.bind_active_behavior(behavior_manager=self, entity=satellite, behavior_name="update_routing_table")
        EntityManager.bind_active_behavior(behavior_manager=self, entity=satellite, behavior_name="update_satellite_load_deviation")
        return

    def bind_default_satellite_passive_behaviors(self, satellite):
        EntityManager.bind_passive_behavior(behavior_manager=self, entity=satellite,
                                             behavior_name="satellite_stack_processing")

        return

    def bind_default_user_passive_behaviors(self, user):
        EntityManager.bind_passive_behavior(behavior_manager=self, entity=user,
                                            behavior_name="user_stack_processing")
        return


    # Some registration in test mode
    def load_test_mode(self, user1):
        self.add_active_behavior(behavior_name="test_access_satellite"
                                 , behavior_func=TESTUserActiveBehavior.direct_access_satellite
                                 , interval=0.3, is_async=True, data=user1, last_run=None)
        self.add_active_behavior(behavior_name="test_send_data"
                                 , behavior_func=TESTUserActiveBehavior.RTT_send_data
                                 , interval=0.001, is_async=True, data=None, last_run=None)

    def bind_direction_connect_mode_active_behaviors(self, user0, user1):
        EntityManager.bind_active_behavior(behavior_manager=self, entity=user0, behavior_name="test_access_satellite")
        EntityManager.bind_active_behavior(behavior_manager=self, entity=user0, behavior_name="test_send_data")
        EntityManager.bind_active_behavior(behavior_manager=self, entity=user1, behavior_name="test_send_data")
        return

    def bind_test_active_behaviors(self, user):
        EntityManager.bind_active_behavior(behavior_manager=self, entity=user, behavior_name="simple_access_satellite")
        EntityManager.bind_active_behavior(behavior_manager=self, entity=user, behavior_name="test_send_data")

