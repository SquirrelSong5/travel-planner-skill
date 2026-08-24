from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from render_markdown import render_trip_markdown  # noqa: E402


class RenderMarkdownTests(unittest.TestCase):
    def test_renders_operational_sections_from_one_trip(self) -> None:
        trip = {
            "trip_name": "雨天周末",
            "date_range": "2026-09-18 — 2026-09-19",
            "city": "成都",
            "party_size": 2,
            "hotel": {"name": "测试酒店"},
            "days": [{
                "day": 1,
                "date": "2026-09-18",
                "region": "市中心",
                "pois": [{
                    "idx": 1,
                    "name": "城市公园",
                    "time": "09:00",
                    "duration_min": 90,
                    "price": {"unit": "free"},
                }],
                "plan_b": {
                    "trigger": "持续降雨",
                    "alternative": "改去城市博物馆",
                    "impact": "午餐顺延 30 分钟",
                },
            }],
            "prebook": [{
                "item": "博物馆预约",
                "deadline": "前一天",
                "priority": "must",
                "status": "not_booked",
                "id_required": True,
            }],
            "safety_notes": [{
                "risk": "湿滑",
                "action": "穿防滑鞋",
                "severity": "warning",
            }],
            "rechecks": [{
                "item": "天气和闭馆通知",
                "status": "verified",
                "recheck_at": "2026-09-17",
            }],
        }

        rendered = render_trip_markdown(trip)

        for expected in (
            "# 雨天周末",
            "城市公园",
            "Plan B｜触发条件：持续降雨",
            "改去城市博物馆",
            "[必须｜待办理]",
            "需要实名/证件",
            "注意｜湿滑",
            "行前复核",
        ):
            self.assertIn(expected, rendered)

    def test_rejects_unsafe_markdown_link_scheme(self) -> None:
        trip = {
            "trip_name": "链接安全",
            "date_range": "2026-09-18",
            "city": "成都",
            "party_size": 1,
            "days": [],
            "prebook": [{
                "item": "不要执行",
                "url": "javascript:alert(1)",
                "priority": "optional",
                "status": "unknown",
            }],
        }
        rendered = render_trip_markdown(trip)
        self.assertNotIn("javascript:", rendered)
        self.assertIn("不要执行", rendered)


if __name__ == "__main__":
    unittest.main()
