from vispy import scene, app
import numpy as np
from vispy.app import Timer


class ChartPlotter:
    def __init__(self):
        self.view = None
        self.line = None
        self.scatter = None
        self.data_capacity = 1024
        self.data_count = 0
        self.data = np.zeros((self.data_capacity, 2), dtype=np.float64)
        self.x_min = None
        self.x_max = None
        self.y_min = None
        self.y_max = None


    def create_line_chart(self, grid, row, col, title_text, y_label="Delay", x_label="Time"):
        title = scene.Label(title_text, color='black')
        title.height_max = 40
        grid.add_widget(title, row=row, col=col+2)
        yaxis = scene.AxisWidget(orientation='left',
                             axis_label=y_label,
                             axis_font_size=12,
                             axis_label_margin=80,
                             tick_label_margin=5,
                             axis_color='black',
                             text_color='black',
                             tick_color='black')
        yaxis.width_max = 80
        grid.add_widget(yaxis, row=row + 1, col=col)


        xaxis = scene.AxisWidget(orientation='bottom',
                             axis_label=x_label,
                             axis_font_size=12,
                             axis_label_margin=80,
                             tick_label_margin=20,
                             axis_color='black',
                             text_color='black',
                             tick_color='black')
        xaxis.height_max = 80
        right_padding = grid.add_widget(xaxis, row=row + 2, col=col + 1, col_span=3)
        right_padding.width_max = 600
        right_padding.height_max = 800
        view = grid.add_view(row=row + 1, col=col + 1, border_color='black', col_span=3)
        view.camera = 'panzoom'
        xaxis.link_view(view)
        yaxis.link_view(view)
        self.view = view
        # Create a Line object to draw the line graph
        self.line = scene.Line(parent=view.scene, color='blue')
        # Create a Markers object to draw hollow dots
        self.scatter = scene.Markers(parent=view.scene)


    def update(self, new_point):
        # Update the data array and add a new data point
        if self.data_count >= self.data_capacity:
            self.data_capacity = self.data_capacity * 2
            new_data = np.zeros((self.data_capacity, 2), dtype=np.float64)
            new_data[:self.data_count] = self.data
            self.data = new_data

        self.data[self.data_count] = new_point
        x_value = self.data[self.data_count][0]
        y_value = self.data[self.data_count][1]
        if self.data_count == 0:
            self.x_min = x_value
            self.x_max = x_value
            self.y_min = y_value
            self.y_max = y_value
        else:
            self.x_min = min(self.x_min, x_value)
            self.x_max = max(self.x_max, x_value)
            self.y_min = min(self.y_min, y_value)
            self.y_max = max(self.y_max, y_value)

        self.data_count += 1
        data_array = self.data[:self.data_count]


        # Update the data of the Line object
        self.line.set_data(data_array)


        # Update the data of the Markers object, only showing the last point
        if len(data_array) > 0:
            self.scatter.set_data(data_array[-1:], edge_color='red', face_color='white', size=10)


        # Adjust the view range to keep the data centered
        self.view.camera.set_range(x=(self.x_min, self.x_max), y=(self.y_min, self.y_max))
