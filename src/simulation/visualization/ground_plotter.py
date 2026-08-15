from vispy.scene import visuals


class GroundPlotter:
    def __init__(self, scale_factor, color, size):
        self.user_scatter = visuals.Markers()
        self.scale_factor = scale_factor
        self.color = color
        self.size = size

    def create_users(self, view, position_3d):
        self.user_scatter.set_data(position_3d * self.scale_factor, edge_color=self.color, face_color=self.color, size=self.size)
        view.add(self.user_scatter)

