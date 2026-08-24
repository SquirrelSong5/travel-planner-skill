# 校验规则

`scripts/validate.py` 检查结构化行程中的可计算约束。它是质量门禁，不是外部证据审计器：`source: "amap-mcp"` 只能说明数据如何被标记，不能证明查询真的发生过。

## 运行

全量严格校验：

```bash
python scripts/validate.py trip.json --pretty --fail-on-warn
```

分阶段检查：

```bash
python scripts/validate.py trip.json --round 1 --pretty
python scripts/validate.py trip.json --round 2 --pretty
python scripts/validate.py trip.json --round 3 --pretty
```

指定规则：

```bash
python scripts/validate.py trip.json --check V0,V5,V8,V10 --pretty
```

V0 始终先运行；核心结构失败时，其余规则不会继续，以免无效数据触发误判。无失败时退出码为 0；有失败时为 1。加 `--fail-on-warn` 后，警告也返回 1。

## 规则表

| ID | 检查 | 典型失败或警告 |
| --- | --- | --- |
| V0 | 核心数据完整性 | 缺城市、日期、人数、day/POI 字段、坐标或 transport 端点 |
| V1 | 区域一致性 | 普通日 POI 离主区域中心过远 |
| V2 | 时间可行性粗算 | 通勤占比过高、停留时长缺失 |
| V3 | 餐厅区域匹配 | 主餐厅缺坐标，或既远离主区域又未列入当日路线 |
| V4 | 一日一重预约 | 同一天堆叠多个高风险预约项目 |
| V5 | 末日返程缓冲 | 末 POI 到返程票时间不足；优先识别“返程/回程/离开”票 |
| V6 | 户外天气敏感 | 恶劣天气下户外 POI 没有室内备选 |
| V7 | 用户禁忌 | 需 Agent 人工对照，脚本不自动判断 |
| V8 | 路线来源字段完整性 | 多 POI 日无 transports，或路线缺合法 source/duration |
| V9 | 通勤时间下限 | 声称的路线时长短于直线粗算的合理下限 |
| V10 | 价格溯源 | 价格缺 source/min/max，或使用 estimate/demo-estimate 等禁止来源 |
| V11 | 国内预订链接 | 使用 trip.com、Booking、Agoda 等国际 OTA 链接 |
| V12 | 信息时效性 | 缺核对时间/来源/复核节点，或临近出发仍使用过期事实 |
| V13 | 酒店早晚通勤 | 有酒店坐标但普通日缺酒店出发/回酒店段 |

V12 使用顶层 `rechecks` 清单。出发前 7 天会检查开放、预约、路线与价格是否近期核对；出发前 1 天会进一步检查天气和预警。

## 三个边界

### V2 不是路线查询

V2 用直线距离和典型速度做粗筛，只能发现明显过满的安排。主要移动段仍应查询地图服务，写入 `transports` 后由 V8/V9 检查字段与数值合理性。

### V3 允许路线型晚餐

餐厅可以不在主区域中心，只要它明确作为当日 POI 并参与路线。这样能支持“白天宽窄巷子，晚上回春熙路吃饭”等真实安排。

### V10 不接受演示估算

以下来源不能通过严格价格校验：

- `estimate`
- `demo-estimate`
- `note-derived`
- `ai-guess`
- `memory`

`scripts/seed_prices.py` 的输出需要重新做实时价格研究后才能交付。

## 人工复核

通过脚本后仍需检查：

- 是否真的访问了记录的来源；
- 官方临时通知是否晚于攻略或 OTA；
- 用户饮食禁忌、无障碍、老人儿童和步行能力；
- 预约是否需要实名、证件或特定放票时间；
- Plan B 是否写明触发条件、替代安排和路线影响；
- 安全提醒是否针对当前同行人和行程，且有可执行动作；
- 公开页面是否泄露不必要的日期、酒店和路线。
