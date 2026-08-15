from configuration import simulation_config as cg
from src.tools.config_loader import load_configuration


if not hasattr(cg, "LEARNING_ARCHITECTURE"):
    cg = load_configuration("cases/case2/src")


CASE2_SCENE_CONFIGURED_FLAG = "_case2_scene_configured"
CASE2_SCENE_SUMMARY_ATTR = "_case2_scene_summary"


def configure_case2_scene(scene_controller, learning_architecture=None):
    if getattr(scene_controller, CASE2_SCENE_CONFIGURED_FLAG, False):
        return getattr(scene_controller, CASE2_SCENE_SUMMARY_ATTR)

    entity_manager = scene_controller.get_entity_manager()
    behavior_manager = scene_controller.get_behavior_manager()
    stack_manager = scene_controller.get_stack_manager()
    active_learning_architecture = normalize_learning_architecture(
        learning_architecture or cg.LEARNING_ARCHITECTURE
    )
    users = entity_manager.get_entity(entity_category="user")
    satellites = entity_manager.get_entity(entity_category="satellite")
    case_details = {}

    if active_learning_architecture == "cl":
        case_details = configure_case2_cl_scene(
            entity_manager=entity_manager,
            behavior_manager=behavior_manager,
            stack_manager=stack_manager,
            users=users,
        )
    elif active_learning_architecture == "fl":
        case_details = configure_case2_fl_scene(
            entity_manager=entity_manager,
            behavior_manager=behavior_manager,
            stack_manager=stack_manager,
            users=users,
        )

    summary = build_case2_summary(
        learning_architecture=active_learning_architecture,
        users=users,
        satellites=satellites,
        case_details=case_details,
    )
    setattr(scene_controller, CASE2_SCENE_CONFIGURED_FLAG, True)
    setattr(scene_controller, CASE2_SCENE_SUMMARY_ATTR, summary)
    print_case2_summary(summary=summary)
    return summary


def configure_scene(scene_controller):
    return configure_case2_scene(scene_controller=scene_controller)


def configure_case2_cl_scene(entity_manager, behavior_manager,
                             stack_manager, users):
    from cases.case2.experiment.data.cifar10_data import load_case2_cifar10
    from cases.case2.experiment.integration.case2_event_logger import (
        reset_case2_event_logs,
    )
    from cases.case2.experiment.integration.cl_center_server import (
        ClCenterServer,
    )
    from cases.case2.src.behaviors.cl_server_behavior import ClServerBehavior
    from cases.case2.src.behaviors.cl_user_behavior import ClUserBehavior
    from cases.case2.src.stack.cl_application import register_cl_application

    datasets = load_case2_cifar10(download=cg.CIFAR10_DOWNLOAD)
    if cg.CASE2_RESET_EVENT_LOGS:
        reset_case2_event_logs(
            cg.LEARNING_METRICS_FILE_PATH,
            cg.COMMUNICATION_EVENTS_FILE_PATH,
        )

    register_cl_application(stack_manager=stack_manager)
    register_case2_cl_behaviors(
        behavior_manager=behavior_manager,
        datasets=datasets,
        cl_user_behavior=ClUserBehavior,
        cl_server_behavior=ClServerBehavior,
    )
    bind_case2_cl_user_behaviors(
        entity_manager=entity_manager,
        behavior_manager=behavior_manager,
        users=users,
    )
    center_server = ClCenterServer(
        entity_category="server",
        entity_id=cg.USER_NUMBER,
        latitude=cg.SERVER_LATITUDE,
        longtitude=cg.SERVER_LONGITUDE,
        ip_address=cg.SERVER_IP_ADDRESS,
        test_dataset=datasets.test_dataset,
    )
    entity_manager.add_entity(
        entity_category="server",
        entity_list=[center_server],
    )
    bind_case2_cl_server_behaviors(
        entity_manager=entity_manager,
        behavior_manager=behavior_manager,
        center_server=center_server,
    )
    return {
        "train_dataset_size": len(datasets.train_dataset),
        "test_dataset_size": len(datasets.test_dataset),
        "cifar10_data_root": str(datasets.data_root),
        "cl_train_trigger_sample_count": cg.CL_TRAIN_TRIGGER_SAMPLE_COUNT,
        "cl_sample_send_interval": cg.CL_SAMPLE_SEND_INTERVAL,
        "cl_samples_per_message": cg.CL_SAMPLES_PER_MESSAGE,
    }


def configure_case2_fl_scene(entity_manager, behavior_manager,
                             stack_manager, users):
    from cases.case2.experiment.data.cifar10_data import load_case2_cifar10
    from cases.case2.experiment.data.user_data_partition import (
        build_case2_user_partitions,
        summarize_partitions,
    )
    from cases.case2.experiment.integration.case2_event_logger import (
        reset_case2_event_logs,
    )
    from cases.case2.experiment.integration.fl_center_server import (
        FlCenterServer,
    )
    from cases.case2.src.behaviors.fl_server_behavior import FlServerBehavior
    from cases.case2.src.behaviors.fl_user_behavior import FlUserBehavior
    from cases.case2.src.stack.fl_application import register_fl_application

    datasets = load_case2_cifar10(download=cg.CIFAR10_DOWNLOAD)
    user_partitions = build_case2_user_partitions(dataset=datasets.train_dataset)
    partition_summary = summarize_partitions(user_partitions=user_partitions)
    if cg.CASE2_RESET_EVENT_LOGS:
        reset_case2_event_logs(
            cg.LEARNING_METRICS_FILE_PATH,
            cg.COMMUNICATION_EVENTS_FILE_PATH,
        )

    register_fl_application(stack_manager=stack_manager)
    register_case2_fl_behaviors(
        behavior_manager=behavior_manager,
        datasets=datasets,
        user_partitions=user_partitions,
        fl_user_behavior=FlUserBehavior,
        fl_server_behavior=FlServerBehavior,
    )
    bind_case2_fl_user_behaviors(
        entity_manager=entity_manager,
        behavior_manager=behavior_manager,
        users=users,
    )
    center_server = FlCenterServer(
        entity_category="server",
        entity_id=cg.USER_NUMBER,
        latitude=cg.SERVER_LATITUDE,
        longtitude=cg.SERVER_LONGITUDE,
        ip_address=cg.SERVER_IP_ADDRESS,
        test_dataset=datasets.test_dataset,
    )
    entity_manager.add_entity(
        entity_category="server",
        entity_list=[center_server],
    )
    bind_case2_fl_server_behaviors(
        entity_manager=entity_manager,
        behavior_manager=behavior_manager,
        center_server=center_server,
    )
    return {
        "train_dataset_size": len(datasets.train_dataset),
        "test_dataset_size": len(datasets.test_dataset),
        "cifar10_data_root": str(datasets.data_root),
        "fl_partition_mode": user_partitions.mode,
        "fl_clients_per_round": cg.FL_CLIENTS_PER_ROUND,
        "fl_updates_per_round": cg.FL_UPDATES_PER_ROUND,
        "fl_local_sample_count": cg.FL_LOCAL_SAMPLE_COUNT,
        "fl_first_user_primary_classes": (
            partition_summary["first_user_primary_classes"]
        ),
    }


def register_case2_cl_behaviors(behavior_manager, datasets,
                                cl_user_behavior, cl_server_behavior):
    behavior_manager.add_active_behavior(
        behavior_name="case2_cl_send_training_samples",
        behavior_func=cl_user_behavior.send_training_samples,
        interval=cg.CL_SAMPLE_SEND_INTERVAL,
        is_async=True,
        data={
            "train_dataset": datasets.train_dataset,
            "train_indices": datasets.train_indices,
            "classes": datasets.classes,
            "server_ip_address": cg.SERVER_IP_ADDRESS,
            "samples_per_message": cg.CL_SAMPLES_PER_MESSAGE,
        },
        last_run=None,
    )
    behavior_manager.add_active_behavior(
        behavior_name="case2_cl_server_access_satellite",
        behavior_func=cl_server_behavior.access_satellite,
        interval=0.3,
        is_async=True,
        data=None,
        last_run=None,
    )
    behavior_manager.add_active_behavior(
        behavior_name="case2_cl_train_model",
        behavior_func=cl_server_behavior.train_model,
        interval=1,
        is_async=False,
        data={
            "trigger_sample_count": cg.CL_TRAIN_TRIGGER_SAMPLE_COUNT,
        },
        last_run=None,
    )
    return


def register_case2_fl_behaviors(behavior_manager, datasets, user_partitions,
                                fl_user_behavior, fl_server_behavior):
    behavior_manager.add_active_behavior(
        behavior_name="case2_fl_train_local_model",
        behavior_func=fl_user_behavior.train_local_model,
        interval=cg.FL_LOCAL_TRAIN_INTERVAL,
        is_async=False,
        data={
            "train_dataset": datasets.train_dataset,
            "user_partition_indices": user_partitions.as_index_lists(),
        },
        last_run=None,
    )
    behavior_manager.add_active_behavior(
        behavior_name="case2_fl_send_model_update",
        behavior_func=fl_user_behavior.send_model_update,
        interval=cg.FL_MODEL_UPLOAD_INTERVAL,
        is_async=True,
        data={
            "server_ip_address": cg.SERVER_IP_ADDRESS,
        },
        last_run=None,
    )
    behavior_manager.add_active_behavior(
        behavior_name="case2_fl_server_access_satellite",
        behavior_func=fl_server_behavior.access_satellite,
        interval=0.3,
        is_async=True,
        data=None,
        last_run=None,
    )
    behavior_manager.add_active_behavior(
        behavior_name="case2_fl_manage_round",
        behavior_func=fl_server_behavior.manage_round,
        interval=cg.FL_SERVER_ROUND_INTERVAL,
        is_async=True,
        data=None,
        last_run=None,
    )
    return


def bind_case2_cl_user_behaviors(entity_manager, behavior_manager, users):
    for user in users:
        if cg.CL_CLEAR_DEFAULT_USER_TRAFFIC:
            user.clear_behaviors()
        bind_active_behavior_once(
            entity_manager=entity_manager,
            behavior_manager=behavior_manager,
            entity=user,
            behavior_name="simple_access_satellite",
        )
        bind_active_behavior_once(
            entity_manager=entity_manager,
            behavior_manager=behavior_manager,
            entity=user,
            behavior_name="case2_cl_send_training_samples",
        )
        bind_passive_behavior_once(
            entity_manager=entity_manager,
            behavior_manager=behavior_manager,
            entity=user,
            behavior_name="user_stack_processing",
        )
    return


def bind_case2_fl_user_behaviors(entity_manager, behavior_manager, users):
    for user in users:
        if cg.FL_CLEAR_DEFAULT_USER_TRAFFIC:
            user.clear_behaviors()
        bind_active_behavior_once(
            entity_manager=entity_manager,
            behavior_manager=behavior_manager,
            entity=user,
            behavior_name="simple_access_satellite",
        )
        bind_active_behavior_once(
            entity_manager=entity_manager,
            behavior_manager=behavior_manager,
            entity=user,
            behavior_name="case2_fl_train_local_model",
        )
        bind_active_behavior_once(
            entity_manager=entity_manager,
            behavior_manager=behavior_manager,
            entity=user,
            behavior_name="case2_fl_send_model_update",
        )
        bind_passive_behavior_once(
            entity_manager=entity_manager,
            behavior_manager=behavior_manager,
            entity=user,
            behavior_name="user_stack_processing",
        )
    return


def bind_case2_cl_server_behaviors(entity_manager, behavior_manager,
                                   center_server):
    bind_active_behavior_once(
        entity_manager=entity_manager,
        behavior_manager=behavior_manager,
        entity=center_server,
        behavior_name="case2_cl_server_access_satellite",
    )
    bind_active_behavior_once(
        entity_manager=entity_manager,
        behavior_manager=behavior_manager,
        entity=center_server,
        behavior_name="case2_cl_train_model",
    )
    bind_passive_behavior_once(
        entity_manager=entity_manager,
        behavior_manager=behavior_manager,
        entity=center_server,
        behavior_name="user_stack_processing",
    )
    return


def bind_case2_fl_server_behaviors(entity_manager, behavior_manager,
                                   center_server):
    bind_active_behavior_once(
        entity_manager=entity_manager,
        behavior_manager=behavior_manager,
        entity=center_server,
        behavior_name="case2_fl_server_access_satellite",
    )
    bind_active_behavior_once(
        entity_manager=entity_manager,
        behavior_manager=behavior_manager,
        entity=center_server,
        behavior_name="case2_fl_manage_round",
    )
    bind_passive_behavior_once(
        entity_manager=entity_manager,
        behavior_manager=behavior_manager,
        entity=center_server,
        behavior_name="user_stack_processing",
    )
    return


def bind_active_behavior_once(entity_manager, behavior_manager,
                              entity, behavior_name):
    if behavior_name in entity.get_active_behaviors():
        return
    entity_manager.bind_active_behavior(
        behavior_manager=behavior_manager,
        entity=entity,
        behavior_name=behavior_name,
    )
    return


def bind_passive_behavior_once(entity_manager, behavior_manager,
                               entity, behavior_name):
    if behavior_name in entity.get_passive_behaviors():
        return
    entity_manager.bind_passive_behavior(
        behavior_manager=behavior_manager,
        entity=entity,
        behavior_name=behavior_name,
    )
    return


def normalize_learning_architecture(value):
    normalized_value = str(value).strip().lower().replace("-", "_")
    if normalized_value in ("cl", "centralized", "centralized_learning"):
        return "cl"
    if normalized_value in ("fl", "federated", "federated_learning"):
        return "fl"
    raise ValueError(
        "LEARNING_ARCHITECTURE must be 'cl' or 'fl', "
        f"but got {value!r}."
    )


def build_case2_summary(learning_architecture, users, satellites,
                        case_details=None):
    summary = {
        "learning_architecture": learning_architecture,
        "user_number": len(users),
        "satellite_number": len(satellites),
        "orbit_number": cg.ORBIT_NUMBER,
        "satellite_number_per_orbit": cg.SATELLITE_NUMBER_PRE_ORBIT,
        "orbit_inclination": cg.ORBIT_INCLINATION,
        "orbit_height": cg.ORBIT_HEIGHT,
        "running_time": cg.CASE_SIMULATION_END_TIME,
        "server_ip_address": cg.SERVER_IP_ADDRESS,
        "server_latitude": cg.SERVER_LATITUDE,
        "server_longitude": cg.SERVER_LONGITUDE,
        "application_port": cg.CASE2_APPLICATION_PORT,
        "network_output_file": cg.SAVE_FILE_PATH,
        "learning_metrics_file": cg.LEARNING_METRICS_FILE_PATH,
        "communication_events_file": cg.COMMUNICATION_EVENTS_FILE_PATH,
    }
    if case_details:
        summary.update(case_details)
    return summary


def print_case2_summary(summary):
    message = (
        "[Case2 setup] "
        f"mode={summary['learning_architecture']}, "
        f"users={summary['user_number']}, "
        f"satellites={summary['satellite_number']}, "
        f"constellation={summary['orbit_number']}x"
        f"{summary['satellite_number_per_orbit']}, "
        f"inclination={summary['orbit_inclination']}deg, "
        f"altitude={summary['orbit_height']}km, "
        f"running_time={summary['running_time']}s, "
        f"server={summary['server_ip_address']}:"
        f"{summary['application_port']}"
    )
    if summary["learning_architecture"] == "cl":
        message += (
            f", train_samples={summary['train_dataset_size']}, "
            f"test_samples={summary['test_dataset_size']}, "
            f"trigger={summary['cl_train_trigger_sample_count']}"
        )
    elif summary["learning_architecture"] == "fl":
        message += (
            f", train_samples={summary['train_dataset_size']}, "
            f"test_samples={summary['test_dataset_size']}, "
            f"partition={summary['fl_partition_mode']}, "
            f"clients_per_round={summary['fl_clients_per_round']}, "
            f"updates_per_round={summary['fl_updates_per_round']}"
        )
    print(message)
    return
