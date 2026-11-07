# 事件选择修复后典型返回

以下18份为隔离游戏中真实MCP stdio返回的完整structuredContent；一份为default，其余为full。场景由测试夹具准备，交互使用原生按钮。
无效ID、锁定及覆盖拒绝后，后续合法操作直接执行；中间直接原生状态核对不刷新MCP许可。

调用参数、源报告行（从0开始）及SHA-256见[manifest](manifest.json)，验证范围见[实施记录](../2026-11-07-event-option-recovery-implementation.md)。

| 完整JSON | 场景 |
| --- | --- |
| [event-next-page.full.json](event-next-page.full.json) | 缺失ID拒绝后直接选择，记录生命变化 |
| [event-finished.default.json](event-finished.default.json) | 旧页面ID被拒后直接完成事件 |
| [upgrade-selection.full.json](upgrade-selection.full.json) | 进入升级选牌 |
| [card-rewards.full.json](card-rewards.full.json) | 扣血后打开奖励页 |
| [confirmation.full.json](confirmation.full.json) | 打开Trial确认框 |
| [divination.full.json](divination.full.json) | 付费后打开占卜 |
| [combat-selection.full.json](combat-selection.full.json) | 战斗进入后首回合选牌 |
| [combat-ready.full.json](combat-ready.full.json) | 战斗进入后玩家可行动 |
| [run-lost.full.json](run-lost.full.json) | 危险选项导致整局失败 |
| [fairy-rescue.full.json](fairy-rescue.full.json) | 瓶中精灵救活后继续事件 |
| [missing-option.full.json](missing-option.full.json) | 无效ID的具体原因与恢复 |
| [locked-option.full.json](locked-option.full.json) | 锁定选项的具体原因与恢复 |
| [deck-covered.full.json](deck-covered.full.json) | 牌组覆盖的具体原因与恢复 |
| [finished-event.full.json](finished-event.full.json) | 事件已完成时提示proceed |
| [selection-after-rejection.full.json](selection-after-rejection.full.json) | 拒绝事件操作后直接选择卡牌 |
| [reward-after-rejection.full.json](reward-after-rejection.full.json) | 拒绝事件操作后直接领取奖励 |
| [cancel-after-rejection.full.json](cancel-after-rejection.full.json) | 拒绝事件操作后直接取消确认框 |
| [no-event.full.json](no-event.full.json) | 非事件场景的具体拒绝与恢复 |
