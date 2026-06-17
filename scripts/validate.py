#!/usr/bin/env python3
"""
travel-planner 自动验证脚本（v1.1.0 新增，v1.5.0 强化）

用法：
    python scripts/validate.py <trip_data.json> [--check V1,V2,...] [--pretty]

行为：
    - 读 tripData JSON（与 examples/chengdu-3d.json 同 schema）
    - 跑 V1/V3/V4/V5/V6 五条**纯数据可验**规则（V2 通勤粗算用 Haversine 距离假设速度；
      V7 用户禁忌**必须 AI 调上下文判断**，脚本不验）
    - **v1.5.0 新增 V8**：transports[].path **MCP 必跑痕迹**——source 必须是 "amap-mcp"，
      path 必须是 ≥ 2 个真实坐标点（不是 2 个点的"直线"）→ 阻断 AI 凭 LLM 记忆
    - **v1.5.0 新增 V9**：V2 高德实算 vs 粗算对比——AI 自报"已用高德 route_* 实算"但
      duration_min 和 Haversine 粗算差 > 50% → 警告（说明 AI 没真跑高德）
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
import sys
from typing import Any


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
DRIVE_KMH = 40.0     # 市内驾车 40 km/h
# 通勤占当天行程 30% 阈值
V2_COMMUTE_RATIO_FAIL = 0.30
# 单段通勤 > 60 分钟强警告（与 V2 规则一致）

# V4 一日一重预约
V4_FAIL_PER_DAY = 2  # >= 2 条 prebook 算"一日多重"

# V5 末日返程缓冲
V5_BUFFER_HOURS_FAIL = 1.5  # 末日去机场缓冲 < 1.5h（国内航班）算失败
V5_BUFFER_HOURS_WARN = 2.0  # < 2h 警告

# V8 MCP 必跑痕迹
V8_MIN_PATH_POINTS = 3  # 真实路径至少 3 个点（直线就 2 个）
V8_STRAIGHT_LINE_RATIO = 0.005  # 中间点到 from→to 直线段 < 0.5% 总距离 算"近似直线"
# 0.5% 阈值说明：
# - 1km 距离偏差 < 5m → 算直线（LLM 编的假 polyline）
# - 1km 距离偏差 ≥ 5m → 算"沿路拐弯"（真路网 polyline）
# - 真实步行/驾车 500m 内街道本来就直，偏差 < 5m 正常
# - 但 LLM 凭记忆"编"的 polyline 一般**完全在直线上**（偏差 0），不会被误判
V8_ALLOWED_SOURCES = {"amap-mcp"}  # 唯一合法的 source 值

# V9 V2 高德实算 vs 粗算对比
V9_DURATION_RATIO_FAIL = 0.5  # 高德实算 vs Haversine 粗算 偏差 > 50% → 失败

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
    if mode == "walk":
        return d / WALK_KMH * 60
    if mode == "drive":
        return d / DRIVE_KMH * 60
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

    末日（is_last_day=True）跳过最远 POI 检查的"距离"判定——
    末日通常要赶机场/高铁站，POI 自然偏远。
    """
    center = day.get("center")
    pois = day.get("pois") or []
    if not center or not pois:
        return {"id": "V1", "rule": "区域一致性", "status": "⚠️", "note": "缺 center 或 pois 字段，跳过"}

    # 末日跳过：返程 POI 偏远是合理的
    if is_last_day:
        return {"id": "V1", "rule": "区域一致性", "status": "✅", "note": f"末日（{day.get('region', '?')}），跳过区域距离检查（返程 POI 偏远是合理的；用 V5 验缓冲）"}

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
    出发前 N 天的机票/酒店**不算**当日预约（启发式：note 里有「Day N」或「Day N 上午/下午」才算）。
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
        # 启发式：note 里提到 "Day N" 或 "Day N 上午/下午" 才算
        if f"Day {day_idx}" in note:
            # 排除"出发前 N 天"模式
            if "出发前" in note or "提前" in note:
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


# ===== V8（v1.5.0 新增）：MCP 必跑痕迹 =====

def _is_straight_line(path: list[list[float]], from_loc: tuple[float, float], to_loc: tuple[float, float]) -> bool:
    """检查 path 是否"近似直线"——AI 凭 LLM 记忆最容易犯的错：写 2-5 个直线排列的"假 polyline"。

    算法：path 任意中间点到 from→to 直线段的距离 < 5% 总距离 → 算直线。
    """
    if len(path) < 3:
        return True  # 2 个点本来就是直线

    def _point_to_segment_dist(px, py, x1, y1, x2, y2):
        """点到线段距离（经纬度用 km 算）。"""
        # 把经纬度当平面坐标（短距离够用）
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)

    x1, y1 = from_loc
    x2, y2 = to_loc
    total_d = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    if total_d == 0:
        return True

    # 检查中间点（去掉首末）
    mid_points = path[1:-1]
    for pt in mid_points:
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            continue
        px, py = float(pt[0]), float(pt[1])
        d_perp = _point_to_segment_dist(px, py, x1, y1, x2, y2)
        if d_perp / total_d < V8_STRAIGHT_LINE_RATIO:
            return True  # 中间点全在直线上 → 假 polyline
    return False


def check_v8(days: list[dict[str, Any]]) -> dict[str, Any]:
    """v1.5.0 新增：MCP 必跑痕迹。

    检查每天 transports[] 的 path 字段：
    - source 必须是 "amap-mcp"（不是 "ai-fallback" / "straight-line" / 空）
    - path 必须是 ≥ V8_MIN_PATH_POINTS 个真实坐标点
    - path 不能是"直线"（AI 凭 LLM 记忆编的假 polyline）
    - 缺 path / 缺 source / 直线 → 阻断

    阻断效果：返回 status="❌" → validate.py exit 1 → AI 必跑 MCP 重试
    """
    total_transports = 0
    missing_path = []
    bad_source = []
    short_path = []
    straight_line = []

    for d in days:
        day_label = f"Day {d.get('day', '?')}"
        transports = d.get("transports") or []
        for i, t in enumerate(transports):
            if not isinstance(t, dict):
                continue
            total_transports += 1
            seg_label = f"{day_label}.transports[{i}]"

            # 1. source 必填且必须是 "amap-mcp"
            src = t.get("source")
            if not src:
                bad_source.append(f"{seg_label}（缺 source 字段）")
                continue
            if src not in V8_ALLOWED_SOURCES:
                bad_source.append(f"{seg_label}（source={src}，合法值：{V8_ALLOWED_SOURCES}）")
                continue

            # 2. path 必填且 ≥ 2 个点
            path = t.get("path")
            if not path or not isinstance(path, list):
                missing_path.append(seg_label)
                continue
            if len(path) < 2:
                short_path.append(f"{seg_label}（{len(path)} 个点，< 2）")
                continue

            # 3. path 不能是"近似直线"（AI 凭 LLM 记忆编的）
            # 需要 from/to 坐标
            from_idx = t.get("from_idx")
            to_idx = t.get("to_idx")
            pois = d.get("pois") or []
            if from_idx is not None and to_idx is not None and from_idx < len(pois) and to_idx < len(pois):
                from_loc = get_loc(pois[from_idx])
                to_loc = get_loc(pois[to_idx])
                if from_loc and to_loc and _is_straight_line(path, from_loc, to_loc):
                    straight_line.append(f"{seg_label}（{len(path)} 个点全是直线排列，疑似 LLM 记忆编的）")

    if total_transports == 0:
        return {"id": "V8", "rule": "MCP 必跑痕迹（v1.5.0 新增）", "status": "✅", "note": "无 transport 段，跳过"}

    errors = []
    if bad_source:
        errors.append(f"{len(bad_source)} 段 source 不合法：{bad_source[:3]}{'...' if len(bad_source) > 3 else ''}")
    if missing_path:
        errors.append(f"{len(missing_path)} 段缺 path：{missing_path[:3]}{'...' if len(missing_path) > 3 else ''}")
    if short_path:
        errors.append(f"{len(short_path)} 段 path 太短：{short_path[:3]}{'...' if len(short_path) > 3 else ''}")
    if straight_line:
        errors.append(f"{len(straight_line)} 段 path 是直线（疑似 LLM 记忆）：{straight_line[:3]}{'...' if len(straight_line) > 3 else ''}")

    if errors:
        return {
            "id": "V8",
            "rule": "MCP 必跑痕迹（v1.5.0 新增）",
            "status": "❌",
            "note": f"❌ 必跑 MCP！共 {total_transports} 段 transport：{'；'.join(errors)}",
            "errors": {"bad_source": bad_source, "missing_path": missing_path, "short_path": short_path, "straight_line": straight_line},
        }

    return {
        "id": "V8",
        "rule": "MCP 必跑痕迹（v1.5.0 新增）",
        "status": "✅",
        "note": f"全部 {total_transports} 段 transport 都已必跑 MCP（source=amap-mcp，path ≥ 2 点且非直线）",
    }


# ===== V9（v1.5.0 新增）：V2 高德实算 vs 粗算对比 =====

def check_v9(days: list[dict[str, Any]]) -> dict[str, Any]:
    """v1.5.0 新增：V2 通勤时间必须 AI 用高德 MCP 实算。

    原理：validate.py 用 Haversine 距离 + 假设速度粗算通勤（V2）；
    AI 调高德 MCP `maps_direction_*` 拿真实通勤时间（V2.ai-amap）；
    两者偏差 > 50% → 说明 AI 没真跑高德 / 用了 LLM 记忆 / 时间不真实。

    阻断效果：偏差 > 50% → status="❌" → 必跑 MCP 重试
    """
    suspicious = []

    for d in days:
        day_label = f"Day {d.get('day', '?')}"
        transports = d.get("transports") or []
        for i, t in enumerate(transports):
            if not isinstance(t, dict):
                continue
            duration_ai = t.get("duration_min")
            if duration_ai is None:
                continue  # 没填 AI 通勤时间，V2 浏览器内粗算兜底
            mode = t.get("mode", "transit")
            seg_label = f"{day_label}.transports[{i}]"

            # 用 Haversine 算直线距离对应的粗算通勤
            from_idx = t.get("from_idx")
            to_idx = t.get("to_idx")
            pois = d.get("pois") or []
            if from_idx is None or to_idx is None or from_idx >= len(pois) or to_idx >= len(pois):
                continue
            from_loc = get_loc(pois[from_idx])
            to_loc = get_loc(pois[to_idx])
            if not from_loc or not to_loc:
                continue

            rough = commute_minutes(from_loc, to_loc, mode)
            if rough == 0:
                continue

            ratio = abs(duration_ai - rough) / rough
            if ratio > V9_DURATION_RATIO_FAIL:
                # 偏差过大
                if t.get("source") == "amap-mcp":
                    # source 是 amap-mcp 但偏差大 → AI 报告值不对
                    suspicious.append(
                        f"{seg_label}：AI 报 {duration_ai} min vs 粗算 {rough:.0f} min（偏差 {ratio*100:.0f}%，source=amap-mcp，疑似 AI 编的）"
                    )
                else:
                    # source 不是 amap-mcp → 阻断
                    suspicious.append(
                        f"{seg_label}：AI 报 {duration_ai} min vs 粗算 {rough:.0f} min（偏差 {ratio*100:.0f}%，source={t.get('source')}）"
                    )

    total_checked = sum(
        1
        for d in days
        for t in (d.get("transports") or [])
        if isinstance(t, dict) and t.get("duration_min") is not None
    )

    if total_checked == 0:
        return {"id": "V9", "rule": "V2 高德实算 vs 粗算（v1.5.0 新增）", "status": "✅", "note": "无 duration_min，跳过"}

    if suspicious:
        return {
            "id": "V9",
            "rule": "V2 高德实算 vs 粗算（v1.5.0 新增）",
            "status": "❌",
            "note": f"❌ 必跑高德 route_* 复核！共 {total_checked} 段，{len(suspicious)} 段偏差 > {V9_DURATION_RATIO_FAIL*100:.0f}%：{'；'.join(suspicious[:3])}{'...' if len(suspicious) > 3 else ''}",
            "suspicious": suspicious,
        }

    return {
        "id": "V9",
        "rule": "V2 高德实算 vs 粗算（v1.5.0 新增）",
        "status": "✅",
        "note": f"全部 {total_checked} 段 duration_min 与 Haversine 粗算偏差 < {V9_DURATION_RATIO_FAIL*100:.0f}%（AI 必跑过高德 MCP）",
    }


# ===== 主流程 =====

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("trip_json", help="tripData JSON 文件路径")
    p.add_argument("--check", default="V1,V2,V3,V4,V5,V6,V8,V9", help="逗号分隔的规则 ID，默认全跑（v1.5.0 起含 V8/V9 必跑 MCP 痕迹）")
    p.add_argument("--pretty", action="store_true", help="缩进输出")
    args = p.parse_args()

    with open(args.trip_json, "r", encoding="utf-8") as f:
        trip = json.load(f)

    days = trip.get("days") or []
    prebook = trip.get("prebook") or []
    selected = set(args.check.split(","))

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
        rules.append(check_v8(days))
    if "V9" in selected:
        rules.append(check_v9(days))

    # 总结
    fail = sum(1 for r in rules if r["status"] == "❌")
    warn = sum(1 for r in rules if r["status"] == "⚠️")
    pass_ = sum(1 for r in rules if r["status"] == "✅")

    summary = {
        "round": 1,
        "rules": rules,
        "summary": f"{pass_} 通过 / {warn} 警告 / {fail} 失败（**V7 用户禁忌需 AI 自行核对**）",
        "script_version": "1.5.0",
        "note": "V1.5.0 起：V2 是粗算（直线距离 + 假设速度），**真通勤必跑高德 route_* MCP**；V8 阻断 transports[].source !== 'amap-mcp'；V9 阻断 AI 报告值偏差 > 50%",
    }

    indent = 2 if args.pretty else None
    print(json.dumps(summary, ensure_ascii=False, indent=indent))

    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
