# 行程规划方法论

> 移植自参考项目 trip-map-builder（MIT 协议），适配本 skill 的 7 步 + 3 轮迭代流程。
> 配套：`../SKILL.md` 是主流程入口；`./multi-turn-protocol.md` 是交互格式；`./validation-rules.md` 是自动验证规则。

---

## 1. 用户输入采集

### 最低必填
- 出发 / 回程日期、到达 / 离开时间
- 机场和航站楼
- 酒店名 + 地址
- 想去点、避开的类型

### 优先补全
- 人数、年龄段、长辈小孩
- 餐饮预算、能否排队、步行耐力
- 偏好标签（咖啡 / 酒吧 / 夜景 / 温泉 / 动漫 / 二次元 等）
- 行李量、交通偏好、是否早起
- 酒店预算 / 类型 / 区域偏好（仅当酒店"待选"时）

### 模板字段
```
时间、到达、回程、酒店、酒店地址、人数、年龄段、
一定要去、可以去、不要去、喜欢、不喜欢、
餐饮预算、能否排队、能走多少、补充
```

---

## 2. 判断优先级（先后顺序）

1. **天数够不够** —— 决定能不能塞远郊、能不能跨城
2. **酒店位置** —— 决定每天通勤圈的形状
3. **用户忌讳** —— 删清单第一刀
4. **天气敏感点** —— 决定是否需要室内备选
5. **预约项** —— 决定哪一天排"重日"
6. **节假日爆点** —— 决定远郊能不能去
7. **最后补餐厅 / 咖啡** —— 不为名店扭曲路线

---

## 3. 选点原则

- **一天一个主区域**
- **一天只放一个重预约点**
- **第一天轻量收尾**（落地疲劳 + 时差 + 行李）
- **末日不跑远**（返程缓冲优先）
- **长距离仅排非节假日**（节假日远郊 2 倍时间起步）
- **户外点标天气敏感 + 配室内备选**
- **用户明确讨厌的类型直接屏蔽**

---

## 4. 选餐原则

- **先保区域顺路** —— 不为名店扭曲路线
- **2-3 个候选** —— 主推 + 备选
- **大众点评看口味 / 排队 / 踩雷 / 值不值**（硬信号）
- **小红书看氛围 / 近期体验 / 拍照**（软信号）
- **名气放最后** —— 名气 ≠ 适合这顿饭

---

## 5. 执行七步（与 SKILL.md 主流程对齐）

### Step 1：抽硬约束
到达时间、回程时间、航站楼决定首末日节奏与按区走线。

### Step 2：清单分组
- 城内轻松组
- 预约组
- 远郊组
- 可路过组

### Step 3：删高风险点（【开始 3 轮迭代】）

**不照单全收。主动删：**
- 天数不够的远郊
- 节假日核心段爆款远郊
- 天气敏感点（放不进则删，放得进则配室内备选）

**明说删了什么 + 为什么删** —— 这是参考项目最强调的硬规则之一。

### Step 4：按区域重组
一天一区 → 换乘少、插饭顺、累得慢、临改灵活。

### Step 5：补吃饭
按当日主区域给候选，不为名店扭曲路线。

每顿写清：
- 吃饭区域
- 主推候选
- 近距离备选
- 大众点评判断
- 小红书补充判断

**餐厅是补给点不是锚点。** 仅预约餐、强目的餐、用户指定店可反推路线。

### Step 6：补票务和交通
只查关键项：
- 官方票务
- 营业时间
- 休馆日
- 机场 ↔ 酒店

### Step 7：写参考文档（结构化 markdown 输出）
见 SKILL.md Step 6 的输出结构。

**【3 轮分阶段筛检】**（v1.5.0，详见 `iteration-rounds.md`）：

```
Round 1 结构筛 → validate.py --round 1（V1,V4 + AI V7）
  ↓ 不通过：只修结构
Round 2 时空筛 → validate.py --round 2（V2,V5,V8,V9 + 高德实算）
  ↓ 不通过：只修时空
Round 3 体验筛 → validate.py --round 3（V3,V6 + 餐厅三源）
  ↓ 不通过 → 列问题请用户介入
  ↓ 通过 → Step 6-7
```

Step 4「补吃饭」已并入 Round 3；Round 3 完成后 Step 4 仅确认即可。

---

## 6. 输出模板结构（详见 SKILL.md Step 6）

- 先说结论
- 每天怎么走（Day 1 / Day 2 / Day 3）
- 每天吃什么（午餐 / 晚餐：区域 + 主推 + 备选）
- 天气敏感点
- 提前订什么
- 删掉什么
- 为什么这样排

---

## 7. 信息源优先级

1. **官方景点 / 票务 / 机场 / 交通页** —— 营业时间、票价、开放日
2. **餐厅：大众点评 + 小红书** —— 硬信号 + 软信号
3. **社媒种草、游记** —— 仅补感觉，不可作营业时间

---

## 7.1 链接真实性硬约束

> **禁止凭 LLM 记忆手写 URL。** 用户会直接在手机上点击；404 或错误起终点 = 方案不可用。

### 导航链接（`links.amap_navi` / `transports[].links.amap_navi`）

- **必须**来自高德 MCP `maps_direction_*` 返回的 `route` / `route_uri` 字段
- 若 MCP 未返回 URI，用 POI 真实坐标拼标准格式（模板也会 fallback，但 AI 仍应优先给 MCP 真链）：
  ```
  https://uri.amap.com/navigation?from={lng},{lat},{name}&to={lng},{lat},{name}&mode={walk|bus|car|ride}&callnative=1
  ```
- `mode` 映射：walking→walk，transit/subway/bus→bus，driving→car，biking→ride

### 提前订链接（`prebook[].url`）

> **国内优先**：用户在中国用手机点开，**必须给国内常用平台深链**（携程 / 飞猪 / 美团 / 大麦 / 官方渠道）。**禁止** Booking.com、Trip.com 国际版、Agoda、Bing 搜索作为首选。

| 类型 | 必须用的平台 | URL 模板（带搜索词 / 日期 / 城市） |
|------|------------|----------------------------------|
| 机票（单程） | 携程机票 | `https://flights.ctrip.com/itinerary/oneway/{from}-{to}?date={YYYY-MM-DD}`<br>例：上海→厦门 `sha-xmn?date=2026-06-25` |
| 机票（往返） | 携程机票 | `https://flights.ctrip.com/itinerary/round/{from}-{to}?date={去程},{返程}` |
| 机票（不知出发城） | 携程搜索 | `https://www.ctrip.com/search/searchresult?keyword={目的地}机票{日期}` —— **Step 1 应先问清出发城市，填进 `origin_city_code`** |
| 高铁 | 携程火车票 | `https://trains.ctrip.com/` 或带站名的搜索结果 |
| 酒店 | 携程酒店 | `https://hotels.ctrip.com/hotels/list?city={cityId}&keyword={酒店名}`<br>例：厦门 `city=25&keyword=如忆酒店` |
| 酒店（备选） | 美团 / 飞猪 | `https://hotel.meituan.com/` 或飞猪酒店搜索（**禁止 Booking 作为首选**） |
| 景点门票 | 官方 + 携程/大麦 | 官方预约站优先；次选 `https://www.ctrip.com/search/searchresult?keyword={景点名}门票` |
| 轮渡/船票 | 官方 | 例：厦门鼓浪屿 `https://www.xiamenferry.com/` |
| 入校预约 | 校方官方 | 例：厦大 `https://cabbage.xmu.edu.cn/`；deadline 里写公众号名，**不用 OTA** |
| 无直链 | `null` | 模板降级为携程搜索（**不是 Bing**） |

**数据来源对齐**：机票/酒店从哪个平台查的，链接就给哪个平台——高德 MCP `maps_flight_*` / 酒店详情返了跳转链就用返的；自己 WebFetch 携程比价就用携程深链。

**可选顶层字段**（方便拼机票链）：
```json
"origin_city_code": "sha",   // 出发城市三字码（Step 1 问用户）
"destination_city_code": "xmn"
```

### 反模式清单（禁止）

- `https://www.booking.com/...` —— 国内用户不常用，改携程/美团
- `https://www.trip.com/` —— Trip.com 国际版首页，改 `flights.ctrip.com` / `hotels.ctrip.com`
- `https://www.ctrip.com/flight/show-1.html` —— 纯占位，必 404
- `https://uri.amap.com/navigation?to=0,0` —— 坐标为 0 或缺省
- 任何 `example.com` / `placeholder` / **无 query 的泛域名首页**
- 用 Bing / Google 搜索当 prebook 主链（模板降级已改携程）
- 小红书 / 大众点评链接不是本次 MCP 或 WebFetch 实查返回的

---

## 7.2 价格调研硬约束（v2.1.0+）

> 完整流程见 [`price-research.md`](price-research.md)。**禁止凭 LLM 记忆写价格**；V10 会阻断无 `source` 的条目。

| 挂载位置 | 字段 | 时间轴（v2.2.0） |
|---------|------|------------------|
| `pois[]` | `price` + **`slot_costs[]`** | 右侧**批注卡**汇总该段全部花销 |
| `transports[]` | `fare` | 早晨酒店段并入**首 POI** `slot_costs`；其余段并入**出发 POI**；`to_idx:0` 标「回酒店」 |
| `meals.*.main` | `price` | 并入绑定 POI 的 `slot_costs` |
| `hotel` / `prebook[]` | `price` | 抽屉「花销预估」；大交通用 `attach` 挂抵达/离境段 |

- Step 1 必收 `party_size`
- Round 2 写 `transports[].fare`（与 direction MCP 同调用）
- Round 3 写 POI/meal `price` + **`pois[].slot_costs[]`**（逐项判断可能花销，不只填单一 `price`）
- Step 5–6 写 `prebook[].price` + `budget_summary`

---

## 8. 常见坑清单

- ❌ 用户清单全塞
- ❌ 计划当脚本
- ❌ 忽略节假日
- ❌ 忽略天气敏感
- ❌ 忽略航站楼
- ❌ 忽略末日返程
- ❌ 忽略酒店位置
- ❌ 社媒作营业时间
- ❌ 名店卡死整天
- ❌ 行程塞满不取舍

---

## 9. 核心原则（不可妥协）

1. **不端水，替用户删东西** —— 行程越顺越好，不是越满越好
2. **计划 = 参考坐标** —— 天气、位置、体力、饥饿均可覆盖
3. **基准价值** —— 给 agent 和用户清楚定位：今日区域、锚点、可放弃点、补给点

---

## 10. Buffer / 跨城衔接（隐含规则）

- **首日**：轻量、不跑远、不压预约
- **末日**：留出返程机场时间，不排远郊
- **远郊**：仅放非节假日，与天数匹配
- **重预约点**：一天只一个，留恢复 buffer

---

## 11. 用户交互：四拍格式（详见 multi-turn-protocol.md）

所有决策提问遵循 **Re-ground → Simplify → Recommend → Options**，顺序不可换。

---

## 移植硬规则（不可妥协的 7 条）

1. **先删后排**（明说删什么 + 为什么）
2. **一天一区 + 一日一重预约**
3. **首末日按航站楼和返程时间倒推**
4. **餐厅是补给不是锚点**
5. **四拍交互 + Smart skip**
6. **每轮迭代必须跑当轮验证**（见 `iteration-rounds.md`）
7. **增量修改必须重验证**（一致性不允许被改坏而不报警）
