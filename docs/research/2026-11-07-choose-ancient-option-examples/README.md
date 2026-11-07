# choose_ancient_option 典型实测返回

2026-11-07，基线e4b1979，Mod0.78.0、MCP0.80.0、schema46。16份实际MCP返回，15份full、1份default，未裁剪字段。调用参数、原始证据行及哈希见[manifest.json](manifest.json)。

[核验与建议](../2026-11-07-choose-ancient-option-review.md)；[开发依据与未验证范围](../2026-11-07-choose-ancient-option-development-notes.md)。

| 文件 | 场景 |
| --- | --- |
| [normal.full.json](normal.full.json) | 普通馈赠：遗物、最大生命与生命反馈 |
| [replace.full.json](replace.full.json) | 替换遗物的完整反馈 |
| [replace.default.json](replace.default.json) | 纠正拒绝后刷新观察，default领取 |
| [transform.full.json](transform.full.json) | 领取后停在变牌选择 |
| [bundle.full.json](bundle.full.json) | 领取后停在卡牌包选择，事件数组为空 |
| [nested-rewards.full.json](nested-rewards.full.json) | 领取后停在额外奖励页 |
| [lethal-timeout.full.json](lethal-timeout.full.json) | 致死披风：运行时致命错误后MCP超时 |
| [unknown-option.full.json](unknown-option.full.json) | 不存在的选项ID被拒绝 |
| [correct-after-rejection.full.json](correct-after-rejection.full.json) | 纠正ID仍被要求重新观察 |
| [already-obtained.full.json](already-obtained.full.json) | 领取完毕后重复旧选项 |
| [dialogue-unfinished.full.json](dialogue-unfinished.full.json) | 对话未结束时选择馈赠 |
| [map-covered.full.json](map-covered.full.json) | 地图覆盖时选择馈赠 |
| [disabled.full.json](disabled.full.json) | 当前按钮已禁用 |
| [selection-covered.full.json](selection-covered.full.json) | 选牌覆盖时再次选择馈赠 |
| [stale.full.json](stale.full.json) | 外部已选择，旧观察正确拒绝 |
| [cold.full.json](cold.full.json) | 首次动作没有观察许可 |

lethal-timeout为实际超时错误，未收到原生成功回执；不能据此声称动作未执行。该实例日志有运行时致命错误，详见开发记录。cold及correct-after-rejection由MCP本地许可检查拒绝，无对应原生请求。
