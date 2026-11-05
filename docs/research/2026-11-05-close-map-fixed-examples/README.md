# close_map 修复后的典型 JSON

文件保存真实 stdio MCP 的完整 structuredContent，保留实际错误原因和恢复指引；不是手写候选。Mod0.69.0、MCP0.71.0、schema41，DLL d188e26338c54fa7687bbf02ed43fd96d037b72027410a43f7b007a5ea6bcb4f。测试局经夹具准备，不代表正常开局。

- [combat.full.json](combat.full.json)：参数 `{"preset": "full"}`。
- [combat.default.json](combat.default.json)：参数 `{"preset": "default"}`。
- [event.full.json](event.full.json)：参数 `{"preset": "full"}`。
- [selection.full.json](selection.full.json)：参数 `{"preset": "full"}`。
- [divination.full.json](divination.full.json)：参数 `{"preset": "full"}`。
- [no-permission.full.json](no-permission.full.json)：参数 `{"preset": "full"}`。
- [retained.full.json](retained.full.json)：参数 `{"preset": "full"}`。
- [covered.full.json](covered.full.json)：参数 `{"preset": "full"}`。
- [mandatory.full.json](mandatory.full.json)：参数 `{"preset": "full"}`。

成功只含 scene/screen、available_actions 和适用 selection.type/status；无 transition、notes、场景主体或图像。divination.full.json 的图像块计数为 0，需要棋盘时另行观察。没有初始许可的拒绝仍要求观察，明确未交互且已有许可的拒绝允许 choose_legal_action。

[manifest.json](manifest.json) 记录原证据下标、调用参数、内容块计数和 SHA-256。完整验证与范围见[实施记录](../2026-11-05-close-map-results-implementation.md)。[原审阅样本](../2026-11-05-close-map-examples/README.md)保留修复前行为，不能混作当前返回。
