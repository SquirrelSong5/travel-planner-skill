---
name: travel-planner
description: 旅行规划助手 —— **唯一交付物 = 单文件 HTML 部署到 GitHub Pages 的 URL**（手机/电脑浏览器直接看）。通过高德地图 MCP（路线/POI/酒店/天气/POI 详情）、**小红书 skill Step 1.5 目的地攻略** + Round 3 店级避雷、美团攻略 WebFetch（编辑过的好店清单）三件套，**零装零扫码**生成含酒店、每日行程、餐厅候选的单文件 HTML 旅行方案。大众点评 OpenCLI 降级为"深度档"（必吃榜 + 评价数才用）。支持多轮对话、**v1.5.0 三阶段分轮筛检**（Round1结构→Round2时空→Round3体验，每轮筛不同维度）、增量修改。**v2.3.0**：Step 1.5 必做小红书目的地攻略后再分组排线。**v1.5.0 硬约束**：AI 必跑 MCP + 必部署 GitHub Pages。适用场景：用户提到"规划旅行"/"做个行程"/"旅行方案"/"旅游规划"/"plan my trip"/"trip itinerary"/"travel plan"，或同时提到高德/小红书/大众点评三个数据源中的两个以上。
---

# travel-planner

## 🔴 v1.5.0 硬约束：唯一交付物 + 必跑 MCP

> **v1.5.0 起明确写入 SKILL.md 顶部**，作为 AI 必须遵守的硬规则：

### 硬约束 1：唯一交付物是【HTML 部署到 GitHub Pages 的 URL】

- ❌ **不允许** AI 把 PDF / Word / Markdown / 长图作为"输出"——**PDF / Word / Markdown 是 chat 里的中间产物，HTML URL 才是交付物**
- ❌ **不允许** AI 写"用浏览器 Cmd+P 打印为 PDF"——**这是用户的**后续操作**，不是 AI 的输出**
- ✅ **必须**走 `gh repo create` + `gh repo push` + 返回 `https://USERNAME.github.io/REPO/`
- ✅ **必须**：手机 / 电脑打开 URL 直接看（响应式 HTML）

### 硬约束 2：必跑高德实时数据（不能凭 LLM 记忆）

- ❌ **不允许** AI 凭训练数据**写** POI 名称 / 地址 / 营业时间 / 评分 / 路线 / 通勤时间 / 餐厅推荐 / 酒店信息——**这些数据必须实时查询**
- ✅ **必须**调高德 MCP `maps_text_search` / `maps_search_detail` / `maps_geo` 拿 POI 真实数据
- ✅ **路线时间/费用**：调 MCP `maps_direction_walking/driving/bicycling/transit_integrated`
- ✅ **地图折线 polyline**：MCP `steps` **无坐标时**，**必须**用同一 Key 调 REST `/v3/direction/*` 提取 `steps[].polyline` → 写 `transports[].path`（详见 `references/amap-mcp-usage.md` §2.3、**P28**）
- ✅ `transports[].source` 写 `"amap-mcp"`（MCP 自带 polyline 时）或 `"amap-rest-api"`（REST 画线兜底）——**不是** `"ai-fallback"` / `"straight-line"` / 空
- ❌ **不允许**手工补 2–3 个「路过某某路」中间点冒充折线
- ❌ **不允许** AI 报告"✅ V2 通过"但实际是 LLM 记忆算的——`scripts/validate.py` **V8 阻断**
- ⚠️ **MCP 整站不可用**（v2.0.0 P23 三层探针失败）：POI/天气等走 **REST API 全量降级**（详见 `references/amap-mcp-usage.md` §P23–P25）

### 硬约束 3：增量修改后必重跑 V1-V6 + V8 + V9 受影响项 + 重渲 HTML + 重部署

- ❌ **不允许** AI 自报告"修改完成"但没重渲 HTML / 没重部署 GitHub Pages
- ✅ **必须**：`python scripts/validate.py` → 渲染 HTML → `gh repo push` → 返回新 URL

### 为什么 v1.5.0 要写硬约束

> 之前 v1.1 / v1.2 / v1.3 / v1.4 都没用——AI 看到 SKILL.md 顶部只是"这是什么" / "客户端适配层"这种"软描述"，**没有强提示"这是硬规则、违反就阻断"**。
> 实际使用中：
> 1. 用户问"我在手机怎么看" → AI 推论"PDF"（错，应该是 GitHub Pages URL）
> 2. AI 凭训练数据写 POI / 路线 / 餐厅 → 数据不准 / 过期 / 凭空编
> 3. AI 报告"✅ 全通过"但 V2 是 LLM 记忆算的
>
> **v1.5.0 修复**：硬约束文字放 SKILL.md **顶部**（AI 必看）+ `scripts/validate.py` **V8 阻断**（代码层校验）+ `template.html` JS 校验（用户可查）。

---

## 这是什么

一个**客户端无关**的旅行规划 Skill（兼容 Claude Code CLI / Hermes desktop GUI / 其他支持 MCP 的客户端）。输入：用户的旅行需求（目的地、日期、人数、偏好、禁忌）。
输出：一个**单文件 HTML**（卡片化、无外部依赖、可直接手机打开分享）+ 多轮对话里的方案迭代。

定位：**生成出发前的参考坐标，不是假装旅行会逐小时照做的执行脚本**。
（参考项目 trip-map-builder 的核心理念，本 skill 沿用。）

---

## 客户端适配层（v1.4.0 重构：覆盖 7 个客户端）

> **v1.1 → v1.4.0 重大扩展**：原版只覆盖 Claude Code CLI + Hermes desktop GUI 两个客户端。**v1.4.0 起扩展到 7 个客户端**：Claude Code / Hermes / Cursor / Codex CLI / Google Cloud Code / Trae / CodeBuddy——基本覆盖国内用户能接触到的所有 AI coding 客户端。
>
> **核心原则**：
> 1. **MCP tool 名字是跨客户端统一的**（`mcp__amap__maps_direction_walking` 在 7 个客户端里都叫这个）—— 这是 MCP 协议的设计目标，**AI 不用管客户端，只看自己工具列表**
> 2. **MCP 装/卸命令**和**配置位置**因客户端而异——AI 按探测到的客户端走对应命令
> 3. **Shell 执行方式**有 3 种：`!cmd` 前缀（CC）/ 终端工具（Hermes/Cursor/Cloud Code/CodeBuddy）/ 直接 shell（Codex CLI）
> 4. **重启策略**也分：必须重启（CC / Cursor / Cloud Code / Trae / CodeBuddy）/ 不需要（Hermes）/ 项目级 config 改动热加载（Codex）
>
> 本节给出一套**客户端感知**的工作流，**同一份 skill 在 7 个客户端跑出来的体验一致**。

### 7 个客户端速查

| 客户端 | 平台 | 探测方式 | MCP 安装方式 | 配置位置 | Shell 执行 | MCP 重启 |
|--------|------|---------|------------|---------|----------|---------|
| **Claude Code CLI** | Mac/Linux/Windows 终端 | `which claude` 存在 | `claude mcp add ...` | `~/.claude.json` | 用户输入 `!cmd` 前缀 | **必须**：完全退出 CC 重开 |
| **Hermes desktop GUI** | Mac 桌面 app | `which hermes` 存在 / 工具列表有 `terminal()` | `hermes mcp add ...` | `~/.hermes/config.yaml` | AI 用 `terminal()` 工具直接跑 | **不需要**（下次启动自动加载）|
| **Cursor** | Mac/Win/Linux IDE | `which cursor` 存在 / 工具列表有 `run_terminal_cmd` | 编辑 `~/.cursor/mcp.json` 或 IDE 设置面板 | `~/.cursor/mcp.json`（全局）/ `.cursor/mcp.json`（项目）| AI 用 `terminal` / `run_terminal_cmd` 工具 | **必须**：Cmd+Shift+P → Reload Window |
| **Codex CLI** (OpenAI) | 终端 | `which codex` 存在 | `codex mcp add ...` | `~/.codex/config.toml`（全局）/ `.codex/config.toml`（项目）| 直接 shell（Codex 自己跑）| **自动**（项目级 config 改动热加载；全局 config 需重启会话）|
| **Google Cloud Code** | 浏览器 / VS Code 扩展 | 在 Cloud Shell 终端 / VS Code 扩展里跑 AI | 编辑 `~/.cloudshell_cloudsdk_mcp.json` 或 VS Code 设置 | `~/.cloudshell_cloudsdk_mcp.json` | AI 用 `terminal` 工具 | **必须**：重开会话 |
| **Trae** (字节) | Mac/Win IDE | `which trae` 存在 | IDE 内 MCP 设置面板 | Trae 内部配置 | AI 用终端工具 | **必须**：重启 IDE |
| **CodeBuddy** (腾讯) | Mac/Win IDE | `which codebuddy` 存在 | IDE 内 MCP 设置面板 | CodeBuddy 内部配置 | AI 用终端工具 | **必须**：重启 IDE |

> **AI 怎么自检自己跑在哪个客户端**（4 选 1）：
> 1. `which claude` / `which hermes` / `which cursor` / `which codex` / `which trae` / `which codebuddy` 哪个存在 → 那个客户端
> 2. 工具列表里有没有 `terminal()` / `run_terminal_cmd` 工具 → 大概率是 GUI 客户端（Hermes / Cursor / Cloud Code / Trae / CodeBuddy）
> 3. 工具列表里的 `mcp__amap__*` 等前缀都在 → 客户端已加载 MCP（CC / Hermes / Cursor / Codex 都有可能）
> 4. 都探测不到 → **直接问用户一次**："你用的是哪个 AI 客户端？Claude Code / Hermes / Cursor / Codex / Cloud Code / Trae / CodeBuddy？"
>
> **建议路径**：先用 `which` 命令探（3 秒完成），探不到再问用户。

### 7 个客户端命令映射表

> **AI 在执行任何 shell 命令前，先按本表翻译**。**不要硬编码 tool 数量或具体 tool 名字**——`mcp__amap__maps_direction_walking` 这种 AI 应该看自己工具列表里实际加载的（如 CHANGELOG v1.0.1「动态探查原则」所述）。本表只列**命令结构**。

| 操作 | Claude Code | Hermes | Cursor | Codex CLI | Cloud Code | Trae / CodeBuddy |
|------|------------|--------|--------|----------|-----------|------------------|
| **加 MCP server** | `claude mcp add <name> <args>` | `hermes mcp add <name> <args>` | 编辑 `~/.cursor/mcp.json` + Cmd+Shift+P Reload | `codex mcp add <name> <args>` | 编辑 `~/.cloudshell_cloudsdk_mcp.json` | IDE 内 MCP 设置面板 |
| **加 HTTP MCP** | `claude mcp add --transport http <name> <url>` | `hermes mcp add <name> --transport http --url <url>` | JSON `"type": "http"` + `"url": "..."` | `codex mcp add <name> --url <url>` | JSON `"httpUrl": "..."` | IDE 表单 |
| **列 MCP** | `claude mcp list` | `hermes mcp list` / `hermes mcp ls` | 看 `~/.cursor/mcp.json` 文件 | `codex mcp list` | 看配置 JSON | 看 IDE 设置面板 |
| **删 MCP** | `claude mcp remove <name>` | `hermes mcp remove <name>` / `hermes mcp rm <name>` | 编辑 `~/.cursor/mcp.json` 删条目 | `codex mcp remove <name>` | 编辑 JSON 删条目 | IDE 设置面板删 |
| **跑 shell** | 用户输入 `!cmd` 前缀 | AI 用 `terminal()` 工具 | AI 用 `terminal` / `run_terminal_cmd` 工具 | AI 自己跑 shell | AI 用 `terminal` 工具 | AI 用 IDE 终端工具 |
| **配置位置** | `~/.claude.json` | `~/.hermes/config.yaml` | `~/.cursor/mcp.json` | `~/.codex/config.toml` | `~/.cloudshell_cloudsdk_mcp.json` | IDE 内部 |
| **MCP 生效** | **必须**完全退出重开 | **自动**（下次启动）| Cmd+Shift+P → Reload | 项目级 config 自动 / 全局需重启 | **必须**重开会话 | **必须**重启 IDE |
| **客户端命令** | `claude` | `hermes` | `cursor` | `codex` | —（Cloud Shell）| `trae` / `codebuddy` |

### 给 AI 看的 7 客户端决策树

**Step 0 开头必做**（1-3 步搞定客户端识别）：

```
1. 跑探测命令（哪个返回非空就选哪个）:
   - !which claude   (CC)
   - !which hermes   (Hermes)
   - !which cursor   (Cursor)
   - !which codex    (Codex)
   - !which trae     (Trae)
   - !which codebuddy (CodeBuddy)
   备注：Cloud Code 通常在 Cloud Shell 终端里 / VS Code Cloud Code 扩展里

2. 看工具列表：
   - 有 terminal() / run_terminal_cmd → GUI 客户端（4 个候选）
   - 没 → CC / Codex CLI（命令行客户端）

3. 探测不到任何 → 直接问用户一次
```

**当且仅当探测到客户端 X**（X ∈ {CC, Hermes, Cursor, Codex, Cloud Code, Trae, CodeBuddy}）：

- ✅ 用 X 客户端的 `mcp add/list/remove` 命令（参见上表）
- ✅ 用 X 客户端对应的 shell 执行方式（`!cmd` / `terminal()` / `run_terminal_cmd` / IDE 终端）
- ✅ 写配置到 X 客户端的配置文件（`~/.claude.json` / `~/.hermes/config.yaml` / `~/.cursor/mcp.json` / `~/.codex/config.toml` / IDE 内部）
- ✅ 按 X 客户端的重启策略提醒用户
- ❌ **不要**把 CC 的 `claude mcp add` 用到 Hermes / Cursor / Codex（**命令不通用**）

**两套都不确定时**：
- 直接问用户一次（最多 1 个问题），确认后整份 skill 走对应分支

> **为什么不让 AI 在多个客户端用同一套命令**：CC / Hermes / Cursor / Codex / Trae / CodeBuddy 的 `mcp add` 语法**不通用**（subcommand 结构、flag 命名、配置位置、配置格式都不同），AI 强行混用会出现"看起来在跑实际不生效"的 silent failure，调试成本更高。
>
> **跨客户端统一的部分**（**AI 不用管的**）：
> - ✅ **MCP tool 名字**：所有客户端里 `mcp__amap__maps_direction_walking` 都叫这个——MCP 协议的设计
> - ✅ **MCP server 内部行为**：高德 MCP server 在 7 个客户端里跑出来的结果**完全一致**（同一份 npm 包，同一份代码）
> - ✅ **输出 JSON 结构**：MCP tool 名字跨客户端一致；**但路线类 MCP 常不返回 polyline**——画线走 REST `steps[].polyline`（§2.3 / P28）
>
> **所以 v1.3.0 的真实路径渲染 / v1.2.0 的餐厅调研 / v1.1.0 的代码级验证 / 等等，**所有"AI 调 MCP tool"的部分都是跨客户端一致的**——**只有"装 MCP + 跑 shell + 重启"这三件事是客户端相关的**。

### 多客户端场景实战

**场景 A：用户在 Cursor 触发**

```
🟢 AI: 我跑探测命令… which cursor 返回 /usr/local/bin/cursor
      ├─ 客户端：Cursor
      ├─ 工具列表：有 terminal 工具（我直接跑 shell）
      └─ 配置位置：~/.cursor/mcp.json

      [编辑 ~/.cursor/mcp.json，加高德 MCP 条目]
      [Cmd+Shift+P → Reload Window（AI 不能做，必须用户）]
      🔴 AI: 请按 Cmd+Shift+P，输入 Reload Window，回车。
            完事告诉我「reload 好了」。

用户: reload 好了

🟢 AI: [tool: mcp__amap__maps_direction_walking origin=... destination=...]
      ✅ 通了。
```

**场景 B：用户在 Cloud Code（Cloud Shell 终端里）触发**

```
🟢 AI: 客户端是 Google Cloud Code（Cloud Shell 终端 / VS Code Cloud Code 扩展）
      配置位置：~/.cloudshell_cloudsdk_mcp.json

      [编辑 ~/.cloudshell_cloudsdk_mcp.json，加高德 MCP 条目]
      🔴 AI: Cloud Code 改完配置必须重开会话才能加载。
            请在 Cloud Shell / Cloud Code 扩展里开新会话。
            完事告诉我「新会话好了」。
```

**场景 C：用户在 Codex CLI 触发**

```
🟢 AI: which codex 返回 /usr/local/bin/codex → 客户端是 Codex CLI

      [tool: codex mcp add amap --url https://mcp.amap.com/mcp?key=... ]
      ✅ 项目级 config 自动加载（不需要重启）
      
      [tool: mcp__amap__maps_geo address=东京]
      ✅ 通了。
```

**场景 D：用户在 Trae / CodeBuddy 触发**

```
🟢 AI: which trae 返回 /usr/local/bin/trae → 客户端是 Trae IDE

      🔴 AI: Trae 的 MCP 装在 IDE 设置面板里，AI 改不了配置。
            请你打开 Trae → Settings → MCP → 加 server:
            - Name: amap
            - URL: https://mcp.amap.com/mcp?key=YOUR_KEY
            加完告诉我「加好了」。
      
      🔴 AI: 加完需要重启 Trae 加载 MCP。
            完全退出 Trae，重开。
            完事告诉我「重启好了」。
```

### ⚠️ 已知坑（v1.4.0 新增）

1. **Cursor 的 MCP 配置在 IDE 设置面板里改的不写盘**——必须编辑 `~/.cursor/mcp.json` 文件才持久化
2. **Cloud Code 浏览器端**（不是 VS Code 扩展）改完 `~/.cloudshell_cloudsdk_mcp.json` **必须重开会话**才生效
3. **Codex CLI 项目级 `mcp_servers` 用 TOML 格式**，全局用 `~/.codex/config.toml`——格式不同，**AI 跑 `codex mcp add` 是统一入口**，不需要手写 TOML
4. **Trae / CodeBuddy 的 MCP 配置不暴露在文件系统**——必须 IDE 操作
5. **`hermes mcp add` 实际可能需要 `--` 分隔符**（如 `hermes mcp add playwright -- npx @playwright/mcp@latest`）——AI 跑前用 `hermes mcp add --help` 确认
6. **CC 的 `--transport http` flag** 和 Hermes 的 `--transport http` flag **位置不同**（CC: `--transport http <name> <url>`；Hermes: `<name> --transport http --url <url>`）——按本表走对应命令

---

## 数据源 & MCP 依赖

> **v1.2.0 重构**：餐厅数据从"主推 opencli 深度档"改为"**高德 POI + 美团攻略 WebFetch + 小红书**"三件套，**零装零扫码**。opencli 降级为"深度档"（非要必吃榜 + 评价数才用）。
>
> **国内优先**：所有数据源都按"国内地点"优化选型与降级。

| 数据源 | 形态 | 用途 | 缺失降级 |
|--------|------|------|----------|
| **高德地图** | 官方 MCP `https://mcp.amap.com/mcp?key=YOUR_KEY` | POI 搜索、路线规划、地理编码、距离测量、天气、**POI 详情（评分/营业时间/类型/人均/坐标）** | 提示申请 Key，降级为通用知识 |
| **美团攻略** 🆕 | WebFetch `guide.meituan.com`（零装） | **国内 8 大热门城市**（沪/京/蓉/穗/深/杭/渝/汉）的**编辑过的好店清单**（数据来源 = 大众点评公开数据 + 媒体评测） | 高德 `text_search` 按菜系搜兜底 |
| **小红书** | Python skill `autoclaw-cc/xiaohongshu-skills`（`python scripts/cli.py ...`）| **Step 1.5 目的地攻略**（必去/避雷/分区）+ Round 3 店级氛围/排队软信号 | WebFetch `xiaohongshu.com` M 站 |
| **大众点评**（深度档）| OpenCLI + Chrome Browser Bridge 扩展（**可选，非必需**）| 必吃榜入选 + 真实评价数 + 排队实况 + 踩雷关键词 | 主轨方案已够用，**不需要装** |

> **小红书数据源（v1.0.2 唯一方案）**：用 `autoclaw-cc/xiaohongshu-skills`（Python CLI + Chrome 扩展）。详见 `references/setup-guide.md` §2 / `references/xhs-research.md`。
>
> **餐厅调研 v1.2.0 主推组合**：高德 POI 详情（坐标/营业/评分）+ 美团攻略（候选池）+ 小红书（软信号）= **零装零扫码**。详见 `references/dianping-research.md`（已重构） / `references/meituan-guide-research.md`（新增）。

详见 `references/amap-mcp-usage.md` / `xhs-research.md` / `dianping-research.md` / `meituan-guide-research.md`。

---

## 主流程（7 步 + 3 轮迭代 + 增量修改）

```
Step 0：环境自检 + 引导（每次启动必做）
  ↓
Step 1：抽硬约束（Re-ground + 一次性问关键信息）
  ↓
Step 1.5：小红书目的地攻略（必做，决策输入）← v2.3.0
  ↓
Step 2：清单分组 + 酒店候选（受 Step 1.5 约束）
  ↓
Step 3：【3 轮分阶段筛检】（v1.5.0 核心）
   Round 1 结构筛 → Round 2 时空筛 → Round 3 体验筛
   每轮筛不同维度 + validate.py --round N
  ↓
Step 4：确认餐饮（Round 3 已补则跳过重复调研）
  ↓
Step 5：补票务 / 跨城交通
  ↓
Step 6：写参考文档（结构化输出）
  ↓
Step 7：渲染 HTML（assets/template.html + demo 数据 schema）
  ↓
【任何时候】用户说"改..." → 走增量修改路径（见 references/multi-turn-protocol.md）
```

---

## Step 0：环境自检 + 引导（小白友好）

> **目标**：零基础用户触发 skill 后，能在 5 分钟内跑起来。

### 0.1 自动检测

每次启动都做（不写 state.json，每次重新检测以反映真实状态）。**先按「客户端适配层」确认客户端**，再用本节的多源探测逻辑。

| 检测项 | 怎么检（**客户端感知**） | 必需 |
|--------|--------|------|
| **客户端类型** | 见「客户端适配层」探测三选一 | 🔒 **必先做** |
| **Playwright MCP** | 工具列表里有 `mcp__playwright__*`？<br>**或** 客户端配置里有 `playwright`（按客户端走对应命令探：`claude mcp list` / `hermes mcp list` / 看 `~/.cursor/mcp.json` / `codex mcp list` / 看 IDE 设置） | 🔒 **强制前置**（未装必须先装，详见 §0.3 情况 D） |
| **高德 MCP** | 工具列表里有 `mcp__amap__*`？<br>**或** 客户端配置里有 `amap` server？<br>**或** 环境变量 `AMAP_KEY` 非空？ | ✅ 必需 |
| **小红书 Skill** | `python ~/xhs-skill/scripts/cli.py check-login` 能跑通 | ⚠️ 推荐 |
| **大众点评**（深度档）| `which opencli` + Chrome 远程调试端口 9223 | 💡 可选（v1.2.0 起**默认不推荐装**）|

> **🔒 强制前置是什么意思**：Playwright MCP 未装时，**AI 不得进入 Step 1**。必须先引导用户装好（或用户显式说"降级 / 跳过"）才能继续。详见 §0.3 情况 D。
> 
> **为什么改"客户端感知"**：原版只检工具列表，Hermes 里 AI 看不到 CC 的 `mcp__*` 工具名（命名空间不同），单源检测在跨客户端会 false negative。多源 = 至少一个能命中就视为已就绪，更稳。

### 0.2 对话开头第一句话：自检结果展示

**完整格式（AI 自己探出来啥就写啥，**不要照抄下面的数字 / tool 名**）**：

> **🔍 探查方法（AI 必须自己跑）**：
> - **MCP tool 类**：看当前工具列表（系统自动注入），扫一遍 `mcp__*` 前缀工具；tool 数用**按客户端对应的命令**拿（CC: `claude mcp list` / Hermes: `hermes mcp list` / Cursor: 看 `~/.cursor/mcp.json` / Codex: `codex mcp list` / 其他: 看 IDE 设置）
> - **CLI 类**：用 `which <cmd>` / `<cmd> --version` / `<cmd> <subcommand>` 试探
> - **小红书**：跑 `python ~/xhs-skill/scripts/cli.py check-login`，返回"已登录"即 OK
>
> **展示原则**：自检报告**只列 AI 实际探到的内容**——"13 个 tool" 这种数字、AI 报告"已就绪（可查 POI/路线/距离/天气）"这种功能列举，**都是 AI 跑出来才写的，不是文档里抄的**。

**模板**（AI 填实际值）：

```
🔍 环境自检（AI 探查）
├─ ✅/❌ <MCP 名>：<状态>（<AI 自己探到的 tool 数或描述>）
├─ ...
```

**示例**（仅供参考，AI 不得照抄）：

```
🔍 环境自检
├─ ✅ Playwright MCP：已就绪（按客户端命令探到 mcp__playwright__* 14 个 tool，**CC 走 `claude mcp list` / Hermes 走 `hermes mcp list` / Cursor 看 `~/.cursor/mcp.json` / Codex 走 `codex mcp list` / Trae-CodeBuddy 看 IDE 设置**）
├─ ✅ 高德地图 MCP：已就绪
├─ ✅ 小红书：已就绪（`python ~/xhs-skill/scripts/cli.py check-login` 返回"已登录"）
└─ ⏭️ 大众点评：未配置（v1.2.0 起**非必需**，主轨用"高德 POI + 美团攻略 WebFetch"）
```

**小红书识别**（**v1.0.2 起只有 B 方案**）：
- `python ~/xhs-skill/scripts/cli.py check-login` 能跑 → 走 **B 方案**（autoclaw-cc/xiaohongshu-skills）
- 跑不通 → 推装 B 方案，或降级为 WebFetch

**状态分支**（**不依赖任何具体 tool 名**，只看"探到了几个 mcp_*_ 前缀"）：

- **Playwright 不在**（其他有几个无所谓）：🔒 不进 Step 1。强制走 §0.3 情况 D（推装 Playwright）
- **Playwright 在 + 至少高德也在**：直接进 Step 1，一句话带过自检
- **Playwright 在 + 高德缺**：AI 主动推装高德（必需项）
- **Playwright 在 + 仅高德（小红书/点评都缺）**：告知影响 + 提供「先配还是先用 demo」二选一

### 0.3 缺失时的引导流程

**情况 A：完全没配过（小白的第一次）**

**Re-ground**："travel-planner Step 0，环境自检。先把数据源配好才能查 POI / 路线。"

**Simplify**："5 分钟搞定，主要是注册一个高德账号拿 Key，复制一行命令就行。"

**Recommend**："我带你一步一步走，配完就能查东京的任意景点。"

**Options**：
- A. 跟着我一步步配（5 分钟）
- B. 先用 demo 演示（看成都示例，先不配）
- C. 我已经配过了

**根据选择**：

- 选 A → AI **主导**走 `references/setup-guide.md` 的"高德（必需）+ 小红书（推荐，B 方案唯一）+ 大众点评（v1.2.0 起**非必需**）"流程，前提是用户已装 [Playwright MCP](https://github.com/microsoft/playwright-mcp)（**按客户端走对应安装命令**：CC `claude mcp add playwright npx @playwright/mcp@latest` / Hermes `hermes mcp install playwright` / Cursor 编辑 `~/.cursor/mcp.json` / Codex `codex mcp add playwright -- npx @playwright/mcp@latest` / Trae-CodeBuddy IDE 设置面板）。整个过程用户只介入 2-3 次（收短信、扫码、**按客户端重启方式让 MCP 生效**）。**大众点评深度档只在用户明确要求"必吃榜 + 评价数"时才装**
- 选 B → 渲染 `examples/chengdu-3d.json`（默认国内示例）让用户看效果，结尾再问"效果 OK 吗？OK 的话花 5 分钟配一下，以后就是做自己的行程了"
- 选 C → 重新检测，确认就绪后进 Step 1

> **没有 Playwright MCP 的退化**：退到"半自动"模式，shell 步骤 AI 跑，浏览器步骤给命令用户手点（见 [references/multi-turn-protocol.md](references/multi-turn-protocol.md) §场景六·退路）。

**情况 B：已有部分 MCP，只缺某一项**

直接触发对应章节的引导，跳过已配置的。

**情况 C：用户中途说"不配了 / 跳过"**

尊重选择，明确告知降级影响（哪类数据不准），继续走流程。后续可在 Step 1 末再次询问"要不要回头配一下"。

**情况 D：Playwright MCP 未装（🔒 强制前置，必须先处理）**

> **关键规则**：Playwright MCP 是 AI 主导配置的唯一入口。**未装时 AI 不得自作主张降级、不得直接进 Step 1**。必须先推荐安装，等用户做出选择（装 / 显式降级）才能继续。

**Re-ground**："travel-planner Step 0，环境自检。Playwright MCP 没装，整个配置流程都得你来手动开浏览器。我强烈推荐先装，1 分钟换后面全自动化。"

**Simplify**："装一个 Microsoft 官方的 Playwright MCP 就行。**先告诉我你在哪个客户端**，我给你对应命令："

**按客户端走对应命令**（**AI 跑前必须先按 §客户端适配层 探测到客户端 X，再选 X 对应的命令**）：

```bash
# Claude Code CLI（用户输入 ! 让 AI 跑，或 AI 用 terminal tool）
!claude mcp add playwright npx @playwright/mcp@latest

# Hermes desktop GUI（AI 用 terminal() 工具跑）
hermes mcp install playwright   # 优先用 catalog 方式（一键）
# 或 catalog 里没有时：
hermes mcp add playwright -- npx @playwright/mcp@latest

# Cursor（AI 编辑 ~/.cursor/mcp.json，然后引导用户 Cmd+Shift+P Reload Window）
# 编辑 mcpServers.playwright = { "command": "npx", "args": ["@playwright/mcp@latest"] }

# Codex CLI（AI 自己跑）
codex mcp add playwright -- npx @playwright/mcp@latest

# Cloud Code（AI 编辑 ~/.cloudshell_cloudsdk_mcp.json，引导用户重开会话）
# 编辑 mcpServers.playwright = { "command": "npx", "args": ["@playwright/mcp@latest"] }

# Trae / CodeBuddy（AI 改不了配置，引导用户 IDE 内加 + 重启 IDE）
```

**Recommend**："强烈推荐装。**装完按客户端走对应重启方式让 MCP 生效**（CC 退出重开 / Hermes 下次启动自动 / Cursor Cmd+Shift+P Reload / Codex 项目级自动 / Cloud Code 重开会话 / Trae-CodeBuddy 重启 IDE）。后面 5 个 MCP 全程我开浏览器帮你点，你只介入 2-3 次。"

**Options**：
- A. 装（推荐，1 分钟）—— AI 立即按客户端跑对应命令，等用户回来确认
- B. **我明白降级影响，但仍要降级** —— 用户**必须显式说出降级**才走降级路径；AI 记录用户主动降级到日志，后续可在 Step 1 末再次询问要不要回头装
- C. 先用 demo 演示（不装不降级，看成都示例）—— 临时演示，不进入正式规划流程

**根据选择**：

- 选 A → AI 按**§客户端适配层探测到的客户端 X**走对应分支：
  - **CC / Codex**：AI 跑对应 `mcp add` 命令 → 提醒用户按客户端重启（CC 完全退出 / Codex 项目级自动） → 用户回「好了」 → AI 重新自检
  - **Hermes**：AI 跑 `hermes mcp install playwright`（或 `hermes mcp add playwright -- npx @playwright/mcp@latest`）→ **不需要告诉用户重启**（下次启动自动加载）→ 引导用户「下次新建一个 Hermes 会话」→ 用户回「好了」→ AI 重新自检
  - **Cursor / Cloud Code**：AI 编辑对应 JSON → 引导用户「Cmd+Shift+P Reload Window」/「重开会话」 → 用户回「好了」 → AI 重新自检
  - **Trae / CodeBuddy**：AI **改不了配置**，引导用户 IDE 设置面板里加 → 用户回「加好了」→ AI 引导用户「重启 IDE」→ 用户回「重启好了」→ AI 重新自检
  - 若 `mcp__playwright__*` 出现 → 进 Step 1；若仍未出现 → 引导排查（见场景八）
- 选 B → AI 显式记录「用户主动降级，Playwright 未装」→ **进入 §0.3 情况 A 的"半自动"模式**（shell 步骤 AI 跑，浏览器步骤给命令用户手点；见 `references/multi-turn-protocol.md` §场景六·退路）
- 选 C → 渲染 `examples/chengdu-3d.json` 演示，**不进入正式规划流程**

> **为什么不能默认降级**：降级意味着小红书 / 大众点评配置从"AI 全程开浏览器"退到"每步用户手点"，每次配耗时 15-20 分钟；装 Playwright 一次 1 分钟，长期受益。**默认走"推装"才能保护用户不被"自检→跳过"的温水煮青蛙体验反复降级**。

### 0.4 引导期间的执行方式

> **v1.0 重大变化**：AI 用 [Playwright MCP](https://github.com/microsoft/playwright-mcp) 自己开浏览器，配 MCP 全流程用户只介入 2-3 次。详见 `references/setup-guide.md` §-1 / `references/multi-turn-protocol.md` §0。

**AI 可以做的事**（无需确认）：
- 探测 MCP 工具可用性（`mcp__amap__*` / `mcp__playwright__*` 等；小红书跑 `python scripts/cli.py check-login`）
- 检测 `which opencli` / **按客户端走对应 mcp list 命令** / `which uv` 等只读命令
- **🟢 装 Playwright MCP 后**：用 `mcp__playwright__browser_navigate/click/type/snapshot` 走完注册表单
- 跑 shell 命令装包（`npm install` / `pip install` / `uv sync` / `docker pull`）
- 按客户端走对应 MCP 装入命令（CC `claude mcp add` / Hermes `hermes mcp add` / Cursor 编辑 `~/.cursor/mcp.json` / Codex `codex mcp add` / Cloud Code 编辑 JSON / Trae-CodeBuddy 引导用户 IDE 操作）
- 跑 `gh auth login` / `gh repo create` 部署到 GitHub Pages
- 渲染 demo HTML 给用户看

**AI 需要用户提供一次信息的步骤**（🟡）：
- 收高德注册短信验证码
- 收 gh device flow 的 8 位 code 后去网页贴

**必须用户亲手做的步骤**（🔴，**按客户端走**）：
- 用小红书 App / 大众点评 App 扫二维码登录
- macOS 首次弹「是否允许打开 Chrome」对话框时点「打开」（一次性 Gatekeeper 确认）
- **仅当用户主动选择"复用日常 Chrome session"时**：chrome://extensions 装 Chrome 扩展（小红书 B 方案）
- **按客户端走对应"让 MCP 生效"操作**：
  - CC / Cursor / Cloud Code / Trae / CodeBuddy：必须**完全退出 / Reload Window / 重开会话 / 重启 IDE**
  - Hermes / Codex 项目级：下次启动自动加载

> **🔄 v1.0.3 重要变化**：小红书的 Chrome 扩展**不一定要用户手装**。`autoclaw-cc/xiaohongshu-skills` 项目**自带 `scripts/chrome_launcher.py`——AI 跑一行就自动启 Chrome + 自动装 XHS Bridge 扩展**。**默认走 launcher 路径**，用户介入只剩"扫码 + 一次性 Gatekeeper 确认"。详见 `references/setup-guide.md` §2.2。

**AI 应该引导用户自己执行的事**（提供命令，**让用户按客户端走对应执行方式**）：

| 客户端 | 用户怎么执行 |
|--------|------------|
| **CC** | 用户输入 `!claude mcp add --transport http amap "https://mcp.amap.com/mcp?key=YOUR_KEY"` |
| **Hermes / Cursor / Cloud Code / CodeBuddy** | AI 自己跑（用 terminal tool） |
| **Codex CLI** | AI 自己跑 `codex mcp add` |
| **Trae** | AI 改不了，引导用户 IDE 内粘贴配置 |

### 0.5 配置完成后的验证

用户说"配好了 / 重启了 / 下次会话开了"之后，**AI 必须自己跑探查，不得照抄文档示例**：

1. **重新做 0.1 检测**（按 §0.1 多源探测逻辑）
2. **按客户端跑对应 mcp list 命令**拿当前已注册 MCP 列表（CC: `claude mcp list` / Hermes: `hermes mcp list` / Cursor: 看 `~/.cursor/mcp.json` / Codex: `codex mcp list` / Cloud Code: 看配置 JSON / Trae-CodeBuddy: 看 IDE 设置）
3. **跑一个最小化调用验证连通性**——**从该 MCP 工具列表里随便挑一个最轻量的 tool 试一下**：
   - 高德：调任一 `mcp__amap__*` tool（AI 看自己环境里有哪些 tool，挑最简单的）
   - 小红书：跑 `python ~/xhs-skill/scripts/cli.py check-login`
   - 大众点评：跑 `opencli dianping search "<keyword>" --city <city> --limit 1 -f json`
4. **不要**预设"用哪个 tool"——AI 看自己环境里实际加载的 tool 列表，**按可用 tool 试探**；试探失败再换下一个
5. 通过 → 进入 Step 1；失败 → 引导排查（见场景八）

### 0.6 关键原则

1. **不假设用户懂 MCP**：第一次必须解释"MCP 是什么、为什么要配"
2. **不强迫**：用户拒绝配置也能继续走流程（降级模式）
3. **不重复**：已经配置过的不要让用户重配
4. **可恢复**：配置失败时给清晰的回退路径
5. **可视化**：每个步骤说清楚"现在在做什么"、"完成后会发生什么"
6. **🟢🟡🔴 三色标注**：配置步骤前显式标"AI 跑 / AI 跑+你口供 / 必你做"，用户秒懂要做什么
7. **🔒 强制前置**：Playwright MCP 未装时 **AI 不得自作主张降级**，必须先推荐安装；**只有用户显式说"降级 / 跳过"才能降级**

---



### Step 1：抽硬约束（Re-ground + 一次性问）

**Re-ground**："行程规划 Step 1，先把硬约束搞清楚，免得排出来全要改。"

**必须问清的最小集合**（一次性问，不要拆成多轮）：
1. **日期**：出发日、回程日、到达时间、离开时间
2. **航站楼 / 车站**：机场名 + 航站楼（如适用）
3. **酒店**：已有（地址截图）/ 待选（推荐）
4. **想去点**：3-10 个地名/类型
5. **禁忌**：明确不要去的类型（如"不要寺庙"、"不要网红打卡"）
6. **人数 / 节奏**：几人 / 有无老人小孩 / 步行耐力 → 写入 `party_size`（v2.1.0 必填，价格 quantity 默认）
7. **餐饮预算 / 偏好**：能不能排队 / 必吃 / 忌口
8. **酒店偏好**（仅当 Step 1 已说"待选"时）：预算区间 / 类型偏好 / 区域偏好

**Smart skip**：用户已主动提到的字段不重复问。

**Question 格式**（四拍协议）：
- Re-ground：上面那句话
- Simplify：避免用"约束提取"这种术语
- Recommend：给一个默认建议（如"推荐先告诉我日期和酒店名"）
- Options：用 A/B/C 而非开放问答

完整四拍协议见 `references/multi-turn-protocol.md`。

### Step 1.5：小红书目的地攻略（v2.3.0 必做）

> **定位升级**：小红书从 Round 3 的「店级软信号验证」前移到 **Step 1.5 目的地级决策输入**。先读攻略，再分组排线；**不得**等 Round 3 才第一次搜小红书。
>
> 完整工作流见 `references/xhs-research.md` §0。

**时机**：Step 1 硬约束收齐后、**Step 2 清单分组之前**。

**AI 必做**（按优先级）：

1. **小红书**（首选 `~/xhs-skill/scripts/cli.py`）—— 搜目的地级关键词，粗筛 10–20 篇 → 精读 3–5 篇
2. **Web search** —— 补官方闭馆、预约、季节性、大型活动（小红书不覆盖的硬信息）
3. **与用户硬约束对齐** —— 用户「必去/禁忌」与攻略结论冲突时，**以用户为准**并说明删改理由

**推荐搜索词**（组合 2–3 个，含天数/人群）：

```
「{城市} {N}天 攻略」「{城市} 避雷」「{城市} 本地人推荐」
「{城市} {主题}」（毕业旅行 / 亲子 / 情侣 等，视 Step 1 而定）
```

**必产出 `xhs_destination_brief`**（写进 chat + 可选写入 `tripData.xhs_destination_brief`）：

| 字段 | 内容 |
|------|------|
| `must_visit` | 攻略高频提及、与用户不冲突的 POI/区域 |
| `skip_or_caution` | 避雷点、网红坑、季节不推荐 |
| `region_layout` | 建议分区/每天主区域（供 Step 2 分组参考） |
| `pace_hints` | 松散/紧凑、排队敏感点 |
| `source_notes` | 2–5 条代表笔记 title + URL |

**降级**（未装 xhs skill）：

1. WebFetch `xiaohongshu.com/search_result?keyword=...`（移动端 UA）
2. Web search「{城市} 旅游攻略 site:xiaohongshu.com」作补充
3. 在 brief 标注 `source: webfetch-degraded`，**不得**凭 LLM 记忆编造笔记结论

**与后续步骤关系**：

| 步骤 | 小红书角色 |
|------|-----------|
| Step 1.5 | **目的地攻略**（本步） |
| Step 2 | 用 `region_layout` / `skip_or_caution` 约束分组与酒店区域 |
| Round 1 | POI 池须覆盖 `must_visit` 或说明为何不纳入 |
| Round 3 | **店级**排队/避雷（`店名 + 排队`），不重复目的地级搜索 |

**不通过 / 未完成 Step 1.5 → 不进 Step 2**（降级模式须显式标注 brief 为降级）。

### Step 2：清单分组 + 酒店候选

**清单分组**（须对照 Step 1.5 的 `xhs_destination_brief`）：
- 城内轻松组（如浅草寺、涩谷 sky）
- 预约组（如米其林、teamLab、富士山新干线指定席）
- 远郊组（如富士山、镰仓、日光）
- 可路过组（如酒店附近的便利店 / 咖啡馆）

**酒店候选**（参考 `references/hotel-planning.md`）：
- 单城行程 → 高德 `poi_search keywords="酒店"` + `radius` 锚定主区域 → 商务/精品/民宿各 1 → 小红书笔记验证"新装修/隔音/近地铁"
- 多城行程 → 每城一个酒店锚点

把分组结果 + 酒店候选摆给用户确认一次，再进入 Step 3。

### Step 3：3 轮分阶段筛检（v1.5.0 核心）

> **v1.5.0 变化**：3 轮不再「每轮全跑 V1-V7」——改为**流水线质检**，每轮筛**不同维度**。详见 `references/iteration-rounds.md`。

```
Round 1 结构筛（该不该去、怎么分组）
    ↓ 通过
Round 2 时空筛（来不来得及、路顺不顺）
    ↓ 通过
Round 3 体验筛（吃得顺、不踩雷、有备选）
    ↓ 通过
Step 6-7 输出 HTML
```

| Round | 焦点 | 脚本命令 | 规则子集 |
|-------|------|----------|----------|
| **1 结构筛** | 删点、分组、一天一区、用户禁忌 | `validate.py --round 1` | V1, V4 + 🤖 V7 |
| **2 时空筛** | 高德 route 实算、polyline、末日缓冲 | `validate.py --round 2` | V2, V5, V8, V9 + 🤖 V2 实算 |
| **3 体验筛** | 美团→高德→小红书店级、户外备选、**地图折线复检** | `validate.py --round 3` | V3, V6, V8, V10 |

**每轮末必做 3 步**（硬流程）：

1. **跑当轮脚本**：
   ```bash
   python scripts/validate.py /path/to/trip_data.json --round {1|2|3} --pretty
   ```
2. **写 AI Critique**（不能只报 ✅）——嵌进 `tripData.validation_report.rounds[]`：
   - `round` / `phase`（结构筛|时空筛|体验筛）
   - `issues[]`：发现的问题 + 修复动作
   - `conclusion`：通过进下一轮 / 不通过重跑当轮
   - `rules[]`：当轮全部规则（含 V7 在 Round 1）
3. **合并到 `validation_report.rules`**（最终交付前跑全量 `validate.py` 无 `--round`）

**收敛**：当轮 ❌ → 只修当轮维度，不进下一轮；Round 1-3 全 ✅/⚠️ → 进 Step 6；满 3 Round 仍 ❌ → 请用户决策。

---

#### Round 1：结构合理性筛

**AI 必做**：对照 `xhs_destination_brief` 删远郊/禁忌点 → `deleted[]`；分组（城内/预约/远郊/可路过）；草案每天主区域 + POI + 粗时间块；V7 禁忌审查；酒店锚点覆盖天数审查；`must_visit` 未纳入须说明原因。

**不跑**高德 route、不调研餐厅。

```bash
python scripts/validate.py trip_data.json --round 1 --pretty
```

**不通过 → 不进 Round 2**。

---

#### Round 2：时空可行性筛

**AI 必做**（含 v2.1.0 价格 + v2.2.2 polyline）：

1. 每对相邻 POI **+ 酒店早晚通勤**（`from_idx`/`to_idx` **0 = 酒店**）：
   - 早晨：`{ from_idx: 0, to_idx: 首POI.idx }`（首日首 POI 已是酒店则跳过）
   - 傍晚：`{ from_idx: 末POI.idx, to_idx: 0 }`（末日末站为机场/车站则跳过）
   - **MCP** `maps_direction_*` → `duration_min` / `distance_m` / `fare`
   - **polyline**：若 MCP `steps` 无 `polyline` → **REST** `/v3/direction/*`（同 Key）→ 拼 `transports[].path`
   - `source`：`amap-mcp` 或 `amap-rest-api`（见 `references/amap-mcp-usage.md` §2.3、P28）

| 距离/场景 | MCP 工具 | REST（polyline 兜底） |
|----------|---------|----------------------|
| < 1.5km 步行 | `maps_direction_walking` | `/v3/direction/walking` |
| 1.5-10km 市内 | `maps_direction_transit_integrated` | `/v3/direction/transit/integrated` + `city` |
| 骑行 | `maps_bicycling` | `/v3/direction/bicycling` |
| > 10km / 跨城 | `maps_direction_driving` | `/v3/direction/driving` |

完整提取代码见 `references/amap-mcp-usage.md` §2.3–2.4。

```bash
python scripts/validate.py trip_data.json --round 2 --pretty
```

**不通过 → 只修时空，不重跑 Round 1 删点**。

---

#### Round 3：体验质量筛

**AI 必做**（含原 Step 4 餐厅调研）：

1. 美团攻略 WebFetch `guide.meituan.com/<city>/canyin` → 候选池
2. 高德 `maps_text_search` + `maps_search_detail` → 硬信号 + **`pois[].price` / `meals.*.price`** + **`pois[].slot_costs[]`**（枚举该段全部可能花销）
3. 小红书搜「<店名> 排队」「<店名> 避雷」（**店级**；目的地攻略已在 Step 1.5 完成）
4. 户外 POI 补 `indoor_backup`；体验 critique（游客店/排队/节奏）
5. Step 5–6 汇总 `prebook[].price` + `budget_summary`（详见 `references/price-research.md` §7）

HTML 时间轴花销为 **Word 批注式**（每段右侧 `slot_costs` 汇总，不展示 `source`）；逛街类 `user_editable` 由用户 localStorage 自填。

```bash
python scripts/validate.py trip_data.json --round 3 --pretty
```

---

#### 🔒 代码级硬约束 + 浏览器重算（v1.1.0 起，v1.5.0 保留）

- `validate.py`：脚本可验的规则**必须真跑**（按 `--round` 或全量）
- `template.html`：加载时 JS **强制重算** V1/V3/V4/V5/V6，覆盖 AI self-report
- 最终部署前建议全量复检：
  ```bash
  python scripts/validate.py trip_data.json --pretty
  ```

#### 7 条规则总览

| ID | 规则 | Round | 验证方式 |
|----|------|-------|---------|
| V1 | 区域一致性 | 1 | ⚙️ 脚本 |
| V4 | 一日一重预约 | 1 | ⚙️ 脚本 |
| V7 | 用户禁忌屏蔽 | 1 | 🤖 AI |
| V2 | 时间可行性 | 2 | 🤖 高德 + ⚙️ 粗算 |
| V5 | 末日返程缓冲 | 2 | ⚙️ 脚本 |
| V8 | MCP 必跑痕迹 / 地图折线 | 2, 3 | ⚙️ 脚本 |
| V9 | 通勤时间下限 | 2 | ⚙️ 脚本 |
| V3 | 餐厅区域匹配 | 3 | ⚙️ 脚本 |
| V6 | 户外天气敏感 | 3 | ⚙️ 脚本 |
| V10 | 价格溯源 | 3 | ⚙️ **脚本** | 补 price/fare + source |

完整规则见 `references/validation-rules.md`；分轮规范见 `references/iteration-rounds.md`。

### Step 4：确认餐饮（Round 3 已补则跳过）

> **v1.5.0**：餐厅调研已并入 **Round 3 体验筛**。若 Round 3 已补全 `meals[]`，Step 4 一句话确认即可，**不必重复**美团/高德/小红书调研。

若用户中途只改了 POI 没动餐厅，可只跑 `validate.py --round 3` 增量验证 V3。

**餐厅是补给点不是锚点** —— 只在预约餐、强目的餐、用户明确指定时允许反向推路线。

### Step 5：补票务 / 跨城交通

只查关键项：
- 官方票务（提前订清单写 deadline）
- 营业时间 / 休馆日
- 机场 ↔ 酒店 交通链
- 多城行程的跨城新干线 / 航班

**输出 `prebook` 列表**：每项含 URL + 截止日期。

**链接红线（v2.2.1）**：所有 `prebook[].url` 必须用**国内 OTA 深链**（`flights.ctrip.com` / `hotels.ctrip.com` / `trains.ctrip.com` / 官方站）。**禁止** `trip.com`（携程国际版）、`booking.com`、Agoda 首页或占位链。缺链写 `null`，模板会降级为国内携程搜索。导航链用 POI 坐标拼 `uri.amap.com`。详见 `references/planning.md` §7.1。

### Step 6：写参考文档（结构化输出）

按下面结构输出（**HTML 渲染前先输出这个 markdown**，让用户确认）：

```md
# {trip_name}

## 结论（先说结论）
{一句话总结这次旅行的取舍}

## 酒店
- {hotel_name}（{address}）—— {推荐理由 2 句}

## 每日行程
### Day 1 · {date} · {region}
- 15:00 {place} —— {why}
- 18:00 {restaurant} —— {why}

### Day 2 · {date} · {region}
...

## 每顿吃什么
- Day 1 晚餐：主推 {restaurant} / 备选 {restaurant}
...

## 天气敏感点
- {outdoor_place} —— 雨天/极端天气改 {indoor_backup}

## 提前订什么
- {item} —— 截止 {date}

## 删了什么 / 为什么删
- {item} —— {reason}

## 末日去机场
- {leave_hotel_time} → {transit} → {airport_checkin_time}
```

### Step 7：渲染 HTML + 部署到 GitHub Pages

> **目标**：返回一个手机能直接点开的公开 URL。
> 工作目录：`~/.travel-planner/travel-plans/`（本地工作副本，承载所有历史行程）
> 部署仓库：`SquirrelSong5/travel-plans`（公开）
> URL 形如：`https://squirrelsong5.github.io/travel-plans/{trip}.html`

#### 7.1 准备阶段（只跑一次）

```bash
# 1. 本地工作副本（若不存在）
mkdir -p ~/.travel-planner/travel-plans
cd ~/.travel-planner/travel-plans
git init && git checkout -b main 2>/dev/null
git remote add origin git@github.com:SquirrelSong5/travel-plans.git

# 2. 远端仓库（若不存在）
gh repo view SquirrelSong5/travel-plans 2>/dev/null || \
  gh repo create travel-plans --public --description "AI-generated travel plans"

# 3. 首次启用 Pages（一次即可，后续跳过）
gh api -X POST repos/SquirrelSong5/travel-plans/pages \
  -f source[branch]=main -f source[path]=/ 2>/dev/null || \
  echo "Pages 已启用或需手动在控制台点一下"
```

#### 7.2 每次行程的部署流程

```bash
# 1. 渲染 HTML（按 examples/{demo}.json 的 schema 填占位符）
# ⚠️ v2.0.5 安全：HTML 不内嵌 AMAP_WEB_KEY（防 git 泄露）
#    - 渲染时删除 tripData.amap_key 顶层字段
#    - template.html IIFE 从 URL ?k= / localStorage 注入 window.AMAP_KEY

# 2. 复制到工作副本
cp /tmp/{trip_name}-{date}.html ~/.travel-planner/travel-plans/{trip_name}-{date}.html

# 3. 提交 + 推送（HTML/JSON 里不得出现真实 Key）
cd ~/.travel-planner/travel-plans
git add {trip_name}-{date}.html {trip_name}-draft.json
git commit -m "trip: {trip_name} {date}"
git push -u origin main
```

#### 7.3 输出契约（聊天里给用户）

```
🌐 行程已上线：https://squirrelsong5.github.io/travel-plans/{trip_name}-{date}.html?k={AMAP_WEB_KEY}
📱 手机点带 ?k= 的链接直接看（含高德地图 / 每日行程 / 餐厅候选）
📄 Markdown 参考文档：[贴聊天]
🗂 本地副本：~/.travel-planner/travel-plans/{trip_name}-{date}.html

修改入口：直接说"Day 2 的 X 换成 Y"、"加一天京都" 等，AI 会重新渲染 + 重新部署。
```

**注意事项**：
- Pages 首次构建约 1 分钟，期间 URL 可能 404，提示用户稍等
- 公开仓库 = 任何拿到 URL 的人都能看行程（GitHub Pages 私有仓需 Pro）。Step 7 提醒用户
- 高德地图需要 Web (JS) Key 已配置 + 域名白名单已加 `squirrelsong5.github.io`（详见 `references/setup-guide.md` §4）
- **v2.0.5**：交付 URL 必须带 `?k=` 参数（Key 从 `~/.travel-planner/config` 读取，**不写入 HTML/git**）
- 不带 `?k=` 的公开 URL 仍可分享行程文字版；地图需带 Key 的 URL 或 localStorage 设置 `amap_web_key`
- 备选：若 `github.io` 手机端慢，可连 Vercel 自动部署（URL 形如 `travel-plans.vercel.app`，白名单同步加）

---

## 增量修改入口（任何时候支持）

用户后续对话说"改..."时，AI 走 **增量修改路径**，不重跑 7 步。

| 用户说 | 类型 | AI 动作 |
|--------|------|---------|
| "Day 2 的 X 换成 Y" | 单点替换 | 改这一项 → `validate.py --round 2`（+ 若餐厅则 `--round 3`）→ 更新 tripData → 重写 HTML 并重新部署 |
| "加一天京都" | 加日 | 插入新 day → Round 1→2→3 → 更新 tripData → 重写 HTML 并重新部署 |
| "取消 Day 3" | 删日 | 删 day → 重编号 → 更新 tripData → 重写 HTML 并重新部署 |
| "酒店换到 X" | 改锚点 | Round 1→2→3（V1/V3）→ 更新 tripData → 重写 HTML 并重新部署 |
| "Day 2 太赶了，分两天" | 节奏拆分 | 提议拆分 → 用户确认 → 新两日 Round 1→2→3 → 更新 tripData → 重写 HTML 并重新部署 |
| "重排 Day 1" | 单日重排 | 该 day Round 1→2→3 → 更新 tripData → 重写 HTML 并重新部署 |

**关键约束**：任何修改后必须跑受影响规则的验证。详见 `references/multi-turn-protocol.md` 第 5 节。

---

## 输出契约（v2.0.0 简洁版）

完成 Step 6 + Step 7 后，AI **只输出 4 项**：

1. **GitHub Pages URL（带 `?k=` 地图 Key）**（主交付物，手机/电脑点开即看完整地图）
2. **本地 HTML 副本路径**（`~/.travel-planner/travel-plans/{trip_name}-{date}.html`）
3. **Markdown 参考文档**（贴聊天，便于复制到笔记/分享）
4. **修改入口提示**（"想改任何地方直接说，比如：换 X、加一天、删一天"）

### 不输出的内容

- ❌ **验证报告 / banner / 检查过程**——HTML 模板默认隐藏 `validation-banner`（v2.0.0 起），用户只看方案不查验证
- ❌ **"针对你贴身定做" / "低精力毕业游" / "3 人（你 + 女朋友 + 闺蜜，刚毕业）"** 等套话——`summary` 字段保持简洁（一句话点题）
- ❌ **"以...为准" / "仅供参考" / "AI self-report"** 等元话语——输出只描述方案本身
- ❌ **重复的 emoji 警示**（🟡/🟢/🔴 等只在配置引导场景用，方案输出不放）

### 模板默认行为

- ✅ `template.html` 不渲染验证报告（`validate.py` 仅开发期用，不写入交付 HTML）
- ✅ Drawer（行程信息侧边栏）默认隐藏，悬浮在右侧不挤压中间内容
- ✅ Wrap `.wrap` 始终 `margin: 0 auto` 居中（drawer 开/关不影响）

---

## 不可妥协的硬规则

1. **先删后排**（明说删什么 + 为什么）
2. **一天一区 + 一日一重预约**
3. **首末日按航站楼和返程时间倒推**
4. **餐厅是补给不是锚点**
5. **四拍交互 + Smart skip**
6. **每轮迭代必须跑当轮验证**（`validate.py --round N`；交付前全量复检）
7. **增量修改必须重验证**（一致性不允许被改坏而不报警）

参考 `references/planning.md` 看完整方法论。

---

## 触发词（YAML description 之外的补充触发）

即使 YAML description 没匹配上，下列语义场景也应触发本 skill：

- 用户提到"高德/小红书/大众点评" + "行程/路线/规划" 中的任意组合
- 用户贴酒店截图 / 机票截图并说"帮我做行程"
- 用户说"上次做的 XX 行程" / "参考我之前的偏好"

---

## 详见

- `references/planning.md` — 7 步规划方法论 + 5 条硬规则 + 反模式表
- `references/multi-turn-protocol.md` — 四拍协议 + Smart skip + 增量修改 6 场景
- `references/validation-rules.md` — V1-V9 自动验证规则 + 按 Round 分组
- `references/iteration-rounds.md` — **v1.5.0** 三阶段分轮筛检规范
- `references/amap-mcp-usage.md` — 高德 MCP 工具调用模式
- `references/xhs-research.md` — 小红书两段式调研
- `references/dianping-research.md` — 餐厅调研方法（v1.2.0 重构：双轨零装 + 深度档）
- `references/meituan-guide-research.md` — 美团攻略 WebFetch 模式（v1.2.0 新增）
- `references/hotel-planning.md` — 酒店候选筛选
- `assets/template.html` — HTML 输出模板
- `examples/chengdu-3d.json` — 默认国内静态 demo（成都 3 日）
