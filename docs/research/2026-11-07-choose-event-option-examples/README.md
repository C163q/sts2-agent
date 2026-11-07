# choose_event_option 典型返回

以下为提交450a041下新启动的隔离游戏实测，经实际MCP stdio获得的完整structuredContent。full保留实际空值；完成事件的一份使用default。
动作回执不包含整个事件、选牌、奖励或占卜主体；后续按需使用对应查看工具。
场景由测试夹具创建，选择均点击原生按钮；复活场景预置瓶中精灵，战斗选牌场景预置Choices Paradox。此处不代表自然流程随机抽中这些组合。

调用参数、源报告行（从0开始）、原始响应路径与SHA-256见[manifest](manifest.json)。证据及未验证范围见[开发核验](../2026-11-07-choose-event-option-development-notes.md)。

| 完整JSON | 场景 | 调用参数 |
| --- | --- | --- |
| [event-next-page.full.json](event-next-page.full.json) | Abyssal Baths：最大生命与生命变化后翻页 | `{"preset": "full", "option_id": 0}` |
| [event-finished.default.json](event-finished.default.json) | Abyssal Baths：完成事件，下一步 proceed | `{"preset": "default", "option_id": 3}` |
| [upgrade-selection.full.json](upgrade-selection.full.json) | Aroma of Chaos：进入升级选牌 | `{"preset": "full", "option_id": 9}` |
| [card-rewards.full.json](card-rewards.full.json) | Brain Leech：扣血后打开奖励页 | `{"preset": "full", "option_id": 11}` |
| [confirmation.full.json](confirmation.full.json) | Trial：打开原生放弃确认框 | `{"preset": "full", "option_id": 15}` |
| [divination.full.json](divination.full.json) | Crystal Sphere：付费后打开占卜 | `{"preset": "full", "option_id": 16}` |
| [combat-selection.full.json](combat-selection.full.json) | 进入战斗，首回合自动效果要求选牌 | `{"preset": "full", "option_id": 20}` |
| [run-lost.full.json](run-lost.full.json) | 危险选项导致整局失败 | `{"preset": "full", "option_id": 21}` |
| [fairy-rescue.full.json](fairy-rescue.full.json) | 危险选项触发原生复活 | `{"preset": "full", "option_id": 23}` |
| [potion-rewards.full.json](potion-rewards.full.json) | Potion Courier：打开药水奖励页 | `{"preset": "full", "option_id": 27}` |
| [missing-option.full.json](missing-option.full.json) | 不存在的选项 ID 被拒绝 | `{"preset": "full", "option_id": 2147483647}` |
| [locked-option.full.json](locked-option.full.json) | 锁定选项被拒绝 | `{"preset": "full", "option_id": 7}` |
| [map-covered.full.json](map-covered.full.json) | 地图覆盖期间拒绝事件选择 | `{"preset": "full", "option_id": 0}` |
| [selection-covered.full.json](selection-covered.full.json) | 升级选牌期间拒绝事件选择 | `{"preset": "full", "option_id": 8}` |
| [after-rejection.full.json](after-rejection.full.json) | 被拒绝后改选合法选项，仍要求观察 | `{"preset": "full", "option_id": 5}` |
| [invalid-option.full.json](invalid-option.full.json) | 布尔值 ID 在 MCP 本地拒绝 | `{"preset": "full", "option_id": true}` |
