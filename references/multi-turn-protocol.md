# 多轮对话协议

> 本文件定义 SKILL.md 主流程中所有与用户对话的标准格式。
> 核心是 **四拍格式 + Smart skip + 增量修改场景模板**。

---

## 0. AI 主导配置原则（v1.0 新增）

> **目标**：把所有"可自动化"步骤都让 AI 跑，用户**只在 4 个真人物理动作上介入**——其余一律 AI 干完。

### 0.1 能力分级

| 级别 | 描述 | 例子 |
|------|------|------|
| **🟢 AI 跑** | 无需用户，AI 直接执行（**按客户端走对应执行方式**：CC 用户用 `!cmd` 前缀 / Hermes-Cursor-Cloud Code-CodeBuddy AI 用 terminal 工具 / Codex AI 自己跑）| shell 命令、生成 URL、跑 MCP 验证、`chrome_launcher.py` 启 Chrome 装扩展 |
| **🟡 AI 跑 + 用户口供 1 个值** | 跑的过程中需要用户提供一次信息（验证码 / 设备码） | 高德注册短信、gh device flow |
| **🔴 必用户做** | 物理设备/真账号/系统操作限制，AI 做不了 | 手机 App 扫码、macOS Gatekeeper 弹窗「打开 Chrome」确认、Load unpacked（仅日常 Chrome 复用 session 场景）、**按客户端走对应"让 MCP 生效"操作**（CC 重开 / Hermes 自动 / Cursor Reload Window / Cloud Code 重开会话 / Trae-CodeBuddy 重启 IDE） |

### 0.2 4 个 MCP 的"AI 能/必用户"矩阵（v1.2.0 起大众点评降级为深度档，v1.4.0 起按客户端走）

> 假设用户已装 [Playwright MCP](https://github.com/microsoft/playwright-mcp)（**按客户端走对应命令**：CC `claude mcp add playwright npx @playwright/mcp@latest` / Hermes `hermes mcp install playwright` / Cursor 编辑 `~/.cursor/mcp.json` / Codex `codex mcp add playwright -- npx @playwright/mcp@latest` / Trae-CodeBuddy IDE 设置面板）。这是浏览器自动化的入口，没它 AI 只能跑 shell 步骤。
>
> **v1.2.0 起**：大众点评不在主轨矩阵里（降级为"深度档"，仅当用户明确要求时走 `references/setup-guide.md` §3 / `references/dianping-research.md` §6）。**美团攻略 WebFetch 零装零配**。
>
> **v1.4.0 起**：所有 shell / MCP 装命令 / 重启策略**按客户端走对应分支**——见 SKILL.md §客户端适配层。下表只列"AI 能 / 必用户"角色分配，**不限定客户端**。

| 步骤 | 高德 | 小红书 | **美团攻略** 🆕 | gh Pages |
|------|------|--------|---------|---------|
| 1. 创建账号 | 🟡 AI 走表单 / **🟡 用户收短信** | — | ❌ 无需账号 | 🟡 gh device flow / **🟡 用户去 github.com 贴码** |
| 2. 装 skill / 启 server | 🟢 AI 走完（**按客户端走对应 mcp add**）| 🟢 shell 装好（`git clone` + `uv sync`） | ❌ **零装** | 🟢 AI 跑 `gh repo create` |
| 3. 启 Chrome + **装扩展** | — | 🟢 AI 跑 `chrome_launcher.py`（**自动启 Chrome + 自动装 XHS Bridge 扩展**） | ❌ **零扩展** | — |
| 4. 拿凭据（Key/Token） | 🟢 AI 从页面提取 | — | ❌ **零凭据** | 🟢 AI 存 token |
| 5. 登录验证（**扫码**） | — | 🟢 AI 跑 `cdp_publish.py login` 开登录页 / **🔴 用户 App 扫** | ❌ **零登录** | — |
| 6. mcp add / 启服务 | 🟢 shell（**按客户端**）| — | ❌ **零服务** | — |
| 7. **让 MCP 生效** | **🔴 按客户端重启/Reload**（CC 重开 / Hermes 自动 / Cursor Reload Window / Codex 项目级自动 / Cloud Code 重开会话 / Trae-CodeBuddy 重启 IDE）| — | ❌ | — |
| 8. 验通 | 🟢 AI 调 `mcp__amap__*`（**跨客户端工具名一致**）| 🟢 shell 跑 `cli.py check-login` | 🟢 `WebFetch guide.meituan.com` | 🟢 `gh repo view` |

**所有 MCP 全装完，用户实际介入的动作**（**v1.2.0 从 5 个减到 3 个，v1.4.0 仍 3 个**）：
1. **收 1 条短信验证码**（高德注册）
2. **小红书 App 扫码 × 1**（autoclaw-cc skill，扫一次）
3. **去 github.com 贴 device code × 1**（部署用）
4. **按客户端让 MCP 生效**（Hermes / Codex 项目级自动加载不需要手动；CC / Cursor / Cloud Code / Trae / CodeBuddy 需要重启/Reload/重开会话）

**全装约 3-5 分钟**（其中真人动作 < 1 分钟）。**美团攻略是零配零装**——AI 直接 `WebFetch` 拿数据，零介入。

> **大众点评（深度档）仅当用户明确要求时走**——见 `references/setup-guide.md` §3 / `references/dianping-research.md` §6 / `references/multi-turn-protocol.md` 场景六·大众点评子流程。
>
> **跨客户端一致性（v1.4.0 重要说明）**：MCP tool 名字（如 `mcp__amap__maps_direction_walking`）和 tool 行为在 7 个客户端里**完全一致**——这是 MCP 协议的设计目标，AI 看自己工具列表实际加载的就行。**只有"装 MCP / 跑 shell / 重启"这 3 件事是客户端相关的**。

### 0.3 强制前置：未装 Playwright MCP 时的处理路径

> **🔒 强原则**：Playwright MCP 是 AI 主导配置的**唯一入口**。**AI 不得在自检后自作主张降级**——必须先走"推荐安装 → 等用户决定"流程。**只有用户显式说"降级 / 跳过 / 不用了"才能进半自动模式**。

#### 0.3.1 默认路径：未装时 AI 主动推装

```
🟢 AI: 启动 Step 0 自检…
      🔍 环境自检
      ├─ 🔒 Playwright MCP：未装 ← 阻断！
      ├─ ✅ 高德地图 MCP：已就绪
      ├─ ❌ 小红书：未配置
      └─ ⏭️ 美团攻略：零装零配（AI 直接 WebFetch）
      ⏭️ 大众点评深度档：默认不装（如要装需用户显式要求）

      ⚠️ Playwright MCP 没装。这意味着我没法开浏览器帮你配小红书。
      
      强烈推荐先装它（1 分钟），装完后面所有 MCP 我开浏览器帮你点。
      
      按客户端走对应命令（我先探测一下你用哪个客户端）：
      - CC: !claude mcp add playwright npx @playwright/mcp@latest
      - Hermes: hermes mcp install playwright（AI 跑）
      - Cursor: 编辑 ~/.cursor/mcp.json + Cmd+Shift+P Reload
      - Codex: codex mcp add playwright -- npx @playwright/mcp@latest
      - Cloud Code: 编辑 ~/.cloudshell_cloudsdk_mcp.json + 重开会话
      - Trae / CodeBuddy: IDE 设置面板加 + 重启 IDE
      
      装完按客户端走对应操作让 MCP 生效（CC 完全退出重开 / Hermes 下次启动自动 / Cursor Reload Window / Codex 项目级自动 / Cloud Code 重开会话 / Trae-CodeBuddy 重启 IDE）。
      
      完事告诉我「好了」，我重做自检。

      或者：
      A. 装（推荐，1 分钟换后面全自动化）
      B. 我明白降级影响，仍要降级 ← 你必须显式选这个
      C. 先用 demo 演示（看成都示例，不进入正式规划）
```

**AI 必须等用户回复再继续**，不得跳过这一步。

#### 0.3.2 三种回应的处理

| 用户选 | AI 动作 |
|--------|---------|
| **A. 装** | AI 按**§客户端适配层 探测到的客户端 X** 走对应分支：<br>• CC / Codex：跑对应 `mcp add` 命令 → 提醒用户按客户端重启（CC 完全退出 / Codex 项目级自动）<br>• Hermes：跑 `hermes mcp install playwright`（或 `hermes mcp add playwright -- npx @playwright/mcp@latest`）→ 不需要告诉用户重启<br>• Cursor / Cloud Code：编辑对应 JSON → 引导 Cmd+Shift+P Reload / 重开会话<br>• Trae / CodeBuddy：引导用户 IDE 内加 + 重启 IDE<br>→ 用户回「好了」→ AI 重做自检 → `mcp__playwright__*` 出现则进 Step 1，仍未出现则引导排查（场景八）|
| **B. 我明白降级影响，仍要降级** | AI 显式记录「用户主动降级（Playwright 未装）」到对话历史；进 §0.3.3 半自动模式 |
| **C. 先用 demo 演示** | 渲染 `examples/chengdu-3d.json` 演示，**不进入正式规划流程**；演示完再问一次要不要装 |

> **B 选项的措辞必须用户说出来**——"算了"、"不用了"、"太麻烦"、"不配了" 这些**都算显式降级**；**沉默 / 不回 / 继续提需求** ≠ 降级，AI 必须继续等或再次提示。

#### 0.3.3 进入场景六前的前置门（落地版）

> **🔒 这是 §0.3 在场景六的具体落地**。进入场景六 6.1 流程前，AI 必须先做这一步检查。

**AI 进入场景六前要做的事**：
1. 工具列表检查 `mcp__playwright__*` 是否存在
2. **不存在** → 跳到 §0.3.1 推装，**不进入 6.1**
3. **存在** → 继续 6.1

#### 0.3.4 半自动模式（仅用户显式选 B 后）

> **这是退路，不是默认**。一旦进入半自动，每个 shell 步骤 AI 自己跑；每个"开浏览器点页面"步骤 AI 给命令 + 用户手点。全程配置 15-20 分钟，比 AI 主导慢 3 倍。

具体执行见本文 §场景六·退路。

---

## 1. 四拍格式

所有决策提问遵循 **Re-ground → Simplify → Recommend → Options**，顺序不可换。

| 拍 | 作用 | 目的 |
|----|------|------|
| **Re-ground** | 告诉用户在哪个流程节点 | 防止用户迷失 |
| **Simplify** | 大白话讲问题 | 消术语 |
| **Recommend** | 给明确推荐 + 理由 | 降低决策成本 |
| **Options** | 2-4 个自解释选项 | 遮住描述也能选 |

### 1.1 四拍示例（首日餐厅）

> **Re-ground**：行程规划 Step 5（补吃饭），Day 1 银座区域。
>
> **Simplify**：Day 1 落地第一顿，挑近酒店、出餐稳、不排队的。
>
> **Recommend**：推荐 KABEAT —— 步行 5 分钟、24h 出餐、银座老牌。
>
> **Options**：
> - A. 落地型（推荐）
> - B. 打卡型（筑地外市场方向）
> - C. 我自己定

---

## 2. Smart skip 规则

| 场景 | 跳过什么 |
|------|----------|
| 用户主动说了日期 | 不再问"什么时候去" |
| 用户给了酒店名 + 地址 | 不再问"住哪里" |
| 用户列了想去点 | 不再问"想去哪里" |
| 用户给了人数 | 不再问"几个人" |
| 用户说"按你判断" | 不再追问细节，直接出方案 + 验证报告 |

---

## 3. 问题合并

无依赖的字段**一次性问完**，不要拆成多轮。

**正确**：
> "请一次性告诉我：日期、到达时间、酒店（或让我推荐）、想去点、不要去的类型。"

**错误**：
> 第一轮："日期呢？" → 第二轮："酒店呢？" → 第三轮："想去哪？"

---

## 4. 严格 will / is

| 情况 | 用词 |
|------|------|
| 未执行 | "计划"、"打算"、"建议" |
| 已完成 | "已经"、"完成" |
| 不确定 | "待定"、"看天气" |

**反例**：方案还没确认就说"已经订好了" → 信任崩塌。

---

## 5. 增量修改 6 场景（核心创新）

> 用户后续对话说"改..."时，AI 走这里的模板，**不重跑 7 步**。
> 每种修改类型有专属的处理流程 + 必跑的验证规则。

### 5.1 单点替换 —— "Day 2 的 X 换成 Y"

```
识别意图：明确说"Day N 的 A 换成 B"
处理流程：
  1. 在 day N 的 timeline 里把 A 改成 B
  2. 跑增量验证：
     - V1 区域一致性（B 是否还在 day N 主区域？）
     - V2 时间可行性（前后时间块和 B 衔接是否仍 OK？）
     - V3 餐厅区域匹配（如果 B 是餐厅）
  3. 更新 tripData（tripData 是单文件全量数据，任何修改都要重写）
  4. 重写整份 HTML 并重新部署到 GitHub Pages
  5. 输出："Day 2 的 X 已换成 Y，验证通过 / 有 1 个警告：... 新 URL: ..."
```

### 5.2 加日 —— "加一天京都"

```
识别意图：明确说"加一天" + 目的地/主题
处理流程：
  1. 询问插入位置（在 Day N 之前 / 之后 / 中间）
  2. 在选定位置插入新 day（M+1）
  3. 重跑该新 day 的完整 Step 3-7 + V1-V7
  4. 重排所有 day 编号（Day N → Day N+1）
  5. 更新 tripData → 重写 HTML → 重新部署
  6. 输出："已加 Day M+1 京都，旧 Day N 变成 Day N+1... 新 URL: ..."
```

### 5.3 删日 —— "取消 Day 3"

```
识别意图：明确说"取消 / 删掉 / 去掉 Day N"
处理流程：
  1. 确认是否真的想删（给出影响："删 Day 3 后 Day 2 的浅草会没地方休息"）
  2. 删除该 day
  3. 重排编号（Day N+1 → Day N+1-1）
  4. 更新 tripData → 重写 HTML → 重新部署
  5. 输出："Day 3 已删，原 Day 4-5 顺延... 新 URL: ..."
```

### 5.4 改锚点 —— "酒店换到 X"

```
识别意图：明确说"换酒店 / 住到 X"
处理流程：
  1. 高德 MCP 验证 X 的位置（`poi_detail`）
  2. 跑酒店通勤圈校验：
     - 计算 X 到每天主区域中心的距离
     - 任何一天通勤 > 30 分钟则告警
  3. 若有告警：
     - 选项 A：坚持新酒店 + 重排受影响 day
     - 选项 B：换回原酒店
     - 选项 C：加一晚分酒店
  4. 用户决策后执行
  5. 更新 tripData → 重写 HTML → 重新部署
```

### 5.5 节奏拆分 —— "Day 2 太赶了，分两天"

```
识别意图：用户反馈某 day 行程过载
处理流程：
  1. 分析过载点（POI 数量 / 总通勤时间 / 总停留时间）
  2. 自动提议拆分方案：
     - "Day 2 现在 8 个点 + 通勤 2.5h，建议拆成 Day 2A（浅草寺+仲见世）和 Day 2B（晴空塔+隅田川）"
  3. 用户确认拆分边界（"X 留 Day 2，Y 挪到 Day 2B"）
  4. 跑完整 7 步 + V1-V7
  5. 更新 tripData → 重写 HTML → 重新部署
```

### 5.6 单日重排 —— "重排 Day 1"

```
识别意图：明确说"重排 Day N"
处理流程：
  1. 只重跑该 day 的 Step 3-7 + V1-V7
  2. 其他 day 不动
  3. 更新 tripData → 重写 HTML → 重新部署
  4. 输出："Day N 已重排，验证通过 / 有 X 个警告：... 新 URL: ..."
```

> **重要**：HTML 是 `window.tripData` 内联 + JS 全量渲染的单文件，**任何修改本质都得重写整个 HTML 并重新部署**，不存在"局部重渲 Day N"的实现。这与术语上的"重渲"不矛盾——是产物整体重写。

---

## 6. 增量修改的反模式

| 反模式 | 后果 |
|--------|------|
| 修改后不跑验证 | 改坏一致性（如改了酒店不联动改 day 通勤圈） |
| 修改后重跑完整 7 步 | 浪费 token + 容易把好的部分也改了 |
| 不告诉用户影响就改 | 用户失去信任 |
| 修改后不重渲 HTML | 输出和视图不一致 |

---

## 7. 典型四拍场景库

### 场景一：信息不足
> **Re-ground**：行程规划 Step 1
> **Simplify**：先搞清楚才能排
> **Recommend**：先给日期和酒店
>
> Q1 出信息方式：A) 截图 / B) 打字
> Q2 节奏：A) 两人标准 / B) 老人小孩 / C) 独自

### 场景二：删点确认
> 4 天塞 12 点需砍 → 推荐砍远郊（黄金周挤、天数短）
>
> A) 按推荐砍 / B) 保留远郊砍别的 / C) 看完整清单再定

### 场景三：餐厅风格
> 首日推荐"落地型"（KABEAT 之类：近酒店、出餐稳、不排队）
>
> A) 落地型（推荐）/ B) 打卡型 / C) 用户自定

### 场景四：迭代确认（出方案后）
> A) 没问题生成 HTML / B) 微调 / C) 推翻重来

### 场景五：增量修改触发
> 用户说"Day 2 的浅草寺换成上野公园"
>
> **Re-ground**：增量修改 → 单点替换
> **Simplify**：换一天的一个点
> **Recommend**：直接改
> 1. 替换
> 2. 跑 V1/V2 验证
> 3. 重渲 Day 2

### 场景六：首次使用 / MCP 配置引导（v1.0 AI 主导版）

> 自检结果：amap/xiaohongshu/dianping 都缺（或部分缺）。
> **前提**：用户已装 [Playwright MCP](https://github.com/microsoft/playwright-mcp)（**按客户端走对应命令**，详见 §客户端适配层 / §0.3.1）。**如未装，先走 §0.3.3 前置门**。
> 完整能力分级见本文 §0。

**Re-ground**："travel-planner Step 0，环境自检。我先帮你把缺的数据源装好，整个过程 5 分钟，中间你只介入 2-3 次（短信验证码 + 扫码 + 重启）。"

**Simplify**："我开浏览器走完所有表单，你只需要收短信、扫一次码、重启一次 Claude Code。"

**Recommend**："我直接开干，先装高德。"

**Options**：
- A. 我开浏览器帮你装（5 分钟，🟢🟡 标注你的介入点）
- B. 先用 demo 演示（看成都示例，先不装）
- C. 我自己看 `references/setup-guide.md` 装

---

**选 A 后的对话节奏**（AI 用 Playwright + shell 主导，每段只让用户做一件事）：

> **⚠️ 以下对话是"意图示意"，不是 AI 必须照抄的剧本**：
> - `[tool: mcp__playwright__browser_navigate ...]` 这种**写法是给读者看的**（让你知道 AI 在做什么），AI 在真实环境里**不会这样写报告**——它**直接调**自己工具列表里**实际存在**的那个 tool
> - **tool 名以你环境里实际加载的为准**（**按客户端走对应 mcp list 命令探**：CC `claude mcp list` / Hermes `hermes mcp list` / Cursor 看 `~/.cursor/mcp.json` / Codex `codex mcp list`）：本文示例用的 `browser_navigate/click/type/snapshot` 是 `@playwright/mcp` 当前版本的常见名，**不同版本/不同 MCP 实现可能不一样**（如有的版本叫 `navigate` 不带 `browser_` 前缀）
> - **要做的动作（导航、点击、填文字）** 才是关键——**怎么写 tool 名是动态的**

```
🟢 AI: 我先看 Playwright MCP 在不在…
     [tool: mcp__playwright__browser_navigate https://lbs.amap.com/]   ← AI 实际调的是它工具列表里那个 navigate tool
     [tool: mcp__playwright__browser_click "注册按钮"]
     [tool: mcp__playwright__browser_type "手机号输入框" "13800138000"]

🟡 AI: 表单填到一半，平台发短信验证码到你手机了。
     请告诉我收到的 6 位验证码。

用户: 482931

🟢 AI: [tool: mcp__playwright__browser_type "验证码输入框" "482931"]
     [tool: mcp__playwright__browser_click "注册完成"]
     ✅ 账号注册完成。
     现在创应用拿 Key…
     [tool: mcp__playwright__browser_navigate https://lbs.amap.com/dev/key/app]
     [tool: mcp__playwright__browser_click "创建新应用"]
     [tool: mcp__playwright__browser_type "应用名" "travel-planner"]
     [tool: mcp__playwright__browser_click "添加 Key → 选 Web 服务"]
     [tool: mcp__playwright__browser_snapshot]  ← 拿 Key 字符串
     🔑 你的 Key: 7d8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c
     （我已自动复制到下一步）

🟢 AI: 配到客户端（**按客户端走对应命令**）…
     [CC] [shell: claude mcp add --transport http amap "https://mcp.amap.com/mcp?key=7d8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c"]
     [Hermes] [shell: hermes mcp add amap --transport http --url "https://mcp.amap.com/mcp?key=7d8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c"]
     [Cursor] [编辑 ~/.cursor/mcp.json 加 amap 条目]
     [Codex] [shell: codex mcp add amap --url "https://mcp.amap.com/mcp?key=7d8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c"]
     [Cloud Code] [编辑 ~/.cloudshell_cloudsdk_mcp.json]
     [Trae / CodeBuddy] [引导用户 IDE 设置面板加]
     [shell: <按客户端走 mcp list 命令>]
     ✅ MCP 已注册。

🔴 AI: 接下来需要你做一件事（**按客户端走对应操作**让 MCP 生效）：
     • CC / Cursor / Cloud Code / Trae / CodeBuddy：必须重启/Reload/重开会话
       - CC: 完全退出 CC 窗口，重新打开（启动时加载 MCP，没法热加载）
       - Cursor: Cmd+Shift+P → Reload Window
       - Cloud Code: 重开会话
       - Trae / CodeBuddy: 重启 IDE
     • Hermes / Codex 项目级 config：下次启动自动加载，**不需要任何操作**
     完事告诉我「好了」。

用户: 好了

🟢 AI: 验通…
     [tool: mcp__amap__geocode "成都东站"]
     ✅ 高德通了，开始下一步：装小红书。
```

---

**小红书（Python skill，v1.0.3 起 `chrome_launcher.py` 主导装扩展）**：

> **关键洞察**：**`autoclaw-cc/xiaohongshu-skills` 项目自带 `scripts/chrome_launcher.py`——它能自动启 Chrome + 自动装 XHS Bridge 扩展 + 开 9222 调试端口**。别的 AI 让人手装是因为它们没看到这个 launcher。**本 skill 让 AI 跑这一行就完事**。

```
🟢 AI: 我先 clone 仓库装依赖…
     [shell: git clone https://github.com/autoclaw-cc/xiaohongshu-skills.git ~/xhs-skill]
     [shell: cd ~/xhs-skill && uv sync]
     ✅ 代码就绪。

🟢 AI: 启 Chrome + 自动装 XHS Bridge 扩展…
     [shell: cd ~/xhs-skill && python scripts/chrome_launcher.py]
     ✅ Chrome 起来了，扩展 XHS Bridge 也装上了（隔离 profile，端口 9222）。

🟡 AI: macOS 可能会弹「是否允许打开 Chrome」对话框——点「打开」即可。
     （一次性 Gatekeeper 确认，之后不会再问）

🟢 AI: 打开小红书登录页…
     [shell: cd ~/xhs-skill && python scripts/cdp_publish.py login]
     ✅ 二维码已弹出。

🔴 AI: 请用小红书 App 扫这个二维码。
     （同一账号不要在别的网页端登录，否则会被踢出）
     扫完告诉我「扫了」。

用户: 扫了

🟢 AI: [shell: cd ~/xhs-skill && python scripts/cli.py check-login]
     ✅ 已登录。
```

---

**大众点评（v1.2.0 起**默认不推荐装**，深度档仅在用户明确要求时走）**：

> 💡 **v1.2.0 默认不装大众点评**——主轨用"**高德 POI + 美团攻略 WebFetch + 小红书**"零装三件套（参见 `references/dianping-research.md` / `meituan-guide-research.md`）。
>
> **什么情况下才装**：
> - 用户明确说"必须大众点评必吃榜 + 评价数 + 排队实况"
> - 或主轨方案拿不定主意需要大众点评评价数排序
>
> 🚫 **不要用 Playwright 跑大众点评**：`verify.meituan.com` 识别 Headless Chrome 指纹，playwright 跑被谜题页挡住，stealth 插件也救不了。

**主轨（默认，零装）**：

```
🟢 AI: 餐厅调研我先用主轨方案做：零装，零扫码。
     主轨 = 高德 POI 详情（坐标/营业/评分）+ 美团攻略 WebFetch（编辑清单）+ 小红书（软信号）。
     
     [WebFetch: https://guide.meituan.com/chengdu/canyin]
     → 拿到编辑推荐清单（火锅品类 8 家）
     [mcp__amap__maps_text_search × 8 家 → maps_search_detail]
     → 拿坐标/营业/类型 → 算 V3
     [python ~/xhs-skill/scripts/cli.py search-feeds --keyword "<店名> 排队 避雷"]
     → 拿软信号
     ✅ 候选 3-5 家。
     
     详细流程见 references/dianping-research.md §3。
```

**深度档（仅当用户明确要求时走）**：

```
🔴 AI: 餐厅硬信号深度档需要装 OpenCLI + Browser Bridge Chrome 扩展 + 扫码登录大众点评。
     装的话需要 5 分钟 + Chrome 常开 + 同电脑维护。
     你确定要走深度档？（要必吃榜 + 评价数 + 排队实况？）

用户: 走深度档

🟢 AI: 装 OpenCLI npm 包…
     [shell: npm install -g @jackwener/opencli]
     [shell: opencli doctor]
     ⚠️ 报 "Extension not connected" —— 正常，下一步装扩展。

🔴 AI: 现在需要你做一件事：装 Browser Bridge 扩展（opencli 没有它就连不进 Chrome）。
     推荐方式 — 1 分钟搞定：
     
     1. 打开 https://chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk
     2. 点「添加至 Chrome」→ 弹窗确认
     
     装好告诉我「扩展装了」。

用户: 扩展装了

🟢 AI: 验证扩展连通…
     [shell: opencli doctor]
     ✅ "Extension connected" — 通了。

🔴 AI: 第二步：用大众点评 App 扫 Chrome 里的登录二维码。
     （不需要专门启隔离 Chrome，opencli 直接连你日常的 Chrome，复用已登录 session）
     1. Chrome 打开 https://www.dianping.com
     2. 用大众点评 App 扫登录二维码
     3. 扫完告诉我「扫了」

用户: 扫了

🟢 AI: [shell: opencli dianping search "火锅" --city 成都 --limit 3 -f json]
     ✅ 通了。
```

---

**GitHub Pages 部署（`gh` CLI）**：

```
🟢 AI: 装 gh CLI（如未装）…
     [shell: which gh || brew install gh]
     [shell: gh auth login --web --git-protocol https]  ← 出现 device code

🟡 AI: 请复制这个 8 位 code，去 https://github.com/login/device 粘贴，授权后回到这里。

用户: 授权好了

🟢 AI: [shell: gh auth status] 确认已登录。
     建仓并 push HTML…
     [shell: gh repo create SquirrelSong5/travel-plans --public --source=. --remote=upstream --push]
     [shell: gh repo edit --enable-pages --pages-source main --pages-path /]
     [shell: git push upstream main]
     ✅ 部署完成，URL: https://squirrelsong5.github.io/travel-plans/chengdu-3d.html
```

---

**关键规则（v1.0）**：
- 每段开头标注 🟢🟡🔴 让用户秒懂谁做
- 🟡 步骤后 AI 显式停手等用户回复，**不连续调用工具**
- 🔴 步骤后 AI 解释为什么必须用户做（"系统限制" / "物理设备" / "安全验证"）
- 不堆 5 步；每段结束等用户"好了 / 扫了 / 收到 X" 再继续
- 命令直接给可复制的（代码块），不绕弯
- 关键节点用 emoji 视觉锚定（🟢 AI / 🟡 用户口供 / 🔴 用户动手 / ✅ 通 / ⚠️ 警告 / ❌ 失败）

---

### 场景六·退路：用户显式降级后

> **🔒 这只是退路，不是默认**。仅当用户在 §0.3 推装流程中**显式选 B**「我明白降级影响，仍要降级」时进入。

```
AI: 收到，你显式选了降级。后面 shell 步骤我跑，浏览器步骤给你命令手点。
    全程约 15-20 分钟，比 AI 主导慢 3 倍，但能用。
    
    —— 接下来半自动流程 ——
    
    1. 装高德：先去 https://lbs.amap.com/ 注册（手机号 + 短信）
       完成后告诉我「高德注册好了」。
    
    2. 我来跑 `mcp add` 配高德 MCP（你给我 Key 字符串即可；**按客户端走对应命令**：CC `claude mcp add` / Hermes `hermes mcp add` / Cursor 编辑 `~/.cursor/mcp.json` / Codex `codex mcp add` / Cloud Code 编辑 JSON / Trae-CodeBuddy IDE 操作）
    
    3. **按客户端让 MCP 生效**（CC 完全退出 / Hermes 下次启动自动 / Cursor Reload Window / Cloud Code 重开会话 / Codex 项目级自动 / Trae-CodeBuddy 重启 IDE）
    
    ...（其他 MCP 同样节奏）
    
    —— 或者 ——
    
    看了下发现你真的只要 demo 演示，那就先跳过 MCP 配
    A. 进入半自动流程（15-20 分钟）
    B. 还是先用 demo 演示
    C. 反悔了，去装 Playwright（推荐）
```

### 场景七：demo 演示路径（拒绝配置的用户）

> 用户说"先不用配 / 用 demo 演示"

```
AI: OK，先用成都 3 日示例给你看效果。
    [渲染 examples/chengdu-3d.json]
    [输出 HTML 路径]
    
    这是没配 MCP 时也能达到的效果 —— 基于示例数据。
    实际规划你的行程时，POI / 路线 / 距离 / 天气这些数据来自高德 MCP，
    没有的话就只能用通用知识，方案会更粗糙。
    
    看完效果后告诉我：
    A. 效果 OK，去配 MCP（5 分钟）
    B. 还要继续用 demo 改改看
```

### 场景七·三阶段分轮验证对话（v1.5.0）

> **核心**：Step 3 分 **Round 1 结构 / Round 2 时空 / Round 3 体验**，每轮 `validate.py --round N` + AI critique；**不能跳过**。

```
🟢 AI: Round 1 · 结构筛 完成。
     删了：九眼桥酒吧街（用户禁忌：无夜场）
     [shell: python scripts/validate.py /tmp/chengdu.json --round 1 --pretty]
     ✅ V1/V4 通过；V7 已自检禁忌
     → 写入 validation_report.rounds[0]，conclusion：进入 Round 2

🟢 AI: Round 2 · 时空筛。
     [tool: mcp__amap__maps_direction_walking ...] × N 段
     [shell: python scripts/validate.py /tmp/chengdu.json --round 2 --pretty]
     ✅ V2/V5/V8/V9 通过
     → rounds[1]：高德实算 Day 3 早上最紧，仍可行

🟢 AI: Round 3 · 体验筛。
     [WebFetch: guide.meituan.com/chengdu/canyin]
     [tool: mcp__amap__maps_search_detail ...]
     [shell: python ~/xhs-skill/scripts/cli.py search-feeds --keyword "蜀大侠 排队"]
     [shell: python scripts/validate.py /tmp/chengdu.json --round 3 --pretty]
     ✅ V3/V6 通过
     → rounds[2]：餐厅三源已留痕

🟢 AI: 最终全量复检：
     [shell: python scripts/validate.py /tmp/chengdu.json --pretty]
     合并 rules → 部署 GitHub Pages
     https://squirrelsong5.github.io/travel-plans/chengdu-3d.html

用户: （点开 HTML）底部能看到 Round 1/2/3 三阶段报告
```

**关键点**：
- 每轮只跑**当轮规则子集**（见 `iteration-rounds.md`）
- `validation_report.rounds[]` 保留三阶段历史 + critique
- 浏览器仍强制重算 V1/V3/V4/V5/V6；V2 看 AI 高德报告；V7 Round 1 必查

### 场景八：配置失败排查

> 用户反馈"配好了但还是报错"

**Re-ground**："配置有问题，我帮你排查。"

**Simplify**："MCP 这玩意儿就是一堆配置，常见就那几个坑。"

**排查清单**（按概率从高到低）：
1. **没让 MCP 生效**（**按客户端走对应操作**：CC 完全退出再开 / Hermes 下次启动自动 / Cursor Reload Window / Codex 项目级自动 / Cloud Code 重开会话 / Trae-CodeBuddy 重启 IDE）→ 让用户按客户端走对应操作
2. Key 填错（漏字符 / 多字符 / 中英文标点）→ 让用户重新复制
3. 平台类型选错（选了 JS API 而非 Web 服务）→ 让用户去控制台看 Key 类型
4. 配置文件格式错误（之前手编辑坏过）→ **按客户端走对应 mcp list 命令**（CC `claude mcp list` / Hermes `hermes mcp list` / Cursor 看 `~/.cursor/mcp.json` / Codex `codex mcp list` / 其他看 IDE 设置）看报错
5. Chrome / 网络代理问题（高德 MCP 走 https）→ 让用户直接访问 https://mcp.amap.com 测试

---

## 8. 严禁清单

| 严禁 | 替代 |
|------|------|
| 列选项无推荐 | 给推荐 + 理由 |
| 让用户打字（当可选项已涵盖时） | 给 A/B/C |
| 已说还问 | Smart skip |
| 未执行说已完成 | 严格 will/is |
| 修改不跑验证 | 增量修改后必跑 V1-V7 受影响项 |
| 修改不重渲 HTML | 重渲并告知文件路径 |
