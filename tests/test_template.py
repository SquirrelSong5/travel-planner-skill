from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TemplateStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "assets" / "template.html").read_text(encoding="utf-8")

    def test_map_key_is_not_read_from_url(self) -> None:
        self.assertNotIn("URLSearchParams(location.search).get('k')", self.html)
        self.assertNotIn('URLSearchParams(location.search).get("k")', self.html)
        self.assertIn("localStorage.getItem('amap_web_key')", self.html)

    def test_no_hardcoded_flight_route_fallback(self) -> None:
        self.assertNotIn("xmn-sha", self.html.lower())
        self.assertNotIn("sha-xmn", self.html.lower())

    def test_ctrip_cn_is_not_treated_as_foreign(self) -> None:
        self.assertIn("host === 'ctrip.com'", self.html)
        self.assertIn("host.endsWith('.ctrip.com')", self.html)

    def test_trip_data_markers_exist(self) -> None:
        self.assertEqual(self.html.count("// TRIP_DATA_START"), 1)
        self.assertEqual(self.html.count("// TRIP_DATA_END"), 1)

    def test_dynamic_html_escapes_identifiers_and_numbers(self) -> None:
        for fragment in (
            "Day ${esc(d.day)}",
            '${esc(slotNum)}.',
            '${esc(D.hotel.price.min)}',
            '${esc(p.duration_min || \'?\')}',
        ):
            self.assertIn(fragment, self.html)


if __name__ == "__main__":
    unittest.main()
