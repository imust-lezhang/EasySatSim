from abc import ABC, abstractmethod


class AbstractBehaviorManager(ABC):
    def __init__(self):
        self.__dict_common_behavior__ = {}
        self.__dict_active_behavior__ = {}
        self.__dict_passive_behavior__ = {}

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
               ,'is_async': is_async, 'data': data, 'last_run': last_run}

    def add_passive_behavior(self, behavior_name, behavior_func, is_async, data):
        """
        Used to add an active behavior to the active behavior dictionary
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

    def get_common_behavior(self, behavior_name):
        """
        Get the behavior by behavior name
        :param behavior_name: Behavior name, which is the key of __dict_active_behavior
        :return: None
        """
        if behavior_name in self.__dict_common_behavior__:
            return self.__dict_common_behavior__[behavior_name]
        else:
            raise KeyError(f"[Wrong] Behavior name '{behavior_name}' not found in __dict_common_behavior__.")


    def get_active_behavior(self, behavior_name):
        """
        Get the behavior by behavior name
        :param behavior_name: Behavior name, which is the key of _dict_active_behavior
        :return: None
        """
        if behavior_name in self.__dict_active_behavior__:
            return self.__dict_active_behavior__[behavior_name]
        else:
            raise KeyError(f"[Wrong] Behavior name '{behavior_name}' not found in _dict_active_behavior.")

    def get_passive_behavior(self, behavior_name):
        """
        Get the behavior by behavior name
        :param behavior_name: Behavior name, which is the key of _dict_passive_behavior
        :return: _dict_passive_behavior
        """
        if behavior_name in self.__dict_passive_behavior__:
            return self.__dict_passive_behavior__[behavior_name]
        else:
            raise KeyError(f"[Wrong] Behavior name '{behavior_name}' not found in _dict_passive_behavior.")