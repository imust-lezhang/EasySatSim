from src.abstract.behavior.behavior import AbstractBehavior
from src.simulation.stack.stack_func import StackFunc
from src.simulation.variable.performance import NetworkPerformance
from src.simulation.variable.virtual_store import VirtualStore
from src.tools.calculation import PhysicalLayerModel
from src.tools.calculation import LinkPhysicalState
from configuration import simulation_config as cg


class SatellitePassiveBehavior(AbstractBehavior):
    @staticmethod
    async def stack_processing(entity, data):
        cross_layer_message = StackFunc.stack_processing(entity=entity, cross_layer_message=data)
        if cross_layer_message:
            entity_position_3d = entity.get_position()
            # Calculate metrics and add a path for drawing
            cross_layer_message.data_others["path"].append(entity_position_3d)
            link_state = _get_link_state(entity=entity, cross_layer_message=cross_layer_message)
            if link_state is not None:
                if not link_state.is_available:
                    NetworkPerformance.packet_loss(
                        data_size_byte=cross_layer_message.data_others["data_size_byte"],
                        reason="physical layer " + link_state.reason,
                    )
                    return
                cross_layer_message.data_others["delay"] += link_state.total_link_delay_ms
                cross_layer_message.data_others["last_link_physical_state"] = PhysicalLayerModel.state_to_dict(link_state)

            target_mac = cross_layer_message.data_others["target_mac"]
            to_buffer = entity.mac_table[target_mac]
            if to_buffer is None:
                print(target_mac, entity.mac_table)
            await to_buffer["Default"].put(cross_layer_message)
        return


def _get_link_state(entity, cross_layer_message) -> LinkPhysicalState or None:
    path = cross_layer_message.data_others.get("path")
    if path is None or len(path) < 2:
        return None

    ip_list = cross_layer_message.data_others.get("ip_list")
    source_ip = ip_list[-2] if ip_list is not None and len(ip_list) >= 2 else "unknown"
    source_category = _get_category_from_ip(source_ip)
    current_time = entity.current_time[0] if hasattr(entity, "current_time") else 0.0
    return PhysicalLayerModel.get_link_state(
        source_position_3d=path[-2],
        target_position_3d=path[-1],
        data_size_byte=cross_layer_message.data_others["data_size_byte"],
        source_id=source_ip,
        target_id=entity.ip_address,
        source_category=source_category,
        target_category="satellite",
        current_time=current_time,
        processing_time_ms=cg.PROCESSING_TIME,
    )


def _get_category_from_ip(ip_address):
    if VirtualStore.set_satellite_ip is not None and ip_address in VirtualStore.set_satellite_ip:
        return "satellite"
    if VirtualStore.set_user_ip is not None and ip_address in VirtualStore.set_user_ip:
        return "user"
    return "ground"
