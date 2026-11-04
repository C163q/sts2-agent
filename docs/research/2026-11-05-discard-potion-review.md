# discard_potion 审阅与建议

> 当前状态：已完成实现、独立审查并合入 main，工具已核销；35 类组合场景、673 项 Python 与 124 项 C# 检查通过，两项重要审查发现已修复，一项低优先级清理事项记录于实施记录。下述 15 类现状及 [62 份返回](2026-11-05-discard-potion-examples/README.md)保留审阅基线；修复后见 [126 份完整返回](2026-11-05-potion-discard-queue-examples/README.md)与[实施记录](2026-11-05-potion-discard-implementation.md)。

## 优先关注的问题

**审阅发现、已实现修复：选牌期间原生允许排队丢弃，旧工具却完全拒绝。** 实测使用技能药水进入选牌，打开另一瓶格挡药水的菜单：“饮用”置灰，“丢弃”可点击。点击丢弃后药水置灰但暂不消失；选好牌后药水才移除，后续回执记录 potion_discarded。审阅基线在同样的选牌状态直接拒绝，基础观察也不列出 discard_potion。

修复让丢弃单独判断当前是否可操作，支持这种原生排队：不替玩家选牌，不把尚未执行的请求说成“已丢弃”，并防止同一瓶被重复提交。仍停在当前选择处，实际丢弃事件随之后的执行回执返回；确定的字段见下文。

前一轮共用修复对丢弃有效：空槽和越界会说明原因，明确未操作的拒绝允许直接纠正或改做其他合法操作，筛选后的药水仍按原始槽位编号操作，一个槽位不可交互不会阻止其他正常槽位。这些部分没有发现新的问题。

## 参数与返回建议

现有参数足够，无须新增参数：

```json
{"potion_slot": 1, "preset": "full"}
```

- `potion_slot` 是从左到右、从 0 开始的原始槽位，空槽也占位置。筛选过 inspect_potions 时，通过它返回的 slot_indices 对照。
- `preset` 保留 default/full，省略为 default。丢弃不接受 target_id。
- 每次丢弃一瓶，成功回执只有当前场景、可用操作和实际变化，已经很短，**无需 summary**。这些回执没有可省略空值时，default 与 full 内容相同。

现有提示词已说明自动药水可丢弃，未发现误导性的前置查看要求；支持排队后，只需补充简短的执行时机说明。

## 场景与完整示例

以下均为**修复前审阅基线**的真实 MCP 返回；链接中的 JSON 保留全部字段。错误不是建议文案。当前返回及排队、取消、未知结果见[修复后样例](2026-11-05-potion-discard-queue-examples/README.md)。

| 情形 | 结果与完整返回 |
| --- | --- |
| 战斗中丢弃中间槽位 | [第 1 槽格挡药水](2026-11-05-discard-potion-examples/basic-17-full-player_ready.json)，player_ready；其他药水不前移 |
| 使用 default | [第 0 槽火焰药水](2026-11-05-discard-potion-examples/default-03-default-player_ready.json)，格式与 full 相同 |
| 自动药水 | [瓶中精灵](2026-11-05-discard-potion-examples/automatic-03-full-player_ready.json)可丢弃，不触发救命效果 |
| 战斗外 | 事件、火堆、商店、商品页、地图、奖励页均验证成功，返回 action_completed；见[全部样例](2026-11-05-discard-potion-examples/README.md) |
| 奖励页腾槽 | [丢弃第 1 槽血液药水](2026-11-05-discard-potion-examples/noncombat_reward-06-full-action_completed.json)后，可直接领取待拿药水，进入腾出的原槽位 |
| 地图连续丢弃 | [第 0 槽](2026-11-05-discard-potion-examples/noncombat_map-04-full-action_completed.json) → [第 1 槽](2026-11-05-discard-potion-examples/noncombat_map-07-full-action_completed.json) → [第 2 槽](2026-11-05-discard-potion-examples/noncombat_map-10-full-action_completed.json)，中间没有额外查看调用 |
| 空槽、越界 | [空槽](2026-11-05-discard-potion-examples/basic-20-full-error.json)、[越界](2026-11-05-discard-potion-examples/basic-13-full-error.json)说明原因，已有操作许可保留 |
| 选牌期间误调用 | [拒绝丢弃](2026-11-05-discard-potion-examples/skill-05-full-error.json)后可直接选牌；选完再丢弃成功 |
| 页面覆盖或槽位不可交互 | 当前返回具体拒绝，具体返回见[全部样例](2026-11-05-discard-potion-examples/README.md)；其他覆盖页是否能原生丢弃仍须分别核验 |
| 同名药水已被替换 | 旧状态拒绝，重新查看前不能继续操作，避免按过期状态丢错药水 |

成功只出现 potion_discarded，没有把丢弃记成 potion_used；测试中的果汁不增加最大生命，恶臭药水不增加金币，其他药水也不因丢弃产生使用效果。丢空药水栏后，available_actions 不再包含 discard_potion。表中“选牌期间误调用”记录的是工具当前行为，不能视为符合原生能力的验收结论。

## 已确认契约

输入参数继续使用 potion_slot 与 preset:default/full，不增加 summary。支持已暴露、原生药水槽允许操作的稳定选牌边界，仍禁止在未验证的牌组／牌堆／战斗地图覆盖、敌人回合或未知选择中提交。使用药水的阶段限制保持原有规则。提示词简要说明“可能排队，完成当前选择后执行”。

成功的 discard_potion 回执增加**顶层** potion_discard；该字段描述本次请求，transition.events 只记录实际发生的变化。字段片段：

```json
{
  "potion_discard": {
    "slot_index": 1,
    "name": "Block Potion",
    "status": "queued"
  }
}
```

排队时 status 为 queued，停在当前 choice_required，不生成尚未发生的 potion_discarded。完成选牌后的 select_card 等回执在 events 中记录实际丢弃，不附带顶层 potion_discard。立即成功丢弃时，顶层 status 为 discarded，events 同时保留 potion_discarded；战斗中通常为 player_ready，战斗外为 action_completed。

取消且确认未丢弃时为 not_discarded；无法确认或执行异常而缺少公开移除证据时为 unknown。unknown 不提供继续玩法的许可，须重新读取；明确未提交的原有错误仍保留已有许可。一个槽位已有原生使用／丢弃等待标记时拒绝重复提交，可继续选牌或处理其他合法槽位，不凭请求成功预测未来移除。

仅 discard_potion 自身的成功回执返回该顶层字段；use_potion、基础观察、选牌回执不携带它。字段在 default/full 中相同，不包含隐藏效果、随机结果或未来执行保证。实际支持和取消等边界须以本轮实现验证为准。

其他效果先移除同一瓶药水时，实际变化仍进入 events，但不能当作本次请求成功的证据。实际丢弃后若后续效果处理异常，保留 discarded 和已发生的事件，同时以 interrupted、complete:false 停止，不允许直接继续玩法。
