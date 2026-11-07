# inspect_run_result 典型实际返回

审阅基线9b95886，Mod0.78.2、MCP0.80.2、schema46。19份未裁剪MCP实际返回：17份full、2份default；参数、原始证据行及SHA-256见[manifest.json](manifest.json)。

样例按不同页面结构选取，未覆盖所有角色、故事和解锁内容。history为现有测试夹具打开的原生页面，当前版本View Run按钮禁用。失败首屏／汇总和战斗拒绝来自未完成的准备尝试，其已成功读取部分与后续脚本误判分开记录，不能据此声称原报告整体通过。详见[开发核验](../2026-11-07-inspect-run-result-development-notes.md)；设计讨论见[审阅报告](../2026-11-07-inspect-run-result-review.md)。

| 文件 | 场景 |
| --- | --- |
| [victory-outcome.full.json](victory-outcome.full.json) | 胜利首屏 |
| [death-outcome.full.json](death-outcome.full.json) | 失败首屏 |
| [victory-summary.full.json](victory-summary.full.json) | 胜利汇总：徽章和发现悬停 |
| [death-summary.full.json](death-summary.full.json) | 失败汇总 |
| [tutorial.full.json](tutorial.full.json) | 首次时间线教程 |
| [timeline.full.json](timeline.full.json) | 时间线：仅一项待揭晓 |
| [timeline-expanded.full.json](timeline-expanded.full.json) | 时间线：已完成、未获得等图标的悬停 |
| [epoch.full.json](epoch.full.json) | 章节故事 |
| [unlock.full.json](unlock.full.json) | 非物品类解锁提示 |
| [unlock-cards.full.json](unlock-cards.full.json) | 三张已揭示卡牌 |
| [unlock-potions.full.json](unlock-potions.full.json) | 三瓶已揭示药水 |
| [unlock-relics.full.json](unlock-relics.full.json) | 三件已揭示遗物 |
| [history.full.json](history.full.json) | 当前版本禁用入口的原生本局详情测试夹具 |
| [wrong-room.full.json](wrong-room.full.json) | 已有许可时错误房间的拒绝 |
| [cold-wrong-room.full.json](cold-wrong-room.full.json) | 首次读取错误房间，不授予许可 |
| [menu.full.json](menu.full.json) | 已返回菜单，不再有本局结算 |
| [unowned-timeline.full.json](unowned-timeline.full.json) | 普通菜单中打开的时间线不属于本局结算 |
| [victory-outcome.default.json](victory-outcome.default.json) | 实际default首屏 |
| [timeline.default.json](timeline.default.json) | 实际default时间线 |
