from src.tools.config_loader import load_configuration
load_configuration()
from src.simulation.controller.scene_controller import SceneController


def main():
    sc = SceneController()
    sc.create_scene()  # Create satellite/user scenarios
    sc.default_behavior()  # Create behavior
    sc.default_stack()
    sc.configuration_complete()  # Configuration completed
    sc.run_simulation(plotter=True)  # Run simulation


if __name__ == '__main__':
    main()
