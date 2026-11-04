# 选牌查看修复后的完整返回

本目录保存修复后的真实 MCP 返回，涵盖明确拒绝、安全续接及两类补齐的文字；原审阅样例保持原状。实现与未验证边界见[实施记录](../2026-11-05-selection-inspection-implementation.md)。

共 27 份。所有输出保持原样；参数、原报告记录序号与样例／DLL 哈希见 [manifest.json](manifest.json)。原报告保存在仓库忽略的 `.tmp/2026-11-05-selection-inspection-fixes/gui-focused/`。

| 场景 | 实际调用 | 完整返回 |
| --- | --- | --- |
| no_selection | `inspect_selection({"preset":"full","view_upgrades":false})` | [no_selection-01-inspect_selection-full.json](no_selection-01-inspect_selection-full.json) |
| no_selection | `end_turn({"preset":"full"})` | [no_selection-02-end_turn-full.json](no_selection-02-end_turn-full.json) |
| no_selection | `inspect_selection({"preset":"full"})` | [no_selection-04-inspect_selection-full.json](no_selection-04-inspect_selection-full.json) |
| no_selection | `end_turn({"preset":"full"})` | [no_selection-05-end_turn-full.json](no_selection-05-end_turn-full.json) |
| no_selection | `inspect_selection({"preset":"full","view_upgrades":false})` | [no_selection-08-inspect_selection-full.json](no_selection-08-inspect_selection-full.json) |
| no_selection | `end_turn({"preset":"full"})` | [no_selection-09-end_turn-full.json](no_selection-09-end_turn-full.json) |
| covered | `inspect_selection({"preset":"full","view_upgrades":true})` | [covered-04-inspect_selection-full.json](covered-04-inspect_selection-full.json) |
| covered | `inspect_selection({"preset":"full"})` | [covered-07-inspect_selection-full.json](covered-07-inspect_selection-full.json) |
| hand_upgrade | `inspect_selection({"preset":"full"})` | [hand_upgrade-03-inspect_selection-full.json](hand_upgrade-03-inspect_selection-full.json) |
| hand_upgrade | `inspect_selection({"preset":"full","view_upgrades":true,"card_ids":[]})` | [hand_upgrade-04-inspect_selection-full.json](hand_upgrade-04-inspect_selection-full.json) |
| hand_upgrade | `inspect_selection({"preset":"full"})` | [hand_upgrade-06-inspect_selection-full.json](hand_upgrade-06-inspect_selection-full.json) |
| hand_upgrade | `inspect_selection({"preset":"full","view_upgrades":false})` | [hand_upgrade-09-inspect_selection-full.json](hand_upgrade-09-inspect_selection-full.json) |
| hand_upgrade | `inspect_selection({"preset":"full"})` | [hand_upgrade-11-inspect_selection-full.json](hand_upgrade-11-inspect_selection-full.json) |
| bundle | `get_observation({"preset":"full"})` | [bundle-01-get_observation-full.json](bundle-01-get_observation-full.json) |
| bundle | `get_observation({"preset":"full"})` | [bundle-03-get_observation-full.json](bundle-03-get_observation-full.json) |
| bundle | `inspect_selection({"preset":"full"})` | [bundle-04-inspect_selection-full.json](bundle-04-inspect_selection-full.json) |
| bundle | `get_observation({"preset":"default"})` | [bundle-05-get_observation-default.json](bundle-05-get_observation-default.json) |
| bundle | `inspect_selection({"preset":"default"})` | [bundle-06-inspect_selection-default.json](bundle-06-inspect_selection-default.json) |
| bundle | `get_observation({"preset":"summary"})` | [bundle-07-get_observation-summary.json](bundle-07-get_observation-summary.json) |
| bundle | `inspect_selection({"preset":"summary"})` | [bundle-08-inspect_selection-summary.json](bundle-08-inspect_selection-summary.json) |
| view_cards | `get_observation({"preset":"full"})` | [view_cards-01-get_observation-full.json](view_cards-01-get_observation-full.json) |
| view_cards | `get_observation({"preset":"full"})` | [view_cards-03-get_observation-full.json](view_cards-03-get_observation-full.json) |
| view_cards | `inspect_selection({"preset":"full"})` | [view_cards-04-inspect_selection-full.json](view_cards-04-inspect_selection-full.json) |
| view_cards | `get_observation({"preset":"default"})` | [view_cards-05-get_observation-default.json](view_cards-05-get_observation-default.json) |
| view_cards | `inspect_selection({"preset":"default"})` | [view_cards-06-inspect_selection-default.json](view_cards-06-inspect_selection-default.json) |
| view_cards | `get_observation({"preset":"summary"})` | [view_cards-07-get_observation-summary.json](view_cards-07-get_observation-summary.json) |
| view_cards | `inspect_selection({"preset":"summary"})` | [view_cards-08-inspect_selection-summary.json](view_cards-08-inspect_selection-summary.json) |
