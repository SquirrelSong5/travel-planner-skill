# 交付与发布

## 必选双交付

先校验，再渲染：

```bash
python scripts/validate.py trip.json --pretty --fail-on-warn
python scripts/render_markdown.py trip.json -o trip.md
python scripts/render_html.py assets/template.html trip.json -o trip.html
```

以已校验的 `trip.json` 为唯一数据源，把 `trip.md` 的完整内容放进对话，并在同一次最终回复中同时交付：

1. 可独立使用的完整对话版攻略；
2. 可离线打开的 `trip.html`。

两者同等重要。不要用简短说明、文件链接或公开 URL 代替对话版攻略，也不要因为已经在对话中给出攻略而省略 HTML。没有地图 Key 时，HTML 中的文字行程、预算和预订信息仍可使用。

交付前核对两种输出的日期、酒店、每日顺序、主要交通、预算和预订事项一致。若任一输出生成失败或仍是旧版本，先修复再结束任务。

## 地图 Key

- Key 只能由浏览者在页面的 Key 输入框填写；
- 页面把 Key 保存到当前浏览器的 `localStorage`；
- 不使用 `?k=` URL 参数；
- 不把 Key 写进 HTML、JSON、提交记录、截图或聊天消息；
- 共享页面不等于共享 Key，每台设备自行配置。

## 可选 URL 的选择顺序

公开 URL 不属于必选双输出。只有用户明确要求分享链接时，按以下顺序选择：

1. 使用当前环境已经连接、授权且能验证结果的静态托管能力；
2. 没有自动发布能力时，继续交付 HTML，并说明用户可手动上传；
3. 不自动安装 CLI、SDK，不要求用户为本次行程注册新账号。

| 已有条件 | 适合方式 | 说明 |
| --- | --- | --- |
| GitHub 已连接 | GitHub Pages | 适合长期链接和版本记录 |
| Cloudflare 已配置 | [Pages Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/) | 上传预构建文件，不要求 Git 集成 |
| 用户希望手动拖放 | [Netlify Drop](https://docs.netlify.com/start/quickstarts/netlify-drop-quickstart/) 或 [Vercel Drop](https://vercel.com/docs/drop) | 上传含 `index.html` 的目录即可 |
| 无任何托管能力 | 直接分享 `trip.html` | 最轻量，也更容易控制隐私 |

平台只是适配器。Skill 核心始终只生成 Markdown、JSON 和单文件 HTML，不包含平台 SDK、部署脚本或账号逻辑。

## 公开发布前

静态托管页面通常可能公开访问。发布前向用户说明页面可能包含：

- 出行城市和日期；
- 酒店名称与位置；
- 每日路线和返程时间；
- 预订项目与预算。

只有用户明确要求公开分享，并确认服务、可见性和目标路径后才发布。公开链接是双交付之外的附加项，发布失败不能阻止对话版攻略和 HTML 文件的交付。不要硬编码账号、仓库、项目名或域名。

## 平台中立发布流程

在用户已经连接所选服务且明确授权发布的前提下：

1. 将 `trip.html` 作为 `index.html` 或用户指定文件名上传；
2. 不上传 API Key、私密 JSON 或无关行程；
3. 等待托管服务返回部署结果；
4. 打开实际页面验证 HTTP 状态、标题和内容；
5. 返回经过验证的 URL。

不要从用户名猜项目，不要自动创建公开空间，也不要把私有行程复制到项目示例中。

## 更新与撤回

- 增量修改后重新校验，同时重生成对话版攻略和 HTML；
- 用户要求同步公开页时，更新原路径，避免散落多个旧版本；
- 如果用户要求撤回，删除公开文件或关闭对应部署，并说明缓存可能短暂存在；
- 页面不再需要时，建议撤回含具体日期和酒店的信息。
