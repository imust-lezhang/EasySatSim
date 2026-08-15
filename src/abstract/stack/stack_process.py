from abc import ABC, abstractmethod, ABCMeta


class CheckStaticMethodsMeta(ABCMeta):
    def __new__(cls, name, bases, dct):
        for attr, value in dct.items():
            if callable(value):
                if not isinstance(value, staticmethod):
                    raise TypeError(f"Method '{attr}' must be defined as a static method")
        return super().__new__(cls, name, bases, dct)


class AbstractStackProcess(ABC):
    """
    This interface is used to implement related functions of protocol stack processing, such as how to process data packets received by the protocol stack, how to encapsulate application layer data into signals, and how to encapsulate ARP data packets into signals.
    Finally, the functions of this interface will be called by the passive behaviors of each entity.
    """
    pass