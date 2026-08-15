import numpy as np
from vispy.io import imread
from vispy.scene import transforms, visuals
from src.tools import calculation


class Constellation2DPlotter:
    def __init__(self, normal_color, failure_color, user_color, connect_color, routing_color):
        self.map_image = None
        self.orbit_lines = visuals.Line()
        self.normal_satellites = visuals.Markers()
        self.failure_satellites = visuals.Markers()
        self.users = visuals.Markers()
        self.connect_lines = visuals.Line()
        self.routing_line = visuals.Line()
        self.grid_lines = visuals.Line()
        self.orbit_color = "black"
        self.normal_color = normal_color
        self.failure_color = failure_color
        self.user_color = user_color
        self.connect_color = connect_color
        self.routing_color = routing_color
        self._set_layer(self.grid_lines, -30)
        self._set_layer(self.orbit_lines, -20)
        self._set_layer(self.connect_lines, 10)
        self._set_layer(self.routing_line, 20)
        self._set_layer(self.normal_satellites, 30)
        self._set_layer(self.failure_satellites, 31)
        self._set_layer(self.users, 32)


    def create_scene(self, view, texture_path, satellite_position_2d, user_position_3d,
                     access_relationship, satellite_load_deviation, orbit_position_3d,
                     routing_path=None, test_mode=False):
        self._create_map(view=view, texture_path=texture_path)
        self._create_grid_lines(view=view)
        self._create_orbits(view=view, orbit_position_3d=orbit_position_3d)
        view.add(self.connect_lines)
        view.add(self.routing_line)
        view.add(self.normal_satellites)
        view.add(self.failure_satellites)
        view.add(self.users)
        self.update_scene(satellite_position_2d=satellite_position_2d,
                          user_position_3d=user_position_3d,
                          access_relationship=access_relationship,
                          satellite_load_deviation=satellite_load_deviation,
                          routing_path=routing_path,
                          test_mode=test_mode)
        return


    def update_scene(self, satellite_position_2d, user_position_3d, access_relationship,
                     satellite_load_deviation, routing_path=None, test_mode=False):
        satellite_load_deviation = satellite_load_deviation.reshape(-1)
        index_survival = np.where(satellite_load_deviation >= 0)[0]
        index_failure = np.where(satellite_load_deviation < 0)[0]

        satellite_xy = self._to_xy(satellite_position_2d)
        user_position_2d = calculation.position_3D_to_2D_array(user_position_3d)
        user_xy = self._to_xy(user_position_2d)
        connect_xy = get_connect_relationship_2d(user_xy=user_xy,
                                                 satellite_xy=satellite_xy,
                                                 access_relationship=access_relationship)

        self.normal_satellites.set_data(satellite_xy[index_survival],
                                        edge_color=self.normal_color,
                                        face_color=self.normal_color,
                                        size=4)
        self.failure_satellites.set_data(satellite_xy[index_failure],
                                         edge_color=self.failure_color,
                                         face_color=self.failure_color,
                                         size=6)
        self.users.set_data(user_xy, edge_color=self.user_color, face_color=self.user_color, size=3)
        self.connect_lines.set_data(connect_xy, color=self.connect_color, width=1, connect="segments")

        if test_mode and routing_path is not None:
            mask = np.any(routing_path != -1, axis=1)
            if np.sum(mask) >= 2:
                routing_position_2d = calculation.position_3D_to_2D_array(routing_path[mask])
                routing_segments = self._build_line_segments(self._to_xy(routing_position_2d))
                self.routing_line.set_data(routing_segments,
                                           color=self.routing_color,
                                           width=2.5,
                                           connect="segments")
            else:
                self.routing_line.set_data(np.empty((0, 2)), color=self.routing_color, width=2.5, connect="strip")
        return


    def _create_map(self, view, texture_path):
        texture = np.flipud(imread(texture_path))
        self.map_image = visuals.Image(texture)
        self._set_layer(self.map_image, -100)
        height = texture.shape[0]
        width = texture.shape[1]
        self.map_image.transform = transforms.STTransform(scale=(360.0 / width, 180.0 / height, 1),
                                                          translate=(-180.0, -90.0, 0))
        view.add(self.map_image)
        return


    def _create_orbits(self, view, orbit_position_3d):
        orbit_position_2d = calculation.position_3D_to_2D_array(orbit_position_3d)
        orbit_position_2d = orbit_position_2d.reshape(-1, 100, 3)
        all_segments = []
        for orbit_position in orbit_position_2d:
            orbit_xy = self._to_xy(orbit_position)
            orbit_segments = self._build_line_segments(orbit_xy)
            if len(orbit_segments) > 0:
                all_segments.append(orbit_segments)

        if all_segments:
            orbit_segments = np.vstack(all_segments)
        else:
            orbit_segments = np.empty((0, 2))
        self.orbit_lines.set_data(orbit_segments,
                                  color=self.orbit_color,
                                  width=1.0,
                                  connect="segments")
        view.add(self.orbit_lines)
        return


    def _create_grid_lines(self, view):
        points = []
        for longitude in range(-180, 181, 60):
            points.append([longitude, -90])
            points.append([longitude, 90])
        for latitude in range(-60, 61, 30):
            points.append([-180, latitude])
            points.append([180, latitude])
        self.grid_lines.set_data(np.array(points, dtype=np.float64),
                                 color=(0.60, 0.65, 0.72, 0.36),
                                 width=1,
                                 connect="segments")
        view.add(self.grid_lines)
        return


    @staticmethod
    def _to_xy(position_2d):
        return np.column_stack((position_2d[:, 1], position_2d[:, 0]))


    @staticmethod
    def _build_line_segments(xy):
        if len(xy) < 2:
            return np.empty((0, 2))

        segments = []
        for i in range(len(xy) - 1):
            if abs(xy[i + 1][0] - xy[i][0]) <= 180:
                segments.append(xy[i])
                segments.append(xy[i + 1])
        return np.array(segments, dtype=np.float64)


    @staticmethod
    def _set_layer(visual, order):
        visual.order = order
        if hasattr(visual, "set_gl_state"):
            visual.set_gl_state(depth_test=False, blend=True)
        return


def get_connect_relationship_2d(user_xy, satellite_xy, access_relationship):
    valid_user_indices = np.where(access_relationship >= 0)[0]
    valid_user_positions = user_xy[valid_user_indices]
    satellite_indices = access_relationship[valid_user_indices]
    valid_satellite_positions = satellite_xy[satellite_indices]
    paired_positions = np.zeros((len(valid_user_indices) * 2, 2))
    paired_positions[0::2] = valid_user_positions
    paired_positions[1::2] = valid_satellite_positions
    return paired_positions
