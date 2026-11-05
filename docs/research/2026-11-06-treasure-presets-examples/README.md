# 宝箱详情修复与 summary 完整返回

17 份真实 stdio MCP 完整 structuredContent，均无图片。不可悬停、离屏、隐藏与裁剪由双重测试门控人工注入，恢复后继续正常原生开箱／领取流程；不是自然游玩复现。实现、原生资料与完整验证范围见[实施记录](../2026-11-06-treasure-inspection-presets-implementation.md)。

原[14 份审阅样本](../2026-11-06-inspect-treasure-examples/README.md)保持为修复前基线。每份的实际参数、来源及 SHA-256 见 [manifest.json](manifest.json)。

| 完整 JSON | 场景 |
| --- | --- |
| [closed.full.json](closed.full.json) | 未开箱 full |
| [closed.summary.json](closed.summary.json) | 未开箱 summary 保留 relic:null |
| [opened.full.json](opened.full.json) | 已开箱 full，正文与关键词 |
| [opened.summary.json](opened.summary.json) | 已开箱静态 summary |
| [empty.summary.json](empty.summary.json) | 白银熔炉空箱 summary |
| [no-hover.full.json](no-hover.full.json) | 不可悬停：正文 null，提示来源明确 |
| [no-hover.default.json](no-hover.default.json) | 不可悬停 default：省略空正文，保留 note |
| [no-hover.summary.json](no-hover.summary.json) | 不可悬停 summary：只提供静态信息 |
| [offscreen.full.json](offscreen.full.json) | 人工离屏：保留读取，enabled:false |
| [offscreen.summary.json](offscreen.summary.json) | 人工离屏 summary |
| [hidden.full.json](hidden.full.json) | 图标隐藏：不提供身份 |
| [clipped.summary.json](clipped.summary.json) | 容器裁剪：不提供身份 |
| [map-covered.full.json](map-covered.full.json) | 地图覆盖的具体原因 |
| [selection-covered.full.json](selection-covered.full.json) | 选牌覆盖的具体原因 |
| [with-permission.full.json](with-permission.full.json) | 无宝箱页，仍保留已有许可 |
| [nested-relic.summary.json](nested-relic.summary.json) | 嵌套遗物 summary |
| [collected.full.json](collected.full.json) | 已领取 full |
