# 使用与丢弃药水

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

使用及丢弃均提交原生动作；游戏负责扣除药水、效果、记录和触发。依据见 [源码核对](../research/2026-10-30-potion-actions.md)。

下文输出字段的空值与 JSON 示例以底层文件或 MCP full 为准；MCP 工具另接受[通用 preset](mcp.md#输出预设)，默认 default 省略普通空值。

## 查询与定位

`inspect_targets({"potion_slot": 0})` 查询从左到右、从 0 开始的药水槽位，与基础观察 `top_bar.potion_slots` 的原始下标一致；药水详情经过 slot_indices 筛选后，使用返回的 slot_indices 对照，不能使用压缩后的数组位置。空槽保留位置；没有药水的槽位不能查询目标或执行动作。该工具提示卡牌或药水可指定的目标，并报告当前可用性；已知当前合法目标时无需先查询。它仍支持 [手牌的 `card_id`](card-play.md)，两个定位参数只能提供一个。

返回结构示例，名称及数值仅为说明：

```json
{
  "potion": {"slot_index": 0, "name": "Fruit Juice"},
  "usable": true,
  "discardable": true,
  "target_type": "any_player",
  "requires_target": false,
  "targets": [{"id": "self", "kind": "player", "name": "The Ironclad"}],
  "reason": null
}
```

- `usable` 表示当前允许请求使用；`reason` 是不能使用的简短原因，否则为 `null`。这不是效果预测或未来执行保证。
- `discardable` 单独报告能否丢弃。例如瓶中精灵不能手动用，但通常能丢弃；禁止移除药水时两者都为 `false`。
- `target_type` 为已核对的 `self/any_player/any_enemy/all_enemies/targeted_no_creature`。`requires_target` 决定请求是否必须带目标，不直接等同于目标类型是否含“单体”。
- `targets` 是当前可指定对象或指示范围，不保证列出全部效果对象。战斗生物 ID 为整数，与敌人观察一致；战斗外自身为 `self`，商人为 `merchant`。不预抽随机目标或生成未来候选，不附送药水正文。

查询不会打开菜单或进入瞄准，成功时刷新状态令牌。药水正文通过 [inspect_potions](potion-inspection.md) 读取。

## 动作

```json
{"potion_slot": 0, "target_id": 2}
```

上述参数用于需要选敌人的 `use_potion`。不要求目标时调用 `use_potion({"potion_slot": 0})`；丢弃调用 `discard_potion({"potion_slot": 0})`，不能附带目标。要求指定时，即使只有一个候选也必须提供；不要求时必须省略，`null` 不等于省略。槽位接受 `0..2147483647` 整数，目标接受 `0..4294967295` 战斗 ID 或字符串 `merchant`；不接受布尔、浮点及数字字符串。

单人模式下正面 `AnyPlayer` 药水直接用于自己；果汁、血瓶等允许战斗外使用。原生多人战斗可以选其他玩家，但战斗外仍直接用于自己；本项目尚不支持真正多人联机，不能把源码结论视为联机验证。

`Foul Potion`在战斗中无需指定目标；战斗外须处于可向商人投掷的原生界面，查询会列出 `merchant`，调用 `use_potion({"potion_slot": 0, "target_id": "merchant"})`。库存页面关闭且商人按钮可见时才允许；不以直接加钱替代投掷流程。

两种动作使用成功读取或满足续接条件的动作结果提供的当前许可。明确未进行操作的参数、页面、槽位或目标拒绝会说明具体原因，保留已有许可，可直接改参数或选择其他合法操作；没有旧许可时不会因失败得到许可。状态过期、已开始操作、取消及无法确认结果时仍须重新读取，完整条件见[MCP 动作许可](mcp.md#调用和错误语义)。提交前重查阶段、队列、可见槽位、药水归属、排队状态、移除限制、自定义可用性及目标；同一槽换成同名药水也会使旧令牌失效。连续使用药水时，每次提交使用的是上一结果的新令牌，不能重复使用旧快照。

## 场景与停止边界

支持正常单人可行动战斗，以及顶栏可见、原生条件允许交互的战斗外页面，例如事件、先古之民、休息处、宝箱、商店、地图、奖励及占卜。战斗外基础观察提供可见顶栏与生命数字，`player/enemies/turn/buttons` 保持为空；普通事件的范围见[事件接口](events.md)。主菜单、过渡、模态、其他卡牌页、忙碌队列、父事件结算和选择期间不能执行药水动作；原生等待可操作子奖励页时可按规则腾出药水槽。

药水槽位按各自的展示与交互状态判断，不按屏幕坐标截断；其他槽位不能点击或悬停，不会使正常槽位也失效。已显示但不能交互的药水仍可查询目标范围，此时 usable/discardable 为 false，并给出原因；真正隐藏或无法识别的目标槽位拒绝查询与动作。

药水触发选择时立即返回 `choice_required`；使用 [选牌工具](card-selection.md) 继续，可通过原生眼睛查看战场。查看期间仍禁止使用和丢弃药水。技能/攻击/能力/无色药水的候选只在实际生成后通过观察或 `inspect_selection` 提供；液态记忆和赌徒佳酿分别沿用牌堆、手牌选择。

结果采用[精简动作回执](mcp.md#动作返回格式)，包含 [transition](end-turn.md)。战斗中停止于 `player_ready/choice_required/combat_won/combat_lost`；战斗外已完成动作时为 `action_completed`。原生取消后恢复可行动为 `action_canceled`；超时或中断不代表动作没有执行，不能自动重发。

`potion_used/potion_discarded` 记录已见药水的槽位和名称，使用事件表示药水已被原生使用流程移除，不代表所有后续效果已完成。记录依据此前已显示的药水身份与仍暴露的槽位，不要求已移除的旧图标还在，也不要求其他槽位能点击；隐藏期间不补记用药，恢复显示后不回放。伤害等沿用现有战报；药水自动触发也可出现在结束回合等其他动作的记录中。不声称提供完整资源变化或因果树。

## 验证

隔离实例入口：`python3 scripts/run_roundtrip.py --potion-scenario basic`。另一终端执行：

```sh
.tmp/mcp-venv/bin/python -m tests.game.verifiers.verify_potion_actions --scenario basic --report .tmp/roundtrip/potion-basic.json
```

测试场景只在独立测试模式配置初始状态，不能用于正式对局。标准库客户端提供 `inspect_targets --potion-slot 0`、`use_potion --potion-slot 0 --target-id 2 --expected-state <令牌>` 和 `discard_potion --potion-slot 0 --expected-state <令牌>`；均须传 `--ipc-dir`。MCP 内部管理令牌。实际通过范围及限制见 [验证记录](../research/2026-10-30-potion-actions-validation.md)。

商店观察可显示恶臭药水当前 `usable_here` 提示及实际 `bouncing` 状态。商品页须先用 `close_shop` 关闭，原生目标才可用；假商人触发战斗时，等待新战斗可行动或选择边界，详见[商店接口](shop.md#恶臭药水与假商人)。

[药水动作 GUI 清单](../../tests/game/data/gui_suite_potion_recovery.json)验证明确拒绝后的直接继续、单槽交互、可见使用／获得事件、隐藏边界及地图中的连续用药。实际通过范围、独立审查与完整返回见[修复验证记录](../research/2026-11-05-potion-actions-implementation.md)。
