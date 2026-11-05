# set_selection_view 典型 full 返回

六份 JSON 均为当前 Mod 0.66.1、MCP 0.68.1 的真实 stdio MCP 公共返回，来自通过场景；保留当前笼统错误及恢复缺陷。成功样例是完整基础观察，没有人为压缩字段或加入内部快照、执行证据。

场景和输出建议见[审阅](../2026-11-05-selection-view-review.md)，核验及未验证边界见[开发记录](../2026-11-05-selection-view-development-notes.md)。不为相同结构的每个变体重复生成 JSON；manifest 记录参数、来源、从 1 起的记录序号和哈希。

| 场景 | 实际参数 | 完整返回 |
| --- | --- | --- |
| overlay | `{"preset":"full","view":"battlefield"}` | [overlay-battlefield.full.json](overlay-battlefield.full.json) |
| overlay | `{"preset":"full","view":"selection"}` | [overlay-selection.full.json](overlay-selection.full.json) |
| hand_upgrade | `{"preset":"full","view":"selection"}` | [hand-upgrade-selection.full.json](hand-upgrade-selection.full.json) |
| no_selection | `{"preset":"full","view":"selection"}` | [no-selection.full.json](no-selection.full.json) |
| covered_deck | `{"preset":"full","view":"selection"}` | [covered-deck.full.json](covered-deck.full.json) |
| noncombat | `{"preset":"full","view":"selection"}` | [noncombat-eye-unavailable.full.json](noncombat-eye-unavailable.full.json) |
