# 价格研究

## 原则

- 价格是查询时点的区间，不是承诺；
- 所有区间写清人数、晚数、张数和含税口径；
- 官方票价优先官方，酒店/机票可用国内 OTA；
- 无数据时写未知，不用模型记忆补数字；
- `scripts/seed_prices.py` 只生成演示/迁移值，不是调研。

## 标准对象

```json
{
  "min": 80,
  "max": 120,
  "currency": "CNY",
  "unit": "per_person",
  "quantity": 2,
  "total_min": 160,
  "total_max": 240,
  "label": "晚餐",
  "source": "meituan-webfetch",
  "source_ref": "页面或查询条件",
  "checked_at": "2026-08-24"
}
```

`unit` 常见值：

- `per_person`
- `per_night`
- `per_ticket`
- `fixed`
- `free`

## 来源

| 类别 | 首选 | 备选 |
| --- | --- | --- |
| 景区/场馆 | 官方票务或公告 | 国内 OTA，标明差异 |
| 酒店 | 国内 OTA 实时搜索 | 酒店官网/电话信息 |
| 航班/火车 | 航司/铁路官方、国内 OTA | 无可靠数据则未知 |
| 公交/地铁 | 运营方或地图路线结果 | 按规则计算并标 `computed` |
| 餐饮 | 美团/餐厅公开菜单/地图详情 | 只给宽区间并说明依据 |

## 汇总

不要重复计算。例如 `prebook` 中的酒店价格若也出现在 `hotel.price`，预算汇总只能计一次。汇总至少区分交通、住宿、门票、餐饮和可选购物，并给总区间。

严格校验拒绝 `estimate`、`demo-estimate`、`note-derived`、`ai-guess` 和 `memory`。重新调研后应替换整个证据对象，而不是只改 `source` 字符串。
