#!/usr/bin/env python3
"""行程文件命名：{城市拼音}-{出发日 YYYY-MM-DD}，如 chengdu-2026-09-18。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# 常见目的地拼音（小写）；未知城市请在 trip JSON 里写 trip_slug
CITY_PINYIN: dict[str, str] = {
    "成都": "chengdu",
    "厦门": "xiamen",
    "青岛": "qingdao",
    "北京": "beijing",
    "上海": "shanghai",
    "杭州": "hangzhou",
    "西安": "xian",
    "重庆": "chongqing",
    "南京": "nanjing",
    "苏州": "suzhou",
    "广州": "guangzhou",
    "深圳": "shenzhen",
    "大理": "dali",
    "丽江": "lijiang",
    "昆明": "kunming",
    "三亚": "sanya",
    "哈尔滨": "haerbin",
    "大连": "dalian",
    "武汉": "wuhan",
    "长沙": "changsha",
    "福州": "fuzhou",
    "泉州": "quanzhou",
    "桂林": "guilin",
    "贵阳": "guiyang",
    "拉萨": "lasa",
    "乌鲁木齐": "wulumuqi",
    "香港": "hongkong",
    "澳门": "macau",
    "台北": "taipei",
    "东京": "tokyo",
    "大阪": "osaka",
    "京都": "kyoto",
    "首尔": "seoul",
    "曼谷": "bangkok",
    "新加坡": "singapore",
}


def departure_date(trip: dict) -> str:
    """出发日：Day 1 的 date，或从 date_range 解析首个 YYYY-MM-DD。"""
    days = trip.get("days") or []
    if days and days[0].get("date"):
        return str(days[0]["date"]).strip()[:10]
    m = re.search(r"(\d{4}-\d{2}-\d{2})", trip.get("date_range") or "")
    if m:
        return m.group(1)
    raise ValueError("无法解析出发日：请设置 days[0].date 或 date_range")


def city_slug(city: str) -> str:
    city = (city or "").strip()
    if not city:
        raise ValueError("trip.city 为空")
    if city in CITY_PINYIN:
        return CITY_PINYIN[city]
    if re.match(r"^[A-Za-z]", city):
        s = re.sub(r"[^a-zA-Z0-9]+", "-", city).strip("-").lower()
        if s:
            return s
    raise ValueError(
        f"未知城市「{city}」：请在 JSON 顶层加 trip_slug（如 chengdu-2026-09-18），"
        f"或扩展 scripts/trip_slug.py 的 CITY_PINYIN"
    )


def trip_slug(trip: dict) -> str:
    """返回规范 basename：chengdu-2026-09-18。"""
    explicit = (trip.get("trip_slug") or "").strip()
    if explicit:
        if not re.fullmatch(r"[a-z0-9]+-\d{4}-\d{2}-\d{2}", explicit):
            raise ValueError(
                f"trip_slug 格式应为 city-YYYY-MM-DD，当前: {explicit!r}"
            )
        return explicit
    return f"{city_slug(trip.get('city', ''))}-{departure_date(trip)}"


def trip_paths(trip: dict, directory: Path | str) -> tuple[Path, Path]:
    """返回 (json_path, html_path)。"""
    d = Path(directory)
    base = trip_slug(trip)
    return d / f"{base}.json", d / f"{base}.html"


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python scripts/trip_slug.py trip.json [workdir]", file=sys.stderr)
        return 2
    trip = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    slug = trip_slug(trip)
    print(slug)
    if len(sys.argv) >= 3:
        jp, hp = trip_paths(trip, sys.argv[2])
        print(jp)
        print(hp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
