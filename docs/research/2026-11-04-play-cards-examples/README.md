# 连续出牌实际返回

> 当前状态：实际样本采集完成；接口与验证说明见[实施记录](../2026-11-04-play-cards-implementation.md)。

本目录 JSON 来自真实 stdio MCP structuredContent，逐项核验其与文本 JSON 相同；没有手写模拟、原生包装或观察令牌。index 为请求数组位置。batch_id 是实际的独立控制关联标识，选择续接沿用同一值。

参数、来源数组下标（从 0 起）、各样本 DLL 摘要与文件 SHA-256 见 [manifest.json](manifest.json)。状态含义见[逐张结果](../../development/card-play.md#逐张结果)。测试使用 Mod 0.63.0、MCP 0.65.0、schema 40；不据此宣称所有卡牌组合均已覆盖。

| 场景 | 工具 | 请求 | 完整返回 | 结果 |
| --- | --- | --- | --- | --- |
| diagnostics | play_card | `{"preset":"full","card_id":5}` | [diagnostics-01-play_card.full.json](diagnostics-01-play_card.full.json) | Close the card browsing page before playing cards. |
| diagnostics | inspect_targets | `{"preset":"full","card_id":8}` | [diagnostics-02-inspect_targets.full.json](diagnostics-02-inspect_targets.full.json) | inspection |
| diagnostics | play_card | `{"preset":"full","card_id":8}` | [diagnostics-03-play_card.full.json](diagnostics-03-play_card.full.json) | I'm blocked
by Normality. |
| diagnostics | play_card | `{"preset":"full","card_id":8}` | [diagnostics-04-play_card.full.json](diagnostics-04-play_card.full.json) | Close the map before playing cards. |
| ordered | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":2},{"card_id":6},{"card_id":7,"target_id":2}]}` | [ordered-01-play_cards.full.json](ordered-01-play_cards.full.json) | player_ready / played, played, played |
| atomic | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":2},{"card_id":2147483647}]}` | [atomic-01-play_cards.full.json](atomic-01-play_cards.full.json) | cards[1]: No supported visible hand card has that ID. |
| atomic | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":2},{"card_id":6,"target_id":2}]}` | [atomic-02-play_cards.full.json](atomic-02-play_cards.full.json) | cards[1]: This card does not accept target_id; omit it. |
| atomic | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":2},{"card_id":7,"target_id":4294967295}]}` | [atomic-03-play_cards.full.json](atomic-03-play_cards.full.json) | cards[1]: target_id does not identify a current visible combat object. |
| atomic | play_cards | `{"preset":"full","cards":[]}` | [atomic-04-play_cards.full.json](atomic-04-play_cards.full.json) | cards must be a nonempty array of card play objects. |
| atomic | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":2},{"card_id":5,"target_id":2}]}` | [atomic-05-play_cards.full.json](atomic-05-play_cards.full.json) | cards[1].card_id duplicates an earlier hand card ID. |
| atomic | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":2},{"card_id":6},{"card_id":7,"target_id":2}]}` | [atomic-06-play_cards.full.json](atomic-06-play_cards.full.json) | player_ready / played, played, played |
| partial | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":2},{"card_id":6,"target_id":2},{"card_id":7}]}` | [partial-01-play_cards.full.json](partial-01-play_cards.full.json) | player_ready / played, not_submitted, played |
| zero | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":2},{"card_id":6}]}` | [zero-01-play_cards.full.json](zero-01-play_cards.full.json) | player_ready / not_submitted, not_submitted |
| energy | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":2},{"card_id":6,"target_id":2},{"card_id":7,"target_id":2},{"card_id":8}]}` | [energy-01-play_cards.full.json](energy-01-play_cards.full.json) | player_ready / played, played, not_played, played |
| stars | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":2},{"card_id":6},{"card_id":7},{"card_id":8}]}` | [stars-01-play_cards.full.json](stars-01-play_cards.full.json) | player_ready / played, played, not_played, played |
| target | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":1},{"card_id":6,"target_id":1},{"card_id":7}]}` | [target-01-play_cards.full.json](target-01-play_cards.full.json) | player_ready / played, not_played, played |
| random_exhaust | play_cards | `{"preset":"full","cards":[{"card_id":5},{"card_id":6},{"card_id":7}]}` | [random_exhaust-01-play_cards.full.json](random_exhaust-01-play_cards.full.json) | player_ready / played, not_played, played |
| hand_exhaust | play_cards | `{"preset":"full","cards":[{"card_id":5},{"card_id":6},{"card_id":7}]}` | [hand_exhaust-01-play_cards.full.json](hand_exhaust-01-play_cards.full.json) | choice_required / resolving, not_played, not_played |
| hand_exhaust | play_cards | `{"preset":"full","cards":[{"card_id":7}]}` | [hand_exhaust-02-play_cards.full.json](hand_exhaust-02-play_cards.full.json) | Resolve the current card selection before playing cards. |
| hand_exhaust | select_card | `{"preset":"full","card_id":6}` | [hand_exhaust-03-select_card.full.json](hand_exhaust-03-select_card.full.json) | choice_required / resolving, not_played, not_played |
| hand_exhaust | selection_option | `{"preset":"full","option_id":"confirm"}` | [hand_exhaust-04-selection_option.full.json](hand_exhaust-04-selection_option.full.json) | player_ready / played, not_played, not_played |
| automatic_hand | play_cards | `{"preset":"full","cards":[{"card_id":5},{"card_id":6}]}` | [automatic_hand-01-play_cards.full.json](automatic_hand-01-play_cards.full.json) | player_ready / played, not_played |
| choose_one | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":2},{"card_id":6},{"card_id":7},{"card_id":8}]}` | [choose_one-01-play_cards.full.json](choose_one-01-play_cards.full.json) | choice_required / played, resolving, queued, queued |
| choose_one | play_cards | `{"preset":"full","cards":[{"card_id":8}]}` | [choose_one-02-play_cards.full.json](choose_one-02-play_cards.full.json) | Resolve the current card selection before playing cards. |
| choose_one | select_card | `{"preset":"full","card_id":9}` | [choose_one-03-select_card.full.json](choose_one-03-select_card.full.json) | player_ready / played, played, played, played |
| immediate_choice | play_cards | `{"preset":"full","cards":[{"card_id":5},{"card_id":6},{"card_id":7}]}` | [immediate_choice-01-play_cards.full.json](immediate_choice-01-play_cards.full.json) | choice_required / resolving, not_submitted, not_submitted |
| immediate_choice | play_cards | `{"preset":"full","cards":[{"card_id":7}]}` | [immediate_choice-02-play_cards.full.json](immediate_choice-02-play_cards.full.json) | Resolve the current card selection before playing cards. |
| immediate_choice | select_card | `{"preset":"full","card_id":8}` | [immediate_choice-03-select_card.full.json](immediate_choice-03-select_card.full.json) | player_ready / played, not_submitted, not_submitted |
| combat_pile | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":2},{"card_id":6,"target_id":2},{"card_id":7},{"card_id":8}]}` | [combat_pile-01-play_cards.full.json](combat_pile-01-play_cards.full.json) | choice_required / played, resolving, queued, queued |
| combat_pile | play_cards | `{"preset":"full","cards":[{"card_id":8}]}` | [combat_pile-02-play_cards.full.json](combat_pile-02-play_cards.full.json) | Resolve the current card selection before playing cards. |
| combat_pile | select_card | `{"preset":"full","card_id":9}` | [combat_pile-03-select_card.full.json](combat_pile-03-select_card.full.json) | player_ready / played, played, played, played |
| victory | play_cards | `{"preset":"full","cards":[{"card_id":5},{"card_id":6},{"card_id":7}]}` | [victory-01-play_cards.full.json](victory-01-play_cards.full.json) | combat_won / played, not_played, not_played |
| death | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":2},{"card_id":6},{"card_id":7},{"card_id":8}]}` | [death-01-play_cards.full.json](death-01-play_cards.full.json) | combat_lost / played, played, not_played, not_played |
| immediate_death | play_cards | `{"preset":"full","cards":[{"card_id":5},{"card_id":6},{"card_id":7}]}` | [immediate_death-01-play_cards.full.json](immediate_death-01-play_cards.full.json) | combat_lost / played, not_submitted, not_submitted |
| default | play_cards | `{"preset":"default","cards":[{"card_id":5,"target_id":2},{"card_id":6},{"card_id":7,"target_id":2}]}` | [default-01-play_cards.default.json](default-01-play_cards.default.json) | player_ready / played, played, played |
| single_entry | play_cards | `{"preset":"full","cards":[{"card_id":6}]}` | [single_entry-01-play_cards.full.json](single_entry-01-play_cards.full.json) | player_ready / played |
| autoplay | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":2},{"card_id":7},{"card_id":8,"target_id":2}]}` | [autoplay-01-play_cards.full.json](autoplay-01-play_cards.full.json) | player_ready / played, played, played |
| pending_reset | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":2},{"card_id":6},{"card_id":7},{"card_id":8}]}` | [pending_reset-01-play_cards.full.json](pending_reset-01-play_cards.full.json) | choice_required / played, resolving, queued, queued |
| single_basic | play_card | `{"preset":"full","card_id":true}` | [single_basic-01-play_card.full.json](single_basic-01-play_card.full.json) | card_id must be integer. |
| single_basic | play_card | `{"preset":"full","card_id":5,"target_id":null}` | [single_basic-02-play_card.full.json](single_basic-02-play_card.full.json) | target_id must be integer. |
| single_basic | play_card | `{"preset":"full","card_id":2147483647}` | [single_basic-03-play_card.full.json](single_basic-03-play_card.full.json) | No supported visible hand card has that ID. |
| single_basic | play_card | `{"preset":"full","card_id":5}` | [single_basic-04-play_card.full.json](single_basic-04-play_card.full.json) | This card requires target_id for a current target; inspect_targets can clarify its target range. |
| single_basic | play_card | `{"preset":"full","card_id":5,"target_id":4294967295}` | [single_basic-05-play_card.full.json](single_basic-05-play_card.full.json) | target_id does not identify a current visible combat object. |
| single_basic | play_card | `{"preset":"full","card_id":6,"target_id":0}` | [single_basic-06-play_card.full.json](single_basic-06-play_card.full.json) | This card does not accept target_id; omit it. |
| single_energy | play_card | `{"preset":"full","card_id":5,"target_id":2}` | [single_energy-01-play_card.full.json](single_energy-01-play_card.full.json) | I don't have
enough Energy. |
| single_cancel | play_card | `{"preset":"full","card_id":5,"target_id":2}` | [single_cancel-01-play_card.full.json](single_cancel-01-play_card.full.json) | action_canceled |
| single_cancel | play_card | `{"preset":"full","card_id":6}` | [single_cancel-02-play_card.full.json](single_cancel-02-play_card.full.json) | Read current state with get_observation or a relevant inspection before acting. |
| single_hand_choice | play_card | `{"preset":"full","card_id":7}` | [single_hand_choice-01-play_card.full.json](single_hand_choice-01-play_card.full.json) | Resolve the current card selection before playing cards. |
| single_hand_choice | select_card | `{"preset":"full","card_id":6}` | [single_hand_choice-02-select_card.full.json](single_hand_choice-02-select_card.full.json) | choice_required |
| single_hand_choice | selection_option | `{"preset":"full","option_id":"confirm"}` | [single_hand_choice-03-selection_option.full.json](single_hand_choice-03-selection_option.full.json) | player_ready |
| single_choose_one | play_card | `{"preset":"full","card_id":7}` | [single_choose_one-01-play_card.full.json](single_choose_one-01-play_card.full.json) | Resolve the current card selection before playing cards. |
| single_choose_one | select_card | `{"preset":"full","card_id":8}` | [single_choose_one-02-select_card.full.json](single_choose_one-02-select_card.full.json) | player_ready |
| single_combat_pile | play_card | `{"preset":"full","card_id":7}` | [single_combat_pile-01-play_card.full.json](single_combat_pile-01-play_card.full.json) | Resolve the current card selection before playing cards. |
| single_combat_pile | select_card | `{"preset":"full","card_id":6}` | [single_combat_pile-02-select_card.full.json](single_combat_pile-02-select_card.full.json) | player_ready |
| native_reject | play_card | `{"preset":"full","card_id":5,"target_id":2}` | [native_reject-01-play_card.full.json](native_reject-01-play_card.full.json) | The game rejected this card play before submission. |
| native_reject | play_cards | `{"preset":"full","cards":[{"card_id":5,"target_id":2},{"card_id":6},{"card_id":7,"target_id":2}]}` | [native_reject-02-play_cards.full.json](native_reject-02-play_cards.full.json) | player_ready / not_submitted, played, played |

pending_reset 在原生选择尚未完成时由隔离套件清理对局，after_reset 在新局确认旧批次未重放。native_reject 使用一次性原生返回 false 的测试注入，验证明确拒绝与继续提交，不表示已在自然游玩遇到相同注入条件。
