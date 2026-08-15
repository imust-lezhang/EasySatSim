from dataclasses import dataclass
from collections import deque
import threading
import time
from colorama import Fore, Style, init
import multiprocessing
from src.simulation.variable import constant as ct
from multiprocessing import shared_memory
import numpy as np
from configuration import simulation_config as cg
from src.tools.file_operations import DataWriter

init(autoreset=True)

@dataclass
class NetworkMetrics:
    generate_packets_number: float = 0  # Total number of generated packets
    generate_packets_byte: float = 0.0  # Total size of generated packets
    arrive_packets_number: float = 0  # Total number of arrived packets
    arrive_packets_byte: float = 0.0  # Size of arrived packets
    loss_packets_number: float = 0  # Number of lost packets
    loss_packets_byte: float = 0.0  # Size of lost packets
    delay: float = 0.0  # Total delay
    user_cover_number: float = 0  # Number of covered users
    normal_satellite_number: float = 0  # Number of normal satellites


    hop_count: float = 0  # Hop count / needs to be divided by the average
    load_deviation: float = 0.0  # Load deviation / value calculated per round


    def report(self, running_time):
        if self.arrive_packets_number > 0:
            delay = self.delay / self.arrive_packets_number
        else:
            delay = self.delay
        if self.arrive_packets_number > 0:
            hop_count = self.hop_count / self.arrive_packets_number
        else:
            hop_count = self.hop_count
        header = f"{Fore.LIGHTWHITE_EX}╔{' Network Metrics '.center(90, '═')}╗"
        footer = f"{Fore.LIGHTWHITE_EX}╚{'═' * 90}╝"
        labels = [f"{Fore.LIGHTWHITE_EX}║  Running Time", f"{Fore.LIGHTWHITE_EX}║  Generated Packets", f"{Fore.LIGHTWHITE_EX}║  Arrived Packets"
            , f"{Fore.LIGHTWHITE_EX}║  Lost Packets", f"{Fore.LIGHTWHITE_EX}║  Latency", f"{Fore.LIGHTWHITE_EX}║  Number of Covered Users"
            , f"{Fore.LIGHTWHITE_EX}║  Number of Operational Satellites", f"{Fore.LIGHTWHITE_EX}║  Average Hop Count", f"{Fore.LIGHTWHITE_EX}║  Load Deviation"]
        if running_time < 15:
            _tmp_running_time = f"{running_time} [Note] The network is initializing, the results may be unstable.)"
        else:
            _tmp_running_time = f"{running_time}"
        values = [_tmp_running_time,
                  f"{self.generate_packets_number:.2f} packets, {self.generate_packets_byte:.2f} bytes",
                  f"{self.arrive_packets_number:.2f} packets, {self.arrive_packets_byte:.2f} bytes",
                  f"{self.loss_packets_number:.2f} packets, {self.loss_packets_byte:.2f} bytes",
                  f"{delay:.2f} ms",
                  f"{self.user_cover_number:.2f}",
                  f"{self.normal_satellite_number:.2f}",
                  f"{hop_count:.2f}",
                  f"{self.load_deviation:.2f}"]

        lines = [f"{label.ljust(18)}: {value}".ljust(95) + f"{Fore.LIGHTWHITE_EX} ║"
                 for label, value in zip(labels, values)]
        return f"{header}\n" + "\n".join(lines) + f"\n{footer}"



class SharedNetworkMetrics:
    def __init__(self):
        self.generate_packets_number = multiprocessing.Value('d', 0.0)
        self.generate_packets_byte = multiprocessing.Value('d', 0.0)
        self.arrive_packets_number = multiprocessing.Value('d', 0.0)
        self.arrive_packets_byte = multiprocessing.Value('d', 0.0)
        self.loss_packets_number = multiprocessing.Value('d', 0.0)
        self.loss_packets_byte = multiprocessing.Value('d', 0.0)
        self.delay = multiprocessing.Value('d', 0.0)
        self.user_cover_number = multiprocessing.Value('d', 0.0)
        self.normal_satellite_number = multiprocessing.Value('d', 0.0)
        self.hop_count = multiprocessing.Value('d', 0.0)
        self.load_deviation = multiprocessing.Value('d', 0.0)

        self.global_generate_packets_number = multiprocessing.Value('d', 0.0)
        self.global_generate_packets_byte = multiprocessing.Value('d', 0.0)
        self.global_arrive_packets_number = multiprocessing.Value('d', 0.0)
        self.global_arrive_packets_byte = multiprocessing.Value('d', 0.0)
        self.global_loss_packets_number = multiprocessing.Value('d', 0.0)
        self.global_loss_packets_byte = multiprocessing.Value('d', 0.0)
        self.global_delay = multiprocessing.Value('d', 0.0)
        self.global_user_cover_number = multiprocessing.Value('d', 0.0)
        self.global_normal_satellite_number = multiprocessing.Value('d', 0.0)
        self.global_hop_count = multiprocessing.Value('d', 0.0)
        self.global_load_deviation = multiprocessing.Value('d', 0.0)


    def update_shared_metrics(self, current_network_metric: NetworkMetrics, global_network_metric: NetworkMetrics):
        if current_network_metric.arrive_packets_number + current_network_metric.loss_packets_number > 0:
            delay = current_network_metric.delay / (current_network_metric.arrive_packets_number + current_network_metric.loss_packets_number)
        else:
            delay = current_network_metric.delay

        if current_network_metric.arrive_packets_number > 0:
            hop_count = current_network_metric.hop_count / current_network_metric.arrive_packets_number
        else:
            hop_count = current_network_metric.hop_count
        self.generate_packets_number.value = current_network_metric.generate_packets_number
        self.generate_packets_byte.value = current_network_metric.generate_packets_byte
        self.arrive_packets_number.value = current_network_metric.arrive_packets_number
        self.arrive_packets_byte.value = current_network_metric.arrive_packets_byte
        self.loss_packets_number.value = current_network_metric.loss_packets_number
        self.loss_packets_byte.value = current_network_metric.loss_packets_byte
        self.delay.value = delay
        self.user_cover_number.value = current_network_metric.user_cover_number
        self.normal_satellite_number.value = current_network_metric.normal_satellite_number
        self.hop_count.value = hop_count
        self.load_deviation.value = current_network_metric.load_deviation

        if global_network_metric.arrive_packets_number + global_network_metric.loss_packets_number > 0:
            delay = global_network_metric.delay / (global_network_metric.arrive_packets_number + global_network_metric.loss_packets_number)
        else:
            delay = global_network_metric.delay
        self.global_generate_packets_number.value = global_network_metric.generate_packets_number
        self.global_generate_packets_byte.value = global_network_metric.generate_packets_byte
        self.global_arrive_packets_number.value = global_network_metric.arrive_packets_number
        self.global_arrive_packets_byte.value = global_network_metric.arrive_packets_byte
        self.global_loss_packets_number.value = global_network_metric.loss_packets_number
        self.global_loss_packets_byte.value = global_network_metric.loss_packets_byte
        self.global_delay.value = delay
        self.global_user_cover_number.value = global_network_metric.user_cover_number
        self.global_normal_satellite_number.value = global_network_metric.normal_satellite_number
        self.global_hop_count.value = global_network_metric.hop_count
        self.global_load_deviation.value = global_network_metric.load_deviation




class NetworkPerformance:
    """
    Global performance metrics, used to record all performance metrics and average performance metrics per window_size
    """
    global_metrics = NetworkMetrics()  # Used to record global performance metrics
    average_metrics = NetworkMetrics()  # Used to output average performance metrics
    current_second_metrics = NetworkMetrics()  # Performance metrics at the current moment


    window_size = 2  # Window size, average performance metrics every 10 seconds
    metrics_window = deque(maxlen=window_size)  # Deque for storing performance metrics


    lock = threading.Lock()
    running = True


    @staticmethod
    def start(shared_metric, output):
        thread = threading.Thread(target=NetworkPerformance.evaluate_per_second, args=(shared_metric, output, ))
        thread.start()

    @staticmethod
    def evaluate_per_second(shared_metric: SharedNetworkMetrics, output):
        """
        Continuously calculate, output, and save metrics
        :param shared_metric:
        :return:
        """
        _shm_access_relationship = shared_memory.SharedMemory(name=ct.SHM_ACCESS_RELATIONSHIP)
        access_relationship = np.ndarray((cg.USER_NUMBER,), dtype=np.int64
                                         , buffer=_shm_access_relationship.buf)
        _shm_satellite_load_deviation = shared_memory.SharedMemory(name=ct.SHM_SATELLITE_LOAD_DEVIATION)
        satellite_load_deviation = np.ndarray((cg.ORBIT_NUMBER, cg.SATELLITE_NUMBER_PRE_ORBIT,), dtype=np.float64
                                              , buffer=_shm_satellite_load_deviation.buf)


        title_row = ["Time"

            , "Current_Generated_Packets_Number", "Current_Arrived_Packets_Number"
            , "Current_Lost_Packets_Number", "Current_Generated_Packets_Byte", "Current_Arrived_Packets_Byte"
            , "Current_Lost_Packets_Byte", "Current_Latency", "Current_Covered_Users_Number"
            , "Current_Operational_Satellite_Number", "Current_Hop_Count", "Current_Load_Deviation"

            , "Total_Generated_Packets_Number", "Total_Arrived_Packets_Number"
            , "Total_Lost_Packets_Number", "Total_Generated_Packets_Byte", "Total_Arrived_Packets_Byte"
            , "Total_Lost_Packets_Byte", "Total_Latency", "Total_Covered_Users_Number"
            , "Total_Operational_Satellite_Number", "Total_Hop_Count", "Total_Load_Deviation"
                     ]
        data_writer = DataWriter(filename=cg.SAVE_FILE_PATH, title_row=title_row)

        write_time = 0
        print("[Note] Network performance is the average within ten seconds. ")
        while NetworkPerformance.running:
            # Collect some variables per second
            cover_user_number = np.sum(access_relationship > 0)
            NetworkPerformance.current_second_metrics.user_cover_number = cover_user_number
            NetworkPerformance.global_metrics.user_cover_number = cover_user_number

            number_of_normal_satellite = np.sum(satellite_load_deviation >= 0)
            NetworkPerformance.current_second_metrics.normal_satellite_number = number_of_normal_satellite
            NetworkPerformance.global_metrics.normal_satellite_number = number_of_normal_satellite

            # Calculate load deviation
            _tmp_load_deviation = satellite_load_deviation[satellite_load_deviation >= 0]

            average_load_deviation = np.mean(_tmp_load_deviation)
            abs_load_deviation = np.abs(_tmp_load_deviation - average_load_deviation)

            if average_load_deviation > 0:
                load_deviation = np.sum(abs_load_deviation) / _tmp_load_deviation.size / average_load_deviation
            else:
                load_deviation = 0
            NetworkPerformance.current_second_metrics.load_deviation = load_deviation
            NetworkPerformance.global_metrics.load_deviation = load_deviation
            NetworkPerformance.current_second_metrics.normal_satellite_number = number_of_normal_satellite
            NetworkPerformance.global_metrics.normal_satellite_number = number_of_normal_satellite
            # Calculate average metrics
            NetworkPerformance.calculate_average_metrics()
            # Upload metrics to a shared variable per second
            shared_metric.update_shared_metrics(current_network_metric=NetworkPerformance.average_metrics
                                                , global_network_metric=NetworkPerformance.global_metrics)

            # Output results
            output_data = [write_time
                , shared_metric.generate_packets_number.value, shared_metric.arrive_packets_number.value, shared_metric.loss_packets_number.value
                , shared_metric.generate_packets_byte.value, shared_metric.arrive_packets_byte.value, shared_metric.loss_packets_byte.value
                , shared_metric.delay.value, shared_metric.user_cover_number.value, shared_metric.normal_satellite_number.value
                , shared_metric.hop_count.value, shared_metric.load_deviation.value

                , shared_metric.global_generate_packets_number.value, shared_metric.global_arrive_packets_number.value, shared_metric.global_loss_packets_number.value
                , shared_metric.global_generate_packets_byte.value, shared_metric.global_arrive_packets_byte.value, shared_metric.global_loss_packets_byte.value
                , shared_metric.global_delay.value, shared_metric.global_user_cover_number.value, shared_metric.global_normal_satellite_number.value
                , shared_metric.global_hop_count.value, shared_metric.global_load_deviation.value
            ]
            data_writer.write_data(data=output_data)
            # Output metrics
            if output:
                NetworkPerformance.report_metrics(write_time)
            with NetworkPerformance.lock:
                NetworkPerformance.current_second_metrics = NetworkMetrics()  # 重新设置新一秒的性能指标
            write_time += 1
            time.sleep(1)


    @staticmethod
    def report_metrics(running_time):
        """
         Output average performance metrics within window_size
         :return: None
        """
        with NetworkPerformance.lock:
            # Output the average result every ten seconds
            print(NetworkPerformance.average_metrics.report(running_time=running_time))


    @staticmethod
    def packet_generate(data_size_byte):
        """
        Method to update metrics after generating a packet
        :param data_size_byte: Packet size
        :return:
        """
        with NetworkPerformance.lock:
            NetworkPerformance.current_second_metrics.generate_packets_number += 1
            NetworkPerformance.current_second_metrics.generate_packets_byte += data_size_byte
            NetworkPerformance.global_metrics.generate_packets_number += 1
            NetworkPerformance.global_metrics.generate_packets_byte += data_size_byte
        return

    @staticmethod
    def packet_loss(data_size_byte, reason):
        """
        Calculate metrics after packet loss
        :param data_size_byte: Packet size
        :return:
        """
        with NetworkPerformance.lock:
            NetworkPerformance.current_second_metrics.loss_packets_number += 1
            NetworkPerformance.global_metrics.loss_packets_number += 1
            NetworkPerformance.current_second_metrics.delay += 999
            NetworkPerformance.global_metrics.delay += 999
            NetworkPerformance.current_second_metrics.loss_packets_byte += data_size_byte
            NetworkPerformance.global_metrics.loss_packets_byte += data_size_byte
        return

    @staticmethod
    def packet_arrive(data_size_byte, total_delay, hop_count, RTT=0):
        """
        Calculate metrics after packet arrival
        :param data_size_byte: Packet size
        :param total_delay: Total delay
        :return:
        """
        with NetworkPerformance.lock:
            NetworkPerformance.current_second_metrics.arrive_packets_number += 1
            NetworkPerformance.global_metrics.arrive_packets_number += 1
            NetworkPerformance.current_second_metrics.arrive_packets_byte += data_size_byte
            NetworkPerformance.global_metrics.arrive_packets_byte += data_size_byte
            NetworkPerformance.current_second_metrics.delay += total_delay
            NetworkPerformance.global_metrics.delay += total_delay
            NetworkPerformance.current_second_metrics.hop_count += hop_count
            NetworkPerformance.global_metrics.hop_count += hop_count
        return

    @staticmethod
    def packet_delay(delay):
        with NetworkPerformance.lock:
            NetworkPerformance.current_second_metrics.delay += delay
            NetworkPerformance.global_metrics.delay += delay
        return


    @staticmethod
    def calculate_average_metrics():
        _temp_metrics = NetworkMetrics()
        NetworkPerformance.metrics_window.append(NetworkPerformance.current_second_metrics)
        for metrics in NetworkPerformance.metrics_window:
            _temp_metrics.generate_packets_number += metrics.generate_packets_number
            _temp_metrics.generate_packets_byte += metrics.generate_packets_byte
            _temp_metrics.arrive_packets_number += metrics.arrive_packets_number
            _temp_metrics.arrive_packets_byte += metrics.arrive_packets_byte
            _temp_metrics.loss_packets_number += metrics.loss_packets_number
            _temp_metrics.loss_packets_byte += metrics.loss_packets_byte
            _temp_metrics.delay += metrics.delay
            _temp_metrics.user_cover_number += metrics.user_cover_number
            _temp_metrics.normal_satellite_number += metrics.normal_satellite_number
            _temp_metrics.hop_count += metrics.hop_count
            _temp_metrics.load_deviation += metrics.load_deviation
        _temp_metrics.generate_packets_number = _temp_metrics.generate_packets_number / len(NetworkPerformance.metrics_window)
        _temp_metrics.generate_packets_byte = _temp_metrics.generate_packets_byte / len(NetworkPerformance.metrics_window)
        _temp_metrics.arrive_packets_number = _temp_metrics.arrive_packets_number / len(NetworkPerformance.metrics_window)
        _temp_metrics.arrive_packets_byte = _temp_metrics.arrive_packets_byte / len(NetworkPerformance.metrics_window)
        _temp_metrics.loss_packets_number = _temp_metrics.loss_packets_number / len(NetworkPerformance.metrics_window)
        _temp_metrics.loss_packets_byte = _temp_metrics.loss_packets_byte / len(NetworkPerformance.metrics_window)
        _temp_metrics.delay = _temp_metrics.delay / len(NetworkPerformance.metrics_window)
        _temp_metrics.user_cover_number = _temp_metrics.user_cover_number / len(NetworkPerformance.metrics_window)
        _temp_metrics.normal_satellite_number = _temp_metrics.normal_satellite_number / len(NetworkPerformance.metrics_window)
        _temp_metrics.hop_count = _temp_metrics.hop_count / len(NetworkPerformance.metrics_window)
        _temp_metrics.load_deviation = _temp_metrics.load_deviation / len(NetworkPerformance.metrics_window)
        NetworkPerformance.average_metrics = _temp_metrics
        return


