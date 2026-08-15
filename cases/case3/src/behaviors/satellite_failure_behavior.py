from configuration import simulation_config as cg
from cases.case3.experiment.integration.event_logger import append_event
from src.abstract.behavior.behavior import AbstractBehavior
from src.simulation.variable.virtual_store import VirtualStore


class SatelliteFailureBehavior(AbstractBehavior):
    @staticmethod
    async def fail_target_satellite_once(entity, data):
        target_satellite = data
        state = getattr(entity, "_case3_failure_controller_state", None)
        if state is None:
            state = {"has_failed": False}
            entity._case3_failure_controller_state = state
        if state["has_failed"]:
            return
        if not target_satellite.is_survival:
            state["has_failed"] = True
            return
        if not VirtualStore.satellite_survival_state.get(target_satellite.entity_id, True):
            state["has_failed"] = True
            return

        current_time = float(entity.current_time[0])
        if current_time < cg.CASE3_FAILURE_TIME:
            return

        target_satellite.set_dead()
        state["has_failed"] = True
        append_event(
            path=cg.CASE3_EVENT_LOG_FILE_PATH,
            event_type="satellite_failure",
            simulation_time=current_time,
            note=(
                f"satellite {target_satellite.entity_id} set_dead at "
                f"configured failure time {cg.CASE3_FAILURE_TIME}"
            ),
        )
