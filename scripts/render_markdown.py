#!/usr/bin/env python3
"""从 trip JSON 确定性生成可直接粘贴到对话中的 Markdown 攻略。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


PRIORITY_LABELS = {"must": "必须", "recommended": "建议", "optional": "可选"}
STATUS_LABELS = {
    "booked": "已完成",
    "not_booked": "待办理",
    "not_required": "无需办理",
    "unknown": "待确认",
}
SEVERITY_LABELS = {"notice": "提示", "warning": "注意", "critical": "重要"}
RECHECK_STATUS_LABELS = {"verified": "已核对", "due": "待复核", "unknown": "待确认"}
MODE_LABELS = {
    "walking": "步行",
    "walk": "步行",
    "transit": "公交/地铁",
    "subway": "地铁",
    "metro": "地铁",
    "bus": "公交",
    "driving": "驾车/打车",
    "taxi": "打车",
    "biking": "骑行",
    "train": "火车",
}
UNIT_LABELS = {
    "per_person": ("每人", "人合计"),
    "per_night": ("每晚", "晚合计"),
    "per_ticket": ("每张", "张合计"),
    "per_room": ("每间", "间合计"),
    "per_trip": ("每程", "程合计"),
}


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _md_text(value: Any) -> str:
    return _text(value).replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def _safe_url(value: Any) -> str:
    raw = _text(value)
    try:
        parsed = urlparse(raw)
    except ValueError:
        return ""
    return raw if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def _linked(label: Any, url: Any) -> str:
    title = _md_text(label)
    safe = _safe_url(url)
    return f"[{title}]({safe})" if safe else title


def _amount(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "?"
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")


def _price(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    if value.get("unit") == "free":
        return "免费"
    uses_total = value.get("total_min") is not None
    low = value.get("total_min", value.get("min"))
    high = value.get("total_max", value.get("max", low))
    if low is None and high is None:
        return ""
    currency = value.get("currency", "CNY")
    symbol = "¥" if currency == "CNY" else f"{currency} "
    result = f"{symbol}{_amount(low)}"
    if high is not None and high != low:
        result += f"–{symbol}{_amount(high)}"
    unit = _text(value.get("unit"))
    if not unit:
        return result
    unit_label, total_label = UNIT_LABELS.get(unit, (unit, f"{unit} 合计"))
    if uses_total:
        quantity = value.get("quantity")
        suffix = f"{_amount(quantity)} {total_label}" if isinstance(quantity, (int, float)) else "合计"
        return f"{result}（{suffix}）"
    return f"{result}（{unit_label}）"


def _point_name(day: dict[str, Any], trip: dict[str, Any], idx: Any) -> str:
    if idx == 0:
        return _text((trip.get("hotel") or {}).get("name")) or "酒店"
    for poi in day.get("pois") or []:
        if isinstance(poi, dict) and poi.get("idx") == idx:
            return _text(poi.get("name")) or f"POI {idx}"
    return f"POI {idx}"


def _plan_b_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def render_trip_markdown(trip: dict[str, Any]) -> str:
    """渲染完整攻略；HTML 和本文本必须消费同一份 trip 数据。"""
    lines: list[str] = []
    trip_name = _md_text(trip.get("trip_name") or "旅行攻略")
    lines.append(f"# {trip_name}")

    meta = [
        _md_text(trip.get("date_range")),
        _md_text(trip.get("city")),
        f"{trip.get('party_size')} 人" if trip.get("party_size") else "",
    ]
    if trip.get("n_days"):
        meta.insert(1, _md_text(trip.get("n_days")))
    lines.append(" · ".join(item for item in meta if item))

    if trip.get("summary"):
        lines.extend(["", _md_text(trip["summary"])])

    assumptions = trip.get("assumptions") or []
    if assumptions:
        lines.extend(["", "## 假设与待确认"])
        lines.extend(f"- {_md_text(item)}" for item in assumptions if _text(item))

    hotel = trip.get("hotel") or {}
    if hotel.get("name"):
        lines.extend(["", "## 住宿"])
        hotel_line = f"- {_linked(hotel.get('name'), hotel.get('amap_uri'))}"
        if hotel.get("address"):
            hotel_line += f"：{_md_text(hotel['address'])}"
        lines.append(hotel_line)
        if hotel.get("why"):
            lines.append(f"- 选择理由：{_md_text(hotel['why'])}")
        hotel_price = _price(hotel.get("price"))
        if hotel_price:
            lines.append(f"- 住宿预算：{hotel_price}")

    lines.extend(["", "## 每日行程"])
    for day in trip.get("days") or []:
        if not isinstance(day, dict):
            continue
        heading = f"### Day {day.get('day', '?')} · {_md_text(day.get('date'))} · {_md_text(day.get('region'))}"
        lines.extend(["", heading])
        day_meta = [
            _md_text(day.get("theme")),
            " ".join(filter(None, [_md_text(day.get("weather_emoji")), _md_text(day.get("weather"))])),
        ]
        if any(day_meta):
            lines.append(" · ".join(item for item in day_meta if item))

        for poi in day.get("pois") or []:
            if not isinstance(poi, dict):
                continue
            time = _md_text(poi.get("time")) or "待定"
            duration = poi.get("duration_min")
            duration_text = f"，约 {_amount(duration)} 分钟" if isinstance(duration, (int, float)) else ""
            lines.append(f"- **{time}｜{_md_text(poi.get('name'))}**{duration_text}")
            detail = poi.get("note") or poi.get("why")
            if detail:
                lines.append(f"  - {_md_text(detail)}")
            price = _price(poi.get("price"))
            if price:
                lines.append(f"  - 费用：{price}")

        transports = [item for item in day.get("transports") or [] if isinstance(item, dict)]
        if transports:
            lines.append("- **主要交通**")
            for item in transports:
                from_name = _point_name(day, trip, item.get("from_idx"))
                to_name = _point_name(day, trip, item.get("to_idx"))
                duration = item.get("duration_min")
                duration_text = f"，约 {_amount(duration)} 分钟" if isinstance(duration, (int, float)) else ""
                lines.append(
                    f"  - {_md_text(from_name)} → {_md_text(to_name)}："
                    f"{_md_text(MODE_LABELS.get(item.get('mode'), item.get('mode')))}{duration_text}"
                )

        meals = day.get("meals") or {}
        if isinstance(meals, dict):
            meal_lines = []
            for key, label in (("breakfast", "早餐"), ("lunch", "午餐"), ("dinner", "晚餐")):
                block = meals.get(key)
                if not isinstance(block, dict) or not isinstance(block.get("main"), dict):
                    continue
                main = block["main"]
                text = f"  - {label}：{_md_text(main.get('name'))}"
                if main.get("price"):
                    text += f"，{_price(main['price'])}"
                alt = block.get("alt") or block.get("alt1")
                if isinstance(alt, dict) and alt.get("name"):
                    text += f"；备选 {_md_text(alt['name'])}"
                meal_lines.append(text)
            if meal_lines:
                lines.append("- **餐饮**")
                lines.extend(meal_lines)

        for plan_b in _plan_b_items(day.get("plan_b")):
            lines.append(f"- **Plan B｜触发条件：{_md_text(plan_b.get('trigger'))}**")
            lines.append(f"  - 替代安排：{_md_text(plan_b.get('alternative'))}")
            if plan_b.get("impact"):
                lines.append(f"  - 调整影响：{_md_text(plan_b['impact'])}")

        for note in day.get("safety_notes") or []:
            if isinstance(note, dict):
                lines.append(f"- **安全提醒：{_md_text(note.get('risk'))}** — {_md_text(note.get('action'))}")
            elif _text(note):
                lines.append(f"- **安全提醒** — {_md_text(note)}")

    prebook = [item for item in trip.get("prebook") or [] if isinstance(item, dict)]
    if prebook:
        lines.extend(["", "## 预订与办理"])
        for item in prebook:
            priority = PRIORITY_LABELS.get(item.get("priority"), _text(item.get("priority")) or "未分级")
            status = STATUS_LABELS.get(item.get("status"), _text(item.get("status")) or "待确认")
            line = f"- **[{priority}｜{status}] {_linked(item.get('item') or item.get('title'), item.get('url'))}**"
            if item.get("deadline"):
                line += f"：{_md_text(item['deadline'])}"
            lines.append(line)
            details = []
            if item.get("id_required") is True:
                details.append("需要实名/证件")
            if item.get("note"):
                details.append(_md_text(item["note"]))
            if details:
                lines.append(f"  - {'；'.join(details)}")

    safety_notes = [item for item in trip.get("safety_notes") or [] if isinstance(item, dict)]
    if safety_notes:
        lines.extend(["", "## 安全提醒"])
        for item in safety_notes:
            severity = SEVERITY_LABELS.get(item.get("severity"), _text(item.get("severity")) or "提示")
            applies = f"（{_md_text(item['applies_to'])}）" if item.get("applies_to") else ""
            lines.append(
                f"- **{severity}｜{_md_text(item.get('risk'))}**{applies}：{_md_text(item.get('action'))}"
            )

    rechecks = [item for item in trip.get("rechecks") or [] if isinstance(item, dict)]
    if rechecks:
        lines.extend(["", "## 行前复核"])
        for item in rechecks:
            status = RECHECK_STATUS_LABELS.get(item.get("status"), _text(item.get("status")) or "待确认")
            due = f"，{_md_text(item['recheck_at'])[:10]} 前" if item.get("recheck_at") else ""
            lines.append(f"- **[{status}] {_md_text(item.get('item'))}**{due}")
            if item.get("note"):
                lines.append(f"  - {_md_text(item['note'])}")
            if item.get("source_ref"):
                lines.append(f"  - 来源：{_linked(item.get('source') or '查看', item['source_ref'])}")

    budget = trip.get("budget_summary") or {}
    if isinstance(budget, dict) and (budget.get("total_min") is not None or budget.get("total_max") is not None):
        lines.extend(["", "## 预算"])
        lines.append(f"- 总预算：{_price(budget)}")
        if budget.get("note"):
            lines.append(f"- {_md_text(budget['note'])}")

    if trip.get("weather_plan"):
        lines.extend(["", "## 天气策略", _md_text(trip["weather_plan"])])

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trip_json", type=Path)
    parser.add_argument("-o", "--output", type=Path, help="写入 Markdown；省略时输出到 stdout")
    args = parser.parse_args()

    trip = json.loads(args.trip_json.read_text(encoding="utf-8"))
    rendered = render_trip_markdown(trip)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"✅ wrote {args.output}")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
