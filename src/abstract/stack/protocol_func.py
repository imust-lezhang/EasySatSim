from abc import ABC, abstractmethod, ABCMeta


class AbstractProtocolFunc(ABC):
    """
    Used to define a certain function of a layer in the protocol stack, must be a static method for invocation
    """
    @staticmethod
    @abstractmethod
    def parse_and_process_func(*args, **kwargs):
        """
        Function to parse and process the protocol data, that is, the same function is used for processing at this layer/processing to the upper layer
        :param args:
        :param kwargs:
        :return: None or upper layer data
        """
        pass


    @staticmethod
    @abstractmethod
    def encapsulate_func(*args, **kwargs):
        """
        Function required for encapsulation, usually upper layer data -> this layer data
        :param args:
        :param kwargs:
        :return: Data of this layer
        """
        pass