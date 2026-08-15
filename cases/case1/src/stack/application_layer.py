from collections import deque

from src.abstract.stack.protocol_func import AbstractProtocolFunc
from src.simulation.stack.cross_layer_message.cross_layer_message import ActionType
from src.simulation.stack.cross_layer_message.cross_layer_message import CrossLayerMessage
from src.simulation.stack.protocol_data.application_data import DataMessage
from src.simulation.variable.performance import NetworkPerformance
from cases.case1.experiment.integration.ids_event_log import record_ids_event


PORT22_PROTOCOL_NAME = 22
GROUND_TRUTH_MALICIOUS = "malicious"
GROUND_TRUTH_BENIGN = "benign"


class Port22IntrusionService(AbstractProtocolFunc):
    @staticmethod
    def parse_and_process_func(entity, cross_layer_message: CrossLayerMessage):
        data_message: DataMessage = cross_layer_message.data
        shell_code = data_message.message
        context = build_intrusion_context(entity=entity, cross_layer_message=cross_layer_message)
        ids_engine = get_satellite_ids_engine(entity=entity)
        ids_result = ids_engine.inspect(payload=shell_code, context=context)
        action = apply_intrusion_result(entity=entity,
                                        ids_result=ids_result,
                                        ground_truth=context["ground_truth"])
        event_log_path = cross_layer_message.data_others.get("ids_event_log_path")
        ids_event = record_ids_event(context=context,
                                     ids_result=ids_result,
                                     action=action,
                                     event_log_path=event_log_path)

        update_port22_network_metrics(entity=entity, cross_layer_message=cross_layer_message)
        cross_layer_message.data_others["case1_port22_context"] = context
        cross_layer_message.data_others["case1_port22_ids_result"] = ids_result
        cross_layer_message.data_others["case1_port22_action"] = action
        cross_layer_message.data_others["case1_ids_event"] = ids_event
        cross_layer_message.action = ActionType.STOP
        return cross_layer_message

    @staticmethod
    def encapsulate_func(entity, cross_layer_message: CrossLayerMessage):
        cross_layer_message.action = ActionType.ENCAPSULATE
        cross_layer_message.cross_layer_interface = 0x0006
        return cross_layer_message


def register_port22_application(stack_manager):
    stack_manager.add_protocol_func(layer_name="application",
                                    protocol_name=PORT22_PROTOCOL_NAME,
                                    parse_func=Port22IntrusionService.parse_and_process_func,
                                    encapsulate_func=Port22IntrusionService.encapsulate_func)
    stack_manager.add_relationship(layer_name="application",
                                   protocol_name=PORT22_PROTOCOL_NAME,
                                   data_name="data_message")
    print("[Case1 port22] Port 22 intrusion service registered.")
    return


def build_intrusion_context(entity, cross_layer_message):
    data_others = cross_layer_message.data_others
    ip_list = data_others.get("ip_list")
    source_ip = get_source_ip(ip_list)
    current_time = get_current_time(entity)

    return {
        "time": current_time,
        "satellite_id": entity.entity_id,
        "source_ip": source_ip,
        "target_ip": entity.ip_address,
        "target_port": PORT22_PROTOCOL_NAME,
        "ground_truth": data_others.get("ground_truth", GROUND_TRUTH_MALICIOUS),
    }


def get_satellite_ids_engine(entity):
    if not hasattr(entity, "ids_engine"):
        raise AttributeError(
            "Satellite IDS engine is not installed. "
            "Run install_satellite_ids(satellites, ids_mode) before starting the case simulation."
        )
    return entity.ids_engine


def apply_intrusion_result(entity, ids_result, ground_truth):
    detected = bool(ids_result["detected"])

    if ground_truth == GROUND_TRUTH_MALICIOUS:
        if detected:
            return "malicious_blocked"
        entity.disconnect_user()
        return "malicious_executed"

    if detected:
        return "benign_blocked"
    return "benign_allowed"


def update_port22_network_metrics(entity, cross_layer_message):
    data_others = cross_layer_message.data_others
    path = data_others.get("path", deque())
    hop_count = max(len(path) - 2, 0)
    NetworkPerformance.packet_arrive(data_size_byte=data_others["data_size_byte"],
                                     total_delay=data_others["delay"],
                                     hop_count=hop_count)
    if entity.entity_id == 0 and hasattr(entity, "set_routing_path"):
        entity.set_routing_path(path_list=path)
    return


def get_source_ip(ip_list):
    if ip_list is None or len(ip_list) == 0:
        return None
    return ip_list[0]


def get_current_time(entity):
    if hasattr(entity, "current_time"):
        return float(entity.current_time[0])
    return 0.0
