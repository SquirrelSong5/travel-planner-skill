<div align="center">

# travel-planner

**把实时旅行信息变成能执行、能校验、能继续修改的行程网页**

[![CI](https://github.com/SquirrelSong5/travel-planner-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/SquirrelSong5/travel-planner-skill/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[在线预览](https://squirrelsong5.github.io/travel-plans/chengdu-2026-09-18.html) ·
[快速开始](#快速开始) ·
[信息源](#现在有哪几个信息源) ·
[文档](#文档)

</div>

`travel-planner` 是面向中国大陆行程的 AI Agent Skill。它组织 POI、官方通知、路线、酒店、餐厅、价格和预订事项，生成结构化 JSON 与响应式单文件 HTML，并用脚本检查路线、时间、预算和来源字段。

默认结果保存在本地。公开 GitHub Pages 链接是可选交付，不再是强制步骤。

## 能做什么

- 基于日期、人数、预算、偏好和已订交通规划多日行程；
- 用实时来源核对开放时间、预约、票价、坐标和通勤；
- 按区域组织每天路线，处理酒店往返与末日返程缓冲；
- 给餐厅主选、备选、位置与价格证据；
- 输出 JSON + 手机可读的单文件 HTML；
- 对改酒店、换景点、延长日期等请求做增量更新；
- 用 V0–V13 规则阻止缺字段、假来源、不可行路线和错误预订链接。

## 现在有哪几个信息源

当前主模型包含 **5 类信息源**：

| 信息源 | 主要提供什么 | 使用方式 |
| --- | --- | --- |
| 高德地图 | POI、坐标、路线、距离、通勤时长 | 地理与路线硬数据 |
| 官方渠道 + 网页搜索 | 营业/闭馆、预约、票务、临时通知、天气、公共交通规则 | 硬事实最高优先级 |
| 携程等国内 OTA | 酒店、机票、火车、实时价格区间与国内预订深链 | 价格与预订 |
| 小红书 | 分区、节奏、排队、拍照、近期踩雷 | 可选体验信号 |
| 美团攻略 | 城市餐厅候选、菜系与场景化推荐 | 可选餐饮候选池 |

Playwright、WebFetch、MCP 是获取信息的工具，不是独立信息源；GitHub Pages 是交付渠道，也不是信息源。

大众点评已移出默认链路。只有用户明确要求，且当前环境已经具备合规访问能力时，才作为补充信号；项目不会要求安装扩展、扫码登录或绕过反爬。

更完整的证据优先级和降级策略见 [references/data-sources.md](references/data-sources.md)。

## 工作流

1. 归一化目的地、日期、人数、预算、偏好和已订项目；
2. 先查官方硬事实，再查地图与 OTA；
3. 用小红书/美团发现候选，不让攻略覆盖官方结论；
4. 按区域和固定时段排日程，实查主要通勤；
5. 写入来源、价格和预订项；
6. 严格校验，修到没有失败和警告；
7. 渲染 HTML；按用户选择本地交付或公开发布。

## 快速开始

### 安装

把仓库克隆到你的 Agent 能发现的 skills 目录。例如：

```bash
git clone https://github.com/SquirrelSong5/travel-planner-skill.git travel-planner
```

不同宿主的 skills 目录和 MCP 配置方式不同。Skill 本身不会自动安装地图、浏览器或第三方账号能力；只有你明确要求配置时，才参考 [setup-guide.md](references/setup-guide.md)。

### 使用

直接描述行程：

```text
帮我规划成都 3 天 2 晚，2 个人，住春熙路，想看熊猫、吃川菜，最后一天 18:00 的航班。
```

也可以要求它修改已有方案：

```text
把第二天晚餐换到宽窄巷子附近，只重新核对受影响的路线和预算。
```

### 本地验证与渲染

仓库内置成都示例：

```bash
python scripts/validate.py examples/chengdu-2026-09-18.json --pretty --fail-on-warn

python scripts/render_html.py \
  assets/template.html \
  examples/chengdu-2026-09-18.json \
  -o /tmp/chengdu-trip.html
```

不需要第三方 Python 包。交互地图的高德 Web Key 由浏览者在页面内输入，仅保存在当前浏览器；Key 不应放入 URL、HTML、JSON 或 Git 仓库。

## 输出与隐私

默认交付：

- `trip.json`：可继续修改、校验和渲染的结构化数据；
- `trip.html`：可离线打开的单文件行程页。

公开发布前需要确认，因为页面可能暴露旅行城市、日期、酒店和每日路线。若只想发给同行人，优先使用私密文件分享；若使用 GitHub Pages，应先删除不想公开的信息。

## 项目结构

```text
travel-planner-skill/
├── SKILL.md                     # Agent 主工作流
├── agents/openai.yaml           # UI 元数据
├── assets/template.html         # 单文件行程模板
├── examples/                    # 可运行示例
├── references/                  # 按需读取的研究与规则
├── scripts/validate.py          # V0–V13 校验
├── scripts/render_html.py       # 安全注入 JSON 并渲染 HTML
├── scripts/add_hotel_legs.py    # 显式补酒店通勤
└── tests/                        # 回归测试
```

## 开发与测试

```bash
python -m unittest discover -s tests -v
python scripts/validate.py examples/chengdu-2026-09-18.json --pretty --fail-on-warn
python scripts/test_day_route_urls.py
```

`scripts/seed_prices.py` 只用于旧数据迁移或演示。它产生的 `demo-estimate` / `note-derived` 来源不会通过严格价格校验，不能冒充实时调研。

## 文档

| 文档 | 内容 |
| --- | --- |
| [SKILL.md](SKILL.md) | Agent 必须遵守的主工作流 |
| [data-sources.md](references/data-sources.md) | 五类信息源、证据优先级与降级 |
| [planning.md](references/planning.md) | 行程编排方法 |
| [hotel-planning.md](references/hotel-planning.md) | 酒店选址与换住判断 |
| [validation-rules.md](references/validation-rules.md) | V0–V13 规则 |
| [deployment.md](references/deployment.md) | 本地交付与可选公开发布 |
| [setup-guide.md](references/setup-guide.md) | 用户明确要求时的能力配置 |
| [trip-schema.json](references/trip-schema.json) | 核心 JSON Schema |

## 限制

- 第三方价格、营业状态和天气会变化，出发前应再次核对；
- 校验脚本能验证结构和部分数值关系，不能证明外部查询真的发生过；
- 攻略内容是软信号，不代表官方事实或对每个人都适用；
- 路线与地图服务受对应平台配额、覆盖范围和服务条款限制。

## License

[MIT](LICENSE)
