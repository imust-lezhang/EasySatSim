import asyncio
from abc import ABC, abstractmethod


class AbstractBuffer(ABC):
    """
    This abstract class is used to define the buffer
    """
    def __init__(self, max_byte, interface):
        """
        :param max_byte: The maximum number of bytes that the buffer can store
        :param interface: The name of the buffer interface
        """
        self.max_byte = max_byte  # The maximum number of bytes that the buffer can store
        self.current_byte = 0  # The current number of bytes in the buffer
        self.interface = interface  # Interface name
        self.queue = asyncio.Queue()  # Queue as a buffer

    # Calculate the packet size
    @abstractmethod
    def get_data_size(self, data):
        """
        Used to calculate the size of the data packet
        :param data: Any type of data packet, usually the data packet received at the interface
        :return: The size of the data packet, float or int
        """
        pass

    @abstractmethod
    async def put(self, data):
        """
        Used to store the data packet in the buffer, need to calculate the current buffer capacity and the size of the data packet and determine whether it can be put in or dropped
        :param data: The received data packet
        :return: None
        """
        pass

    @abstractmethod
    async def get(self):
        """
        Used to get the data packet from the buffer, need to calculate the current buffer capacity in real time
        :return: data, the obtained data packet
        """
        pass

    @abstractmethod
    def task_done(self):
        """
        Because of the queue type, task_done needs to be executed after the buffer operation is completed, usually directly defined as task_done
        :return: None
        """
        pass