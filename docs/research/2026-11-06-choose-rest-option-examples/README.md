# choose_rest_option 实际返回示例

基线0e059f5，Mod0.72.0／MCP0.74.0。以下为真实stdio MCP完整公开JSON，保留修复前行为；没有改写字段或拼接预期值。后续确认样本来自对应的selection_option调用。来源行、调用参数及SHA-256见[manifest](manifest.json)。

| 样本 | 工具 | 参数 |
| --- | --- | --- |
| [no_rest.full.json](no_rest.full.json) | choose_rest_option | `{"preset": "full", "option_id": "HEAL"}` |
| [no_rest_blocked_continuation.full.json](no_rest_blocked_continuation.full.json) | end_turn | `{"preset": "full"}` |
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

问题、解释及验证边界见[审阅记录](../2026-11-06-choose-rest-option-review.md)。
