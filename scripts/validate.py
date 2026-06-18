#!/usr/bin/env python3
"""
travel-planner 自动验证脚本（v1.1.0 新增，v1.5.0 强化）

用法：
    python scripts/validate.py <trip_data.json> [--round 1|2|3] [--check V1,V2,...] [--pretty]

行为：
    - 读 tripData JSON（与 examples/chengdu-2026-09-18.json 同 schema）
    - 跑 V1/V3/V4/V5/V6 五条**纯数据可验**规则（V2 通勤粗算用 Haversine 距离假设速度；
      V7 用户禁忌**必须 AI 调上下文判断**，脚本不验）
    - **v1.5.0 三阶段分轮筛检**：--round 1=结构(V1,V4) 2=时空(V2,V5,V8,V9) 3=体验(V3,V6)
    - **v1.5.0 新增 V8**：transports[].path **MCP 必跑痕迹**
    - **v1.5.0 新增 V9**：通勤时间下限（v2.2.3 只拦过快，不拦实算比粗算慢）
    - 输出 JSON validation_report（stdout）
    - 退出码：全通过 → 0；有失败 → 1

为什么是硬约束：
    - SKILL.md / multi-turn-protocol.md 都规定 AI 必须跑这条命令
    - 输出 JSON 必须嵌进 tripData.validation_report
    - template.html 浏览器端 JS 会用同样规则**强制重算**（不依赖 AI 的 self-report）
    - **v1.5.0 起 V8 阻断 AI 凭 LLM 记忆**：transports[].source !== "amap-mcp" → ❌
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
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
# 通勤占当天行程 50% 阈值（v1.5.0 调整：远程日河口湖→新宿 80km 通勤本就占大头，30% 太严）
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
V10_BAD_SOURCES = frozenset({"", "ai-guess", "memory"})
V10_BUDGET_TOLERANCE = 0.15  # budget_summary 与明细加总偏差 > 15% → 警告

# v1.5.0 三阶段分轮筛检：--round N 只跑当轮子集（见 references/iteration-rounds.md）
ROUND_CHECKS: dict[int, tuple[str, ...]] = {
    1: ("V1", "V4", "V11"),
    2: ("V2", "V5", "V8", "V9", "V13"),
    3: ("V3", "V6", "V8", "V10"),
}
ROUND_PHASE: dict[int, str] = {
    1: "结构筛",
    2: "时空筛",
    3: "体验筛",
}
DEFAULT_CHECKS = ("V1", "V2", "V3", "V4", "V5", "V6", "V8", "V9", "V10", "V11", "V13")

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
    """餐厅到主区域中心距离。"""
    center = day.get("center")
    meals = day.get("meals") or {}
    if not center:
        return {"id": "V3", "rule": "餐厅区域匹配", "status": "⚠️", "note": "缺 center 字段"}

    worst_d = 0.0
    worst_meal = None
    worst_rest = None
    for meal_name, meal in meals.items():
        if not isinstance(meal, dict):
            continue
        for tag in ("main", "alt1", "alt2"):
            r = meal.get(tag) or {}
            loc = get_loc(r)
            if loc is None:
                continue
            d = haversine_km(tuple(center), loc)
            if d > worst_d:
                worst_d = d
                worst_meal = meal_name
                worst_rest = r.get("name", "?")

    if worst_d == 0.0:
        return {"id": "V3", "rule": "餐厅区域匹配", "status": "✅", "note": "无餐厅坐标字段可验（正常）"}

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

    flight = flights[0]
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
    """检查 outdoor POI 是否配 indoor_backup。"""
    pois = day.get("pois") or []
    if not pois:
        return {"id": "V6", "rule": "户外天气敏感", "status": "✅", "note": "无 POI"}

    weather = (day.get("weather") or "").lower()
    bad_weather = any(k in weather for k in ("雨", "雪", "雷", "storm", "rain", "snow"))

    outdoor_pois = [p for p in pois if p.get("type") == "outdoor" or any(k in (p.get("tags") or []) for k in ("outdoor", "户外", "露台", "天台", "观景"))]
    if not outdoor_pois:
        return {"id": "V6", "rule": "户外天气敏感", "status": "✅", "note": "无户外 POI"}

    if not bad_weather:
        return {"id": "V6", "rule": "户外天气敏感", "status": "✅", "note": f"天气好（{day.get('weather')}），{len(outdoor_pois)} 个户外 POI 不强制要 indoor_backup"}

    missing = [p.get("name", "?") for p in outdoor_pois if not p.get("indoor_backup")]
    if missing:
        return {"id": "V6", "rule": "户外天气敏感", "status": "❌", "note": f"天气{day.get('weather')}，户外 POI 缺 indoor_backup：{'、'.join(missing)}"}
    return {"id": "V6", "rule": "户外天气敏感", "status": "✅", "note": f"户外 POI 均配 indoor_backup"}


# ===== V8：MCP 必跑痕迹（source + duration_min）=====

def check_v8(days: list[dict[str, Any]], trip: dict[str, Any] | None = None) -> dict[str, Any]:
    """每段 transport 须有高德实算来源与 duration_min（v2.3.0 起不再要求 path）。"""
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
        return {"id": "V8", "rule": "MCP 必跑痕迹", "status": "✅", "note": "无 transport 段，跳过"}

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
            "rule": "MCP 必跑痕迹",
            "status": "❌",
            "note": f"❌ 共 {total_transports} 段 transport：{'；'.join(errors)}。请 MCP/REST maps_direction_* 实算（见 amap-mcp-usage §2）。",
            "errors": {"bad_source": bad_source, "missing_duration": missing_duration},
        }

    return {
        "id": "V8",
        "rule": "MCP 必跑痕迹",
        "status": "✅",
        "note": f"全部 {total_transports} 段 transport 含合法 source 与 duration_min",
    }


# ===== V9（v1.5.0 新增，v2.2.3 修正）：通勤时间下限 =====

def check_v9(days: list[dict[str, Any]], trip: dict[str, Any] | None = None) -> dict[str, Any]:
    """v1.5.0 新增：transports[].duration_min 必须来自高德实算。

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
            "status": "✅",
            "note": "无 hotel 坐标，跳过",
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


# ===== V10（v2.1.0 新增）：价格溯源 =====

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
            "rule": "价格溯源（v2.1.0 新增）",
            "status": "❌",
            "note": f"❌ {len(errors)} 项缺价或无溯源：{errors[:4]}{'...' if len(errors) > 4 else ''}",
            "errors": errors,
        }
    if warnings:
        return {
            "id": "V10",
            "rule": "价格溯源（v2.1.0 新增）",
            "status": "⚠️",
            "note": "；".join(warnings),
            "warnings": warnings,
        }
    n_poi = sum(len(d.get("pois") or []) for d in days)
    n_trans = sum(len(d.get("transports") or []) for d in days)
    return {
        "id": "V10",
        "rule": "价格溯源（v2.1.0 新增）",
        "status": "✅",
        "note": f"全部 {n_poi} POI + {n_trans} transport + 餐食均有 source 标价",
    }


# ===== V11（v2.2.1 新增）：prebook 禁止国际 OTA =====

_FOREIGN_OTA_SUFFIXES = ("booking.com", "agoda.com", "expedia.com")


def _is_foreign_ota_url(url: str) -> bool:
    try:
        host = (urlparse(url.strip()).hostname or "").lower().replace("www.", "")
    except Exception:
        return False
    if not host:
        return False
    if host.endswith("ctrip.com"):
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
            "rule": "prebook 国内 OTA 链接（v2.2.1）",
            "status": "❌",
            "note": f"禁止 trip.com / Booking 等国际 OTA，改 flights.ctrip.com 等：{bad[0]}{'…' if len(bad) > 1 else ''}",
            "bad_urls": bad,
        }
    return {
        "id": "V11",
        "rule": "prebook 国内 OTA 链接（v2.2.1）",
        "status": "✅",
        "note": "prebook 链接均为国内携程深链或官方站",
    }


# ===== 主流程 =====

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("trip_json", help="tripData JSON 文件路径")
    p.add_argument(
        "--round",
        type=int,
        choices=(1, 2, 3),
        help="v1.5.0 三阶段分轮筛检：1=结构(V1,V4) 2=时空(V2,V5,V8,V9) 3=体验(V3,V6)",
    )
    p.add_argument(
        "--check",
        default=None,
        help="逗号分隔的规则 ID；默认全跑；与 --round 同时用时 --check 优先",
    )
    p.add_argument("--pretty", action="store_true", help="缩进输出")
    args = p.parse_args()

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

    rules = []
    n_days = len(days)
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
        "script_version": "1.5.0",
        "note": "v1.5.0 三阶段分轮筛检：--round 1|2|3 见 references/iteration-rounds.md；V2 粗算 + 高德实算；V8/V9 阻断假 MCP 痕迹",
    }

    indent = 2 if args.pretty else None
    print(json.dumps(summary, ensure_ascii=False, indent=indent))

    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
