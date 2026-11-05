# set_selection_view 修复后的典型返回

以下六份 JSON 是 Mod 0.67.0、MCP 0.69.0 的真实 stdio MCP full 结果，仅提取通过场景的公共内容；不添加原生快照或执行标记。成功结果已采用 actions_only 内容，保留 default/full 参数，没有新增 actions_only 预设。

定稿见[工具审阅](../2026-11-05-selection-view-review.md#设计定稿)，验证及边界见[实施记录](../2026-11-05-selection-view-results-implementation.md)；旧六份完整观察保留在[审阅基线](../2026-11-05-selection-view-examples/README.md)。manifest 记录请求参数、来源、从 1 起的序号和哈希。

| 完整返回 | 实际参数 |
| --- | --- |
| [battlefield.full.json](battlefield.full.json) | `{"preset":"full","view":"battlefield"}` |
| [selection.full.json](selection.full.json) | `{"preset":"full","view":"selection"}` |
| [no-selection.full.json](no-selection.full.json) | `{"preset":"full","view":"selection"}` |
| [covered.full.json](covered.full.json) | `{"preset":"full","view":"selection"}` |
| [eye-disabled.full.json](eye-disabled.full.json) | `{"preset":"full","view":"selection"}` |
| [eye-absent.full.json](eye-absent.full.json) | `{"preset":"full","view":"selection"}` |
