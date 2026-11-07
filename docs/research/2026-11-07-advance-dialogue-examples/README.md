# advance_dialogue 典型返回

核验基线e325609，Mod0.78.1、MCP0.80.1、schema46。17份未裁剪JSON：14份为本轮实际MCP返回；3份full示例由本轮原生实测响应经过现行输出流程生成，不能计作额外的MCP实测。后者包括先古对话中段，以及两个实际default成功回执对应的full。调用参数、原始行、生成类型及SHA-256见[manifest.json](manifest.json)。

[审阅报告](../2026-11-07-advance-dialogue-review.md)；[开发核验](../2026-11-07-advance-dialogue-development-notes.md)。

| 文件 | 场景与来源 |
| --- | --- |
| [ancient.default.json](ancient.default.json) | 实际default：推进到馈赠 |
| [ancient.full.json](ancient.full.json) | 原生实测响应生成full：对话中段 |
| [ancient-to-gifts.full.json](ancient-to-gifts.full.json) | 同次实测响应生成full：推进到馈赠 |
| [architect.default.json](architect.default.json) | 实际default：建筑师推进到最终按钮 |
| [architect-to-proceed.full.json](architect-to-proceed.full.json) | 同次实测响应生成full：建筑师推进到最终按钮 |
| [wrong-room.full.json](wrong-room.full.json) | 错误房间 |
| [no-dialogue.full.json](no-dialogue.full.json) | 已展开馈赠，无待推进对话 |
| [gift-finished.full.json](gift-finished.full.json) | 馈赠已领取 |
| [map-covered.full.json](map-covered.full.json) | 先古对话被地图覆盖 |
| [deck-covered.full.json](deck-covered.full.json) | 建筑师被牌组覆盖 |
| [selection-covered.full.json](selection-covered.full.json) | 卡牌包选择覆盖 |
| [architect-final.full.json](architect-final.full.json) | 建筑师最终按钮应使用proceed |
| [stale.full.json](stale.full.json) | 外部推进后的旧观察 |
| [cold.full.json](cold.full.json) | 首次动作没有观察许可 |
| [local-invalid.full.json](local-invalid.full.json) | 本地拒绝额外参数 |
| [proceed-after-rejection.full.json](proceed-after-rejection.full.json) | 拒绝后前进仍要求观察 |
| [direct-close-map.full.json](direct-close-map.full.json) | 关闭地图不要求玩法许可，已可直接调用 |
