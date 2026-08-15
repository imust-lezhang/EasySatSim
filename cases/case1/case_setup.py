from configuration import simulation_config as cg
from src.tools.config_loader import load_configuration


if not hasattr(cg, "CASE_MALICIOUS_USER_NUMBER"):
    cg = load_configuration("cases/case1/src")


from cases.case1.src.behaviors.malicious_user_behavior import bind_malicious_user_behavior
from cases.case1.src.behaviors.malicious_user_behavior import register_malicious_user_behavior
from cases.case1.src.behaviors.normal_port22_behavior import bind_normal_port22_behavior
from cases.case1.src.behaviors.normal_port22_behavior import register_normal_port22_behavior
from cases.case1.experiment.data.user_locations import locations_malicious_users
from cases.case1.experiment.data.user_locations import locations_normal_users
from cases.case1.experiment.integration.ids_event_log import reset_ids_event_log
from cases.case1.experiment.integration.satellite_ids_engine import install_satellite_ids
from cases.case1.experiment.integration.satellite_ids_engine import normalize_ids_mode
from cases.case1.src.stack.application_layer import register_port22_application


CASE1_SCENE_CONFIGURED_FLAG = "_case1_scene_configured"
CASE1_SCENE_SUMMARY_ATTR = "_case1_scene_summary"


def configure_case1_scene(scene_controller, ids_mode=None, reset_event_log=True):
    if getattr(scene_controller, CASE1_SCENE_CONFIGURED_FLAG, False):
        return getattr(scene_controller, CASE1_SCENE_SUMMARY_ATTR)

    entity_manager = scene_controller.get_entity_manager()
    behavior_manager = scene_controller.get_behavior_manager()
    stack_manager = scene_controller.get_stack_manager()

    users = entity_manager.get_entity(entity_category="user")
    satellites = entity_manager.get_entity(entity_category="satellite")
    active_ids_mode = normalize_ids_mode(ids_mode or cg.IDS_MODE)

    assign_case1_user_locations(users=users)
    register_malicious_user_behavior(behavior_manager=behavior_manager)
    register_normal_port22_behavior(behavior_manager=behavior_manager)
    malicious_users = get_case1_malicious_users(users=users)
    normal_users = get_case1_normal_users(users=users)
    bind_malicious_user_behavior(entity_manager=entity_manager,
                                 behavior_manager=behavior_manager,
                                 malicious_users=malicious_users)
    bind_normal_port22_behavior(entity_manager=entity_manager,
                                behavior_manager=behavior_manager,
                                normal_users=normal_users)
    install_satellite_ids(satellites=satellites, ids_mode=active_ids_mode)
    register_port22_application(stack_manager=stack_manager)
    if reset_event_log:
        reset_ids_event_log(ids_mode=active_ids_mode)

    summary = build_case1_summary(ids_mode=active_ids_mode,
                                  users=users,
                                  satellites=satellites)
    setattr(scene_controller, CASE1_SCENE_CONFIGURED_FLAG, True)
    setattr(scene_controller, CASE1_SCENE_SUMMARY_ATTR, summary)
    print_case1_summary(summary=summary)
    return summary


def configure_scene(scene_controller):
    return configure_case1_scene(scene_controller=scene_controller)


def assign_case1_user_locations(users):
    malicious_count = cg.CASE_MALICIOUS_USER_NUMBER
    all_locations = list(locations_malicious_users) + list(locations_normal_users)

    if len(locations_malicious_users) != malicious_count:
        raise ValueError(
            f"CASE_MALICIOUS_USER_NUMBER is {malicious_count}, but "
            f"{len(locations_malicious_users)} malicious user locations were provided."
        )
    if cg.USER_NUMBER != len(all_locations):
        raise ValueError(
            f"USER_NUMBER is {cg.USER_NUMBER}, but {len(all_locations)} user locations were provided."
        )
    if len(users) != len(all_locations):
        raise ValueError(
            f"The scene contains {len(users)} users, but {len(all_locations)} user locations were provided."
        )

    for i, malicious_user in enumerate(users[:malicious_count]):
        latitude, longitude = locations_malicious_users[i]
        malicious_user.set_position(latitude, longitude)

    for i, normal_user in enumerate(users[malicious_count:]):
        latitude, longitude = locations_normal_users[i]
        normal_user.set_position(latitude, longitude)
    return


def get_case1_malicious_users(users):
    return users[:cg.CASE_MALICIOUS_USER_NUMBER]


def get_case1_normal_users(users):
    return users[cg.CASE_MALICIOUS_USER_NUMBER:]


def build_case1_summary(ids_mode, users, satellites):
    return {
        "ids_mode": ids_mode,
        "user_number": len(users),
        "malicious_user_number": cg.CASE_MALICIOUS_USER_NUMBER,
        "normal_user_number": len(users) - cg.CASE_MALICIOUS_USER_NUMBER,
        "satellite_number": len(satellites),
        "attack_start_time": cg.CASE_ATTACK_START_TIME,
        "attack_end_time": cg.CASE_ATTACK_END_TIME,
        "attack_probability": cg.CASE_ATTACK_PROBABILITY,
        "malicious_behavior_interval": cg.CASE_MALICIOUS_BEHAVIOR_INTERVAL,
        "normal_port22_enabled": cg.CASE_ENABLE_NORMAL_PORT22_TRAFFIC,
        "normal_port22_start_time": cg.CASE_NORMAL_PORT22_START_TIME,
        "normal_port22_end_time": cg.CASE_NORMAL_PORT22_END_TIME,
        "normal_port22_probability": cg.CASE_NORMAL_PORT22_PROBABILITY,
        "normal_port22_behavior_interval": cg.CASE_NORMAL_PORT22_BEHAVIOR_INTERVAL,
    }


def print_case1_summary(summary):
    print(
        "[Case1 setup] "
        f"users={summary['user_number']} "
        f"(malicious={summary['malicious_user_number']}, normal={summary['normal_user_number']}), "
        f"satellites={summary['satellite_number']}, ids={summary['ids_mode']}, "
        f"attack_window={summary['attack_start_time']}-{summary['attack_end_time']}s, "
        f"benign22={summary['normal_port22_enabled']}"
    )
    return
