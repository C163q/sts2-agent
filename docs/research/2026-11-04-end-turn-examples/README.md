# end_turn 完整返回示例

核验结论见[专项审阅](../2026-11-04-end-turn-review.md)。调用参数、原始证据位置、条目下标和 SHA-256 见 [manifest](manifest.json)。

本目录所有 JSON 均为当前构建的真实 MCP structuredContent，逐次核对其与文字 JSON 一致；未补字段、未删事件、未用省略号替换内容。

`normal-next-turn.default.json` 是随后另一次结束回合，不能据它与前一个 full 的事件差异判断预设行为。超时、中断和缓冲截断只做模拟／源码核验，未伪造成游戏实测示例。

| 完整示例 | 内容 |
| --- | --- |
| [normal.full.json](normal.full.json) | 普通回合 |
| [normal-next-turn.default.json](normal-next-turn.default.json) | 无需重新观察，直接结束下一回合；不是同一回合的预设对比 |
| [wither.full.json](wither.full.json) | 结束回合时卡牌损血 |
| [wither_death.full.json](wither_death.full.json) | 卡牌损血导致战败 |
| [enemy_death.full.json](enemy_death.full.json) | 敌方攻击导致战败 |
| [tyranny.full.json](tyranny.full.json) | 下回合开始时选牌 |
| [retain_choice.full.json](retain_choice.full.json) | 结束回合时保留选牌 |
| [boulder.full.json](boulder.full.json) | 结束回合效果导致战胜 |
| [doom.full.json](doom.full.json) | 灾厄处决导致战胜 |
| [stampede.full.json](stampede.full.json) | 自动出牌导致战胜 |
| [revive.full.json](revive.full.json) | 死亡后等待复活的普通回合 |
| [revive-following-3.full.json](revive-following-3.full.json) | 后续回合中的复活 |
| [blocked.full.json](blocked.full.json) | 格挡抵消伤害 |
| [hellraiser.full.json](hellraiser.full.json) | 回合开始抽牌并自动出牌 |
| [exhaust_block.full.json](exhaust_block.full.json) | 消耗牌触发格挡 |
| [hidden_hp.full.json](hidden_hp.full.json) | 无限生命显示的敌人 |
| [thieving_hopper.full.json](thieving_hopper.full.json) | 偷窃草蜢首回合 |
| [handoff.full.json](handoff.full.json) | 同一动作切换战斗 |
| [eye.full.json](eye.full.json) | 佩尔之眼额外回合 |
| [error-no-observation.json](error-no-observation.json) | 首次没有观察许可 |
| [error-main-menu.json](error-main-menu.json) | 主菜单不能结束回合 |
| [error-deck.json](error-deck.json) | 牌组覆盖拒绝 |
| [error-draw.json](error-draw.json) | 抽牌堆覆盖拒绝 |
| [error-map.json](error-map.json) | 地图覆盖拒绝 |
| [error-rejection-loses-permission.json](error-rejection-loses-permission.json) | 明确拒绝后仍要求重新观察 |
| [error-event.json](error-event.json) | 非战斗事件不能结束回合 |
| [error-event-next-action.json](error-event-next-action.json) | 事件合法选项被观察前置阻挡 |
| [error-choice.json](error-choice.json) | 选牌期间不能结束回合 |
| [error-choice-next-action.json](error-choice-next-action.json) | 合法选牌被观察前置阻挡 |
| [error-summary.json](error-summary.json) | 本地参数错误，不发 IPC |
| [error-extra-field.json](error-extra-field.json) | 本地参数错误，不发 IPC |
| [error-null-preset.json](error-null-preset.json) | 本地参数错误，不发 IPC |
| [terminal-won-turn.full.json](terminal-won-turn.full.json) | 胜负回执清空可用工具，但未重新观察也能查看遗物 |
| [terminal-won-direct-relics.full.json](terminal-won-direct-relics.full.json) | 胜负回执清空可用工具，但未重新观察也能查看遗物 |
| [terminal-lost-turn.full.json](terminal-lost-turn.full.json) | 胜负回执清空可用工具，但未重新观察也能查看遗物 |
| [terminal-lost-direct-relics.full.json](terminal-lost-direct-relics.full.json) | 胜负回执清空可用工具，但未重新观察也能查看遗物 |
