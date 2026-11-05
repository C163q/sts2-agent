# claim_reward 典型完整返回

基线为 43ea846；样本来自真实 stdio MCP 图形核验，保留完整 structuredContent。共 15 份，14 份 full 和 1 份 default，均无图片。场景、问题及未验证范围见[审阅记录](../2026-11-05-claim-reward-review.md)。

错误样本保留修复前行为；after-rejection 展示此前拒绝导致操作许可丢失。互斥金币样本也可作为普通金币的 full 回执结构参考。not_obtained 仅核对源码与现有 Python 检查，未伪造实测样本。

调用参数、原始证据位置／序号及 SHA-256 见 [manifest.json](manifest.json)。

| 完整 JSON | 场景 | 调用参数 |
| --- | --- | --- |
| [gold.default.json](gold.default.json) | 金币领取，default | `{"preset":"default","reward_id":0}` |
| [gold-linked.full.json](gold-linked.full.json) | 金币领取，互斥奖励组同时移除 | `{"preset":"full","reward_id":12}` |
| [potion.full.json](potion.full.json) | 取得药水 | `{"preset":"full","reward_id":2}` |
| [special-card.full.json](special-card.full.json) | 指定卡牌加入牌组 | `{"preset":"full","reward_id":4}` |
| [relic.full.json](relic.full.json) | 遗物与永久卡牌升级 | `{"preset":"full","reward_id":3}` |
| [card-choice.full.json](card-choice.full.json) | 打开卡牌奖励 | `{"preset":"full","reward_id":5}` |
| [full-belt.full.json](full-belt.full.json) | 满药水槽，not_claimed | `{"preset":"full","reward_id":8}` |
| [nested-rewards.full.json](nested-rewards.full.json) | 遗物打开嵌套奖励，pending/action_completed | `{"preset":"full","reward_id":15}` |
| [relic-transform.full.json](relic-transform.full.json) | 遗物打开变牌选择 | `{"preset":"full","reward_id":29}` |
| [stolen-card-returned.full.json](stolen-card-returned.full.json) | 追回被偷的卡牌 | `{"preset":"full","reward_id":21}` |
| [already-claimed.full.json](already-claimed.full.json) | 重复领取已经消失的奖励 | `{"preset":"full","reward_id":0}` |
| [after-rejection.full.json](after-rejection.full.json) | 拒绝后合法领取仍要求观察 | `{"preset":"full","reward_id":2}` |
| [map-covered.full.json](map-covered.full.json) | 地图覆盖时拒绝领取 | `{"preset":"full","reward_id":23}` |
| [selection-covered.full.json](selection-covered.full.json) | 卡牌选择覆盖时拒绝领取 | `{"preset":"full","reward_id":5}` |
| [wrong-scene.full.json](wrong-scene.full.json) | 战斗中没有奖励页 | `{"preset":"full","reward_id":0}` |
