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

`travel-planner` 是面向中国大陆行程的 AI Agent Skill。它不是简单罗列景点，而是核对开放、路线、餐饮、价格和预订事项，再从同一份数据同时生成：

- **对话内完整攻略**：不用打开附件，直接在聊天里看；
- **响应式单文件 HTML**：适合手机查看、离线保存和分享。

公开网页链接只是可选项，不会成为完成旅行规划的前提。

## 它解决什么

- 营业时间、票价和预约规则来自可回溯的近期来源，不靠模型记忆；
- 每天按区域排线，检查酒店往返、相邻地点通勤和返程缓冲；
- 餐厅、预算、待订事项、雨天 Plan B 和安全提醒都进入攻略；
- 信息变化后只重查受影响部分，再同步更新对话版和 HTML；
- 严格校验缺字段、过期信息、假来源、不可行路线和错误预订链接。

> 需求 → 五源调研 → 路线与预算校验 → 对话攻略 + HTML

## 快速开始

### 1. 安装

```bash
npx skills add SquirrelSong5/travel-planner-skill
```

需要在所有项目中使用时加 `--global`。该命令通过通用的 [Skills CLI](https://github.com/vercel-labs/skills) 安装，本仓库不需要发布 npm 包。

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

| 交付物 | 用途 | 是否必选 |
| --- | --- | --- |
| 对话版攻略 | 直接阅读完整日程、交通、餐饮、预算、预约和 Plan B | 必选 |
| `trip.html` | 手机查看、离线保存和分享 | 必选 |
| `trip.json` | 两种输出的共同数据源，方便继续修改 | 建议保留 |
| 公开 URL | GitHub Pages 等公开分享 | 用户确认后可选 |

公开发布可能暴露旅行城市、日期、酒店和路线，因此必须先确认隐私范围。本地 HTML 不受影响。

## 五个信息源怎么分工

完整多日攻略默认逐一尝试 5 类来源，但每个平台只做自己擅长的事：

| 阶段 | 信息源 | 主要用途 |
| --- | --- | --- |
| 发现 | 小红书 | 近期玩法、分区、排队和踩雷信号 |
| 确认 | 官方与运营方 | 开放、预约、票务、临时通知和交通规则 |
| 落线 | 高德地图 | POI、坐标、顺路程度和通勤时间 |
| 餐饮 | 美团攻略 | 按区域、菜系、预算和场景建立餐厅候选 |
| 交易 | 携程等国内 OTA | 酒店、交通、门票的价格和可订状态 |

交付前再用官方、高德和 OTA 复核最容易变化的内容。发生冲突时，以最新官方结论为准；某个平台无法访问时会明确标注降级，不会假装已经使用。

> 网页搜索、浏览器和 MCP 是获取信息的方式，不是第六个信息源。

## 推荐能力

核心 Skill 可以单独安装，外部能力按需补充：

- **网页搜索或浏览器**：强烈推荐，通常使用 Agent 自带能力；
- **高德地图 MCP**：强烈推荐，用于真实 POI 和路线计算，见[官方接入文档](https://lbs.amap.com/api/mcp-server/gettingstarted)；
- **小红书 MCP Skill**：可选，只用于近期体验软信号。

```bash
npx skills add autoclaw-cc/xiaohongshu-mcp-skills --skill xiaohongshu
```

小红书增强还需要对应 MCP 服务和用户登录；不想配置时可以直接跳过。完整边界见 [setup-guide.md](references/setup-guide.md)。

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
