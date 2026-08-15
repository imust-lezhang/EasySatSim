from vispy.scene import visuals


class RoutingPathPlotter:
    def __init__(self,scale_factor , color, width):
        self.routing_path_line = visuals.Line()
        self.color = color
        self.width = width
        self.scale_factor = scale_factor

    def create_path(self, view):
        view.add(self.routing_path_line)

    def update_routing_path(self, position_3d):
        self.routing_path_line.set_data(position_3d * self.scale_factor, color=self.color
                                               , width=self.width, connect='strip')