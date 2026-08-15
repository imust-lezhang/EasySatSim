from src.tools.config_loader import load_configuration
load_configuration()
from src.simulation.controller.scene_controller import SceneController


def main():
    # beijing
    user1_latitude = 39.916668
    user1_longtitude = 116.383331
    # # new york


    # tokyo
    user2_latitude = 35.652832
    user2_longtitude = 139.839478


    sc = SceneController(test_mode=True, user1_latitude=user1_latitude, user1_longtitude=user1_longtitude
                        , user2_latitude=user2_latitude, user2_longtitude=user2_longtitude
                        , direct_connection_mode=False)
    sc.create_scene()  # Create satellite/user scene
    sc.default_behavior()  # Create behavior
    sc.default_stack()
    sc.configuration_complete()  # Configuration completed
    sc.run_simulation(plotter=True)  # Run simulation


if __name__ == '__main__':
    main()
