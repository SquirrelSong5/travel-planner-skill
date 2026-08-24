# 可选能力配置

只有用户明确要求配置环境时才使用本文。不同 Agent 宿主的配置格式变化很快，应优先查对应产品的官方文档，不要照搬其他客户端命令。

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

## 高德地图

优先使用宿主已提供的高德工具。若用户选择配置：

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
