#!/usr/bin/env python3
"""
travel-planner 自动验证脚本

用法：
    python scripts/validate.py <trip_data.json> [--round 1|2|3] [--check V1,V2,...] [--pretty]

行为：
    - 读 tripData JSON（与 examples/chengdu-2026-09-18.json 同 schema）
    - V0 校验核心 schema；V1-V13 检查可计算规则
    - --round 1=结构、2=时空、3=体验；V7 用户禁忌需人工判断
    - V8 校验路线来源声明与时长字段；V9 只拦快得不合理的时长
    - 输出 JSON validation_report（stdout）
    - 退出码：全通过 → 0；有失败 → 1；--fail-on-warn 可把警告也设为失败

注意：source 字段只能验证声明是否完整，不能证明外部查询真的发生过。
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urlparse


# ===== 字段兼容（POI 坐标可能叫 location / [lng,lat] / lng+lat） =====

def get_loc(p: dict[str, Any]) -> tuple[float, float] | None:
    """兼容多种坐标字段命名，返回 (lng, lat) 或 None。"""
    if not isinstance(p, dict):
        return None
    loc = p.get("location")
    if isinstance(loc, (list, tuple)) and len(loc) >= 2:
        return (float(loc[0]), float(loc[1]))
    if "lng" in p and "lat" in p:
        return (float(p["lng"]), float(p["lat"]))
    if "lon" in p and "lat" in p:
        return (float(p["lon"]), float(p["lat"]))
    return None


def get_hotel_loc(trip: dict[str, Any] | None) -> tuple[float, float] | None:
    if not trip:
        return None
    return get_loc(trip.get("hotel"))


def poi_by_idx(pois: list[Any], idx: int) -> dict[str, Any] | None:
    for p in pois:
        if isinstance(p, dict) and p.get("idx") == idx:
            return p
    if 1 <= idx <= len(pois) and isinstance(pois[idx - 1], dict):
        return pois[idx - 1]
    return None


def resolve_transport_point(
    idx: int | None,
    pois: list[Any],
    trip: dict[str, Any] | None = None,
) -> tuple[float, float] | None:
    if idx is None:
        return None
    if idx == 0:
        return get_hotel_loc(trip)
    p = poi_by_idx(pois, idx)
    return get_loc(p) if p else None


def get_transport_endpoints(
    t: dict[str, Any],
    pois: list[Any],
    trip: dict[str, Any] | None = None,
) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
    """transports[].from_idx/to_idx：0 = 酒店（trip.hotel），≥1 与 POI.idx 对齐。"""
    fi, ti = t.get("from_idx"), t.get("to_idx")
    if fi is None or ti is None:
        return None, None
    from_loc = resolve_transport_point(fi, pois, trip)
    to_loc = resolve_transport_point(ti, pois, trip)
    return from_loc, to_loc


# ===== 常量（与 references/validation-rules.md 阈值对齐） =====

# V1 区域一致性：POI 到主区域中心直线距离
V1_WARN_KM = 3.0
V1_FAIL_KM = 5.0

# V3 餐厅区域匹配：餐厅到主区域中心距离
V3_WARN_KM = 1.5
V3_FAIL_KM = 3.0

# V2 时间可行性：粗算（直线距离 / 典型速度）
WALK_KMH = 5.0       # 步行 5 km/h
TRANSIT_KMH = 20.0   # 公交/地铁 20 km/h
BIKE_KMH = 12.0      # 市内骑行 12 km/h
DRIVE_KMH = 40.0     # 市内驾车 40 km/h
# 通勤占当天行程 50% 阈值
V2_COMMUTE_RATIO_FAIL = 0.50
# 单段通勤 > 60 分钟强警告（与 V2 规则一致）

# V4 一日一重预约
V4_FAIL_PER_DAY = 2  # >= 2 条 prebook 算"一日多重"

# V5 末日返程缓冲
V5_BUFFER_HOURS_FAIL = 1.5  # 末日去机场缓冲 < 1.5h（国内航班）算失败
V5_BUFFER_HOURS_WARN = 2.0  # < 2h 警告

# V8 MCP 必跑痕迹（高德实算 source + duration_min）
V8_ALLOWED_SOURCES = {"amap-mcp", "amap-rest-api"}

# V9 通勤时间下限（v2.2.3：只拦「快得离谱」，不拦实算比直线慢）
V9_TOO_FAST_RATIO = 0.55  # duration_min < 粗算×55% → 疑似未跑高德 / 时间造假

# V10 价格溯源（v2.1.0）
V10_ALLOWED_SOURCES = frozenset({
    "amap-mcp", "amap-rest-api", "official-site",
    "ctrip-webfetch", "meituan-webfetch", "computed",
})
V10_BAD_SOURCES = frozenset({
    "", "ai-guess", "memory", "estimate", "demo-estimate", "note-derived",
})
V10_BUDGET_TOLERANCE = 0.15  # budget_summary 与明细加总偏差 > 15% → 警告

# 五类平台按自身属性参与不同阶段；完整攻略默认逐一尝试并记录结果。
SOURCE_PLATFORM_STAGES: dict[str, frozenset[str]] = {
    "official": frozenset({"constraints", "recheck"}),
    "amap": frozenset({"spatial", "recheck"}),
    "ota": frozenset({"booking", "pricing", "recheck"}),
    "xiaohongshu": frozenset({"discovery", "experience"}),
    "meituan": frozenset({"dining", "experience"}),
}
SOURCE_COVERAGE_STATUSES = frozenset({"used", "degraded", "unavailable", "not_applicable"})
SOURCE_COVERAGE_STAGES = frozenset().union(*SOURCE_PLATFORM_STAGES.values())

# 三阶段分轮筛检：--round N 只跑当轮子集（见 references/iteration-rounds.md）
ROUND_CHECKS: dict[int, tuple[str, ...]] = {
    1: ("V0", "V1", "V4", "V11"),
    2: ("V0", "V2", "V5", "V8", "V9", "V13"),
    3: ("V0", "V3", "V6", "V8", "V10", "V12"),
}
ROUND_PHASE: dict[int, str] = {
    1: "结构筛",
    2: "时空筛",
    3: "体验筛",
}
DEFAULT_CHECKS = ("V0", "V1", "V2", "V3", "V4", "V5", "V6", "V8", "V9", "V10", "V11", "V12", "V13")

EARTH_R_KM = 6371.0088


# ===== 工具函数 =====

def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """两点经纬度（lng, lat）之间的球面距离（km）。"""
    lng1, lat1 = a
    lng2, lat2 = b
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a_h = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_R_KM * math.asin(math.sqrt(a_h))


def commute_minutes(a: tuple[float, float], b: tuple[float, float], mode: str = "transit") -> float:
    """粗算通勤分钟（基于直线距离 + 典型速度，不调高德 MCP）。"""
    d = haversine_km(a, b)
    m = (mode or "").lower()
    if m in ("walk", "walking"):
        return d / WALK_KMH * 60
    if m in ("bike", "biking", "cycling", "ride"):
        return d / BIKE_KMH * 60
    if m in ("drive", "driving", "taxi", "car"):
        return d / DRIVE_KMH * 60
    if m in ("train", "jr", "metro", "subway"):
        return d / 45.0 * 60  # 城轨/铁路 45 km/h（含停靠）
    return d / TRANSIT_KMH * 60


def status(v: float, warn: float, fail: float) -> str:
    """三档：✅ / ⚠️ / ❌。"""
    if v >= fail:
        return "❌"
    if v >= warn:
        return "⚠️"
    return "✅"


def _as_date(value: Any) -> date | None:
    """兼容 YYYY-MM-DD 与 ISO datetime，返回日期部分。"""
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            return None


def _is_http_url(value: Any) -> bool:
    try:
        parsed = urlparse(str(value or "").strip())
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


# ===== V0：核心数据完整性 =====

def check_v0(trip: dict[str, Any]) -> dict[str, Any]:
    """阻断空计划、缺坐标、重复 idx 和无效 transport 端点。"""
    errors: list[str] = []
    for field in ("trip_name", "city", "date_range"):
        if not str(trip.get(field) or "").strip():
            errors.append(f"缺 tripData.{field}")
    if not isinstance(trip.get("party_size"), int) or trip["party_size"] < 1:
        errors.append("tripData.party_size 必须为正整数")

    source_coverage = trip.get("source_coverage")
    seen_platforms: set[str] = set()
    if not isinstance(source_coverage, list):
        errors.append("tripData.source_coverage 必须为数组")
    else:
        for index, item in enumerate(source_coverage):
            label = f"source_coverage[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{label} 必须为对象")
                continue
            platform = item.get("platform")
            if platform not in SOURCE_PLATFORM_STAGES:
                errors.append(f"{label}.platform 不合法")
                continue
            if platform in seen_platforms:
                errors.append(f"{label}.platform 重复：{platform}")
            seen_platforms.add(platform)
            if item.get("status") not in SOURCE_COVERAGE_STATUSES:
                errors.append(f"{label}.status 不合法")
            stages = item.get("stages")
            if not isinstance(stages, list) or not stages:
                errors.append(f"{label}.stages 必须为非空数组")
            else:
                invalid_stages = [stage for stage in stages if stage not in SOURCE_COVERAGE_STAGES]
                if invalid_stages:
                    errors.append(f"{label}.stages 含无效阶段：{invalid_stages}")
                if not set(stages).intersection(SOURCE_PLATFORM_STAGES[platform]):
                    errors.append(f"{label}.stages 不符合 {platform} 的平台职责")
            for field in ("purpose", "checked_at"):
                if not str(item.get(field) or "").strip():
                    errors.append(f"{label}.{field} 不能为空")
            if item.get("checked_at") and _as_date(item.get("checked_at")) is None:
                errors.append(f"{label}.checked_at 不是有效日期")
            refs = item.get("source_refs")
            if not isinstance(refs, list):
                errors.append(f"{label}.source_refs 必须为数组")
            elif item.get("status") in {"used", "degraded"}:
                if not refs:
                    errors.append(f"{label}.source_refs 使用或降级时不能为空")
                elif any(not _is_http_url(ref) for ref in refs):
                    errors.append(f"{label}.source_refs 只能包含 HTTP(S) 链接")
            if item.get("status") in {"unavailable", "not_applicable"} and not str(item.get("note") or "").strip():
                errors.append(f"{label}.note 必须说明未使用原因")
        missing_platforms = set(SOURCE_PLATFORM_STAGES).difference(seen_platforms)
        if missing_platforms:
            errors.append(f"source_coverage 缺少平台：{sorted(missing_platforms)}")

    prebook = trip.get("prebook")
    if not isinstance(prebook, list):
        errors.append("tripData.prebook 必须为数组")
    else:
        for index, item in enumerate(prebook):
            label = f"prebook[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{label} 必须为对象")
                continue
            for field in ("item", "deadline", "url"):
                if not str(item.get(field) or "").strip():
                    errors.append(f"{label}.{field} 不能为空")
            if item.get("priority") not in {"must", "recommended", "optional"}:
                errors.append(f"{label}.priority 不合法")
            if item.get("status") not in {"booked", "not_booked", "not_required", "unknown"}:
                errors.append(f"{label}.status 不合法")
            if not isinstance(item.get("id_required"), bool):
                errors.append(f"{label}.id_required 必须为布尔值")

    safety_notes = trip.get("safety_notes")
    if not isinstance(safety_notes, list) or not safety_notes:
        errors.append("tripData.safety_notes 必须为非空数组")
    else:
        for index, item in enumerate(safety_notes):
            label = f"safety_notes[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{label} 必须为对象")
                continue
            for field in ("risk", "action", "source", "source_ref", "checked_at"):
                if not str(item.get(field) or "").strip():
                    errors.append(f"{label}.{field} 不能为空")
            if item.get("severity") not in {"notice", "warning", "critical"}:
                errors.append(f"{label}.severity 不合法")

    days = trip.get("days")
    if not isinstance(days, list) or not days:
        errors.append("tripData.days 必须为非空数组")
        days = []

    for day_index, day in enumerate(days):
        label = f"days[{day_index}]"
        if not isinstance(day, dict):
            errors.append(f"{label} 必须为对象")
            continue
        if not isinstance(day.get("day"), int):
            errors.append(f"{label}.day 必须为整数")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(day.get("date") or "")):
            errors.append(f"{label}.date 必须为 YYYY-MM-DD")
        if not str(day.get("region") or "").strip():
            errors.append(f"{label}.region 不能为空")
        try:
            center_ok = get_loc({"location": day.get("center")}) is not None
        except (TypeError, ValueError):
            center_ok = False
        if not center_ok:
            errors.append(f"{label}.center 缺有效经纬度")

        pois = day.get("pois")
        if not isinstance(pois, list) or not pois:
            errors.append(f"{label}.pois 必须为非空数组")
            continue
        idxs: list[int] = []
        for poi_index, poi in enumerate(pois):
            poi_label = f"{label}.pois[{poi_index}]"
            if not isinstance(poi, dict):
                errors.append(f"{poi_label} 必须为对象")
                continue
            idx = poi.get("idx")
            if not isinstance(idx, int) or idx < 1:
                errors.append(f"{poi_label}.idx 必须为正整数")
            else:
                idxs.append(idx)
            if not str(poi.get("name") or "").strip():
                errors.append(f"{poi_label}.name 不能为空")
            if not re.match(r"^\d{1,2}:\d{2}", str(poi.get("time") or "")):
                errors.append(f"{poi_label}.time 缺有效时间")
            if not isinstance(poi.get("duration_min"), (int, float)) or poi["duration_min"] <= 0:
                errors.append(f"{poi_label}.duration_min 必须大于 0")
            try:
                loc_ok = get_loc(poi) is not None
            except (TypeError, ValueError):
                loc_ok = False
            if not loc_ok:
                errors.append(f"{poi_label} 缺有效经纬度")
        if len(idxs) != len(set(idxs)):
            errors.append(f"{label}.pois 存在重复 idx")

        valid_endpoints = {0, *idxs}
        for transport_index, transport in enumerate(day.get("transports") or []):
            t_label = f"{label}.transports[{transport_index}]"
            if not isinstance(transport, dict):
                errors.append(f"{t_label} 必须为对象")
                continue
            if transport.get("from_idx") not in valid_endpoints:
                errors.append(f"{t_label}.from_idx 不对应酒店或当日 POI")
            if transport.get("to_idx") not in valid_endpoints:
                errors.append(f"{t_label}.to_idx 不对应酒店或当日 POI")

    if errors:
        return {
            "id": "V0", "rule": "核心数据完整性", "status": "❌",
            "note": f"{len(errors)} 项 schema 错误：{errors[:5]}{'...' if len(errors) > 5 else ''}",
            "errors": errors,
        }
    return {"id": "V0", "rule": "核心数据完整性", "status": "✅", "note": "核心字段、五类信息源覆盖、POI 坐标与 transport 端点完整"}


# ===== V1：区域一致性 =====

def check_v1(day: dict[str, Any], is_last_day: bool = False) -> dict[str, Any]:
    """POI 到主区域中心直线距离。

    末日（is_last_day=True）或 `region_flex: true` 跳过最远 POI 距离判定——
    末日通常要赶机场/高铁站；`region_flex: true` 标记"白天去郊区 + 晚上回市区"的合理跨区域行程。
    """
    center = day.get("center")
    pois = day.get("pois") or []
    if not center or not pois:
        return {"id": "V1", "rule": "区域一致性", "status": "⚠️", "note": "缺 center 或 pois 字段，跳过"}

    # 跨区日跳过：末日（赶机场/高铁）或 region_flex=true（白天远郊+晚上回市区）
    region = day.get("region", "?")
    if is_last_day:
        return {"id": "V1", "rule": "区域一致性", "status": "✅", "note": f"末日（{region}），跳过区域距离检查（返程 POI 偏远是合理的；用 V5 验缓冲）"}
    if day.get("region_flex") is True:
        return {"id": "V1", "rule": "区域一致性", "status": "✅", "note": f"含跨区返程（{region}），region_flex=true 跳过最远距离检查"}

    worst = None
    worst_poi = None
    for p in pois:
        loc = get_loc(p)
        if loc is None:
            continue
        d = haversine_km(tuple(center), loc)
        if worst is None or d > worst:
            worst = d
            worst_poi = p.get("name", "?")

    if worst is None:
        return {"id": "V1", "rule": "区域一致性", "status": "⚠️", "note": "POI 缺 location / lng+lat 字段"}

    st = status(worst, V1_WARN_KM, V1_FAIL_KM)
    note = f"主区域 {day.get('region', '?')}，最远 POI「{worst_poi}」 {worst:.2f} km（阈值 {V1_WARN_KM}/{V1_FAIL_KM}）"
    return {"id": "V1", "rule": "区域一致性", "status": st, "note": note, "worst_km": round(worst, 2)}


# ===== V2：时间可行性（粗算） =====

def check_v2(day: dict[str, Any]) -> dict[str, Any]:
    """相邻 POI 通勤粗算（直线距离 + 假设速度）。"""
    pois = day.get("pois") or []
    if len(pois) < 2:
        return {"id": "V2", "rule": "时间可行性（粗算）", "status": "✅", "note": "单 POI 日，跳过"}

    total_commute = 0.0
    total_stay = 0.0
    worst_seg = 0.0
    worst_pair = None
    for i in range(len(pois) - 1):
        a = get_loc(pois[i])
        b = get_loc(pois[i + 1])
        if a is None or b is None:
            continue
        mode = pois[i].get("next_mode", "transit")  # 默认公交
        cm = commute_minutes(a, b, mode)
        total_commute += cm
        if cm > worst_seg:
            worst_seg = cm
            worst_pair = (pois[i].get("name", "?"), pois[i + 1].get("name", "?"))

    for p in pois:
        total_stay += p.get("duration_min", 0)

    if total_stay == 0:
        return {"id": "V2", "rule": "时间可行性（粗算）", "status": "⚠️", "note": "POI 缺 duration_min，无法判占比"}

    ratio = total_commute / (total_commute + total_stay)
    st = status(ratio, V2_COMMUTE_RATIO_FAIL * 0.66, V2_COMMUTE_RATIO_FAIL)
    pair_str = f"{worst_pair[0]}→{worst_pair[1]}" if worst_pair else "（POI 缺 location）"
    note = f"通勤占总时长 {ratio*100:.1f}%；最远段 {worst_seg:.0f} min（{pair_str}，**粗算，建议用高德 route_* 复核**）"
    return {"id": "V2", "rule": "时间可行性（粗算）", "status": st, "note": note, "commute_ratio": round(ratio, 3)}


# ===== V3：餐厅区域匹配 =====

def check_v3(day: dict[str, Any]) -> dict[str, Any]:
    """餐厅应靠近主区域，或明确作为当日路线中的一站。"""
    center = day.get("center")
    meals = day.get("meals") or {}
    if not center:
        return {"id": "V3", "rule": "餐厅区域匹配", "status": "⚠️", "note": "缺 center 字段"}

    worst_d = 0.0
    worst_meal = None
    worst_rest = None
    missing_main_coords: list[str] = []
    candidate_count = 0
    routed_count = 0
    poi_locs = [loc for p in day.get("pois") or [] if (loc := get_loc(p)) is not None]
    for meal_name, meal in meals.items():
        if not isinstance(meal, dict):
            continue
        for tag in ("main", "alt", "alt1", "alt2"):
            r = meal.get(tag) or {}
            if not isinstance(r, dict) or not r.get("name"):
                continue
            loc = get_loc(r)
            if loc is None:
                if tag == "main":
                    missing_main_coords.append(f"{meal_name}.main（{r.get('name')}）")
                continue
            candidate_count += 1
            d = haversine_km(tuple(center), loc)
            nearest_poi = min((haversine_km(loc, p) for p in poi_locs), default=float("inf"))
            if d > V3_WARN_KM and nearest_poi <= 0.3:
                routed_count += 1
                continue
            if d > worst_d:
                worst_d = d
                worst_meal = meal_name
                worst_rest = r.get("name", "?")

    if missing_main_coords:
        return {
            "id": "V3", "rule": "餐厅区域匹配", "status": "❌",
            "note": f"主餐厅缺坐标，无法验证区域：{'、'.join(missing_main_coords)}",
            "errors": missing_main_coords,
        }
    if candidate_count == 0:
        return {"id": "V3", "rule": "餐厅区域匹配", "status": "⚠️", "note": "没有可验证的餐厅候选"}
    if worst_d == 0.0:
        note = "所有餐厅均在主区域内"
        if routed_count:
            note = f"{routed_count} 个偏离主区域的餐厅已明确列入当日路线，其余餐厅均在主区域内"
        return {"id": "V3", "rule": "餐厅区域匹配", "status": "✅", "note": note}

    st = status(worst_d, V3_WARN_KM, V3_FAIL_KM)
    note = f"最远餐厅「{worst_rest}」({worst_meal}) 离主区域 {worst_d:.2f} km（阈值 {V3_WARN_KM}/{V3_FAIL_KM}）"
    return {"id": "V3", "rule": "餐厅区域匹配", "status": st, "note": note, "worst_km": round(worst_d, 2)}


# ===== V4：一日一重预约 =====

def check_v4(day: dict[str, Any], prebook: list[dict[str, Any]]) -> dict[str, Any]:
    """每天 prebook 条数。

    只数**当日必须预约/取票的** POI（如 Day 3 熊猫基地提前 1 天预约）。
    出发前 N 天的机票/酒店**不算**当日预约（启发式：note 里有「Day N」才匹配当日，
    且仅排除「出发前」一次性购买类条目；「提前 1 天预约/放票」算作当日重预约）。
    """
    day_idx = day.get("day")
    day_prebooks = []
    for p in prebook:
        note = p.get("note") or ""
        item = p.get("item") or p.get("title") or ""
        # 显式 day 字段
        if p.get("day") == day_idx:
            day_prebooks.append(p)
            continue
        # 启发式：note 里提到 "Day N" 才算
        if f"Day {day_idx}" in note:
            # 仅排除"出发前 N 天买机票/酒店"；"提前 N 天预约/放票"算作当日重预约
            if "出发前" in note:
                continue
            day_prebooks.append(p)
    n = len(day_prebooks)
    if n >= V4_FAIL_PER_DAY:
        st = "❌"
    else:
        st = "✅"
    items = "、".join(p.get("item") or p.get("title") or "?" for p in day_prebooks) or "无"
    return {"id": "V4", "rule": "一日一重预约", "status": st, "note": f"Day {day_idx} 当日预约 {n} 条：{items}", "count": n}


# ===== V5：末日返程缓冲 =====

def check_v5(last_day: dict[str, Any], trip_meta: dict[str, Any]) -> dict[str, Any]:
    """末日去机场/高铁站的缓冲。"""
    prebook = trip_meta.get("prebook") or []
    flights = [p for p in prebook if any(k in (p.get("item") or p.get("title") or "") for k in ("航班", "飞机", "高铁", "火车", "动车", "机票"))]
    if not flights:
        return {"id": "V5", "rule": "末日返程缓冲", "status": "✅", "note": "无返程票，跳过"}

    return_flights = [p for p in flights if any(k in (p.get("item") or p.get("title") or "") for k in ("返程", "回程", "离开"))]
    flight = return_flights[-1] if return_flights else flights[-1]
    flight_time = flight.get("depart_time") or flight.get("time") or ""
    flight_note = flight.get("item") or flight.get("title") or "返程"

    pois = last_day.get("pois") or []
    if not pois:
        return {"id": "V5", "rule": "末日返程缓冲", "status": "⚠️", "note": f"末日无 POI 数据；返程：{flight_note} {flight_time}"}

    last_poi = pois[-1]
    end_time = last_poi.get("end_time") or last_poi.get("time") or ""

    if not end_time or not flight_time:
        return {"id": "V5", "rule": "末日返程缓冲", "status": "⚠️", "note": f"末日末 POI 或航班缺时间；POI 末 = {end_time}，航班 = {flight_time}"}

    # 简化为 HH:MM 比较（不处理跨日）
    def to_min(t: str) -> int:
        h, m = t.split(":")[:2]
        return int(h) * 60 + int(m)

    last_poi_min = to_min(end_time)
    flight_min = to_min(flight_time)
    buffer_min = flight_min - last_poi_min

    if buffer_min < V5_BUFFER_HOURS_FAIL * 60:
        st = "❌"
    elif buffer_min < V5_BUFFER_HOURS_WARN * 60:
        st = "⚠️"
    else:
        st = "✅"

    note = f"末日末 POI {end_time} → 航班 {flight_time}，缓冲 {buffer_min/60:.2f} h（{flight_note}）"
    return {"id": "V5", "rule": "末日返程缓冲", "status": st, "note": note, "buffer_hours": round(buffer_min / 60, 2)}


# ===== V6：户外天气敏感 =====

def check_v6(day: dict[str, Any]) -> dict[str, Any]:
    """检查天气敏感 POI 是否有具体 Plan B。"""
    pois = day.get("pois") or []
    if not pois:
        return {"id": "V6", "rule": "户外天气敏感", "status": "✅", "note": "无 POI"}

    weather = (day.get("weather") or "").lower()
    bad_weather = any(k in weather for k in ("雨", "雪", "雷", "storm", "rain", "snow"))

    outdoor_pois = [
        p for p in pois
        if p.get("weather_sensitive") is True
        or p.get("type") == "outdoor"
        or any(k in (p.get("tags") or []) for k in ("outdoor", "户外", "露台", "天台", "观景"))
    ]
    if not outdoor_pois:
        return {"id": "V6", "rule": "户外天气敏感", "status": "✅", "note": "无户外 POI"}

    raw_plan_b = day.get("plan_b")
    plan_b_items = raw_plan_b if isinstance(raw_plan_b, list) else [raw_plan_b]
    plan_b_items = [item for item in plan_b_items if isinstance(item, dict)]
    has_decision = any(
        all(str(item.get(field) or "").strip() for field in ("trigger", "alternative", "impact"))
        for item in plan_b_items
    )
    if not has_decision:
        return {
            "id": "V6",
            "rule": "户外天气敏感",
            "status": "❌",
            "note": "存在天气敏感 POI，但 day.plan_b 缺 trigger / alternative / impact 决策",
        }

    if not bad_weather:
        return {"id": "V6", "rule": "户外天气敏感", "status": "✅", "note": f"天气好（{day.get('weather')}），{len(outdoor_pois)} 个敏感 POI 已配结构化 Plan B"}

    missing = [p.get("name", "?") for p in outdoor_pois if not p.get("indoor_backup")]
    if missing:
        return {"id": "V6", "rule": "户外天气敏感", "status": "❌", "note": f"天气{day.get('weather')}，户外 POI 缺 indoor_backup：{'、'.join(missing)}"}
    return {"id": "V6", "rule": "户外天气敏感", "status": "✅", "note": "户外 POI 均配 indoor_backup 与结构化 Plan B"}


# ===== V8：MCP 必跑痕迹（source + duration_min）=====

def check_v8(days: list[dict[str, Any]], trip: dict[str, Any] | None = None) -> dict[str, Any]:
    """每段 transport 须有允许的路线来源声明与 duration_min。"""
    total_transports = 0
    bad_source = []
    missing_duration = []

    for d in days:
        day_label = f"Day {d.get('day', '?')}"
        for i, t in enumerate(d.get("transports") or []):
            if not isinstance(t, dict):
                continue
            total_transports += 1
            seg_label = f"{day_label}.transports[{i}]"

            src = t.get("source")
            if not src:
                bad_source.append(f"{seg_label}（缺 source 字段）")
                continue
            if src not in V8_ALLOWED_SOURCES:
                bad_source.append(f"{seg_label}（source={src}，合法值：{V8_ALLOWED_SOURCES}）")
                continue

            dur = t.get("duration_min")
            if dur is None or not isinstance(dur, (int, float)) or dur <= 0:
                missing_duration.append(f"{seg_label}（缺或无效 duration_min）")

    if total_transports == 0:
        needs_routes = any(len(d.get("pois") or []) > 1 for d in days)
        return {
            "id": "V8",
            "rule": "路线来源字段完整性",
            "status": "❌" if needs_routes else "⚠️",
            "note": "存在多 POI 行程但没有 transport 段" if needs_routes else "无 transport 段可验证",
        }

    errors = []
    if bad_source:
        errors.append(f"{len(bad_source)} 段 source 不合法：{bad_source[:3]}{'...' if len(bad_source) > 3 else ''}")
    if missing_duration:
        errors.append(
            f"{len(missing_duration)} 段缺 duration_min：{missing_duration[:3]}{'...' if len(missing_duration) > 3 else ''}"
        )

    if errors:
        return {
            "id": "V8",
            "rule": "路线来源字段完整性",
            "status": "❌",
            "note": f"❌ 共 {total_transports} 段 transport：{'；'.join(errors)}。请用当前可用的地图能力重新实算。",
            "errors": {"bad_source": bad_source, "missing_duration": missing_duration},
        }

    return {
        "id": "V8",
        "rule": "路线来源字段完整性",
        "status": "✅",
        "note": f"全部 {total_transports} 段 transport 含合法 source 与 duration_min",
    }


# ===== V9：通勤时间下限 =====

def check_v9(days: list[dict[str, Any]], trip: dict[str, Any] | None = None) -> dict[str, Any]:
    """检查 transports[].duration_min 是否快得不合理。

    v2.2.3 修正：旧版用 |实算-粗算|/粗算 > 50% 双向比较——公交/步行实算常**比** Haversine
    直线粗算慢很多（绕路、换乘、等站），会误杀真数据。

    新版只拦「快得离谱」：duration_min < Haversine粗算 × V9_TOO_FAST_RATIO。
    实算 ≥ 粗算下限即通过（30 min 公交 vs 粗算 10 min 不算违规）。

    缺 duration_min 不再跳过——与 V8 一样阻断。
    """
    suspicious: list[str] = []
    missing_duration: list[str] = []
    total_segments = 0

    for d in days:
        day_label = f"Day {d.get('day', '?')}"
        for i, t in enumerate(d.get("transports") or []):
            if not isinstance(t, dict):
                continue
            total_segments += 1
            seg_label = f"{day_label}.transports[{i}]"
            duration_ai = t.get("duration_min")
            if duration_ai is None:
                missing_duration.append(seg_label)
                continue

            mode = t.get("mode", "transit")
            from_loc, to_loc = get_transport_endpoints(t, d.get("pois") or [], trip)
            if not from_loc or not to_loc:
                continue

            rough = commute_minutes(from_loc, to_loc, mode)
            if rough <= 0:
                continue

            floor = rough * V9_TOO_FAST_RATIO
            if duration_ai < floor:
                suspicious.append(
                    f"{seg_label}：报 {duration_ai} min < 粗算下限 {floor:.0f} min"
                    f"（直线粗算 {rough:.0f} min×{V9_TOO_FAST_RATIO}，mode={mode}，疑似未跑高德）"
                )

    if total_segments == 0:
        return {
            "id": "V9",
            "rule": "通勤时间下限（高德实算）",
            "status": "✅",
            "note": "无 transport 段，跳过",
        }

    errors: list[str] = []
    if missing_duration:
        errors.append(
            f"{len(missing_duration)} 段缺 duration_min：{missing_duration[:3]}{'...' if len(missing_duration) > 3 else ''}"
        )
    if suspicious:
        errors.append(
            f"{len(suspicious)} 段时间快得离谱：{suspicious[:3]}{'...' if len(suspicious) > 3 else ''}"
        )

    if errors:
        return {
            "id": "V9",
            "rule": "通勤时间下限（高德实算）",
            "status": "❌",
            "note": f"❌ 通勤时间未就绪！共 {total_segments} 段：{'；'.join(errors)}。须 MCP/REST 填真实 duration_min。",
            "errors": {"missing_duration": missing_duration, "too_fast": suspicious},
        }

    return {
        "id": "V9",
        "rule": "通勤时间下限（高德实算）",
        "status": "✅",
        "note": f"全部 {total_segments} 段 duration_min 已填且 ≥ 直线粗算×{V9_TOO_FAST_RATIO:.0%}（实算比粗算慢允许）",
    }


# ===== V13（v2.2.4 新增）：酒店早晚通勤 =====

_DEPARTURE_NAME_RE = re.compile(r"机场|火车站|高铁站|(?:汽车)?车站|码头|港口")


def _first_poi_is_hotel(pois: list[Any], trip: dict[str, Any]) -> bool:
    if not pois:
        return False
    first = pois[0]
    if not isinstance(first, dict):
        return False
    if first.get("cat") == "hotel":
        return True
    hotel_name = (trip.get("hotel") or {}).get("name")
    return bool(hotel_name and first.get("name") == hotel_name)


def _last_poi_is_departure(last: dict[str, Any]) -> bool:
    if last.get("cat") == "transport":
        return True
    return bool(_DEPARTURE_NAME_RE.search(last.get("name") or ""))


def _first_poi_skips_morning(pois: list[Any], trip: dict[str, Any], day_num: int) -> bool:
    """仅抵达日（Day 1 机场/车站首站）免早晨酒店出发；邮轮码头等仍须酒店→首站。"""
    if _first_poi_is_hotel(pois, trip):
        return True
    if day_num != 1:
        return False
    if not pois:
        return False
    first = pois[0]
    if not isinstance(first, dict):
        return False
    if first.get("cat") == "transport":
        return True
    return bool(_DEPARTURE_NAME_RE.search(first.get("name") or ""))


def check_v13(trip: dict[str, Any], days: list[dict[str, Any]]) -> dict[str, Any]:
    """每天须含 酒店→首站 / 末站→酒店 的 transports（from_idx|to_idx=0 表示酒店）。

    例外：首日首 POI 已是酒店则免早晨段；末日末站为机场/车站则免傍晚回酒店。
    """
    if not get_hotel_loc(trip):
        return {
            "id": "V13",
            "rule": "酒店早晚通勤",
            "status": "⚠️",
            "note": "无 hotel 坐标，无法验证酒店早晚通勤",
        }

    missing: list[str] = []
    for d in days:
        pois = d.get("pois") or []
        if not pois:
            continue
        day_num = d.get("day", "?")
        first, last = pois[0], pois[-1]
        first_idx = first.get("idx") if isinstance(first, dict) else None
        last_idx = last.get("idx") if isinstance(last, dict) else None
        transports = d.get("transports") or []

        if not _first_poi_skips_morning(pois, trip, d.get("day", 0)) and first_idx is not None:
            has_morning = any(
                isinstance(t, dict) and t.get("from_idx") == 0 and t.get("to_idx") == first_idx
                for t in transports
            )
            if not has_morning:
                missing.append(f"Day {day_num} 缺 酒店→首站（from_idx:0 → to_idx:{first_idx}）")

        if isinstance(last, dict) and not _last_poi_is_departure(last) and last_idx is not None:
            has_evening = any(
                isinstance(t, dict) and t.get("from_idx") == last_idx and t.get("to_idx") == 0
                for t in transports
            )
            if not has_evening:
                missing.append(f"Day {day_num} 缺 末站→酒店（from_idx:{last_idx} → to_idx:0）")

    if not missing:
        return {
            "id": "V13",
            "rule": "酒店早晚通勤",
            "status": "✅",
            "note": "每日酒店出发/回酒店段已写入 transports（idx=0）",
        }

    return {
        "id": "V13",
        "rule": "酒店早晚通勤",
        "status": "❌",
        "note": f"❌ {len(missing)} 天缺酒店通勤：{'；'.join(missing)}。Round 2 须 MCP+REST 补 path/fare。",
        "errors": missing,
    }


# ===== V10：价格溯源 =====

def _valid_price_field(obj: Any, label: str) -> str | None:
    """返回错误信息，无错返回 None。"""
    if not isinstance(obj, dict):
        return f"{label} 缺 price/fare 对象"
    src = (obj.get("source") or "").strip()
    if src in V10_BAD_SOURCES or not src:
        return f"{label} source 缺失或禁止（{src!r}）"
    if src not in V10_ALLOWED_SOURCES:
        return f"{label} source 不在白名单：{src}"
    unit = obj.get("unit")
    if unit == "free":
        return None
    if obj.get("min") is None and obj.get("max") is None:
        return f"{label} 缺 min/max"
    return None


def _price_totals(obj: dict[str, Any]) -> tuple[float, float]:
    """从 price/fare 对象取 (total_min, total_max)。"""
    if not isinstance(obj, dict):
        return 0.0, 0.0
    tmin, tmax = obj.get("total_min"), obj.get("total_max")
    if tmin is not None:
        return float(tmin), float(tmax if tmax is not None else tmin)
    mn, mx = obj.get("min"), obj.get("max")
    if mn is None:
        return 0.0, 0.0
    mx = mx if mx is not None else mn
    q = float(obj.get("quantity") or 1)
    return float(mn) * q, float(mx) * q


def check_v10(trip: dict[str, Any]) -> dict[str, Any]:
    """v2.1.0：POI/交通/餐饮必有调研价 + source；禁止 ai-guess。"""
    errors: list[str] = []
    warnings: list[str] = []

    party_size = trip.get("party_size")
    if not isinstance(party_size, int) or party_size < 1:
        errors.append("缺 tripData.party_size（正整数）")

    days = trip.get("days") or []
    line_min, line_max = 0.0, 0.0

    def _add_price(obj: Any) -> None:
        nonlocal line_min, line_max
        if not isinstance(obj, dict):
            return
        a, b = _price_totals(obj)
        line_min += a
        line_max += b

    for d in days:
        day_label = f"Day {d.get('day', '?')}"
        for i, p in enumerate(d.get("pois") or []):
            if not isinstance(p, dict):
                continue
            err = _valid_price_field(p.get("price"), f"{day_label}.pois[{i}]")
            if err:
                errors.append(err)
            else:
                _add_price(p.get("price"))
            for j, sc in enumerate(p.get("slot_costs") or []):
                if not isinstance(sc, dict):
                    warnings.append(f"{day_label}.pois[{i}].slot_costs[{j}] 非对象")
                    continue
                if not (sc.get("label") or "").strip():
                    warnings.append(f"{day_label}.pois[{i}].slot_costs[{j}] 缺 label")
                err = _valid_price_field(sc.get("price"), f"{day_label}.pois[{i}].slot_costs[{j}]")
                if err:
                    warnings.append(err)
        for i, t in enumerate(d.get("transports") or []):
            if not isinstance(t, dict):
                continue
            err = _valid_price_field(t.get("fare"), f"{day_label}.transports[{i}]")
            if err:
                errors.append(err)
            else:
                _add_price(t.get("fare"))
        meals = d.get("meals") or {}
        if isinstance(meals, dict):
            for mt in ("breakfast", "lunch", "dinner"):
                block = meals.get(mt)
                if not isinstance(block, dict):
                    continue
                main = block.get("main")
                if not isinstance(main, dict):
                    if mt in ("lunch", "dinner"):
                        errors.append(f"{day_label}.meals.{mt}.main 缺 price")
                    continue
                err = _valid_price_field(main.get("price"), f"{day_label}.meals.{mt}.main")
                if err:
                    errors.append(err)
                else:
                    _add_price(main.get("price"))

    _add_price((trip.get("hotel") or {}).get("price"))
    for pb in trip.get("prebook") or []:
        if isinstance(pb, dict) and "机票" in (pb.get("item") or ""):
            _add_price(pb.get("price"))

    bs = trip.get("budget_summary")
    if isinstance(bs, dict) and bs.get("total_min") is not None:
        bmin, bmax = float(bs["total_min"]), float(bs.get("total_max") or bs["total_min"])
        if line_min > 0 and bmin > 0:
            diff = abs(bmin - line_min) / bmin
            if diff > V10_BUDGET_TOLERANCE:
                warnings.append(
                    f"budget_summary.total_min({bmin:.0f}) 与时间轴明细加总({line_min:.0f}) 偏差 {diff*100:.0f}%"
                )

    if errors:
        return {
            "id": "V10",
            "rule": "价格溯源",
            "status": "❌",
            "note": f"❌ {len(errors)} 项缺价或无溯源：{errors[:4]}{'...' if len(errors) > 4 else ''}",
            "errors": errors,
        }
    if warnings:
        return {
            "id": "V10",
            "rule": "价格溯源",
            "status": "⚠️",
            "note": "；".join(warnings),
            "warnings": warnings,
        }
    n_poi = sum(len(d.get("pois") or []) for d in days)
    n_trans = sum(len(d.get("transports") or []) for d in days)
    return {
        "id": "V10",
        "rule": "价格溯源",
        "status": "✅",
        "note": f"全部 {n_poi} POI + {n_trans} transport + 餐食均有 source 标价",
    }


# ===== V11：prebook 禁止国际 OTA =====

_FOREIGN_OTA_SUFFIXES = ("booking.com", "agoda.com", "expedia.com")


def _is_foreign_ota_url(url: str) -> bool:
    try:
        host = (urlparse(url.strip()).hostname or "").lower().replace("www.", "")
    except Exception:
        return False
    if not host:
        return False
    if host == "ctrip.com" or host.endswith(".ctrip.com"):
        return False
    if host == "trip.com" or host.endswith(".trip.com"):
        return True
    return any(host == s or host.endswith("." + s) for s in _FOREIGN_OTA_SUFFIXES)


def check_v11(trip: dict[str, Any]) -> dict[str, Any]:
    """prebook 链接须为国内携程深链或官方站，禁止 trip.com / Booking 等。"""
    bad: list[str] = []
    for pb in trip.get("prebook") or []:
        if not isinstance(pb, dict):
            continue
        url = (pb.get("url") or "").strip()
        if url and _is_foreign_ota_url(url):
            bad.append(f"{pb.get('item') or '?'} → {url}")
    if bad:
        return {
            "id": "V11",
            "rule": "prebook 国内 OTA 链接",
            "status": "❌",
            "note": f"禁止 trip.com / Booking 等国际 OTA，改 flights.ctrip.com 等：{bad[0]}{'…' if len(bad) > 1 else ''}",
            "bad_urls": bad,
        }
    return {
        "id": "V11",
        "rule": "prebook 国内 OTA 链接",
        "status": "✅",
        "note": "prebook 链接均为国内携程深链或官方站",
    }


# ===== V12：信息时效性与行前复核 =====

V12_CATEGORIES = {"opening", "booking", "transport", "price", "weather", "safety"}
V12_STATUSES = {"verified", "due", "unknown"}


def check_v12(trip: dict[str, Any], as_of: date | None = None) -> dict[str, Any]:
    """检查易变事实是否有核对时间、下一次复核时间与可追溯来源。"""
    today = as_of or date.today()
    errors: list[str] = []
    warnings: list[str] = []
    rechecks = trip.get("rechecks")
    if not isinstance(rechecks, list) or not rechecks:
        return {
            "id": "V12",
            "rule": "信息时效性",
            "status": "❌",
            "note": "缺 rechecks 行前复核清单；易变事实没有统一的核对时间与复核节点",
            "errors": ["tripData.rechecks 必须为非空数组"],
        }

    categories: set[str] = set()
    parsed: list[tuple[str, date | None, date | None, str]] = []
    for index, item in enumerate(rechecks):
        label = f"rechecks[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} 必须为对象")
            continue
        title = str(item.get("item") or "").strip()
        category = str(item.get("category") or "").strip()
        status_value = str(item.get("status") or "").strip()
        checked_at = _as_date(item.get("checked_at"))
        recheck_at = _as_date(item.get("recheck_at"))
        if not title:
            errors.append(f"{label}.item 不能为空")
        if category not in V12_CATEGORIES:
            errors.append(f"{label}.category 不合法：{category!r}")
        else:
            categories.add(category)
        if status_value not in V12_STATUSES:
            errors.append(f"{label}.status 不合法：{status_value!r}")
        if not checked_at:
            errors.append(f"{label}.checked_at 缺失或格式错误")
        elif checked_at > today:
            errors.append(f"{label}.checked_at 不能晚于核验日期 {today.isoformat()}")
        if not recheck_at:
            errors.append(f"{label}.recheck_at 缺失或格式错误")
        elif recheck_at <= today:
            warnings.append(f"{title or label} 已到复核时间 {recheck_at.isoformat()}")
        if not str(item.get("source") or "").strip():
            errors.append(f"{label}.source 不能为空")
        if not str(item.get("source_ref") or "").strip():
            errors.append(f"{label}.source_ref 不能为空")
        if status_value in {"due", "unknown"}:
            warnings.append(f"{title or label} 状态为 {status_value}")
        parsed.append((category, checked_at, recheck_at, title or label))

    required = {"opening", "transport", "price"}
    if trip.get("prebook"):
        required.add("booking")
    has_weather_risk = bool(trip.get("weather_plan")) or any(
        isinstance(poi, dict) and (
            poi.get("weather_sensitive") is True
            or poi.get("type") == "outdoor"
            or any(tag in {"outdoor", "户外", "露台", "天台", "观景"} for tag in (poi.get("tags") or []))
        )
        for day_item in trip.get("days") or [] if isinstance(day_item, dict)
        for poi in day_item.get("pois") or []
    )
    if has_weather_risk:
        required.add("weather")
    if trip.get("safety_notes"):
        required.add("safety")
    missing_categories = sorted(required - categories)
    if missing_categories:
        errors.append(f"缺复核类别：{missing_categories}")

    days = [item for item in trip.get("days") or [] if isinstance(item, dict)]
    trip_start = _as_date(days[0].get("date")) if days else None
    if trip_start:
        days_until = (trip_start - today).days
        if days_until <= 7:
            recent_categories = {"opening", "booking", "transport", "price"}
            for category, checked_at, _, title in parsed:
                if category in recent_categories and checked_at and checked_at < today - timedelta(days=7):
                    warnings.append(f"{title} 距出发不足 7 天，但最近核对为 {checked_at.isoformat()}")
        if days_until <= 1 and has_weather_risk:
            weather_records = [row for row in parsed if row[0] == "weather"]
            if not weather_records or any(
                checked_at is None or checked_at < today - timedelta(days=1)
                for _, checked_at, _, _ in weather_records
            ):
                warnings.append("距出发不足 1 天，天气/预警需要在 24 小时内重新核对")

    if errors:
        return {
            "id": "V12",
            "rule": "信息时效性",
            "status": "❌",
            "note": f"{len(errors)} 项时效数据错误：{errors[:4]}{'...' if len(errors) > 4 else ''}",
            "errors": errors,
            "warnings": warnings,
        }
    if warnings:
        return {
            "id": "V12",
            "rule": "信息时效性",
            "status": "⚠️",
            "note": "；".join(warnings),
            "warnings": warnings,
        }
    return {
        "id": "V12",
        "rule": "信息时效性",
        "status": "✅",
        "note": f"{len(rechecks)} 项易变事实均有来源、核对时间和下一次复核节点",
    }


# ===== 主流程 =====

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("trip_json", help="tripData JSON 文件路径")
    p.add_argument(
        "--round",
        type=int,
        choices=(1, 2, 3),
        help="三阶段筛检：1=结构 2=时空 3=体验；每轮都会先跑 V0",
    )
    p.add_argument(
        "--check",
        default=None,
        help="逗号分隔的规则 ID；默认全跑；与 --round 同时用时 --check 优先；V0 始终先运行",
    )
    p.add_argument("--pretty", action="store_true", help="缩进输出")
    p.add_argument("--fail-on-warn", action="store_true", help="存在警告时也返回非零退出码（CI 推荐）")
    p.add_argument("--as-of", help="按 YYYY-MM-DD 计算 V12 到期状态；默认使用今天")
    args = p.parse_args()

    as_of = _as_date(args.as_of) if args.as_of else date.today()
    if args.as_of and not as_of:
        p.error("--as-of 必须为 YYYY-MM-DD")

    with open(args.trip_json, "r", encoding="utf-8") as f:
        trip = json.load(f)

    days = trip.get("days") or []
    prebook = trip.get("prebook") or []
    if args.check:
        selected = set(args.check.split(","))
        round_num = args.round
    elif args.round is not None:
        round_num = args.round
        selected = set(ROUND_CHECKS[round_num])
    else:
        round_num = None
        selected = set(DEFAULT_CHECKS)
    selected.add("V0")

    rules = []
    n_days = len(days)
    v0_result = check_v0(trip)
    rules.append(v0_result)
    if v0_result["status"] == "❌":
        selected = {"V0"}
    if "V1" in selected:
        for i, d in enumerate(days):
            rules.append(check_v1(d, is_last_day=(i == n_days - 1)))
    if "V2" in selected:
        for d in days:
            rules.append(check_v2(d))
    if "V3" in selected:
        for d in days:
            rules.append(check_v3(d))
    if "V4" in selected:
        for d in days:
            rules.append(check_v4(d, prebook))
    if "V5" in selected:
        last_day = days[-1] if days else {}
        rules.append(check_v5(last_day, trip))
    if "V6" in selected:
        for d in days:
            rules.append(check_v6(d))
    if "V8" in selected:
        rules.append(check_v8(days, trip))
    if "V9" in selected:
        rules.append(check_v9(days, trip))
    if "V10" in selected:
        rules.append(check_v10(trip))
    if "V11" in selected:
        rules.append(check_v11(trip))
    if "V12" in selected:
        rules.append(check_v12(trip, as_of=as_of))
    if "V13" in selected:
        rules.append(check_v13(trip, days))

    # 总结
    fail = sum(1 for r in rules if r["status"] == "❌")
    warn = sum(1 for r in rules if r["status"] == "⚠️")
    pass_ = sum(1 for r in rules if r["status"] == "✅")

    phase = ROUND_PHASE.get(round_num) if round_num else None
    round_note = f"Round {round_num} · {phase}" if round_num else "全量复检"
    summary = {
        "round": round_num if round_num else 0,
        "phase": phase,
        "rules": rules,
        "summary": f"{pass_} 通过 / {warn} 警告 / {fail} 失败（{round_note}；**V7 用户禁忌需 AI 自行核对**）",
        "script_version": "3.3.0",
        "note": "V0 校验核心 schema；V8 只验证来源声明；V12 检查易变事实的核对与复核节点",
    }

    indent = 2 if args.pretty else None
    print(json.dumps(summary, ensure_ascii=False, indent=indent))

    return 1 if fail or (args.fail_on_warn and warn) else 0


if __name__ == "__main__":
    sys.exit(main())
