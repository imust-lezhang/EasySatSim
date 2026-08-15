from abc import ABC, abstractmethod, ABCMeta


class CheckStaticMethodsMeta(ABCMeta):
    def __new__(cls, name, bases, dct):
        for attr, value in dct.items():
            if callable(value):
                if not isinstance(value, staticmethod):
                    raise TypeError(f"Method '{attr}' must be defined as a static method")
        return super().__new__(cls, name, bases, dct)


class RoutingAlgorithm(ABC):
    """
    Routing algorithm
    """
    @staticmethod
    @abstractmethod
    def routing_algorithm(entity, cross_layer_message, src_satellite_id, dst_satellite_id):
        """
        Routing algorithm, calculate the next hop of the data packet
        :param entity: Satellite entity
        :param cross_layer_message: Cross-layer message
        :param src_satellite_id: Source satellite ID, already converted from IP to ID
        :param dst_satellite_id: Destination satellite ID, already converted from IP to ID
        :return: int or bool, returns the ID of the next hop satellite next_satellite_id
        """
        pass