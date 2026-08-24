from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate import _valid_price_field, check_v0, check_v5, check_v8  # noqa: E402


class ValidateTests(unittest.TestCase):
    def test_empty_trip_fails_core_schema(self) -> None:
        result = check_v0({})
        self.assertEqual(result["status"], "❌")
        self.assertTrue(result["errors"])

    def test_multi_poi_day_without_transports_fails(self) -> None:
        days = [{"day": 1, "pois": [{"idx": 1}, {"idx": 2}], "transports": []}]
        result = check_v8(days, {})
        self.assertEqual(result["status"], "❌")

    def test_demo_price_source_is_rejected(self) -> None:
        value = {
            "min": 10,
            "max": 20,
            "unit": "per_person",
            "source": "demo-estimate",
        }
        error = _valid_price_field(value, "meal")
        self.assertIsNotNone(error)
        self.assertIn("demo-estimate", error or "")

    def test_return_ticket_is_used_for_buffer(self) -> None:
        day = {"pois": [{"name": "机场", "time": "15:00"}]}
        trip = {
            "prebook": [
                {"item": "国内机票（出发 → 成都）", "depart_time": "09:00"},
                {"item": "国内机票（成都 → 返程）", "depart_time": "18:00"},
            ]
        }
        result = check_v5(day, trip)
        self.assertEqual(result["status"], "✅")
        self.assertEqual(result["buffer_hours"], 3.0)


if __name__ == "__main__":
    unittest.main()
