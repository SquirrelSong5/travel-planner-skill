#!/usr/bin/env python3
"""为 trip JSON 补酒店早晚通勤段（from_idx/to_idx=0），高德 REST 拉 polyline。"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

_DEPARTURE_RE = re.compile(r"机场|火车站|高铁站|(?:汽车)?车站|码头|港口")


def load_amap_key() -> str:
    env = __import__("os").environ.get("AMAP_MCP_KEY") or __import__("os").environ.get("MCP_AMAP_API_KEY")
    if env:
        return env.strip()
    cfg = Path.home() / ".travel-planner" / "config"
    if cfg.exists():
        for line in cfg.read_text().splitlines():
            if line.startswith("AMAP_MCP_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("未找到 AMAP_MCP_KEY")


def get_loc(obj: dict[str, Any] | None) -> tuple[float, float] | None:
    if not obj:
        return None
    if obj.get("lng") is not None and obj.get("lat") is not None:
        return float(obj["lng"]), float(obj["lat"])
    loc = obj.get("location")
    if isinstance(loc, list) and len(loc) >= 2:
        return float(loc[0]), float(loc[1])
    return None


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 6371000.0
    lat1, lon1 = math.radians(a[1]), math.radians(a[0])
    lat2, lon2 = math.radians(b[1]), math.radians(b[0])
    dlat, dlng = lat2 - lat1, lon2 - lon1
    x = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def parse_polyline_str(s: str) -> list[list[float]]:
    out: list[list[float]] = []
    for pair in (s or "").split(";"):
        pair = pair.strip()
        if not pair or "," not in pair:
            continue
        lng, lat = pair.split(",", 1)
        out.append([float(lng), float(lat)])
    return out


def extract_walking_polyline(route_json: dict) -> list[list[float]]:
    points: list[list[float]] = []
    for step in route_json.get("route", {}).get("paths", [{}])[0].get("steps", []):
        raw = step.get("polyline") or step.get("path") or ""
        points.extend(parse_polyline_str(raw))
    return points


def extract_transit_polyline(route_json: dict) -> list[list[float]]:
    points: list[list[float]] = []
    segs = route_json.get("route", {}).get("transits", [{}])[0].get("segments", [])
    for seg in segs:
        for key in ("walking", "bus", "railway"):
            block = seg.get(key) or {}
            raw = block.get("polyline") or block.get("path") or ""
            points.extend(parse_polyline_str(raw))
    return points


def pick_mode(dist_m: float, hint: str) -> str:
    if dist_m < 1500:
        return "walking"
    h = (hint or "").lower()
    if "步行" in hint or "walk" in h:
        return "walking"
    if "骑行" in hint or "bike" in h or "bicycling" in h or "ride" in h:
        return "biking"
    if "打车" in hint or "驾车" in hint or "taxi" in h or "drive" in h:
        return "driving"
    if "地铁" in hint or "公交" in hint or "transit" in h:
        return "transit"
    if dist_m < 4000:
        return "biking"
    if dist_m < 25000:
        return "transit"
    return "driving"


def amap_direction(
    key: str,
    mode: str,
    origin: tuple[float, float],
    dest: tuple[float, float],
    city: str,
) -> dict[str, Any]:
    modes_try = [mode]
    for m in ("walking", "biking", "transit", "driving"):
        if m not in modes_try:
            modes_try.append(m)
    last_err: Exception | None = None
    for try_mode in modes_try:
        try:
            return _fetch_direction(key, try_mode, origin, dest, city)
        except Exception as e:
            last_err = e
    raise RuntimeError(f"高德无路线: {origin} -> {dest}: {last_err}")


def _fetch_direction(
    key: str,
    mode: str,
    origin: tuple[float, float],
    dest: tuple[float, float],
    city: str,
) -> dict[str, Any]:
    o = f"{origin[0]},{origin[1]}"
    d = f"{dest[0]},{dest[1]}"
    if mode == "transit":
        url = (
            f"https://restapi.amap.com/v3/direction/transit/integrated"
            f"?key={key}&origin={o}&destination={d}&city={urllib.parse.quote(city)}"
        )
        rest = json.loads(urllib.request.urlopen(url, timeout=20).read())
        transits = rest.get("route", {}).get("transits") or []
        if not transits:
            raise RuntimeError(f"无公交方案: {o} -> {d}")
        t0 = transits[0]
        duration_min = max(1, int(int(t0.get("duration", 0)) / 60))
        distance_m = int(t0.get("distance", 0))
        path = extract_transit_polyline(rest)
        cost = float(t0.get("cost", 0) or 0)
        return {
            "mode": "transit",
            "duration_min": duration_min,
            "distance_m": distance_m,
            "path": path,
            "source": "amap-rest-api",
            "fare_per_person": cost if cost > 0 else 3.0,
        }
    endpoint = {
        "walking": "walking",
        "driving": "driving",
        "biking": "bicycling",
    }.get(mode, "driving")
    url = f"https://restapi.amap.com/v3/direction/{endpoint}?key={key}&origin={o}&destination={d}"
    rest = json.loads(urllib.request.urlopen(url, timeout=20).read())
    paths = rest.get("route", {}).get("paths") or []
    if not paths:
        raise RuntimeError(f"高德无路线: {mode} {o} -> {d}")
    p0 = paths[0]
    duration_min = max(1, int(int(p0.get("duration", 0)) / 60))
    distance_m = int(p0.get("distance", 0))
    path = extract_walking_polyline(rest)
    taxi = p0.get("taxi_cost")
    fare_fixed = float(taxi) if taxi else 0.0
    return {
        "mode": mode if mode != "biking" else "biking",
        "duration_min": duration_min,
        "distance_m": distance_m,
        "path": path,
        "source": "amap-rest-api",
        "fare_per_person": 0.0,
        "fare_fixed": fare_fixed,
    }


def build_fare(mode: str, party: int, route: dict[str, Any]) -> dict[str, Any]:
    if mode == "walking":
        return {
            "min": 0.0, "max": 0.0, "currency": "CNY", "unit": "free", "quantity": 1,
            "total_min": 0.0, "total_max": 0.0, "label": "步行",
            "source": "computed", "source_ref": "零元交通",
        }
    if mode in ("transit", "subway", "bus", "metro"):
        pp = route.get("fare_per_person", 3.0)
        return {
            "min": pp, "max": pp + 3, "currency": "CNY", "unit": "per_person",
            "quantity": party, "total_min": pp * party, "total_max": (pp + 3) * party,
            "label": "公交/地铁", "source": "amap-rest-api",
            "source_ref": "direction/transit cost",
        }
    fixed = route.get("fare_fixed") or 25.0
    return {
        "min": fixed, "max": fixed + 15, "currency": "CNY", "unit": "fixed", "quantity": 1,
        "total_min": fixed, "total_max": fixed + 15, "label": "打车",
        "source": "amap-rest-api", "source_ref": "direction/driving taxi_cost",
    }


def first_skips_morning(pois: list[Any], trip: dict[str, Any], day_num: int) -> bool:
    if not pois:
        return True
    first = pois[0]
    hotel_name = (trip.get("hotel") or {}).get("name")
    if first.get("cat") == "hotel" or (hotel_name and first.get("name") == hotel_name):
        return True
    if day_num != 1:
        return False
    if first.get("cat") == "transport":
        return True
    return bool(_DEPARTURE_RE.search(first.get("name") or ""))


def last_skips_evening(last: dict[str, Any]) -> bool:
    if last.get("cat") == "transport":
        return True
    return bool(_DEPARTURE_RE.search(last.get("name") or ""))


def commute_hint(trip: dict[str, Any], day_num: int) -> str:
    for c in (trip.get("hotel") or {}).get("commute") or []:
        if c.get("day") == day_num:
            return c.get("mode") or ""
    return ""


def leg_description(kind: str, mode: str, duration: int, from_name: str, to_name: str) -> str:
    mode_zh = {"walking": "步行", "transit": "公交/地铁", "driving": "打车", "biking": "骑行"}.get(mode, mode)
    if kind == "morning":
        return f"{mode_zh} 酒店 → {to_name}（约 {duration} 分钟）"
    return f"{mode_zh} {from_name} → 酒店（约 {duration} 分钟）"


def has_leg(transports: list[Any], from_idx: int, to_idx: int) -> bool:
    return any(
        isinstance(t, dict) and t.get("from_idx") == from_idx and t.get("to_idx") == to_idx
        for t in transports
    )


def finalize_route(
    key: str,
    route: dict[str, Any],
    origin: tuple[float, float],
    dest: tuple[float, float],
    city: str,
) -> dict[str, Any]:
    """步行过久改骑行/公交；缺 polyline 时用步行/驾车路网补 path（不改变已选 mode）。"""
    if route.get("mode") == "walking" and route.get("duration_min", 0) > 25:
        dist_m = haversine_m(origin, dest)
        next_mode = "biking" if dist_m < 4000 else "transit"
        try:
            route = amap_direction(key, next_mode, origin, dest, city)
        except Exception:
            if next_mode == "biking":
                try:
                    route = amap_direction(key, "transit", origin, dest, city)
                except Exception:
                    pass
    path = route.get("path") or []
    if len(path) < 3:
        try:
            walk = _fetch_direction(key, "walking", origin, dest, city)
            if len(walk.get("path") or []) >= 2:
                route["path"] = walk["path"]
                if route.get("source") == "amap-rest-api":
                    pass
        except Exception:
            pass
    if len(route.get("path") or []) < 3:
        drive = _fetch_direction(key, "driving", origin, dest, city)
        route["path"] = drive.get("path") or route.get("path")
    return route


def repair_hotel_legs(trip: dict[str, Any], key: str) -> int:
    hotel_loc = get_loc(trip.get("hotel"))
    if not hotel_loc:
        return 0
    city = trip.get("city") or ""
    party = int(trip.get("party_size") or 2)
    fixed = 0
    poi_by_idx_map: dict[int, dict] = {}

    for day in trip.get("days") or []:
        for p in day.get("pois") or []:
            if p.get("idx") is not None:
                poi_by_idx_map[p["idx"]] = p

        for t in day.get("transports") or []:
            if not isinstance(t, dict):
                continue
            if t.get("from_idx") != 0 and t.get("to_idx") != 0:
                continue
            fi, ti = t.get("from_idx"), t.get("to_idx")
            if fi == 0:
                dest_p = poi_by_idx_map.get(ti)
                origin, dest = hotel_loc, get_loc(dest_p)
                kind = "morning"
                to_name = (dest_p or {}).get("name", "")
                from_name = "酒店"
            else:
                src_p = poi_by_idx_map.get(fi)
                origin, dest = get_loc(src_p), hotel_loc
                kind = "evening"
                from_name = (src_p or {}).get("name", "")
                to_name = "酒店"
            if not origin or not dest:
                continue
            path_len = len(t.get("path") or [])
            bad = path_len < 3 or (t.get("mode") == "walking" and t.get("duration_min", 0) > 30)
            if not bad:
                continue
            dist = haversine_m(origin, dest)
            hint = commute_hint(trip, day.get("day", 0))
            mode = pick_mode(dist, hint)
            route = finalize_route(key, amap_direction(key, mode, origin, dest, city), origin, dest, city)
            t.update({
                "mode": route["mode"],
                "duration_min": route["duration_min"],
                "description": leg_description(kind, route["mode"], route["duration_min"], from_name, to_name),
                "distance_m": route["distance_m"],
                "path": route["path"],
                "source": route["source"],
                "fare": build_fare(route["mode"], party, route),
            })
            fixed += 1
    return fixed


def add_legs(trip: dict[str, Any], key: str) -> int:
    hotel = trip.get("hotel") or {}
    hotel_loc = get_loc(hotel)
    if not hotel_loc:
        raise SystemExit("trip.hotel 缺坐标")
    city = trip.get("city") or ""
    party = int(trip.get("party_size") or 2)
    added = 0

    for day in trip.get("days") or []:
        pois = day.get("pois") or []
        if not pois:
            continue
        day_num = day.get("day", 0)
        transports: list[Any] = list(day.get("transports") or [])
        first, last = pois[0], pois[-1]
        fi, li = first.get("idx"), last.get("idx")
        first_loc = get_loc(first)
        last_loc = get_loc(last)
        hint = commute_hint(trip, day_num)

        if not first_skips_morning(pois, trip, day_num) and fi is not None and first_loc and not has_leg(transports, 0, fi):
            dist = haversine_m(hotel_loc, first_loc)
            mode = pick_mode(dist, hint)
            route = finalize_route(key, amap_direction(key, mode, hotel_loc, first_loc, city), hotel_loc, first_loc, city)
            transports.insert(0, {
                "from_idx": 0,
                "to_idx": fi,
                "mode": route["mode"],
                "duration_min": route["duration_min"],
                "description": leg_description("morning", route["mode"], route["duration_min"], "酒店", first.get("name", "")),
                "distance_m": route["distance_m"],
                "path": route["path"],
                "source": route["source"],
                "fare": build_fare(route["mode"], party, route),
            })
            added += 1

        if not last_skips_evening(last) and li is not None and last_loc and not has_leg(transports, li, 0):
            dist = haversine_m(last_loc, hotel_loc)
            mode = pick_mode(dist, hint)
            route = finalize_route(key, amap_direction(key, mode, last_loc, hotel_loc, city), last_loc, hotel_loc, city)
            transports.append({
                "from_idx": li,
                "to_idx": 0,
                "mode": route["mode"],
                "duration_min": route["duration_min"],
                "description": leg_description("evening", route["mode"], route["duration_min"], last.get("name", ""), "酒店"),
                "distance_m": route["distance_m"],
                "path": route["path"],
                "source": route["source"],
                "fare": build_fare(route["mode"], party, route),
            })
            added += 1

        day["transports"] = transports

    return added


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("trip_json", type=Path)
    ap.add_argument("--in-place", action="store_true")
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--repair", action="store_true", help="修复已有酒店段 path/时长")
    args = ap.parse_args()
    key = load_amap_key()
    trip = json.loads(args.trip_json.read_text(encoding="utf-8"))
    n = add_legs(trip, key)
    if args.repair:
        n += repair_hotel_legs(trip, key)
    out = args.trip_json if args.in_place else (args.output or args.trip_json)
    out.write_text(json.dumps(trip, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✅ {args.trip_json.name}: 新增 {n} 段酒店通勤 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
