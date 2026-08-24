# 交付与发布

## 默认：本地文件

先校验，再渲染：

```bash
python scripts/validate.py trip.json --pretty --fail-on-warn
python scripts/render_html.py assets/template.html trip.json -o trip.html
```

交付 `trip.json` 与 `trip.html`。HTML 可直接在现代浏览器打开；没有地图 Key 时，文字行程、预算和预订信息仍可使用。

## 地图 Key

- Key 只能由浏览者在页面的 Key 输入框填写；
- 页面把 Key 保存到当前浏览器的 `localStorage`；
- 不使用 `?k=` URL 参数；
- 不把 Key 写进 HTML、JSON、提交记录、截图或聊天消息；
- 共享页面不等于共享 Key，每台设备自行配置。

## 公开发布前

GitHub Pages 通常是公开页面。发布前向用户说明页面可能包含：

- 出行城市和日期；
- 酒店名称与位置；
- 每日路线和返程时间；
- 预订项目与预算。

只有用户明确要求公开分享，并确认目标仓库与路径后才发布。不要硬编码仓库所有者、仓库名或域名。

## GitHub Pages 示例流程

在用户已经登录 GitHub 且明确授权发布的前提下：

1. 将渲染后的 HTML 写到用户指定仓库；
2. 使用 `main`/`docs` 或 GitHub Actions 作为 Pages 来源；
3. 等待部署完成；
4. 打开实际页面验证 HTTP 状态、标题和内容；
5. 返回经过验证的 URL。

不要从用户名猜仓库，不要自动创建公开仓库，也不要把私有行程复制到项目示例中。

## 更新与撤回

- 增量修改后重新校验和渲染；
- 用户要求同步公开页时，更新原路径，避免散落多个旧版本；
- 如果用户要求撤回，删除公开文件或关闭 Pages，并说明缓存可能短暂存在；
- 页面不再需要时，建议撤回含具体日期和酒店的信息。
