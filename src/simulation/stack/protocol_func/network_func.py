from src.abstract.stack.protocol_func import AbstractProtocolFunc
from src.abstract.stack.routing import RoutingAlgorithm
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage, ActionType
from src.simulation.stack.protocol_data.network_data import DataPacket, NeighborInfo
from src.simulation.variable.virtual_store import VirtualStore
from configuration import simulation_config as cg
from src.simulation.variable.performance import NetworkPerformance
from src.tools.calculation import find_valid_directions


class MinHopRouting(RoutingAlgorithm):
    @staticmethod
    def routing_algorithm(entity, cross_layer_message, src_satellite_id, dst_satellite_id):
        src_satellite_set = (
        src_satellite_id // cg.SATELLITE_NUMBER_PRE_ORBIT, src_satellite_id % cg.SATELLITE_NUMBER_PRE_ORBIT)
        dst_satellite_set = (
        dst_satellite_id // cg.SATELLITE_NUMBER_PRE_ORBIT, dst_satellite_id % cg.SATELLITE_NUMBER_PRE_ORBIT)
        next_dict, next_satellite_id = find_valid_directions(origin=src_satellite_set, target=dst_satellite_set,
                                                             N=cg.ORBIT_NUMBER, M=cg.SATELLITE_NUMBER_PRE_ORBIT)
        return next_satellite_id


class Type0x0800(AbstractProtocolFunc):
    routing_algorithm_func = MinHopRouting.routing_algorithm
    """
    Network layer 0x0800 protocol IP protocol
    """

    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage, callback=None):
        if entity.ip_address in cross_layer_message.data_others["ip_list"]:
            cross_layer_message.action = ActionType.STOP
            NetworkPerformance.packet_loss(data_size_byte=cross_layer_message.data_others["data_size_byte"],
                                           reason="network layer ttl > 64")
            return cross_layer_message
        cross_layer_message.data_others["ip_list"].append(entity.ip_address)

        data_packet: DataPacket = cross_layer_message.data
        if data_packet.destination_ip == entity.ip_address:  # If the target IP is itself, then directly resolve it upwards.
            cross_layer_message.action = ActionType.PARSE
            cross_layer_message.cross_layer_interface = data_packet.protocol

        else:  # If the destination IP is not itself, it needs to perform forwarding operation.
            if data_packet.destination_ip in entity.routing_table:  # If the destination IP is in its own routing table, just forward it directly.
                next_hop_ip = entity.routing_table[data_packet.destination_ip]["next_hop_ip"]
                cross_layer_message.action = ActionType.ENCAPSULATE
                cross_layer_message.data_others["next_hop_ip"] = next_hop_ip
                cross_layer_message.cross_layer_interface = "Ethernet"
                cross_layer_message.data_others["type"] = 0x0800
            else:  # The destination IP is not in its own routing table, and the routing path needs to be calculated.
                # Judging whether the target IP is a user or a satellite.
                if data_packet.destination_ip in VirtualStore.set_user_ip:  # The target IP is a user and needs to find the satellite it accesses.

                    if data_packet.destination_ip in VirtualStore.user_access_table:  # If the user IP has been accessed.

                        dst_satellite_ip = VirtualStore.user_access_table[data_packet.destination_ip]
                    else:  # Otherwise, the target user does not access any satellite, and the packet is lost.

                        NetworkPerformance.packet_loss(data_size_byte=cross_layer_message.data_others["data_size_byte"], reason="network layer target user dont access any satellite")
                        cross_layer_message.action = ActionType.STOP
                        return cross_layer_message
                elif data_packet.destination_ip in VirtualStore.set_satellite_ip:  #The target IP is a satellite.

                    dst_satellite_ip = data_packet.destination_ip
                else:  # The target IP is neither a user nor a satellite, and the packet is directly dropped.

                    NetworkPerformance.packet_loss(data_size_byte=cross_layer_message.data_others["data_size_byte"], reason="network layer unknown target ip")
                    cross_layer_message.action = ActionType.STOP
                    return cross_layer_message
                # Calculate routing path
                src_satellite_id = entity.entity_id
                dst_satellite_id = VirtualStore.satellite_ip_to_id_table[dst_satellite_ip]

                next_satellite_id = Type0x0800.routing_algorithm_func(entity=entity
                                                                      , cross_layer_message=cross_layer_message
                                                                      , src_satellite_id=src_satellite_id
                                                                      , dst_satellite_id=dst_satellite_id)

                if next_satellite_id is None:
                    NetworkPerformance.packet_loss(
                        data_size_byte=cross_layer_message.data_others["data_size_byte"],
                        reason="network layer no next satellite id")
                    cross_layer_message.action = ActionType.STOP
                    return cross_layer_message


                next_hop_ip = VirtualStore.satellite_id_to_ip_table[next_satellite_id]
                entity.update_routing_table(destination_ip=data_packet.destination_ip, next_hop_ip=next_hop_ip)
                cross_layer_message.action = ActionType.ENCAPSULATE
                cross_layer_message.data_others["next_hop_ip"] = next_hop_ip
                cross_layer_message.cross_layer_interface = "Ethernet"
                cross_layer_message.data_others["type"] = 0x0800
        return cross_layer_message


    @staticmethod
    def encapsulate_func(entity, cross_layer_message: CrossLayerMessage):
        source_ip = cross_layer_message.data_others["source_ip"]
        del cross_layer_message.data_others["source_ip"]
        destination_ip = cross_layer_message.data_others["target_ip"]
        del cross_layer_message.data_others["target_ip"]
        out_interface = 'Ethernet'
        data_packet = DataPacket(version=1, header_length=5, total_length=150, identification=12345, ttl=64,
                                 protocol=cross_layer_message.data_others["protocol"], header_checksum=0,
                                 source_ip=source_ip, destination_ip=destination_ip,
                                 payload=cross_layer_message.data)
        del cross_layer_message.data_others["protocol"]
        cross_layer_message.action = ActionType.ENCAPSULATE
        cross_layer_message.cross_layer_interface = out_interface
        cross_layer_message.data = data_packet
        cross_layer_message.data_others["type"] = 0x0800
        return cross_layer_message


class Type0x9000(AbstractProtocolFunc):
    """
    The neighbor update protocol customized by 0x9000 protocol.
    """
    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage):
        neighbor_info: NeighborInfo = cross_layer_message.data
        if neighbor_info.destination_ip == entity.ip_address:  # 如果目标IP是自己，处理
            satellite_id = neighbor_info.satellite_id
            entity.neighbor_table[satellite_id]["is_alive"] = neighbor_info.is_alive
            entity.neighbor_table[satellite_id]["delay"] = neighbor_info.delay
            entity.neighbor_table[satellite_id]["load"] = neighbor_info.load
            entity.neighbor_table[satellite_id]["last_update_time"] = neighbor_info.last_update_time
        cross_layer_message.action = ActionType.STOP
        return cross_layer_message

    @staticmethod
    def encapsulate_func(entity, cross_layer_message: CrossLayerMessage):
        cross_layer_message.action = ActionType.ENCAPSULATE
        cross_layer_message.cross_layer_interface = 'Ethernet'
        cross_layer_message.data_others["type"] = 0x9000
        return cross_layer_message

