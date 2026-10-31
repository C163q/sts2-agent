# 使用与丢弃药水

适用于 Mod `0.29.0`、MCP server `0.25.0`、Linux 游戏 `v0.107.1` 和 RitsuLib `0.6.10`。使用及丢弃均提交原生动作；游戏负责扣除药水、效果、记录和触发。依据见 [源码核对](../research/2026-10-30-potion-actions.md)。

## 查询与定位

`inspect_targets({"potion_slot": 0})` 查询从左到右、从 0 开始的药水槽位，与基础观察 `top_bar.potion_slots` 及药水详情的下标一致。空槽保留位置；没有药水的槽位不能查询目标或执行动作。该工具仍支持 [手牌的 `card_id`](card-play.md)，两个定位参数只能提供一个。

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

查询不会打开菜单、进入瞄准或准备动作许可。已有许可只在成功且快照不变时保留。药水正文通过 [inspect_potions](potion-inspection.md) 读取。

## 动作

```json
{"potion_slot": 0, "target_id": 2}
```

上述参数用于需要选敌人的 `use_potion`。不要求目标时调用 `use_potion({"potion_slot": 0})`；丢弃调用 `discard_potion({"potion_slot": 0})`，不能附带目标。要求指定时，即使只有一个候选也必须提供；不要求时必须省略，`null` 不等于省略。槽位接受 `0..2147483647` 整数，目标接受 `0..4294967295` 战斗 ID 或字符串 `merchant`；不接受布尔、浮点及数字字符串。

单人模式下正面 `AnyPlayer` 药水直接用于自己；果汁、血瓶等允许战斗外使用。原生多人战斗可以选其他玩家，但战斗外仍直接用于自己；本项目尚不支持真正多人联机，不能把源码结论视为联机验证。

`Foul Potion`在战斗中无需指定目标；战斗外须处于可向商人投掷的原生界面，查询会列出 `merchant`，调用 `use_potion({"potion_slot": 0, "target_id": "merchant"})`。库存页面关闭且商人按钮可见时才允许；不以直接加钱替代投掷流程。

两种动作使用 `get_observation` 或上一步完整成功的动作结果提供的当前许可，失败后须重新观察，完整条件见[MCP 动作许可](mcp.md#调用和错误语义)。提交前重查阶段、队列、可见槽位、药水归属、排队状态、移除限制、自定义可用性及目标；同一槽换成同名药水也会使旧令牌失效。连续使用药水时，每次提交使用的是上一结果的新令牌，不能重复使用旧快照。

## 场景与停止边界

支持正常单人可行动战斗，以及当前可见、可交互顶栏所在的战斗外事件、休息点、商店、地图及奖励页。战斗外基础观察提供可见顶栏与生命数字，`player/enemies/turn/buttons` 保持为空；普通事件的范围见[事件接口](events.md)。主菜单、过渡、模态、其他卡牌页、忙碌队列、父事件结算和选择期间不能执行药水动作；原生等待可操作子奖励页时可按规则腾出药水槽。

药水触发选择时立即返回 `choice_required`；使用 [选牌工具](card-selection.md) 继续，可通过原生眼睛查看战场。查看期间仍禁止使用和丢弃药水。技能/攻击/能力/无色药水的候选只在实际生成后返回；液态记忆和赌徒佳酿分别沿用牌堆、手牌选择。

结果包含基础观察与 [transition](end-turn.md)。战斗中停止于 `player_ready/choice_required/combat_won/combat_lost`；战斗外已完成动作时为 `action_completed`。原生取消后恢复可行动为 `action_canceled`；超时或中断不代表动作没有执行，不能自动重发。

`potion_used/potion_discarded` 记录已见药水的槽位和名称，使用事件表示药水已被原生使用流程移除，不代表所有后续效果已完成。伤害等沿用现有战报；药水自动触发也可出现在结束回合等其他动作的记录中。不声称提供完整资源变化或因果树。

## 验证

隔离实例入口：`python3 scripts/run_roundtrip.py --potion-scenario basic`。另一终端执行：

```sh
.tmp/mcp-venv/bin/python scripts/verify_potion_actions.py --scenario basic --report .tmp/roundtrip/potion-basic.json
```

测试场景只在独立测试模式配置初始状态，不能用于正式对局。标准库客户端提供 `inspect_targets --potion-slot 0`、`use_potion --potion-slot 0 --target-id 2 --expected-state <令牌>` 和 `discard_potion --potion-slot 0 --expected-state <令牌>`；均须传 `--ipc-dir`。MCP 内部管理令牌。实际通过范围及限制见 [验证记录](../research/2026-10-30-potion-actions-validation.md)。

商店观察可显示恶臭药水当前 `usable_here` 提示及实际 `bouncing` 状态。商品页须先用 `close_shop` 关闭，原生目标才可用；假商人触发战斗时，等待新战斗可行动或选择边界，详见[商店接口](shop.md#恶臭药水与假商人)。
