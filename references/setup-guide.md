# MCP 安装配置指南

> 本文件是 SKILL.md Step 0 引导流程的详细操作手册。
> AI 在检测到 MCP 缺失时，会按本文件的内容逐步引导用户配置。

> **v1.0 改造**：每个步骤标了 🟢 AI 跑 / 🟡 AI 跑+你口供 / 🔴 必你做 三色。
>
> **🔒 强制前置**：**Playwright MCP 是 AI 主导配置的入口**。自检发现未装时，AI **不得自作主张降级**——必须先引导装好，或用户**显式说"降级 / 跳过"**才能进半自动模式。详见 `references/multi-turn-protocol.md` §0.3。

---

## -1. 前置：装 Playwright MCP（🔒 强制前置，1 分钟）

> **不装 = 走半自动，全程慢 3 倍**。这是默认路径，**不装是显式降级**。

| | 没装 Playwright | 装了 Playwright |
|---|---|---|
| **5 个 MCP 配置总时间** | 15-20 分钟 | 5-7 分钟 |
| **用户介入次数** | 5-10 次手点 + 重启 | 1 次短信 + 1 次扫码 + 1 次重启 |
| **小红书 / 大众点评配置** | 浏览器步骤你手点 | AI 用 Playwright 自己点 |
| **用户体感** | 配 MCP 像在跑"5 个网页向导" | 像跟一个"会装 MCP 的同事"对话 |

### 怎么装（**按客户端走对应命令**）

> **AI 必须先按 SKILL.md §客户端适配层 探测到客户端 X，再选 X 对应的命令**。

| 客户端 | 装命令 | 装后操作 |
|--------|-------|---------|
| **Claude Code CLI** | `claude mcp add playwright npx @playwright/mcp@latest` | 完全退出 CC 重开 |
| **Hermes desktop GUI** | `hermes mcp install playwright`（或 `hermes mcp add playwright -- npx @playwright/mcp@latest`）| 下次启动自动加载（不用重启）|
| **Cursor** | 编辑 `~/.cursor/mcp.json` 加 playwright 条目 | Cmd+Shift+P → Reload Window |
| **Codex CLI** | `codex mcp add playwright -- npx @playwright/mcp@latest` | 项目级 config 自动 / 全局需重启会话 |
| **Cloud Code** | 编辑 `~/.cloudshell_cloudsdk_mcp.json` 加 playwright 条目 | 重开会话 |
| **Trae / CodeBuddy** | IDE 内 MCP 设置面板加 | 重启 IDE |

```bash
# 示例：Claude Code（用户输入 ! 让 AI 跑，或 AI 用 terminal tool）
!claude mcp add playwright npx @playwright/mcp@latest

# 示例：Hermes（AI 用 terminal() 工具跑）
hermes mcp install playwright
# 或 catalog 里没有时：
hermes mcp add playwright -- npx @playwright/mcp@latest

# 示例：Codex（AI 自己跑）
codex mcp add playwright -- npx @playwright/mcp@latest
```

装完**按客户端走对应操作让 MCP 生效**（CC/Cursor/Cloud Code/Trae/CodeBuddy 需重启/Reload；Hermes/Codex 项目级自动加载）。重启/Reload 后让 AI 试一下：

```
用 playwright MCP 打开 https://example.com 看看能不能拿到页面快照
```

能拿到 → AI 接管后面所有浏览器操作。

### 不想装怎么办？

> **这是显式降级**，AI 不得主动问"要不要降级"，**只在你主动说"降级 / 跳过 / 不用了"时**才进半自动模式。详见 `references/multi-turn-protocol.md` §0.3.2。

> **为什么不内置到 skill 依赖？** Playwright MCP 是 Microsoft 官方项目，独立维护，不属于"travel-planner 私有依赖"。用户装一次，所有项目都能用（不限于 travel-planner）。

---

## 0. 速览

| MCP | 必需度 | 没配的影响 | 配的话要多久 | 自动化级别 |
|-----|--------|----------|------------|------------|
| **高德地图 MCP** | 必需 | 路线/POI/距离/天气都是通用知识，数据不准 | 3 分钟（Playwright 装后） | 🟢🟡🔴 = 6/2/1 步 |
| **小红书（autoclaw-cc skill）** | 推荐 | 没法搜种草笔记，氛围/拍照/避雷信号缺失 | 2 分钟 | 🟢🟢🔴 = 1+1/1 步（装 skill+启 Chrome 装扩展 / 扫码） |
| **美团攻略（WebFetch）** 🆕 | 推荐（零装）| 国内 8 大城市缺"编辑过的好店清单"，候选池直接靠高德 text_search 召回 100+ 家 | **0 分钟**（AI 直接 WebFetch）| — |
| **大众点评（OpenCLI 深度档）**| 可选（v1.2.0 起**默认不推荐**）| 缺必吃榜入选 + 真实评价数 + 排队实况 | 5 分钟 | 🟢🔴🔴🔴 = 1/3 步（装扩展 + 扫码 + Chrome 常开）|
| **gh CLI（部署用）** | 必需 | 方案无法部署到 GitHub Pages | 2 分钟 | 🟢🟡 = 1 次贴 device code |

**最小可用**：只配高德地图 MCP 就能出方案（POI/路线/距离/天气）。
**完整体验（v1.2.0 推荐）**：高德 + 小红书 + 美团攻略 WebFetch（**零装**）。
**极致质量**：再加大众点评（OpenCLI + Chrome）。

> **小红书数据源（v1.0.2 唯一方案）**：`autoclaw-cc/xiaohongshu-skills`，Python CLI + Chrome 扩展。
> AI 通过 `python ~/xhs-skill/scripts/cli.py <subcommand> [args]` 调用。
> **选 A 的理由**：想发视频、想用商品绑定带货、想要更多筛选维度（发布时间/位置距离/已看未看等）、想用定时发布/原创声明/可见范围。
>
> 选完后续在 [references/xhs-research.md](xhs-research.md) 顶部"工具映射表"用对应调用方式。

---

## 1. 高德地图 MCP（必需，3 分钟 / 装 Playwright 后）

> 高德地图 MCP 是 AI 实时查询 POI / 路线 / 距离 / 天气的通道。
> 没它 AI 只能用通用知识，方案会很粗糙。

### Step 1.1：注册高德开放平台账号 🟡

> **AI 主导**（装了 Playwright 时）：AI 走完表单到「请输入验证码」停下，把控制权交还给你收短信。

```
🟢 AI: [tool: mcp__playwright__browser_navigate https://lbs.amap.com/]
      [tool: mcp__playwright__browser_click "注册按钮"]
      [tool: mcp__playwright__browser_type "手机号输入框" "13800138000"]
      [tool: mcp__playwright__browser_click "发送验证码"]

🟡 AI: 我把表单填到一半，平台发短信验证码到你手机了。
      请告诉我收到的 6 位验证码。

用户: 482931

🟢 AI: [tool: mcp__playwright__browser_type "验证码输入框" "482931"]
      [tool: mcp__playwright__browser_click "注册完成"]
      ✅ 账号注册完成。
```

**手动版**（没 Playwright 时）：
```
打开 https://lbs.amap.com/
点右上角「注册」
用手机号注册（免费）
收短信验证码 → 输入 → 完成
```

### Step 1.2：创建应用 + 拿 Key 🟢

> **AI 主导**：AI 自己进控制台 → 创应用 → 创 Key → 从页面快照里提取 Key 字符串。

```
🟢 AI: [tool: mcp__playwright__browser_navigate https://lbs.amap.com/dev/key/app]
      [tool: mcp__playwright__browser_click "创建新应用"]
      [tool: mcp__playwright__browser_type "应用名" "travel-planner"]
      [tool: mcp__playwright__browser_click "添加 Key → 选 Web 服务"]
      [tool: mcp__playwright__browser_snapshot]  ← 提取 Key 字符串
      🔑 你的 Key: 7d8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c
      （AI 把它存到下一步 shell 命令的占位符里）
```

**手动版**：
```
登录后 → 控制台
→ 「应用管理」→「我的应用」
→ 点右上角「创建新应用」

填写：
  应用名称：travel-planner
  应用类型：其他

提交后进入应用详情页
→ 点「添加 Key」按钮

填写：
  Key 名称：mcp-server
  服务平台：勾选「Web 服务」（⚠️ 不是「Web 端 (JS API)」！）

提交后系统生成一个长字符串 API Key，**复制下来**
```

### Step 1.3：配置到 Claude Code 🟢

> **AI 跑**：一行 shell，AI 直接执行（不需要你打开终端）。

```bash
# AI 自己跑（用户 Key 由 Step 1.2 的 browser_snapshot 提取后填入）：
claude mcp add --transport http amap "https://mcp.amap.com/mcp?key=7d8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c"
```

> 这条命令会写到对应客户端的配置文件（CC: `~/.claude.json` / Hermes: `~/.hermes/config.yaml` / Cursor: `~/.cursor/mcp.json` / Codex: `~/.codex/config.toml` / 其他: IDE 内部）。

### Step 1.4：让 MCP 生效 🔴

> **必须用户做**（按客户端走对应操作）：

| 客户端 | 操作 |
|--------|------|
| **Claude Code CLI** | 完全退出 CC 窗口，重新打开（启动时加载 MCP 列表，**没法热加载**）|
| **Hermes desktop GUI** | **不需要重启**——下次 `hermes chat` 启动自动加载 |
| **Cursor** | Cmd+Shift+P → 输入 `Reload Window` → 回车 |
| **Codex CLI** | 项目级 config 自动加载；全局 config 需重启会话 |
| **Cloud Code** | 重开会话 |
| **Trae / CodeBuddy** | 完全退出 IDE，重新打开 |

### Step 1.5：验证 🟢

> **AI 跑**：调任一 `mcp__amap__*` tool（**AI 看自己环境里实际加载的 tool 名字，挑最简单的**）。

```
🟢 AI: [tool: mcp__amap__maps_geo "成都东站"]    # 或 maps_text_search 等
      ✅ 返回坐标 → 高德通了。
```

### Step 1.6：常见问题

| 报错 | 原因 | 解决 |
|------|------|------|
| 找不到 `claude` 命令 | Claude Code CLI 没装 | 装 Claude Code 桌面版或 CLI |
| `claude: command not found` | PATH 没设 | `which claude` 看看在哪，加到 PATH |
| `INVALID_USER_KEY` | Key 填错 | 重新检查 Key 字符串 |
| 添加后看不到工具 | 没重启 | 完全退出再开 Claude Code |
| 添加后还是看不到 | 配置没生效 | 删掉 `~/.claude.json` 里其他无关 MCP 配置再试 |
| Playwright 找不到元素 | 页面改版了 | 让 AI 重新 `browser_snapshot` 看新结构 |

---

## 2. 小红书（推荐）

> 用来搜种草笔记（景点氛围 / 餐厅拍照 / 避雷）。
>
> **v1.0.2 起唯一方案**：`autoclaw-cc/xiaohongshu-skills`（Python CLI + Chrome 扩展）。
> 原 `xpzouying/xiaohongshu-mcp` 方案已弃用，**别再装 Docker/Go server 那套**——多此一举且维护负担重。

### Step 2.0：先看环境里是否已经有了

新会话里输入：

```bash
python ~/xhs-skill/scripts/cli.py check-login
# 期望输出：✓ 已登录（用户名）
```

- 跑得通 + 显示"已登录" → 你的环境已装好，**跳过本节**
- 跑不通（`No such file` / 命令找不到） → 进 §2.1 装
- 命令在但显示"未登录" → 跳到 §2.3 重新扫码

---

### 2.1 装 Python skill 🟢

> **AI 跑**：

```bash
git clone https://github.com/autoclaw-cc/xiaohongshu-skills.git ~/xhs-skill
cd ~/xhs-skill
uv sync   # 装 uv：brew install uv
```

### 2.2 装 Chrome 扩展 + 启 Chrome（**AI 主导** 🟢）

> **这个 skill 项目的 `chrome_launcher.py` 本来就是设计给 AI 跑的**——它会**自己启 Chrome + 自动装扩展 + 开 9222 调试端口**，**用户不需要去 chrome://extensions 手装**。别的 AI 让人手装，是因为它们没看到这个 launcher。

**方式 A：项目自带 launcher（推荐，🟢 AI 跑）**

```bash
cd ~/xhs-skill
python scripts/chrome_launcher.py
# 行为：自动起一个隔离 Chrome 实例 + 自动加载 extension/ 目录作为 unpacked 扩展 + 开 9222 调试端口
# 第一次会要求用户确认「打开 Chrome」对话框（macOS Gatekeeper），点「打开」即可
```

AI 跑完告诉用户「Chrome 已经起来了，扩展 XHS Bridge 也自动装上了」。

**方式 B：Load unpacked 到日常 Chrome（备选，🔴 必用户做）**

> **什么情况下走这条**：用户**已经在日常 Chrome 里登录了小红书**，想复用 session 不重启浏览器。

1. Chrome 打开 `chrome://extensions/`
2. 开「开发者模式」
3. 点「加载已解压的扩展程序」→ 选 `~/xhs-skill/extension/`
4. 确认扩展 **XHS Bridge** 已启用

做完告诉 AI「扩展装了」。

> **判断走 A 还是 B**：
> - 用户没特殊说明 → **A**（AI 跑 launcher，最省事）
> - 用户说"我日常 Chrome 已经登了小红书" → **B**（复用 session）

### 2.3 扫码登录（🟢 AI 启页 + 🔴 用户扫）

> **AI 不能扫码**（必须用户用小红书 App 扫），**但 AI 能把登录页打开 + 让二维码显示出来**——这样用户只需看一眼手机 App。

**方式 A 配套（🟢 AI 跑）**：

```bash
cd ~/xhs-skill
python scripts/cdp_publish.py login
# 行为：通过 CDP 协议在 launcher 起的 Chrome 里打开小红书登录页，弹出二维码
```

**方式 B 配套（🔴 必用户做）**：

1. 在装好扩展的 Chrome 里访问 https://www.xiaohongshu.com
2. 页面弹出二维码 → **移动 App 扫**

**扫的姿势**（A/B 都一样）：
- 弹出二维码 → **移动 App 扫**（同一账号不要在别的网页端登录，否则会被踢出）
- 扫完告诉 AI「扫了」

⚠️ **同账号多端登录会被踢**：登录后不要再在浏览器里登录同一账号。

### 2.4 验证 🟢

> **AI 跑**：

```bash
cd ~/xhs-skill && python scripts/cli.py check-login
# 期望输出：✓ 已登录（用户名）
```

### 2.5 常用命令（完整映射见 [references/xhs-research.md](xhs-research.md) §1.2）

```bash
# 搜索
python scripts/cli.py search-feeds --keyword "成都 火锅" --sort_by "最多点赞"

# 帖子详情（需 feed_id + xsec_token）
python scripts/cli.py get-feed-detail --feed_id <ID> --xsec_token <TOKEN>

# 发图文（本地图片，推荐）
python scripts/cli.py publish-content \
  --title "成都三日游攻略" \
  --content "正文..." \
  --images "/Users/me/photos/01.jpg,/Users/me/photos/02.jpg" \
  --tags "成都,旅行,火锅" \
  --visibility "公开可见"

# 评论 / 点赞 / 收藏
python scripts/cli.py post-comment --feed_id <ID> --xsec_token <TOKEN> --content "想去！"
python scripts/cli.py like-feed --feed_id <ID> --xsec_token <TOKEN>
python scripts/cli.py favorite-feed --feed_id <ID> --xsec_token <TOKEN>
```

---

### 2.x 都不装也无所谓

skill 会降级为 WebFetch 小红书 M 站，方案质量略低但能用。

---

## 3. 大众点评（v1.2.0 起**深度档，非必需**）

> ⚠️ **v1.2.0 重大变化**：本节**默认不推荐装**。**80% 场景用"高德 POI + 美团攻略 WebFetch"双轨零装就够**（参见 `references/dianping-research.md` §0 / `references/meituan-guide-research.md`）。
>
> **什么情况下才装**：用户**明确要求**"必吃榜上榜 + 评价数 + 排队实况"**或**主轨方案拿不定主意需要大众点评评价数排序。
>
> **本节内容**：当上面条件满足时，按以下步骤装。**普通用户**请直接跳到 §4。

### 3.0 先确认：是不是真的需要？

**自检流程**（AI 应先跟用户对一下）：

```
1. 这次做哪几个城市？ → 8 大热门城市（沪/京/蓉/穗/深/杭/渝/汉）→ 美团攻略够用
2. 用户是否说"必吃榜" / "评价数" / "真实排队"？ → 是才需要本节
3. 高德 text_search + 美团攻略 5+ 候选拿不定主意？ → 是才需要本节

三个都"否" → 跳过本节，用主轨方案
任一是 → 进 Step 3.1
```

### Step 3.1：装 OpenCLI + Chrome 🟢

> **AI 跑**：

```bash
# 装 opencli（如没装 Node.js，AI 也会装；Node 需 >= 21）
npm install -g @jackwener/opencli

# 装 Chrome（如已装则跳过；macOS 多数已自带）
brew install --cask google-chrome
```

### Step 3.2：装 Browser Bridge Chrome 扩展 🔴

> **必须你做**（chrome://extensions 必须人手；opencli 没有扩展就连不进真实 Chrome session）：
>
> **方式 A：Chrome Web Store（推荐，1 分钟）**
> 1. 打开 [Chrome Web Store - OpenCLI](https://chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk)
> 2. 点「添加至 Chrome」
> 3. 在弹窗里点「添加扩展程序」
>
> **方式 B：从 GitHub releases 手动装（Web Store 不可用时备选）**
> 1. AI 跑：`curl -sL https://api.github.com/repos/jackwener/OpenCLI/releases/latest | grep opencli-extension`
> 2. 拿到最新 zip URL 后 AI 下载到 `~/Downloads/opencli-extension.zip`
> 3. 解压：`unzip ~/Downloads/opencli-extension.zip -d ~/Downloads/opencli-extension/`
> 4. Chrome 打开 `chrome://extensions/`
> 5. 开「开发者模式」（右上角开关）
> 6. 点「加载已解压的扩展程序」→ 选 `~/Downloads/opencli-extension/`
> 7. 装好后 AI 跑 `opencli doctor` 验通（应看到「Extension connected」）

### Step 3.3：登录大众点评 🔴

> **必须你做**（大众点评强制 App 扫码，AI 做不了）：

1. 在**已装 opencli 扩展**的 Chrome 里访问 https://www.dianping.com
2. 用大众点评 App 扫登录二维码
3. 扫完告诉 AI「扫了」

> 💡 **关于 profile 隔离**：不需要专门启隔离 Chrome。**直接用你日常的 Chrome 即可**——opencli 通过 Browser Bridge 扩展连真实 Chrome 进程，**复用你已登录的 session**。
>
> ⚠️ 唯一例外：你同时跑别的自动化爬虫（怕互相污染 cookie）才用隔离 profile：
> ```bash
> mkdir -p ~/.opencli-chrome-profile
> /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
>   --remote-debugging-port=9223 \
>   --user-data-dir=$HOME/.opencli-chrome-profile &
> ```

### Step 3.4：测试连通性 🟢

> **AI 跑**：

```bash
opencli doctor                              # 应看到 "Extension connected"
opencli dianping search "烤肉" --city 成都 --limit 3 -f json
```

`opencli doctor` 全绿 + `dianping search` 返回 JSON → 成功。

### Step 3.5：常见问题

| 报错 / 现象 | 原因 | 解决 |
|------------|------|------|
| `opencli doctor` 报 "Extension not connected" | Browser Bridge 扩展没装 / 被禁用 | 回到 Step 3.2 重装；确认 `chrome://extensions` 扩展开着 |
| `dianping search` 返回空 / 401 | Chrome session 没登录 / 登录过期 | 在装好扩展的 Chrome 里访问 dianping.com 重新登录 |
| `verify.meituan.com` 弹谜题 | **AI 用 Playwright 跑点评**（必失败，参见顶部警告） | 改用 opencli 路线；不要尝试用 Playwright 硬刚 |
| `attach failed: Cannot access a chrome-extension:// URL` | 别的扩展冲突 | 临时禁用其他扩展 |
| daemon 起不来 | Node 版本过低 | 装 Node 21+ |

### Step 3.6：跳过也没事（**v1.2.0 默认状态**）

skill 会自动降级为"**高德 POI 详情 + 美团攻略 WebFetch + 小红书软信号**"组合，**零装零扫码**。评分/营业/类型从高德拿，城市/品类/场景筛选从美团攻略拿，软信号从小红书拿。**80% 场景方案质量与 opencli 深度档相差不大**。

---

## 4. 高德 Web (JS) API Key + 部署白名单（手机端看地图的关键）

> 本节是**手机端能否看到地图**的关键。如果只在本机用电脑打开 HTML，可跳过；用 GitHub Pages 部署必须配。

### 4.1 同一个账号下创建两个不同 Key

高德开放平台有**两套不同的 Key**，同一个账号下需要分别申请：

| Key 类型 | 用途 | 申请入口 |
|---------|------|---------|
| **Web 服务 Key** | MCP server 调 POI / 路线 / 天气（后端用） | 控制台 → 添加 Key → 服务平台「Web 服务」 |
| **Web 端 (JS API) Key** | 浏览器 JS 加载地图（前端用） | 控制台 → 添加 Key → 服务平台「Web 端 (JS API)」 |

### 4.2 申请 Web (JS API) Key

```
控制台 → 应用管理 → 我的应用 → 选已有应用（或新建） → 添加 Key
服务平台：勾选「Web 端 (JS API)」
创建后复制该 Key
```

### 4.3 配置域名白名单（必须！否则部署后地图空白）

```
控制台 → 我的应用 → 找到该应用 → 设置 → 域名白名单
按部署方式加：
  - GitHub Pages：squirrelsong5.github.io  （替换成你的用户名）
  - 自定义域名：yourdomain.com
  - 本地测试：留空 或 127.0.0.1
```

**不配白名单会报 `INVALID_USER_KEY` / 地图不显示**。

### 4.4 Key 复用：存到本地配置

把 Web JS Key 存到 `~/.travel-planner/config`，Step 7 交付时在 URL 加 `?k=` 参数注入地图 Key（**不写入 HTML/git**，防泄露）。

```bash
mkdir -p ~/.travel-planner
cat > ~/.travel-planner/config <<EOF
# 高德 Web (JS API) Key —— 给浏览器 JS 地图用
AMAP_WEB_KEY=你的Web-JS-API-Key

# 高德 Web 服务 Key —— 已通过 MCP 配置过；可在此冗余存一份
AMAP_MCP_KEY=你的Web服务Key
EOF
chmod 600 ~/.travel-planner/config
```

**加载顺序**（浏览器运行时，template.html IIFE）：
1. URL 参数 `?k=YOUR_KEY`（Step 7 交付 URL 用这个）
2. `localStorage.amap_web_key`（一次设置，后续免带参数）
3. 都没有 → 地图降级为「按 Tab 切换文字版行程」（HTML 仍可正常部署）

**AI 部署时**：从 `~/.travel-planner/config` 或环境变量 `AMAP_WEB_KEY` 读取 Key，拼到交付 URL 的 `?k=` 参数，**禁止写入 HTML/JSON/git**。

### 4.5 Vercel 备选

如果 `squirrelsong5.github.io` 手机端访问慢/打不开，备选：
1. Vercel 自动部署：GitHub 仓库连 Vercel，push 即部署，URL 形如 `travel-plans.vercel.app`。
2. **白名单同步加 `travel-plans.vercel.app`**（否则同 4.3 问题）。

---

## 5. 部署：GitHub Pages（AI 主导 2 分钟）

> 把生成的 HTML 推到 GitHub 公开仓，启用 Pages，手机直接点 URL 看活地图。

### Step 5.1：装 gh CLI（如未装）🟢

> **AI 跑**（macOS 自带，其他平台 AI 会装）：

```bash
which gh || brew install gh
```

### Step 5.2：device flow 登录 GitHub 🟡

> **AI 跑 + 你贴 device code**（GitHub 官方授权机制）：

```bash
gh auth login --web --git-protocol https
```

AI 跑这条会输出一个 8 位 device code，**AI 暂停**让你去 https://github.com/login/device 粘贴 → 授权 → 告诉 AI「授权好了」。

### Step 5.3：建仓 + push + 启 Pages 🟢

> **AI 跑**（一行连发）：

```bash
cd ~/.travel-plans-work/  # 你的本地 trip-plans 工作目录
gh repo create SquirrelSong5/travel-plans --public --source=. --remote=upstream --push
gh repo edit --enable-pages --pages-source main --pages-path /
git push upstream main
```

### Step 5.4：跳过也没事

不部署就用本地 HTML 文件（或 P2P 分享），但**手机打开不方便**。

---

## 5.5 一键脚本（可选，给懒得手动的人）

> **注意**：v1.0 之后这脚本基本没用——所有"可自动化的"AI 都跑了，剩 2 分钟真人动作，脚本反而绕远。
> 保留作"批量部署给朋友用"的备选。

```bash
#!/bin/bash
# travel-planner MCP 一键配置（手动版，无 Playwright）
# 注意：此脚本假定用户在 Claude Code CLI 客户端。
# 其他客户端（Hermes/Cursor/Codex/Cloud Code/Trae/CodeBuddy）请按 §客户端适配层走对应命令。

echo "=== 高德地图 MCP 配置 ==="
echo "先去 https://lbs.amap.com/ 拿一个 API Key（Web 服务类型）"
read -p "粘贴你的高德 API Key: " AMAP_KEY

# Claude Code CLI 专用
claude mcp add --transport http amap "https://mcp.amap.com/mcp?key=$AMAP_KEY"
# Hermes desktop GUI
# hermes mcp add amap --transport http --url "https://mcp.amap.com/mcp?key=$AMAP_KEY"
# Codex CLI
# codex mcp add amap --url "https://mcp.amap.com/mcp?key=$AMAP_KEY"

echo ""
echo "✅ 配置完成！请按客户端走对应操作让 MCP 生效："
echo "  - Claude Code: 完全退出 CC 重开"
echo "  - Hermes: 不需要重启，下次启动自动加载"
echo "  - Cursor: Cmd+Shift+P Reload Window"
echo "  - Codex: 项目级自动 / 全局重启会话"
echo "  - Cloud Code: 重开会话"
echo "  - Trae / CodeBuddy: 重启 IDE"
echo "新会话里输入'高德地图'测试是否加载成功。"
```

```bash
chmod +x ~/.travel-planner/setup.sh
~/.travel-planner/setup.sh
```

---

## 6. 检测 MCP 是否配置成功的速查表

> **这张表是"装好后应该看到什么"的期望值**，不是"AI 必须按这个表读"的硬编码。AI 应该用**按客户端对应的命令**（`claude mcp list` / `hermes mcp list` / 看 `~/.cursor/mcp.json` / `codex mcp list` / 看 IDE 设置）**自己探**，看到啥就报告啥。

打开客户端新会话，输入：

```
列出你能用的所有 mcp__* 工具
```

或用 shell 自己探（**按客户端走对应命令**）：

```bash
claude mcp list         # Claude Code CLI
hermes mcp list         # Hermes desktop GUI
cat ~/.cursor/mcp.json  # Cursor（看 mcpServers 字段）
codex mcp list          # Codex CLI
# Cloud Code / Trae / CodeBuddy: 看 IDE 设置面板
```

对照期望（**装好应该看到**）：

| 期望看到的工具前缀 | 含义 | 怎么验通 |
|------------------|------|---------|
| `mcp__playwright__*` | Playwright ✅（**🔒 必装**） | 调任一 `mcp__playwright__*` tool 试 |
| `mcp__amap__*` | 高德 ✅ | 调任一 `mcp__amap__*` tool 试 |
| `python ~/xhs-skill/scripts/cli.py check-login` 可用 | 小红书 ✅ | 跑这条命令 |
| `opencli doctor` 全绿 | 大众点评 ✅ | 跑 `opencli dianping search ...` 试 |

**没看到某个前缀** ≠ 一定没装——可能是：
- MCP 注册了但客户端没加载（**重启客户端**）
- MCP 装在别的客户端（Hermes vs CC 配置不共享）
- 该 MCP 当前版本没暴露这个前缀

**正确的调试姿势**：
1. **按客户端走对应 mcp list 命令**看实际注册了哪些（CC: `claude mcp list` / Hermes: `hermes mcp list` / Cursor: 看 `~/.cursor/mcp.json` / Codex: `codex mcp list` / 其他: 看 IDE 设置）
2. 对比上表
3. 没注册的 → 装
4. 装了没看到 → **按客户端重启**（CC 完全退出 / Hermes 下次启动 / Cursor Reload Window / Codex 重启会话 / Cloud Code 重开会话 / Trae-CodeBuddy 重启 IDE）
5. 重启后还没 → 检查对应的 server 是否在跑（如 `ps aux | grep xhs-skill` / `ps aux | grep opencli` 等）

---

## 7. 卸载 / 重置

```bash
# 移除高德 MCP（按客户端走对应命令）
claude mcp remove amap         # Claude Code CLI
# hermes mcp remove amap       # Hermes desktop GUI
# 编辑 ~/.cursor/mcp.json 删条目  # Cursor
# codex mcp remove amap        # Codex CLI
# 编辑对应 JSON 删条目          # Cloud Code
# IDE 设置面板删               # Trae / CodeBuddy

# 查看所有 MCP
claude mcp list                # Claude Code CLI
# hermes mcp list              # Hermes desktop GUI
# cat ~/.cursor/mcp.json       # Cursor
# codex mcp list               # Codex CLI
# 看 IDE 设置                  # Trae / CodeBuddy
```
