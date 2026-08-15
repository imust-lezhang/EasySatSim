from cases.case3.experiment.data.centralized_route_tables import (
    load_centralized_route_tables,
    table_name_for_deployment,
)


class GroundNetworkControlCenter:
    def __init__(self, refresh_interval):
        self.refresh_interval = float(refresh_interval)
        self.route_version = 0
        self.next_refresh_time = 0.0
        self.deployment_index = -1
        self.deployed_table_name = None
        self.route_tables = load_centralized_route_tables()
        self.deployed_next_hop_table = None

    def get_next_hop(self, current_time, src_satellite_id, dst_satellite_id):
        self.refresh_if_needed(current_time=current_time)
        next_hop_id = int(
            self.deployed_next_hop_table[src_satellite_id, dst_satellite_id]
        )
        return None if next_hop_id < 0 else next_hop_id

    def refresh_if_needed(self, current_time):
        while current_time >= self.next_refresh_time:
            self.deployment_index += 1
            self._deploy_table(self.deployment_index)
            self.next_refresh_time += self.refresh_interval

    def _deploy_table(self, deployment_index):
        table_name = table_name_for_deployment(deployment_index)
        self.deployed_table_name = table_name
        self.deployed_next_hop_table = self.route_tables[table_name]
        self.route_version += 1
