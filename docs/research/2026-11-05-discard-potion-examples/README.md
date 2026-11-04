# discard_potion 完整返回样例

真实 MCP 返回，未裁剪字段；每份样例的参数、原始报告、从 0 开始的记录位置及 SHA-256 见 [manifest.json](manifest.json)。错误示例保留实际传入的 preset 名称，不表示该预设受支持。

两次套件分别因强制地图不可返回、最后一项奖励自动关闭的测试假设错误而失败；仅采用各自通过用例。covered、noncombat_reward 分别采用后续独立复测，失败报告保留。

| 场景 | 参数 | 返回 | 完整 JSON |
| --- | --- | --- | --- |
| basic | `{"preset": "full", "potion_slot": 0}` | error | [basic-00-full-error.json](basic-00-full-error.json) |
| basic | `{"preset": "full"}` | error | [basic-02-full-error.json](basic-02-full-error.json) |
| basic | `{"preset": "full", "potion_slot": true}` | error | [basic-03-full-error.json](basic-03-full-error.json) |
| basic | `{"preset": "full", "potion_slot": -1}` | error | [basic-04-full-error.json](basic-04-full-error.json) |
| basic | `{"preset": "full", "potion_slot": 0.0}` | error | [basic-05-full-error.json](basic-05-full-error.json) |
| basic | `{"preset": "full", "potion_slot": "0"}` | error | [basic-06-full-error.json](basic-06-full-error.json) |
| basic | `{"preset": "full", "potion_slot": null}` | error | [basic-07-full-error.json](basic-07-full-error.json) |
| basic | `{"preset": "full", "potion_slot": 2147483648}` | error | [basic-08-full-error.json](basic-08-full-error.json) |
| basic | `{"preset": "full", "potion_slot": 0, "target_id": 1}` | error | [basic-09-full-error.json](basic-09-full-error.json) |
| basic | `{"preset": "summary", "potion_slot": 0}` | error | [basic-10-summary-error.json](basic-10-summary-error.json) |
| basic | `{"preset": "full", "potion_slot": 0, "unknown": true}` | error | [basic-11-full-error.json](basic-11-full-error.json) |
| basic | `{"preset": "full", "potion_slot": 99}` | error | [basic-13-full-error.json](basic-13-full-error.json) |
| basic | `{"preset": "full", "potion_slot": 1}` | player_ready | [basic-17-full-player_ready.json](basic-17-full-player_ready.json) |
| basic | `{"preset": "full", "potion_slot": 1}` | error | [basic-20-full-error.json](basic-20-full-error.json) |
| basic | `{"preset": "full", "potion_slot": 0}` | player_ready | [basic-23-full-player_ready.json](basic-23-full-player_ready.json) |
| basic | `{"preset": "full", "potion_slot": 2}` | player_ready | [basic-26-full-player_ready.json](basic-26-full-player_ready.json) |
| default | `{"preset": "full", "potion_slot": 0}` | error | [default-00-full-error.json](default-00-full-error.json) |
| default | `{"preset": "default", "potion_slot": 0}` | player_ready | [default-03-default-player_ready.json](default-03-default-player_ready.json) |
| default | `{"preset": "full", "potion_slot": 1}` | player_ready | [default-06-full-player_ready.json](default-06-full-player_ready.json) |
| automatic | `{"preset": "full", "potion_slot": 0}` | error | [automatic-00-full-error.json](automatic-00-full-error.json) |
| automatic | `{"preset": "full", "potion_slot": 2}` | player_ready | [automatic-03-full-player_ready.json](automatic-03-full-player_ready.json) |
| automatic | `{"preset": "full", "potion_slot": 1}` | player_ready | [automatic-06-full-player_ready.json](automatic-06-full-player_ready.json) |
| fruit | `{"preset": "full", "potion_slot": 0}` | error | [fruit-00-full-error.json](fruit-00-full-error.json) |
| fruit | `{"preset": "full", "potion_slot": 0}` | player_ready | [fruit-03-full-player_ready.json](fruit-03-full-player_ready.json) |
| fruit | `{"preset": "full", "potion_slot": 1}` | player_ready | [fruit-06-full-player_ready.json](fruit-06-full-player_ready.json) |
| blocked | `{"preset": "full", "potion_slot": 0}` | error | [blocked-00-full-error.json](blocked-00-full-error.json) |
| blocked | `{"preset": "full", "potion_slot": 0}` | error | [blocked-03-full-error.json](blocked-03-full-error.json) |
| replace | `{"preset": "full", "potion_slot": 0}` | error | [replace-00-full-error.json](replace-00-full-error.json) |
| replace | `{"preset": "full", "potion_slot": 0}` | error | [replace-05-full-error.json](replace-05-full-error.json) |
| replace | `{"preset": "full", "potion_slot": 0}` | player_ready | [replace-09-full-player_ready.json](replace-09-full-player_ready.json) |
| covered | `{"preset": "full", "potion_slot": 0}` | error | [covered-00-full-error.json](covered-00-full-error.json) |
| covered | `{"preset": "full", "potion_slot": 0}` | error | [covered-06-full-error.json](covered-06-full-error.json) |
| covered | `{"preset": "full", "potion_slot": 0}` | error | [covered-12-full-error.json](covered-12-full-error.json) |
| covered | `{"preset": "full", "potion_slot": 0}` | error | [covered-18-full-error.json](covered-18-full-error.json) |
| display | `{"preset": "full", "potion_slot": 0}` | error | [display-00-full-error.json](display-00-full-error.json) |
| display | `{"preset": "full", "potion_slot": 2}` | error | [display-05-full-error.json](display-05-full-error.json) |
| display | `{"preset": "full", "potion_slot": 2}` | error | [display-11-full-error.json](display-11-full-error.json) |
| display | `{"preset": "full", "potion_slot": 2}` | error | [display-17-full-error.json](display-17-full-error.json) |
| display | `{"preset": "full", "potion_slot": 0}` | player_ready | [display-19-full-player_ready.json](display-19-full-player_ready.json) |
| display | `{"preset": "full", "potion_slot": 2}` | player_ready | [display-24-full-player_ready.json](display-24-full-player_ready.json) |
| display | `{"preset": "full", "potion_slot": 1}` | player_ready | [display-29-full-player_ready.json](display-29-full-player_ready.json) |
| skill | `{"preset": "full", "potion_slot": 0}` | error | [skill-00-full-error.json](skill-00-full-error.json) |
| skill | `{"preset": "full", "potion_slot": 1}` | error | [skill-05-full-error.json](skill-05-full-error.json) |
| skill | `{"preset": "full", "potion_slot": 1}` | player_ready | [skill-09-full-player_ready.json](skill-09-full-player_ready.json) |
| noncombat_event | `{"preset": "full", "potion_slot": 0}` | error | [noncombat_event-00-full-error.json](noncombat_event-00-full-error.json) |
| noncombat_event | `{"preset": "full", "potion_slot": 0}` | action_completed | [noncombat_event-03-full-action_completed.json](noncombat_event-03-full-action_completed.json) |
| noncombat_event | `{"preset": "full", "potion_slot": 1}` | action_completed | [noncombat_event-06-full-action_completed.json](noncombat_event-06-full-action_completed.json) |
| noncombat_rest | `{"preset": "full", "potion_slot": 0}` | error | [noncombat_rest-00-full-error.json](noncombat_rest-00-full-error.json) |
| noncombat_rest | `{"preset": "full", "potion_slot": 0}` | action_completed | [noncombat_rest-03-full-action_completed.json](noncombat_rest-03-full-action_completed.json) |
| noncombat_rest | `{"preset": "full", "potion_slot": 1}` | action_completed | [noncombat_rest-06-full-action_completed.json](noncombat_rest-06-full-action_completed.json) |
| noncombat_shop | `{"preset": "full", "potion_slot": 0}` | error | [noncombat_shop-00-full-error.json](noncombat_shop-00-full-error.json) |
| noncombat_shop | `{"preset": "full", "potion_slot": 0}` | action_completed | [noncombat_shop-03-full-action_completed.json](noncombat_shop-03-full-action_completed.json) |
| noncombat_shop | `{"preset": "full", "potion_slot": 1}` | action_completed | [noncombat_shop-06-full-action_completed.json](noncombat_shop-06-full-action_completed.json) |
| noncombat_map | `{"preset": "full", "potion_slot": 0}` | error | [noncombat_map-00-full-error.json](noncombat_map-00-full-error.json) |
| noncombat_map | `{"preset": "full", "potion_slot": 0}` | action_completed | [noncombat_map-04-full-action_completed.json](noncombat_map-04-full-action_completed.json) |
| noncombat_map | `{"preset": "full", "potion_slot": 1}` | action_completed | [noncombat_map-07-full-action_completed.json](noncombat_map-07-full-action_completed.json) |
| noncombat_map | `{"preset": "full", "potion_slot": 2}` | action_completed | [noncombat_map-10-full-action_completed.json](noncombat_map-10-full-action_completed.json) |
| noncombat_reward | `{"preset": "full", "potion_slot": 0}` | error | [noncombat_reward-00-full-error.json](noncombat_reward-00-full-error.json) |
| noncombat_reward | `{"preset": "full", "potion_slot": 1}` | action_completed | [noncombat_reward-06-full-action_completed.json](noncombat_reward-06-full-action_completed.json) |
| merchant_inventory | `{"preset": "full", "potion_slot": 0}` | error | [merchant_inventory-00-full-error.json](merchant_inventory-00-full-error.json) |
| merchant_inventory | `{"preset": "full", "potion_slot": 0}` | action_completed | [merchant_inventory-03-full-action_completed.json](merchant_inventory-03-full-action_completed.json) |
| merchant_inventory | `{"preset": "full", "potion_slot": 1}` | action_completed | [merchant_inventory-06-full-action_completed.json](merchant_inventory-06-full-action_completed.json) |
