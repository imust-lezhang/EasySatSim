import numpy as np
from vispy.io import imread
from vispy.scene.visuals import Mesh
from vispy.scene import transforms
from vispy.visuals.filters import TextureFilter


class EarthPlotter:
    def __init__(self):
        pass


    def create_earth(self, view, texture_path):
        # Load the earth texture file
        texture = np.flipud(imread(texture_path))
        # Generate sphere mesh data
        vertices, faces, texcoords = self._create_sphere(radius=1, rows=50, cols=50)
        # Create a Mesh object and add it to the view
        mesh = Mesh(vertices, faces, shading='smooth', color='white')
        mesh.transform = transforms.MatrixTransform()
        mesh.transform.rotate(180, (1, 0, 0))
        mesh.transform.rotate(180, (0, 0, 1))
        mesh.shading = None
        view.add(mesh)
        texture_filter = TextureFilter(texture, texcoords)
        mesh.attach(texture_filter)
        return


    # Create sphere vertices, faces, and texture coordinates
    def _create_sphere(self, radius, rows, cols):
        phi = np.linspace(0, np.pi, rows)
        theta = np.linspace(0, 2 * np.pi, cols)
        phi, theta = np.meshgrid(phi, theta)


        x = radius * np.sin(phi) * np.cos(theta)
        y = radius * np.sin(phi) * np.sin(theta)
        z = radius * np.cos(phi)


        vertices = np.stack([x, y, z], axis=-1).reshape(-1, 3)
        # texcoords = np.stack([theta / (2 * np.pi), phi / np.pi], axis=-1).reshape(-1, 2)
        # Adjust the order of texture coordinates
        texcoords = np.stack([(2 * np.pi - theta) / (2 * np.pi), phi / np.pi], axis=-1).reshape(-1, 2)


        faces = []
        for i in range(rows - 1):
            for j in range(cols - 1):
                p1 = i * cols + j
                p2 = p1 + 1
                p3 = p1 + cols
                p4 = p3 + 1
                faces.append([p1, p2, p3])
                faces.append([p2, p4, p3])


        faces = np.array(faces)
        return vertices, faces, texcoords