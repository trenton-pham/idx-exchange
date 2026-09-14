from __future__ import annotations

import sys
import unittest
from unittest import mock

from scripts.pipeline import (
    PROJECT_DIR,
    SCRIPTS_DIR,
    get_stages,
    parse_args,
    run_pipeline,
)


class PipelineTests(unittest.TestCase):
    def test_no_fetch_preserves_existing_first_stage(self):
        stages = get_stages(False)
        self.assertEqual(stages[0][1], ["process.py"])

    def test_fetch_is_first_and_reports_follow_aggregation(self):
        stages = get_stages(True, "2026-08", "2026-09", True)
        self.assertEqual(
            stages[0][1],
            [
                "extract_crmls.py",
                "--start-month",
                "2026-08",
                "--end-month",
                "2026-09",
                "--force",
            ],
        )
        self.assertEqual(stages[1][1], ["process.py"])
        self.assertEqual(stages[2][1], ["distribution.py"])

    def test_fetch_arguments_must_be_paired(self):
        with self.assertRaises(SystemExit):
            parse_args(["--fetch-start", "2026-08"])

    def test_force_requires_fetch_range(self):
        with self.assertRaises(SystemExit):
            parse_args(["--force-fetch"])

    def test_pipeline_runs_scripts_from_scripts_directory_at_project_root(self):
        with mock.patch("scripts.pipeline.subprocess.run") as subprocess_run:
            result = run_pipeline([("Combine monthly data", ["process.py"])])

        self.assertEqual(result, 0)
        subprocess_run.assert_called_once_with(
            [sys.executable, str(SCRIPTS_DIR / "process.py")],
            cwd=PROJECT_DIR,
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
