# proceed 修复后实际完整返回

来源为隔离游戏与真实MCP structuredContent。基线、验证与限制见[实施记录](../2026-11-06-proceed-recovery-implementation.md)。

共26份返回：25份full、一份default；均无图片。错误样本保留实际error.code/message/recovery；内部未提交证明另留原始证据，不进入公开JSON。

shop-recovered是被拒后没有重新观察、直接调用close_shop的结果；terminal-no-permission是run_won后直接再次proceed的结果。

| 文件 | 工具与参数 | 场景标记 |
| --- | --- | --- |
| [combat-rejected.full.json](combat-rejected.full.json) | `proceed({"preset": "full"})` | no_proceed_in_combat |
| [map-covered.full.json](map-covered.full.json) | `proceed({"preset": "full"})` | reward_map_covered |
| [deck-covered.full.json](deck-covered.full.json) | `proceed({"preset": "full"})` | reward_deck_covered |
| [reward-skip.full.json](reward-skip.full.json) | `proceed({"preset": "full"})` | reward_skip |
| [reward-empty.default.json](reward-empty.default.json) | `proceed({"preset": "default"})` | empty_reward |
| [nested-return.full.json](nested-return.full.json) | `proceed({"preset": "full"})` | nested_reward_return |
| [closed-chest.full.json](closed-chest.full.json) | `proceed({"preset": "full"})` | closed_chest |
| [treasure-skip.full.json](treasure-skip.full.json) | `proceed({"preset": "full"})` | unclaimed_relic_skip |
| [rest-rejected.full.json](rest-rejected.full.json) | `proceed({"preset": "full"})` | unused_rest |
| [rest.full.json](rest.full.json) | `proceed({"preset": "full"})` | rest_leave |
| [shop-rejected.full.json](shop-rejected.full.json) | `proceed({"preset": "full"})` | shop_inventory_open |
| [shop-recovered.full.json](shop-recovered.full.json) | `close_shop({"preset": "full"})` | after_shop_rejection |
| [shop.full.json](shop.full.json) | `proceed({"preset": "full"})` | shop_leave |
| [event-rejected.full.json](event-rejected.full.json) | `proceed({"preset": "full"})` | unfinished_event |
| [event.full.json](event.full.json) | `proceed({"preset": "full"})` | event_leave |
| [ancient-rejected.full.json](ancient-rejected.full.json) | `proceed({"preset": "full"})` | unfinished_ancient |
| [ancient.full.json](ancient.full.json) | `proceed({"preset": "full"})` | ancient_leave |
| [divination-rejected.full.json](divination-rejected.full.json) | `proceed({"preset": "full"})` | unfinished_divination |
| [divination.full.json](divination.full.json) | `proceed({"preset": "full"})` | divination_leave |
| [next-act.full.json](next-act.full.json) | `proceed({"preset": "full"})` | next_act |
| [selection-covered.full.json](selection-covered.full.json) | `proceed({"preset": "full"})` | rest_selection_covered |
| [confirmation-covered.full.json](confirmation-covered.full.json) | `proceed({"preset": "full"})` | event_confirmation_covered |
| [architect-rejected.full.json](architect-rejected.full.json) | `proceed({"preset": "full"})` | architect_dialogue_not_finished |
| [run-won.full.json](run-won.full.json) | `proceed({"preset": "full"})` | architect_run_won |
| [terminal-no-permission.full.json](terminal-no-permission.full.json) | `proceed({"preset": "full"})` | terminal_has_no_permission |
| [result-rejected.full.json](result-rejected.full.json) | `proceed({"preset": "full"})` | result_requires_result_tool |

逐项来源、数组位置及SHA-256见[manifest](manifest.json)。修复前样本见[原审阅返回](../2026-11-06-proceed-examples/README.md)，保持原始基线。
