# travel-planner

[![Validate](https://github.com/SquirrelSong5/travel-planner-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/SquirrelSong5/travel-planner-skill/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.4.0-blue.svg)](CHANGELOG.md)

> Claude Code / Hermes / Cursor / Codex / Cloud Code / Trae / CodeBuddy 全局 Skill ——
> 通过 **高德地图 MCP + 小红书 skill + 美团攻略 WebFetch** 三件套，
> **零装零扫码**生成含酒店、每日行程、餐厅候选的单文件 HTML 旅行方案。
> 大众点评 OpenCLI 降级为"深度档"（必吃榜 + 评价数才用）。
> 支持 **v1.5.0 三阶段分轮筛检**（Round1 结构 → Round2 时空 → Round3 体验）+ 增量修改。

## 安装

```bash
# 方式 1：作为 Claude Code / Hermes 等的全局 skill（推荐）
git clone https://github.com/SquirrelSong5/travel-planner-skill.git \
  ~/.claude/skills/travel-planner

# 方式 2：放进项目目录（项目级 skill，仅当前项目生效）
git clone https://github.com/SquirrelSong5/travel-planner-skill.git \
  .claude/skills/travel-planner
```

仓库地址：<https://github.com/SquirrelSong5/travel-planner-skill>


## 🔴 硬约束：唯一交付物 = HTML 部署到 GitHub Pages 的 URL

> **v1.5.0 起明确写入**：
>
> **本 skill 的**唯一**交付物是【单文件 HTML 部署到 GitHub Pages 后返回的公开 URL】**。
> **不允许 AI 给 PDF / Word / Markdown / 长图 / 任何其他形态**作为"输出"。
>
> - ❌ **不允许**："给你生成了 PDF" / "给你导出了 Word" / "Markdown 方案" / "长图方案"
> - ❌ **不允许**："Cmd+P 打印为 PDF" / "用浏览器打印"——**这是用户的**后续操作**，不是 AI 的输出**
> - ✅ **必须**：`gh repo create` + `gh repo push` + 返回 `https://USERNAME.github.io/REPO/`
> - ✅ **必须**：手机 / 电脑打开 URL 直接看（响应式 HTML）
>
> 用户的"手机访问"= 部署到 GitHub Pages 拿 URL，**不是 PDF**。

---

## 🚀 5 分钟快速开始（小白专用）

> 零基础？按这 3 步走，5 分钟跑起来。

### Step 1：触发 skill

直接对 Claude Code 说一句话：

```
帮我做个东京 4 泊 5 日行程
```

skill 会自动加载，并检测你的环境。

### Step 2：跟着引导装高德 MCP（5 分钟）

如果 AI 检测到没装高德 MCP，会自动给出详细步骤。**核心就两条命令**：

```bash
# 1. 注册 + 拿 Key（去 https://lbs.amap.com/ 注册账号，创建应用拿 API Key）

# 2. 配到 Claude Code（替换 YOUR_KEY）
claude mcp add --transport http amap "https://mcp.amap.com/mcp?key=YOUR_KEY"
```

然后**完全退出 Claude Code 重新打开**。

### Step 3：开始规划

新会话里说"做个 XX 行程"即可，AI 会：
1. 自检环境（告诉你哪些 MCP 装好了）
2. 问几个关键信息（日期 / 酒店 / 想去点）
3. 跑 **三阶段分轮筛检**（Round 1 结构 → Round 2 时空 → Round 3 体验 + `validate.py --round`）
4. 输出 HTML 方案 + 可选渲染地图

### 不想配 MCP 也能用？

可以！第一次用时选"先用 demo 演示"，AI 会渲染内置的 Tokyo 4 泊 5 日示例给你看效果。
但要做自己的行程还是建议配高德 —— 没配的话方案会很粗糙。

---

## 这是什么

一个 Claude Code 全局 Skill。**输入**：你的旅行需求（目的地、日期、人数、偏好）。
**输出**：单文件 HTML 行程方案 + 多轮对话里的方案迭代。

### 和参考项目 trip-map-builder 的区别

| 维度 | trip-map-builder | travel-planner（本 skill） |
|------|------------------|---------------------------|
| 数据获取 | OpenCLI + Chrome CDP | **MCP + WebFetch 优先**（高德 / 小红书 / 美团攻略） |
| 地图 | Leaflet 交互地图 | **高德 JS API 内嵌** + Tab 切换 |
| 规划轮次 | 单轮 | **3 阶段分轮筛检**（结构→时空→体验，每轮不同规则子集） |
| 增量修改 | 不支持 | **6 种修改场景模板** |
| 酒店规划 | 仅当硬约束 | **独立推荐流程** |
| 餐厅调研 | OpenCLI | **v1.2.0**：高德 POI + 美团攻略 + 小红书（零装） / opencli 降级为深度档 |

---

## 安装

### 方式一：直接克隆（最简单）

```bash
git clone <repo-url> ~/.claude/skills/travel-planner
# 或者直接复制本目录到 ~/.claude/skills/travel-planner/
```

### 方式二：手动

把本目录复制到 `~/.claude/skills/travel-planner/`，目录结构如下：

```
~/.claude/skills/travel-planner/
├── SKILL.md
├── README.md
├── CHANGELOG.md
├── references/
├── assets/
└── examples/
```

**无需重启 Claude Code**，下次触发时自动加载。

---

## 配置数据源

### 高德地图 MCP（必需）+ 高德 Web API Key（可选但强烈推荐，用于 HTML 地图渲染）

高德有 **两套不同的 API**，需要分别配置（同一个 lbs.amap.com 账号）：

#### 1. 高德地图 MCP（AI 在规划时调用）

这是让 AI 在生成方案时能实时查询 POI / 路线 / 天气 / 距离的 MCP server。

**Step 1**：注册账号
- 访问 https://lbs.amap.com/ 注册开发者账号（免费）

**Step 2**：创建应用 + 拿 Key
- 控制台 → 应用管理 → 我的应用 → 创建新应用
- 应用名称随意（如 `travel-planner-mcp`）
- 服务平台选 **「Web 服务」**（不是 JS API）
- 创建后系统生成一个 API Key，复制备用

**Step 3**：配置 Claude Code MCP
- 找到 Claude Code 的 MCP 配置文件（通常是 `~/.claude.json` 或 `.mcp.json`）
- 添加：

```json
{
  "mcpServers": {
    "amap": {
      "url": "https://mcp.amap.com/mcp?key=YOUR_AMAP_KEY"
    }
  }
}
```

或者用 Node.js 方式：

```json
{
  "mcpServers": {
    "amap": {
      "command": "npx",
      "args": ["-y", "@amap/amap-maps-mcp-server"],
      "env": { "AMAP_MAPS_API_KEY": "YOUR_AMAP_KEY" }
    }
  }
}
```

**Step 4**：重启 Claude Code
- 重启后输入 "高德地图" 之类的话，AI 应该能用 `mcp__amap__*` 工具查询

> 没配高德 MCP？skill 会降级为通用知识，仍可出方案，但路线 / 距离 / POI / 天气数据会缺失。

#### 2. 高德 Web (JS) API Key（最终 HTML 渲染地图）

这是给**浏览器**用的 Key，跟上面的 MCP Key 是两个独立的 Key（虽然同一个账号下）。

**Step 1**：创建应用 + 拿 Key
- 同一个 lbs.amap.com 账号
- 控制台 → 我的应用 → 创建新应用（如 `travel-planner-html`）
- 服务平台选 **「Web 端 (JS API)」**（注意：是 JS API，不是 Web 服务）
- 创建后复制 Key

**Step 2**：填到 HTML 里
- AI 生成的 HTML 里有 `window.AMAP_KEY = "";` 一行
- 把你的 Web JS Key 填进去：`window.AMAP_KEY = "你的Key";`

**Step 3**：配置域名白名单（重要！）
- 控制台 → 我的应用 → 找到刚创建的应用 → 设置
- 域名白名单：
  - 本地测试：`localhost` / `127.0.0.1` 或留空
  - GitHub Pages：`yourname.github.io`
  - 自定义域名：你部署的域名
- 不配白名单会报 `INVALID_USER_KEY` 或 `USER_DAILY_QUERY_OVER_LIMIT`

**没配 Web JS Key 会怎样？**
- HTML 仍能打开，但地图区域显示"未配置高德 Web API Key"降级提示
- 其他功能（Tab 切换、文字版行程、餐厅推荐、抽屉等）全部正常

#### 3. 高德 Key 配额

- 免费版每天 **5000-10000 次** 调用（个人开发者）
- 本 skill 单次行程大约用 50-200 次
- 个人使用完全够

---

### 小红书（推荐）

> **v1.0.2 起唯一方案**：`autoclaw-cc/xiaohongshu-skills`（Python CLI + Chrome 扩展）。
> 原 `xpzouying/xiaohongshu-mcp` 方案已弃用（部署太重，本 skill 只需要搜索/详情）。

| 用途 | 接入方式 |
|------|---------|
| `python ~/xhs-skill/scripts/cli.py <subcommand> [args]` | `git clone https://github.com/autoclaw-cc/xiaohongshu-skills.git ~/xhs-skill && cd ~/xhs-skill && uv sync` + 装 Chrome 扩展 |

详见 `references/setup-guide.md` §2 / `references/xhs-research.md` §1.2 工具映射表。

> 不装也行，skill 降级为 WebFetch 小红书 M 站。

### 大众点评（**v1.2.0 起深度档，非必需**）

> ⚠️ 大众点评**无官方 MCP**。v1.2.0 起**默认不推荐装**——反爬严（`_token` 签名 + 行为指纹 + 滑块），所有 Playwright / WebFetch 直抓方案都必败。
>
> **主轨方案（v1.2.0 推荐，零装）**：
> - **高德 POI 详情**（`mcp__amap__maps_search_detail`）—— 坐标 / 营业 / 评分 / 人均 / 类型
> - **美团攻略 WebFetch**（`guide.meituan.com/<city>/canyin`）—— 编辑过的好店清单
> - **小红书**（`autoclaw-cc` skill）—— 排队 / 避雷 / 氛围
>
> 详见 `references/dianping-research.md`（已重构）/ `references/meituan-guide-research.md`（新增）。

**深度档（仅当用户明确要必吃榜 + 评价数 + 排队实况才装）**：

```bash
npm install -g @jackwener/opencli
# + 装 Browser Bridge Chrome 扩展 + 登录大众点评（详见 references/dianping-research.md §6）
```

按 `references/dianping-research.md` §6 指引启动 Chrome 远程调试 + 登录。

---

## 使用

### 触发词

中文：`规划旅行` / `做个行程` / `旅行规划` / `帮我做旅行方案` / `旅游规划`
英文：`plan my trip` / `trip itinerary` / `travel plan` / `vacation planning`

或同时提到 `高德` + `小红书` + `大众点评`（或 `美团攻略` / `美团`）中两个以上 + `行程` 相关词。

### 典型流程

1. 你说："做个东京 5 日行程，我和老婆两人，预算 1.5 万"
2. AI 加载本 skill，**Step 0 自动检测 MCP 状态**（首次会引导安装）
3. AI 一次性问完硬约束（日期 / 酒店 / 想去点 / 禁忌）
4. AI 跑三阶段分轮筛检 + `validate.py --round` + 最终全量验证
5. AI 输出 markdown 参考文档 + 渲染 HTML 文件
6. 你说"Day 2 的 X 换成 Y"，AI 走增量修改

详细流程见 [`SKILL.md`](./SKILL.md)。

### 想跳过 MCP 配置直接体验？

告诉 AI "先用 demo 演示"，它会渲染内置的 Tokyo 示例给你看效果，之后再决定要不要配。

---

## 目录结构

```
travel-planner/
├── SKILL.md                          # 入口：YAML frontmatter + 7 步主流程
├── README.md                         # 本文件
├── CHANGELOG.md                      # 版本历史
├── references/
│   ├── planning.md                   # 7 步规划方法论 + 5 条硬规则
│   ├── multi-turn-protocol.md        # 四拍交互 + 增量修改 6 场景
│   ├── validation-rules.md           # V1-V9 自动验证 + 按 Round 分组
│   ├── iteration-rounds.md         # v1.5.0 三阶段分轮筛检规范
│   ├── amap-mcp-usage.md             # 高德 MCP 工具调用模式
│   ├── xhs-research.md               # 小红书两段式调研
│   ├── dianping-research.md          # 餐厅调研方法（v1.2.0 重构：双轨零装 + 深度档）
│   ├── meituan-guide-research.md     # 美团攻略 WebFetch 模式（v1.2.0 新增）
│   ├── hotel-planning.md             # 酒店候选筛选
│   └── setup-guide.md                # MCP 安装配置 step-by-step
├── assets/
│   └── template.html                 # 单文件 HTML 模板（卡片化 + 移动端适配）
├── scripts/
│   └── validate.py                   # V1-V9 硬约束验证（--round 1|2|3）
└── examples/
    ├── chengdu-3d.json               # 国内静态 demo（成都 3 日，默认）
    ├── tokyo-4n5d.json               # 境外参考 demo（东京 5 日）
    └── README.md                     # schema 文档
```

---

## 核心特性

### ✅ 交互式地图 + Tab 切换

- HTML 内嵌高德地图，显示每天 POI 标记 + 交通路线
- 顶部 Tab 切换 Day 1 / Day 2 / ...，地图同步更新
- 交通方式用不同颜色区分：🟢 步行 / 🔵 地铁公交JR / 🔴 驾车 / 🟠 骑行
- 缺地图 Key 时降级为"按 Tab 切换文字版行程"

### ✅ 三阶段分轮筛检（v1.5.0）

每阶段筛**不同维度**，不是同一套规则重复三遍：

| Round | 焦点 | 规则 |
|-------|------|------|
| 1 结构筛 | 删点、分组、禁忌 | V1, V4, V7 |
| 2 时空筛 | 高德实算、路线、末日缓冲 | V2, V5, V8, V9 |
| 3 体验筛 | 餐厅三源、户外备选 | V3, V6 |

```bash
python scripts/validate.py trip.json --round 1   # 结构
python scripts/validate.py trip.json --round 2   # 时空
python scripts/validate.py trip.json --round 3   # 体验
python scripts/validate.py trip.json --pretty  # 交付前全量
```

详见 `references/iteration-rounds.md`。最多 3 Round，超出请用户决策。

### ✅ 增量修改（不重跑全部）

用户后续对话说"改..."时，AI 按 6 种场景走模板：

- 单点替换 / 加日 / 删日 / 改酒店锚点 / 节奏拆分 / 单日重排

详见 `references/multi-turn-protocol.md` 第 5 节。

### ✅ 数据源降级

每个数据源都有降级路径：

| 数据源 | 缺失时降级 |
|--------|-----------|
| 高德 MCP | 提示申请 Key；或用通用知识 |
| 小红书 | WebFetch 小红书 M 站 |
| **美团攻略 WebFetch** 🆕 | 高德 `text_search` 按菜系搜（候选池 100+，多花 10 分钟做 V3 过滤）|
| 大众点评（深度档）| 主轨方案（高德 POI + 美团攻略 + 小红书）已够用，**不需要装** |

降级不是失败 —— 仍能出方案，只是数据质量降低。

---

## 开发 / 自定义

### 修改模板

直接编辑 `assets/template.html`。它是纯 CSS + 极简 HTML，无依赖。

### 添加示例

把新 JSON 放到 `examples/` 下，参考 `tokyo-4n5d.json` 格式。

### 调整验证规则

编辑 `references/validation-rules.md`。AI 每轮规划后会读它。

---

## 常见问题

### Q：高德 MCP 申请 Key 要钱吗？
A：高德开放平台有免费版，每天 5000-10000 次调用限额，本 skill 一般只会用几十次 / 天，足够。Web (JS) API Key 同账号下也可以申请免费版。

### Q：地图不显示怎么办？
A：检查 3 件事：
1. `window.AMAP_KEY` 是否填了有效的 Key
2. Key 是否为「Web 端 (JS API)」类型（不是 MCP 类型）
3. 浏览器 Console 有无报错（如域名白名单 / Key 失效）

也可以保持 Key 为空，HTML 会自动降级为"按 Tab 切换文字版行程"。

### Q：3 轮迭代够吗？
A：90% 的行程 2 轮内收敛。第 3 轮还不通过就说明冲突严重，需要用户决策（如放弃远郊 / 多加一天）。

### Q：HTML 怎么分享？
A：**默认走 GitHub Pages 部署**（v1.0 加的 Step 7），AI 跑 `gh repo create` + `gh repo push` 后返回公开 URL（`https://USERNAME.github.io/REPO/`），手机 / 电脑浏览器直接打开。
如不想走 GitHub Pages，备选：发 HTML 文件给朋友（手机直接打开），或上传到任意静态托管（Netlify / Vercel）。

### Q：能改主题色吗？
A：能。修改 `assets/template.html` 里的 CSS 变量（`:root { --accent: ... }`）即可。

---

## 许可

MIT。参考项目 trip-map-builder（https://github.com/hiyeshu/trip-map-builder）的部分方法论移植自该项目，遵循原项目 MIT 协议。
