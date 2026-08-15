from src.abstract.entity.buffer import AbstractBuffer
from src.simulation.variable.performance import NetworkPerformance
from configuration import simulation_config as cg


class DefaultBuffer(AbstractBuffer):
    """
    Implements a wireless interface
    """
    def __init__(self, max_byte, interface):
        super().__init__(max_byte, interface)
        self.count = 0


    def get_buffer_length(self):
        return self.queue.qsize()


    def get_data_size(self, data):
        return data.size * 1024


    def get_current_byte(self):
        return self.current_byte


    def get_current_kb(self):
        return self.current_byte / 1024


    def get_current_mb(self):
        return self.current_byte / 1024 / 1024


    def get_queue_delay(self):
        # print(self.current_byte / cg.SERVICE_RATE)
        return self.current_byte / cg.SERVICE_RATE  # 100Mbps


    async def put(self, data):
        data_size = data.data_others["data_size_byte"]
        if self.current_byte + data_size <= self.max_byte:
            await self.queue.put(data)
            self.current_byte = self.current_byte + data_size
            # Calculate queuing delay
            self.count += 1
            data.data_others["delay"] += self.get_queue_delay()
        else:  # The data packet is full and cannot be added, packet loss
            NetworkPerformance.packet_loss(data_size_byte=data_size, reason="buffer over flow")
        return


    async def get(self):
        data = await self.queue.get()
        self.current_byte = self.current_byte - data.data_others["data_size_byte"]
        self.count -= 1
        return data


    def task_done(self):
        self.queue.task_done()
        return