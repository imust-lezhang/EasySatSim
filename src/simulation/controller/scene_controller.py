from src.abstract.controller.scene_controller import AbstractSceneController
from src.simulation.manager.entity_manager import EntityManager
from src.simulation.manager.behavior_manager import BehaviorManager
from src.simulation.manager.stack_manager import StackManager
from src.simulation.variable.timer import GlobalTimer
from src.simulation.variable.shared_value import SharedValue
from src.simulation.variable.performance import NetworkPerformance
from src.simulation.variable.virtual_store import VirtualStore
from src.simulation.controller.plotter_controller import PlotterController
from src.simulation.variable.performance import SharedNetworkMetrics
from src.simulation.stack.stack_func import StackFunc
import asyncio
import multiprocessing
from configuration import simulation_config as cg
from threading import Timer
from multiprocessing import shared_memory
from src.simulation.variable import constant as ct
from src.tools.config_loader import get_active_config_root


class SceneController(AbstractSceneController):
    def __init__(self, test_mode=False
                , user1_latitude=None, user1_longtitude=None, user2_latitude=None, user2_longtitude=None
                , direct_connection_mode=False):
        self.init_step = 6  # Number of key initialization steps

        self.shared_value = SharedValue()  # Initialize shared variables
        self.shared_metric = SharedNetworkMetrics()  # Initialize shared metrics


        self.entity_manager = EntityManager()
        self.behavior_manager = BehaviorManager()
        self.stack_manager = StackManager()


        self._is_completed = False
        self.test_mode = test_mode
        self.user1_position = None
        self.user2_position = None
        self.direct_connection_mode = direct_connection_mode
        if test_mode:
            if user1_latitude is None or user1_longtitude is None or user2_latitude is None or user2_longtitude is None:
                raise ValueError("user1_latitude, user1_longtitude, user2_latitude and user2_longtitude"
                                 "  must be provided when test_mode=True")
            else:
                if cg.USER_NUMBER!= 2:
                    raise ValueError("configuration.simulation_config.USER_NUMBER must set to 2 in test mode.")
                self.user1_position = [user1_latitude, user1_longtitude, 0]
                self.user2_position = [user2_latitude, user2_longtitude, 0]
        if cg.USER_NUMBER!= 2 and self.direct_connection_mode:
            raise ValueError("Direct connect mode is used to connect two users directly to one satellite."
                             " You must enable test mode and set two users.")
        self.routing_algorithm = None
        return


    def create_scene(self):
        if self.test_mode:
            self.entity_manager.test_mode_create_users(user1_position=self.user1_position, user2_position=self.user2_position)
        else:
            self.entity_manager.create_users()
        self.entity_manager.create_satellites()
        print(f"[Success 1/{self.init_step}] Satellite and user entities created.")
        self.entity_manager.create_constellation()
        self.entity_manager.create_ground()
        print(f"[Success 2/{self.init_step}] Constellation and ground entity cluster created.")
        return


    def default_behavior(self):
        self.behavior_manager.load_default_behaviors()
        users = self.entity_manager.get_entity(entity_category="user")

        if not self.direct_connection_mode:
            for user in users:
                self.behavior_manager.bind_default_user_active_behaviors(user=user)
                self.behavior_manager.bind_default_user_passive_behaviors(user=user)
        else:
            self.behavior_manager.load_test_mode(user1=users[1])
            self.behavior_manager.bind_direction_connect_mode_active_behaviors(user0=users[0], user1=users[1])
            self.behavior_manager.bind_default_user_passive_behaviors(user=users[0])
            self.behavior_manager.bind_default_user_passive_behaviors(user=users[1])


        satellites = self.entity_manager.get_entity(entity_category="satellite")
        for satellite in satellites:
            self.behavior_manager.bind_default_satellite_active_behaviors(satellite=satellite)
            self.behavior_manager.bind_default_satellite_passive_behaviors(satellite=satellite)
        print(f"[Success 3/{self.init_step}] Satellite and user default behaviors loaded.")
        constellation = self.entity_manager.get_entity_cluster("constellation")
        self.behavior_manager.bind_default_common_behaviors(constellation=constellation)
        print(f"[Success 4/{self.init_step}] Constellation and ground default behaviors loaded.")
        return


    def default_stack(self):
        if self.direct_connection_mode or self.test_mode:
            self.stack_manager.load_test_mode()
        else:
            self.stack_manager.load_default_setting()
        print(f"[Success 5/{self.init_step}] The default protocol stack is loaded.")
        return


    def configuration_complete(self):
        self._is_completed = True
        print(f"[Success 6/{self.init_step}] Scene configuration completed.")
        return


    def run_simulation(self, plotter=True, running_time=None, output=True):
        if self._is_completed:
            if plotter:
                print_simulation_info(num_satellites=cg.TOTAL_SATELLITE_NUMBER, num_users=cg.USER_NUMBER)
                if self.direct_connection_mode:
                    print("\n\n[Note] After enabling direct connection mode, data packets will be sent to port 20000 instead of port"
                          " 80. The average latency indicates the RTT, not the one-way latency.\n\n")
                scene_options = self.get_scene_options()
                self.release_shared_memory()
                from src.simulation.visualization.simulation_control_window import cleanup_stale_shared_memory
                from src.simulation.visualization.simulation_control_window import run_control_window
                cleanup_stale_shared_memory()
                return run_control_window(scene_options=scene_options,
                                          output_console=False,
                                          auto_start=False,
                                          running_time=running_time,
                                          config_root=get_active_config_root())

            process_entity = multiprocessing.Process(target=self._create_entity, args=(output, ))
            process_timer = multiprocessing.Process(target=self._create_timer, args=())
            print_simulation_info(num_satellites=cg.TOTAL_SATELLITE_NUMBER, num_users=cg.USER_NUMBER)
            if self.direct_connection_mode:
                print("\n\n[Note] After enabling direct connection mode, data packets will be sent to port 20000 instead of port"
                      " 80. The average latency indicates the RTT, not the one-way latency.\n\n")
            process_timer.start()
            process_entity.start()


            # Set a timer to end the process after a specified time
            if running_time is not None:
                def stop_processes():
                    process_entity.terminate()
                    process_timer.terminate()
                    print("\n\n[Note] The program has automatically stopped as the specified running time limit was reached. Task was cancelled...")


                timer = Timer(running_time, stop_processes)
                timer.start()


            try:
                process_timer.join()
                process_entity.join()
            except KeyboardInterrupt:
                print("Main process received shutdown signal...")
        else:
            print("[Wrong] Configuration is not complete. If the scene has been configured"
                  ", you must call scene_controller.scene_configuration_complete() "
                  "before scene_controller.run_simulation().")
        return


    def _create_timer(self):
        global_timer = GlobalTimer()
        global_timer.start()
        for entity_cluster in self.entity_manager.dict_entity_cluster.values():
            if hasattr(entity_cluster, "bind_shared_memory_views"):
                entity_cluster.bind_shared_memory_views()
        try:
            asyncio.run(self.entity_manager.start_entity_cluster_tasks())
        except KeyboardInterrupt:
            print("\n\n[Note] The program has been terminated manually by the user. Task was cancelled...")


    def _create_plotter(self):
        try:
            PlotterController.plot_3d(shared_metric=self.shared_metric, test_mode=self.test_mode)
        except KeyboardInterrupt:
            print("\n\n[Note] The program has been terminated manually by the user. Task was cancelled...")


    def _create_entity(self, output):
        if self.routing_algorithm:
            self.stack_manager.register_routing_algorithm(self.routing_algorithm)


        for entity_list in self.entity_manager.dict_entity.values():
            for entity in entity_list:
                if hasattr(entity, "bind_shared_memory_views"):
                    entity.bind_shared_memory_views()
                entity.set_info()
        VirtualStore.set_user_ip = set(VirtualStore.user_id_to_ip_table.values())
        VirtualStore.set_satellite_ip = set(VirtualStore.satellite_id_to_ip_table.values())
        satellites = self.entity_manager.get_entity(entity_category="satellite")
        for satellite in satellites:
            satellite.init_tables()
        StackFunc.stack_manager = self.stack_manager
        NetworkPerformance.start(shared_metric=self.shared_metric, output=output)
        try:
            asyncio.run(self.entity_manager.start_entity_tasks())
        except KeyboardInterrupt:
            print("\n\n[Note] The program has been terminated manually by the user. Task was cancelled...")


    def get_entity_manager(self):
        return self.entity_manager


    def get_behavior_manager(self):
        return self.behavior_manager


    def get_stack_manager(self):
        return self.stack_manager


    def register_routing_algorithm(self, routing_algorithm):
        self.routing_algorithm = routing_algorithm


    def get_scene_options(self):
        scene_options = {
            "test_mode": self.test_mode,
            "direct_connection_mode": self.direct_connection_mode,
        }
        if self.test_mode:
            scene_options["user1_latitude"] = self.user1_position[0]
            scene_options["user1_longtitude"] = self.user1_position[1]
            scene_options["user2_latitude"] = self.user2_position[0]
            scene_options["user2_longtitude"] = self.user2_position[1]
        return scene_options


    def release_shared_memory(self):
        shared_memory_objects = []
        self._collect_shared_memory_objects(self.shared_value, shared_memory_objects)
        self._collect_shared_memory_objects(self.entity_manager, shared_memory_objects)

        for entity_cluster in self.entity_manager.dict_entity_cluster.values():
            self._collect_shared_memory_objects(entity_cluster, shared_memory_objects)
        for entity_list in self.entity_manager.dict_entity.values():
            for entity in entity_list:
                self._collect_shared_memory_objects(entity, shared_memory_objects)

        for shm in shared_memory_objects:
            try:
                shm.close()
            except (BufferError, OSError) as exc:
                name = getattr(shm, "name", "unknown")
                print(f"[Warning] Shared memory close failed ({name}): {exc}")

        for name in self._shared_memory_names():
            try:
                shm = shared_memory.SharedMemory(name=name)
            except FileNotFoundError:
                continue
            try:
                shm.unlink()
            except FileNotFoundError:
                pass
            except (BufferError, OSError) as exc:
                print(f"[Warning] Shared memory unlink failed ({name}): {exc}")
            try:
                shm.close()
            except (BufferError, OSError) as exc:
                print(f"[Warning] Shared memory close failed ({name}): {exc}")
        return


    @staticmethod
    def _collect_shared_memory_objects(owner, shared_memory_objects):
        if owner is None:
            return
        for value in vars(owner).values():
            if isinstance(value, shared_memory.SharedMemory):
                shared_memory_objects.append(value)
        return


    @staticmethod
    def _shared_memory_names():
        return [
            ct.SHM_CURRENT_TIME,
            ct.SHM_SATELLITE_POSITION_3D,
            ct.SHM_SATELLITE_POSITION_2D,
            ct.SHM_ORBIT_POSITION_3D,
            ct.SHM_USER_POSITION_3D,
            ct.SHM_ACCESS_RELATIONSHIP,
            ct.SHM_ROUTING_PATH,
            ct.SHM_SATELLITE_LOAD_DEVIATION,
            ct.SHM_SATELLITE_LATENCY,
        ]


def print_simulation_info(num_satellites, num_users):
    title_lines = [
        "  ███████╗ █████╗ ███████╗██╗   ██╗███████╗ █████╗ ████████╗███████╗██╗███╗   ███╗  ",
        "  ██╔════╝██╔══██╗██╔════╝╚██╗ ██╔╝██╔════╝██╔══██╗╚══██╔══╝██╔════╝██║████╗ ████║  ",
        "  █████╗  ███████║███████╗ ╚████╔╝ ███████╗███████║   ██║   ███████║██║██╔████╔██║  ",
        "  ██╔══╝  ██╔══██║╚════██║  ╚██╔╝  ╚════██║██╔══██║   ██║   ╚════██║██║██║╚██╔╝██║  ",
        "  ███████╗██║  ██║███████║   ██║   ███████║██║  ██║   ██║   ███████║██║██║ ╚═╝ ██║  ",
        "  ╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝╚═╝     ╚═╝  "
    ]


    lines = [
        "Start LEO Satellite Network Simulation!",
        f"Includes {num_satellites} satellites and {num_users} users in total."
    ]


    # Determine the maximum width of the box
    all_lines = title_lines + lines
    max_width = max(len(line) for line in all_lines) + 2  # Ensure there is 1 space on each side


    # Border design
    top_border = "╔" + "═" * (max_width + 2) + "╗"
    bottom_border = "╚" + "═" * (max_width + 2) + "╝"
    line_border = "║"


    # Print the upper border
    print(top_border)


    # Print art text and center it
    for line in title_lines:
        print(f"{line_border} {line.center(max_width)} {line_border}")


    # Print a blank line to separate art text and ordinary content
    print(f"{line_border}{' ' * (max_width + 2)}{line_border}")


    # Print ordinary content and center it
    for line in lines:
        print(f"{line_border} {line.center(max_width)} {line_border}")


    # Print the lower border
    print(bottom_border)
