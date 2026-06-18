#!/usr/bin/env python3
"""Smoke-test day-route URL generation (no browser)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

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
    if hotel_name and (re.search(r"^酒店\b", raw) or "退房" in raw or "入住" in raw):
        return hotel_name
    s = re.sub(r"^抵达", "", raw)
    s = re.sub(r"\s*[\|｜].*$", "", s)
    s = re.sub(r"\s*[（(][^）)]*[）)]\s*$", "", s)
    s = re.sub(r"\s*(?:办理)?(?:入住|退房).*$", "", s, flags=re.I)
    s = re.sub(r"(?:午餐|晚餐|早饭|午饭|晚饭|早餐)$", "", s, flags=re.I)
    return (s or raw).strip()


def same_coords(a, b) -> bool:
    ca, cb = poi_coords(a), poi_coords(b)
    if not ca or not cb:
        return False
    return abs(ca["lng"] - cb["lng"]) < 1e-5 and abs(ca["lat"] - cb["lat"]) < 1e-5


def is_activity_only_route_stop(p) -> bool:
    if p.get("nav_name") or p.get("place_name"):
        return False
    if p.get("cat") == "hotel":
        return False
    raw = str(p.get("name") or "").strip()
    if not raw:
        return True
    if re.search(r"^(?:出发去|前往|赶往|转场|出发)", raw):
        return True
    if re.search(r"(?:退房|入住|取行李)", raw):
        return True
    if re.search(r"\+\s*出发", raw):
        return True
    return False


def is_stale_arrival_poi(p, day: dict) -> bool:
    if (day.get("day") or 1) <= 1:
        return False
    if p.get("nav_name") or p.get("place_name"):
        return False
    return p.get("cat") == "transport" and str(p.get("name") or "").strip().startswith("抵达")


def first_poi_by_idx(day: dict):
    pois = sorted(day.get("pois") or [], key=lambda p: p["idx"])
    return pois[0] if pois else None


def first_poi_skips_morning(day: dict, hotel_name: str) -> bool:
    p = first_poi_by_idx(day)
    if not p:
        return True
    if p.get("cat") == "hotel" or (hotel_name and p.get("name") == hotel_name):
        return True
    if day.get("day") != 1:
        return False
    if p.get("cat") == "transport":
        return True
    return bool(re.search(r"机场|火车站|高铁站|(?:汽车)?车站|码头|港口", p.get("name") or ""))


def day_starts_from_hotel(day: dict, hotel_name: str) -> bool:
    if first_poi_skips_morning(day, hotel_name):
        return False
    return any(t.get("from_idx") == 0 for t in day.get("transports") or [])


def is_hotel_stop(p, hotel_name: str, hotel_pt: dict | None) -> bool:
    if not p:
        return False
    if p.get("idx") == 0 or p.get("cat") == "hotel":
        return True
    if hotel_name and p.get("name") == hotel_name:
        return True
    return bool(hotel_pt and same_coords(p, hotel_pt))


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

    pois = [
        p
        for p in sorted(day.get("pois") or [], key=lambda p: p["idx"])
        if poi_coords(p) and not is_activity_only_route_stop(p) and not is_stale_arrival_poi(p, day)
    ]
    if not pois:
        return None

    ordered = []

    def push(p):
        if not p or not poi_coords(p):
            return
        if ordered:
            last = ordered[-1]
            if same_coords(p, last):
                return
            if is_hotel_stop(p, hotel_name, hotel_pt) and is_hotel_stop(last, hotel_name, hotel_pt):
                return
        ordered.append(p)

    if day_starts_from_hotel(day, hotel_name) and hotel_pt:
        push(hotel_pt)
    elif first_poi_skips_morning(day, hotel_name) and (
        first_poi_by_idx(day) or {}).get("cat") == "hotel":
        push(hotel_pt or pois[0])

    for p in pois:
        if is_hotel_stop(p, hotel_name, hotel_pt) and any(
            is_hotel_stop(q, hotel_name, hotel_pt) and same_coords(p, q) for q in ordered
        ):
            continue
        push(p)

    if len(ordered) < 2:
        return None

    start, end = ordered[0], ordered[-1]
    vias = [p for p in ordered[1:-1] if not same_coords(p, start) and not same_coords(p, end)]
    if same_coords(start, end):
        if not vias:
            return None
        end = vias.pop()
    while vias and same_coords(end, vias[-1]):
        vias.pop()
    if same_coords(start, end):
        return None
    return {"start": start, "vias": vias, "end": end}


def encode_amap_nav_name(name: str) -> str:
    return quote(name or "地点", safe="").replace("%28", "(").replace("%29", ")")


def mobile_url(start, vias, end, hotel_name: str) -> str | None:
    def pt(p):
        c = poi_coords(p)
        return f"{c['lng']},{c['lat']},{encode_amap_nav_name(navi_place_name(p, hotel_name) or '地点')}"

    saddr, daddr = pt(start), pt(end)
    parts = [f"saddr={saddr}", f"daddr={daddr}", "sort=dist"]
    if len(vias) == 1:
        parts.append(f"maddr={pt(vias[0])}")
    elif len(vias) > 1:
        return None
    return f"https://m.amap.com/navigation/carmap/{'&'.join(parts)}"


def native_url(start, vias, end, hotel_name: str, platform: str = "ios") -> str:
    def pt(p):
        c = poi_coords(p)
        return {
            "lat": c["lat"],
            "lon": c["lng"],
            "name": navi_place_name(p, hotel_name) or "地点",
        }

    s, e = pt(start), pt(end)
    common = (
        f"sourceApplication={quote('travel-planner', safe='')}"
        f"&sid=&slat={s['lat']}&slon={s['lon']}&sname={quote(s['name'], safe='')}"
        f"&did=&dlat={e['lat']}&dlon={e['lon']}&dname={quote(e['name'], safe='')}"
        "&dev=0&t=0"
    )
    if vias:
        via_pts = [pt(v) for v in vias]
        common += (
            f"&vian={len(via_pts)}"
            f"&vialons={'|'.join(str(v['lon']) for v in via_pts)}"
            f"&vialats={'|'.join(str(v['lat']) for v in via_pts)}"
            f"&vianames={'|'.join(quote(v['name'], safe='') for v in via_pts)}"
        )
    if platform == "android":
        return f"amapuri://route/plan/?{common}"
    return f"iosamap://path?{common}"


def dir_url(start, vias, end, hotel_name: str) -> str:
    ts = 1_781_792_351_000

    def endpoint(role, p, eid):
        c = poi_coords(p)
        name = quote(navi_place_name(p, hotel_name) or "地点", safe="")
        return f"{role}[lnglat]={c['lng']},{c['lat']}&{role}[name]={name}&{role}[id]={eid}"

    def via_pt(p, index):
        c = poi_coords(p)
        name = quote(navi_place_name(p, hotel_name) or "地点", safe="")
        return f"via[{index}][lnglat]={c['lng']},{c['lat']}&via[{index}][name]={name}"

    q = (
        [endpoint("from", start, f"{ts}-from"), endpoint("to", end, f"{ts}-to")]
        + [via_pt(v, i) for i, v in enumerate(vias)]
        + ["type=car", "src=uriapi", "innersrc=uriapi", "policy=1"]
    )
    return f"https://ditu.amap.com/dir?{'&'.join(q)}"


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
            stops = [route["start"], *route["vias"], route["end"]]
            names = [navi_place_name(p, hotel_name) for p in stops]
            issues = []
            if same_coords(route["start"], route["end"]):
                issues.append("SAME_START_END")
            if len(set(names)) < len([n for n in names if hotel_name in n or n == "酒店"]) and names.count(hotel_name) > 1:
                issues.append("DUP_HOTEL")
            if any(re.search(r"^(?:出发去|前往|退房)", n) for n in names):
                issues.append("ACTIVITY_NAME")
            desktop = dir_url(route["start"], route["vias"], route["end"], hotel_name)
            if len(route["vias"]) > 1 and "via[1]" not in desktop:
                issues.append("MISSING_MULTI_VIA")
            mobile = mobile_url(route["start"], route["vias"], route["end"], hotel_name)
            if len(route["vias"]) <= 1 and not (mobile or "").startswith("https://m.amap.com/"):
                issues.append("BAD_MOBILE")
            if len(route["vias"]) > 1:
                ios = native_url(route["start"], route["vias"], route["end"], hotel_name, "ios")
                if f"vian={len(route['vias'])}" not in ios:
                    issues.append("BAD_VIAN")
                if "%7C" in ios.split("vianames=")[-1]:
                    issues.append("VIANAMES_PIPE_ENCODED")
            status = "OK" if not issues else "FAIL " + ",".join(issues)
            if issues:
                failed += 1
            print(
                f"  Day {day['day']}: {status} stops={len(stops)} "
                f"names={' → '.join(n[:12] for n in names)}"
            )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
