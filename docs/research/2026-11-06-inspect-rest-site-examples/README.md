# inspect_rest_site 当前完整返回

以下均来自隔离游戏和真实MCP structuredContent，基线2e0037b、Mod0.71.2、MCP0.73.2。含15份full、一份default，没有图像内容。场景目录、问题和建议见[审阅记录](../2026-11-06-inspect-rest-site-review.md)。

错误样本分别展示首次失败和已有许可时的恢复方式；普通、灰置、帐篷、追加奖励与空选项是内容变体，返回结构一致。

| 文件 | 调用参数 | 场景标记 |
| --- | --- | --- |
| [basic.full.json](basic.full.json) | `{"preset": "full"}` | basic_initial |
| [basic.default.json](basic.default.json) | `{"preset": "default"}` | basic_default |
| [disabled.full.json](disabled.full.json) | `{"preset": "full"}` | disabled_initial |
| [tent.full.json](tent.full.json) | `{"preset": "full"}` | tent_initial |
| [tent-after-lift.full.json](tent-after-lift.full.json) | `{"preset": "full"}` | tent_after_lift |
| [dig.full.json](dig.full.json) | `{"preset": "full"}` | dig_initial |
| [heal-with-reward.full.json](heal-with-reward.full.json) | `{"preset": "full"}` | heal_rewards_initial |
| [activity-complete.full.json](activity-complete.full.json) | `{"preset": "full"}` | activity_complete |
| [after-selection-cancel.full.json](after-selection-cancel.full.json) | `{"preset": "full"}` | after_selection_cancel |
| [after-reward.full.json](after-reward.full.json) | `{"preset": "full"}` | after_nested_reward |
| [no-rest-first-read.full.json](no-rest-first-read.full.json) | `{"preset": "full"}` | no_rest_first_read |
| [no-rest-existing-permission.full.json](no-rest-existing-permission.full.json) | `{"preset": "full"}` | no_rest_existing_permission |
| [map-covered.full.json](map-covered.full.json) | `{"preset": "full"}` | map_covered |
| [deck-covered.full.json](deck-covered.full.json) | `{"preset": "full"}` | deck_covered |
| [selection-covered.full.json](selection-covered.full.json) | `{"preset": "full"}` | selection_covered |
| [reward-covered.full.json](reward-covered.full.json) | `{"preset": "full"}` | reward_covered |

来源数组位置和SHA-256见[manifest](manifest.json)。CLONE、HATCH、多人MEND及第三方选项未新增实际样本；对应源码与边界见[开发核验](../2026-11-06-inspect-rest-site-development-notes.md)。
