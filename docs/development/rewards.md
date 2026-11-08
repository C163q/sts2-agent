# 战后搜刮与前进

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

本接口逐项操作原生奖励界面；地图选路另用 `travel_to_node`。地图查看继续使用 `inspect_map` / `close_map`，卡牌奖励继续使用[选牌工具](card-selection.md)。

含 null 的字段说明与示例按 full 表达；默认输出的空值处理见[公共预设](mcp.md#输出预设)。

页面主体的展示进度见[共用展示状态](observation.md#页面主体的展示状态)，按钮启用状态按当前操作条件判断。

## 观察与详情

`get_observation` 在奖励阶段返回 `scene: "rewards"` 和 `rewards`。这也覆盖奖励领完后只剩前进按钮的页面。被地图、选牌或其他页面覆盖时，`rewards.status` 为 `covered`，标题、条目和按钮均为 `null`。

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
  }
}
```

这是节选；完整观察还包含可见顶栏、选择状态等公共字段，并可能提供药水动作。基础观察与 inspect_rewards 读取整张可滚动奖励列表，保留当前顺序和滚动位置；行和标签须实际显示。领取画外条目时先滚动到原生可点击位置。

| 字段 | 含义 |
| --- | --- |
| `id` | 稳定整数奖励 ID，领取其他项目后仍保留；作为 claim_reward 的 reward_id 使用 |
| `type` | `gold`、`potion`、`relic`、`card`、`special_card`、`card_removal` 或 `unsupported` |
| `text` | 原生奖励行的英语文本；追回金币有对应标注，特殊卡牌保留原生描述 |
| `enabled` | 这行当前可以由工具点击；未支持类型为 `false` |
| `linked_group` | 同组互斥奖励的共同 ID，普通独立奖励为 `null` |
| `proceed` | 当前显示的原生跳过/前进按钮；未显示为 `null` |
| `skips_remaining` | 按钮当前处于原生 Skip 模式；具体后续流程仍由游戏决定 |

标题区分搜刮与被抢劫等 UI 状态；逃脱、金币比例和追回内容按当前原生奖励行的实际文本呈现。

### inspect_rewards 预设与筛选

MCP 的 inspect_rewards 返回 scene/screen 与 rewards，支持 default/full/summary：

| 预设 | 奖励内容 |
| --- | --- |
| full | 完整奖励行和每行 hover_tips，保留普通 null |
| default（默认） | full 应用统一空值规则 |
| summary | 静态奖励行，保留状态、标题、id/type/text/enabled/linked_group 和 proceed，应用 default 空值规则 |

get_observation 的 full/default/summary 均使用静态奖励格式；full 保留普通 null，default/summary 的 rewards 与未筛选的 inspect_rewards.summary 一致。点开卡牌奖励后，inspect_selection 提供候选牌及选择按钮。可用操作列表通过 get_observation 获取。

reward_ids 按当前最上层奖励页的 items[].id 筛选。省略或 null 取全部，[] 取空；重复 ID 去重，结果保留原生顺序。title 和 proceed 保留整页内容，每行使用已有 id 标识。未找到的 ID 按请求顺序合并到 errors，例如：

```json
{"errors":[{"code":"reward_ids_not_found","reward_ids":[99,100]}]}
```

有效行同时返回。完整响应先通过格式与可见性一致性校验，再应用预设和筛选。

纯读取的明确拒绝保留已有操作许可。提示区分无奖励、地图／牌组／选择覆盖、预览、过渡及动作等待；首次读取失败仍需取得有效观察。读取可用性与基础观察的工具列表共用同一检查。接口样本与验证范围见[奖励详情实施](../research/2026-11-05-reward-inspection-presets-implementation.md)。

## 领取与后续选择

`claim_reward({"reward_id": 5})` 点击一行，按模型选择的顺序执行。每次领取后由模型根据返回结果决定下一项、后续选牌或药水槽位操作。领取遗物可能立即改变牌组或后续奖励，因此每次都应阅读返回结果再决定下一项。

动作返回[精简回执](mcp.md#动作返回格式)，保留 `transition` 和 `reward_result`：

```json
{"reward_result": {"reward_id": 1, "status": "not_claimed"}}
```

`status` 为 `claimed`、`not_claimed`、`not_obtained` 或 `pending`。`not_obtained` 表示药水奖励行已被原生处理并消耗，但玩家没有获得该药水，例如添水禁止获取；后续以当前奖励行和药水栏为准。满槽等原生拒绝通常返回 `not_claimed`，保留奖励行；需要腾出药水槽时，由模型另外调用 `discard_potion` 或合法的 `use_potion`，再决定是否领取。`pending` 表示已进入选择或后续交互，不能据此认为已获得奖励，也不能自动重试。`complete` 仍只确认 `stop_reason` 所述边界。

点开卡牌奖励后，在已显示的候选中使用 `select_card`，或点击当前 `selection.options` 提供的 `selection_option`。卡牌奖励的 Skip 与整页跳过不同：原生通常返回搜刮列表并保留这一奖励入口，可以重新打开。奖励卡牌启用和入场动画完成后才返回可继续选择的边界。已识别的原生大卡预览存在时，奖励视为被覆盖；等待其结束后再提供奖励动作。领取遗物若打开另一张奖励页，到达新页面即返回，供模型继续决策。

佩尔之翼的献祭、浮木的重掷同样使用[卡牌奖励替代按钮](card-selection.md#卡牌奖励替代按钮)，通过 selection_option 点击当前替代按钮。

动作沿用[MCP 动作许可](mcp.md#调用和错误语义)：成功读取及完整动作结果可以续接下一步，查看页关闭后无需额外观察。claim_reward 在滚动／点击前明确拒绝时保留已有许可，错误会说明奖励 ID 已不存在、地图／牌组／选择覆盖、尚未就绪等原因，可按 recovery 纠正或改用合法动作。首次调用仍需已有有效观察。

第一次滚动及点击即标记交互；滚动后拒绝、状态过期、超时和未知结果须重新观察。proceed 的点击前明确拒绝按[MCP 许可规则](mcp.md#调用和错误语义)保留已有许可。成功领取响应须先完整校验，并核对 reward_result.reward_id 与本次请求一致；矛盾响应返回 transport_error，清除操作许可。

## 跳过、前进和地图

`proceed()` 只点击奖励页当前暴露且启用的原生按钮。尚有奖励时常显示 Skip，全部领取后列表淡出、按钮显示 Proceed；没有掉落的终结奖励页也能提供 Proceed。剩余条目的领取由独立 claim_reward 操作决定。

普通战斗后按钮通常打开地图，地图顶栏入口也可在搜刮时直接使用。打开地图保留当前房间，旅行时沿原生流程放弃剩余奖励。查看地图会隐藏奖励内容。原生允许返回时，关闭地图的成功结果可直接续接搜刮；奖励变化时按需读取详情。

Boss 或特殊事件战斗的前进沿原生流程进入下一幕、结束本局或返回父事件。返回[通用事件](events.md)后，继续等待其 `Resume` 任务、卡牌预览和资源动画；若出现子奖励或选择则先返回该输入边界。未支持的原生对话或页面立即返回 `manual_input_required` 并清除动作许可，避免一直等待玩家输入。地图旅行见[选路接口](map-inspection.md#地图选路)；终章对话与结局页使用[终章与结算接口](run-ending.md)。

## 实现与验证

游戏侧由 RewardInspection.cs 采样 UI 和奖励身份、提供共用查看／领取诊断与行可领取判断，GameAdapter.Rewards.cs 使用共用领取判断并点击原生按钮，领取与后续界面由原生流程负责。`RewardCompatibility.cs` 只适配目标版本互斥奖励中已核实的信号参数错误，保留原生领取与收尾流程。外部层由 reward_details.py 验证字段与可见性上下文，action_details.py 核对领取结果与请求 ID，reward_presets.py 在校验后生成摘要和筛选；参数与许可遵循共用 MCP 流程。

奖励详情的隔离图形核验先按[往返指南](roundtrip.md)准备运行目录，再执行：

```sh
.tmp/mcp-venv/bin/python scripts/gui_suite.py --suite tests/game/data/gui_suite_reward_inspection_review.json --output .tmp/reward-inspection-review
```

输出目录须全新；套件拥有测试游戏与存档，会实际读取、领取、覆盖奖励并旅行离开房间，用于核对预设、ID 筛选、基础观察对照、完整列表、稳定身份、互斥／嵌套／追回、空列表与错误后续接，并运行旧领取流程。范围及证据见[奖励详情实施](../research/2026-11-05-reward-inspection-presets-implementation.md)。

全流程入口 [verify_rewards.py](../../tests/game/verifiers/verify_rewards.py) 通过当前工具目录核对发现结果，basic 场景由上述套件准备并验证，随后原生旅行完成夹具清理。其他历史分支的范围见[奖励调研](../research/2026-10-31-rewards.md)。

领取验证使用 [claim_reward_review 清单](../../tests/game/data/gui_suite_claim_reward_review.json)，入口与输出约定同上，替换 --suite 和独立输出目录即可。它采集正常领取、满槽、互斥、嵌套、追回、覆盖与拒绝后的真实返回，验证明确拒绝后直接操作、成功滚动及滚动后失败须观察。滚动失败使用双重测试门控扰动，finally 和局间重置恢复；验证范围见[领取修复记录](../research/2026-11-05-claim-reward-recovery-implementation.md)。
