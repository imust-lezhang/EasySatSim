from configuration import simulation_config as cg
from cases.case3.experiment.routing.centralized_control import GroundNetworkControlCenter
from src.simulation.stack.protocol_func.network_func import MinHopRouting


class CentralizedPeriodicRouting:
    controller = None

    @staticmethod
    def reset_controller():
        CentralizedPeriodicRouting.controller = GroundNetworkControlCenter(
            refresh_interval=cg.CASE3_CENTRALIZED_ROUTE_REFRESH_INTERVAL
        )

    @staticmethod
    def routing_algorithm(entity, cross_layer_message, src_satellite_id, dst_satellite_id):
        if CentralizedPeriodicRouting.controller is None:
            CentralizedPeriodicRouting.reset_controller()
        current_time = float(entity.current_time[0])
        next_satellite_id = CentralizedPeriodicRouting.controller.get_next_hop(
            current_time=current_time,
            src_satellite_id=src_satellite_id,
            dst_satellite_id=dst_satellite_id,
        )
        if next_satellite_id is None:
            return MinHopRouting.routing_algorithm(
                entity=entity,
                cross_layer_message=cross_layer_message,
                src_satellite_id=src_satellite_id,
                dst_satellite_id=dst_satellite_id,
            )
        return next_satellite_id
