<div align="center">

# travel-planner

**把实时旅行信息整理成真正能出门照着走的攻略**

[![CI](https://github.com/SquirrelSong5/travel-planner-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/SquirrelSong5/travel-planner-skill/actions/workflows/validate.yml)
[![GitHub stars](https://img.shields.io/github/stars/SquirrelSong5/travel-planner-skill?style=flat)](https://github.com/SquirrelSong5/travel-planner-skill/stargazers)
[![Install with npx](https://img.shields.io/badge/install-npx%20skills%20add-CB3837?logo=npm)](#快速开始)
[![Version](https://img.shields.io/badge/version-3.3.0-blue.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[在线预览](https://squirrelsong5.github.io/travel-plans/chengdu-2026-09-18.html) ·
[快速开始](#快速开始) ·
[信息源](#五个信息源怎么分工) ·
[完整文档](#完整文档)

</div>

`travel-planner` 是一个可安装到 Codex、Claude Code、Cursor 等 AI Agent 的中国大陆旅行规划 Skill。安装后，只需告诉 AI 目的地、日期、人数、预算和偏好，它就会调研最新信息、编排每日路线，并生成一份可以直接使用的旅行攻略。

一份行程会同时提供两种形式：

- **对话版攻略**：完整内容直接显示在聊天中；
- **行程网页**：响应式单文件 HTML，可在手机上查看、离线保存或分享给同行人。

## 为什么使用

- **信息更可靠**：查询近期开放时间、票价、预约规则、交通和价格，并保留来源与核对时间；
- **路线能执行**：围绕每天的主要区域排线，计算地点之间的通勤时间，兼顾酒店往返与返程缓冲；
- **准备更完整**：统一整理餐厅、预算、待订事项、雨天备选和与同行人有关的安全提醒；
- **方便继续修改**：更换酒店、航班或景点后，重新核对受影响的路线和费用；
- **多端阅读**：同一份行程同时生成对话版和适合手机浏览的 HTML。

适合规划多日旅行、优化已有路线、出发前复核信息，以及行程临时变化后的调整。

## 快速开始

### 1. 安装

```bash
npx skills add SquirrelSong5/travel-planner-skill
```

安装命令使用 [Skills CLI](https://github.com/vercel-labs/skills)，会识别当前使用的 AI Agent。需要在所有项目中使用时加 `--global`。

<details>
<summary>没有 npx？使用 Git clone</summary>

```bash
git clone https://github.com/SquirrelSong5/travel-planner-skill.git travel-planner
```

</details>

### 2. 直接描述行程

```text
帮我规划成都 3 天 2 晚，2 个人，住春熙路，
想看熊猫、吃川菜，最后一天 18:00 的航班。
```

已有方案也可以继续修改：

```text
把第二天晚餐换到宽窄巷子附近，只重新核对受影响的路线和预算。
```

## 每次会得到什么

| 交付物 | 用途 |
| --- | --- |
| 对话版攻略 | 直接阅读完整日程、交通、餐饮、预算、预约和 Plan B |
| `trip.html` | 手机查看、离线保存和分享 |
| `trip.json` | 保存结构化行程，方便后续继续修改 |

需要在线分享时，直接告诉 AI“把行程部署到线上”。travel-planner 自带部署引导，会根据当前环境推荐 GitHub Pages、Cloudflare Pages、Netlify 或 Vercel 等托管方式，并协助生成可直接访问的网页链接。

## 五个信息源怎么分工

完整多日攻略默认逐一尝试 5 类来源，但每个平台只做自己擅长的事：

| 阶段 | 信息源 | 主要用途 |
| --- | --- | --- |
| 发现 | 小红书 | 近期玩法、分区、排队和踩雷信号 |
| 确认 | 官方与运营方 | 开放、预约、票务、临时通知和交通规则 |
| 落线 | 高德地图 | POI、坐标、顺路程度和通勤时间 |
| 餐饮 | 美团攻略 | 按区域、菜系、预算和场景建立餐厅候选 |
| 交易 | 携程等国内 OTA | 酒店、交通、门票的价格和可订状态 |

交付前会再次核对开放状态、主要路线和可订价格。攻略中会显示各类来源的使用状态和核对时间；不同来源发生冲突时，以最新官方信息为准。

## 推荐能力

若希望获取更完整的实时数据，建议让 AI Agent 具备以下能力：

- **网页搜索或浏览器**：查询官方通知、OTA 页面和餐饮攻略，通常由 Agent 自带；
- **高德地图 MCP**：查询 POI、坐标和路线，见[高德官方接入文档](https://lbs.amap.com/api/mcp-server/gettingstarted)；
- **小红书 MCP Skill**：补充近期玩法、排队体验和避雷信息。

```bash
npx skills add autoclaw-cc/xiaohongshu-mcp-skills --skill xiaohongshu
```

小红书 Skill 还需要配置对应的 MCP 服务并完成用户登录。未配置时仍可使用其他来源生成行程，但不会包含小红书的近期体验信息。配置方法见 [setup-guide.md](references/setup-guide.md)。

<details>
<summary>本地验证与渲染</summary>

只需要 Python 3.10+，不需要第三方 Python 包。

```bash
python -m unittest discover -s tests -v
python scripts/validate.py examples/chengdu-2026-09-18.json --pretty --fail-on-warn --as-of 2026-08-24
python scripts/render_markdown.py examples/chengdu-2026-09-18.json -o /tmp/trip.md
python scripts/render_html.py assets/template.html examples/chengdu-2026-09-18.json -o /tmp/trip.html
```

</details>

## 完整文档

| 文档 | 内容 |
| --- | --- |
| [SKILL.md](SKILL.md) | Agent 主工作流 |
| [data-sources.md](references/data-sources.md) | 五类来源、证据优先级与降级 |
| [planning.md](references/planning.md) | 行程编排方法 |
| [validation-rules.md](references/validation-rules.md) | V0–V13 校验规则 |
| [recheck-and-safety.md](references/recheck-and-safety.md) | 行前复核、临场调整与安全提醒 |

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=SquirrelSong5/travel-planner-skill&type=Date)](https://star-history.com/#SquirrelSong5/travel-planner-skill&Date)

如果它帮你省下了做攻略和反复核对的时间，欢迎点一个 [Star](https://github.com/SquirrelSong5/travel-planner-skill)。问题和真实旅行场景可以提交到 [Issues](https://github.com/SquirrelSong5/travel-planner-skill/issues)。

## License

[MIT](LICENSE)
