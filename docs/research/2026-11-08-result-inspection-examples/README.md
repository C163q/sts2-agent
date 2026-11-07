# 结算查看与展示状态实际返回

Mod0.79.0、MCP0.81.0、schema47；36份未裁剪MCP structuredContent。预设数量：{'full': 24, 'default': 1, 'summary': 11}。参数、证据行及SHA-256见[manifest.json](manifest.json)。

历史页使用现有原生页面测试夹具，本版本正常入口禁用；其余为对应隔离对局的原生流程及明确标记的测试状态注入。来源与边界见[实施记录](../2026-11-08-result-inspection-implementation.md)。

| 文件 | 场景 |
| --- | --- |
| [victory-outcome.full.json](victory-outcome.full.json) | 胜利首屏 |
| [victory-summary.full.json](victory-summary.full.json) | 胜利汇总完整详情 |
| [victory-summary.summary.json](victory-summary.summary.json) | 汇总摘要保留名称与标题 |
| [outcome-partial.full.json](outcome-partial.full.json) | 展示中允许读取且标记not_ready |
| [summary-partial.summary.json](summary-partial.summary.json) | 摘要保留展示中提示 |
| [summary-disabled.full.json](summary-disabled.full.json) | 完整展示但按钮禁用仍visible |
| [timeline.full.json](timeline.full.json) | 时间线原生说明 |
| [timeline.summary.json](timeline.summary.json) | 时间线摘要标题 |
| [epoch.full.json](epoch.full.json) | 当前章节完整文字 |
| [epoch.summary.json](epoch.summary.json) | 摘要保留章节文字 |
| [unlock-cards.full.json](unlock-cards.full.json) | 已解锁卡牌完整效果 |
| [unlock-cards.summary.json](unlock-cards.summary.json) | 已解锁卡牌摘要 |
| [unlock-cards-partial.full.json](unlock-cards-partial.full.json) | 展示中省略暂不可悬停解释 |
| [unlock-potions.full.json](unlock-potions.full.json) | 药水完整效果 |
| [unlock-potions.summary.json](unlock-potions.summary.json) | 药水摘要仅名称 |
| [unlock-relics.full.json](unlock-relics.full.json) | 遗物完整效果 |
| [unlock-relics.summary.json](unlock-relics.summary.json) | 遗物摘要仅名称 |
| [observation-cards.full.json](observation-cards.full.json) | 基础观察full使用face卡牌 |
| [observation-cards.default.json](observation-cards.default.json) | 基础观察default使用face卡牌 |
| [observation-cards.summary.json](observation-cards.summary.json) | 基础观察使用共用卡牌摘要 |
| [observation-timeline.full.json](observation-timeline.full.json) | 基础观察也保留时间线提示标题 |
| [tutorial.full.json](tutorial.full.json) | 时间线教程 |
| [death-outcome.full.json](death-outcome.full.json) | 原生失败首屏 |
| [death-summary.full.json](death-summary.full.json) | 失败汇总 |
| [death-summary.summary.json](death-summary.summary.json) | 失败汇总摘要 |
| [history.full.json](history.full.json) | 原生本局详情测试夹具 |
| [history.summary.json](history.summary.json) | 本局详情摘要 |
| [wrong-room.full.json](wrong-room.full.json) | 错误房间的具体原因 |
| [direct-end-turn.full.json](direct-end-turn.full.json) | 读取拒绝后直接结束回合 |
| [menu.full.json](menu.full.json) | 已离开结算的菜单拒绝 |
| [unowned-timeline.full.json](unowned-timeline.full.json) | 无关时间线拒绝 |
| [event-partial.full.json](event-partial.full.json) | 事件主体not_ready |
| [ancient-disabled.full.json](ancient-disabled.full.json) | 先古主体visible且按钮禁用 |
| [treasure-partial.full.json](treasure-partial.full.json) | 宝箱主体not_ready |
| [divination-partial.summary.json](divination-partial.summary.json) | 占卜主体not_ready |
| [epilogue-partial.full.json](epilogue-partial.full.json) | 建筑师主体not_ready |
