from src.abstract.stack.protocol_data import AbstractProtocolData
from dataclasses import dataclass
import numpy as np
from numba import jit


@dataclass
class DataBinary(AbstractProtocolData):
    payload: np.ndarray

    @staticmethod
    def to_data(cross_layer_data):
        return DataBinary(payload=cross_layer_data)

    @staticmethod
    def data_to(this_layer_data):
        return this_layer_data.payload