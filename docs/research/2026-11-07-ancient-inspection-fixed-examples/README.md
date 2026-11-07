# 先古详情修复后的实际返回

Mod0.78.0、MCP0.80.0、schema46；全部为实际MCP structuredContent，未裁剪字段。23份样本包含18份full、1份default、4份summary。参数、证据行、原生响应及哈希见[manifest.json](manifest.json)。

[实施与验证](../2026-11-07-ancient-inspection-presets-implementation.md)；[输出定稿](../2026-11-07-inspect-ancient-review.md#输出定稿)。

| 文件 | 场景 |
| --- | --- |
| [normal.full.json](normal.full.json) | 普通馈赠完整详情 |
| [normal.summary.json](normal.summary.json) | 保留馈赠正文的摘要 |
| [missing-ids.full.json](missing-ids.full.json) | 混合筛选与合并缺失ID |
| [empty-filter.full.json](empty-filter.full.json) | 空筛选保留对话及上下文 |
| [map-covered.full.json](map-covered.full.json) | 地图覆盖的具体原因 |
| [deck-covered.full.json](deck-covered.full.json) | 牌组覆盖的具体原因 |
| [wrong-room.full.json](wrong-room.full.json) | 首次错误读取不建立许可 |
| [continued.full.json](continued.full.json) | 已有许可时错误读取后直接结束回合 |
| [dialogue.full.json](dialogue.full.json) | 只显示已揭示台词及继续按钮 |
| [references.full.json](references.full.json) | 当前角色遗物和卡牌的引用 |
| [obtained.summary.json](obtained.summary.json) | 领取后保留前进按钮 |
| [selection-covered.full.json](selection-covered.full.json) | 选牌覆盖的具体提示 |
| [rewards-covered.full.json](rewards-covered.full.json) | 奖励覆盖的具体提示 |
| [safe.default.json](safe.default.json) | 安全选项在default保留false |
| [lethal.full.json](lethal.full.json) | 原生致死红框对应true |
| [lethal.summary.json](lethal.summary.json) | 摘要保留true警告 |
| [lethal-observation.full.json](lethal-observation.full.json) | 基础观察保留true警告 |
| [offscreen.full.json](offscreen.full.json) | 离屏馈赠仍完整可读且不可点击 |
| [no-hover.full.json](no-hover.full.json) | 无法悬停保留正文并给来源note |
| [no-hover-filtered.full.json](no-hover-filtered.full.json) | 筛选去掉无关悬停note |
| [no-hover.summary.json](no-hover.summary.json) | 摘要省略悬停正文及相关note |
| [hidden.full.json](hidden.full.json) | 真正隐藏的馈赠仍排除 |
| [clipped.full.json](clipped.full.json) | 真实裁剪的馈赠仍排除 |
