#!/usr/bin/env python3
"""将 tripData JSON 注入 template.html，输出可部署的单文件 HTML。

用法：
  python scripts/render_html.py assets/template.html trip.json -o out.html
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def inject_trip_data(html: str, trip: dict) -> str:
    marker = "window.tripData = "
    start = html.find(marker)
    if start < 0:
        raise ValueError("template 中未找到 window.tripData")
    brace = html.find("{", start + len(marker))
    if brace < 0:
        raise ValueError("window.tripData 后未找到 {")
    depth = 0
    end = brace
    for i in range(brace, len(html)):
        ch = html[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    trip_json = json.dumps(trip, ensure_ascii=False, indent=2)
    html = html[:brace] + trip_json + html[end:]

    hotel = trip.get("hotel") or {}
    repl = {
        "{{TRIP_NAME}}": trip.get("trip_name", ""),
        "{{DATE_RANGE}}": trip.get("date_range", ""),
        "{{N_DAYS}}": trip.get("n_days", ""),
        "{{CITY}}": trip.get("city", ""),
        "{{SUMMARY}}": trip.get("summary", ""),
        "{{HOTEL_NAME}}": hotel.get("name", ""),
        "{{HOTEL_ADDRESS}}": hotel.get("address", ""),
        "{{HOTEL_WHY}}": hotel.get("why", ""),
        "{{HOTEL_AMAP_URI}}": hotel.get("amap_uri", "#"),
    }
    for k, v in repl.items():
        html = html.replace(k, v if v is not None else "")

    title = trip.get("trip_name", "行程")
    dr = trip.get("date_range", "")
    if dr:
        title = f"{title} · {dr}"
    html = re.sub(r"<title>[^<]*</title>", f"<title>{title}</title>", html, count=1)
    return html


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("template", type=Path)
    ap.add_argument("trip_json", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args()

    html = args.template.read_text(encoding="utf-8")
    trip = json.loads(args.trip_json.read_text(encoding="utf-8"))
    out = inject_trip_data(html, trip)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(out, encoding="utf-8")
    print(f"✅ wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
