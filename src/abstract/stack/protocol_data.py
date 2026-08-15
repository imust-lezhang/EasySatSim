from abc import ABC, abstractmethod, ABCMeta
from dataclasses import dataclass


class CheckStaticMethodsMeta(ABCMeta):
    def __new__(cls, name, bases, dct):
        for attr, value in dct.items():
            if callable(value):
                if not isinstance(value, staticmethod):
                    raise TypeError(f"Method '{attr}' must be defined as a static method")
        return super().__new__(cls, name, bases, dct)


@dataclass
class AbstractProtocolData(ABC, metaclass=CheckStaticMethodsMeta):

    @staticmethod
    @abstractmethod
    def to_data(cross_layer_data):
        """
        Convert data from other layers to data of this layer
        :param cross_layer_data: Data from other layers
        :return: Data format of this layer
        """
        pass


    @staticmethod
    @abstractmethod
    def data_to(this_layer_data):
        """
        Used to convert data from other layers to data of this layer
        :param this_layer_data: Data format of this layer
        :return: Data format of other layers
        """
        pass