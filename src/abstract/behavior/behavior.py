from abc import ABC, ABCMeta, abstractmethod


class CheckStaticMethodsMeta(ABCMeta):
    def __new__(cls, name, bases, dct):
        for attr, value in dct.items():
            if callable(value):
                if not isinstance(value, staticmethod):
                    raise TypeError(f"Method '{attr}' must be defined as a static method")
        return super().__new__(cls, name, bases, dct)


class AbstractBehavior(ABC, metaclass=CheckStaticMethodsMeta):
    """
    Interface for various behaviors, behaviors must be defined as static classes
    """
    pass