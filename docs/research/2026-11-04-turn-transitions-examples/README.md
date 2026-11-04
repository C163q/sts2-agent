# 结束回合与牌堆移动实际返回

结论见[实施记录](../2026-11-04-turn-transitions-implementation.md)。所有文件均为最终测试构建的真实完整 MCP structuredContent，逐次核对与文字 JSON 一致，不补字段或删事件。调用参数、来源条目与 SHA-256 见 [manifest](manifest.json)。

full/default 文件名对应实际参数。default 仅省略手动 card_played.autoplay:false，事件 null 不变；没有 position。旧缺口样例仍留在原审阅目录，不混充修复后的结果。

| 完整示例 | 内容 |
| --- | --- |
| [headbutt_empty-play.full.json](headbutt_empty-play.full.json) | 头槌出牌，按实际候选停止并记录可见移动 |
| [headbutt_single-play.full.json](headbutt_single-play.full.json) | 头槌出牌，按实际候选停止并记录可见移动 |
| [headbutt_multiple-play.full.json](headbutt_multiple-play.full.json) | 头槌出牌，按实际候选停止并记录可见移动 |
| [headbutt-select.full.json](headbutt-select.full.json) | 选择防御后的 discard→draw，无 position |
| [headbutt-selection.full.json](headbutt-selection.full.json) | 完整候选及原生选择文字，文字不转换为移动位置 |
| [manual.default.json](manual.default.json) | default 省略手动出牌的 autoplay:false |
| [manual.full.json](manual.full.json) | full 保留手动出牌的 autoplay:false |
| [shining.full.json](shining.full.json) | 明耀打击回抽牌堆，伤害／星星变化保留 |
| [hatchet-play.full.json](hatchet-play.full.json) | 无休手斧出牌后进入弃牌 |
| [hatchet-turn.full.json](hatchet-turn.full.json) | 无休手斧从原来的堆回手，不能按来源误报成抽牌 |
| [hatchet_draw-play.full.json](hatchet_draw-play.full.json) | 无休手斧出牌后进入弃牌 |
| [hatchet_draw-turn.full.json](hatchet_draw-turn.full.json) | 无休手斧从原来的堆回手，不能按来源误报成抽牌 |
| [hatchet-headbutt.full.json](hatchet-headbutt.full.json) | 头槌将无休手斧从弃牌放回抽牌堆，为来源变体准备 |
| [knife.default.json](knife.default.json) | 刀刃陷阱及自动小刀，true 和来源保留，消耗不重复 |
| [end-turn-won.full.json](end-turn-won.full.json) | 胜负回执保留无需许可的查看工具 |
| [direct-relics-won.full.json](direct-relics-won.full.json) | 不重新观察直接查看遗物 |
| [no-action-permission-won.json](no-action-permission-won.json) | 查看工具列表不表示游戏动作许可已续接 |
| [end-turn-lost.full.json](end-turn-lost.full.json) | 胜负回执保留无需许可的查看工具 |
| [direct-relics-lost.full.json](direct-relics-lost.full.json) | 不重新观察直接查看遗物 |
| [no-action-permission-lost.json](no-action-permission-lost.json) | 查看工具列表不表示游戏动作许可已续接 |
| [rejected-selection.json](rejected-selection.json) | 具体原因且保留已有许可，可按已知信息继续合法操作 |
| [rejected-deck.json](rejected-deck.json) | 具体原因且保留已有许可，可按已知信息继续合法操作 |
| [rejected-map.json](rejected-map.json) | 具体原因且保留已有许可，可按已知信息继续合法操作 |
| [rejected-event.json](rejected-event.json) | 具体原因且保留已有许可，可按已知信息继续合法操作 |
| [direct-event-option.full.json](direct-event-option.full.json) | 误结束回合被拒后直接执行合法事件选项 |
