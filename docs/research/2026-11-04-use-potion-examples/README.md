# use_potion 完整返回样例

这些是基线 `30a01e9` 的真实 stdio MCP 返回，未修改玩法行为。背景、问题及未验证范围见[审阅记录](../2026-11-04-use-potion-review.md)。

共 30 类场景／边界、207 次 MCP 调用，选取 120 份完整返回；未截断字段或省略事件。full/default 以各文件原调用为准，错误响应不受 preset 影响。

每个文件的参数、原始报告行号（从 0 开始）、构建及 SHA-256 见[样本清单](manifest.json)。文件只含公开返回；原生执行事实与状态令牌保留在不纳入 Git 的原始证据中。slot_boundary/journal_boundary 的显示状态为测试注入，不表示自然游玩中出现同类布局。

| 场景 | use_potion 返回／关键边界 |
| --- | --- |
| `basic` | [use_potion → invalid_request](basic-03-use_potion.json)、[use_potion → invalid_request](basic-04-use_potion.json)、[use_potion → invalid_request](basic-05-use_potion.json)、[use_potion → invalid_request](basic-06-use_potion.json)、[use_potion → invalid_request](basic-07-use_potion.json)、[use_potion → illegal_action](basic-10-use_potion.json)、[use_potion → illegal_action](basic-15-use_potion.json)、[use_potion → illegal_action](basic-20-use_potion.json)、[use_potion → illegal_action](basic-25-use_potion.json)、[use_potion → illegal_action](basic-30-use_potion.json)、[use_potion → player_ready](basic-34-use_potion.full.json)、[use_potion → player_ready](basic-35-use_potion.full.json)、[use_potion → illegal_action](basic-37-use_potion.json) |
| `default` | [use_potion → player_ready](default-03-use_potion.default.json) |
| `aoe` | [use_potion → player_ready](aoe-03-use_potion.full.json) |
| `victory` | [use_potion → combat_won](victory-03-use_potion.full.json) |
| `death` | [use_potion → combat_lost](death-03-use_potion.full.json) |
| `fairy_rescue` | [use_potion → player_ready](fairy_rescue-03-use_potion.full.json) |
| `cancel` | [use_potion → action_canceled](cancel-03-use_potion.full.json)、[use_potion → observation_required](cancel-04-use_potion.json) |
| `skill` | [use_potion → choice_required](skill-03-use_potion.full.json)、[use_potion → illegal_action](skill-05-use_potion.json) |
| `attack` | [use_potion → choice_required](attack-03-use_potion.full.json)、[use_potion → illegal_action](attack-05-use_potion.json) |
| `power` | [use_potion → choice_required](power-03-use_potion.full.json)、[use_potion → illegal_action](power-05-use_potion.json) |
| `colorless` | [use_potion → choice_required](colorless-03-use_potion.full.json)、[use_potion → illegal_action](colorless-05-use_potion.json) |
| `memories` | [use_potion → choice_required](memories-03-use_potion.full.json)、[use_potion → illegal_action](memories-05-use_potion.json) |
| `gamblers` | [use_potion → choice_required](gamblers-03-use_potion.full.json)、[use_potion → illegal_action](gamblers-05-use_potion.json) |
| `fruit_combat` | [use_potion → player_ready](fruit_combat-03-use_potion.full.json)、[use_potion → player_ready](fruit_combat-06-use_potion.full.json) |
| `noncombat_event` | [use_potion → action_completed](noncombat_event-03-use_potion.full.json)、[use_potion → action_completed](noncombat_event-06-use_potion.full.json)、[use_potion → illegal_action](noncombat_event-08-use_potion.json) |
| `noncombat_rest` | [use_potion → action_completed](noncombat_rest-03-use_potion.full.json)、[use_potion → action_completed](noncombat_rest-06-use_potion.full.json)、[use_potion → illegal_action](noncombat_rest-08-use_potion.json) |
| `noncombat_shop` | [use_potion → action_completed](noncombat_shop-03-use_potion.full.json)、[use_potion → action_completed](noncombat_shop-06-use_potion.full.json)、[use_potion → illegal_action](noncombat_shop-08-use_potion.json) |
| `noncombat_map` | [use_potion → action_completed](noncombat_map-03-use_potion.full.json)、[use_potion → action_completed](noncombat_map-06-use_potion.full.json)、[use_potion → illegal_action](noncombat_map-08-use_potion.json) |
| `noncombat_reward` | [use_potion → action_completed](noncombat_reward-03-use_potion.full.json)、[use_potion → action_completed](noncombat_reward-06-use_potion.full.json)、[use_potion → illegal_action](noncombat_reward-08-use_potion.json) |
| `merchant` | [use_potion → action_completed](merchant-03-use_potion.full.json) |
| `merchant_inventory` | [use_potion → illegal_action](merchant_inventory-03-use_potion.json) |
| `merchant_map` | [use_potion → illegal_action](merchant_map-03-use_potion.json) |
| `blocked` | [use_potion → illegal_action](blocked-03-use_potion.json) |
| `entropic` | [use_potion → player_ready](entropic-03-use_potion.full.json) |
| `replace` | [use_potion → stale_state](replace-06-use_potion.json)、[use_potion → observation_required](replace-07-use_potion.json) |
| `unhittable` | [use_potion → illegal_action](unhittable-03-use_potion.json)、[use_potion → player_ready](unhittable-05-use_potion.full.json) |
| `covered` | [use_potion → illegal_action](covered-06-use_potion.json)、[use_potion → illegal_action](covered-11-use_potion.json)、[use_potion → illegal_action](covered-16-use_potion.json) |
| `slot_boundary` | [use_potion → illegal_action](slot_boundary-08-use_potion.json)、[use_potion → illegal_action](slot_boundary-13-use_potion.json)、[use_potion → illegal_action](slot_boundary-18-use_potion.json)、[use_potion → player_ready](slot_boundary-21-use_potion.full.json) |
| `journal_boundary` | [end_turn → player_ready](journal_boundary-04-end_turn.full.json) |
| `fake_merchant` | [use_potion → observation_required](fake_merchant-01-use_potion.json)、[use_potion → player_ready](fake_merchant-04-use_potion.full.json) |

其他文件包含目标查询、完整选择候选及继续／确认回执，用于核对边界，而非增加 use_potion 的返回字段。错误处理现状按原样保留，不能把这些基线样例当作修复结果。
