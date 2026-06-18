# examples/

本目录是 `assets/template.html` 模板的填充示例，方便：

1. **开发期验证模板渲染** —— 用 `tokyo-4n5d.json` 的数据填模板，能看到完整的最终 HTML 效果
2. **作为 AI 输出参考** —— AI 生成方案时，对照本 JSON 的结构填字段，不要漏字段、不要多字段
3. **测试增量修改** —— 改本 JSON 后重新渲染模板，验证修改后的效果

---

## 文件清单

- `tokyo-4n5d.json` — Tokyo 4 泊 5 日静态 demo 数据（含地图数据）

---

## Schema

> ⚠️ 这是简化的中文说明文档，不是机器可读的 JSON Schema。完整字段以 `tokyo-4n5d.json` 实例为准。

```typescript
{
  // ===== 顶层（必填）=====
  amap_key: string                // 高德 Web (JS) API Key（空字符串则地图降级为文字版）
  trip_name: string              // 行程名（HTML <title> 和 <h1> 用）
  date_range: string             // 例："2026-09-12 ~ 2026-09-16"
  n_days: string                 // 例："4 泊 5 日" / "3 泊 4 日"
  city: string                   // 主城市
  summary: string                // 一句话总结（带取舍说明），≤ 100 字
  party_size: number             // v2.1.0 必填：出行人数（价格 quantity 默认）

  // ===== 顶层（可选）=====
  weather_plan: string           // 整体天气策略（行程前说明）
  budget_summary?: {            // v2.1.0 推荐：全程花销汇总（抽屉展示）
    currency: string             // "CNY" | "JPY" 等
    by_category: {
      transport_local?: { min, max, note? }
      food?: { min, max }
      tickets?: { min, max }
      hotel?: { min, max, nights? }
      flights?: { min, max, note? }
    }
    total_min: number
    total_max: number
    per_person_min: number
    per_person_max: number
    disclaimer?: string
  }

  // ===== 价格对象（v2.1.0，POI/meal/prebook/hotel 复用）=====
  // PriceObject = {
  //   min, max, currency, unit, quantity?,
  //   total_min, total_max, label?,
  //   source, source_ref, source_url?
  // }
  // unit: per_person | per_order | per_night | fixed | free
  // source: amap-mcp | amap-rest-api | official-site | ctrip-webfetch | meituan-webfetch | computed

  // ===== 酒店（必填，1 个）=====
  hotel: {
    name: string
    address: string
    lng: number
    lat: number
    amap_uri: string
    why: string
    price?: PriceObject          // per_night；仅抽屉汇总，不在时间轴
    commute: [
      {
        day: number
        region: string
        duration_min: number
        mode: string              // 步行 / 地铁 / JR / 等
      }
    ]
  }

  // ===== 每日行程（必填，n_days 个）=====
  days: [
    {
      day: number                 // 1-based
      date: string                // YYYY-MM-DD
      weekday: string             // 周一 ~ 周日
      region: string              // 当天主区域
      theme: string               // 一句话当日主题
      weather: string             // 当天天气 + 温度
      weather_emoji: string       // ☀️ ⛅ ☁️ 🌧️
      weather_decision?: string   // 天气敏感日的决策说明（可选）

      // 地图相关（必填，否则地图渲染异常）
      center: [lng, lat]          // 地图中心 [经度, 纬度]
      zoom: number                // 地图缩放（11-16，越大越细）

      // POI 列表（按时间顺序，必填）
      pois: [
        {
          idx: number             // 1-based，在 transports 里引用
          time: string            // HH:MM
          name: string
          cat: string             // hotel / food / scenery / culture / shopping / transport
          lng: number             // 经度（用于地图 marker）
          lat: number             // 纬度
          duration_min: number    // 停留时间
          note?: string           // 用户备注 / 注意事项
          why?: string            // 为什么排这里
          weather_sensitive?: boolean
          indoor_backup?: string  // weather_sensitive=true 时必填
          requires_booking?: boolean
          links: {
            amap_navi?: string
            xhs?: string
            dianping?: string
          }
          price?: PriceObject     // v2.1.0 必填（V10 溯源）；与 slot_costs 并存
          slot_costs?: [          // v2.2.0 推荐：本时间段全部可能花销（批注 UI）
            {
              label: string       // 机票 / 船票 / 餐饮 / 打车 / 门票 / 逛街预算 …
              price: PriceObject  // user_editable: true 仅 discretionary（逛街等）
              attach?: "arrival" | "departure"  // 跨段一次性大项挂载点
              from_transport_idx?: number
            }
          ]
        }
      ],

      transports: [
        {
          from_idx: number
          to_idx: number
          mode: string
          duration_min: number
          description: string
          path?: [lng, lat][]
          distance_m?: number
          source?: string
          fare?: PriceObject      // v2.1.0 必填：next-leg 下 price-card
        }
      ],

      meals: {
        breakfast?: { main: { name, why, price?: PriceObject }, alt?: { name, why, price? } }
        lunch: { main: { name, why, price?: PriceObject }, alt?: { name, why, price? } }
        dinner: { main: { name, why, price?: PriceObject }, alt?: { name, why, price? } }
      }
    }
  ]

  // ===== 删了什么（必填，至少 1 条）=====
  deleted: [
    { item: string, reason: string }
  ]

  // ===== 提前订（必填，至少 1 条）=====
  prebook: [
    { item: string, deadline: string, url: string, note?: string, price?: PriceObject }
  ]

  // ===== 验证报告（可选但推荐）=====
  validation_report?: {
    round: number                 // 第几轮通过
    rules: [
      { id: "V1"..."V7", rule, status: "✅"|"⚠️"|"❌", note }
    ]
    summary: string
  }
}
```

---

## 字段填写规则

### 经纬度（lng, lat）

- **顺序**：先经度（lng），后纬度（lat）
- **范围**：日本 lng ≈ 130-146 / lat ≈ 26-46；中国 lng ≈ 73-135 / lat ≈ 3-54
- **精度**：6 位小数即可（米级精度）
- **数据源**：高德 `poi_search` / `poi_detail` 返回的 `location` 字段

### 交通方式 mode

| 值 | 含义 | 地图颜色 | 是否虚线 |
|----|------|---------|---------|
| `walking` | 步行 | 绿色 | 是 |
| `transit` | 公交（通用） | 蓝色 | 否 |
| `subway` / `metro` | 地铁 | 蓝色 | 否 |
| `bus` | 公交 | 蓝色 | 否 |
| `train` | 火车 | 蓝色 | 否 |
| `jr` | JR（日本） | 蓝色 | 否 |
| `driving` | 驾车 | 红色 | 否 |
| `biking` | 骑行 | 橙色 | 是 |

### 路径渲染 v1.3.0

| 字段 | 含义 | 优先级 |
|------|------|-------|
| `path` 存在且非空 | **画真实路网 polyline**（沿公路/步行道/公交线） | 高 |
| `path` 不存在/为空 | **画直线**（POI1→POI2 直线，**旧行为，向后兼容**） | 低（兜底）|

**AI 在 Step 3 必做的事**：每对相邻 POI 调 `maps_direction_walking/driving/bicycling/transit_integrated`，从返回的 `paths[].steps[].path` 或 `transits[].segments[].*.path` 提取 polyline 坐标，**写进 `transports[].path`**。**V2 验证（`duration_min`）和 polyline 提取是同一次 MCP 调用，零额外开销**。

### 类别 cat

| 值 | 含义 | 地图 marker 颜色 |
|----|------|----------------|
| `hotel` | 酒店 | 灰色 |
| `food` | 餐饮 | 棕色 |
| `scenery` | 风景 / 户外 | 绿色 |
| `culture` | 文化 / 寺庙 / 博物馆 | 紫色 |
| `shopping` | 购物 | 粉色 |
| `transport` | 交通 / 转场 | 蓝色 |

### 地图中心 + 缩放

- **center**：当天主区域的几何中心（不一定落在 POI 上）
- **zoom**：
  - 11：远郊（如富士山、整个镰仓）
  - 12-13：跨区（如新宿 + 机场）
  - 14：单区（如浅草寺周边）
  - 15-16：极细（如一个小型公园）

### URL

- **amap_navi**：`https://uri.amap.com/navigation?to={lng},{lat}&mode={car/walk/transit}`
- **xhs**：`https://www.xiaohongshu.com/search_result?keyword=<URL encoded 店名>`
- **dianping**：`https://www.dianping.com/search/keyword/0_0<店名>`

### 删减理由

每条 deleted 必须有 reason，且理由要具体：
- ✅ "Day 4 已排富士山 + 远郊强度大；加横滨会让 Day 4 变成 6AM 出门 11PM 返酒店"
- ❌ "时间不够"（太笼统）

---

## 模板渲染示例

要把本 JSON 渲染成 HTML，AI 在 Step 7 中需要做的事：

1. **替换顶层占位符**：`{{TRIP_NAME}}` / `{{DATE_RANGE}}` / `{{SUMMARY}}` 等
2. **填充 `window.tripData`**：把整个 JSON 转成 JS 对象字面量注入 `<script>` 块
3. **填充 `window.AMAP_KEY`**：高德 Web API Key（用户在 Step 1 提供）
4. **渲染 prebook 列表**：`#prebook-list` 由 JS `renderDrawerLists()` 从 `tripData.prebook` 动态渲染（支持 `**加粗**` mdLite）

简化版渲染脚本（仅供开发期验证）：

```python
import json
from pathlib import Path

data = json.loads(Path("examples/tokyo-4n5d.json").read_text())
tpl = Path("assets/template.html").read_text()

# 1. 顶层占位符
top_replacements = {
    "{{TRIP_NAME}}": data["trip_name"],
    "{{DATE_RANGE}}": data["date_range"],
    "{{N_DAYS}}": data["n_days"],
    "{{CITY}}": data["city"],
    "{{SUMMARY}}": data["summary"],
    "{{HOTEL_NAME}}": data["hotel"]["name"],
    "{{HOTEL_ADDRESS}}": data["hotel"]["address"],
    "{{HOTEL_WHY}}": data["hotel"]["why"],
    "{{HOTEL_AMAP_URI}}": data["hotel"]["amap_uri"],
}

# 2. deleted 块
data["deleted"]
replacements["{{DELETED_BLOCK}}"] = "\n".join(
    f'<li><span class="label">✗ {x["item"]}</span><span class="reason">{x["reason"]}</span></li>'
    for x in data["deleted"]
)

# 3. prebook 块
data["prebook"]

# 4. 注入 tripData JSON 到 <script>
# 把 data 转成 JS 字面量（用 json.dumps + 简单转义）
import json
trip_data_js = json.dumps(data, ensure_ascii=False, indent=2)

# 在 <script>window.tripData = { ... }</script> 里填入
```

**完整的渲染逻辑写在 SKILL.md 的 Step 7 里**（AI 直接生成最终 HTML）。

---

## 增量修改测试模式

### 测试"Day 2 的 X 换成 Y"

1. 复制 `tokyo-4n5d.json` → `tokyo-4n5d-modified.json`
2. 修改 `days[1].pois` 里某个 POI（name / 坐标 / links 等）
3. 重新跑模板渲染
4. 对比修改前后的 HTML

### 测试"加一天京都"

1. 在 `days` 数组末尾插入新 day
2. 给新 day 填 `pois` + `transports` + `center` + `zoom`
3. 更新 `n_days`（4 泊 5 日 → 5 泊 6 日）
4. 更新 `date_range`
5. 跑 V1-V7 验证
6. 重新渲染

### 测试"改酒店"

1. 改 `hotel` 对象（name / address / lng / lat）
2. 检查 `commute` 数组是否需要调整
3. 跑通勤圈校验（V1 衍生）
4. 必要时联动改 day 的 center / pois

### 测试"Day 2 太赶了，分两天"

1. 把 `days[1].pois` 拆成两个数组
2. 创建新 day 承接后半段
3. 调整 transport（最后一个 POI 到新 day 第一个 POI）
4. 更新 n_days + date_range

---

## 字段演变历史

### v2.2.0 (2026-06-18)

- **改版**：时间轴花销改为 **Word 批注式**（每时间段右侧汇总 `slot_costs[]`）；前端**不展示** `source`
- **新增**：`pois[].slot_costs[]` — AI 智能枚举该段全部可能花销（机票/路费仅为举例）
- **新增**：`price.user_editable` — 逛街等 discretionary 预算，用户浏览器 localStorage 自填
- `pois[].price` / `fare` 仍保留供 V10 溯源；无 `slot_costs` 时前端自动兜底聚合

### v2.1.0 (2026-06-18)

- **新增**：`party_size`、`budget_summary`、统一 `PriceObject`（`pois[].price`、`transports[].fare`、`meals.*.price`、`hotel.price`、`prebook[].price`）
- **新增**：V10 价格溯源验证；详见 `references/price-research.md`
- ~~时间轴渲染 price-card~~ → v2.2.0 改为段批注；抽屉「花销预估」区保留

### v1.3.0 (2026-06-17)

- **新增**：`transports[].path`（真实路网 polyline 坐标数组）+ `distance_m` + `source`
  - 原因：v1.3.0 起 HTML 地图渲染**沿路网真实路径**（不再画直线）
  - 数据源：高德 MCP `maps_direction_walking/driving/bicycling/transit_integrated` 返回的 `steps[].path` 或 `segments[].*.path`
  - 向后兼容：旧数据没填 `path` 字段，HTML 自动降级为直线
- **更新**：所有 `poi_search` / `route_walking` 等旧工具名 → 官方 `maps_*` 命名（详见 `references/amap-mcp-usage.md`）

### v0.2.0 (2026-06-17)

- **新增**：`amap_key` 顶层字段
- **重构**：每天用 `pois` + `transports` 取代原来的 `timeline`
  - 原因：地图渲染需要结构化的 POI（带 lng/lat）和 transport（带 mode）数据
  - timeline 那种"混入 transport 条目"的方式无法驱动地图
- **新增**：每天的 `center` + `zoom` 字段（地图初始化用）
- **新增**：hotel 的 `lng` / `lat` 字段（地图显示酒店位置，未来扩展用）

### v0.1.0 (2026-06-17)

- 初始版本：每天用 `timeline` 数组，混合 POI 和 transport 条目
