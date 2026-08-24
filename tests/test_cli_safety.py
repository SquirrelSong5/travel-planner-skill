from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CliSafetyTests(unittest.TestCase):
    def test_add_hotel_legs_requires_explicit_output_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            trip = Path(tmp) / "trip.json"
            original = '{"days": []}\n'
            trip.write_text(original, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "add_hotel_legs.py"), str(trip)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("不会默认覆盖", result.stderr)
            self.assertEqual(trip.read_text(encoding="utf-8"), original)

    def test_validator_stops_cleanly_on_invalid_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            trip = Path(tmp) / "bad.json"
            trip.write_text('{"days": [{"pois": "not-a-list"}]}\n', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "validate.py"), str(trip), "--pretty"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn('"id": "V0"', result.stdout)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
