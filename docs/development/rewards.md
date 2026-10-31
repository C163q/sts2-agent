# 战后搜刮与前进

适用于 Mod `0.28.0`、MCP server `0.24.0`、Linux 游戏 `v0.107.1` 和 RitsuLib `0.6.10`。本接口逐项操作原生奖励界面，不选择地图节点。地图查看继续使用 `inspect_map` / `close_map`，卡牌奖励继续使用[选牌工具](card-selection.md)。

## 观察与详情

`get_observation` 在奖励阶段返回 `scene: "rewards"` 和 `rewards`。这也覆盖奖励领完后只剩前进按钮的页面。被地图、选牌或其他页面覆盖时，`rewards.status` 为 `covered`，标题、条目和按钮均为 `null`，不能领取隐藏奖励。

基础观察中的奖励示例：

```json
{
  "scene": "rewards",
  "rewards": {
    "status": "visible",
    "title": "Loot!",
    "items": [
      {"id": 0, "type": "gold", "text": "17 Gold", "enabled": true, "linked_group": null},
      {"id": 1, "type": "potion", "text": "Block Potion", "enabled": true, "linked_group": null},
      {"id": 5, "type": "card", "text": "Add a card to your deck.", "enabled": true, "linked_group": null}
    ],
    "proceed": {"text": "Skip", "enabled": true, "skips_remaining": true}
  },
  "available_actions": ["claim_reward", "proceed"]
}
```

这是节选；完整观察还包含可见顶栏、选择状态等公共字段，并可能提供药水动作。基础观察只列当前屏幕可见的奖励行。`inspect_rewards()` 返回当前整张可浏览奖励列表，每行另附 `hover_tips`；不会提前查看尚未打开的卡牌奖励候选，也不会生成或重抽奖励。两种读取都不改变奖励顺序。

| 字段 | 含义 |
| --- | --- |
| `id` | 稳定整数奖励 ID；领取其他项目后不重排，不是卡牌 ID 或药水槽位 |
| `type` | `gold`、`potion`、`relic`、`card`、`special_card`、`card_removal` 或 `unsupported` |
| `text` | 原生奖励行的英语文本；追回金币有对应标注，特殊卡牌保留原生描述 |
| `enabled` | 这行当前可以由工具点击；未支持类型为 `false` |
| `linked_group` | 同组互斥奖励的共同 ID，普通独立奖励为 `null` |
| `proceed` | 当前显示的原生跳过/前进按钮；未显示为 `null` |
| `skips_remaining` | 按钮当前处于原生 Skip 模式；具体后续流程仍由游戏决定 |

标题保留搜刮与被抢劫等可见区别。只呈现实际掉落，不根据敌人类型补发被偷的牌或金币。怪物逃离可能改变金币比例和追回条目，但不会被工具当成一种固定奖励模板。

## 领取与后续选择

`claim_reward({"reward_id": 5})` 点击一行，按模型选择的顺序执行。工具不连领、不自动选择卡牌，也不自动丢弃已有药水。领取遗物可能立即改变牌组或后续奖励，因此每次都应阅读返回结果再决定下一项。

动作返回完整观察、`transition` 和 `reward_result`：

```json
{"reward_result": {"reward_id": 1, "status": "not_claimed"}}
```

`status` 为 `claimed`、`not_claimed`、`not_obtained` 或 `pending`。`not_obtained` 表示药水奖励行已被原生处理并消耗，但玩家没有获得该药水，例如添水禁止获取；不能把它当作已入栏或自动重试。满槽等原生拒绝通常返回 `not_claimed`，保留奖励行；需要腾出药水槽时，由模型另外调用 `discard_potion` 或合法的 `use_potion`，再决定是否领取。`pending` 表示已进入选择或后续交互，不能据此认为已获得奖励，也不能自动重试。`complete` 仍只确认 `stop_reason` 所述边界。

点开卡牌奖励后，在已显示的候选中使用 `select_card`，或点击当前 `selection.options` 提供的 `selection_option`。卡牌奖励的 Skip 与整页跳过不同：原生通常返回搜刮列表并保留这一奖励入口，可以重新打开。不能把卡牌候选 ID 传给 `claim_reward`。奖励卡牌启用和入场动画完成后才返回可继续选择的边界。已识别的原生大卡预览存在时，奖励视为被覆盖；等待其结束后再提供奖励动作。领取遗物若打开另一张奖励页，返回新页面供模型继续决策，不等待依赖后续操作的父任务。

两类动作沿用[MCP 动作许可](mcp.md#调用和错误语义)：首次先观察，完整成功结果可以续接下一步。失败、超时或切换查看页后重新观察。动作始终校验当前原始令牌和界面合法性。

## 跳过、前进和地图

`proceed()` 只点击奖励页当前暴露且启用的原生按钮。尚有奖励时常显示 Skip，全部领取后列表淡出、按钮显示 Proceed；没有掉落的终结奖励页也能提供 Proceed。不会自动领取剩余项目。

普通战斗后按钮通常打开地图，地图顶栏入口也可在搜刮时直接使用。打开地图不等于已经离开房间；剩余奖励的最终放弃时机由原生旅行流程决定。查看地图会隐藏奖励内容并清除动作许可。原生允许返回时，关闭地图后重新观察，再继续搜刮。

Boss 或特殊事件战斗的前进可能进入下一幕、结束本次游戏或返回父事件，而不是地图。工具沿用原生流程，不强行转换。返回[通用事件](events.md)后，继续等待其 `Resume` 任务、卡牌预览和资源动画；若出现子奖励或选择则先返回该输入边界。未支持的原生对话或页面立即返回 `manual_input_required` 并清除动作许可，避免一直等待玩家输入。结局页操作和地图旅行尚未开放。

## 实现与验证

游戏侧由 `RewardInspection.cs` 采样 UI 和奖励身份，`GameAdapter.Rewards.cs` 校验并点击原生按钮；不直接增加金币、卡牌、药水或遗物。`RewardCompatibility.cs` 只适配目标版本互斥奖励中已核实的信号参数错误，保留原生领取与收尾流程。外部层由 `reward_details.py` 验证参数、字段和结果，不输出内部令牌或未声明字段。

隔离图形测试先按[往返指南](roundtrip.md)准备运行目录，再启动：

```sh
python3 scripts/run_roundtrip.py --windowed --reward-scenario basic
```

在另一终端运行：

```sh
.tmp/mcp-venv/bin/python scripts/verify_rewards.py --scenario basic --report .tmp/rewards-check/basic.json
```

只允许新建的隔离实例；报告及截图目录须全新。该检查会实际领取奖励、跳过卡牌、打开地图和前进。其他场景参数与验证范围见[本次调研记录](../research/2026-10-31-rewards.md)。
