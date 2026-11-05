# close_map 审阅基线的典型完整 JSON

基线 b6eb397、Mod 0.68.0、MCP 0.70.0，实际 DLL 为 1ffb82d5790e9bc51729c44e092223ce0faa511cb302f08627bbc8820fd8d774。文件保存真实 stdio MCP 的完整 structuredContent，保留当前 null、列表及 note；不是修复后输出。测试局经夹具准备，不代表正常开局数值。

- [combat.full.json](combat.full.json)：`close_map`，参数 `{"preset": "full"}`。
- [event.full.json](event.full.json)：`close_map`，参数 `{"preset": "full"}`。
- [selection.full.json](selection.full.json)：`close_map`，参数 `{"preset": "full"}`。
- [divination.full.json](divination.full.json)：`close_map`，参数 `{"preset": "full"}`。
- [rejected.full.json](rejected.full.json)：`close_map`，参数 `{"preset": "full"}`。
- [selection-observation.full.json](selection-observation.full.json)：`get_observation`，参数 `{"preset": "full"}`。

selection.full.json 缺少结构化 selection，但仍有 notes.selection；selection-observation.full.json 是同场景随后显式读取的完整基础观察，用于对照。当前各种拒绝对外 JSON 相同，使用一份代表样本，其他原因的原生证据见审阅记录。

divination.full.json 之外还返回 1 个 PNG 图像内容块；PNG 不属于 structuredContent，本阶段仅记录计数，未另存图像文件。占卜 JSON 的字段没有因此裁剪。

[manifest.json](manifest.json) 保存调用参数、原 evidence.json 下标、图像块数量与输出 SHA-256。场景、问题和建议见[审阅](../2026-11-05-close-map-review.md)，源码与验证界限见[开发核验](../2026-11-05-close-map-development-notes.md)。
