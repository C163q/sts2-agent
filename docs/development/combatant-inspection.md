# 双方 powers 与敌人意图详情

文件操作 `inspect_combatants` 适用于 Linux 游戏 `v0.107.1`、Mod `0.7.0`。一次只读查看本地玩家和当前可见敌人的 powers，以及敌人当前展示的意图，返回原生英语悬停说明。不触发实际鼠标悬停，不改变目标、语言或游戏流程。目前尚未注册为 MCP 工具。

## 读取

按 [正常游戏加载](live-game.md) 安装并重启，进入无遮挡战斗后执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_combatants > .tmp/live/combatant-inspection.json
```

读取无须动作令牌，不进入 `available_actions`。默认客户端移除响应包装、状态令牌等控制信息；加 `--raw` 可保留这些字段。

## 格式

| 字段 | 内容 |
| --- | --- |
| `scene` | 当前固定为 `combat` |
| `player.powers[]` | 玩家当前可读的 power 名称和可见计数 `name/amount` |
| `enemies[]` | 当前可见敌人，从左到右排列 |
| `enemies[].id/name` | 基础观察相同的战斗对象 ID 和英语名称 |
| `enemies[].powers[]` | 该敌人当前可读的 powers，格式同玩家 |
| `enemies[].intents[]` | 当前渲染意图的 `category/value`，格式同基础观察 |
| `hover_tips[]` | 主说明和附带原生解释，按 `title/description` 同时相同去重 |
| `hover_tips[].sources[]` | 关联到本次结果的具体 power 或 intent，如 `player.powers.0`、`enemies.1.intents.0` |

`sources` 中的数组下标从 0 开始，只对本次结果有效。重复怪物用 `id` 区分；不要把数组位置当作跨请求的稳定 ID。同名提示正文不同时分开保留，包括层数、持续回合或拥有者不同造成的区别。附带的术语或卡牌预览也关联到提供它的 power。

计数取自屏幕标签，不使用模型 Amount 替代不可见的计数。无计数标签时 `amount: null`。容器隐藏时 powers 或 intents 为 `null`；可见容器中没有可读条目时为 `[]`。玩家节点不可见时 `player: null`。正文保留换行，移除格式标记，图标沿用 `<Energy>`、`<Star>` 等文本表示。

返回敌人意图时附带 `notes.enemy_attack_intents`，规则和完整文案见 [观察数值说明](observation.md#数值预览说明)；意图伤害已经包含当前预览修正，不能再叠加一次易伤等效果，也不保证等于最终生命损失。没有敌人意图时不附带该 note；不返回 `card_values`。

## 读取边界

仅支持无遮挡战斗；瞄准或打出卡牌期间，原生界面会抑制战斗对象悬停说明，因此整次读取返回 `illegal_action`。敌人身份与顺序复用基础观察的可见节点筛选；power 必须有可见图标、模型允许展示且能接收鼠标悬停；意图必须有可见的 holder 和图标且能接收悬停。不枚举隐藏 powers，不读 `Monster.NextMove` 或后续招式，不增加格挡说明。`HasIntentTip: false` 的意图不构造说明。

power 主说明使用当前实例 `HoverTips` 的动态正文，而非静态通用定义；包含人悬停时会看到的当前持续回合、层数、拥有者或施加者等变量。意图从已显示 `NIntent` 绑定的意图、目标和拥有者构造原生提示，包含当前预览伤害及连击次数。对 Shrink 等施加时缓存怪物本地化名称的情况，仅在独立格式化变量中放入英语施加者名称，不修改实际 power 的缓存或中文说明。读取不调用控件的 `OnFocus/OnHovered` 或更新流程；未知提示类型显式返回错误，不静默丢弃。

沿用 [信息边界](../observation.md) 和现有英语作用域。当前可见性判断使用节点、透明度、视口及裁剪矩形，不能精确判断任意像素遮挡。读取过程中如果发现绑定对象无效，则整次报错，不用其他模型状态补齐。其他 Mod 改写悬停行为、其他游戏版本、多人/宠物及非战斗场景尚未验证。

## 验证

运行期间避免手动改变游戏：

```sh
python3 scripts/verify_combatants.py --ipc-dir .tmp/live/ipc --output .tmp/live/combatant-inspection.json --report .tmp/live/combatant-inspection-check.json
```

该脚本重复读取并核对前后状态令牌一致、敌人 ID 和基础字段对应、共享说明去重、来源路径可解析及数值 note 的范围。详情仅保留可悬停图标，核对时按顺序匹配基础观察的子序列。

独立中文实例可用 `scripts/run_roundtrip.py --windowed --capture --check-combatants`。此标志仅在原有测试入口创建战斗时，通过 `PowerCmd.Apply` 给测试玩家准备 Strength、Vulnerable、怪物施加的永久 Shrink，给测试敌人准备 Vulnerable，并检查动态说明、共享提示及可见性。不要为正式游戏设置测试标志。实施依据、验证结果和未验证范围见 [实施记录](../research/2026-10-29-combatant-inspection-plan.md)。

已完成独立中文游戏的 31 项检查和前后状态一致的只读导出，取得 3 个敌人及 6 条共享提示；样本为 `.tmp/roundtrip/combatant-inspection.json`。原有观察、手牌、界面及药水均回归通过，Python 全套 51 项通过。正式重启后另完成 2 个敌人、3 条共享提示的只读采样：玩家没有 powers，Twig Slime (M) 有 2 回合 Vulnerable；攻击预览分别为 3 和 11。重复详情及前后观察均一致，样本为 `.tmp/live/combatant-inspection.json`。正式与独立数据分别保存，未在正式游戏中执行动作。
