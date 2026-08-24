---
name: travel-planner
description: 面向中国大陆行程的旅行规划、行前复核与临场调整 Skill。使用地图、官方渠道、OTA、目的地攻略和餐饮指南等实时信息，生成并校验包含路线、餐饮、预算、预订状态、Plan B 和安全提醒的对话版攻略与响应式单文件 HTML。Use when the user asks to plan, optimize, review, update, recheck, or publish a domestic trip itinerary, including requests based on flight, train, hotel, attraction, restaurant, weather, safety, or route details.
---

# Travel Planner

把旅行需求变成可执行、可校验、可继续修改的中国大陆行程。每次必须同时交付可独立使用的对话版攻略与本地单文件 HTML；两者同等重要，并由同一份已校验 JSON 生成。只有用户明确希望分享，并确认隐私影响后，才额外发布公开链接。

## 工作原则

1. **实时信息不靠记忆。** 营业时间、闭园、票价、班次、天气、酒店和餐厅状态必须查询；查不到就标注未知或估算，不得伪造来源。
2. **硬事实优先官方。** 开放时间、预约、临时关闭、票务和交通规则以景区、场馆、铁路、航司、政府或运营方为准。
3. **路线必须可行。** POI 要有坐标，主要移动段要有查询所得的方式与时长；字符串 `source` 只是记录，不是外部查询已经发生的证明。
4. **区分事实、体验和估算。** 攻略用于发现候选与软信号，不能覆盖官方硬事实；价格区间必须带来源和查询时间。
5. **最少打扰用户。** 先利用已有信息和工具，只询问会实质改变方案的缺项。
6. **保护隐私。** 不把 API Key 写进 JSON、HTML、URL 或仓库；公开发布前明确提示页面可能暴露城市、日期、酒店和路线。
7. **不擅自改环境。** 不自动安装 MCP、浏览器扩展或 CLI；缺能力时说明影响，并提供可继续的降级方案。
8. **双输出保持一致。** 对话版攻略与 HTML 必须包含相同的核心行程事实；缺少任一输出、仅返回摘要或链接、两者版本不一致，都不算完成。

## 信息源

按任务组合以下五类来源。详细优先级、证据字段与降级策略见 [references/data-sources.md](references/data-sources.md)。

| 来源 | 主要用途 | 角色 |
| --- | --- | --- |
| 高德地图 | POI、坐标、地理编码、距离、路线、通勤时长 | 路线与地理硬数据 |
| 官方与运营方渠道 | 开放时间、预约、票务、临时通知、天气和公共交通规则 | 最高优先级硬事实 |
| 携程等国内 OTA | 酒店、机票、火车与可预订价格区间、国内深链 | 价格和预订 |
| 小红书 | 分区、游玩节奏、排队、拍照、踩雷等近期体验 | 可选软信号 |
| 美团攻略 | 餐厅候选、菜系与场景化推荐 | 可选候选池 |

大众点评不属于默认主链路。仅在用户明确要求且当前环境已有合规能力时作为补充，不要求安装或绕过反爬。

网页搜索、浏览器、WebFetch 和 MCP 是检索方式，不是信息源。用搜索发现页面后，尽量打开原始官方页并记录它；不要把搜索摘要标成官方来源。

## 能力发现

开始前检查当前环境实际可用的搜索、地图、浏览、文件和 GitHub 能力。按能力而非客户端名称工作：

- 有地图工具：查询 POI、坐标和路线。
- 无地图工具但有合法 API 配置：可用官方 REST 接口。
- 两者都没有：仍可给出草案，但把路线时长标为待核验，不得标成高德实算。
- 有网页搜索或浏览能力：查询官方页、OTA 和攻略。
- 某个可选来源不可用：跳过并在结果里说明，不阻塞整个规划。

不要假设具体工具前缀、数量或安装路径。只有用户主动要求配置环境时，才读取 [references/setup-guide.md](references/setup-guide.md)。

## 标准流程

### 1. 归一化需求

收集并确认：

- 目的地、日期、人数和出发地；
- 已订交通与酒店；
- 必去/不去、预算、节奏、饮食禁忌、步行能力；
- 老人、儿童、无障碍、行李和返程缓冲等约束。

信息不足时先做合理假设，并清楚列出。日期或目的地不明确且会改变检索结果时再询问。

### 2. 研究硬事实

先查官方渠道，再查地图和 OTA：

- 景区/场馆开放、预约、票价、临时通知；
- 酒店与交通枢纽坐标；
- 主要路线方式、时长和末班风险；
- 酒店、机票、火车及门票价格区间；
- 旅行日期对应的天气或季节风险。

为易变事实保存 `source`、`source_ref`、`checked_at`，并在顶层 `rechecks` 安排 `recheck_at`。无法核验时写 `unknown`，不要伪装成已验证，也不要让估算价格通过严格校验。

### 3. 建候选池并排日程

用攻略发现区域和候选，用地图确认位置，用官方页确认可用性。安排时：

- 每天围绕一个主区域或清楚的转场逻辑；
- 先放时间固定、必须预约的项目；
- 控制每日 POI 数量和步行强度；
- 午晚餐靠近当日区域或明确成为路线一站；
- 最后一日从返程时间倒排，保留安检、取行李和拥堵缓冲。
- 为天气敏感或可能临时关闭的日程写结构化 `plan_b`：触发条件、替代安排和路线影响；
- 按同行人、天气、海拔、夜间交通、行李和返程风险生成具体 `safety_notes`，避免通用套话。

酒店选择与换住判断见 [references/hotel-planning.md](references/hotel-planning.md)，整体编排细节见 [references/planning.md](references/planning.md)。

### 4. 写结构化数据

以 [references/trip-schema.json](references/trip-schema.json) 为核心结构。至少包含：

- `trip_name`、`city`、`date_range`、`party_size`；
- 酒店名称与坐标；
- 每日 `day`、`date`、`region`、`center`、`pois`；
- POI 的序号、时间、停留时长与坐标；
- `transports` 的端点、方式、时长与来源；
- 主餐厅坐标和价格；
- 带 `priority`、`status`、`deadline`、`id_required` 的 `prebook`；
- 结构化 `plan_b`、`safety_notes`、`rechecks`、预算和关键提醒。

不要用 `scripts/seed_prices.py` 生成的演示估算冒充实时调研结果。该脚本只用于旧数据迁移和模板演示。

### 5. 校验并修正

运行：

```bash
python scripts/validate.py trip.json --pretty --fail-on-warn
```

失败或警告时先修数据，再继续。规则含义见 [references/validation-rules.md](references/validation-rules.md)。此外人工检查用户禁忌、近期临时通知和来源是否真实访问过。

如需补酒店早晚通勤，必须显式选择输出方式：

```bash
python scripts/add_hotel_legs.py trip.json --output trip-with-hotel-legs.json
# 或明确接受覆盖
python scripts/add_hotel_legs.py trip.json --in-place
```

V12 会阻止缺失或过期的关键复核项。测试历史/未来日期时可显式传 `--as-of YYYY-MM-DD`，但真实交付默认使用今天。

### 6. 渲染双输出

```bash
python scripts/render_markdown.py trip.json -o trip.md
python scripts/render_html.py assets/template.html trip.json -o trip.html
```

对话版必须直接使用 `trip.md` 的内容，不要另写一份可能漂移的攻略。打开 HTML 检查标题、日期、地图、预订状态、Plan B、安全提醒、行前复核、预算和移动端布局。高德 Web Key 只允许用户在页面内输入并保存到当前设备；不得通过 `?k=` 参数传递。

### 7. 生成对话版攻略

把 `trip.md` 的完整内容放进对话，确保无需打开附件也能使用，至少包含：

- 行程概览、关键假设和待核验项；
- 每日时段、POI 顺序、区域和主要交通；
- 餐饮安排、预算区间、预约事项和 Plan B；
- 与老人、儿童、天气、末班车或返程有关的安全提醒。

不要只回复“已生成 HTML”、文件链接或改动摘要来代替对话版攻略。

### 8. 双交付或额外发布

在同一次最终回复中同时提供对话版攻略与 HTML 文件。JSON 是两种输出的唯一数据源和后续修改底稿，可一并提供，但不能替代任一用户可见输出。

用户明确要求公开链接时，把链接作为 HTML 文件之外的额外交付：

1. 提示城市、日期、酒店和路线可能公开；
2. 确认发布仓库、可见性和目标路径；
3. 发布后实际打开链接验证；
4. 只返回经过验证的链接。

公开发布失败时仍交付对话版攻略与 HTML 文件，不让托管能力阻塞规划结果。

部署细节见 [references/deployment.md](references/deployment.md)。

## 行前复核与临场调整

根据首日日期自动选择核对强度：

- 距出发超过 7 天：保留当前证据，并安排每类易变事实的 `recheck_at`；
- 距出发 7 天内：重新查询开放/预约、主要路线、末班、可售状态和未付款价格；
- 距出发 1 天内：再查逐小时天气、预警、临时闭馆和机场/车站路线；
- 用户说“今天”“明天”或现场发生变化：只重算受影响日期，立即给出触发条件明确的替代方案。

细则见 [references/recheck-and-safety.md](references/recheck-and-safety.md)。这不是后台定时任务；每次 Skill 被调用时根据当前日期执行。

## 增量修改

用户后续改酒店、日期、航班或 POI 时，不要重做无关部分：

1. 读取现有 JSON；
2. 找出受影响的日期、路线、价格和预订项；
3. 只重新查询会失效的事实；
4. 重跑全量校验；
5. 重新生成 Markdown 与 HTML；
6. 直接使用最新 Markdown 作为完整对话版攻略；
7. 在同一回复中重新交付两种最新输出；
8. 已发布且用户要求同步时，再更新同一页面。

如果来源出现冲突，保留官方结论，并在说明里记录冲突与取舍。

## 资源索引

- [data-sources.md](references/data-sources.md)：五类信息源、优先级和证据规范
- [planning.md](references/planning.md)：行程编排方法
- [hotel-planning.md](references/hotel-planning.md)：酒店与换住策略
- [validation-rules.md](references/validation-rules.md)：V0–V13 校验规则（含 V12 时效性）
- [recheck-and-safety.md](references/recheck-and-safety.md)：行前复核、临场调整与安全提醒
- [deployment.md](references/deployment.md)：本地交付与可选发布
- [setup-guide.md](references/setup-guide.md)：用户明确要求时的能力配置
- [amap-mcp-usage.md](references/amap-mcp-usage.md)：高德查询与路线字段
- [xhs-research.md](references/xhs-research.md)：小红书软信号
- [meituan-guide-research.md](references/meituan-guide-research.md)：美团餐厅候选
