# Examples

`chengdu-2026-09-18.json` 是仓库的国内行程示例，用于验证数据、测试路线 URL 和渲染 HTML。

## 运行

```bash
python scripts/validate.py examples/chengdu-2026-09-18.json --pretty --fail-on-warn
python scripts/test_day_route_urls.py examples/chengdu-2026-09-18.json
python scripts/render_html.py assets/template.html examples/chengdu-2026-09-18.json -o /tmp/chengdu-trip.html
```

机器可读的核心结构见 [trip-schema.json](../references/trip-schema.json)。示例包含模板使用的扩展字段，因此 Schema 有意只约束核心必填结构。

## 文件命名

建议使用 `{城市拼音}-{出发日 YYYY-MM-DD}`：

```text
chengdu-2026-09-18.json
chengdu-2026-09-18.html
```

可用 `python scripts/trip_slug.py trip.json` 生成 slug。

## 安全与来源

- 不在示例中保存真实用户隐私或未公开行程；
- 不写入高德 Key，地图 Key 由浏览者在 HTML 页面内填写；
- 价格与路线的 `source` 应对应实际查询；
- `demo-estimate`、`note-derived` 等演示值不会通过严格校验。
