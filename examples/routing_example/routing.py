from src.abstract.stack.routing import RoutingAlgorithm

class CustomRoutingAlgorithm(RoutingAlgorithm):
    @staticmethod
    def routing_algorithm(entity, cross_layer_message, src_satellite_id, dst_satellite_id):
        """
        In this example, we simply choose the first satellite from the routing table as the next hop.
        A real routing algorithm may need to consider more factors, such as link status, transmission cost, congestion, etc., to achieve more efficient data transmission.
        """
        # Check if the routing table is empty
        if not entity.routing_table:
            raise ValueError("The routing table is empty, unable to make a routing decision.")

        next_satellite_id = entity.routing_table[0]
        return next_satellite_id

        # Note: A real routing algorithm may need to consider more factors, such as link status, transmission cost, congestion, etc., to achieve more efficient data transmission.
