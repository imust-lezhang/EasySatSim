from src.abstract.stack.protocol_data import AbstractProtocolData
from dataclasses import dataclass
import struct
import socket
from enum import Enum


@dataclass
class DataMessage(AbstractProtocolData):
    message: str


    @staticmethod
    def to_data(cross_layer_data):
        message = cross_layer_data.decode('utf-8').rstrip('\x00')
        return DataMessage(message=message)


    @staticmethod
    def data_to(this_layer_data):
        message_fixed = this_layer_data.message.encode('utf-8')
        # Return serialized bytes
        return message_fixed


class AccessActionType(Enum):
    ACCESS = "access"  # Access
    QUIT = "quit"  # Quit


@dataclass
class AccessMessage(AbstractProtocolData):
    user_id: int
    user_ip: str
    user_mac: str
    access_action: AccessActionType


    @staticmethod
    def to_data(cross_layer_data):
        # Parse the structure as 'I4s6s7s': user_id, user_ip, user_mac, access_action
        unpacked_data = struct.unpack('I4s6s7s', cross_layer_data)
        user_id = unpacked_data[0]
        user_ip = socket.inet_ntoa(unpacked_data[1])
        user_mac = ':'.join(f'{x:02X}' for x in unpacked_data[2])
        access_action = AccessActionType(unpacked_data[3].decode().strip('\x00'))  # Convert from bytes and remove padded null characters
        return AccessMessage(user_id=user_id, user_ip=user_ip, user_mac=user_mac, access_action=access_action)


    @staticmethod
    def data_to(this_layer_data):
        user_ip_encoded = socket.inet_aton(this_layer_data.user_ip)
        user_mac_encoded = bytes(int(x, 16) for x in this_layer_data.user_mac.split(':'))
        access_action_encoded = this_layer_data.access_action.value.encode().ljust(7, b'\x00')  # Ensure fixed length of 7 bytes
        return struct.pack('I4s6s7s', this_layer_data.user_id, user_ip_encoded, user_mac_encoded, access_action_encoded)