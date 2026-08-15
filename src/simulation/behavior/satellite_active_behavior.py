from collections import deque
from src.abstract.behavior.behavior import AbstractBehavior
from configuration import simulation_config as cg
from src.simulation.variable.virtual_store import VirtualStore
from src.tools.calculation import PhysicalLayerModel
from src.simulation.stack.protocol_data.network_data import NeighborInfo
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage, ActionType
from src.simulation.stack.stack_func import StackFunc


class SatelliteActiveBehavior(AbstractBehavior):
    @staticmethod
    async def update_routing_table(entity, data):
        # Update the routing table
        delete_keys = []
        for key, value in entity.routing_table.items():
            if (entity.current_time[0] - value["last_update_time"]) > value["update_interval"]:
                delete_keys.append(key)
        for key in delete_keys:
            del entity.routing_table[key]

        # Update the neighbor table and set neighbors that are not updated on time as invalid
        for satellite_id, info in entity.neighbor_table.items():
            if (entity.current_time[0] - info["last_update_time"]) > cg.MAX_NEIGHBOR_UPDATE_TIME:
                info["is_alive"] = False

        # Send messages to neighbors
        if (entity.current_time[0] - entity.last_send_info_time) > cg.SATELLITE_NEIGHBOR_UPDATE_TIME:
            my_position = entity.satellite_position_3d[entity.entity_id]
            my_load = entity.buffers["Default"].get_current_kb()
            queue_delay = entity.buffers["Default"].get_queue_delay()
            for satellite_id in entity.neighbor_table.keys():
                satellite_position = entity.satellite_position_3d[satellite_id]
                link_state = PhysicalLayerModel.get_link_state(
                    source_position_3d=my_position,
                    target_position_3d=satellite_position,
                    data_size_byte=0,
                    source_id=entity.entity_id,
                    target_id=satellite_id,
                    source_category="satellite",
                    target_category="satellite",
                    current_time=entity.current_time[0],
                    processing_time_ms=0,
                )
                _update_neighbor_physical_state(entity=entity, satellite_id=satellite_id, link_state=link_state)
                if not link_state.is_available:
                    entity.neighbor_table[satellite_id]["is_alive"] = False
                    continue

                transmission_delay = my_load / link_state.effective_rate_bps
                delay = link_state.propagation_delay_ms + queue_delay + transmission_delay
                satellite_ip, satellite_mac, satellite_buffers = VirtualStore.get_satellite_info_from_id(
                    satellite_id=satellite_id)
                await _send_neighbor_info(entity=entity, satellite_ip=satellite_ip, satellite_buffer=satellite_buffers
                                     , delay=delay, is_alive=True, load=my_load, last_update_time=entity.current_time[0])
            entity.last_send_info_time = entity.current_time[0]
        return

    @staticmethod
    def update_load_deivation(entity, data):

        if entity.satellite_load_deviation[entity.orbit_id][entity.satellite_id] >= 0:
            entity.satellite_load_deviation[entity.orbit_id][entity.satellite_id] = entity.buffers["Default"].get_current_kb()
            queue_delay = entity.buffers["Default"].get_queue_delay()
            effective_rate_bps = _get_average_neighbor_rate(entity=entity)
            transmission_delay = entity.buffers["Default"].get_current_kb() / effective_rate_bps
            entity.satellite_latency[entity.orbit_id][entity.satellite_id] = queue_delay + transmission_delay
        return


async def _send_neighbor_info(entity, satellite_ip, satellite_buffer, delay, is_alive, load, last_update_time):
    message = NeighborInfo(source_ip=entity.ip_address, destination_ip=satellite_ip, delay=delay, is_alive=is_alive
                        , load=load, satellite_id=entity.entity_id, last_update_time=last_update_time)
    data_others = {"source_ip": entity.ip_address, "target_ip": satellite_ip, "next_hop_ip": satellite_ip
                 , "data_size_byte": 0, "delay": 0, "path": None, "ip_list": deque()}
    cross_layer_message = CrossLayerMessage(action=ActionType.ENCAPSULATE, cross_layer_interface=0x9000,
                                       data=message, data_others=data_others)
    cross_layer_message = StackFunc.encapsulate_network_to_signal(entity=entity,
                                                       cross_layer_message=cross_layer_message)
    await satellite_buffer["Default"].put(cross_layer_message)


def _update_neighbor_physical_state(entity, satellite_id, link_state):
    entity.neighbor_table[satellite_id]["distance_m"] = link_state.distance_m
    entity.neighbor_table[satellite_id]["propagation_delay_ms"] = link_state.propagation_delay_ms
    entity.neighbor_table[satellite_id]["doppler_shift_hz"] = link_state.doppler_shift_hz
    entity.neighbor_table[satellite_id]["snr_db"] = link_state.snr_db
    entity.neighbor_table[satellite_id]["effective_rate_bps"] = link_state.effective_rate_bps
    entity.neighbor_table[satellite_id]["path_loss_db"] = link_state.path_loss_db
    entity.neighbor_table[satellite_id]["physical_is_available"] = link_state.is_available
    entity.neighbor_table[satellite_id]["physical_update_time"] = link_state.updated_at
    return


def _get_average_neighbor_rate(entity):
    rates = []
    for info in entity.neighbor_table.values():
        rate = info.get("effective_rate_bps", 0)
        if info.get("physical_is_available", True) and rate > 0:
            rates.append(rate)
    if rates:
        return sum(rates) / len(rates)
    return PhysicalLayerModel.get_link_config("isl")["static_rate_bps"]
