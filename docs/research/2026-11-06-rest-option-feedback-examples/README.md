# 火堆修复与遗物计数的实际返回

Mod0.73.0／MCP0.75.0／schema42。以下均为真实stdio MCP公开返回，未拼接预期字段；[manifest](manifest.json)记录调用参数、证据行与SHA-256。原审阅样本保持原样。

| 样本 | 工具 | 参数 |
| --- | --- | --- |
| [no_rest.full.json](no_rest.full.json) | choose_rest_option | `{"preset": "full", "option_id": "HEAL"}` |
| [no_rest_direct_continuation.full.json](no_rest_direct_continuation.full.json) | end_turn | `{"preset": "full"}` |
| [no_initial_permission.full.json](no_initial_permission.full.json) | choose_rest_option | `{"preset": "full", "option_id": "HEAL"}` |
| [local_invalid.full.json](local_invalid.full.json) | choose_rest_option | `{"preset": "full", "option_id": ""}` |
| [map_covered.full.json](map_covered.full.json) | choose_rest_option | `{"preset": "full", "option_id": "HEAL"}` |
| [deck_covered.full.json](deck_covered.full.json) | choose_rest_option | `{"preset": "full", "option_id": "HEAL"}` |
| [wrong_case.full.json](wrong_case.full.json) | choose_rest_option | `{"preset": "full", "option_id": "heal"}` |
| [unknown_option.full.json](unknown_option.full.json) | choose_rest_option | `{"preset": "full", "option_id": "UNKNOWN"}` |
| [heal.full.json](heal.full.json) | choose_rest_option | `{"preset": "full", "option_id": "HEAL"}` |
| [already_consumed.full.json](already_consumed.full.json) | choose_rest_option | `{"preset": "full", "option_id": "HEAL"}` |
| [disabled_smith.full.json](disabled_smith.full.json) | choose_rest_option | `{"preset": "full", "option_id": "SMITH"}` |
| [disabled_cook.full.json](disabled_cook.full.json) | choose_rest_option | `{"preset": "full", "option_id": "COOK"}` |
| [heal_default.default.json](heal_default.default.json) | choose_rest_option | `{"preset": "default", "option_id": "HEAL"}` |
| [smith.full.json](smith.full.json) | choose_rest_option | `{"preset": "full", "option_id": "SMITH"}` |
| [selection_covered.full.json](selection_covered.full.json) | choose_rest_option | `{"preset": "full", "option_id": "HEAL"}` |
| [heal_reward.full.json](heal_reward.full.json) | choose_rest_option | `{"preset": "full", "option_id": "HEAL"}` |
| [reward_covered.full.json](reward_covered.full.json) | choose_rest_option | `{"preset": "full", "option_id": "SMITH"}` |
| [smith-confirm.full.json](smith-confirm.full.json) | selection_option | `{"preset": "full", "option_id": "confirm"}` |
| [multi-confirm.full.json](multi-confirm.full.json) | selection_option | `{"preset": "full", "option_id": "confirm"}` |
| [cook.full.json](cook.full.json) | choose_rest_option | `{"preset": "full", "option_id": "COOK"}` |
| [cook-confirm.full.json](cook-confirm.full.json) | selection_option | `{"preset": "full", "option_id": "confirm"}` |
| [lift.full.json](lift.full.json) | choose_rest_option | `{"preset": "full", "option_id": "LIFT"}` |
| [kindle.full.json](kindle.full.json) | choose_rest_option | `{"preset": "full", "option_id": "KINDLE"}` |
| [dig.full.json](dig.full.json) | choose_rest_option | `{"preset": "full", "option_id": "DIG"}` |
| [dig-nested.full.json](dig-nested.full.json) | choose_rest_option | `{"preset": "full", "option_id": "DIG"}` |
| [dig-transform.full.json](dig-transform.full.json) | choose_rest_option | `{"preset": "full", "option_id": "DIG"}` |
| [transform-confirm.full.json](transform-confirm.full.json) | selection_option | `{"preset": "full", "option_id": "confirm"}` |
| [combat-victory.full.json](combat-victory.full.json) | play_card | `{"preset": "full", "card_id": 2, "target_id": 3}` |
| [no_hover-rejected.full.json](no_hover-rejected.full.json) | choose_rest_option | `{"preset": "full", "option_id": "HEAL"}` |
| [offscreen-rejected.full.json](offscreen-rejected.full.json) | choose_rest_option | `{"preset": "full", "option_id": "HEAL"}` |

[实施与验证](../2026-11-06-rest-option-feedback-implementation.md)说明范围、失败验证和边界。
