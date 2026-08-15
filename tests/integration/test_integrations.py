import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.diagnostics.common import PROJECT_ROOT, prepare_imports


prepare_imports()


class IntegrationTests(unittest.TestCase):
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
