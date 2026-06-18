# 高德地图 MCP 使用指南（v1.3.0 修正工具名 + 真实路径）

> 本文件按"5 个使用场景"组织，每个场景给出高德 MCP 的工具名、调用模式、注意事项。
> 适配本 skill 的 7 步流程 + V1-V7 自动验证。
> 接入方式见 SKILL.md 的"数据源"小节（需要高德 Key）。

> **v1.3.0 重要修正**：
> 1. 工具名从旧版（`geocode` / `poi_search` / `poi_detail` / `route_walking` 等）**改为官方 MCP 实际命名**（`maps_geo` / `maps_text_search` / `maps_search_detail` / `maps_direction_walking` 等）——之前命名不规范，AI 调不到。
> 2. **新增「路线规划 → 真实路径」完整工作流**：Round 2 用高德拿通勤时间 + **路网 polyline** 写进 `tripData.transports[].path`，HTML 地图沿公路/步行道/公交线渲染。
>
> **v2.2.2 实战修正（2026-06）**：官方 MCP `maps_direction_*` **常只返回** `instruction` / `distance` / `duration`，**不含**画线坐标。polyline 须从 **REST API**（`/v3/direction/*`，同 Key）提取；MCP 仍负责 POI / 天气 / 通勤时间。详见 §2.3、**P28**。
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
| **`maps_direction_walking`** | **步行路径规划** | `origin`, `destination` | `paths[]`（distance/duration/**`steps[]` 导航摘要**）；**polyline 常需 REST 兜底**，见 §2.3 |
| **`maps_direction_driving`** | **驾车路径规划** | `origin`, `destination` | 同上 |
| **`maps_bicycling`** | **骑行路径规划** | `origin`, `destination` | 同上 |
| **`maps_direction_transit_integrated`** | **公交路径规划**（综合火车/公交/地铁） | `origin`, `destination`, `city`, `cityd`(跨城) | `transits[]`（distance/duration/**`segments[]` 分段摘要**）；**polyline 常需 REST 兜底** |
| `maps_weather` | 城市天气 | `city` 或 `adcode` | `forecasts[]` |

> **路线类 4 个工具 — MCP vs REST 字段名**：
> - **MCP 常见返回**（精简）：`steps[]` 只有 `instruction` / `road` / `distance` / `orientation` / `duration`，**没有坐标**
> - **REST API 完整返回**（画线用）：`route.paths[].steps[].polyline` = `lng,lat;lng,lat;...` 字符串（公交在 `route.transits[].segments[].walking|bus|railway.polyline`）
> - **tripData 写入字段**：统一写 `transports[].path` = `[[lng,lat], ...]` 数组（与 REST/MCP 响应字段名无关）

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

## 场景 2：规划路线（V2 验证 + 地图 polyline）

> **v2.2.2 混合工作流**（实战验证）：
> 1. **V2 通勤时间**：调 MCP `maps_direction_*` 拿 `distance` / `duration`（及公交 `cost`、驾车 `taxi_cost`）
> 2. **地图折线 polyline**：若 MCP `steps` **无** `polyline`/`path` 坐标 → **同一段立刻调 REST** `/v3/direction/*`（同一 `AMAP_MCP_KEY`）拼接坐标
> 3. **禁止**凭经验手工补中间点（V8 会判假路线 ❌）；**禁止**只连 POI 起终点当 path

### 2.1 模式选择（公共交通优先）

| 距离/场景 | MCP 工具（时间/费用） | REST endpoint（polyline 兜底） |
|----------|---------------------|-------------------------------|
| < 1.5km | `maps_direction_walking` | `/v3/direction/walking` |
| **1.5–4km** | **`maps_bicycling`** | `/v3/direction/bicycling` |
| **4–25km 市内** | **`maps_direction_transit_integrated`** | `/v3/direction/transit/integrated` + `city` |
| 机场/高铁（有快线/地铁） | **`maps_direction_transit_integrated`** | 同上；`transits` 为空再试 `driving` |
| 远郊无公交 / 深夜 / 用户要打车 | `maps_direction_driving` | `/v3/direction/driving` |
| 骑行（用户要） | `maps_bicycling` | `/v3/direction/bicycling` |

> **AI 默认流程**：< 1.5km 步行 → **1.5–4km 先 `bicycling`** → 4–25km `transit_integrated` → 无方案或用户要打车才 `driving`。

### 2.2 MCP 实际返回（常无 polyline）

```
工具：maps_direction_walking
输入：origin: "104.061,30.671"  destination: "104.062,30.6695"
输出（典型 — 只有导航摘要）：
{
  "paths": [{
    "distance": "327",
    "duration": "300",
    "steps": [{
      "instruction": "向北步行18米右转",
      "road": "",
      "distance": 18,
      "orientation": "北",
      "duration": 14
    }]
  }]
}
```

> ⚠️ **没有 `polyline` / `path` 字段时不能画地图折线**——这不是 MCP「坏了」，是当前官方 MCP 为省 token 裁掉了坐标。继续 §2.3 走 REST。

### 2.3 polyline 提取（REST 为主，MCP 有则用）

**每段 transport 的标准流程**：

```python
AMAP_KEY = os.environ["MCP_AMAP_API_KEY"]  # 或 ~/.travel-planner/config 的 AMAP_MCP_KEY

def parse_polyline_str(s: str) -> list[list[float]]:
    """REST steps[].polyline：'lng,lat;lng,lat;...' → [[lng,lat], ...]"""
    out = []
    for pair in (s or "").split(";"):
        pair = pair.strip()
        if not pair or "," not in pair:
            continue
        lng, lat = pair.split(",", 1)
        out.append([float(lng), float(lat)])
    return out

def steps_have_polyline(steps: list) -> bool:
    for step in steps or []:
        if step.get("polyline") or step.get("path"):
            return True
    return False

def extract_walking_polyline(route_json: dict) -> list[list[float]]:
    """步行/驾车/骑行：拼 route.paths[0].steps[].polyline"""
    points = []
    for step in route_json.get("route", {}).get("paths", [{}])[0].get("steps", []):
        raw = step.get("polyline") or step.get("path") or ""
        points.extend(parse_polyline_str(raw))
    return points

def extract_transit_polyline(route_json: dict) -> list[list[float]]:
    """公交：拼 transits[0].segments[].walking|bus|railway.polyline"""
    points = []
    segs = route_json.get("route", {}).get("transits", [{}])[0].get("segments", [])
    for seg in segs:
        for key in ("walking", "bus", "railway"):
            block = seg.get(key) or {}
            raw = block.get("polyline") or block.get("path") or ""
            points.extend(parse_polyline_str(raw))
    return points

# --- 单段 transport ---
mcp_result = call_mcp("maps_direction_walking", {"origin": o, "destination": d})
path_obj = (mcp_result.get("paths") or [{}])[0]
duration_min = int(int(path_obj.get("duration", 0)) / 60)
distance_m = int(path_obj.get("distance", 0))
source = "amap-mcp"

if steps_have_polyline(path_obj.get("steps")):
    all_points = extract_walking_polyline({"route": {"paths": [path_obj]}})
else:
    # REST 兜底（与 MCP 同 Key）
    import urllib.request
    url = (
        f"https://restapi.amap.com/v3/direction/walking"
        f"?key={AMAP_KEY}&origin={o}&destination={d}"
    )
    rest = json.loads(urllib.request.urlopen(url, timeout=15).read())
    all_points = extract_walking_polyline(rest)
    source = "amap-rest-api"
    # duration/distance 以 REST route.paths[0] 为准亦可

tripData["days"][day_idx]["transports"][i].update({
    "path": all_points,
    "duration_min": duration_min,
    "distance_m": distance_m,
    "source": source,
})
```

**Bash 一行（步行 REST 兜底）**：

```bash
AMAP_KEY="${MCP_AMAP_API_KEY:-$(grep ^AMAP_MCP_KEY= ~/.travel-planner/config | cut -d= -f2-)}"
curl -sS --max-time 15 \
  "https://restapi.amap.com/v3/direction/walking?key=${AMAP_KEY}&origin=104.061,30.671&destination=104.062,30.6695"
# → route.paths[0].steps[].polyline
```

> **V8 校验**（`scripts/validate.py`）：`path` 须为完整 polyline（通常几十～几百点），非短步行至少 **3 点**；`source` 须为 `amap-mcp` 或 `amap-rest-api`。详见 `references/validation-rules.md` §V8。

**公交 REST 示例**：

```bash
curl -sS "https://restapi.amap.com/v3/direction/transit/integrated?key=${AMAP_KEY}&origin=104.061,30.6635&destination=104.082,30.6605&city=成都"
# → route.transits[0].segments[].walking.polyline / .bus.polyline / .railway.polyline
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
  "source": "amap-mcp"        // "amap-mcp" | "amap-rest-api"（REST 兜底画线时）
}
```

### 2.5 费用字段提取（v2.1.0 新增 → `transports[].fare`）

与 §2.2 同一次 `maps_direction_*` 调用，**同步写 `fare`**：

| mode | MCP 返回字段 | `fare` 写法 |
|------|-------------|------------|
| `walking` / `biking` | — | `unit: "free"`, `source: "computed"` |
| `transit` / `subway` / `bus` | `transits[0].cost` 或各 `segment.bus.cost` 之和 | `min=max=实值`, `source: "amap-mcp"` |
| `driving` | `paths[0].taxi_cost`（元，字符串） | 写入 `fare.min/max` |
| 无费用字段 | WebFetch 当地公交票价页 | `source: "official-site"` + `source_url` |

```json
"fare": {
  "min": 2,
  "max": 2,
  "currency": "CNY",
  "unit": "per_person",
  "quantity": 3,
  "total_min": 6,
  "total_max": 6,
  "label": "地铁",
  "source": "amap-mcp",
  "source_ref": "maps_direction_transit_integrated cost"
}
```

步行示例：`quantity` 可省略，`total_min=max=0`。

---

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
5. **rate limit**：高德免费版有日调用上限（一般 5000–10000 次/天）。Round 2 每段 transport 通常 **1 次 MCP + 1 次 REST**（MCP 无 polyline 时），注意总调用量。
6. **跨城/远郊的 polyline 精度**：驾车路网覆盖好；步行/骑行在郊区/小路可能返回"沿公路步行"（无独立步行道），**这是高德数据限制，不是 skill bug**。
7. **公交 polyline 的拼接**：高德返回的公交方案是分段的（步行段 + 公交段 + 地铁段 + 换乘段），**每段都有 polyline**，AI 应**按段拼接成一条完整 path**，浏览器用不同颜色展示——但 v1.3.0 简化方案是**全部拼成一条 polyline 统一画**（按 mode 颜色），分段可视化留作 v1.4.0。

---

## 跨客户端一致性（v1.4.0 新增）

> **v1.4.0 重构后**：本节给 AI 一个保证——**所有"AI 调 MCP tool 拿数据"的部分在 7 个客户端里完全一致**。

| 客户端 | `mcp__amap__maps_direction_walking` | MCP steps 含 polyline？ | polyline 来源 |
|--------|----------------------------------|------------------------|--------------|
| 全部 7 客户端 | ✅ 工具名一致 | ⚠️ **常无**（仅 instruction/distance/duration） | **REST** `/v3/direction/*` 的 `steps[].polyline` |

**为什么一致**：MCP 协议的设计目标之一就是"工具命名空间 + 输出 schema 跨客户端统一"。高德 MCP server 是个独立的 npm 包，**所有客户端加载的都是同一份代码**，输出的 JSON 字段名 + 结构完全一致。

**AI 的判断原则**：
- ✅ **POI / 天气 / 地理编码**：继续用 MCP tool
- ✅ **路线时间/费用**：MCP `maps_direction_*` 优先
- ✅ **路线 polyline（画地图）**：MCP `steps` 无 `polyline` 时 **必须 REST 兜底**（§2.3），`source` 写 `amap-rest-api`
- ❌ **不要**手工编中间路网点；❌ **不要**因 MCP 无坐标就放弃 REST 改用 POI 直线

**所以 v1.3.0 的真实路径渲染 / v1.2.0 的餐厅调研 / v1.1.0 的代码级验证**——这些**纯 MCP 调用的功能**跨客户端零差异。

**跨客户端会有差异的**（参考 SKILL.md §客户端适配层）：
- 装 MCP 的命令（`claude mcp add` / `hermes mcp add` / `codex mcp add` / 编辑 `~/.cursor/mcp.json` / 编辑 `~/.cloudshell_cloudsdk_mcp.json` / IDE 设置面板）
- 配置文件位置（`~/.claude.json` / `~/.hermes/config.yaml` / `~/.cursor/mcp.json` / `~/.codex/config.toml` / IDE 内部）
- 跑 shell 的方式（用户输入 `!` 前缀 / terminal 工具 / IDE 终端 / Codex 直接跑）
- 让 MCP 生效的方式（完全退出 / 下次启动自动 / Cmd+Shift+P Reload / 项目级自动加载 / 重开会话 / 重启 IDE）

---

---

## v2.0.0 实战踩坑（2026-06-18 厦门任务新增）

> **本节是真实使用中遇到 + 验证过的硬坑**。AI 每次跑 travel-planner 必读，否则会走错路径。

### P23：amap MCP 探活必须三步，不能信单层信号

**背景**：`hermes mcp list` 显示 `✓ enabled` 完全是装饰，**不代表工具能调通**。

**三层探针**（按顺序跑，**任一失败都走降级**）：

```bash
# 第一层：hermes mcp test（被动探活，可信度 30%）
hermes mcp test amap
#  ❌ "Server error '500 Internal Server Error'" → 服务端挂
#  ❌ "Connection failed"  → 网络/配置问题
#  ✅ "Connection successful" → 才继续往下
#  ⚠️ 报成功也不一定稳——继续第二层

# 第二层：直接 POST tools/list 到 MCP server（手动验协议）
#  SSE 协议要带 Accept 和 Mcp-Session-Id
curl -sS --max-time 8 -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $(uuidgen)" \
  "https://mcp.amap.com/mcp?key=YOUR_KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
#  ✅ 返回 result.tools[] → MCP server 端 OK
#  ❌ 返回 error / 超时 → 降级 REST API

# 第三层：实际工具调用（验证 tools 真的能在本会话调用）
#  这一步只能在 agent 里跑：直接调 mcp__amap__maps_geo address="北京天安门" city="北京"
#  ✅ 返回 location: "116.397,39.908" → 全链路通
#  ❌ 工具名不在当前工具列表 / 调了报错 → 系统没注入 MCP，降级 REST
```

**反例（2026-06-18 真实发生）**：
- `hermes mcp list` 显示 `✓ enabled`
- `hermes mcp test amap` 报 500
- SSE 协议 POST `initialize` + `tools/list` 都 OK
- **但当前 agent 工具列表里没有 `mcp__amap__*`**（系统没注入）
- → 降级 REST API

**结论**：**第一层和第二层都通过 ≠ 工具可用**。**必须第三层真发 mcp__amap__* 工具调用**。看不到这个工具 → 降级 REST。

### P24：降级路径 = 高德 REST API（MCP_AMAP_API_KEY 通用）

**关键发现**：**MCP 端用的 Key 和 REST API 端用的是同一个**（都来自 `MCP_AMAP_API_KEY` 环境变量或 `~/.travel-planner/config` 里的 `AMAP_MCP_KEY`）。

**REST 端验证 Key 有效性**（1 条命令搞定）：

```bash
curl -sS --max-time 8 \
  "https://restapi.amap.com/v3/place/text?key=YOUR_KEY&keywords=酒店&city=厦门&offset=1"
#  ✅ "status":"1","info":"OK"  +  pois[]  → Key 有效
#  ❌ "status":"0","info":"INVALID_USER_KEY" → Key 失效/没启用
#  ❌ "status":"0","info":"CUQPS_HAS_EXCEEDED_THE_LIMIT" → 配额用完
```

**REST 端常用 endpoint**（MCP 端 tool 对应关系）：

| MCP tool | REST endpoint | 备注 |
|---------|--------------|------|
| `maps_text_search` | `/v3/place/text?keywords=&city=&types=` | 关键词搜 POI |
| `maps_around_search` | `/v3/place/around?keywords=&location=&radius=` | 周边搜 |
| `maps_geo` | `/v3/geocode/geo?address=&city=` | 地址→坐标 |
| `maps_regeocode` | `/v3/geocode/regeo?location=` | 坐标→地址 |
| `maps_search_detail` | `/v3/place/detail?id=` | POI 详情 |
| `maps_direction_walking` | `/v3/direction/walking?origin=&destination=` | 步行路径 |
| `maps_direction_driving` | `/v3/direction/driving?origin=&destination=` | 驾车路径 |
| `maps_direction_transit_integrated` | `/v3/direction/transit/integrated?origin=&destination=&city=` | 公交综合 |
| `maps_bicycling` | `/v3/direction/bicycling?origin=&destination=` | 骑行路径 |
| `maps_distance` | `/v3/distance?origins=&destination=&type=` | 距离测量（type=1 直线 / 2 驾车 / 3 步行）|
| `maps_weather` | `/v3/weather/weatherInfo?city=adcode&extensions=base` | **⚠️ 免费 Key 常 INVALID_PARAMS**（P20）|

**完整 Bash helper 模板**（`/tmp/amap_helpers.sh`，P22 已落）：

```bash
AMAP_KEY="${MCP_AMAP_API_KEY:-$(grep ^AMAP_MCP_KEY= ~/.travel-planner/config | cut -d= -f2-)}"
BASE="https://restapi.amap.com/v3"

amap_text_search() {
  local kw="$1" city="$2" types="${3:-}"
  local url="${BASE}/place/text?key=${AMAP_KEY}&keywords=$(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' "$kw")&city=$(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' "$city")&extensions=all&offset=10"
  [[ -n "$types" ]] && url="${url}&types=$(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' "$types")"
  curl -sS --max-time 15 "$url"
}

# 步行路线 + polyline（Round 2 画地图用，§2.3 / P28）
amap_direction_walking() {
  local origin="$1" destination="$2"
  curl -sS --max-time 15 \
    "${BASE}/direction/walking?key=${AMAP_KEY}&origin=${origin}&destination=${destination}"
}
```

**降级标识**：`transports[].source` 写 `"amap-rest-api"`（REST 画线）或 `"amap-mcp"`（MCP 响应里自带 polyline 时）。**二者 V8 均认可**。

### P28：路线 polyline 必须 REST 兜底（MCP steps 常无坐标）

**背景**（2026-06 多城实战）：`maps_direction_walking` / `maps_direction_transit_integrated` 等 MCP 工具**能调通**，返回 `distance` / `duration` / `instruction`，但 `steps[]` **经常没有** `polyline` 或 `path`。若 AI 只连两个 POI 当折线，地图画飞线 + V8 ❌ 阻断。

**标准动作**（每段 `transports[]`）：

1. MCP `maps_direction_*` → 拿 `duration_min` / `distance_m` / `fare`
2. 检查 `steps` 是否含 `polyline`（或 `path`）
3. **若无** → 同参数调 REST（§2.3 表），从 `route.paths[].steps[].polyline` 拼接 → `transports[].path`，`source: "amap-rest-api"`
4. **禁止**方案：手工补 2–3 个「路过中山路」式中间点（V8 假直线/端点检测会拦）

**与 P24 关系**：P24 是「MCP 整站不可用」时的全局降级；P28 是「MCP 能调但缺 polyline」时的**路线专项**降级——**更常见**，Round 2 **默认预期会触发**。

### P25：天气数据双源（避免 P20 重演）

| 源 | 适用 | 失败信号 |
|---|------|---------|
| `maps_weather`（MCP）| 城市/区域预报 | `INVALID_PARAMS` 免费 Key 经常返这个 |
| `/v3/weather/weatherInfo`（REST）| 同上 | 同上，免费 Key 不稳 |
| `wttr.in/<city>?format=%C+%t&lang=zh` | 实时 + 短临（1-3 天）| 极少失败 |
| 客户端自带的 web search tool（如 `WebSearch` / `WebFetch` / 客户端特定 MCP）| 任意时段 | 查"<城市> YYYY-MM-DD 天气预报"可拿到气象局数据 |

**降级链**：MCP weather → REST weather → wttr.in → web search（**用当前客户端实际有的 web search 工具，不要硬编码某个 MCP 名**——不同客户端的 web 搜索工具名不同：CC / Hermes / Cursor / Codex / Cloud Code / Trae / CodeBuddy 各有各的命名，AI 按自己工具列表里实际看到的写）。

**AI 怎么查"我自己有哪些 web search 工具"**：
- 扫工具列表，找 `WebSearch` / `web_search` / `mcp__*__web_search` / `internet_search` 之类关键字
- 找到一个能调通就行，**不写死**

### P26：amap MCP 在 SSE 模式下的双 endpoint 行为

**MCP server 行为（amap-sse-server v1.0.0）**：
- **GET 端点**（`Accept: text/event-stream`）：开 SSE 长连接，持续推送
- **POST 端点**（`Content-Type: application/json`）：单次请求-响应
- **Mcp-Session-Id**：GET 开连接时分配，POST 复用同一个 ID 才能关联会话

**踩坑**（2026-06-18 真实发生）：
- 用 `hermes mcp test amap` 报 500（应该是 POST 路径走错了或服务端某个 endpoint 挂）
- 但用 curl 手动 POST `initialize` + `tools/list` 都正常返回
- 说明**amap MCP server 端没全挂**，是某个 endpoint 临时挂

**AI 的判断原则**：
- 不要因为 `hermes mcp test` 一次失败就判定 amap MCP 全挂
- 手动 POST `tools/list` 验证一下再说
- 但**第三层（实际工具调用）才最权威**

### P27：travel-planner 实战起手式（Step 0 改版）

**v2.0.0 起**，travel-planner Step 0 环境自检的标准流程：

```bash
# 1. 客户端识别
which hermes && hermes --version | head -1   # 确认客户端

# 2. MCP 注册表（被动，仅参考）
hermes mcp list

# 3. amap MCP 三层探针（P23）
hermes mcp test amap                                      # 第一层
curl -sS -X POST -H "Content-Type: application/json" \   # 第二层
  -H "Accept: application/json, text/event-stream" \
  "https://mcp.amap.com/mcp?key=${MCP_AMAP_API_KEY}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# 4. 实际工具调用（第三层，由 agent 跑 mcp__amap__maps_geo 验证）

# 5. 降级路径准备
echo "AMAP_KEY=$MCP_AMAP_API_KEY"           # 供 REST 端用
echo "WEB_KEY=$AMAP_WEB_KEY"                # 供 HTML 地图 JS 用
curl -sS --max-time 6 "https://wttr.in/Xiamen?format=%C+%t&lang=zh"  # 天气备选
```

**输出报告格式**（AI 写给用户看的，不要照抄）：

```
🔍 环境自检
├─ ✅/❌ amap MCP：<第三层实测结果>（<失败时降级到 REST/搜索/浏览器>）
├─ ✅/❌ Playwright MCP：<状态>
├─ ✅/❌ 小红书：<cli.py check-login 状态>（未装则标"未装，本方案用 WebFetch 兜底"）
└─ ⏭️ 大众点评：未配置（非必需，主轨用高德 POI + 美团攻略 WebFetch）
```

---

## v2.0.0 改动摘要（2026-06-18 实战补丁）

| 改动 | v1.3.0（旧）| v2.0.0（新）|
|------|----------|------------|
| MCP 探活 | 信 `✓ enabled` | **三层探针**（mcp test → tools/list POST → 真工具调用）|
| MCP 失败时 | "降级为通用知识" | **明确走 REST API**（`/v3/place/text` 等），helpers 在 `/tmp/amap_helpers.sh`|
| 天气源 | 只 MCP | **四源降级链**（MCP → REST → wttr.in → web search）|
| 端点行为 | 默认 HTTP | **SSE 协议细节**（GET 长连 + POST 单次 + Mcp-Session-Id）|
| 降级标识 | 模糊 | `transports[].source = "amap-rest-api"` 显式标记 |
| Step 0 模板 | 单层 `mcp list` | **三层探针 + 降级准备** |

---

## v2.2.2 改动摘要（2026-06 路线 polyline）

| 改动 | v1.3.0–v2.0.0（旧）| v2.2.2（新）|
|------|-------------------|------------|
| 路线 polyline 来源 | 假设 MCP `steps[].path` 同次返回 | **MCP 拿时间 + REST `/v3/direction/*` 拿 `steps[].polyline`**（P28）|
| `source` 含义 |  mostly `amap-mcp` | `amap-mcp`（MCP 自带坐标时）或 **`amap-rest-api`（画线 REST 兜底，V8 认可）** |
| 禁止动作 | 未明确 | **禁止**手工补路网点；MCP 无坐标时**必须** REST，不得 POI 直线糊弄 |

---

## v1.3.0 改动摘要

| 改动 | 旧 | 新 |
|------|-----|-----|
| 工具名 | `geocode` / `poi_search` / `poi_detail` / `route_walking` / `route_transit` / `route_biking` / `route_driving` | `maps_geo` / `maps_text_search` / `maps_search_detail` / `maps_direction_walking` / `maps_direction_transit_integrated` / `maps_bicycling` / `maps_direction_driving` |
| 路线规划用途 | 只算通勤时间（V2 验证）| **同时拿 polyline 写进 `tripData.transports[].path`**（真实路网路径渲染）|
| HTML 地图 | 直线 polyline（POI1→POI2 直线）| 优先用 `path` 真实路径，否则降级为直线 |
| `tripData.transports[]` schema | `{from_idx, to_idx, mode, duration_min}` | **+ `path`（坐标数组）+ `distance_m` + `source`** |
| 文档完整性 | 工具表 + 5 场景 | **+ 场景 2.3 polyline 提取代码 + 2.4 schema 示例** |
