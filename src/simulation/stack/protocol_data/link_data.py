from src.abstract.stack.protocol_data import AbstractProtocolData
from dataclasses import dataclass
import struct
import numpy as np
from numba import jit


@dataclass
class DataFrame(AbstractProtocolData):
    source_mac: str
    destination_mac: str
    type: int
    checksum: int
    payload: bytes


    @staticmethod
    def to_data(cross_layer_data):
        data_binary = cross_layer_data.payload
        data_bytes = DataFrame._binary_to_bytes(data_binary)
        data_frame = DataFrame._bytes_to_frame(data_bytes)
        return data_frame


    @staticmethod
    def data_to(this_layer_data):
        data_bytes = DataFrame._frame_to_bytes(this_layer_data)
        data_binary = DataFrame._bytes_to_binary(data_bytes)
        return data_binary


    @staticmethod
    def _binary_to_bytes(cross_layer_data):
        packed_bytes = np.packbits(cross_layer_data)
        return packed_bytes.tobytes()


    @staticmethod
    def _bytes_to_frame(cross_layer_data):
        # Unpack the header, unpack the data frame header of 6s6sHH format
        header = struct.unpack('>6s6sHH', cross_layer_data[:16])
        source_mac = ':'.join(format(x, '02X') for x in header[0])
        destination_mac = ':'.join(format(x, '02X') for x in header[1])
        type = header[2]
        checksum = header[3]
        # The payload is all data after the frame header
        payload = cross_layer_data[16:]
        return DataFrame(source_mac, destination_mac, type, checksum, payload)


    @staticmethod
    @jit(nopython=True)
    def _bytes_to_binary(cross_layer_data):
        data_length = len(cross_layer_data)
        num_bits = data_length * 8
        binary_array = np.zeros(num_bits, dtype=np.uint8)


        for i in range(data_length):
            byte = cross_layer_data[i]
            for j in range(8):
                binary_array[i * 8 + (7 - j)] = (byte >> j) & 1
        return binary_array


    @staticmethod
    def _frame_to_bytes(this_layer_data):
        # Process the MAC address into six pairs of two hexadecimal digits (without colons) and convert to bytes
        source_mac_bytes = bytes.fromhex(this_layer_data.source_mac.replace(':', ''))
        destination_mac_bytes = bytes.fromhex(this_layer_data.destination_mac.replace(':', ''))
        # Pack the entire DataFrame, including MAC addresses, type, checksum, and payload
        frame_header = struct.pack('>6s6sHH', source_mac_bytes, destination_mac_bytes,
                               this_layer_data.type, this_layer_data.checksum)
        # Return the complete frame including the header and payload
        return frame_header + this_layer_data.payload