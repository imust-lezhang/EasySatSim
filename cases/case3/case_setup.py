from configuration import simulation_config as cg
from cases.case3.src.behaviors.controlled_pair_traffic import ControlledPairTraffic
from cases.case3.src.behaviors.satellite_failure_behavior import SatelliteFailureBehavior
from cases.case3.experiment.data.user_groups import build_case3_user_locations
from cases.case3.experiment.routing.centralized_routing import CentralizedPeriodicRouting
from cases.case3.experiment.routing.distributed_rerouting import DistributedLocalRerouting
from cases.case3.src.stack.application_layer import Case3ControlledTrafficPort
from cases.case3.src.stack.network_layer import Case3CentralizedNetworkLayer
from cases.case3.experiment.integration.event_logger import prepare_event_log
from src.abstract.manager.entity_manager import AbstractEntityManager


CASE3_TRAFFIC_BEHAVIOR_NAME = "case3_controlled_pair_send"
CASE3_FAILURE_BEHAVIOR_NAME = "case3_satellite_failure_once"


def configure_case3_scene(scene_controller):
    _prepare_case3_output_files()
    _set_fixed_user_locations(scene_controller)
    _configure_case3_failure(scene_controller)
    _replace_default_random_traffic(scene_controller)
    _register_case3_application_port(scene_controller)
    _configure_case3_routing(scene_controller)
    print("[Case 3] Fixed users, paired traffic, failure, and routing configured.")


def _prepare_case3_output_files():
    event_log_path = prepare_event_log(cg.CASE3_EVENT_LOG_FILE_PATH)
    print(f"[Case 3] Event log: {event_log_path}")


def _set_fixed_user_locations(scene_controller):
    users = scene_controller.get_entity_manager().get_entity(entity_category="user")
    locations = build_case3_user_locations()
    if len(users) != len(locations):
        raise ValueError(
            f"Case 3 requires {len(locations)} users, but the scene has {len(users)} users."
        )
    for user, (latitude, longitude) in zip(users, locations):
        user.set_position(latitude=latitude, longtitude=longitude)
    print(f"[Case 3] Fixed user locations assigned: {len(locations)} users.")


def _replace_default_random_traffic(scene_controller):
    behavior_manager = scene_controller.get_behavior_manager()
    try:
        behavior_manager.add_active_behavior(
            behavior_name=CASE3_TRAFFIC_BEHAVIOR_NAME,
            behavior_func=ControlledPairTraffic.send_case3_pair_data,
            interval=cg.CASE3_CONTROLLED_BEHAVIOR_INTERVAL,
            is_async=True,
            data=None,
            last_run=None,
        )
    except KeyError:
        pass

    users = scene_controller.get_entity_manager().get_entity(entity_category="user")
    for user in users:
        user.get_active_behaviors().pop("simple_send_data", None)
        if CASE3_TRAFFIC_BEHAVIOR_NAME not in user.get_active_behaviors():
            AbstractEntityManager.bind_active_behavior(
                behavior_manager=behavior_manager,
                entity=user,
                behavior_name=CASE3_TRAFFIC_BEHAVIOR_NAME,
            )
    print("[Case 3] Default random user traffic replaced by controlled pair traffic.")


def _register_case3_application_port(scene_controller):
    stack_manager = scene_controller.get_stack_manager()
    try:
        stack_manager.add_protocol_func(
            layer_name="application",
            protocol_name=cg.CASE3_APPLICATION_PORT,
            parse_func=Case3ControlledTrafficPort.parse_and_process_func,
            encapsulate_func=Case3ControlledTrafficPort.encapsulate_func,
        )
    except KeyError:
        pass
    stack_manager.add_relationship(
        layer_name="application",
        protocol_name=cg.CASE3_APPLICATION_PORT,
        data_name="data_message",
    )
    print(f"[Case 3] Application port {cg.CASE3_APPLICATION_PORT} registered.")


def _configure_case3_routing(scene_controller):
    if cg.CASE3_ROUTING_MODE == "centralized":
        CentralizedPeriodicRouting.reset_controller()
        _register_case3_centralized_network_layer(scene_controller)
        scene_controller.register_routing_algorithm(CentralizedPeriodicRouting.routing_algorithm)
        print(
            "[Case 3] Routing mode: centralized periodic routing "
            f"(refresh interval={cg.CASE3_CENTRALIZED_ROUTE_REFRESH_INTERVAL}s)."
        )
        return

    if cg.CASE3_ROUTING_MODE == "distributed":
        scene_controller.register_routing_algorithm(DistributedLocalRerouting.routing_algorithm)
        print("[Case 3] Routing mode: distributed local rerouting.")
        return

    raise ValueError(f"Unsupported CASE3_ROUTING_MODE: {cg.CASE3_ROUTING_MODE}")


def _register_case3_centralized_network_layer(scene_controller):
    stack_manager = scene_controller.get_stack_manager()
    protocol_funcs = getattr(stack_manager, "__dict_protocol_func__")
    protocol_funcs["network"][0x0800] = {
        "parse": Case3CentralizedNetworkLayer.parse_and_process_func,
        "encapsulate": Case3CentralizedNetworkLayer.encapsulate_func,
    }
    stack_manager.add_relationship(
        layer_name="network",
        protocol_name=0x0800,
        data_name="data_packet",
    )


def _configure_case3_failure(scene_controller):
    satellites = scene_controller.get_entity_manager().get_entity(entity_category="satellite")
    if cg.CASE3_FAILED_SATELLITE_ID < 0 or cg.CASE3_FAILED_SATELLITE_ID >= len(satellites):
        raise ValueError(
            f"Invalid CASE3_FAILED_SATELLITE_ID: {cg.CASE3_FAILED_SATELLITE_ID}"
        )

    behavior_manager = scene_controller.get_behavior_manager()
    try:
        behavior_manager.add_active_behavior(
            behavior_name=CASE3_FAILURE_BEHAVIOR_NAME,
            behavior_func=SatelliteFailureBehavior.fail_target_satellite_once,
            interval=cg.CASE3_FAILURE_BEHAVIOR_INTERVAL,
            is_async=True,
            data=satellites[cg.CASE3_FAILED_SATELLITE_ID],
            last_run=None,
        )
    except KeyError:
        pass

    users = scene_controller.get_entity_manager().get_entity(entity_category="user")
    for user in users:
        if CASE3_FAILURE_BEHAVIOR_NAME not in user.get_active_behaviors():
            AbstractEntityManager.bind_active_behavior(
                behavior_manager=behavior_manager,
                entity=user,
                behavior_name=CASE3_FAILURE_BEHAVIOR_NAME,
            )
    print(
        "[Case 3] Satellite failure injection: "
        f"satellite={cg.CASE3_FAILED_SATELLITE_ID}, time={cg.CASE3_FAILURE_TIME}s."
    )
