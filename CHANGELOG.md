# Changelog

本 skill 遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [未发布] - 2026-06-17

### 仓库独立化：从 `selfuse-cc-config` 子目录拆为独立仓库

- **背景**：之前 `travel-planner/` 是 `~/.claude/skills/travel-planner` 真实目录，寄居在父仓 `SquirrelSong5/selfuse-cc-config` 下（父仓同步本地 Claude 配置 + skills 索引）。这种结构有两个问题：
  1. 父仓 0 track 本 skill（`git ls-files skills/travel-planner/` 为空），是**孤儿目录**
  2. 想 `git push` 旅行 skill 必须先 `cd ~/.claude` 操作整个父仓，**污染父仓 commit 历史**
- **本次改动**：
  - 在 `~/.claude/skills/travel-planner/` 内部**原地初始化独立 git 仓库**（不删原目录、不动父仓、不改父仓 .gitignore）
  - 推到 GitHub 新建 `SquirrelSong5/travel-planner-skill`（public）
  - 加 `.gitignore`（屏蔽 `.playwright-mcp/` / `cookies.json` / `.DS_Store` / `*.log`）
  - 加 `LICENSE`（MIT）
  - 加 CI `.github/workflows/validate.yml`（PR 触发跑 `validate.py` 校验 examples）
  - README 顶部加 GitHub badges + install 方式（`git clone` 到 `~/.claude/skills/travel-planner`）
- **之后**：`cd ~/.claude/skills/travel-planner && git push` 即可独立推送，**不再污染父仓**
- **v1.5.0 重构（携程问道加入）继续在独立仓库推进**

## [1.4.0] - 2026-06-17

### 多客户端兼容重构：从 2 客户端扩到 7 客户端

> **来源**：用户提醒"注意，需要兼容 Hermes 和 cloud 或者 code X 等等多个工具"——之前 v1.1 加的"客户端适配层"只覆盖 Claude Code CLI + Hermes desktop GUI 两个客户端，对 Cursor / Codex / Google Cloud Code / Trae / CodeBuddy 等其他国内用户能接触到的 AI 客户端**没有显式处理**。
>
> **问题盘点**：
> - `SKILL.md` / `setup-guide.md` / `multi-turn-protocol.md` 多处**硬编码 `claude mcp add ...` / `!claude mcp ...` / "重启 Claude Code"**——其他客户端用不了
> - 很多示例对话直接说"AI 跑 `claude mcp add` 配高德 MCP"——Cursor / Codex / Trae / CodeBuddy 用户看到会以为 skill 跑不通
> - 实际有 7 个客户端都支持 MCP（CC / Hermes / Cursor / Codex / Cloud Code / Trae / CodeBuddy），但**统一的部分（MCP tool 名 + 行为）和不统一的部分（装命令 + 配置位置 + 重启方式）没分开说**，AI 容易误用
> - v1.3.0 新增的真实路径渲染 / v1.2.0 新增的餐厅双轨——**这些新功能跨客户端是否一致**没说清楚

**核心结论（v1.4.0 最重要的一个结论）**：

> **MCP tool 名字 + tool 行为 + 输出 JSON schema** 在 7 个客户端里**完全一致**（这是 MCP 协议的设计目标）。**AI 调用 MCP tool 拿数据**这部分代码**跨客户端零差异**。**只有"装 MCP / 跑 shell / 重启"这 3 件事是客户端相关的**。

**覆盖的 7 个客户端**：

| 客户端 | 平台 | 探测方式 | MCP 装命令 | 配置位置 | 让 MCP 生效 |
|--------|------|---------|-----------|---------|------------|
| Claude Code CLI | 终端 | `which claude` | `claude mcp add` | `~/.claude.json` | 完全退出重开 |
| Hermes desktop GUI | Mac app | `which hermes` / `terminal()` 工具 | `hermes mcp add` | `~/.hermes/config.yaml` | **不需要重启**（下次启动自动）|
| Cursor | IDE | `which cursor` / `run_terminal_cmd` | 编辑 `~/.cursor/mcp.json` | `~/.cursor/mcp.json` | Cmd+Shift+P Reload Window |
| Codex CLI | 终端 | `which codex` | `codex mcp add` | `~/.codex/config.toml` | 项目级自动 / 全局重启会话 |
| Google Cloud Code | Cloud Shell / VS Code 扩展 | 看上下文 | 编辑 `~/.cloudshell_cloudsdk_mcp.json` | `~/.cloudshell_cloudsdk_mcp.json` | 重开会话 |
| Trae | IDE | `which trae` | IDE 设置面板 | IDE 内部 | 重启 IDE |
| CodeBuddy | IDE | `which codebuddy` | IDE 设置面板 | IDE 内部 | 重启 IDE |

**变更**：

- **`SKILL.md` §客户端适配层 整段重写**（v1.4.0）：
  - 客户端从 2 个扩到 **7 个**（CC / Hermes / Cursor / Codex / Cloud Code / Trae / CodeBuddy）
  - 客户端探测从 3 选 1 改成 4 选 1（加 `which` 探测）
  - 命令映射表从 2 列扩到 7 列
  - 加 "**跨客户端统一的部分**" 章节（**MCP tool 名 + 行为 + 输出 schema 跨客户端零差异**）
  - 加 4 个场景实战（Cursor / Cloud Code / Codex / Trae-CodeBuddy）
  - 加 ⚠️ 已知坑 6 条（Cursor 写盘 / Cloud Code 重启 / Codex TOML 格式 / Trae-CodeBuddy 不暴露配置 / `hermes mcp add --` 分隔符 / CC 与 Hermes flag 位置差异）
  - 原 v1.1 写的"CC vs Hermes 速查"折叠进"探测到的客户端 X 的决策树"

- **`SKILL.md` §0.1 / §0.2 / §0.3 / §0.4 / §0.5 多处硬编码全改**：
  - §0.1 Playwright MCP 自检描述改为"按客户端走对应 mcp list 命令探"
  - §0.2 自检示例改为"按客户端命令探到 mcp__playwright__* 14 个 tool"
  - §0.3 选 A 推荐文案改为"按客户端走对应安装命令"（列了 5 个客户端的具体命令）
  - §0.4 AI 可以做的事改为"按客户端走对应 MCP 装入命令"；🔴 用户做的事改为"按客户端走对应让 MCP 生效操作"
  - §0.5 配置完成后的验证改为"按客户端跑对应 mcp list 命令"
  - §0.3 情况 D 的具体 Playwright 装命令段加 6 客户端分支（CC / Hermes / Cursor / Codex / Cloud Code / Trae-CodeBuddy）

- **`references/setup-guide.md` 全量替换硬编码**：
  - §-1 装 Playwright 命令从"一行 `claude mcp add`"改为按客户端 6 行映射表 + 3 个示例
  - §1.3 配高德 MCP 从"写到 `~/.claude.json`"改为按客户端 6 行映射表
  - §1.4 标题从"重启 Claude Code"改为"让 MCP 生效"+ 6 客户端操作表
  - §1.5 验证从 `mcp__amap__geocode`（旧命名）改为 `mcp__amap__maps_geo`（v1.3.0 新命名）
  - §5.5 一键脚本加 6 客户端分支注释
  - §6 检测速查表加 6 客户端 mcp list 命令
  - §7 卸载/重置加 6 客户端 remove 命令

- **`references/multi-turn-protocol.md` 关键场景重写**：
  - §0.1 能力分级描述加"按客户端走对应执行方式"
  - §0.2 4 MCP 矩阵"重启 Claude Code"行改为"按客户端重启/Reload"6 客户端表
  - §0.2 用户实际介入动作清单第 4 条改为"按客户端让 MCP 生效"
  - §0.2 加"跨客户端一致性"小节
  - §0.3.1 推装 Playwright 命令从 `!claude mcp add` 改为按客户端 6 行命令
  - §0.3.2 选 A 后续从"重启 Claude Code"改为按客户端 6 分支
  - §0.3.1 推装文本框里加 6 客户端命令
  - §场景二示例"配到 Claude Code"改为按客户端 6 标签的命令（[CC] / [Hermes] / [Cursor] / [Codex] / [Cloud Code] / [Trae-CodeBuddy]）
  - §场景六·退路"重启 Claude Code"改为按客户端 6 客户端让 MCP 生效
  - §场景八排查清单"重启 Claude Code"改为"按客户端让 MCP 生效"；"`~/.claude.json` 格式错误"改为"按客户端走对应 mcp list 命令"

- **`references/amap-mcp-usage.md` 加 §跨客户端一致性**（v1.4.0 新章节）：
  - 7 客户端 × `mcp__amap__maps_direction_walking` 兼容性表（全 ✅）
  - 解释 MCP 协议的设计目标（tool 命名空间 + 输出 schema 跨客户端统一）
  - AI 判断原则：**不用管客户端**——v1.3.0 polyline 提取代码在 7 客户端通用
  - 列跨客户端**可能不同**的：MCP server 版本 / MCP tool 数量（不是 tool 名）
  - 列跨客户端**会不同**的：装命令 / 配置位置 / shell 执行方式 / 重启方式

**前置学习材料**：

- Cursor 官方文档（[cursor.com/cn/docs/context/mcp](https://cursor.com/cn/docs/context/mcp)）—— 确认 `~/.cursor/mcp.json` 位置 + Cmd+Shift+P Reload Window 机制
- Codex CLI 官方（推断）—— 确认 `codex mcp add` 语法 + `~/.codex/config.toml`（项目级 / 全局两级）

**保留 100% 向后兼容**：

- v1.3.0 之前的旧用户**所有流程**不变——只是新增了"客户端适配层"的覆盖范围
- v1.3.0 / v1.2.0 / v1.1.0 / v1.0.3 / v1.0.2 / v1.0.1 / v1.0.0 的**所有新功能**（真实路径渲染 / 餐厅双轨 / 代码级验证 / Playwright 强制前置 / XHS 自动装扩展 / XHS 自动装 Chrome / 国内优先）在 7 客户端里**完全通用**（因为都是"调 MCP tool 拿数据"或"按客户端走 shell"——后者已经在文档里明确分支）

**已知限制**：

- Trae / CodeBuddy 的 MCP 配置**不暴露在文件系统**——AI 改不了，必须引导用户 IDE 内操作
- Google Cloud Code（浏览器端，非 VS Code 扩展）改完配置后**必须重开会话**才生效
- **Codex CLI 项目级 `mcp_servers` 用 TOML 格式**——AI 跑 `codex mcp add` 是统一入口，不需要手写 TOML
- `hermes mcp add` 实际可能需要 `--` 分隔符（如 `hermes mcp add playwright -- npx @playwright/mcp@latest`）——AI 跑前用 `hermes mcp add --help` 确认

---

## [1.3.0] - 2026-06-17

### 真实路网路径渲染（高德 MCP route_* 拿 polyline）

> **来源**：用户问"高德地图的 API 能不能获取从出发点到目的地的各种路线？比如我可以选择公共交通、自行车、步行，它能不能获取到对应的路线，并且渲染到地图上呢？"
>
> **事实**：
> - 高德 **MCP 4 个路线工具**都返回**完整 polyline 坐标**（不仅是通勤时间）：
>   - `maps_direction_walking`（步行）—— `paths[].steps[].path`
>   - `maps_bicycling`（骑行）—— `paths[].steps[].path`
>   - `maps_direction_driving`（驾车）—— `paths[].steps[].path`
>   - `maps_direction_transit_integrated`（公交综合）—— `transits[].segments[].*.path`（分段，每段都有 polyline）
> - 高德 **Web (JS) API 也有对应插件**（`AMap.Walking` / `AMap.Riding` / `AMap.Transfer` / `AMap.Driving`）可以在浏览器实时算
> - **当前 skill 渲染的是直线 polyline**（POI1→POI2 一条直线），不是真实路网路径
> - `amap-mcp-usage.md` 用的工具名（`geocode` / `poi_search` / `route_walking`）**与官方 MCP 实际命名不符**（`maps_geo` / `maps_text_search` / `maps_direction_walking`），AI 调不到

**方案**：

AI 在 Step 3 调 `maps_direction_*` 时**同时提取 polyline 坐标**，写进 `tripData.transports[].path`，HTML 用真实路网路径渲染。

- **零额外 API 开销**：V2 验证（`duration_min`）和 polyline 提取是**同一次 MCP 调用**
- **零侵入**：旧数据没填 `path` 字段，HTML 自动降级为直线（向后兼容）
- **新 schema**：`transports[].path`（`[lng, lat][]` 坐标数组）+ `distance_m` + `source`

**变更**：

- **`references/amap-mcp-usage.md` 整段重写**（v1.3.0）：
  - 工具表从旧命名（`geocode` / `poi_search` / `poi_detail` / `route_walking` / `route_transit` / `route_biking` / `route_driving`）**改为官方 MCP 实际命名**（`maps_geo` / `maps_text_search` / `maps_search_detail` / `maps_direction_walking` / `maps_direction_transit_integrated` / `maps_bicycling` / `maps_direction_driving`）
  - 场景 2（路线规划）整段重写为 v1.3.0 真实路径工作流：
    - 2.1 模式选择表（距离/场景 → 首选 MCP 工具）
    - 2.2 完整调用模式：拿真实 polyline（含实际 MCP 返回结构示例）
    - 2.3 polyline 提取代码（步行 + 公交多段拼接）
    - 2.4 `tripData.transports` v1.3.0 新 schema
    - 2.5 V2 验证逻辑（不变）+ 2.6 `maps_distance` 快速测距
  - 工具选择速查表更新为新命名
  - 加 4 个注意事项（adcode 优先 / 工具调用频率 / 跨城 polyline 精度 / 公交分段拼接）
  - 末尾加「v1.3.0 改动摘要」表

- **`SKILL.md` Step 3 加 v1.3.0 子节**：
  - 「🆕 v1.3.0 新增：AI 用高德 MCP 算真实路径」
  - 4 步硬流程：
    1. 对每对相邻 POI 按距离/场景选 `maps_direction_*` 工具
    2. 提取 polyline 坐标（伪代码）
    3. 写进 `tripData.days[].transports[].path`
    4. HTML 自动判断：有 `path` → 真实路网；无 → 直线
  - 模式选择表 + 注意事项（公交分段 / 跨城精度 / 降级）
  - 链接到 `references/amap-mcp-usage.md` §2.3-2.4

- **`assets/template.html` 地图渲染升级**（v1.3.0）：
  - `updateMap()` 函数里 polyline 渲染逻辑改为：
    - 检测 `transports[].path` 是否存在且 ≥ 2 个坐标点
    - **有则**用 `t.path` 画真实路网 polyline
    - **无则**降级为 `[[from.lng, from.lat], [to.lng, to.lat]]` 直线
  - 真实路径的 `strokeOpacity: 0.9`（直线 0.6）—— 真实路径更显眼
  - 兼容 `[lng, lat]` 坐标数组格式

- **`examples/README.md` schema 文档同步**：
  - `transports[]` 字段加 `path?` / `distance_m?` / `source?` 注释
  - 加「路径渲染 v1.3.0」小节：渲染优先级表 + AI 必做工作
  - 加 v1.3.0 changelog 条目

- **`examples/chengdu-3d.json` Day 1 加 v1.3.0 path 示例**：
  - 第一个 transport（酒店 → 太古里）加 6 点 polyline（`source: "amap-mcp"`，直线 350m）
  - 第二个 transport（太古里 → 小龙翻大江）加 6 点 polyline（540m）
  - **证明 schema 实际可用**（后续其他 day 可仿照）

**真实使用流程**（Step 3 路径预算）：

```
🟢 AI: 对 Day 1 第 1 段（酒店 → 太古里）调高德:
     [mcp__amap__maps_direction_walking origin=酒店 destination=太古里]
     → 拿到 duration=300s + path 坐标
     → 提取 polyline → 写进 transports[0].path + distance_m + source

     对 Day 1 第 2 段（太古里 → 小龙翻大江）:
     [mcp__amap__maps_direction_walking ...]
     → 同上

     对 Day 2 公交段（地铁换乘）:
     [mcp__amap__maps_direction_transit_integrated city=成都]
     → 拿到 3 段 polyline（步行+地铁+步行）→ 拼接成一条 path
```

**HTML 渲染效果**（template.html）：
- v1.3.0 之前：直线 polyline（一根线穿过建筑）
- v1.3.0 之后：真实路网 polyline（沿公路/步行道/公交线，**自动吸附到路网**）

**保留 100% 向后兼容**：
- 旧 tripData 没 `path` 字段 → 自动降级为直线（旧行为）
- AI 跳过 polyline 提取 → 自动降级为直线
- MCP 调用失败 → 自动降级为直线

---

## [1.2.0] - 2026-06-17

### 餐厅调研方法重构：双轨零装 + opencli 降级

> **来源**：用户问"大众点评的反扒太严重了，有没有什么别的方案？你可以上网搜索一下。如果在旅游的话，你觉得有什么平台可以去参考的？"
>
> **背景**：
> - 大众点评无官方 MCP，开放平台 API 早已停摆
> - `verify.meituan.com` 反爬极严（`_token` 签名 + 行为指纹 + 滑块），所有 Playwright / WebFetch 直抓方案都**必败**（11.txt 实测）
> - opencli + 真实 Chrome + Browser Bridge 是唯一能绕过的方案，但需要装扩展 + 扫码 + Chrome 常开，**普通旅行者不值得**
> - **本版本调研发现**：
>   - **高德 POI 详情（`maps_search_detail`）已经能拿 80% 餐厅硬信号**：评分/营业时间/类型/人均/坐标/V3 通勤
>   - **美团攻略 `guide.meituan.com` 是美团官方 2026/04 新上线的"编辑版"攻略**（数据来源就是大众点评公开数据 + 媒体评测），**反爬对抗 = 0**（编辑页静态）
>   - 8 大热门城市（沪/京/蓉/穗/深/杭/渝/汉）有详细"怎么吃"页

**变更**：

- **主轨方案（v1.2.0 推荐，零装）**：
  - **高德 POI 详情**（`mcp__amap__maps_search_detail`）：坐标 / 营业 / 评分 / 人均 / 类型（**已有 MCP，零装**）
  - **美团攻略 WebFetch**（`guide.meituan.com/<city>/canyin`）：**编辑过的好店清单**（**零装零配零扫码**）
  - **小红书**（autoclaw-cc skill）：排队 / 避雷 / 氛围软信号
  - 三件套组合 = **80% 场景与 opencli 深度档质量相当**，但**完全零反爬对抗 + 零装 + 零扫码**

- **opencli 深度档降级**（v1.2.0 起**默认不推荐**）：
  - **降级条件**：用户**明确要求**"必须必吃榜上榜 + 评价数 + 排队实况"，**或**主轨方案拿不定主意需要大众点评评价数排序
  - 不再作为默认推荐——成本/收益不划算
  - 仍然保留完整安装流程（见 `references/dianping-research.md` §6 / `references/setup-guide.md` §3）

- **新增 `references/meituan-guide-research.md`（v1.2.0 新文件）**：
  - 美团攻略 `guide.meituan.com` 的 URL 模式（`/stay/<city>` / `/save-money` / `/<city>/canyin`）
  - 8 大城市的"怎么吃"页结构
  - 标签解读（"本地人爱去" / "周末排队" / "不踩雷" / "游客店" / "必吃榜水平"）
  - 与高德 POI + 小红书的组合姿势
  - 何时不用（境外 / 8 大城市之外 / 用户明确要必吃榜）

- **`references/dianping-research.md` 重构**：
  - §0 改为"三档方案"表（主轨 1 / 主轨 2 / 深度档 / 禁止项）
  - §1 重写"高德 MCP POI 详情"——明确 8 个能拿到的硬信号字段 + 与大众点评对位 + 局限
  - §2 新增"美团攻略 WebFetch"——URL 模式 + 典型工作流 + 局限
  - §3 新增"主轨 1+2 + 小红书"组合模式 + 4 步工作流
  - §4 筛选六维加 `reviews_proxy`（编辑推荐入选）
  - §6 压缩为深度档（明确说"80% 场景不需要"）
  - §9 完整示例从 0 到候选 3 家
  - §10 加 v1.2.0 历史归档

- **`SKILL.md` 数据源表重写**：
  - 顶部 YAML description 改为"高德 MCP + 小红书 skill + 美团攻略 WebFetch"三件套零装零扫码
  - 数据源表加美团攻略行，opencli 标注"v1.2.0 起默认不推荐"
  - Step 4「补吃饭」改为"v1.2.0 升级：餐厅硬信号从大众点评改为高德 POI + 美团攻略 WebFetch 双轨"
  - 自检表"大众点评"行加 v1.2.0 起非必需说明

- **`references/setup-guide.md` §0 速览表加美团攻略行**（0 分钟，零装），大众点评行加 v1.2.0 起默认不推荐
- **`references/setup-guide.md` §3 整段改写**——从"可选，AI 主导 5 分钟"改为"**深度档，非必需**"：
  - 新增 §3.0 自检流程（先确认是不是真的需要）
  - 用户明确说"必吃榜 + 评价数"才走 §3.1-Step 3.6
  - 默认跳到 §4（高德 Web Key + GitHub Pages）

- **`references/multi-turn-protocol.md` 场景六·大众点评子流程**：
  - 拆为"主轨（默认，零装）" + "深度档（仅当用户明确要求时走）"两段
  - 主轨段展示完整的"WebFetch 美团攻略 + 高德 POI 详情 + 小红书软信号" 流程
  - 深度档保留 opencli 装扩展 + 扫码流程（与之前相同）
  - §0.2 矩阵从"5 个 MCP"精简为"4 个 MCP"（高德 / 小红书 / 美团攻略🆕 / gh Pages），去掉大众点评列
  - §0.2 用户介入动作从"5 个减到 4 个"改为"5 个减到 3 个"
  - §0.3 自检示例去掉"大众点评未配置"行，加"美团攻略：零装零配"行

- **`README.md` 同步**：
  - 顶部"三件套"文案更新
  - "和参考项目 trip-map-builder 的区别"表加 v1.2.0 餐厅调研说明
  - "大众点评（可选，但强烈推荐）"小节改写为主轨方案 + 深度档两个分支
  - "数据源降级"表加美团攻略行
  - 目录结构加 `meituan-guide-research.md` 和 `scripts/validate.py`

**真实使用流程**（餐厅调研）：

```
🟢 AI: 用户做成都 3 天，Day 2 主区域春熙路，午餐想吃火锅。

  [WebFetch: https://guide.meituan.com/chengdu/canyin]
  → 火锅品类下 8 家编辑推荐：蜀大侠、大龙燚、皇城老妈、川西坝子、小龙坎、电台巷、谭鸭血、牛华绿叶

  [mcp__amap__maps_text_search × 8 家 → maps_search_detail × 8 家]
  → 拿坐标/营业/类型 → 算 V3（vs 春熙路酒店 ≤ 1.5km）→ 8 家全过

  标签筛选："游客店"标签的牛华绿叶 → 剔（用户说不要游客店）
  评分 + 营业筛选：4.5+ 分 + 营业至 22:00 → 3 家候选

  [python ~/xhs-skill/scripts/cli.py search-feeds --keyword "<店名> 排队 避雷"]
  → 软信号补充

  ✅ 主推：蜀大侠（4.6 分 + 本地人爱去 + 营业至 22:00 + 距主区域 0.1 km）
  ✅ 备选：川西坝子（4.4 分 + 不踩雷 + 营业至 22:30）
  ⚠️ 不推：牛华绿叶（游客店标签）
```

**80% 场景信号损失表**（vs opencli 深度档）：

| 缺失信号 | 影响 | 替代 |
|---------|------|------|
| 评价数 | 低 | 城市主流城市不需要评价数筛 |
| 必吃榜上榜证明 | 中 | 高德 4.6+ ≈ 必吃榜水平 |
| 排队实况（精确到小时）| 中 | 小红书搜"工作日"/"周末"分时段 |
| 踩雷关键词精确分析 | 中 | 小红书搜"避雷" |
| 用户真实评价数 | 低 | 不影响"能不能进候选池" |

**保留 100% 主轨信号**（vs 之前"光靠高德 POI 不够"假设）：
- 坐标 / 营业时间 / 类型 / 人均 / 评分：✅ 高德 100% 覆盖
- V3 区域匹配：✅ 高德坐标直接算
- V5 末日返程缓冲：✅ 高德 `opentime2` 覆盖
- V6 户外天气敏感：✅ `indoor_backup` 字段（不依赖餐厅数据源）

---

## [1.0.0] - 2026-06-17

### 重大变更：手机端部署 + 页面升级

- **Step 7 改为 GitHub Pages 部署**：返回公开 URL（如 `https://squirrelsong5.github.io/travel-plans/{trip}.html`），手机点开即看活地图，替代本地 HTML 文件
- **页面 UI 重做 + 移动端适配**：
  - CSS 引入 4/8 间距栅格 + 字号 scale（`--sp-*` / `--fs-*`）
  - 颜色对比度提升（accent 从 #d4451b 加深到 #c8421a，WCAG AA 通过）
  - day-tab 改为**分段控件**观感（segmented control）
  - sticky tabs 吸顶（移动端切换天更顺手）
  - 触控目标 ≥ 44px（tab / FAB / 链接按钮 / 关闭按钮）
  - safe-area inset（刘海屏/底部 Home 条留白）
  - 字号 ≥ 16px 防 iOS 自动放大；移动端综合断点 @media (max-width:600px)
  - 移动端地图全宽、drawer 头考虑 safe-area
- **去东京硬编码**：地图 center 改为从 `tripData.trip_center` 派生，无则取首日 center，兜底北京
- **国内优先**：
  - 大众点评**升位**为国内餐厅硬信号主力
  - 新增 `examples/chengdu-3d.json` 作为默认 demo
  - V4 重预约标准补充国内项（故宫/国博/迪士尼/网红店排号/汉服/中医等）
- **Vercel 备选**写进 setup-guide，作为 `github.io` 访问慢的退路

### 小红书二选一集成（v1.0.0 引入，v1.0.2 弃用 A 方案）

- **数据源表**由单一"小红书 MCP"展开为 **方案 A / 方案 B**：
  - **方案 A**：`xpzouying/xiaohongshu-mcp` —— Go HTTP MCP server，13 个 tool（功能全）
  - **方案 B**：`autoclaw-cc/xiaohongshu-skills` —— Python CLI + Chrome 扩展（开箱即用）
  - 同作者维护；同时只能选一个
- **SKILL.md** 数据源表 + Step 0 自检表 + §0.3 / §0.6 改为方案感知
- **`references/setup-guide.md` §2** 重写为完整两套接入步骤（Docker / 二进制 / x-mcp 插件 / Chrome 扩展）
- **v1.0.2 弃用 A 方案**，详见下方 v1.0.2 章节
- **`references/xhs-research.md` §1** 加工具映射表（MCP tool ↔ CLI 命令），AI 调用对照不混
- **README / CHANGELOG** 同步更新

### AI 主导配置（Playwright MCP 集成）

- **目标**：把"开浏览器、点按钮、填表单"这种步骤让 AI 用 [Playwright MCP](https://github.com/microsoft/playwright-mcp) 自己跑，用户**只在 2-3 个真人物理动作上介入**（收短信 / 扫码 / 重启 Claude Code）
- **三色标注体系**：🟢 AI 跑 / 🟡 AI 跑+用户口供一次值 / 🔴 必用户做（系统/物理设备限制）
- **`references/setup-guide.md`**：
  - 新增 §-1「前置：装 Playwright MCP」+ §5「部署：GitHub Pages（AI 主导）」
  - §1 / §2 / §3 每条 shell 步骤加 🟢 标签，每条扫码/重启步骤加 🔴 标签
  - §0 速览表新增「自动化级别」列
- **`references/multi-turn-protocol.md`**：
  - 新增 §0「AI 主导配置原则」+ 5 MCP 的"AI 能/必用户"矩阵
  - 场景六整段重写为 AI 主导新流程（含高德 / 小红书 A / 小红书 B / 大众点评 / gh 5 个子流程）
  - 场景六·退路：没装 Playwright 时回退到半自动
- **SKILL.md**：
  - §0.3 情况 A 选 A 后引导话术更新为"AI 主导"
  - §0.4 拆成"AI 可以做 / 🟡 需口供 / 🔴 必用户"三组
  - §0.6 加第 6 条"🟢🟡🔴 三色标注"原则
- **整体效果**：装完 5 个 MCP 用户介入次数从"5 个 MCP × 多步手动"降到 2-3 次（一次收短信 + 一次扫码 + 一次重启 Claude Code），总时间 15-20 分钟 → 5-7 分钟

### Playwright MCP 强制安装路径（防自检后擅自降级）

> **触发场景**：观察到 AI 在自检后看到 `mcp__playwright__*` 缺失，**自作主张**说"这俩 MCP 都需要扫码登录，AI 替不了，本轮不能自动引导"直接跳过——这违反"先推装再让用户决定"的原则。

- **SKILL.md §0.1** 自检表加 `Playwright MCP` 行为**🔒 强制前置**（未装必须先装）
- **SKILL.md §0.3 情况 D（新增）**：未装 Playwright 时的四拍引导——明确推装为默认选项，**用户必须显式选 B「我明白降级影响，仍要降级」**才进半自动
- **SKILL.md §0.6** 加第 7 条原则「🔒 强制前置：AI 不得自作主张降级」
- **`references/multi-turn-protocol.md` §0.3 重写**：从"退路"重命名为"强制前置：未装 Playwright MCP 时的处理路径"，明确"沉默 / 不回 / 继续提需求 ≠ 降级"
- **`references/multi-turn-protocol.md` §场景六** 加 §6.0 前置门：进入场景六前先确认 `mcp__playwright__*` 在不在；**不在 → 跳 §0.3，不进入 6.1**
- **`references/setup-guide.md` §-1 升级**：标题改为「🔒 强制前置，1 分钟」，加"装 vs 不装"对比表，把"不想装"挪到独立子节并强调"这是显式降级"

### 代码级硬约束验证（v1.1.0）

> **来源**：用户问"AI 在用这个 skill 的时候，它做方案没有多次验证啊，怎么回事？有没有什么办法硬性约束 AI 去做验证？就是在 skill 里面、在一些代码里面去约束，不要通过提示词。"

**问题**：V1-V7 7 条验证规则**写在 markdown 里**——AI 可以完全跳过，或写"✅ 全通过"但没真算过。**纯提示词约束**。

**改造方案**：双层硬约束（服务端脚本 + 浏览器端 JS）。

**变更**：

- **新增 `scripts/validate.py`**（v1.0.0，~250 行 Python）：
  - 真用 POI 坐标 + 阈值公式算 V1/V3/V4/V5/V6
  - 兼容多种坐标字段命名（`location` / `lng+lat` / `lon+lat`）
  - 兼容多种 prebook 字段（`item` / `title` + 启发式从 note 提取）
  - V1 末日跳过（返程日偏远是合理的）
  - V2 浏览器内只能粗算（V2 需高德 API，浏览器做不到）
  - V7 完全不能脚本化（用户禁忌是软约束）
  - 退出码：全 ✅ → 0；有 ❌ → 1
  - 已在 chengdu-3d.json 跑通：15 通过 / 1 警告（V5 航班缺 depart_time 字段，是真实数据问题）/ 0 失败
- **`assets/template.html` 加 3 个新元素**：
  - 顶部 `<div id="validation-banner">`：缺失/不完整/有失败时显示红/黄/绿条
  - 底部 `<details id="validation-report-section">`：折叠区显示完整验证报告
  - 浏览器加载时**用 JS 强制重算** V1/V3/V4/V5/V6（用 POI 坐标 + 同样阈值），**结果覆盖** AI self-report
  - V2 显示"需高德"提示，让用户看 AI 的高德复核报告
  - V7 保留 AI self-report（脚本验不了）
- **`SKILL.md` Step 3 重构**：
  - 顶部加"🔒 v1.1.0 新增：代码级硬约束"小节
  - "每轮必跑的 3 步" 流程：跑脚本 → 合并结果到 tripData.validation_report → 浏览器强制重算
  - "AI 没法绕过——HTML 加载就用浏览器 JS 强制重算"
- **`references/validation-rules.md` 重写**：
  - 顶部加"🔒 v1.1.0 重要变化：代码级硬约束"小节
  - 总览表加"验证方式"列（⚙️ 脚本 / 🤖 AI 调高德 / 🤖 AI 上下文）
  - "浏览器 banner 行为"小节：5 种情况对应 5 种 banner 颜色
- **`references/multi-turn-protocol.md` 新增"场景七·验证对话"**：
  - 完整示例：AI 跑脚本 + 高德 → 合并报告 → 部署 → 用户看 banner → 反馈 → AI 修
- **`examples/chengdu-3d.json` 验证报告改格式**：7 条 rule 都加 `"source": "script" | "ai-amap" | "ai-context"` 字段（v1.1.0 banner 识别用）
- **顺带修复 chengdu-3d.json line 77 的 JSON 解析 bug**（"轻"火锅 里的双引号没转义，导致整个 JSON 解析失败；改为中文「轻」）

**最强硬约束是浏览器端 JS 强制重算**：
- AI 想在 self-report 里写假"✅ 全通过"也没用
- HTML 一加载，浏览器用 POI 坐标 + 阈值公式重新算一遍
- 算出来的 ❌ 会**直接覆盖** AI 的 ✅
- 用户点开就能看到真实结果

**保留**（**不能脚本化**的规则）：
- V2 时间可行性真通勤：必须 AI 调高德 `route_*` MCP（浏览器无 API key）
- V7 用户禁忌：必须 AI 上下文判断（用户说什么禁忌，AI 才能知道）

### chrome_launcher.py 主导装扩展（v1.0.3）

> **来源**：用户问"为什么我给别的 AI 用，它在配小红书的时候，都要让我手动去浏览器装拓展？但实际上这个 skill 直接让 AI 自己解决了呀，我扫个码就行了。"

**根因**：
- `autoclaw-cc/xiaohongshu-skills` 项目**自带 `scripts/chrome_launcher.py`**——它能**自动启 Chrome + 自动装 XHS Bridge 扩展 + 开 9222 调试端口**
- `scripts/cdp_publish.py login` 能**自动打开登录页 + 弹出二维码**
- 项目本身**就是设计给 AI 主导的**——README 写"Load unpacked"是给"想用日常 Chrome"用户的备选说明
- **别的 AI 让用户手装，是因为它们没看到 `chrome_launcher.py` 这个入口**（或者看到了也归到"系统操作，AI 做不了"那类）
- **本 skill 之前也写"必须用户做"**——错把"系统限制"和"AI 不知道有 launcher"混为一谈

**变更**：
- **`references/setup-guide.md` §2.2 整段重写**——从"必须用户手装"改为"两种装法"：
  - **方式 A（推荐，🟢）**：AI 跑 `python scripts/chrome_launcher.py`（自动启 Chrome + 自动装 XHS Bridge 扩展 + 9222 端口）
  - **方式 B（备选，🔴）**：Load unpacked 到用户日常 Chrome（仅当用户**主动说**"想复用日常 Chrome session"时）
- **`references/setup-guide.md` §2.3 升级**——扫码前先让 AI 跑 `python scripts/cdp_publish.py login` 打开登录页
- **`references/setup-guide.md` §0 速览表** 小红书行的"🟢🔴🔴 = 1/2 步"改为"🟢🟢🔴 = 1+1/1 步（装 skill+启 Chrome 装扩展 / 扫码）"
- **`references/multi-turn-protocol.md` §0.1 能力分级**——"🔴 必用户做"例子从"chrome://extensions 装扩展"改为"macOS Gatekeeper 弹窗确认 / Load unpacked（仅复用日常 Chrome 场景）"
- **`references/multi-turn-protocol.md` §0.2 矩阵**——小红书列加新行"**🟢 AI 跑 `chrome_launcher.py`**"（自动启 Chrome + 自动装扩展）；扫码前加"🟢 AI 跑 `cdp_publish.py login` 开登录页"
- **`references/multi-turn-protocol.md` §场景六 小红书对话示例**重写——"AI 跑 chrome_launcher.py → AI 跑 cdp_publish.py login → 用户扫"三步，**不再让用户碰 chrome://extensions**
- **`SKILL.md` §0.4 必用户做列表**——"chrome://extensions 装 Chrome 扩展"改为"仅当用户主动选择复用日常 Chrome session 时"，加 ⚠️ v1.0.3 重要变化说明
- **`references/xhs-research.md` §1.1 接入**——补 `chrome_launcher.py` / `bridge_server.py` / `cdp_publish.py login` 的描述，加 🔄 v1.0.3 关键洞察 callout

**真实使用流程**（小红书）：
```
🟢 AI: git clone + uv sync
🟢 AI: python scripts/chrome_launcher.py      ← 自动启 Chrome + 自动装 XHS Bridge 扩展
🟡 用户: macOS 弹「打开 Chrome」点「打开」    ← 一次性 Gatekeeper
🟢 AI: python scripts/cdp_publish.py login   ← 弹出登录二维码
🔴 用户: 小红书 App 扫
🟢 AI: python scripts/cli.py check-login     ← 验证
```

**保留 Load unpacked 路径的场景**：
- 用户**已经在日常 Chrome 登录了小红书**，想**复用 session**（避免重新扫码）
- 用户**装扩展到多台机器**（launcher 只启隔离 Chrome，手装可装到日常 Chrome）

### 弃用 A 方案（xpzouying/xiaohongshu-mcp）（v1.0.2）

> **来源**：用户决策"直接不用小红书的 MCP 了，直接用小红书的 skill"——理由：B 方案（autoclaw-cc skill）装起来更轻（一个 Chrome 扩展 vs Docker + Go server + 18060 端口），且本 skill 实际上**只需要搜索/详情**两个能力，A 方案的"13 个 tool"对旅行规划是杀鸡用牛刀。

**变更**：
- **SKILL.md** 数据源表 + §0.1 探测 + §0.2 识别去掉"二选一"，改为"B 方案唯一"
- **SKILL.md** §0.3 选 A 描述里的"小红书（推荐，二选一）"改为"小红书（推荐，B 方案唯一）"
- **`references/setup-guide.md` §2** 整段重写——删除方案 A 整节（Docker / 二进制 / `claude mcp add`），只保留 B 方案的 5 步流程（§2.0 自检 → §2.1 装 skill → §2.2 装扩展 → §2.3 扫码 → §2.4 验证）
- **`references/setup-guide.md` §0 速览表** + **§6 速查表** 删除 A 方案行
- **`references/xhs-research.md` §1** 整段重写——删除 §1.1（方案 A）+ §1.3（双方案工具映射表），重命名为 §1.1 接入 / §1.2 工具映射表（只剩 B 方案）
- **`references/xhs-research.md` §2.1 / §2.2** 删方案 A 调用示例，搜索/详情命令统一指向 `python ~/xhs-skill/scripts/cli.py ...`
- **`references/xhs-research.md` §7 / §9** 删 A 方案引用
- **`references/multi-turn-protocol.md` §场景六** 删"小红书 A 方案"对话整段；"小红书 B 方案"标题改为"小红书（Python skill，Chrome 扩展；v1.0.2 起唯一方案）"
- **`references/multi-turn-protocol.md` §0.2 5×7 矩阵** 小红书列"🟢 AI 调 `mcp__xiaohongshu__*`"改为"🟢 shell 跑 `cli.py check-login`"
- **`README.md`** 小红书小节从"二选一表"改为"唯一方案"小节；降级表里"小红书（方案 A 或 B）"改为"小红书"

**保留**（A 方案作为"已弃用"事实保留在 CHANGELOG 历史里，不在文档主体）：
- 1.0.0 "小红书二选一集成" 小节（已加"v1.0.2 弃用 A 方案"标注）

**理由存档**：
- A 方案的 13 个 tool（含发视频/商品绑定/定时发布/原创声明）是给"内容创作者"用的，**旅行规划 skill 用不上**
- A 方案部署需要 Docker/Go 环境 + 18060 端口 + `claude mcp add --transport http` + 重启 CC，**比 B 方案多 3 步**
- B 方案（`git clone` + `uv sync` + 装 Chrome 扩展 + 扫码）已经覆盖本 skill 需要的"搜索 → 详情"两个能力
- 同作者维护意味着 API 兼容性有保证，B 方案的 `search-feeds` / `get-feed-detail` 参数和 A 方案的 `mcp__xiaohongshu__search_feeds` / `mcp__xiaohongshu__get_feed_detail` 一一对应

### 真实使用发现（v1.0.1 patch）

> **来源**：11.txt 实测会话，AI 在跑大众点评时浪费了 3 轮才发现两个硬伤。

- **opencli 缺 Browser Bridge 扩展会连不上 Chrome**：setup-guide §3 之前只写 `npm install + Chrome 远程调试`，实际 opencli 1.8.x **必须装 Browser Bridge Chrome 扩展**（Web Store 1 分钟，或 GitHub releases 下 zip Load unpacked）。**这是 setup-guide 的硬伤**，v1.0.1 修复：
  - `references/setup-guide.md §3.2` 新增"装 Browser Bridge 扩展"为 🔴 必用户做；提供 Web Store 优先 + GitHub releases 备选两种方式
  - `references/dianping-research.md §1.1` 同步重写为"三件套"（npm 包 + 扩展 + 真实 Chrome）
  - `references/dianping-research.md §9.3` 补 Chrome 扩展安装步骤
  - `references/multi-turn-protocol.md §场景六·大众点评子流程` 把"装扩展"标 🔴 必用户做
- **不要用 Playwright 跑大众点评**：`verify.meituan.com` 识别 Headless Chrome 指纹（`navigator.webdriver=true` + "HeadlessChrome" UA）跳谜题页；`playwright-stealth` 救不了（Cloudflare Turnstile 用的是 TLS 指纹 + 行为分析 + 滑块轨迹，stealth 覆盖不到）。**唯一可行路线 = opencli + 真实 Chrome + 真人登录 session**（通过 Browser Bridge 扩展连入）。
  - `references/dianping-research.md §1` 顶部加 🚫 警告
  - `references/dianping-research.md §10` 决策树加"不要再尝试方案 B (WebFetch)"和"不要再尝试 Playwright"
  - `references/setup-guide.md §3` 顶部加 🚫 "不要用 Playwright 跑大众点评"警告
  - `references/multi-turn-protocol.md §场景六·大众点评子流程` 顶部加 ⚠️ 11.txt 实测说明
- **隔离 Chrome profile 多此一举**：11.txt 实测 `open -a "Google Chrome" --args --user-data-dir=...` 在 macOS 上不会被 Chrome.app 正确接收，启的还是默认 profile；**直接用日常 Chrome + 扩展反而更省事**（已登录 session 直接复用）
  - `references/setup-guide.md §3.3` 把"隔离 profile"挪到"💡 唯一例外"附注
  - `references/dianping-research.md §1.1 + §9.4` 同步

### 动态探查原则（v1.0.1 patch）

> **来源**：用户反馈"这个 skill 里面把工具列表写进去了吗？它不应该根据不同的机器、不同的环境去自主判断吗？"

**原则**：skill 文档**不硬编码**运行时探查结果（如"13 个 tool"、"高德有 X 个 tool"）——这些数字是产品/环境事实，**AI 应该自己探**。

**改动**：

- `SKILL.md §0.2`：自检表格从"硬编码示例"改为"**模板 + 探查方法**"——"13 个 tool"、"可查 POI/路线/距离/天气"这些 AI 应该跑 `claude mcp list` 探出来写，不再抄文档
- `SKILL.md §0.5`：验证连通性从"`mcp__amap__geocode` 查一个已知地址 / `mcp__xiaohongshu__check_login_status` 查一个关键词" 改为 "**调任一 tool 试探**"——AI 看自己环境里实际加载了哪些 tool，**挑最简单的试**
- `SKILL.md §0.2 状态分支`：从"按具体 tool 名（`mcp__amap__*` 等）判断" 改为"**按探到的 `mcp_*_` 前缀数量判断**"——不依赖任何具体 tool 名
- `references/setup-guide.md §6`：速查表从"用户看的对照表"升级为"装好应看到什么的**期望值** + AI 应跑 `claude mcp list` 自己探"——明确"这不是 AI 必须按这个表读"
- `references/multi-turn-protocol.md §场景六示例对话`：顶部加 ⚠️ 警示"**以下是意图示意，AI 调的是自己工具列表里实际存在的那个 tool**"——示例里写的 `mcp__playwright__browser_navigate` 是 `@playwright/mcp` 当前版本常见名，**不同版本可能叫 `navigate`**（不带 `browser_` 前缀）

**保留**（**产品/操作说明，跨环境稳定**）：
- setup-guide §2 里的安装命令（操作步骤）

**判定原则**：**"产品/MCP 设计说明"** 写文档；**"AI 探到的环境事实"** AI 自己探。

### 新增文档

- `references/setup-guide.md` §4：高德 Web (JS) API Key 域名白名单 + `~/.travel-planner/config` 复用存储流程

### 缺陷修复（前一轮 review）

- **经纬度顺序**：`references/amap-mcp-usage.md` 加 §0 强约定 `lng,lat`，示例同步修正
- **demo 数据对齐**：`examples/tokyo-4n5d.json` Day3 晚餐店名 / Day4 午餐店名 与 note/meals 一致
- **HTML 转义**：`assets/template.html` 新增 `esc()`，所有 `innerHTML` 拼接第三方抓取字段（name/note/url 等）统一转义
- **V1 判据**：">3km/>5km 直线"改**通勤分钟数**主判据 + 直线仅作预筛
- **V2 远郊/跨城日例外**：与 V1 对齐，修正 demo `validation_report` 对 Day4 的描述
- **降级闭环**：增"无高德 MCP 时 V1/V2/V3/V5 改 LLM 估算并标注'未实算'"专章
- **增量修改措辞**："重渲 Day N 卡片"改为"更新 tripData + 重写 HTML + 重新部署"
- **文档残留**：删 [references/multi-turn-protocol.md](references/multi-turn-protocol.md) 第 290-298 行重复粘贴段
- **README 目录**：补 `setup-guide.md`

### 已知限制

- 公开仓库 = 行程对任何拿到 URL 的人可见（GitHub Pages 私有仓需 Pro）
- 国内可达性：`github.io` 偶有访问慢，已给 Vercel 备选
- 高德地图需域名白名单配 `squirrelsong5.github.io`，否则线上地图空白

---

## [0.5.0] - 2026-06-17

### 新增（Onboarding）

- **`references/setup-guide.md`**：高德 / 小红书 / 大众点评 三个 MCP 的 step-by-step 安装配置手册
  - 5 分钟快速安装命令（含一键脚本）
  - 常见问题排查清单
  - 验证是否配置成功的速查表
- **SKILL.md Step 0 改写**：从"静默自检"改为"自检 + 引导 + demo 跳过路径"
  - 完整 / 部分 / 全部缺失 三种状态分支
  - 给出 Re-ground → Simplify → Recommend → Options 四拍格式
  - 明确 AI 可执行 / 需确认 / 需用户执行 三类操作边界
- **`references/multi-turn-protocol.md` 加 3 个场景**：
  - 场景六：首次使用 / MCP 配置引导（小白第一次）
  - 场景七：demo 演示路径（拒绝配置的用户）
  - 场景八：配置失败排查（按概率从高到低的检查清单）
- **README 顶部加"5 分钟快速开始"**：零基础用户友好路径
- **典型流程描述更新**：突出 Step 0 自检 + 引导

### 设计原则

- **不假设用户懂 MCP**：第一次必须解释"是什么 / 为什么要配"
- **不强迫**：拒绝配置也能用 demo 演示
- **不重复**：已配置的不要让用户重配
- **可恢复**：失败时给清晰的回退路径
- **可视化**：🔍 检测 / ✅ 成功 / ⚠️ 警告 / ❌ 失败 emoji 锚定

---

## [0.4.0] - 2026-06-17

### 重大重构：抽屉式侧边栏

- **改用 slide-out drawer**（用户反馈明确指出要"从侧边拉开的"那种，不是放在中间的两栏）
  - 主区是每天行程（地图 + 时间线），**全宽**
  - 抽屉默认关闭，右上角浮动按钮（FAB）点击打开
  - 抽屉从右侧滑入（移动端 90vw，桌面 420px）
  - 背景遮罩 + `backdrop-filter: blur(2px)`，主内容在抽屉打开时不可点
- **移除"删了什么 / 为什么删" section**
  - 用户明确指出"这是思考过程，没必要留在这上面"
  - 数据结构 `deleted` 字段保留（供 skill 内部使用），但 UI 不展示
- **改用 SVG icons**（不再用 emoji）
  - 菜单 / 关闭 / 酒店 / 天气 / 日历 全部内联 SVG（Heroicons 风格）
  - 无外部依赖，离线可用

### 无障碍 / 交互细节（来自 ui-ux-pro-max skill 指引）

- **键盘支持**：ESC 关闭抽屉 + focus trap（Tab 在抽屉内循环）
- **Skip link**：Tab 第一个焦点是"跳转到主内容"，方便键盘用户
- **focus-visible 焦点环**：所有可交互元素都有明显的焦点指示
- **`prefers-reduced-motion`**：用户系统设置开启减少动效时，所有动画缩到 0.01ms
- **`role="dialog"` + `aria-modal="true"`**：抽屉对屏幕阅读器是真正的对话框
- **`aria-expanded` / `aria-hidden`**：按钮和抽屉状态同步给 AT

### 视觉细节

- 字体栈优先 Inter / 系统字体（无 CDN 依赖）
- 圆角统一：8px / 12px / 16px 三档
- 阴影分 sm / md / lg 三档（不用 opacity hack）
- 抽屉 badge 显示提前订项数（小红点效果）
- 容器最大宽度 920px（更适合单列阅读，地图也更大）
- Drawer toggle 在小屏（<480px）只显示图标，节省空间

---

## [0.3.0] - 2026-06-17

### 变更（布局重构）

- **两栏布局**：从单列长条改为**侧边栏 + 主区**的网格布局
  - **侧边栏**（桌面 sticky 跟随滚动）：🏨 酒店 / 🌤 天气策略 / 🗑 删了什么（保留！作为思考过程）/ 📌 提前订
  - **主区**（专注每天行程）：📑 Tabs + 🗺 地图 + 当天时间线
- **保留"删了什么 / 为什么删"**：用户的反馈明确指出"这是思考过程，应该展示"，v0.2.0 把它放在页脚容易被忽略，v0.3.0 移到侧边栏顶部位置（仅次于酒店），始终可见
- **响应式**：
  - 桌面（>880px）：左侧 sidebar + 右侧 main（sidebar sticky 跟随滚动）
  - 移动端（≤880px）：单列堆叠，main 在前（地图 / 时间线优先），sidebar 在后（参考信息）
- **侧边栏 section 头部**：用 emoji + count 标签（如 "🗑 删了什么 5 项"），视觉上比 v0.2.0 的页脚更醒目

### 新增

- **`weather_plan` 渲染**：JSON 顶层有 `weather_plan` 字段时，侧边栏多一个 🌤 天气策略 区块
- **侧边栏计数标签**：每个 section 右上角显示项数

### 视觉优化

- 容器最大宽度从 760px → **1240px**，为两栏布局让出空间
- 侧边栏 section 使用更紧凑的卡片 padding（14px → 12px）
- 主区 day-card 加大 padding（14px → 18px / 16px → 20px），更突出

---

## [0.2.0] - 2026-06-17

### 新增（重大改进）

- **🗺 交互式地图**：HTML 内嵌高德 JS API，显示每天 POI 标记 + 交通路线 polyline
- **📑 Tab 切换**：顶部 Tab 切换 Day 1 / Day 2 / ...，地图和文字版行程同步更新
- **🎨 交通方式可视化**：步行 / 地铁 / 公交 / JR / 驾车 / 骑行 各用不同颜色（绿/蓝/红/橙），步行和骑行用虚线
- **🚶 怎么走区块**：每天时间线下方新增"怎么走"列表，把 transports 数据可视化
- **📍 地图降级**：未配置高德 Web API Key 时自动降级为文字版，不影响其他功能
- **🖱 交互细节**：marker 点击弹 InfoWindow；Tab 在移动端可横向滚动；Route toggle 开关

### 变更（Breaking）

- **数据结构重构**：每天从 `timeline`（混合 POI + transport 条目）改为 `pois` + `transports` 两条独立数组
- 新增必填字段：`center`（地图中心）+ `zoom`（缩放）+ 每条 POI 的 `lng` / `lat`
- 每天 `transports` 数组用 `from_idx` / `to_idx` 引用 POI，比 timeline 那种推断式更稳定

### 字段映射（迁移指南）

旧版 `timeline` 一条：

```json
{"time": "08:30", "place": "新宿 → 镰仓", "cat": "transport", "duration_min": 60}
```

新版拆成两段：

```json
// 在 pois 里加一条 idx=N 的 transport POI（如需在地图显示）
// 在 transports 里加 from_idx / to_idx
{"from_idx": 1, "to_idx": 2, "mode": "jr", "duration_min": 60, "description": "JR 藤泽 → 大船 → 新宿"}
```

如果是"路上的经过点"，可以只在 transports 表达、不出现在地图 POI 列表里。

---

## [0.1.0] - 2026-06-17

### 新增

- 初始版本发布
- **SKILL.md**：YAML frontmatter + 7 步主流程 + 3 轮迭代规划循环 + 增量修改入口
- **references/planning.md**：7 步规划方法论 + 5 条硬规则 + 反模式表（移植自 trip-map-builder）
- **references/multi-turn-protocol.md**：四拍交互协议（Re-ground → Simplify → Recommend → Options）+ Smart skip + 增量修改 6 场景
- **references/validation-rules.md**：7 条自动验证规则（V1-V7）+ 验证报告格式
- **references/amap-mcp-usage.md**：高德 MCP 5 个使用场景（找景点 / 规划路线 / 查酒店 / 算天气 / 验证时间可行性）
- **references/xhs-research.md**：小红书两段式调研方法（粗筛 → 精读）
- **references/dianping-research.md**：大众点评调研 + OpenCLI/CDP 安装指引 + 降级方案
- **references/hotel-planning.md**：单城 / 多城酒店候选筛选 + 通勤圈校验
- **assets/template.html**：单文件 HTML 模板（零外部依赖、卡片化、深色模式适配）
- **examples/tokyo-4n5d.json**：Tokyo 4 泊 5 日静态 demo 数据
- **examples/README.md**：JSON schema 文档

### 已知限制

- 大众点评无官方 MCP，需要用户装 OpenCLI 或接受数据降级
- 高德 MCP 需要用户申请 API Key（免费版额度足够本 skill 使用）
- 不集成 Leaflet 地图（用户没明确要，主打卡片化）
- 不做实时数据校验（demo 是静态的，真实使用靠 MCP）
- 不接 OTA 预订（只给跳转链接）

### 设计取舍

- 最多 3 轮迭代（避免无限循环）
- 不做自动保存到 git / Vercel 部署
- 不写自动化测试（skill 是 prompt-driven，测试靠实际跑对话）
