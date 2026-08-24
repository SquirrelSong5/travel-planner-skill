from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from render_html import inject_trip_data  # noqa: E402


class RenderHtmlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.template = (ROOT / "assets" / "template.html").read_text(encoding="utf-8")

    def test_script_breakout_and_placeholders_are_escaped(self) -> None:
        attack = "</script><script>alert('xss')</script>"
        trip = {
            "trip_name": attack,
            "date_range": "2026-09-18 — 2026-09-20",
            "city": "成都",
            "summary": "<img src=x onerror=alert(1)>",
            "hotel": {
                "name": "酒店 & 测试",
                "amap_uri": "javascript:alert(1)",
            },
            "days": [],
        }

        rendered = inject_trip_data(self.template, trip)

        self.assertNotIn(attack, rendered)
        self.assertNotIn("<img src=x onerror=alert(1)>", rendered)
        self.assertNotIn('href="javascript:', rendered)
        self.assertIn("\\u003c/script\\u003e", rendered)
        self.assertIn("酒店 &amp; 测试", rendered)
        self.assertIn('href="#"', rendered)

    def test_embedded_trip_json_is_still_valid_data(self) -> None:
        trip = {"trip_name": "成都 & 周末", "days": []}
        rendered = inject_trip_data(self.template, trip)
        start = rendered.index("window.tripData = ") + len("window.tripData = ")
        end = rendered.index(";", start)
        embedded = json.loads(rendered[start:end])
        self.assertEqual(embedded, trip)


if __name__ == "__main__":
    unittest.main()
