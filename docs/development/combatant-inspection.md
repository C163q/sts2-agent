# 战斗对象与充能球详情

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

文件操作 `inspect_combatants` 与同名 [MCP 工具](mcp.md)用于一次只读查看玩家、可见敌人和友方召唤物的 powers、敌人当前意图、玩家已生成充能球及悬浮君王之剑的原生英语说明。不触发实际鼠标悬停，不改变目标、语言或游戏流程。MCP full 与文件客户端返回相同的玩法 JSON，默认 default 省略普通空值；规则见[公共预设](mcp.md#输出预设)。

## 读取

按 [正常游戏加载](live-game.md) 安装并重启，进入无遮挡战斗后执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_combatants > .tmp/live/combatant-inspection.json
```

MCP 调用 `inspect_combatants()` 除通用 preset 外无其他参数，成功时刷新状态令牌；完整规则见 [MCP 调用语义](mcp.md#调用和错误语义)。文件读取无须动作令牌，可用时列入 `available_actions`。默认客户端移除响应包装、状态令牌等控制信息；加 `--raw` 可保留这些字段。

## 格式

| 字段 | 内容 |
| --- | --- |
| `scene` | 当前固定为 `combat` |
| `player.powers[]` | 玩家当前可读的 power 名称和可见计数 `name/amount` |
| `player.orb_slots` | 与[基础观察](observation.md#玩法字段)相同的球槽顺序、空值和显示数字；不把悬停才出现的数字填入该摘要 |
| `player.sovereign_blades[]` | 当前可见悬浮剑的绑定卡牌 `id/name`，与基础观察和手牌 ID 一致；按稳定 ID 排列 |
| `allies[]` | 当前可见友方召唤物的 `id/name/powers`；如奥斯提，powers 格式同玩家 |
| `enemies[]` | 当前可见敌人，从左到右排列 |
| `enemies[].id/name` | 基础观察相同的战斗对象 ID 和英语名称 |
| `enemies[].powers[]` | 该敌人当前可读的 powers，格式同玩家 |
| `enemies[].intents[]` | 当前渲染意图的 `category/value`，格式同基础观察 |
| `hover_tips[]` | 主说明和附带原生解释，按 `title/description` 同时相同去重 |
| `hover_tips[].sources[]` | 关联到本次结果的对象，如 `player.powers.0`、`enemies.1.intents.0`、`allies.0.powers.0`、`player.orb_slots.0`、`player.sovereign_blades.0` |

`sources` 中的数组下标从 0 开始，只对本次结果有效。重复怪物用 `id` 区分；不要把数组位置当作跨请求的稳定 ID。同名提示正文不同时分开保留，包括层数、持续回合或拥有者不同造成的区别。附带的术语或卡牌预览也关联到提供它的 power。

充能球说明使用可见且可悬停 `NOrb` 所绑定实例的原生 `HoverTips`，包含人悬停时可读的当前被动／激发效果及附带术语；这些正文可以包含基础画面未显示的激发数值。空槽不生成这里的正文，通用空槽帮助由 [inspect_ui](ui-inspection.md) 提供。隐藏、离屏、裁剪或不可悬停的球不提供正文；读取不调用 `OnFocus` 或改变标签显示状态。

计数取自屏幕标签，不使用模型 Amount 替代不可见的计数。无计数标签时 `amount: null`。容器隐藏时 powers 或 intents 为 `null`；可见容器中没有可读条目时为 `[]`。玩家节点不可见时 `player: null`。正文保留换行，移除格式标记，图标沿用 `<Energy>`、`<Star>` 等文本表示。

返回敌人意图时附带 `notes.enemy_attack_intents`，规则和完整文案见 [观察数值说明](observation.md#数值预览说明)；意图伤害已经包含当前预览修正，不能再叠加一次易伤等效果，也不保证等于最终生命损失。没有敌人意图时不附带该 note；不返回 `card_values`。

## 读取边界

支持无遮挡战场，包括原生可查看的建筑师战斗背景；瞄准或打出卡牌期间，原生界面会抑制战斗对象悬停说明，因此整次读取返回 `illegal_action`。敌人身份与顺序复用基础观察的可见节点筛选；power 必须有可见图标、模型允许展示且能接收鼠标悬停；意图必须有可见的 holder 和图标且能接收悬停。不枚举隐藏 powers，不读 `Monster.NextMove` 或后续招式，不增加格挡说明。`HasIntentTip: false` 的意图不构造说明。

奥斯提按真实阵营进入 `allies`，不占用敌人下标。君王之剑的说明来自可见 `NSovereignBladeVfx.Card` 的原生卡牌预览，按原生 `PileType.Deck` 格式化；不返回独立铸造计数、所在牌堆或隐藏卡牌信息。剑可见但 hitbox 不可悬停、攻击动画进行中或被隐藏时不提供正文；多把剑分别绑定卡牌 ID，相同提示仍可共享多个来源。核对与验证见[记录](../research/2026-11-02-companions.md)。

power 主说明使用当前实例 `HoverTips` 的动态正文，而非静态通用定义；包含人悬停时会看到的当前持续回合、层数、拥有者或施加者等变量。意图从已显示 `NIntent` 绑定的意图、目标和拥有者构造原生提示，包含当前预览伤害及连击次数。对 Shrink 等施加时缓存怪物本地化名称的情况，仅在独立格式化变量中放入英语施加者名称，不修改实际 power 的缓存或中文说明。读取不调用控件的 `OnFocus/OnHovered` 或更新流程；未知提示类型显式返回错误，不静默丢弃。

原生 `PowerModel.HoverTips` 的格式化调用在英语读取作用域内显式经过英语渲染器，避免预编译或内联调用绕过 `LocString.GetFormattedText` 的拦截后，以中文复数规则解释英文模板。实例变量仍由原生提示流程填入；例如 Escape Artist 计数为 5、4 时分别显示 `after 5 turns`、`after 4 turns`，为 1 时显示 `this turn`。这是当前 UI 状态说明，不提供敌人后续招式或对未来回合的额外推演。修复与同类审查见[状态说明验证](../research/2026-11-01-power-descriptions.md)。

沿用 [信息边界](../observation.md) 和现有英语作用域。当前可见性判断使用节点、透明度、视口及裁剪矩形，不能精确判断任意像素遮挡。读取过程中如果发现绑定对象无效，则整次报错，不用其他模型状态补齐。其他 Mod 改写悬停行为、其他游戏版本、多人及其他非战斗背景尚未穷举验证。

## 验证

运行期间避免手动改变游戏：

```sh
python3 -m tests.game.verifiers.verify_combatants --ipc-dir .tmp/live/ipc --output .tmp/live/combatant-inspection.json --report .tmp/live/combatant-inspection-check.json
```

该脚本重复读取并核对前后状态令牌一致、敌人 ID 和基础字段对应、共享说明去重、来源路径可解析及数值 note 的范围。详情仅保留可悬停图标，核对时按顺序匹配基础观察的子序列。

独立中文实例可用 `scripts/run_roundtrip.py --windowed --capture --check-combatants`。此标志仅在原有测试入口创建战斗时，通过 `PowerCmd.Apply` 给测试玩家准备 Strength、Vulnerable、怪物施加的永久 Shrink，给测试敌人准备 Vulnerable 与计数 5 的 Escape Artist，并检查动态说明、共享提示及可见性；另用控制变量对照原生英文与中文环境下英语作用域的状态说明模板。模板对照不代表全部状态的生命周期均已实机验证。不要为正式游戏设置测试标志。实施依据、验证结果和未验证范围见 [实施记录](../research/2026-10-29-combatant-inspection-plan.md)。

历史独立及正式游戏采样见[战斗对象实施记录](../research/2026-10-29-combatant-inspection-plan.md)和[MCP 实施记录](../research/2026-10-29-mcp-combatant-inspection.md)；召唤物及悬浮剑的专项范围见[同伴验证](../research/2026-11-02-companions.md)。
