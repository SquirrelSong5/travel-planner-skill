# 三阶段分轮筛检（v1.5.0）

> 本文件定义 SKILL.md Step 3 的 **3 轮迭代循环**：每轮筛**不同维度**，不是同一套 V1-V7 重复三遍。
> 配套：`./validation-rules.md`（规则细节）、`../scripts/validate.py`（`--round 1|2|3`）、`./planning.md`（先删后排）。

---

## 为什么分三轮

v1.1–v1.4 的 3 轮迭代是「每轮全跑 V1-V7，哪条失败修哪条」——三轮验的是**同一套规则**。

v1.5.0 改为**流水线质检**：

```
Round 1 结构筛 → Round 2 时空筛 → Round 3 体验筛 → Step 6-7 输出
```

| 轮次 | 焦点 | 类比 |
|------|------|------|
| Round 1 | 该不该去、怎么分组 | TriFlow Planning 前的删点 |
| Round 2 | 来不来得及、路顺不顺 | 约束满足 + 高德实算 |
| Round 3 | 吃得顺、不踩雷、有备选 | TriFlow Governance / 体验抛光 |

**业内参考**（可延伸阅读，非硬依赖）：

- [TriFlow](https://arxiv.org/html/2512.11271)：Retrieval → Planning → Governance（有界 refine）
- [ATLAS](https://openreview.net/forum?id=mIYGiBf9Pm)：iterative plan critique + 约束管理
- [Multi-Agent Critic 模式](https://dev.to/palash1417/building-a-multi-agent-travel-planner-from-a-one-sentence-prompt-to-a-validated-budget-aware-5f8i)：确定性 Critic（代码规则）+ 有界 revision
- [Odysya](https://github.com/pranayyb/Odysya)：只重跑失败模块，不重跑已成功部分
- **trip-map-builder**：先删后排、一天一区

---

## 总流程

```mermaid
flowchart LR
    subgraph R1 [Round 1 结构筛]
        A1[删点/分组]
        A2[V1 V4 + AI V7]
    end
    subgraph R2 [Round 2 时空筛]
        B1[高德 route + polyline]
        B2[V2 V5 V8 V9]
    end
    subgraph R3 [Round 3 体验筛]
        C1[美团+高德+小红书]
        C2[V3 V6]
    end
    R1 --> R2 --> R3 --> OUT[渲染 HTML]
```

**收敛规则**：

- 当轮有 ❌ → **只修当轮维度**，重跑**当轮**（最多 3 次 attempt 仍算 1 个 Round 编号内的修复）
- 当轮全 ✅/⚠️ → 进入下一 Round
- Round 1–3 全部 ✅/⚠️ → 进 Step 6-7
- **满 3 个 Round 仍有关键 ❌** → 列剩余冲突请用户决策（不无限循环）

**修复范围约束**（防浪费）：

| 失败轮 | 允许修 | 禁止重跑 |
|--------|--------|----------|
| Round 1 | 挪日/删点/换酒店锚点/分组 | 高德 route 实算、餐厅调研 |
| Round 2 | 调时间/删 POI/补 transports | Round 1 删点逻辑、美团/小红书 |
| Round 3 | 换餐厅/补 indoor_backup/软信号 | 大规模改 POI 清单（应回 Round 1） |

---

## Round 1：结构合理性筛

**目标**：产出可执行的 POI 清单 + 每日主区域。**先删后排**。

### AI 必做

1. 删天数不够的远郊、节假日爆款远郊、用户禁忌点 → 写入 `deleted[]`（明说删了什么 + 为什么）
2. 清单分组：城内轻松 / 预约 / 远郊 / 可路过
3. 草案：每天主区域 + 锚点 POI + 粗时间块（**不**调高德 route，只用直线距离预筛）
4. 酒店锚点是否覆盖最多天数（🤖 AI 审查）
5. V7 用户禁忌：方案中不得出现禁忌类型 POI

### 脚本必跑

```bash
python scripts/validate.py trip_data.json --round 1 --pretty
```

| 规则 | 方式 |
|------|------|
| V1 区域一致性 | ⚙️ 脚本 |
| V4 一日一重预约 | ⚙️ 脚本 |
| V7 用户禁忌 | 🤖 AI 自填进 validation_report |

### Round 1 产出

- `tripData.days[].pois` 草案
- `tripData.deleted[]`
- `validation_report.rounds[]` 追加一条 `phase: "结构筛"`

**不通过 → 不进 Round 2**。

---

## Round 2：时空可行性筛

**目标**：结构确定后，用高德实算验证通勤与末日缓冲。

### AI 必做

1. 对每对相邻 POI 调 `maps_direction_*` → `duration_min` + `transports[].path` + `source: "amap-mcp"`
2. 用高德 route 结果填 V2（🤖 `source: "ai-amap"`）
3. 检查累计通勤是否「赶死」（🤖 critique）

### 脚本必跑

```bash
python scripts/validate.py trip_data.json --round 2 --pretty
```

| 规则 | 方式 |
|------|------|
| V2 时间可行性（粗算） | ⚙️ 脚本粗算 + 🤖 高德实算 |
| V5 末日返程缓冲 | ⚙️ 脚本 |
| V8 MCP 必跑痕迹 | ⚙️ 脚本 |
| V9 实算 vs 粗算 | ⚙️ 脚本 |

### Round 2 产出

- `tripData.days[].transports[]` 全填
- `validation_report.rounds[]` 追加 `phase: "时空筛"`

**不通过 → 只修时空，不重跑 Round 1 删点**。

---

## Round 3：体验质量筛

**目标**：结构和时间 OK 后，补餐厅 + 软信号 + 天气备选。

### AI 必做

1. 美团攻略 WebFetch → 高德 POI 详情 → 小红书「排队/避雷」
2. 每顿 2–3 候选（主推 + 备选），写清 `source` 留痕
3. 户外 POI 补 `indoor_backup`
4. 体验 critique：游客店、排队风险、节奏太赶

### 脚本必跑

```bash
python scripts/validate.py trip_data.json --round 3 --pretty
```

| 规则 | 方式 |
|------|------|
| V3 餐厅区域匹配 | ⚙️ 脚本 |
| V6 户外天气敏感 | ⚙️ 脚本 |

### Round 3 产出

- `tripData.days[].meals[]` 完整
- `validation_report.rounds[]` 追加 `phase: "体验筛"`

**三轮全 ✅/⚠️ → Step 6-7**。

---

## 每轮 AI Critique 模板（必写，防走过场）

每轮末 AI **必须**输出并嵌进 `tripData.validation_report.rounds[]`：

```md
## Round {N} · {结构筛|时空筛|体验筛} 审查

### 本轮焦点
{一句话}

### 发现的问题
- {问题} → 修复动作：{...}
（无问题写「未发现需修复项」）

### 验证结果
| ID | 状态 | 说明 |
|----|------|------|
| V* | ✅/⚠️/❌ | ... |

### 本轮结论
{通过，进入 Round N+1 / 不通过，修复后重跑 Round N}
```

**JSON 结构**（每条 round 记录）：

```json
{
  "round": 1,
  "phase": "结构筛",
  "focus": "删点、分组、一天一区、用户禁忌",
  "issues": ["富士山挪到 Day 4 → 已执行"],
  "conclusion": "通过，进入 Round 2",
  "rules": [ ... ]
}
```

---

## validate.py 与 Round 映射

| `--round` | 规则 ID | 用途 |
|-----------|---------|------|
| `1` | V1, V4 | Step 3 Round 1 末 |
| `2` | V2, V5, V8, V9 | Step 3 Round 2 末 |
| `3` | V3, V6 | Step 3 Round 3 末 |
| 缺省 / `--check` 全量 | V1–V6, V8, V9 | 增量修改后 / 最终交付前复检 |

V7 **永不进脚本**——每轮由 AI 在 `rules` 里自填（Round 1 必查）。

**最终交付前**建议再跑一遍全量：

```bash
python scripts/validate.py trip_data.json --pretty
```

---

## 增量修改时的 Round 子集

| 用户修改 | 必跑 Round / 规则 |
|----------|------------------|
| 单点替换 POI | Round 2（V2,V8,V9）+ 若换餐厅则 Round 3 |
| 加日 / 删日 | 受影响 day 的 Round 1→2→3 顺序重跑 |
| 改酒店锚点 | Round 1（V1）+ Round 2 + Round 3（V3） |
| 只换餐厅 | Round 3（V3） |
| 节奏拆分 | 新拆两日完整 Round 1→2→3 |

---

## 与 Step 4 的关系

SKILL.md 主流程里 **Step 4「补吃饭」** 在 v1.5.0 并入 **Round 3 体验筛**（餐厅是三源组合最重的一步）。

若 AI 已在 Round 3 补全 `meals[]`，Step 4 可一句话确认「已在 Round 3 完成」，不必重复调研。
