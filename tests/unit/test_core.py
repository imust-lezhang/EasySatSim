import ast
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.diagnostics.common import PROJECT_ROOT, TEST_CONFIG_ROOT, prepare_imports


prepare_imports()


class ConfigurationTests(unittest.TestCase):
    def test_small_configuration_derivations(self):
        from src.tools.config_loader import load_configuration

        cg = load_configuration(TEST_CONFIG_ROOT)
        self.assertEqual(cg.TOTAL_SATELLITE_NUMBER, 6)
        self.assertGreater(cg.COVER_RADIUS, 0)

    def test_main_presets_have_same_ordered_schema(self):
        files = sorted((PROJECT_ROOT / "configuration").glob("simulation_config*.py"))
        reference = self._names(PROJECT_ROOT / "configuration" / "simulation_config.default.py")
        self.assertTrue(files)
        for path in files:
            with self.subTest(path=path.name):
                self.assertEqual(self._names(path), reference)

    def test_sys_path_cleanup_tolerates_non_path_entries(self):
        import sys
        from src.tools.config_loader import _remove_sys_path

        target = PROJECT_ROOT.resolve()
        invalid_entry = object()
        temporary_path = [invalid_entry, str(target)]
        with patch.object(sys, "path", temporary_path):
            _remove_sys_path(target)
            self.assertEqual(sys.path, [invalid_entry])

    @staticmethod
    def _names(path):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return [
            node.targets[0].id
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id.isupper()
        ]


class BehaviorManagerTests(unittest.TestCase):
    def test_duplicate_behavior_is_rejected(self):
        from src.simulation.manager.behavior_manager import BehaviorManager

        manager = BehaviorManager()
        manager.add_active_behavior("x", lambda **_: None, 1, False, None, None)
        with self.assertRaises(KeyError):
            manager.add_active_behavior("x", lambda **_: None, 1, False, None, None)

    def test_unknown_behavior_is_rejected(self):
        from src.simulation.manager.behavior_manager import BehaviorManager

        with self.assertRaises(KeyError):
            BehaviorManager().get_passive_behavior("missing")


class StackManagerTests(unittest.TestCase):
    def test_default_stack_resolves_every_registered_protocol(self):
        from src.simulation.manager.stack_manager import StackManager

        manager = StackManager()
        manager.load_default_setting()
        for layer, protocol in (
            ("application", 80),
            ("application", 10001),
            ("transport", 0x0006),
            ("network", 0x0800),
            ("network", 0x9000),
            ("link", "Ethernet"),
            ("physical", "Ethernet"),
        ):
            self.assertEqual(len(manager.get_parse_funcs(layer, protocol)), 2)
            self.assertEqual(len(manager.get_encapsulate_funcs(layer, protocol)), 2)

    def test_unknown_replacement_is_rejected(self):
        from src.simulation.manager.stack_manager import StackManager

        manager = StackManager()
        manager.load_default_setting()
        with self.assertRaises(KeyError):
            manager.replace_protocol_func("network", 0x1234, lambda: None, lambda: None)

    def test_replacement_is_local_to_manager(self):
        from src.simulation.manager.stack_manager import StackManager

        first = StackManager()
        second = StackManager()
        first.load_default_setting()
        second.load_default_setting()

        def parse(*_args):
            return None

        def encapsulate(*_args):
            return None

        first.replace_protocol_func("network", 0x0800, parse, encapsulate)
        first.replace_relationship("network", 0x0800, "data_packet")
        self.assertIs(first.get_parse_funcs("network", 0x0800)[1], parse)
        self.assertIsNot(second.get_parse_funcs("network", 0x0800)[1], parse)


class RoutingAndPhysicalLayerTests(unittest.TestCase):
    def test_min_hop_returns_neighbor_and_reaches_destination(self):
        from src.simulation.stack.protocol_func.network_func import MinHopRouting

        current = 0
        destination = 5
        visited = {current}
        for _ in range(10):
            if current == destination:
                break
            next_hop = MinHopRouting.routing_algorithm(None, None, current, destination)
            self.assertNotIn(next_hop, visited)
            visited.add(next_hop)
            current = next_hop
        self.assertEqual(current, destination)

    def test_discrete_rate_boundaries(self):
        from src.tools.calculation import PhysicalLayerModel

        config = {
            "rate_mapping_mode": "discrete",
            "static_rate_bps": 10,
            "spectral_efficiency": 1,
            "bandwidth_hz": 100,
            "discrete_rate_table": ((-5, 1), (0, 10), (5, 100)),
        }
        self.assertEqual(PhysicalLayerModel.calculate_rate_bps(-6, config), 0)
        self.assertEqual(PhysicalLayerModel.calculate_rate_bps(0, config), 10)
        self.assertEqual(PhysicalLayerModel.calculate_rate_bps(6, config), 100)

    def test_physical_configuration_and_link_type(self):
        from src.tools.calculation import PhysicalLayerModel

        PhysicalLayerModel.validate_config()
        self.assertEqual(PhysicalLayerModel.infer_link_type("satellite", "satellite"), "isl")
        self.assertEqual(PhysicalLayerModel.infer_link_type("satellite", "user"), "sgl")


class MetricAndExportTests(unittest.TestCase):
    def test_shared_metrics_average_delay_and_hops(self):
        from src.simulation.variable.performance import NetworkMetrics, SharedNetworkMetrics

        current = NetworkMetrics(arrive_packets_number=2, loss_packets_number=1, delay=30, hop_count=8)
        total = NetworkMetrics(arrive_packets_number=2, loss_packets_number=0, delay=20, hop_count=8)
        shared = SharedNetworkMetrics()
        shared.update_shared_metrics(current, total)
        self.assertEqual(shared.delay.value, 10)
        self.assertEqual(shared.hop_count.value, 4)

    def test_export_name_increments(self):
        import tempfile
        from src.simulation.visualization.simulation_control_window import SimulationControlWindow

        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests" / "artifacts") as directory:
            source = Path(directory) / "result.csv"
            self.assertEqual(
                SimulationControlWindow._next_available_export_path(source).name,
                "result_export.csv",
            )
            (Path(directory) / "result_export.csv").touch()
            self.assertEqual(
                SimulationControlWindow._next_available_export_path(source).name,
                "result_export_01.csv",
            )

    def test_open_local_folder_uses_qt_desktop_service(self):
        import tempfile
        from src.simulation.visualization.simulation_control_window import SimulationControlWindow

        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests" / "artifacts") as directory:
            folder = Path(directory).resolve()
            service = "src.simulation.visualization.simulation_control_window.QDesktopServices.openUrl"
            with patch(service, return_value=True) as open_url:
                self.assertTrue(SimulationControlWindow._open_local_folder(folder))
                requested_url = open_url.call_args.args[0]
                self.assertTrue(requested_url.isLocalFile())
                self.assertEqual(Path(requested_url.toLocalFile()).resolve(), folder)
            with patch(service, return_value=False):
                self.assertFalse(SimulationControlWindow._open_local_folder(folder))


class CleanupTests(unittest.TestCase):
    def test_stale_shared_memory_cleanup_reports_unexpected_errors_and_continues(self):
        from src.simulation.visualization.simulation_control_window import cleanup_stale_shared_memory

        locked = MagicMock(name="locked_shared_memory")
        locked.unlink.side_effect = OSError("locked")
        locked.close.side_effect = BufferError("exported view")
        already_removed = MagicMock(name="already_removed_shared_memory")
        already_removed.unlink.side_effect = FileNotFoundError()
        handles = [locked, already_removed]

        def open_shared_memory(**_kwargs):
            if handles:
                return handles.pop(0)
            raise FileNotFoundError()

        module = "src.simulation.visualization.simulation_control_window"
        with patch(f"{module}.shared_memory.SharedMemory", side_effect=open_shared_memory) as open_shm:
            with patch("builtins.print") as print_warning:
                cleanup_stale_shared_memory()

        self.assertGreater(open_shm.call_count, 2)
        already_removed.close.assert_called_once_with()
        messages = [call.args[0] for call in print_warning.call_args_list]
        self.assertTrue(any("unlink failed" in message and "locked" in message for message in messages))
        self.assertTrue(any("close failed" in message and "exported view" in message for message in messages))

    def test_runtime_stop_collects_process_warnings_and_continues(self):
        from src.simulation.visualization.simulation_control_window import SimulationRuntime

        runtime = SimulationRuntime()
        entity_process = MagicMock(name="entity_process")
        entity_process.is_alive.side_effect = [True, True]
        entity_process.terminate.side_effect = OSError("access denied")
        timer_process = MagicMock(name="timer_process")
        timer_process.is_alive.side_effect = [False, False]
        runtime.process_entity = entity_process
        runtime.process_timer = timer_process

        warnings = runtime.stop()

        self.assertTrue(any("terminate entity process" in warning for warning in warnings))
        entity_process.kill.assert_called_once_with()
        timer_process.join.assert_called_once_with(timeout=3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
