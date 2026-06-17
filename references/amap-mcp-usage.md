# 高德地图 MCP 使用指南（v1.3.0 修正工具名 + 真实路径）

> 本文件按"5 个使用场景"组织，每个场景给出高德 MCP 的工具名、调用模式、注意事项。
> 适配本 skill 的 7 步流程 + V1-V7 自动验证。
> 接入方式见 SKILL.md 的"数据源"小节（需要高德 Key）。

> **v1.3.0 重要修正**：
> 1. 工具名从旧版（`geocode` / `poi_search` / `poi_detail` / `route_walking` 等）**改为官方 MCP 实际命名**（`maps_geo` / `maps_text_search` / `maps_search_detail` / `maps_direction_walking` 等）——之前命名不规范，AI 调不到。
> 2. **新增「路线规划 → 真实路径」完整工作流**：AI 在 Step 3 调 `maps_direction_*` 不仅拿通勤时间，**还提取 polyline 坐标写进 `tripData.transports[].path`**，HTML 用真实路网路径渲染（不再是直线）。
>
> AI 实际调时**按自己工具列表里看到的为准**（可能是 `maps_geo` 也可能本地装的是 `amap_geocode` 等变体），本表给的是官方 `@amap/amap-maps-mcp-server` 的标准命名。

---

## 0. 硬约定：经纬度格式

**全文统一使用 `lng,lat`（先经度后纬度）**，与高德 `location` 字段定义一致。

| 工具 | 入参格式 | 示例 |
|------|---------|------|
| `maps_geo` 返回 | `lng,lat` 字符串 | `"116.397,39.908"`（天安门） |
| `maps_direction_*` 入参 origin/destination | `lng,lat` | `"139.7967,35.7148"` |
| `maps_distance` 入参 origins/destination | `lng,lat` | 同上 |
| `maps_text_search` 返回 POI | `location: "lng,lat"` | `"116.397,39.908"` |

**判定方法**：东经 (E) > 0、北纬 (N) > 0，**第一个数字 > 100 通常是经度**（北京 lng≈116、lat≈40）。

---

## 高德 MCP 工具速查（v1.3.0 官方命名）

| 工具名 | 功能 | 输入关键字段 | 输出关键字段 |
|--------|------|------------|------------|
| `maps_geo` | 地址 → 经纬度 | `address`, `city`(可选) | `location` |
| `maps_regeocode` | 经纬度 → 地址 | `location` | `addressComponent`, `formatted_address` |
| `maps_ip_location` | IP 定位 | `ip`(可选) | `location`, `city` |
| `maps_text_search` | 关键词搜 POI | `keywords`, `city`(可选) | `pois[]` |
| `maps_around_search` | 周边半径搜 POI | `keywords`, `location`, `radius`(可选) | `pois[]` |
| `maps_search_detail` | POI 详情 | `id` | `location`, `address`, `city`, `type`, `cost`, `rating`, `opentime2` |
| `maps_distance` | 多模式距离测量 | `origins[]`, `destination`, `type`(1:直线 2:驾车 3:步行) | `results[]` (含 distance/duration) |
| **`maps_direction_walking`** | **步行路径规划** | `origin`, `destination` | `paths[]` (含 distance/duration/**`steps[]` 含 `path` polyline**) |
| **`maps_direction_driving`** | **驾车路径规划** | `origin`, `destination` | `paths[]` (含 distance/duration/**`steps[]` 含 `path` polyline**) |
| **`maps_bicycling`** | **骑行路径规划** | `origin`, `destination` | `paths[]` (含 distance/duration/**`steps[]` 含 `path` polyline**) |
| **`maps_direction_transit_integrated`** | **公交路径规划**（综合火车/公交/地铁） | `origin`, `destination`, `city`, `cityd`(跨城) | `transits[]` (含 distance/duration/**`segments[]` 含 `bus/railway/walking` 各段 polyline**) |
| `maps_weather` | 城市天气 | `city` 或 `adcode` | `forecasts[]` |

> **路线类 4 个工具返回结构差异**：
> - 步行/驾车/骑行：`paths[].steps[].path` = `[{lng,lat}, {lng,lat}, ...]` 坐标数组
> - 公交：`transits[].segments[]`，每段类型不同（`WALK` / `BUS` / `RAILWAY` / `TRANSFER`），**每段都有 `path`**（步行段必有，公交/地铁段是线路坐标数组）

---

## 场景 1：找景点（Step 2 清单分组 + Step 3 区域设计）

### 用 `maps_text_search` 关键词搜索

```
工具：maps_text_search
输入：
  keywords: "浅草寺"
  city: "东京"
输出：pois[]（含 name/location/address/type 等）
```

**使用模式**：
- 用户说"想去浅草寺" → 直接 `maps_text_search keywords="浅草寺" city="东京"`
- 用户说"想找涩谷附近的夜景点" → `maps_around_search keywords="夜景" location="涩谷站经纬度" radius=2000`
- 城内轻松组 → `maps_text_search keywords="<类型>" city="<城市>"` 拿 Top 5-10
- 远郊组 → `maps_text_search keywords="<景点名>"` 单点搜

### 用 `maps_search_detail` 查详情

```
工具：maps_search_detail
输入：id（从 pois[] 拿）
输出：完整字段，含 address/city/type/cost/rating/opentime2
```

**使用场景**：
- 确认景点类型（type 字段判断是否户外 / 是否需要预约）
- 取 cost 字段判断预算（v1.2.0 起**餐厅硬信号主要来源**）
- 取 opentime2 字段 → Step 5 票务

---

## 场景 2：规划路线（V2 验证 + v1.3.0 真实路径）

> **v1.3.0 重大变化**：路线规划现在有**两个目的**——
> 1. **V2 验证**（用通勤时间）：判断一天里通勤占比是否合理
> 2. **真实路径渲染**（用 polyline 坐标）：让 HTML 地图显示**沿公路/步行道/公交线**的路径，**不再是直线**
>
> **两件事用同一个 MCP 调用**——`maps_direction_*` 返回值**同时含 distance/duration 和 polyline 坐标**。

### 2.1 模式选择

| 距离/场景 | 首选模式 | 备选 |
|----------|---------|------|
| < 1.5km 且无障碍 | `maps_direction_walking` | `maps_distance type=3` |
| 1.5-10km（市内）| `maps_direction_transit_integrated` | `maps_distance type=1`（直线）|
| > 10km（跨城/远郊）| `maps_direction_driving` | `maps_distance type=2` |
| 适合骑行（平坦城市/景区）| `maps_bicycling` | `maps_distance type=3` |

### 2.2 完整调用模式：拿真实 polyline

**以步行路线为例**：

```
工具：maps_direction_walking
输入：
  origin: "139.7967,35.7148"      # 浅草寺经纬度（lng,lat）
  destination: "139.8107,35.7101"  # 晴空塔经纬度
输出：
{
  "status": "1",
  "message": "OK",
  "route": {
    "origin": "139.7967,35.7148",
    "destination": "139.8107,35.7101",
    "paths": [
      {
        "distance": "1234",   # 米
        "duration": "900",    # 秒（15 分钟）
        "steps": [
          {
            "instruction": "向东南步行 50 米",
            "path": "139.7967,35.7148;139.7970,35.7145;139.7975,35.7140;..."  # ← 这个就是 polyline
            "distance": "50",
            "duration": "40"
          },
          ...
        ]
      }
    ]
  }
}
```

**关键发现**：`steps[].path` 是一串 `;` 分隔的 `lng,lat` 字符串。**这就是要写进 `tripData.transports[].path` 的东西**。

### 2.3 polyline 提取 + 写进 tripData

**AI 拿到 MCP 返回后的处理流程**：

```python
# 1. 调 MCP（伪代码）
result = call_mcp("maps_direction_walking", {
    "origin": "139.7967,35.7148",
    "destination": "139.8107,35.7101"
})

# 2. 提取真实 polyline（拼接所有 step.path）
all_points = []
for path in result["paths"]:
    for step in path["steps"]:
        for coord in step["path"].split(";"):
            lng, lat = coord.split(",")
            all_points.append([float(lng), float(lat)])

# 3. 写进 tripData
tripData["days"][day_idx]["transports"][i]["path"] = all_points
#  + "duration_sec": int(path["duration"])
#  + "distance_m": int(path["distance"])
```

**公交路线更复杂**（多段拼接）：

```python
# maps_direction_transit_integrated 返回
result = call_mcp("maps_direction_transit_integrated", {...})

all_points = []
for transit in result["transits"]:  # 可能有 3-5 个方案，挑第一个或最佳
    for segment in transit["segments"]:
        # WALK 段：步行 polyline
        if segment.get("walking") and segment["walking"].get("path"):
            for coord in segment["walking"]["path"].split(";"):
                lng, lat = coord.split(",")
                all_points.append([float(lng), float(lat)])
        # BUS 段：公交车线路坐标
        elif segment.get("bus") and segment["bus"].get("path"):
            for coord in segment["bus"]["path"].split(";"):
                lng, lat = coord.split(",")
                all_points.append([float(lng), float(lat)])
        # RAILWAY 段：地铁线
        elif segment.get("railway") and segment["railway"].get("path"):
            for coord in segment["railway"]["path"].split(";"):
                lng, lat = coord.split(",")
                all_points.append([float(lng), float(lat)])
```

### 2.4 tripData.transports schema（v1.3.0 新增）

```json
{
  "from_idx": 0,
  "to_idx": 1,
  "mode": "walking",          // walking | biking | transit | driving
  "duration_min": 15,
  "distance_m": 1234,
  "path": [                   // ← v1.3.0 新增：真实路网 polyline（可选，没填则用直线）
    [139.7967, 35.7148],
    [139.7970, 35.7145],
    [139.7975, 35.7140]
  ],
  "source": "amap-mcp"        // ← 标识来源（"amap-mcp" | "ai-amap" | "ai-fallback" | "straight-line"）
}
```

**渲染优先级**（template.html 自动判断）：
1. `path` 存在且非空 → **画真实路网 polyline**（沿公路/步行道/公交线）
2. `path` 不存在/为空 → **画直线**（POI1→POI2 直线，旧行为，**保留向后兼容**）

### 2.5 V2 验证逻辑（用 `duration_sec`）

**`scripts/validate.py` 的 check_v2 不变**（仍基于 POI 时间块），但 AI 报告的 V2 备注里**应附上每段的 `duration_sec` / `distance_m`**，让用户看到"实算通勤时长"。

### 2.6 用 `maps_distance` 快速测距

```
工具：maps_distance
输入：
  origins: ["POI1经纬度", "POI2经纬度", ...]
  destination: "主区域中心经纬度"
  type: 2   # 1=直线 2=驾车 3=步行
输出：results[]（每个 origin 对应一个 distance/duration）
```

**使用场景**：
- V1 区域一致性：批量算所有 POI 到主区域中心的距离
- V3 餐厅区域匹配：批量算所有餐厅到主区域中心的距离
- **比 `maps_direction_*` 快**（不用算路径）——但**没有 polyline**

---

## 场景 3：查酒店（Step 2 酒店候选）

### 三段式：搜 → 详情 → 通勤校验

#### Step 3.1 关键词搜酒店

```
工具：maps_text_search
输入：
  keywords: "酒店"
  city: "东京"
  location: "新宿站经纬度"  # 可选，配合半径
  radius: 1000
输出：pois[]
```

#### Step 3.2 候选筛选（参考 hotel-planning.md）
- 取 Top 10-20
- 按 cost / rating / type 过滤
- 留 3 个候选（商务 / 精品 / 民宿各 1）

#### Step 3.3 通勤圈校验（V1 衍生）
```
对每个候选酒店：
  对每天主区域中心，跑 maps_distance 计算通勤时间
  任一天 > 30 分钟 → 候选告警
```

**输出**：每个酒店附"每天通勤时间表"给用户看。

### 用 `maps_search_detail` 查酒店详情

取关键字段：
- `address` —— HTML 展示
- `type` —— 酒店 vs 民宿 vs 旅馆
- `cost` —— 决策参考
- 联系方式（订房前用户自己打电话确认）

---

## 场景 4：算天气（V6 户外敏感 + 富士山/海岛决策）

### 用 `maps_weather` 查城市天气

```
工具：maps_weather
输入：city: "东京"（或 adcode）
输出：forecasts[]
```

**返回字段示例**：
```json
[
  {
    "date": "2026-09-12",
    "weather": "晴",
    "temperature": "28",
    "wind": "东南风 3 级",
    "precipitation": "0"
  }
]
```

### V6 户外点决策流程

1. 拉取行程日期范围内的全部 `maps_weather`
2. 标出户外 POI 所在日期
3. 看天气：
   - 晴 / 多云 → 保留户外 POI
   - 小雨 → 提示用户，可保留也可换备选
   - 大雨 / 暴雨 / 台风 → 强制换 indoor_backup

### 远郊日决策
富士山 / 海岛 / 长距离徒步 等远郊日：
- 提前 3 天查天气
- 不行就改室内 / 改期

---

## 场景 5：导航唤端（HTML 链接生成）

### 拼 URL 唤端

**HTML 模板里的导航按钮**（参考 `assets/template.html`）：

```html
<a href="https://uri.amap.com/navigation?to={lng},{lat}&mode={mode}">高德地图导航</a>
<a href="https://maps.apple.com/?daddr={lat},{lng}&dirflg=w">Apple Maps</a>
<a href="https://www.google.com/maps/dir/?api=1&destination={lat},{lng}">Google Maps</a>
```

**`mode` 参数**（高德 URL scheme）：
- `car` = 驾车
- `walk` = 步行
- `ride` = 骑行
- `bus` = 公交
- 不传 → 用户在 App 内选

### 高德 MCP 唤端（可选）

如有 `navigate` / `taxi` / `generate_trip_map` 工具（部分 MCP 版本包含），AI 可调生成唤端链接，**不是必需**——直接拼 URL 完全够用。

---

## 工具选择速查表（v1.3.0 更新）

| 任务 | 首选工具 | 备选 |
|------|---------|------|
| 找景点 | `maps_text_search` | `maps_geo`（地名 → 经纬度 → text_search） |
| 景点详情 | `maps_search_detail` | `maps_text_search` 拿 id 后再 detail |
| 区域中心 | `maps_text_search keywords="<区域名>"` 取第一个 | `maps_geo` |
| **步行路线 + polyline** | `maps_direction_walking` | `maps_distance type=3`（无 polyline）|
| **驾车路线 + polyline** | `maps_direction_driving` | `maps_distance type=2`（无 polyline）|
| **骑行路线 + polyline** | `maps_bicycling` | `maps_distance type=3`（无 polyline）|
| **公交路线 + polyline** | `maps_direction_transit_integrated` | `maps_distance type=1`（无 polyline）|
| 批量距离 | `maps_distance`（一次算多个 origin） | 多次 `maps_direction_*`（慢，但有 polyline）|
| 天气 | `maps_weather` | 无备选 |
| 导航链接 | 拼 URL `https://uri.amap.com/navigation?to={lng},{lat}` | — |
| 打车链接 | 拼 URL `https://uri.amap.com/taxi?from=...&to=...` | — |

---

## 注意事项

1. **adcode 优先于 city 名**：部分工具用 `city` 字段时，传中文城市名（如"东京"）可能不识别，建议先 `maps_geo` 拿到 `adcode` 再用 adcode 查。
2. **POI type 字段**：高德 POI type 是中分类（如"风景名胜"），需要在 `maps_search_detail` 拿全字段或参考高德分类表判断是否户外。
3. **经纬度格式**：`"lng,lat"`（注意：先经度后纬度），不是 `"lat,lng"`。
4. **MCP 调用频率**：每个 tool 一次只返回 Top N 条，需要翻页就调多次。**路线规划 4 个工具一次只算一对起终点**，每天 4-5 对 POI = 4-5 次调用，**单次行程约 20-30 次调用**。
5. **rate limit**：高德免费版有日调用上限（一般是 5000-10000 次/天），注意控制总调用次数。**新加的 polyline 提取不增加额外调用**——和 V2 验证是同一次调用。
6. **跨城/远郊的 polyline 精度**：驾车路网覆盖好；步行/骑行在郊区/小路可能返回"沿公路步行"（无独立步行道），**这是高德数据限制，不是 skill bug**。
7. **公交 polyline 的拼接**：高德返回的公交方案是分段的（步行段 + 公交段 + 地铁段 + 换乘段），**每段都有 polyline**，AI 应**按段拼接成一条完整 path**，浏览器用不同颜色展示——但 v1.3.0 简化方案是**全部拼成一条 polyline 统一画**（按 mode 颜色），分段可视化留作 v1.4.0。

---

## 跨客户端一致性（v1.4.0 新增）

> **v1.4.0 重构后**：本节给 AI 一个保证——**所有"AI 调 MCP tool 拿数据"的部分在 7 个客户端里完全一致**。

| 客户端 | `mcp__amap__maps_direction_walking` | 跨城步行 polyline 格式 | 公交分段响应 |
|--------|----------------------------------|----------------------|------------|
| Claude Code CLI | ✅ | `paths[].steps[].polyline` | ✅ |
| Hermes desktop GUI | ✅ | 同上 | ✅ |
| Cursor | ✅ | 同上 | ✅ |
| Codex CLI | ✅ | 同上 | ✅ |
| Google Cloud Code | ✅ | 同上 | ✅ |
| Trae | ✅ | 同上 | ✅ |
| CodeBuddy | ✅ | 同上 | ✅ |

**为什么一致**：MCP 协议的设计目标之一就是"工具命名空间 + 输出 schema 跨客户端统一"。高德 MCP server 是个独立的 npm 包，**所有客户端加载的都是同一份代码**，输出的 JSON 字段名 + 结构完全一致。

**AI 的判断原则**：
- ✅ **不用管客户端**：调用 `mcp__amap__maps_direction_walking` 后，AI 解析 JSON 提取 polyline 的代码在 7 个客户端里**通用**——不需要 `if (client == "CC") { ... } else if (client == "Cursor") { ... }` 这种分支
- ✅ **跨客户端唯一可能不同的**：**MCP server 本身**（高德官方 npm 包 / @amap/amap-mcp-tools / 第三方 fork）的版本——v1.3.0 假设你装的是**官方 npm 包**，输出 schema 稳定
- ⚠️ **跨客户端可能不同的**：**MCP tool 数量**（如 `@playwright/mcp@0.5.0` 在 CC 暴露 14 个 tool，在 Hermes 暴露 13 个——具体以 `claude mcp list` / `hermes mcp list` 实际探到的为准）

**所以 v1.3.0 的真实路径渲染 / v1.2.0 的餐厅调研 / v1.1.0 的代码级验证**——这些**纯 MCP 调用的功能**跨客户端零差异。

**跨客户端会有差异的**（参考 SKILL.md §客户端适配层）：
- 装 MCP 的命令（`claude mcp add` / `hermes mcp add` / `codex mcp add` / 编辑 `~/.cursor/mcp.json` / 编辑 `~/.cloudshell_cloudsdk_mcp.json` / IDE 设置面板）
- 配置文件位置（`~/.claude.json` / `~/.hermes/config.yaml` / `~/.cursor/mcp.json` / `~/.codex/config.toml` / IDE 内部）
- 跑 shell 的方式（用户输入 `!` 前缀 / terminal 工具 / IDE 终端 / Codex 直接跑）
- 让 MCP 生效的方式（完全退出 / 下次启动自动 / Cmd+Shift+P Reload / 项目级自动加载 / 重开会话 / 重启 IDE）

---

## v1.3.0 改动摘要

| 改动 | 旧 | 新 |
|------|-----|-----|
| 工具名 | `geocode` / `poi_search` / `poi_detail` / `route_walking` / `route_transit` / `route_biking` / `route_driving` | `maps_geo` / `maps_text_search` / `maps_search_detail` / `maps_direction_walking` / `maps_direction_transit_integrated` / `maps_bicycling` / `maps_direction_driving` |
| 路线规划用途 | 只算通勤时间（V2 验证）| **同时拿 polyline 写进 `tripData.transports[].path`**（真实路网路径渲染）|
| HTML 地图 | 直线 polyline（POI1→POI2 直线）| 优先用 `path` 真实路径，否则降级为直线 |
| `tripData.transports[]` schema | `{from_idx, to_idx, mode, duration_min}` | **+ `path`（坐标数组）+ `distance_m` + `source`** |
| 文档完整性 | 工具表 + 5 场景 | **+ 场景 2.3 polyline 提取代码 + 2.4 schema 示例** |
