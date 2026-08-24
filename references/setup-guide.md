# 可选能力配置

只有用户明确要求配置环境时才使用本文。不同 Agent 宿主的配置格式变化很快，应优先查对应产品的官方文档，不要照搬其他客户端命令。

## 安装 travel-planner

推荐使用通用的 Skills CLI。项目级安装：

```bash
npx skills add SquirrelSong5/travel-planner-skill
```

全局安装：

```bash
npx skills add SquirrelSong5/travel-planner-skill --global
```

安装器只负责把 Skill 文件放到目标 Agent 能发现的位置，不会配置地图 Key、浏览器账号或第三方 MCP。`npx` 只用于安装；travel-planner 自身的验证和渲染脚本没有 npm 运行时依赖。

## 最小可用配置

运行仓库内的验证、渲染和测试只需要：

- Python 3.10+；
- 一个能打开本地 HTML 的现代浏览器。

```bash
python scripts/validate.py examples/chengdu-2026-09-18.json --pretty --fail-on-warn --as-of 2026-08-24
python scripts/render_markdown.py examples/chengdu-2026-09-18.json -o /tmp/trip.md
python scripts/render_html.py assets/template.html examples/chengdu-2026-09-18.json -o /tmp/trip.html
```

## 可选能力

| 能力 | 作用 | 不可用时 |
| --- | --- | --- |
| 高德地图 MCP 或 REST | POI、坐标、路线、时长 | 路线标待核验，不伪造实算来源 |
| 网页搜索/浏览 | 官方通知、OTA、攻略 | 只做可验证范围内的草案 |
| 已有静态托管或文件分享能力 | 可选公开 URL | 交付本地 Markdown/HTML，不阻塞规划 |
| 小红书访问能力 | 近期体验软信号 | 跳过，不阻塞基础规划 |

Playwright 是一种浏览工具，不是 travel-planner 的强制依赖。美团攻略可以通过当前环境已有的网页能力访问。大众点评不需要配置。

## 推荐安装的配套 Skill

没有配套 Skill 是 travel-planner 的硬依赖。只有用户希望实际读取小红书近期内容，且当前环境没有等价能力时，才推荐安装：

```bash
npx skills add autoclaw-cc/xiaohongshu-mcp-skills --skill xiaohongshu
```

该项目还需要单独运行 `xiaohongshu-mcp` 并完成登录。安装前应让用户知道：

- 它会访问用户自己的小红书登录状态；
- 登录、验证码或扫码必须由用户本人完成；
- 不应把 Cookie、Token 或登录信息写入行程 JSON、HTML 或仓库；
- 用户不愿登录或能力不可用时，在 `source_coverage` 标为 `unavailable` 并继续规划。

网页搜索/浏览器通常是宿主能力，高德提供的是 MCP Server，都不应包装成 travel-planner 的 npm 依赖。不要为了凑齐来源自动安装扩展或第三方工具。

## 高德地图

优先使用宿主已提供的高德工具。若用户选择配置，先参考[高德地图 MCP Server 官方快速接入](https://lbs.amap.com/api/mcp-server/gettingstarted)：

1. 让用户在高德开放平台自行创建应用与 Key；
2. 按当前宿主的官方 MCP 配置文档添加服务；
3. 不要求用户把 Key 发到公共对话或写进仓库；
4. 用一次 POI 查询和一次路线查询验证能力；
5. 记录实际可用的工具名，不假设固定前缀。

若使用 REST，将 Key 放在本地环境变量中。仓库脚本 `add_hotel_legs.py` 支持 `AMAP_MCP_KEY` 或 `MCP_AMAP_API_KEY`，但不要提交包含 Key 的配置文件。

## HTML 地图 Key

浏览器地图使用高德 Web Key，与服务端 REST/MCP Key 可能不是同一类型。用户在渲染页面内输入，Key 只保存在该浏览器的 `localStorage`。不要把 Key 拼进 URL。

## GitHub 发布

GitHub 仅在用户需要公开分享时配置。先确认：

- 仓库所有者与仓库名；
- 页面是否允许公开；
- 要发布的文件路径；
- 页面中是否需要删除酒店、日期或返程信息。

具体发布约束见 [deployment.md](deployment.md)。

## 验收清单

- 地图查询返回了真实 POI 坐标；
- 路线查询返回了方式和时长；
- HTML 打开后不需要 URL 中的 Key；
- Key 没有出现在 `git diff`、JSON 或 HTML；
- 缺失的可选来源被明确标注，而不是伪装成已启用。
