# selection_option 修复后的完整返回

以下是 Mod 0.66.1、MCP 0.68.1 的真实 stdio MCP full 返回。仅提取通过场景的公共结果；原生快照、内部执行证据和夹具检查不进入样例。manifest 记录实际参数、来源、从 1 起的记录序号和文件哈希。

行为及验证范围见[实施记录](../2026-11-05-selection-option-recovery-implementation.md)；原 [81 份审阅返回](../2026-11-05-selection-option-examples/README.md)保留修复前行为。

| 场景 | 调用 | 完整返回 |
| --- | --- | --- |
| no_selection | `selection_option({"preset":"full","option_id":"confirm"})` | [no_selection-11-no_selection.full.json](no_selection-11-no_selection.full.json) |
| no_selection | `end_turn({"preset":"full"})` | [no_selection-12-after_unsubmitted_rejection.full.json](no_selection-12-after_unsubmitted_rejection.full.json) |
| invalid_option | `selection_option({"preset":"full","option_id":"not_offered"})` | [invalid_option-03-invalid_option.full.json](invalid_option-03-invalid_option.full.json) |
| invalid_option | `select_card({"preset":"full","card_id":5})` | [invalid_option-04-valid_card_after_rejection.full.json](invalid_option-04-valid_card_after_rejection.full.json) |
| disabled | `selection_option({"preset":"full","option_id":"confirm"})` | [disabled-03-disabled.full.json](disabled-03-disabled.full.json) |
| disabled | `select_card({"preset":"full","card_id":5})` | [disabled-04-select_after_rejection.full.json](disabled-04-select_after_rejection.full.json) |
| disabled | `select_card({"preset":"full","card_id":6})` | [disabled-06-select_after_rejection.full.json](disabled-06-select_after_rejection.full.json) |
| disabled | `selection_option({"preset":"full","option_id":"confirm"})` | [disabled-08-confirm_after_rejection.full.json](disabled-08-confirm_after_rejection.full.json) |
| battlefield | `selection_option({"preset":"full","option_id":"confirm"})` | [battlefield-04-battlefield.full.json](battlefield-04-battlefield.full.json) |
| covered | `selection_option({"preset":"full","option_id":"confirm"})` | [covered-05-covered.full.json](covered-05-covered.full.json) |
| choose_skip | `selection_option({"preset":"full","option_id":"skip"})` | [choose_skip-05-skip.full.json](choose_skip-05-skip.full.json) |
| reward_skip | `selection_option({"preset":"full","option_id":"skip"})` | [reward_skip-03-skip.full.json](reward_skip-03-skip.full.json) |
| grid_manual | `selection_option({"preset":"full","option_id":"confirm"})` | [grid_manual-08-confirm.full.json](grid_manual-08-confirm.full.json) |
| hand_zero | `selection_option({"preset":"full","option_id":"confirm"})` | [hand_zero-05-confirm_zero_cards.full.json](hand_zero-05-confirm_zero_cards.full.json) |
| hand_one | `selection_option({"preset":"full","option_id":"confirm"})` | [hand_one-07-confirm.full.json](hand_one-07-confirm.full.json) |
| hand_upgrade | `selection_option({"preset":"full","option_id":"confirm"})` | [hand_upgrade-07-confirm.full.json](hand_upgrade-07-confirm.full.json) |
| deck_cancel | `selection_option({"preset":"full","option_id":"cancel"})` | [deck_cancel-03-cancel_selection.full.json](deck_cancel-03-cancel_selection.full.json) |
| deck_preview | `selection_option({"preset":"full","option_id":"cancel_preview"})` | [deck_preview-06-cancel_preview.full.json](deck_preview-06-cancel_preview.full.json) |
| deck_preview | `selection_option({"preset":"full","option_id":"confirm"})` | [deck_preview-11-confirm.full.json](deck_preview-11-confirm.full.json) |
| smith | `selection_option({"preset":"full","option_id":"cancel_preview"})` | [smith-08-cancel_preview.full.json](smith-08-cancel_preview.full.json) |
| smith | `selection_option({"preset":"full","option_id":"confirm"})` | [smith-13-confirm.full.json](smith-13-confirm.full.json) |
| multi_upgrade | `selection_option({"preset":"full","option_id":"cancel_preview"})` | [multi_upgrade-08-cancel_preview.full.json](multi_upgrade-08-cancel_preview.full.json) |
| multi_upgrade | `selection_option({"preset":"full","option_id":"confirm"})` | [multi_upgrade-15-confirm.full.json](multi_upgrade-15-confirm.full.json) |
| enchant_single | `selection_option({"preset":"full","option_id":"cancel_preview"})` | [enchant_single-08-cancel_preview.full.json](enchant_single-08-cancel_preview.full.json) |
| enchant_single | `selection_option({"preset":"full","option_id":"confirm"})` | [enchant_single-13-confirm.full.json](enchant_single-13-confirm.full.json) |
| enchant_multi | `selection_option({"preset":"full","option_id":"cancel_preview"})` | [enchant_multi-15-cancel_preview.full.json](enchant_multi-15-cancel_preview.full.json) |
| enchant_multi | `selection_option({"preset":"full","option_id":"confirm"})` | [enchant_multi-24-confirm.full.json](enchant_multi-24-confirm.full.json) |
| transform | `selection_option({"preset":"full","option_id":"cancel_preview"})` | [transform-10-cancel_preview.full.json](transform-10-cancel_preview.full.json) |
| transform | `selection_option({"preset":"full","option_id":"confirm"})` | [transform-15-confirm.full.json](transform-15-confirm.full.json) |
| bundle | `selection_option({"preset":"full","option_id":"bundle:0"})` | [bundle-07-select_bundle.full.json](bundle-07-select_bundle.full.json) |
| bundle | `selection_option({"preset":"full","option_id":"cancel_preview"})` | [bundle-10-cancel_bundle.full.json](bundle-10-cancel_bundle.full.json) |
| bundle | `selection_option({"preset":"full","option_id":"bundle:1"})` | [bundle-13-reselect_bundle_without_read.full.json](bundle-13-reselect_bundle_without_read.full.json) |
| bundle | `selection_option({"preset":"full","option_id":"confirm"})` | [bundle-15-confirm_bundle.full.json](bundle-15-confirm_bundle.full.json) |
| view_cards | `selection_option({"preset":"full","option_id":"confirm"})` | [view_cards-07-confirm_results.full.json](view_cards-07-confirm_results.full.json) |
| death | `selection_option({"preset":"full","option_id":"confirm"})` | [death-07-confirm.full.json](death-07-confirm.full.json) |
| victory | `selection_option({"preset":"full","option_id":"confirm"})` | [victory-07-confirm.full.json](victory-07-confirm.full.json) |
| paels_wing | `selection_option({"preset":"full","option_id":"alternative:1"})` | [paels_wing-07-alternative_1.full.json](paels_wing-07-alternative_1.full.json) |
| paels_wing | `selection_option({"preset":"full","option_id":"alternative:1"})` | [paels_wing-17-alternative_1.full.json](paels_wing-17-alternative_1.full.json) |
| driftwood | `selection_option({"preset":"full","option_id":"alternative:1"})` | [driftwood-07-alternative_1.full.json](driftwood-07-alternative_1.full.json) |
| driftwood | `selection_option({"preset":"full","option_id":"alternative:1"})` | [driftwood-16-alternative_1.full.json](driftwood-16-alternative_1.full.json) |
| driftwood | `selection_option({"preset":"full","option_id":"alternative:1"})` | [driftwood-26-alternative_1.full.json](driftwood-26-alternative_1.full.json) |
| driftwood | `selection_option({"preset":"full","option_id":"alternative:1"})` | [driftwood-35-alternative_1.full.json](driftwood-35-alternative_1.full.json) |
| driftwood | `selection_option({"preset":"full","option_id":"skip"})` | [driftwood-39-skip.full.json](driftwood-39-skip.full.json) |
| shop_remove | `selection_option({"preset":"full","option_id":"cancel_preview"})` | [shop_remove-11-cancel_preview.full.json](shop_remove-11-cancel_preview.full.json) |
| shop_remove | `selection_option({"preset":"full","option_id":"confirm"})` | [shop_remove-16-confirm.full.json](shop_remove-16-confirm.full.json) |
