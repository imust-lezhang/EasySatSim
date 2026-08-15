from vispy.scene import visuals

class SatelliteGroundConnectPlotter:
    def __init__(self,scale_factor , color, width):
        self.satellite_ground_connect = visuals.Line()
        self.color = color
        self.width = width
        self.scale_factor = scale_factor

    def create_connect(self, view):
        view.add(self.satellite_ground_connect)

    def update_connect(self, position_pair_3d):
        self.satellite_ground_connect.set_data(position_pair_3d * self.scale_factor, color=self.color
                                               , width=self.width, connect='segments')
