import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.diagnostics.common import PROJECT_ROOT, prepare_imports


prepare_imports()


class IntegrationTests(unittest.TestCase):
    def test_test_mode_example_uses_isolated_configuration(self):
        script = """
import os
from pathlib import Path
from src.tools.config_loader import load_configuration

os.environ['EASYSATSIM_TEST_MODE_OUTPUT_ID'] = 'integration_check'
config = load_configuration('examples/test_mode_example/src')
assert config.USER_NUMBER == 2
assert config.TOTAL_SATELLITE_NUMBER == 1600
assert config.AUTO_ASSIGN_SAVE_FILE_PATH is False
expected = Path('examples/test_mode_example/output/easysatsim_result_test_mode_integration_check.csv')
actual = (Path('src') / config.SAVE_FILE_PATH).resolve()
assert actual == expected.resolve(), (actual, expected.resolve())
"""
        subprocess.run(
            [sys.executable, "-c", script],
            cwd=PROJECT_ROOT,
            check=True,
            timeout=30,
        )

    def test_test_mode_example_can_be_imported_as_a_direct_script(self):
        example_root = PROJECT_ROOT / "examples" / "test_mode_example"
        script = f"""
import runpy
import sys

# Reproduce PyCharm's direct-script path order: the example directory is
# searched before an already-present project root.
sys.path.insert(0, {str(PROJECT_ROOT)!r})
sys.path.insert(0, {str(example_root)!r})
runpy.run_path({str(example_root / 'main.py')!r}, run_name='entry_import_check')
import src.tools.config_loader as config_loader
expected = {str(PROJECT_ROOT / 'src' / 'tools' / 'config_loader.py')!r}
assert config_loader.__file__ == expected, config_loader.__file__
"""
        subprocess.run(
            [sys.executable, "-c", script],
            cwd=example_root,
            check=True,
            timeout=30,
        )

    def test_test_mode_example_workers_inherit_local_dimensions(self):
        probe_text = f"""
import multiprocessing
import sys

sys.path.insert(0, {str(PROJECT_ROOT)!r})
from examples.test_mode_example import main as example_main


def read_dimensions(queue):
    from configuration import simulation_config as config
    queue.put((config.USER_NUMBER, config.TOTAL_SATELLITE_NUMBER))


if __name__ == '__main__':
    context = multiprocessing.get_context('spawn')
    queue = context.Queue()
    process = context.Process(target=read_dimensions, args=(queue,))
    process.start()
    process.join(30)
    if process.exitcode != 0:
        raise SystemExit(process.exitcode)
    dimensions = queue.get(timeout=5)
    if dimensions != (2, 1600):
        raise AssertionError(dimensions)
"""
        with tempfile.TemporaryDirectory() as directory:
            probe_path = Path(directory) / "test_mode_spawn_probe.py"
            probe_path.write_text(probe_text, encoding="utf-8")
            subprocess.run(
                [sys.executable, str(probe_path)],
                cwd=PROJECT_ROOT,
                check=True,
                timeout=40,
            )

    def test_case2_summary_paths_are_project_relative(self):
        from cases.case2.experiment.evaluation.case2_metrics import (
            to_project_relative_path,
        )

        path = PROJECT_ROOT / "cases" / "case2" / "experiment" / "output" / "x.csv"
        self.assertEqual(
            to_project_relative_path(path),
            "cases/case2/experiment/output/x.csv",
        )

    def test_case3_recorded_paths_are_portable(self):
        from cases.case3.experiment.integration.paths import (
            normalize_recorded_path,
            resolve_recorded_path,
            to_project_relative_path,
        )

        relative = "cases/case3/experiment/output/example.csv"
        expected = PROJECT_ROOT / Path(relative)
        self.assertEqual(resolve_recorded_path(relative), expected)
        self.assertEqual(to_project_relative_path(expected), relative)
        self.assertEqual(
            normalize_recorded_path(
                r"Z:\old\author\EasySatSim\cases\case3\experiment\output\example.csv"
            ),
            relative,
        )

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                to_project_relative_path(Path(directory) / "outside.csv")

    def test_case3_route_table_archive(self):
        subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from cases.case3 import main; "
                    "from cases.case3.experiment.data.centralized_route_tables "
                    "import load_centralized_route_tables; "
                    "t=load_centralized_route_tables(); "
                    "assert t['normal'].shape == (400, 400); "
                    "assert t['s377_failed'].shape == (400, 400); "
                    "assert int((t['s377_failed'] == 377).sum()) == 0"
                ),
            ],
            cwd=PROJECT_ROOT,
            check=True,
            timeout=30,
        )

    def test_ipv4_stack_registration_validator(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "examples.protocol_ipv4_example.experiment.evaluation.validate_stack_registration",
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            self.fail(result.stdout + "\n" + result.stderr)

    def test_case3_batch_dry_run_has_paired_modes(self):
        result = subprocess.run(
            [sys.executable, "cases/case3/run_experiment.py", "--seed-count", "1", "--dry-run"],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=True,
            timeout=30,
        )
        self.assertIn("--routing-mode centralized", result.stdout)
        self.assertIn("--routing-mode distributed", result.stdout)
        self.assertIn("Planned runs: 2", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
