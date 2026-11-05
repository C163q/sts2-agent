# inspect_rewards 典型完整 JSON

以下为[审阅基线](../2026-11-05-inspect-rewards-development-notes.md)下真实 stdio MCP 的完整 structuredContent，未手工删字段；除显式标出的 default 外，全部使用 preset:full。夹具准备隔离局面，不代表自然完整游玩。

| 场景 | JSON |
| --- | --- |
| 金币、药水、遗物、指定卡牌及未展开卡牌奖励 | [basic.full.json](basic.full.json) |
| 同一列表的 default，省略普通 null，保留空 hover_tips | [basic.default.json](basic.default.json) |
| 二选一互斥组，保留共同 linked_group 与悬停说明 | [linked.full.json](linked.full.json) |
| 空列表；标题已淡出为 null，按钮为 Proceed | [empty.full.json](empty.full.json) |
| 领取遗物后打开的子奖励页 | [nested.full.json](nested.full.json) |
| 敌人死亡后追回被偷卡牌与金币 | [returned.full.json](returned.full.json) |
| 敌人逃脱后的 Mugged... 标题与实际奖励，没有补回被偷卡牌 | [escaped.full.json](escaped.full.json) |
| 无初始许可时读取失败，要求观察 | [no-permission.full.json](no-permission.full.json) |
| 已有许可时奖励被选牌覆盖，保留许可；地图覆盖与非奖励页同样使用笼统原因 | [covered.full.json](covered.full.json) |

[manifest.json](manifest.json) 保存原始证据文件／数组下标、实际参数、图像块计数和 SHA-256。九份样本的图像块均为 0。上下文损坏探针没有混入这些真实返回。

领取后的稳定 ID、重复读取不变和拒绝后直接继续合法动作等证据见[开发核验](../2026-11-05-inspect-rewards-development-notes.md)；不是每个内容变体都单独导出一份 JSON。
