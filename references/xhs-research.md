# 小红书调研方法

> 移植自参考项目 trip-map-builder，适配本 skill 的 MCP 调用方式。
> 配套：`./dianping-research.md` 是硬信号源；本文件是软信号源。
>
> **v2.3.0**：小红书分两层——**Step 1.5 目的地攻略（必做、前置）** + **Round 3 店级软信号**。本节 §0 是前者；§2 起是后者。

---

## 0. Step 1.5：目的地攻略（必做，前置）

> **在 Step 2 清单分组之前完成**。先读攻略，再决定 POI 池和每天主区域。
> 不做点点 AI / Playwright 侧边栏抓取——用本 skill 的 `search-feeds` + `get-feed-detail` **自己聚合多篇笔记**，效果等价且更稳。

### 0.1 时机与输入

| 输入 | 来源 |
|------|------|
| 城市、天数、人群、主题 | Step 1 硬约束 |
| 用户必去 / 禁忌 | Step 1 |
| 官方闭馆、预约、季节 | Web search（与小红书并行） |

### 0.2 工作流（约 5–10 分钟）

```
① 定 2–3 个搜索词（含天数/人群）
      ↓
② search-feeds 粗筛 10–20 篇（sort_by=最多点赞，publish_time=半年内）
      ↓
③ 按 §3 筛选标准剔除噪音，留 5–8 篇
      ↓
④ get-feed-detail 精读 3–5 篇（load_all_comments 看避雷评论）
      ↓
⑤ Web search 补硬信息（闭馆、预约、天气季节）
      ↓
⑥ 写出 xhs_destination_brief（§0.4）→ 用户确认或默认可进 Step 2
```

**推荐关键词模板**：

```
{城市} {N}天 攻略
{城市} 避雷
{城市} 本地人推荐
{城市} {人群/主题}   # 如 毕业旅行、亲子、情侣
```

### 0.3 精读提取清单（目的地级）

与 §4 店级不同，目的地级优先提取：

| 类别 | 提取什么 |
|------|----------|
| **分区** | 「一天玩鼓浪屿」「别住曾厝垵」「住中山路方便」 |
| **必去** | 多篇重复出现的 POI/街区 |
| **避雷** | 「XX 全是游客」「雨天别去 XX」「排队 2h 不值」 |
| **节奏** | 松散/紧凑、上午/傍晚最佳时段 |
| **季节** | 梅雨季、暴晒、节假日人潮 |
| **交通印象** | 「租车没必要」「地铁够用」（供 Step 2 酒店区域参考） |

**不提取**：具体店名细节（留给 Round 3）、无法交叉验证的单篇暴论。

### 0.4 产出：`xhs_destination_brief`

**必须**在 chat 展示；**建议**写入 `tripData.xhs_destination_brief`（Step 6 一并进 HTML 元数据）。

```json
{
  "city": "厦门",
  "keywords_searched": ["厦门 4天 攻略", "厦门 避雷"],
  "source": "xiaohongshu-cli",
  "degraded": false,
  "must_visit": [
    { "name": "鼓浪屿", "why": "3/5 篇攻略列为 Day 独立区" },
    { "name": "八市", "why": "本地人海鲜+小吃，多篇避雷网红海鲜楼" }
  ],
  "skip_or_caution": [
    { "name": "曾厝垵住店", "why": "多篇称交通不便、过度商业化" }
  ],
  "region_layout": [
    "Day 型：中山路/八市（落地）",
    "Day 型：鼓浪屿（邮轮中心出发）",
    "Day 型：厦大/环岛路",
    "Day 型：沙坡尾+返程"
  ],
  "pace_hints": "每天 ≤3 POI；鼓浪屿须早班船减少排队",
  "weather_hints": "6–7 月梅雨季，户外段备室内 Plan B",
  "source_notes": [
    { "title": "厦门三天两夜不绕路", "url": "https://www.xiaohongshu.com/explore/..." }
  ],
  "web_search_supplement": "厦大需预约（官方公众号）"
}
```

**Chat 展示模板**（用户扫一眼即可）：

```md
## 📕 小红书目的地简报 · {城市}

**必纳入**（与用户禁忌无冲突）：
- {POI/区域} — {一句理由}

**谨慎 / 建议跳过**：
- {项} — {理由}

**分区建议**（供 Step 2）：
- {每天主区域草案}

**代表笔记**：{title1} · {title2} …

**Web 补充**：{闭馆/预约/季节硬信息}

> 数据来源：{xiaohongshu-cli | webfetch-degraded} · {N} 篇精读
```

### 0.5 降级（未装 xhs skill）

1. WebFetch `https://www.xiaohongshu.com/search_result?keyword={URL编码词}`（移动端 UA）
2. Web search：`{城市} 旅游攻略 site:xiaohongshu.com`
3. `tripData.xhs_destination_brief.degraded = true`，`source = "webfetch-degraded"`
4. **禁止**用 LLM 训练记忆冒充笔记结论

### 0.6 与 Round 3 店级调研的分工

| 层级 | 步骤 | 搜索词示例 | 目的 |
|------|------|-----------|------|
| **目的地** | Step 1.5 | `厦门 4天 攻略` | 分区、必去、避雷、节奏 |
| **店铺** | Round 3 | `小郡肝 排队` | 排队、踩雷、氛围 |

**不要**在 Round 3 重复搜「{城市} N天攻略」——应在 Step 1.5 已完成。

### 0.7 与验证规则

`xhs_destination_brief` **不进** `validate.py` 自动校验，但 Round 1 AI critique **必须**核对：

- `must_visit` 是否纳入 POI 池或已解释剔除
- `skip_or_caution` 是否误纳入行程
- 用户 V7 禁忌是否与 brief 冲突（冲突以用户为准）

---

## 1. 工具链

> **v1.0.2 起唯一方案**：`autoclaw-cc/xiaohongshu-skills`（Python CLI + Chrome 扩展）。
> 原 `xpzouying/xiaohongshu-mcp` 方案已弃用（部署 Docker/Go server 太重，本 skill 只需要搜索/详情）。

### 1.1 接入

- **CLI 路径**：`~/xhs-skill/scripts/cli.py`
- **Chrome 接入**：`scripts/chrome_launcher.py`（**v1.0.3 起，AI 跑这一行就完事——它会自动启 Chrome + 自动装 XHS Bridge 扩展 + 开 9222 调试端口**）
- **Bridge 通信**：`scripts/bridge_server.py`（CLI 和扩展之间的本地 WebSocket 中转，AI 不需要直接调）
- **登录入口**：`scripts/cdp_publish.py login`（AI 跑这一行，Chrome 弹出二维码让用户扫）
- **配置**：`references/setup-guide.md` §2

> **🔄 v1.0.3 关键洞察**：这个项目**自带 launcher**——`scripts/chrome_launcher.py` 是设计给 AI 用的。**别再让用户去 chrome://extensions 手装扩展**（那是给"想用日常 Chrome 复用 session"用户的备选路径）。

### 1.2 工具映射表（AI 调用对照）

| 用途 | 命令 |
|------|------|
| 登录检查 | `python scripts/cli.py check-login` |
| 关键词搜索 | `python scripts/cli.py search-feeds --keyword "..." [--sort_by ...]` |
| 首页推荐流 | `python scripts/cli.py list-feeds` |
| 帖子详情 | `python scripts/cli.py get-feed-detail --feed_id <ID> --xsec_token <TOKEN>` |
| 发图文 | `python scripts/cli.py publish-content --title ... --content ... --images ...` |
| 发视频 | `python scripts/cli.py publish-with-video --video ...` |
| 一级评论 | `python scripts/cli.py post-comment` |
| 二级回复 | `python scripts/cli.py reply-comment` |
| 点赞 / 取消 | `python scripts/cli.py like-feed` |
| 收藏 / 取消 | `python scripts/cli.py favorite-feed` |
| 用户主页 | `python scripts/cli.py user-profile` |

> **本 skill 的搜索流程只用前 4 行**（登录检查 / 搜索 / 详情）。其余 7 行供发版回程时使用。
>
> ⚠️ **`feed_id` 和 `xsec_token` 缺一不可**：`xsec_token` 由搜索/推荐列表返回，单独拿不到。

### 1.3 降级方案（没装 skill）

WebFetch 直接抓 `xiaohongshu.com`：
- 搜索页：`https://www.xiaohongshu.com/search_result?keyword=<关键词>`
- 详情页：`https://www.xiaohongshu.com/explore/<note_id>`

注意：移动端 UA 限制较少，建议在 WebFetch 时设置 User-Agent 为移动端。

---

## 2. 核心方法：两段式（粗筛 → 精读）

> **适用**：Step 1.5 目的地攻略 + Round 3 店级调研。目的地级见 §0；店级见 §8 关键词。

### 2.1 Step 1：粗筛（搜索结果页）

**不要模拟输入框** —— 直接进搜索结果路由。

```bash
python ~/xhs-skill/scripts/cli.py search-feeds \
  --keyword "<关键词>" \
  --sort_by "最多点赞" \
  --publish_time "半年内" \
  --note_type "图文"
```

**粗筛目标**：拿到 10-20 条候选笔记的 `feed_id` + `xsec_token` + `title`。

### 2.2 Step 2：精读（详情页）

只挑最相关的 2-3 条，读完整内容：

```bash
python ~/xhs-skill/scripts/cli.py get-feed-detail \
  --feed_id <ID> \
  --xsec_token <TOKEN> \
  --load_all_comments
```

**精读目标**：提取决策导向信息（见第 4 节）。

### 2.3 收益

- **快** —— 一次搜索 + 2-3 次详情，比逐页抓快 10 倍
- **抗风控** —— 走 MCP/API，不模拟 UI 操作
- **信号强弱先判断** —— 粗筛看笔记数 / 互动量，精读看内容质量
- **写回更干净** —— 只留决策结论，不搬原文

---

## 3. 笔记筛选标准

### 3.1 保留（真店信号）

✅ 店名 / 地址 / 菜品明确
✅ 有亲身体验（"我去吃了..."、"我点了..."、"我们点了..."）
✅ 关键信息在多条笔记里复现（"排队 2 小时" 在 3 条以上都出现）
✅ 近期（半年内发布）

### 3.2 不保留（噪音）

❌ 泛东京合集里顺带一句（"东京 5 日游：Day 1 浅草寺、Day 2 晴空塔、Day 3 银座... [某家店]"）
❌ 标题写酒店 / 散步，正文才提店（不专注）
❌ 明显搬运（无图无亲历，纯抄官网）
❌ 1 年前发布（参考价值衰减）
❌ 营销号痕迹明显（"探店"机构号 + 全是好评）

---

## 4. 信息提取清单（决策导向）

优先保留能帮决策的：

- **要不要排队** —— "排了 2 小时"、"工作日 5 分钟"、"周末别去"
- **主餐还是收尾** —— "适合当主餐"、"只能下午茶"
- **白天还是晚上** —— "夜景绝佳"、"午餐限定"
- **打卡还是稳饭** —— "拍照好看但味道一般"、"当地人常去"
- **容不容易踩空** —— "周一定休"、"现金 / 支付宝"、"要预约"
- **是否新开 / 装修** —— "2024 年新开"、"刚装修完味道大"

**不优先**：纯情绪、漂亮但无用的形容、复读三遍的"氛围很好"。

---

## 5. 写回格式（写到方案里）

只留一层结论，不搬原文：

```md
## {place_name} 小红书判断
- 代表笔记：[标题](URL)
- {信号 1}
- {信号 2}
- 软信号整体：{打卡型 / 稳饭型 / 避雷型}
```

**示例**：

```md
## 寿司 鮨青木 小红书判断
- 代表笔记：[银座隐藏 omakase 性价比](https://www.xiaohongshu.com/explore/xxx)
- 工作日午餐 6000 yen 起，无需排队
- 师傅英语 OK，外国游客友好
- 软信号整体：稳饭型（适合预算敏感）
```

---

## 6. 选店使用模式（与大众点评交叉）

| 任务 | 大众点评 | 小红书 |
|------|---------|--------|
| 评分 / 排队 / 踩雷 | ✅ 硬信号 | |
| 营业时间 / 休馆日 | ✅ | |
| 口味 / 价格 | ✅ | |
| 氛围 / 拍照 | | ✅ 软信号 |
| 近期体验 | | ✅ |
| 当地人偏好 | | ✅ |
| 网红 vs 稳饭 | | ✅ |
| 工作日 vs 周末 | 部分 | ✅ 更详细 |

**硬信号 + 软信号组合**：先大众点评筛评分，再小红书看氛围 / 拍照 / 当地人评价。

---

## 7. 避雷要点

1. **输入框不要碰** —— 走 `python scripts/cli.py search-feeds` / 降级 WebFetch `search_result` 路由
2. **不要只按互动量选** —— 互动高 ≠ 真口碑（可能是推广）
3. **不要把种草当硬口碑** —— 小红书只是软信号，营业时间要去官网
4. **不要忽略负面笔记** —— "踩雷"笔记可能比"安利"笔记更有价值
5. **跨店笔记不可当单店口碑** —— "东京 5 日 8 家必吃"里的某家，参考价值低

---

## 8. 典型搜索关键词

### 8.1 景点

```
"<景点名>" + "值得去吗"
"<景点名>" + "避雷"
"<景点名>" + "拍照"
"<景点名>" + "人多"
```

### 8.2 餐厅

```
"<店名>" + "排队"
"<店名>" + "踩雷"
"<店名>" + "工作日"
"<城市> <菜系>" + "必吃"
"<城市> <菜系>" + "当地人"
```

### 8.3 酒店

```
"<酒店名>" + "隔音"
"<酒店名>" + "新装修"
"<酒店名>" + "近地铁"
"<城市> <区域> 酒店" + "推荐"
```

---

## 9. 调用失败时的回退

如果 `python ~/xhs-skill/scripts/cli.py ...` 调用失败：

1. **WebFetch 搜索结果页**：能拿到前 10-20 条标题和作者
2. **WebFetch 详情页**：能拿到正文，但可能不全（登录墙）
3. **直接说"小红书数据缺失"**：用通用知识 + 大众点评 + 高德 POI 描述填补
4. **不建议**：让用户自己去看小红书（破坏 skill 自闭环）

---

## 10. 与 V1-V7 验证的关联

小红书数据**不直接参与 V1-V7 验证**，但影响：

| 验证规则 | 小红书的影响 |
|---------|------------|
| V3 餐厅区域匹配 | 小红书笔记确认餐厅确实在该区域（防"挂名"店） |
| V6 户外天气敏感 | 小红书笔记确认天气影响（如"雨天别来"） |
| V7 用户禁忌屏蔽 | 小红书笔记确认是否符合用户禁忌（"避雷" = "符合不要去"） |
