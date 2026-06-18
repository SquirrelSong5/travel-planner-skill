# 价格调研方法（v2.1.0 新增）

> 本文件是 SKILL.md Step 1 / Round 2 / Round 3 / Step 5 / Step 6 的价格调研规范。
> 配套：`references/planning.md` §7.2、`references/amap-mcp-usage.md` 场景 2 费用字段、`scripts/validate.py` V10。

---

## 1. 硬约束

- **禁止** `source: "ai-guess"` / `"memory"` / 空字符串
- **禁止** 无调研依据的整数价格（V10 会失败）
- 允许 `min` / `max` 区间（如餐饮人均 80–120），但必须写明 `source_ref`
- 免费项：`unit: "free"`，`min=max=0`，`source: "computed"` 或 `"official-site"`

### 合法 `source` 枚举

| source | 含义 |
|--------|------|
| `amap-mcp` | 高德 MCP `maps_search_detail.cost` 或 `maps_direction_*` 费用字段 |
| `amap-rest-api` | 高德 REST API 同上（降级路径） |
| `official-site` | 官方票务 / 景区 / 轮渡站 WebFetch |
| `ctrip-webfetch` | 携程机票 / 酒店 WebFetch 实查 |
| `meituan-webfetch` | 美团攻略 / 酒店 WebFetch |
| `computed` | 步行/骑行零元等可推导项 |

---

## 2. 统一 `price` 对象

```json
{
  "min": 35,
  "max": 35,
  "currency": "CNY",
  "unit": "per_person",
  "quantity": 3,
  "total_min": 105,
  "total_max": 105,
  "label": "船票",
  "source": "official-site",
  "source_ref": "厦门轮渡官网",
  "source_url": "https://www.xiamenferry.com/"
}
```

| `unit` | 含义 | `quantity` 默认 |
|--------|------|----------------|
| `per_person` | 按人头（门票、船票） | `party_size` |
| `per_order` | 按次/桌 | 1 |
| `per_night` | 每晚（酒店） | 泊数 |
| `fixed` | 固定总额 | 1 |
| `free` | 免费 | — |

`transports[]` 使用同结构，字段名为 **`fare`**（不是 `price`）。

---

## 3. 调研来源（按类别）

| 类别 | 首选数据源 | 写入位置 |
|------|-----------|---------|
| 餐厅 / 有 cost 的 POI | `maps_search_detail` → `cost` | `pois[].price` 或 `meals.*.main.price` |
| 门票 / 船票 | 官方站 WebFetch | `pois[].price` + `prebook[].price` |
| 免费景点 / 步行街 | 官方说明或高德 type | `unit: "free"` |
| 公交 / 地铁 | `maps_direction_transit_integrated` → `cost` / `transit_fee` | `transports[].fare` |
| 打车 | `maps_direction_driving` → `taxi_cost` | `transports[].fare` |
| 步行 / 骑行 | 零元 | `transports[].fare`，`source: "computed"` |
| 酒店 | 携程酒店 WebFetch / 高德酒店 | `hotel.price` + `prebook[].price` |
| 机票 | 携程机票 WebFetch | `prebook[].price` + `budget_summary.by_category.flights` |

**对齐原则**：从哪个平台查的价，就给哪个平台的 `source` + `source_url`。

---

## 4. 嵌入分轮流程（不新增 Round）

| 阶段 | AI 必做 |
|------|---------|
| **Step 1** | 收 `party_size`，写入 tripData 顶层 |
| **Round 2** | 调 `maps_direction_*` 时同步写 `transports[].fare`（与 path/duration 同一次调用） |
| **Round 3** | 调 `maps_search_detail` 时同步写 POI/meal 的 `price` |
| **Step 5** | prebook 官方站 + 携程实查后写 `prebook[].price` |
| **Step 6** | 汇总 `budget_summary`（分类小计 + 全程 + 人均），禁止心算编造 |

---

## 5. `budget_summary` 顶层汇总

```json
{
  "party_size": 3,
  "budget_summary": {
    "currency": "CNY",
    "by_category": {
      "transport_local": { "min": 120, "max": 180, "note": "市内公交/打车" },
      "food": { "min": 800, "max": 1200 },
      "tickets": { "min": 315, "max": 315 },
      "hotel": { "min": 1200, "max": 1500, "nights": 3 },
      "flights": { "min": 2400, "max": 3600, "note": "携程往返实查" }
    },
    "total_min": 4835,
    "total_max": 6195,
    "per_person_min": 1612,
    "per_person_max": 2065,
    "disclaimer": "价格为调研日参考，不含个人购物；机票/酒店以平台实时为准"
  }
}
```

- `hotel` / `flights`：**仅抽屉汇总**；抵达/离境段通过 `slot_costs[].attach` 挂在对应时间块（只计一次）
- 时间轴展示：**`pois[].slot_costs[]` 批注卡**（无 `source` 文案）；`price`/`fare` 仍写入 JSON 供 V10

---

## 7. 每段花销智能枚举（v2.2.0）

> 用户举例的「机票、机场路费、逛街、打车」**不是完整清单**。AI 必须为每个 `time-block` 扫描并写入 `slot_costs[]`。

| 信号 | 写入 `slot_costs` 项 | 调研来源 |
|------|---------------------|---------|
| Day1 抵达机场/高铁 | 出发机票、`attach: arrival` | `prebook[]` + direction `fare` |
| 末日离境 | 返程机票、`attach: departure` | `prebook[]` |
| `cat=scenery/culture` + 门票/预约 | 门票、讲解器、轮渡 | 官方站 + `maps_search_detail` |
| 绑定 `meal` | 早餐/午餐/晚餐 | `maps_search_detail.cost` |
| `next-leg` transport | 打车/公交/步行（0） | `transports[].fare` |
| `cat=shopping` | 逛街预算，`user_editable: true` | AI 给参考区间 |
| `requires_booking` | 预约/抢票费 | 同日 `prebook[]` |
| 活动体验 | 单项体验费 | 官方/高德 detail |

- `source` / `source_ref`：**仅 JSON + V10**；HTML 批注**不展示来源**
- `user_editable: true`：仅 discretionary（逛街、伴手礼）；其余为调研价不可改

---

## 6. V10 验证

部署前必须：

```bash
python scripts/validate.py trip_data.json --round 3 --pretty
python scripts/validate.py trip_data.json --pretty   # 全量含 V10
```

失败项见 `references/validation-rules.md` §V10。
