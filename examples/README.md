# Examples

`chengdu-2026-09-18.json` 是仓库的国内行程示例，用于验证数据、测试路线 URL，以及渲染同源 Markdown/HTML。

## 运行

```bash
python scripts/validate.py examples/chengdu-2026-09-18.json --pretty --fail-on-warn --as-of 2026-08-24
python scripts/test_day_route_urls.py examples/chengdu-2026-09-18.json
python scripts/render_markdown.py examples/chengdu-2026-09-18.json -o /tmp/chengdu-trip.md
python scripts/render_html.py assets/template.html examples/chengdu-2026-09-18.json -o /tmp/chengdu-trip.html
```

机器可读结构见 [trip-schema.json](../references/trip-schema.json)，包括五类平台覆盖、预订状态、Plan B、安全提醒和行前复核。

`--as-of` 只用于冻结示例的历史核对日期；真实行程应按当天运行 V12。

## 文件命名

建议使用 `{城市拼音}-{出发日 YYYY-MM-DD}`：

```text
chengdu-2026-09-18.json
chengdu-2026-09-18.md
chengdu-2026-09-18.html
```

可用 `python scripts/trip_slug.py trip.json` 生成 slug。

## 安全与来源

- 不在示例中保存真实用户隐私或未公开行程；
- 不写入高德 Key，地图 Key 由浏览者在 HTML 页面内填写；
- 价格与路线的 `source` 应对应实际查询；
- `source_coverage` 应包含五个平台各一项，并记录实际阶段、用途和证据链接；
- `demo-estimate`、`note-derived` 等演示值不会通过严格校验。
