import threading
import time
from configuration import simulation_config as cg
from src.simulation.variable import constant as ct
from multiprocessing import shared_memory
import numpy as np


class GlobalTimer:
    """
    Global timer, used to record global time
    """
    def __init__(self):
        self.step_size = cg.NETWORK_RUNNING_STEP_SECOND  # The actual number of seconds corresponding to one step in the program
        self.shm_current_time = shared_memory.SharedMemory(name=ct.SHM_CURRENT_TIME)
        self.current_time = np.ndarray((1,), dtype=np.float64, buffer=self.shm_current_time.buf)  # Assume we use this space to store integers
        self.running = False
        self.lock = threading.Lock()
        self.update_event = threading.Event()  # Used for synchronizing updates and printing


    def start(self):
        """
        Start timing
        :return: None
        """
        with self.lock:
            if not self.running:
                self.running = True
                threading.Thread(target=self._update_timer, daemon=True).start()


    def _update_timer(self):
        """
        Time updater
        :return: None
        """
        while self.running:
            time.sleep(0.05)  # Update once per second
            with self.lock:
                self.current_time[0] = self.current_time[0] + self.step_size
            self.update_event.set()  # Set the event to notify the main thread that it can print the time


    def stop(self):
        with self.lock:
            self.running = False
        self.update_event.set()  # Ensure that any waiting threads can continue


    def reset(self):
        with self.lock:
            self.current_time[0] = 0


    def get_current_time(self) -> int:
        with self.lock:
            return self.current_time[0]


    def wait_for_update(self):
        self.update_event.wait()  # Wait for the update event
        self.update_event.clear()  # Clear the event for the next update


    def report_current_time(self):
        self.wait_for_update()
        print(f" ======================================================\n"
              f"Program Time: {self.get_current_time()} steps")