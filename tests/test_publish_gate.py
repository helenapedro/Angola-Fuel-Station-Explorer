"""Tests for the publication gate (PR 4, design section 4.3)."""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ingestion.publish_gate import evaluate, main

NOW = datetime(2026, 10, 5, 6, 0, tzinfo=timezone.utc)
NEW = {"generated_at": "2026-10-05T06:00:00+00:00", "record_count": 279, "rejected_count": 63}
PREVIOUS = {"generated_at": "2026-09-28T06:00:00+00:00", "record_count": 279, "rejected_count": 63}


class PublishGateTest(unittest.TestCase):
    def test_normal_snapshot_passes(self):
        self.assertEqual(evaluate(NEW, PREVIOUS, now=NOW), [])

    def test_first_snapshot_with_no_previous_passes_on_absolute_checks(self):
        self.assertEqual(evaluate(NEW, None, now=NOW), [])

    def test_missing_or_future_generated_at_blocks(self):
        self.assertTrue(evaluate({"record_count": 10, "rejected_count": 0}, PREVIOUS, now=NOW))
        self.assertTrue(
            evaluate(dict(NEW, generated_at="2026-10-06T06:00:00+00:00"), PREVIOUS, now=NOW)
        )

    def test_zero_records_blocks(self):
        self.assertTrue(evaluate(dict(NEW, record_count=0), PREVIOUS, now=NOW))

    def test_drop_over_30_percent_blocks(self):
        self.assertTrue(evaluate(dict(NEW, record_count=195), PREVIOUS, now=NOW))

    def test_drop_at_30_percent_passes(self):
        # 279 * 0.70 = 195.3, so 196 is inside the threshold.
        self.assertEqual(evaluate(dict(NEW, record_count=196), PREVIOUS, now=NOW), [])

    def test_rejected_rise_over_50_percent_blocks(self):
        self.assertTrue(evaluate(dict(NEW, rejected_count=95), PREVIOUS, now=NOW))

    def test_rejected_rise_at_50_percent_passes(self):
        self.assertEqual(evaluate(dict(NEW, rejected_count=94), PREVIOUS, now=NOW), [])

    def test_cli_blocks_and_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            new_path = Path(tmp) / "new.json"
            prev_path = Path(tmp) / "prev.json"
            new_path.write_text(json.dumps({"metadata": NEW}), encoding="utf-8")
            prev_path.write_text(json.dumps({"metadata": PREVIOUS}), encoding="utf-8")
            self.assertEqual(main(["--new", str(new_path), "--previous", str(prev_path)]), 0)
            new_path.write_text(
                json.dumps({"metadata": dict(NEW, record_count=0)}), encoding="utf-8"
            )
            self.assertEqual(main(["--new", str(new_path), "--previous", str(prev_path)]), 1)

    def test_cli_without_previous_file_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            new_path = Path(tmp) / "new.json"
            new_path.write_text(json.dumps({"metadata": NEW}), encoding="utf-8")
            self.assertEqual(main(["--new", str(new_path)]), 0)
