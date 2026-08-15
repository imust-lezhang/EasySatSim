from vispy.scene import visuals
import numpy as np


class ConstellationPlotter:
    def __init__(self, scale_factor, color_survival, size_survival, color_failure, size_failure):
        self.survival_satellites_scatter = visuals.Markers()
        self.failure_satellites_scatter = visuals.Markers()
        self.orbits_lines = []  # Store multiple Line objects
        self.color_survival = color_survival
        self.size_survival = size_survival
        self.color_failure = color_failure
        self.size_failure = size_failure
        self.scale_factor = scale_factor


    def create_survival_satellites(self, view, position_3d):
        self.survival_satellites_scatter.set_data(position_3d * self.scale_factor, edge_color=self.color_survival, face_color=self.color_survival
                                         , size=self.size_survival)
        view.add(self.survival_satellites_scatter)


    def create_failure_satellites(self, view, position_3d):
        self.failure_satellites_scatter.set_data(position_3d * self.scale_factor, edge_color=self.color_failure, face_color=self.color_failure
                                         , size=self.size_failure)
        view.add(self.failure_satellites_scatter)


    def create_orbits(self, view, position_3d):
        num_orbits = position_3d.shape[0]
        for i in range(num_orbits):
            orbit_line = visuals.Line()
            orbit_data = np.vstack([position_3d[i], position_3d[i][0]])  # Add connection point back to the starting point
            orbit_line.set_data(orbit_data * self.scale_factor, color='black', width=2, connect='strip')
            self.orbits_lines.append(orbit_line)
            view.add(orbit_line)


    def update_survival_constellation(self, position_3d):
        self.survival_satellites_scatter.set_data(position_3d * self.scale_factor, edge_color=self.color_survival, face_color=self.color_survival
                                         , size=self.size_survival)


    def update_failure_constellation(self, position_3d):
        self.failure_satellites_scatter.set_data(position_3d * self.scale_factor, edge_color=self.color_failure, face_color=self.color_failure
                                         , size=self.size_failure)