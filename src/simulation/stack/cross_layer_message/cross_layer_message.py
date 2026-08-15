from dataclasses import dataclass
from typing import Any
from src.abstract.stack.cross_layer_message import AbstractCrossLayerMessage
from enum import Enum


class ActionType(Enum):
    ENCAPSULATE = "encapsulate"  # Encapsulation
    PARSE = "parse"  # Parsing
    STOP = "stop"  # Same-layer processing


@dataclass
class CrossLayerMessage(AbstractCrossLayerMessage):
    action: ActionType
    cross_layer_interface: int or str
    data: Any
    data_others: dict