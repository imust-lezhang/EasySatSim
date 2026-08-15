from abc import ABC, abstractmethod
import asyncio


class AbstractEntityManager(ABC):
    def __init__(self):
        self.dict_entity = {}
        self.dict_entity_cluster = {}


    async def start_entity_tasks(self):
        tasks = []
        for entity_list in self.dict_entity.values():
            for entity in entity_list:
                tasks.append(entity.start_behaviors())
        await asyncio.gather(*tasks)


    async def start_entity_cluster_tasks(self):
        tasks = []
        for entity_cluster in self.dict_entity_cluster.values():
            tasks.append(entity_cluster.start_behaviors())
        await asyncio.gather(*tasks)


    def add_entity(self, entity_category: str, entity_list: list):
        """
        Add an entity
        :param entity_category: Entity category
        :param entity_list: A collection of entities
        :return: None
        """
        self.dict_entity[entity_category] = entity_list
        return


    def add_entity_cluster(self, entity_cluster_category: str, entity_cluster):
        """
        Add an entity cluster
        :param entity_cluster_category: The category of the entity cluster
        :param entity_cluster: The object of the entity cluster
        :return:
        """
        self.dict_entity_cluster[entity_cluster_category] = entity_cluster
        return


    def get_entity(self, entity_category: str):
        return self.dict_entity[entity_category]


    def get_entity_cluster(self, entity_cluster_category: str):
        return self.dict_entity_cluster[entity_cluster_category]


    @staticmethod
    def bind_common_behavior(behavior_manager, entity_cluster, behavior_name):
        """
        Bind a common behavior to an entity cluster
        :param behavior_manager: Behavior manager for invoking behaviors
        :param entity_cluster: Entity cluster
        :param behavior_name: Behavior name
        :return: None
        """
        common_behavior = behavior_manager.get_common_behavior(behavior_name)
        entity_cluster.add_common_behavior(behavior_name=behavior_name, behavior_func=common_behavior['behavior_func']
                                      , interval=common_behavior['interval'], is_async=common_behavior['is_async']
                                      , data=common_behavior['data'], last_run=common_behavior['last_run'])
        return


    @staticmethod
    def bind_active_behavior(behavior_manager, entity, behavior_name):
        """
        Bind an active behavior to an entity
        :param behavior_manager: Behavior manager for invoking behaviors
        :param entity: Entity
        :param behavior_name: Behavior name
        :return: None
        """
        active_behavior = behavior_manager.get_active_behavior(behavior_name)
        entity.add_active_behavior(behavior_name=behavior_name, behavior_func=active_behavior['behavior_func']
                               , interval=active_behavior['interval'], is_async=active_behavior['is_async']
                               , data=active_behavior['data'], last_run=active_behavior['last_run'])
        return


    @staticmethod
    def bind_passive_behavior(behavior_manager, entity, behavior_name):
        """
        Bind a passive behavior to an entity
        :param behavior_manager: Behavior manager for invoking behaviors
        :param entity: Entity
        :param behavior_name: Behavior name
        :return:
        """
        common_behavior = behavior_manager.get_passive_behavior(behavior_name)
        entity.add_passive_behavior(behavior_name=behavior_name, behavior_func=common_behavior['behavior_func']
                                , is_async=common_behavior['is_async'], data=common_behavior['data'])
        return


    @staticmethod
    def clear_behaviors(entity):

        return


    def __str__(self):
        output_lines = ["[EntityManager]\n"
                       f"Entity:"]


        # Handle dict_entity, only show the first few elements of each type, and show the total length
        for entity_type, entities in self.dict_entity.items():
            preview = entities[0]
            output_lines.append(f"{entity_type} (Total: {len(entities)}): [{preview},...]")
        output_lines.append(f"Entity Cluster:")
        # Handle dict_entity_cluster
        for cluster_type, clusters in self.dict_entity_cluster.items():
            preview = clusters  # Only take the first three elements for preview
            output_lines.append(f"{cluster_type}: {preview}")


        # Combine all lines into one string, with each element on one line
        return "\n".join(output_lines)