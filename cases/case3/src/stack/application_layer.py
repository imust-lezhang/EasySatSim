from src.abstract.stack.protocol_func import AbstractProtocolFunc
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage, ActionType
from src.simulation.stack.protocol_data.application_data import DataMessage
from src.simulation.variable.performance import NetworkPerformance
from src.simulation.variable.virtual_store import VirtualStore
from cases.case3.experiment.integration.event_logger import append_event
from configuration import simulation_config as cg


class Case3ControlledTrafficPort(AbstractProtocolFunc):
    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage):
        data_message: DataMessage = cross_layer_message.data
        message_info = _parse_case3_message(data_message.message)
        path = cross_layer_message.data_others.get("path") or []
        hop_count = max(len(path) - 2, 0)
        NetworkPerformance.packet_arrive(
            data_size_byte=cross_layer_message.data_others["data_size_byte"],
            total_delay=cross_layer_message.data_others["delay"],
            hop_count=hop_count,
        )
        append_event(
            path=cg.CASE3_EVENT_LOG_FILE_PATH,
            event_type="arrival",
            simulation_time=float(entity.current_time[0]),
            message_id=message_info.get("message_id", ""),
            pair_id=message_info.get("pair_id", ""),
            direction=message_info.get("direction", ""),
            source_user_id=message_info.get("source_user_id", ""),
            target_user_id=entity.entity_id,
            target_access_satellite_id=entity.access_satellite,
            delay_ms=cross_layer_message.data_others["delay"],
            hop_count=hop_count,
            path_length=len(path),
            path_satellite_ids=_satellite_path_from_ip_list(
                cross_layer_message.data_others.get("ip_list")
            ),
        )
        cross_layer_message.action = ActionType.STOP
        return cross_layer_message

    @staticmethod
    def encapsulate_func(entity, cross_layer_message: CrossLayerMessage):
        cross_layer_message.action = ActionType.ENCAPSULATE
        cross_layer_message.cross_layer_interface = 0x0006
        return cross_layer_message


def _parse_case3_message(message):
    parts = message.split("|")
    if len(parts) < 6 or parts[0] != "case3":
        return {}
    return {
        "message_id": parts[1],
        "pair_id": parts[2],
        "direction": parts[3],
        "source_user_id": parts[4],
        "target_user_id": parts[5],
    }


def _satellite_path_from_ip_list(ip_list):
    if ip_list is None:
        return ""
    satellite_ids = []
    for ip_address in ip_list:
        satellite_id = VirtualStore.satellite_ip_to_id_table.get(ip_address)
        if satellite_id is not None:
            satellite_ids.append(str(satellite_id))
    return " ".join(satellite_ids)
