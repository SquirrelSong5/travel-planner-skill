from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from render_html import inject_trip_data  # noqa: E402
from render_markdown import render_trip_markdown  # noqa: E402
from validate import check_v0, check_v5, check_v12  # noqa: E402


def recheck(category: str) -> dict:
    return {
        "item": f"{category} 复核",
        "category": category,
        "status": "verified",
        "checked_at": "2026-08-24T10:00:00+08:00",
        "recheck_at": "2026-10-01T09:00:00+08:00",
        "source": "official-site",
        "source_ref": "https://example.com/official",
    }


def source_coverage() -> list[dict]:
    stages = {
        "official": ["constraints", "recheck"],
        "amap": ["spatial", "recheck"],
        "ota": ["booking", "pricing"],
        "xiaohongshu": ["discovery", "experience"],
        "meituan": ["dining", "experience"],
    }
    return [
        {
            "platform": platform,
            "status": "used",
            "stages": platform_stages,
            "purpose": f"{platform} 场景证据",
            "checked_at": "2026-08-24T10:00:00+08:00",
            "source_refs": [f"https://example.com/{platform}"],
        }
        for platform, platform_stages in stages.items()
    ]


def base_trip(name: str) -> dict:
    return {
        "trip_name": name,
        "city": "成都",
        "date_range": "2026-10-02 — 2026-10-03",
        "party_size": 2,
        "hotel": {"name": "中心酒店", "lng": 104.06, "lat": 30.66},
        "days": [{
            "day": 1,
            "date": "2026-10-02",
            "region": "市中心",
            "center": [104.06, 30.66],
            "pois": [{
                "idx": 1,
                "name": "城市博物馆",
                "time": "09:00",
                "duration_min": 120,
                "lng": 104.061,
                "lat": 30.661,
            }],
            "transports": [],
        }],
        "prebook": [],
        "source_coverage": source_coverage(),
        "safety_notes": [{
            "risk": "人流拥挤",
            "action": "错峰出行并保留集合点",
            "severity": "warning",
            "applies_to": "全体同行人",
            "source": "official-site",
            "source_ref": "https://example.com/official",
            "checked_at": "2026-08-24T10:00:00+08:00",
        }],
        "rechecks": [recheck(category) for category in ("opening", "transport", "price", "safety")],
    }


class TravelScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = (ROOT / "assets" / "template.html").read_text(encoding="utf-8")

    def assert_scenario(self, trip: dict, expected: str) -> str:
        self.assertEqual(check_v0(trip)["status"], "✅")
        self.assertEqual(check_v12(trip, as_of=date(2026, 8, 24))["status"], "✅")
        markdown = render_trip_markdown(trip)
        self.assertIn(expected, markdown)

        html = inject_trip_data(self.template, trip)
        start = html.index("window.tripData = ") + len("window.tripData = ")
        end = html.index(";", start)
        self.assertEqual(json.loads(html[start:end]), trip)
        return markdown

    def test_rainy_weekend_has_decision_ready_plan_b(self) -> None:
        trip = base_trip("雨天周末")
        trip["weather_plan"] = "出发前一天根据雷电预警决定是否切换。"
        trip["rechecks"].append(recheck("weather"))
        trip["days"][0]["pois"][0].update({
            "name": "人民公园",
            "weather_sensitive": True,
            "indoor_backup": "成都博物馆",
        })
        trip["days"][0]["plan_b"] = {
            "trigger": "持续降雨或雷电预警",
            "alternative": "改去成都博物馆",
            "impact": "取消户外茶歇，午餐顺延 30 分钟",
        }
        self.assert_scenario(trip, "Plan B｜触发条件：持续降雨或雷电预警")

    def test_elderly_trip_surfaces_specific_safety_action(self) -> None:
        trip = base_trip("老人同行慢游")
        trip["safety_notes"][0].update({
            "risk": "连续步行与久站",
            "action": "每 90 分钟安排坐席休息，不排队超过 30 分钟",
            "applies_to": "老人",
        })
        markdown = self.assert_scenario(trip, "老人")
        self.assertIn("每 90 分钟安排坐席休息", markdown)

    def test_late_arrival_keeps_last_mile_visible(self) -> None:
        trip = base_trip("深夜抵达")
        trip["days"][0]["pois"][0].update({
            "name": "双流机场 T2",
            "time": "23:00",
            "lng": 103.947,
            "lat": 30.5785,
        })
        trip["days"][0]["transports"] = [{
            "from_idx": 1,
            "to_idx": 0,
            "mode": "taxi",
            "duration_min": 45,
            "source": "amap-mcp",
        }]
        trip["safety_notes"][0].update({
            "risk": "深夜公共交通班次不足",
            "action": "落地后直接走官方出租车排队区，不接受揽客车辆",
        })
        markdown = self.assert_scenario(trip, "双流机场 T2 → 中心酒店")
        self.assertIn("官方出租车排队区", markdown)

    def test_holiday_return_tracks_booking_and_buffer(self) -> None:
        trip = base_trip("节假日返程")
        trip["prebook"] = [{
            "item": "国内机票（成都 → 返程）",
            "depart_time": "18:00",
            "deadline": "出发前 2 周",
            "priority": "must",
            "status": "not_booked",
            "id_required": True,
            "url": "https://flights.ctrip.com/",
        }]
        trip["rechecks"].append(recheck("booking"))
        trip["days"][0]["pois"][0].update({"name": "机场", "time": "15:00"})
        markdown = self.assert_scenario(trip, "[必须｜待办理]")
        self.assertEqual(check_v5(trip["days"][0], trip)["buffer_hours"], 3.0)
        self.assertIn("需要实名/证件", markdown)


if __name__ == "__main__":
    unittest.main()
