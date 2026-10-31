# 结束回合与期间事件

适用于 Mod `0.24.0`、Linux 游戏 `v0.107.1` 和 RitsuLib `0.6.10` 的 `0.107.1` 兼容运行时。MCP 调用仍为无参数的 `end_turn()`；文件协议为 `end_turn`，需要最新观察令牌。

## 执行与停止边界

工具提交原生 `EndPlayerTurnAction`，从提交前开始记录，到以下边界之一返回。游戏负责结算；工具不模拟规则、不替玩家选择，也不连续结束多个可行动回合。

| `transition.stop_reason` | 含义 |
| --- | --- |
| `player_ready` | 已恢复玩家可行动且队列为空，已识别的牌堆飞行动画结束且观察稳定；`end_turn` 还要求后续玩家回合开始通知已发出，出牌、药水和选牌可在同一回合继续 |
| `choice_required` | 原生动作等待本地玩家选择，且已识别其界面；尚未接通操作的类型也会停止，范围见选牌接口 |
| `combat_won` | 原生事件确认本场战斗胜利；不是整局通关 |
| `combat_lost` | 原生事件确认本场战斗失败；不以暂时零血代替结果 |
| `action_completed` | 药水的战斗外动作已完成，非结束回合结果 |
| `action_canceled` | 原生动作已取消并恢复可行动，仍须重新观察 |
| `timeout` | 提交后 25 秒内未到达上述边界，游戏仍可能继续结算 |
| `interrupted` | 原战斗对象被替换，未取得已确认的胜负 |

选择可能发生在回合结束、敌方行动或回合开始。暴政出现时只返回此前事件，不包含未来选牌结果。使用 [选牌工具](card-selection.md) 处理当前选择，不能再次调用 `end_turn` 代替选择。尚未识别的选择界面仍可能最终返回 `timeout`，不能据此重发动作。

## 返回结构

保留原有基础观察，增加 `transition`；以下仅为该字段的示意：

```json
{
  "transition": {
    "stop_reason": "choice_required",
    "complete": true,
    "events": [
      {
        "sequence": 1,
        "type": "damage",
        "source": {"kind": "card", "name": "Wither"},
        "target": {"id": 0, "kind": "player", "name": "The Ironclad"},
        "hp_loss": 3,
        "blocked": 0
      }
    ]
  }
}
```

`complete` 表示已到达正常停止边界且事件缓冲未截断，不表示已经证明覆盖全部游戏机制。`timeout`、`interrupted` 或超过 512 条记录时为 `false`。非 `player_ready` 或不完整的结果不向模型宣告可以再次结束回合。底层成功响应只表示本次调用已返回，仍须检查停止原因；传输先超时或游戏异常时适用原有未知结果错误语义。

## 动作完成与画面稳定

出牌、药水、战斗内选牌继续结算及结束回合共用动作等待。停止原因在等待期间持续重新判断；`player_ready`、`action_completed` 和 `action_canceled` 还须等待原生 `NCardFlyVfx`、`NCardFlyShuffleVfx`、`NCardFlyPowerVfx` 离开场景，同时等待顶栏金币计数和药水入栏动画结束，再确认观察连续 250 毫秒不变。原因、状态或可行动条件变化都会重新计时。帧持续推进时按 25 秒截止时间检查，未满足时返回 `timeout/complete=false`，不沿用先前已出现过的正常原因。

原生动作完成与界面更新不是同一时机。例如打击的牌已经进入逻辑弃牌堆，屏幕计数仍可能等待飞牌动画落地；不能只凭队列为空或 JSON 暂时不变判断结束，也不能把内部牌堆数量提前填入观察。当前仍从真实可见计数读取，等待这些有限流程完成后再返回。具体复现与证据见[动作观察边界修复](../research/2026-10-30-action-settling.md)。

`choice_required/complete=true` 表示已经到达需要输入的选择边界，父卡牌、药水或回合流程可以仍未完成；此时不会等待它的完整任务，也不因牌堆飞行动画而卡住选择。胜负与战斗替换同样按各自边界处理。环境循环动画、伤害飘字等装饰效果不在等待保证之内，`complete` 不是所有画面像素停止变化的承诺。MCP 公共提示也明确这一语义。等待依赖游戏继续产生帧；若游戏暂停渲染或主线程停止响应，不能保证恰在第 25 秒返回，由外层 IPC 超时处理未知结果。

后续 `get_observation` 和截图读取调用时的当前画面，不自动等待；玩家手动输入、页面变化或未覆盖的第三方异步流程仍可能使观察变化。本版验证针对已核对的原生卡牌、牌堆及资源显示流程，不能据此推断全部机制均已覆盖。

`get_state` / `get_observation` 只返回当前观察，不回放战报；事件不参与基础观察的 `snapshot_id`。相同请求 ID 的已有响应缓存保留原战报。进程重启、缓存删除或客户端未收到响应后的事件恢复尚未实现。MCP 可以复用完整成功且可继续行动的动作结果，新令牌的取得与失效规则见[调用语义](mcp.md#调用和错误语义)。

## 事件语义

`sequence` 从 1 递增，表示本记录器捕获顺序，不承诺任意嵌套效果的完整因果树。

| `type` | 内容 |
| --- | --- |
| `card_played` | 已进入出牌流程的牌、`autoplay`，以及可选目标和已核实的触发来源；不代表全部效果已完成 |
| `card_drawn`、`card_discarded`、`card_exhausted` | 本地玩家牌的公开移动；抽牌在原生历史写入时记录，手牌弃置和消耗在原生入堆事件时记录，先于其后续触发效果 |
| `card_added` | 生成后实际在手牌或预览中公开展示的牌；不输出隐藏入堆位置或未来抽取顺序 |
| `potion_used`、`potion_discarded` | 已见药水的 `potion.slot_index/name`；使用事件在原生移除时记录，后续效果可能仍需选择 |
| `damage` | 实际 `hp_loss`、`blocked`，可选伤害角色与来源；普通直接伤害包含全部格挡和致命一击，生命数字未公开时 `hp_loss` 为 `null` |
| `hp_changed` | 未作为伤害记录的公开 HP 变化，含 `before`、`after`，例如治疗或直接处决；生命数字隐藏时不返回内部绝对值 |
| `block_changed` | 格挡变化，含 `before`、`after`；普通伤害消耗的格挡由 `damage.blocked` 表达 |
| `power_changed` | 名称、`change`（`applied` / `modified` / `removed`）及显示计数前后值；无数字图标或不存在的一侧用 `null` |
| `died`、`revived`、`creature_added` | 可见实例的死亡、复活或加入，分别保留 |

角色沿用战斗 `CombatId`，同一实例复活不换标识。牌沿用基础观察的稳定 ID；已经见过或期间实际展示的完整名称可以保留，遵循[可见牌名规则](observation.md#手牌与身份)，未识别牌名为 `null`。开始记录时也记住当前可见确认区中的已选牌，避免确认后的消耗事件丢失名称。来源仅提供已核实的卡牌、power、遗物或药水名称，不附送完整效果；未知来源为 `null` 或缺省。不输出敌人内部 move ID、未来动作、未发生的随机结果或未展示牌堆内容。

## 实现与限制

RitsuLib 提供统一通知，用于出牌、生成牌、角色加入及生命周期核对。抽牌事实使用原生历史写入点，弃置与消耗使用原生牌堆事件，避免 RitsuLib 后置通知在嵌套触发后才到达而倒序或漏记。原生角色事件补齐 HP、格挡、powers、死亡与复活；原生战斗事件决定胜负，原生选择界面识别交互边界。伤害通过已核对的 `CreatureCmd.Damage` 和 `Creature.LoseHpInternal` 入口补录，保留事件发生位置并避免丢失最后一击。原生 `DamageResult` 的格挡字段在同一流程稍后赋值，返回前补齐。

来源通过异步执行上下文传递；惊逃自动出牌与灾厄处决另外保留明确来源。订阅在返回或异常时释放。游戏访问留在主线程，文件与模型等待在外部。

当前不是完整游戏回放系统。未接入资源、牌面数值变化、复杂召唤和任意第三方 Mod 效果仍可能缺项；Osty 代受伤分支可能缺少原目标的格挡记录，不能用于这类战斗的完整伤害核算。未知选择界面、超时后的持续事件、断线恢复不在本版覆盖范围。升级游戏或 RitsuLib 后须重新验证。设计依据见 [调研](../research/2026-10-29-end-turn-events.md)。

## 验证

先按 [运行指南](roundtrip.md) 准备隔离实例。一个终端用 `python3 scripts/run_roundtrip.py --turn-scenario tyranny` 启动新实例；另一个终端运行：

```sh
python3 scripts/verify_end_turn.py --ipc-dir .tmp/roundtrip/ipc --scenario tyranny --report .tmp/turn-tyranny.json
```

验证只用于带相同场景参数的新测试实例主菜单。场景入口改变测试初始条件，仅由 `STS2_AGENT_TEST_MODE=1` 下的 `start_test_combat` 使用，不是公开玩法工具。每个场景须重启实例，不能在正式对局执行；`--windowed` 可验证图形显示。

其他场景名称：`normal`、`wither`、`wither_death`、`enemy_death`、`retain_choice`、`boulder`、`doom`、`stampede`、`revive`、`blocked`、`hellraiser`、`exhaust_block`、`hidden_hp`。其中 `revive` 连续验证多个回合，以同时取得千足虫死亡及后续复活证据；`hellraiser` 和 `exhaust_block` 检查触发顺序，`hidden_hp` 检查未公开生命数字不进入日志。

选牌动作复用本页事件格式，并增加非战斗完成原因 `selection_resolved`。`choice_required` 的完整响应可以提供已支持的选牌动作，仍不会提供 `end_turn`。

[出牌工具](card-play.md) 同样复用期间事件，并增加 `action_canceled`：原生动作已取消且恢复可行动。入队成功不代表实际打出，失败或取消后仍须重新观察。

[搜刮动作](rewards.md) 复用 `transition`，但不接战斗事件记录。`action_completed` 表示当前奖励交互已经结算或到达新的奖励页面；`manual_input_required` 表示已识别的原生对话或未支持页面需要手动输入，不续接动作许可。
