from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class AbstractCrossLayerMessage(ABC):
    """
    Cross-layer message, that is, the message passed when the protocol stack is passed to the upper or lower layer
    """
    """
    :param action:  
    :param interface: The name of the buffer interface
    """
    action: Any  # Action, that is, how the data should be processed after a certain layer processing ends, such as continuing parsing to the upper layer, directly encapsulating to the lower layer, or doing nothing
    cross_layer_interface: Any  # Cross-layer interface, designed to use which protocol when passing to the upper or lower layer
    data: Any  # Data passed to other layers, the most important field