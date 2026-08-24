<div align="center">

# travel-planner

**把实时旅行信息变成能直接阅读、也能保存分享的可执行行程**

[![CI](https://github.com/SquirrelSong5/travel-planner-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/SquirrelSong5/travel-planner-skill/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[在线预览](https://squirrelsong5.github.io/travel-plans/chengdu-2026-09-18.html) ·
[快速开始](#快速开始) ·
[信息源](#现在有哪几个信息源) ·
[文档](#文档)

</div>

`travel-planner` 是面向中国大陆行程的 AI Agent Skill。它组织 POI、官方通知、路线、酒店、餐厅、价格和预订事项，基于同一份结构化数据同时生成对话版攻略与响应式单文件 HTML，并用脚本检查路线、时间、预算和来源字段。

对话版攻略和 HTML 是同等重要的必选交付：前者无需打开文件即可使用，后者适合离线保存和分享。公开网页链接只是可选的额外交付。

## 能做什么

- 基于日期、人数、预算、偏好和已订交通规划多日行程；
- 用实时来源核对开放时间、预约、票价、坐标和通勤；
- 按区域组织每天路线，处理酒店往返与末日返程缓冲；
- 给餐厅主选、备选、位置与价格证据；
- 从同一 JSON 确定性生成对话版攻略和手机可读的单文件 HTML；
- 管理预订状态、行前复核、Plan B 和针对性安全提醒；
- 对改酒店、换景点、延长日期等请求做增量更新；
- 用 V0–V13 规则阻止缺字段、过期事实、假来源、不可行路线和错误预订链接。

## 现在有哪几个信息源

当前主模型包含 **5 类信息源**：

| 信息源 | 主要提供什么 | 使用方式 |
| --- | --- | --- |
| 高德地图 | POI、坐标、路线、距离、通勤时长 | 地理与路线硬数据 |
| 官方与运营方渠道 | 营业/闭馆、预约、票务、临时通知、天气、公共交通规则 | 硬事实最高优先级 |
| 携程等国内 OTA | 酒店、机票、火车、实时价格区间与国内预订深链 | 价格与预订 |
| 小红书 | 分区、节奏、排队、拍照、近期踩雷 | 可选体验信号 |
| 美团攻略 | 城市餐厅候选、菜系与场景化推荐 | 可选餐饮候选池 |

网页搜索、Playwright、WebFetch 和 MCP 是获取信息的方式，不是独立信息源；GitHub Pages 等静态托管是交付渠道，也不是信息源。搜索摘要只用于发现，硬事实尽量回到原始官方页面。

大众点评已移出默认链路。只有用户明确要求，且当前环境已经具备合规访问能力时，才作为补充信号；项目不会要求安装扩展、扫码登录或绕过反爬。

更完整的证据优先级和降级策略见 [references/data-sources.md](references/data-sources.md)。

## 工作流

1. 归一化目的地、日期、人数、预算、偏好和已订项目；
2. 先查官方硬事实，再查地图与 OTA；
3. 用小红书/美团发现候选，不让攻略覆盖官方结论；
4. 按区域和固定时段排日程，实查主要通勤；
5. 写入来源、价格、预订状态、Plan B、安全提醒和复核节点；
6. 严格校验，包括 V12 信息时效性，修到没有失败和警告；
7. 从同一份 JSON 确定性生成 Markdown 攻略并渲染 HTML；
8. 在同一回复中交付两者，按用户选择额外公开发布。

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
python scripts/validate.py examples/chengdu-2026-09-18.json --pretty --fail-on-warn --as-of 2026-08-24

python scripts/render_markdown.py \
  examples/chengdu-2026-09-18.json \
  -o /tmp/chengdu-trip.md

python scripts/render_html.py \
  assets/template.html \
  examples/chengdu-2026-09-18.json \
  -o /tmp/chengdu-trip.html
```

不需要第三方 Python 包。交互地图的高德 Web Key 由浏览者在页面内输入，仅保存在当前浏览器；Key 不应放入 URL、HTML、JSON 或 Git 仓库。

示例固定使用 `--as-of 2026-08-24` 以保证回归测试可复现；规划真实行程时不要传该参数，V12 应按当天判断哪些信息需要重查。

## 输出与隐私

每次必须同时交付：

- **对话版攻略**：由 `render_markdown.py` 生成，在聊天中直接呈现完整日程、交通、餐饮、预算、预约、Plan B、安全提醒和行前复核；
- **`trip.html`**：包含相同核心行程事实、可离线打开的单文件行程页。

`trip.json` 是两种输出共同的数据源和后续修改底稿，可一并提供，但不替代以上任一输出。修改已有方案后，两种输出都要从最新 JSON 重新生成，不能只更新其中一种。

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
├── scripts/render_markdown.py   # 确定性生成对话版攻略
├── scripts/render_html.py       # 安全注入 JSON 并渲染 HTML
├── scripts/add_hotel_legs.py    # 显式补酒店通勤
└── tests/                        # 回归测试
```

## 开发与测试

```bash
python -m unittest discover -s tests -v
python scripts/validate.py examples/chengdu-2026-09-18.json --pretty --fail-on-warn --as-of 2026-08-24
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
| [recheck-and-safety.md](references/recheck-and-safety.md) | 行前复核、现场调整与安全提醒 |
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
