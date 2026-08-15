from configuration import simulation_config as cg
from cases.case3.experiment.routing.centralized_routing import CentralizedPeriodicRouting
from src.abstract.stack.protocol_func import AbstractProtocolFunc
from src.simulation.stack.cross_layer_message.cross_layer_message import (
    ActionType,
    CrossLayerMessage,
)
from src.simulation.stack.protocol_data.network_data import DataPacket
from src.simulation.stack.protocol_func.network_func import Type0x0800
from src.simulation.variable.performance import NetworkPerformance
from src.simulation.variable.virtual_store import VirtualStore


class Case3CentralizedNetworkLayer(AbstractProtocolFunc):
    routing_algorithm_func = Type0x0800.routing_algorithm_func

    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage, callback=None):
        if entity.ip_address in cross_layer_message.data_others["ip_list"]:
            cross_layer_message.action = ActionType.STOP
            NetworkPerformance.packet_loss(
                data_size_byte=cross_layer_message.data_others["data_size_byte"],
                reason="network layer ttl > 64",
            )
            return cross_layer_message
        cross_layer_message.data_others["ip_list"].append(entity.ip_address)

        data_packet: DataPacket = cross_layer_message.data
        if data_packet.destination_ip == entity.ip_address:
            cross_layer_message.action = ActionType.PARSE
            cross_layer_message.cross_layer_interface = data_packet.protocol
            return cross_layer_message

        if data_packet.destination_ip in entity.routing_table:
            route_entry = entity.routing_table[data_packet.destination_ip]
            _refresh_controller_if_needed(entity=entity)
            if _is_outdated_centralized_cache(route_entry):
                del entity.routing_table[data_packet.destination_ip]
            else:
                next_hop_ip = route_entry["next_hop_ip"]
                cross_layer_message.action = ActionType.ENCAPSULATE
                cross_layer_message.data_others["next_hop_ip"] = next_hop_ip
                cross_layer_message.cross_layer_interface = "Ethernet"
                cross_layer_message.data_others["type"] = 0x0800
                return cross_layer_message

        dst_satellite_ip = _resolve_destination_satellite_ip(
            data_packet=data_packet,
            cross_layer_message=cross_layer_message,
        )
        if dst_satellite_ip is None:
            return cross_layer_message

        src_satellite_id = entity.entity_id
        dst_satellite_id = VirtualStore.satellite_ip_to_id_table[dst_satellite_ip]
        next_satellite_id = Type0x0800.routing_algorithm_func(
            entity=entity,
            cross_layer_message=cross_layer_message,
            src_satellite_id=src_satellite_id,
            dst_satellite_id=dst_satellite_id,
        )
        if next_satellite_id is None:
            NetworkPerformance.packet_loss(
                data_size_byte=cross_layer_message.data_others["data_size_byte"],
                reason="network layer no next satellite id",
            )
            cross_layer_message.action = ActionType.STOP
            return cross_layer_message

        next_hop_ip = VirtualStore.satellite_id_to_ip_table[next_satellite_id]
        entity.update_routing_table(
            destination_ip=data_packet.destination_ip,
            next_hop_ip=next_hop_ip,
        )
        _tag_route_entry_with_current_version(
            entity=entity,
            destination_ip=data_packet.destination_ip,
        )
        cross_layer_message.action = ActionType.ENCAPSULATE
        cross_layer_message.data_others["next_hop_ip"] = next_hop_ip
        cross_layer_message.cross_layer_interface = "Ethernet"
        cross_layer_message.data_others["type"] = 0x0800
        return cross_layer_message

    @staticmethod
    def encapsulate_func(entity, cross_layer_message: CrossLayerMessage):
        return Type0x0800.encapsulate_func(
            entity=entity,
            cross_layer_message=cross_layer_message,
        )


def _resolve_destination_satellite_ip(data_packet, cross_layer_message):
    if data_packet.destination_ip in VirtualStore.set_user_ip:
        if data_packet.destination_ip in VirtualStore.user_access_table:
            return VirtualStore.user_access_table[data_packet.destination_ip]
        NetworkPerformance.packet_loss(
            data_size_byte=cross_layer_message.data_others["data_size_byte"],
            reason="network layer target user dont access any satellite",
        )
        cross_layer_message.action = ActionType.STOP
        return None

    if data_packet.destination_ip in VirtualStore.set_satellite_ip:
        return data_packet.destination_ip

    NetworkPerformance.packet_loss(
        data_size_byte=cross_layer_message.data_others["data_size_byte"],
        reason="network layer unknown target ip",
    )
    cross_layer_message.action = ActionType.STOP
    return None


def _refresh_controller_if_needed(entity):
    controller = CentralizedPeriodicRouting.controller
    if controller is not None:
        controller.refresh_if_needed(current_time=float(entity.current_time[0]))


def _is_outdated_centralized_cache(route_entry):
    controller = CentralizedPeriodicRouting.controller
    if controller is None:
        return False
    if route_entry.get("update_interval") != cg.SATELLITE_ROUTING_UPDATE_TIME:
        return False
    route_version = route_entry.get("route_version")
    if route_version is None:
        return False
    return int(route_version) < int(controller.route_version)


def _tag_route_entry_with_current_version(entity, destination_ip):
    controller = CentralizedPeriodicRouting.controller
    if controller is None:
        return
    route_entry = entity.routing_table.get(destination_ip)
    if route_entry is None:
        return
    if route_entry.get("update_interval") == cg.SATELLITE_ROUTING_UPDATE_TIME:
        route_entry["route_version"] = controller.route_version

