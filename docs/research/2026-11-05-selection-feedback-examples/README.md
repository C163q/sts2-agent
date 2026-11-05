# 选牌状态反馈与拒绝修复后的完整返回

这些 JSON 来自真实 stdio MCP 的 `preset:"full"` 返回，未补入内部状态、任务结果或测试标记。工具参数保持不变。每个来源均为通过场景；manifest 记录精确参数、原始证据、从 1 起的记录序号和产物哈希。

验证范围与两份仅测试夹具不同的产物见[实施记录](../2026-11-05-selection-feedback-implementation.md)。原始审阅的 91 份返回继续保留在[基线目录](../2026-11-05-select-card-examples/README.md)，不覆盖旧行为。

| 场景 | 调用 | 完整返回 |
| --- | --- | --- |
| no_selection | `select_card` no_selection-no_selection | [JSON](no_selection-no_selection.full.json) |
| no_selection | `end_turn` no_selection-after_unsubmitted_rejection | [JSON](no_selection-after_unsubmitted_rejection.full.json) |
| invalid_candidate | `select_card` invalid_candidate-unknown_id | [JSON](invalid_candidate-unknown_id.full.json) |
| invalid_candidate | `select_card` invalid_candidate-valid_card_after_rejection | [JSON](invalid_candidate-valid_card_after_rejection.full.json) |
| covered | `select_card` covered-battlefield | [JSON](covered-battlefield.full.json) |
| covered | `select_card` covered-covered | [JSON](covered-covered.full.json) |
| grid | `select_card` grid-select_first | [JSON](grid-select_first.full.json) |
| grid | `select_card` grid-deselect_without_read | [JSON](grid-deselect_without_read.full.json) |
| grid | `select_card` grid-choose_candidate | [JSON](grid-choose_candidate.full.json) |
| smith | `select_card` smith-choose_candidate | [JSON](smith-choose_candidate.full.json) |
| smith | `selection_option` smith-cancel_after_preview_rejection | [JSON](smith-cancel_after_preview_rejection.full.json) |
| smith | `selection_option` smith-confirm | [JSON](smith-confirm.full.json) |
| multi_upgrade | `select_card` multi_upgrade-choose_candidate | [JSON](multi_upgrade-choose_candidate.full.json) |
| multi_upgrade | `selection_option` multi_upgrade-cancel_after_preview_rejection | [JSON](multi_upgrade-cancel_after_preview_rejection.full.json) |
| hand_replace | `select_card` hand_replace-replace_selected | [JSON](hand_replace-replace_selected.full.json) |
| grid_manual | `select_card` grid_manual-already_full | [JSON](grid_manual-already_full.full.json) |
| headbutt | `select_card` headbutt-select_card | [JSON](headbutt-select_card.full.json) |
| choose_one | `select_card` choose_one-choose_candidate | [JSON](choose_one-choose_candidate.full.json) |
| reward | `select_card` reward-choose_candidate | [JSON](reward-choose_candidate.full.json) |
| chain | `select_card` chain-first_choice | [JSON](chain-first_choice.full.json) |
| chain | `select_card` chain-second_choice_without_read | [JSON](chain-second_choice_without_read.full.json) |
| combat_entry | `select_card` combat_entry-choose_candidate | [JSON](combat_entry-choose_candidate.full.json) |
| bundle | `select_card` bundle-not_individually_selectable | [JSON](bundle-not_individually_selectable.full.json) |
| bundle | `selection_option` bundle-valid_button_after_rejection | [JSON](bundle-valid_button_after_rejection.full.json) |
| view_cards | `select_card` view_cards-not_individually_selectable | [JSON](view_cards-not_individually_selectable.full.json) |
| view_cards | `selection_option` view_cards-valid_button_after_rejection | [JSON](view_cards-valid_button_after_rejection.full.json) |
| enchant_multi | `selection_option` enchant_multi-cancel_after_preview_rejection | [JSON](enchant_multi-cancel_after_preview_rejection.full.json) |
| death | `selection_option` death-confirm | [JSON](death-confirm.full.json) |
| victory | `selection_option` victory-confirm | [JSON](victory-confirm.full.json) |
| upgrade_view | `select_card` upgrade_view-choose_candidate | [JSON](upgrade_view-choose_candidate.full.json) |
| upgrade_view | `selection_option` upgrade_view-cancel_after_preview_rejection | [JSON](upgrade_view-cancel_after_preview_rejection.full.json) |
