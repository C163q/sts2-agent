# 头槌 transition 核验样例

结论见[专项记录](../2026-11-04-headbutt-transition-review.md)。所有 JSON 均为真实 MCP 完整 structuredContent，逐次核对与文字 JSON 相同，未补字段或删事件。来源、参数、条目下标与哈希见 [manifest](manifest.json)。

构建仅新增测试场景以准备头槌；没有修改生产事件记录器。这些文件展示已复现的缺口，不表示已修复或期望最终保持此行为。

| 完整示例 | 内容 |
| --- | --- |
| [empty-play.full.json](empty-play.full.json) | 空弃牌堆，只有费用／出牌／伤害，没有移动也不应虚构移动 |
| [single-play.full.json](single-play.full.json) | 唯一弃牌自动放回；当前没有该牌移动事件 |
| [multiple-play.full.json](multiple-play.full.json) | 先完成伤害，再停在选牌边界 |
| [selection.full.json](selection.full.json) | 真实候选及明确的抽牌堆顶提示 |
| [select-card.full.json](select-card.full.json) | 完成选牌及移动，但当前 events 为空 |
| [after.full.json](after.full.json) | 移动后可见抽牌堆 1、弃牌堆 2 |
| [draw-after.full.json](draw-after.full.json) | 原生抽牌堆仅有防御 |
| [discard-after.full.json](discard-after.full.json) | 原生弃牌堆只有头槌和打击 |
