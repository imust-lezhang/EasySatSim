import asyncio
from abc import ABC, abstractmethod


class AbstractEntityCluster(ABC):
    def __init__(self, cluster_category):
        """
        Initialize the cluster class, used to store entities of the same type and invoke their common behaviors, and these behaviors are usually uniformly computable
        :param category: Category str
        """
        self.cluster_category = cluster_category
        self.__dict_common_behavior__ = {}  # Dictionary for storing common behaviors, its principle should be the same as that of active behaviors

    async def start_behaviors(self):
        """
        Start the common behaviors of a cluster
        :return: None
        """
        await asyncio.gather(
            self.common_behavior(),
        )

    @abstractmethod
    async def common_behavior(self):
        """
        The invocation method of common behaviors, usually in a while True logic
        :return: None
        """
        pass

    def get_common_behaviors(self):
        """
        Get the dictionary of all common behaviors
        :return:
        """
        return self.__dict_common_behavior__

    def add_common_behavior(self, behavior_name, behavior_func, interval, is_async, data, last_run):
        """
        Used to add an active behavior to the common behavior dictionary
        :param behavior_name: Behavior name
        :param behavior_func: Behavior function
        :param interval: Time interval for executing the active behavior
        :param is_async: Whether the behavior function is async
        :param data: Additional data to be passed in
        :param last_run: The last running time
        :return: None
        """
        if behavior_name in self.__dict_common_behavior__:
            raise KeyError(f"[Wrong] Behavior name '{behavior_name}' is already in __dict_common_behavior__.")
        else:
            self.__dict_common_behavior__[behavior_name] = {'behavior_func': behavior_func, 'interval': interval
               ,'is_async': is_async, 'data': data, 'last_run': last_run}