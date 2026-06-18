#!/usr/bin/env python3
"""Smoke-test day-route URL generation (no browser)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote, urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]


def poi_coords(p):
    lng, lat = p.get("lng"), p.get("lat")
    if lng is None or lat is None:
        return None
    return {"lng": lng, "lat": lat}


def navi_place_name(p, hotel_name: str) -> str:
    if p.get("nav_name"):
        return str(p["nav_name"]).strip()
    if p.get("place_name"):
        return str(p["place_name"]).strip()
    raw = str(p.get("name") or "").strip()
    if p.get("idx") == 0 or p.get("cat") == "hotel":
        return hotel_name or raw or "酒店"
    if hotel_name and (raw == hotel_name or raw.startswith(hotel_name)):
        return hotel_name
    s = re.sub(r"\s*[\|｜].*$", "", raw)
    s = re.sub(r"\s*[（(][^）)]*[）)]\s*$", "", s)
    s = re.sub(r"\s*(?:办理)?(?:入住|退房).*$", "", s, flags=re.I)
    return (s or raw).strip()


def same_coords(a, b) -> bool:
    ca, cb = poi_coords(a), poi_coords(b)
    if not ca or not cb:
        return False
    return abs(ca["lng"] - cb["lng"]) < 1e-5 and abs(ca["lat"] - cb["lat"]) < 1e-5


def collect_and_finalize(trip: dict, day: dict):
    hotel_info = trip.get("hotel") or {}
    hotel_name = hotel_info.get("name", "")
    hotel_pt = None
    if hotel_info.get("lng") is not None and hotel_info.get("lat") is not None:
        hotel_pt = {
            "idx": 0,
            "name": hotel_name or "酒店",
            "lng": hotel_info["lng"],
            "lat": hotel_info["lat"],
            "cat": "hotel",
        }
    pois = sorted([p for p in day.get("pois", []) if poi_coords(p)], key=lambda p: p["idx"])
    if not pois:
        return None

    def first_poi_is_hotel():
        p = pois[0]
        return p.get("cat") == "hotel" or (hotel_name and p.get("name") == hotel_name)

    def last_poi_is_departure():
        last = pois[-1]
        if last.get("cat") == "transport":
            return True
        return bool(re.search(r"机场|火车站|高铁站|(?:汽车)?车站|码头|港口", last.get("name") or ""))

    def first_poi_skips_morning():
        if first_poi_is_hotel():
            return True
        if day.get("day") != 1:
            return False
        p = pois[0]
        if p.get("cat") == "transport":
            return True
        return bool(re.search(r"机场|火车站|高铁站|(?:汽车)?车站|码头|港口", p.get("name") or ""))

    def find_hotel_leg(kind: str):
        ts = day.get("transports") or []
        if kind == "morning":
            return next((t for t in ts if t.get("from_idx") == 0 and t.get("to_idx") == pois[0]["idx"]), None)
        if kind == "evening":
            if last_poi_is_departure():
                return None
            last = pois[-1]
            return next((t for t in ts if t.get("from_idx") == last["idx"] and t.get("to_idx") == 0), None)
        return None

    ordered = []

    def push(p):
        if not p or not poi_coords(p):
            return
        if ordered and same_coords(p, ordered[-1]):
            return
        ordered.append(p)

    if not first_poi_skips_morning() and find_hotel_leg("morning") and hotel_pt:
        push(hotel_pt)
    elif first_poi_skips_morning() and first_poi_is_hotel():
        push(hotel_pt or pois[0])
    for p in pois:
        if (
            first_poi_skips_morning()
            and first_poi_is_hotel()
            and (p.get("cat") == "hotel" or (hotel_name and p.get("name") == hotel_name))
            and ordered
            and same_coords(p, ordered[0])
        ):
            continue
        push(p)
    if not last_poi_is_departure() and find_hotel_leg("evening") and hotel_pt:
        push(hotel_pt)
    if len(ordered) < 2:
        return None

    start, end = ordered[0], ordered[-1]
    vias = ordered[1:-1]
    if same_coords(start, end):
        if not vias:
            return None
        end = vias.pop()
    while vias and same_coords(end, vias[-1]):
        vias.pop()
    if same_coords(start, end):
        return None
    return {"start": start, "vias": vias, "end": end}


def web_url(start, vias, end, hotel_name: str, desktop: bool = True) -> str:
    def pos(p):
        c = poi_coords(p)
        name = quote(navi_place_name(p, hotel_name) or "地点", safe="")
        return f"{c['lng']},{c['lat']},{name}"

    url = f"https://uri.amap.com/navigation?from={pos(start)}&to={pos(end)}&mode=car"
    if not desktop:
        url += "&callnative=1"
    if len(vias) == 1:
        url += f"&via={pos(vias[0])}"
    return url


def main() -> int:
    files = [
        Path.home() / ".travel-planner/travel-plans/qingdao-2026-06-25.json",
        Path.home() / ".travel-planner/travel-plans/xiamen-2026-06-25.json",
    ]
    failed = 0
    for path in files:
        trip = json.loads(path.read_text(encoding="utf-8"))
        hotel_name = (trip.get("hotel") or {}).get("name", "")
        print(path.name)
        for day in trip["days"]:
            route = collect_and_finalize(trip, day)
            if not route:
                print(f"  Day {day['day']}: skip (no route)")
                continue
            same = same_coords(route["start"], route["end"])
            url = web_url(route["start"], route["vias"], route["end"], hotel_name)
            has_via = "via=" in url
            q = parse_qs(urlparse(url).query)
            issues = []
            if same:
                issues.append("SAME_START_END")
            if len(route["vias"]) > 1 and has_via:
                issues.append("MULTI_VIA_ON_WEB")
            if "%7C" in q.get("via", [""])[0]:
                issues.append("BAD_VIA_ENCODING")
            status = "OK" if not issues else "FAIL " + ",".join(issues)
            if issues:
                failed += 1
            print(
                f"  Day {day['day']}: {status} vias={len(route['vias'])} "
                f"start={navi_place_name(route['start'], hotel_name)[:16]} "
                f"end={navi_place_name(route['end'], hotel_name)[:16]}"
            )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
