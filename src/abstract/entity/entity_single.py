import asyncio
from abc import ABC, abstractmethod


class AbstractEntity(ABC):
    def __init__(self, entity_category, entity_id):
        self.entity_category = entity_category
        self.entity_id = entity_id  # ID within each category
        self.__dict_active_behavior__ = {}  # Active behaviors of the entity
        self.__dict_passive_behavior__ = {}  # Passive behaviors of the entity

    async def start_behaviors(self):
        """
        Used to start all behaviors of the entity
        :return: None
        """
        await asyncio.gather(
            self.active_behavior(),
            self.passive_behavior()
        )


    @abstractmethod
    async def active_behavior(self):
        """
        Invocation method of active behavior, usually in a while True logic
        :return:
        """
        pass

    @abstractmethod
    async def passive_behavior(self):
        """
        Invocation method of passive behavior, usually in a while True logic
        :return:
        """
        pass

    def get_active_behaviors(self):
        """
        Get the dictionary of active behaviors
        :return:
        """
        return self.__dict_active_behavior__

    def get_passive_behaviors(self):
        """
        Get the dictionary of passive behaviors
        :return:
        """
        return self.__dict_passive_behavior__

    def add_active_behavior(self, behavior_name, behavior_func, interval, is_async, data, last_run):
        """
        Used to add an active behavior to the active behavior dictionary
        :param behavior_name: Behavior name
        :param behavior_func: Behavior function
        :param interval: Time interval for executing the active behavior
        :param is_async: Whether the behavior function is async
        :param data: Additional data to be passed in
        :param last_run: The last running time
        :return: None
        """
        if behavior_name in self.__dict_active_behavior__:
            raise KeyError(f"[Wrong] Behavior name '{behavior_name}' is already in _dict_active_behavior.")
        else:
            self.__dict_active_behavior__[behavior_name] = {'behavior_func': behavior_func, 'interval': interval
               , 'is_async': is_async, 'data': data, 'last_run': last_run}

    def add_passive_behavior(self, behavior_name, behavior_func, is_async, data):
        """
        Used to add a passive behavior to the passive behavior dictionary
        :param behavior_name: Behavior name
        :param behavior_func: Behavior function
        :param is_async: Whether the behavior function is async
        :param data: Additional data to be passed in
        :return: None
        """
        if behavior_name in self.__dict_passive_behavior__:
            raise KeyError(f"[Wrong] Behavior name '{behavior_name}' is already in _dict_passive_behavior.")
        else:
            self.__dict_passive_behavior__[behavior_name] = {'behavior_func': behavior_func
               , 'is_async': is_async, 'data': data}

    def clear_behaviors(self):
        self.__dict_active_behavior__ = {}
        self.__dict_passive_behavior__ = {}