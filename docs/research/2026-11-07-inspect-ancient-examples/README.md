# inspect_ancient 典型实测返回

2026-11-07，基线 `831975d`，Mod 0.77.2、MCP 0.79.2、schema 45。共16份实际MCP返回，14份full、1份default，以及1份不支持summary的错误；未裁剪字段。基础观察及结束回合样本用于对照，其他为inspect_ancient。参数、原始证据行及哈希见[manifest.json](manifest.json)。

[审阅与建议](../2026-11-07-inspect-ancient-review.md)；[开发核验与验证限制](../2026-11-07-inspect-ancient-development-notes.md)。

| 返回 | 场景 |
| --- | --- |
| [not-ancient.full.json](not-ancient.full.json) | 无先古之民时的拒绝 |
| [legal-after-rejection.full.json](legal-after-rejection.full.json) | 错误查看后直接结束回合 |
| [arrival.full.json](arrival.full.json) | 刚进入房间、选项尚未稳定 |
| [choices.full.json](choices.full.json) | 普通三选一、选项已启用 |
| [choices-observation.full.json](choices-observation.full.json) | 基础观察中的同类先古主体 |
| [returning.default.json](returning.default.json) | 牌组返回后、短暂过渡中的default |
| [map-covered.full.json](map-covered.full.json) | 地图覆盖时拒绝 |
| [deck-covered.full.json](deck-covered.full.json) | 牌组覆盖时拒绝 |
| [summary-unsupported.json](summary-unsupported.json) | 当前不支持summary的本地参数错误 |
| [dialogue.full.json](dialogue.full.json) | 已显示对话与继续按钮 |
| [dialogue-finished.full.json](dialogue-finished.full.json) | 对话完成后可选择 |
| [relic-references.full.json](relic-references.full.json) | 欧洛巴斯：当前角色遗物与卡牌的悬停解释 |
| [obtained.full.json](obtained.full.json) | 获得馈赠后只剩前进按钮 |
| [selection-covered.full.json](selection-covered.full.json) | 变牌选择覆盖时拒绝 |
| [bundle-covered.full.json](bundle-covered.full.json) | 卡牌包选择覆盖时拒绝 |
| [rewards-covered.full.json](rewards-covered.full.json) | 嵌套奖励覆盖时拒绝 |

arrival与returning展示合法的读取中间态，须以当前enabled判断是否可操作。summary-unsupported由MCP本地校验拒绝，没有发送原生请求。其余返回均有对应原生响应；原始令牌、测试状态及游戏截图保留在忽略的.tmp证据目录。
