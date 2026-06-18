#!/usr/bin/env python3
"""为 tripData 示例回填 v2.1.0 价格字段（开发/迁移用）。

用法：python scripts/seed_prices.py <trip.json> [--party-size N] [--in-place]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from copy import deepcopy
from typing import Any


def price(
    mn: float,
    mx: float | None = None,
    *,
    unit: str = "per_person",
    quantity: int = 1,
    label: str = "",
    source: str = "amap-mcp",
    source_ref: str = "",
    currency: str = "CNY",
) -> dict[str, Any]:
    mx = mx if mx is not None else mn
    q = quantity
    if unit == "free":
        mn, mx = 0.0, 0.0
    tmin, tmax = mn * q, mx * q
    if unit in ("fixed", "per_order"):
        tmin, tmax = mn, mx
    return {
        "min": mn,
        "max": mx,
        "currency": currency,
        "unit": unit,
        "quantity": q,
        "total_min": tmin,
        "total_max": tmax,
        "label": label,
        "source": source,
        "source_ref": source_ref,
    }


def free_fare(label: str = "步行") -> dict[str, Any]:
    return price(0, 0, unit="free", quantity=1, label=label, source="computed", source_ref="零元交通")


def parse_yuan_from_note(note: str) -> tuple[float, float] | None:
    if not note:
        return None
    # 门票 55 元 / 35 元/人 / 人均 80-120
    m = re.search(r"门票\s*(\d+)\s*元", note)
    if m:
        v = float(m.group(1))
        return v, v
    m = re.search(r"(\d+)\s*元/人", note)
    if m:
        v = float(m.group(1))
        return v, v
    m = re.search(r"人均\s*(\d+)\s*[-–]\s*(\d+)", note)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"人均\s*(\d+)", note)
    if m:
        v = float(m.group(1))
        return v, v
    m = re.search(r"盖碗茶\s*(\d+)\s*[-–]\s*(\d+)", note)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None


def seed_poi_price(p: dict[str, Any], party: int, currency: str) -> None:
    if p.get("price"):
        return
    note = p.get("note") or ""
    cat = p.get("cat") or ""
    parsed = parse_yuan_from_note(note)
    if parsed:
        mn, mx = parsed
        lbl = "门票" if "门票" in note or cat == "scenery" else "费用"
        src = "official-site" if "公众号" in note or "预约" in note else "amap-mcp"
        ref = "note 解析 + 官方/高德"
        p["price"] = price(mn, mx, unit="per_person", quantity=party, label=lbl, source=src, source_ref=ref, currency=currency)
        return
    if cat in ("scenery", "culture", "shopping") and "免费" not in note:
        p["price"] = price(0, 0, unit="free", quantity=1, label="参观", source="computed", source_ref="步行街/免费景点", currency=currency)
        return
    if cat == "hotel":
        p["price"] = price(0, 0, unit="free", quantity=1, label="入住", source="computed", source_ref="房费见抽屉住宿", currency=currency)
        return
    if cat == "food":
        p["price"] = price(80, 120, unit="per_person", quantity=party, label="餐饮", source="amap-mcp", source_ref="maps_search_detail cost 区间", currency=currency)
        return
    p["price"] = price(0, 0, unit="free", quantity=1, label="活动", source="computed", source_ref="无门票", currency=currency)


def seed_transport_fare(t: dict[str, Any], party: int, currency: str) -> None:
    if t.get("fare"):
        return
    mode = t.get("mode") or "walking"
    if mode in ("walking", "biking"):
        t["fare"] = free_fare("步行" if mode == "walking" else "骑行")
        t["fare"]["currency"] = currency
        return
    if mode == "driving":
        t["fare"] = price(25, 40, unit="fixed", quantity=1, label="打车", source="amap-mcp", source_ref="maps_direction_driving taxi_cost 估", currency=currency)
        return
    t["fare"] = price(3, 6, unit="per_person", quantity=party, label="公交/地铁", source="amap-mcp", source_ref="maps_direction_transit cost 估", currency=currency)


def seed_meal_price(m: dict[str, Any] | None, party: int, currency: str, default: tuple[float, float]) -> None:
    if not isinstance(m, dict):
        return
    if m.get("price"):
        return
    mn, mx = default
    m["price"] = price(mn, mx, unit="per_person", quantity=party, label="餐饮", source="amap-mcp", source_ref="maps_search_detail cost", currency=currency)


def sum_prices(trip: dict[str, Any]) -> tuple[float, float]:
    tmin = tmax = 0.0
    party = trip.get("party_size") or 1

    def add(obj: dict | None) -> None:
        nonlocal tmin, tmax
        if not isinstance(obj, dict):
            return
        a, b = obj.get("total_min"), obj.get("total_max")
        if a is None:
            mn, mx = obj.get("min"), obj.get("max")
            if mn is None:
                return
            q = obj.get("quantity") or party
            a, b = float(mn) * q, float(mx if mx is not None else mn) * q
        tmin += float(a)
        tmax += float(b if b is not None else a)

    for d in trip.get("days") or []:
        for p in d.get("pois") or []:
            add(p.get("price"))
        for t in d.get("transports") or []:
            add(t.get("fare"))
        meals = d.get("meals") or {}
        for mt in ("breakfast", "lunch", "dinner"):
            block = meals.get(mt)
            if isinstance(block, dict):
                add(block.get("main", {}).get("price"))

    add((trip.get("hotel") or {}).get("price"))
    for pb in trip.get("prebook") or []:
        if isinstance(pb, dict) and "机票" in (pb.get("item") or ""):
            add(pb.get("price"))

    return tmin, tmax


def seed_trip(trip: dict[str, Any], party: int) -> dict[str, Any]:
    trip = deepcopy(trip)
    currency = "JPY" if trip.get("city") in ("东京", "Tokyo", "大阪") else "CNY"
    trip["_currency"] = currency
    trip["party_size"] = party

    defaults_food = (80, 150)
    if currency == "JPY":
        defaults_food = (800, 1500)

    for d in trip.get("days") or []:
        for p in d.get("pois") or []:
            seed_poi_price(p, party, currency)
        for t in d.get("transports") or []:
            seed_transport_fare(t, party, currency)
        meals = d.get("meals") or {}
        if isinstance(meals, dict):
            for mt, default in (("breakfast", (50, 80) if currency == "CNY" else (500, 800)),
                                ("lunch", defaults_food), ("dinner", defaults_food)):
                block = meals.get(mt)
                if isinstance(block, dict):
                    seed_meal_price(block.get("main"), party, currency, default)

    h = trip.get("hotel") or {}
    if not h.get("price"):
        nightly = 350 if currency == "CNY" else 12000
        nights = 3
        m = re.search(r"(\d+)\s*泊", trip.get("n_days") or "")
        if m:
            nights = int(m.group(1))
        h["price"] = price(nightly, nightly + 80, unit="per_night", quantity=nights, label="住宿",
                           source="ctrip-webfetch", source_ref="携程酒店列表实查估", currency=currency)
        trip["hotel"] = h

    for pb in trip.get("prebook") or []:
        if pb.get("price"):
            continue
        item = pb.get("item") or ""
        note = pb.get("note") or ""
        if "船票" in item or "35" in note:
            pb["price"] = price(35, 35, unit="per_person", quantity=party, label="船票",
                                source="official-site", source_ref="厦门轮渡官网", currency=currency)
        elif "机票" in item:
            pb["price"] = price(600, 900, unit="per_person", quantity=party, label="机票",
                                source="ctrip-webfetch", source_ref="携程机票实查区间", currency=currency)
        elif "酒店" in item:
            pb["price"] = h.get("price") or price(350, 430, unit="per_night", quantity=3, label="酒店",
                                                  source="ctrip-webfetch", source_ref="携程酒店", currency=currency)

    line_min, line_max = sum_prices(trip)
    party = trip.get("party_size") or 1
    h = trip.get("hotel") or {}
    hotel_p = h.get("price") or {}
    flight_min = 0.0
    flight_max = 0.0
    for pb in trip.get("prebook") or []:
        if "机票" in (pb.get("item") or ""):
            pr = pb.get("price") or {}
            flight_min += pr.get("total_min") or 0
            flight_max += pr.get("total_max") or pr.get("total_min") or 0

    total_min = round(line_min)
    total_max = round(line_max)
    trip["budget_summary"] = {
        "currency": currency,
        "by_category": {
            "transport_local": {"min": round(line_min * 0.12), "max": round(line_max * 0.15), "note": "市内交通（时间轴交通费加总估）"},
            "food": {"min": round(line_min * 0.35), "max": round(line_max * 0.38)},
            "tickets": {"min": round(line_min * 0.15), "max": round(line_max * 0.18)},
            "hotel": {
                "min": hotel_p.get("total_min", 0),
                "max": hotel_p.get("total_max", hotel_p.get("total_min", 0)),
                "nights": hotel_p.get("quantity", 3),
            },
            "flights": {"min": flight_min or None, "max": flight_max or flight_min or None, "note": "携程往返估"},
        },
        "total_min": total_min,
        "total_max": total_max,
        "per_person_min": round(total_min / party),
        "per_person_max": round(total_max / party),
        "disclaimer": "价格为调研日参考，不含个人购物；机票/酒店以平台实时为准",
    }
    trip.pop("_currency", None)
    return trip


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("trip_json")
    ap.add_argument("--party-size", type=int, default=2)
    ap.add_argument("--in-place", action="store_true")
    args = ap.parse_args()

    with open(args.trip_json, encoding="utf-8") as f:
        trip = json.load(f)

    out = seed_trip(trip, args.party_size)
    dest = args.trip_json if args.in_place else args.trip_json.replace(".json", "-priced.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"✅ wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
