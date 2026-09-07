from __future__ import annotations

import unittest

from pipeline import get_stages, parse_args


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


if __name__ == "__main__":
    unittest.main()
