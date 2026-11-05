# loot_treasure 典型完整返回

基线8753038，17份真实stdio MCP完整structuredContent，16份full、一份default，均无图片。问题、行为和参数建议见[审阅记录](../2026-11-06-loot-treasure-review.md)。

空箱的events:[]是正常完成；嵌套奖励的complete:true表示到达输入边界。disabled样本来自已有双重门控显示扰动，不作为自然复现。错误样本保留修复前的笼统原因和许可丢失行为。

每份实际参数、来源和SHA-256见[manifest.json](manifest.json)。

| 完整 JSON | 场景 | 调用参数 |
| --- | --- | --- |
| [default-complete.full.json](default-complete.full.json) | 默认开箱并领取 | `{"preset":"full"}` |
| [open-only.full.json](open-only.full.json) | 只开箱，记录金币变化 | `{"preset":"full","open_only":true}` |
| [take-opened.default.json](take-opened.default.json) | 已开箱后领取，default | `{"preset":"default","open_only":false}` |
| [empty-chest.full.json](empty-chest.full.json) | 空箱正常完成，events为空 | `{"preset":"full"}` |
| [extra-rewards.full.json](extra-rewards.full.json) | 额外奖励中止自动领取 | `{"preset":"full"}` |
| [explicit-take-after-extra.full.json](explicit-take-after-extra.full.json) | 处理额外奖励后显式领取 | `{"preset":"full"}` |
| [nested-rewards.full.json](nested-rewards.full.json) | 取得遗物后停在嵌套奖励 | `{"preset":"full"}` |
| [card-choice.full.json](card-choice.full.json) | 取得遗物后停在变牌选择 | `{"preset":"full"}` |
| [map-after-obtain.full.json](map-after-obtain.full.json) | 遗物延迟效果打开地图并完成 | `{"preset":"full"}` |
| [already-open.full.json](already-open.full.json) | 已开箱再次要求只开箱 | `{"preset":"full","open_only":true}` |
| [after-rejection.full.json](after-rejection.full.json) | 拒绝后合法领取被迫观察 | `{"preset":"full"}` |
| [empty-or-collected.full.json](empty-or-collected.full.json) | 已领取后再次操作 | `{"preset":"full"}` |
| [map-covered.full.json](map-covered.full.json) | 地图覆盖的拒绝 | `{"preset":"full"}` |
| [selection-covered.full.json](selection-covered.full.json) | 选牌覆盖的拒绝 | `{"preset":"full"}` |
| [disabled.full.json](disabled.full.json) | 人工禁用遗物的拒绝 | `{"preset":"full"}` |
| [no-observation.full.json](no-observation.full.json) | 无初始观察 | `{"preset":"full"}` |
| [wrong-scene.full.json](wrong-scene.full.json) | 非宝箱房的拒绝 | `{"preset":"full"}` |
