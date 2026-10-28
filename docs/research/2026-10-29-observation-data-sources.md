# 可见战斗信息的获取方式调研

核对日期：2026-10-29。结论：缺失项的主要来源已在游戏自身的模型和 Godot UI 节点中找到，不需要先引入 BaseLib、RitsuLib 或 OCR。建议结合模型与 UI 读取：模型提供本地化身份和稳定数值，UI 提供当前实际显示的文字、计数和显示条件。本次为来源调查及编译访问验证，尚未修改运行中的 Mod 或扩展 `available_actions`。

信息范围遵循 [观察约定](../observation.md)，具体样本见 [画面对照](2026-10-29-battle-observation-audit.md)。名称可用于文本化人能通过外观识别的对象；卡牌效果仍留给后续专门查看调用。

## 基线与验证等级

- 游戏：Linux `v0.107.1`，分支 `v0.107.1`，提交 `59260271`；证据为本地安装的 `release_info.json`。
- API 与 UI 规则：定向检查同一安装的 `data_sts2_linuxbsd_x86_64/sts2.dll`，Godot 绑定来自同目录 `GodotSharp.dll`；反编译器 `11.2.0.10050`。
- 编译访问检查：`.tmp/observation-api-probe/Probe.csproj` 使用 SDK `9.0.122` 编译成功，0 个警告、0 个错误。覆盖模型成员、可见节点枚举、标签读取、Shader 参数和帧后事件的访问。
- 反编译结果和编译检查产物均在 `.tmp/`，不纳入 Git。检查程序集未加载进游戏，其方法未执行；编译证明成员可访问，不证明节点路径已在运行场景中成功解析。
- 下列节点名来自目标版本现有代码的 `GetNode` 调用；节点存在、所有者范围、显示状态和动画时序仍需游戏内只读验证。

## 共同入口

| 入口 | 用途 |
| --- | --- |
| `RunManager.Instance.DebugOnlyGetState()` | 当前对局状态；进入主菜单或切换场景时可能为空 |
| `LocalContext.GetMe(runState)` | 当前本地玩家，不假定固定玩家编号 |
| `NRun.Instance.GlobalUi` | 顶栏、遗物栏、地图入口等当前对局 UI |
| `NCombatRoom.Instance` | 当前战斗场景及其 `Ui`、`CreatureNodes` |
| `NCombatRoom.GetCreatureNode(creature)` | 将模型对象与实际战斗节点对应，避免直接枚举全部模型就当作当前已显示 |
| `NPlayerHand.Instance.ActiveHolders` | 当前手牌节点；`CardNode` 给出实际卡牌显示对象 |

以上入口和 Godot 对象均在主线程读取。空入口、尚未 Ready、节点正在释放等状态应形成明确的采样结果，不能用模型中仍存留的数据伪装成已显示内容。

## 数值和对象身份

| 缺失或需改进的内容 | 模型来源 | UI 依据与读取约束 |
| --- | --- | --- |
| 怪物和角色的可读名称 | `Creature.Name`；怪物实际调用 `Monster.Title.GetFormattedText()` | 使用当前语言的名称；只为当前可见、可辨识的对象提供身份，不读取技能表和后续动作 |
| 敌人最大生命 | `Creature.MaxHp`，当前生命为 `CurrentHp` | 遵循 `NHealthBar` 的 `HpDisplay` 与数字可见规则；数值被隐藏时不返回真实数字 |
| 能量上限 | `PlayerCombatState.MaxEnergy` | `NEnergyCounter.RefreshLabel` 显示 `Energy/MaxEnergy`；不要用 `Player.MaxEnergy` 代替，它未包含同样的战斗修正 |
| 金币 | `Player.Gold` | `NTopBar.Gold` 的 `%GoldLabel` 才是该帧文字；`UpdateGoldAnim` 会逐步改变显示值，动画中不能直接以模型最终值替代画面数字 |
| 药水和空槽 | `Player.PotionSlots`、`MaxPotionCount`；保留槽位顺序与 `null` | `NTopBar.PotionContainer` 下 `MarginContainer/PotionHolders` 的 `NPotionHolder`，读取 `HasPotion` 与节点显示状态；不能只枚举 `Player.Potions`，它会过滤空槽 |
| 遗物身份和顺序 | `Player.Relics`、`RelicModel.Title.GetFormattedText()` | `NRun.Instance.GlobalUi.RelicInventory.RelicNodes` 是实际显示容器，可通过 `holder.Relic.Model` 对应身份；不读取 `DynamicDescription` |
| 遗物计数 | `RelicModel.ShowCounter` 和 `DisplayAmount` | `NRelicInventoryHolder.RefreshAmount` 仅在 `ShowCounter` 且对局进行中显示 `%AmountLabel`；隐藏计数不是数值 0，也不是所有遗物都返回 `StackCount` |
| 进阶等级 | `RunState.AscensionLevel` | `NTopBar.Initialize` 控制 `%AscensionIcon` 与 `%AscensionLabel`；等级为 0 时图标不一定显示 |
| 楼层 | `RunState.TotalFloor` | `NTopBar.FloorIcon` 的 `FloorNumLabel`；不要把 `ActFloor` 当作顶部总楼层 |
| 主牌组数量 | `Player.Deck.Cards.Count` | `NTopBar.Deck` 的 `DeckCardCount`；计数来自主牌组，不用手牌和各战斗牌堆的数量之和替代 |
| 抽牌、弃牌及消耗牌堆计数 | `PlayerCombatState` 的对应牌堆 | `NCombatCardPile` 的 `CountContainer/Count` 是实际显示计数；检查按钮和计数是否可见，不返回尚未打开的内容或抽牌顺序 |

数值稳定时，模型值适合结构化输出；要求严格对应某一帧时，以可见标签为准。对于 `HpDisplay` 隐藏数字、金币动画、临时效果或 Mod 改写显示的情形，两者可能不同。

## 手牌名称、费用和外框

读取链为 `NPlayerHand.ActiveHolders → NHandCardHolder.CardNode → NCard`。`NCard` 的 `Visibility` 表示模型展示状态，不能与 Godot 的 `Visible` 混为一谈。

| 内容 | 当前版本可读取的位置 | 重要约束 |
| --- | --- | --- |
| 名称 | `NCard` 的 `%TitleLabel`；真实模型名称为 `CardModel.Title` | `NCard.UpdateTitleLabel` 可能显示未知或锁定占位文字，应优先读取已显示标签；不能绕过展示状态 |
| 能量费用 | `%EnergyLabel`，配合 `%EnergyIcon` 的可见性 | `NCard.UpdateEnergyCostVisuals` 处理 `X`、未知费用和修正后费用；隐藏图标时标签仍可能存着负数，不把该内部数值输出为可见费用 |
| 星星费用 | `%StarLabel`、`%StarIcon` | 按 `UpdateStarCostVisuals` 的显示条件读取；不能给没有该费用显示的牌附加一个 0 或负数 |
| 费用颜色及不可打出标记 | 标签颜色、`%UnplayableEnergyIcon` 与 `%UnplayableStarIcon` | 仅报告已呈现的显示状态，完整可执行目标与动作枚举留到工具实现 |
| 青色、金色或红色外框 | `NCard.CardHighlight.Modulate` 与其 Shader 的 `width` 参数 | `NCardHighlight` 用描边宽度隐藏/显示外框，节点仍在树中；仅检查 `IsVisibleInTree()` 会把宽度 0 的外框误报为显示 |
| 手牌位置和悬停状态 | Holder 的全局位置、`NPlayerHand.FocusedHolder`，以及 `CardHolderContainer` 的排列 | 当前可见顺序要与布局核对；悬停可能改变层级、位置和遮挡，不仅是鼠标坐标问题 |

卡牌正文虽然已经存在于 UI 节点，半隐藏时也不能自动导出。`NCard.UpdateVisuals` 会重新计算预览变量、描述和费用，不是只读查询入口；观察代码应读现有结果，不为取值调用刷新方法。

## 敌人当前意图

游戏自身的链路为：

```text
Monster.NextMove.Intents
→ NCreature.UpdateIntent(targets)
→ NCreature.IntentContainer 中的 NIntent
→ 图像、动画、%Value 标签
```

`NextMove.Intents` 是当前已准备的意图来源，可以核对 UI 对应关系；不能把整个 `NextMove`、状态机、回调或后续状态序列化出去。实际采样优先检查 `IntentContainer` 及 `NIntent` 当前呈现的结果。

- `NIntent.UpdateVisuals` 使用 `GetAnimation(targets, owner)`、`GetTexture(targets, owner)` 生成显示。当前目标及角色状态参与显示，不能只抄怪物招式里的基础伤害。
- 攻击和相应状态类型才显示 `%Value` 数字。可读 `MegaRichTextLabel`（继承 `RichTextLabel`）的 `GetParsedText()`，保留画面已有的伤害、次数或其他文字；标签为空时不补具体数值。
- `AbstractIntent.GetHoverTip` 提供悬停详情，本次基础观察不调用。
- 本版本 `DebuffIntent` 的普通与强力枚举使用相同 `SpritePath`，`IntentPrefix` 都是 `DEBUFF`。因此即使模型返回 `DebuffStrong`，也不能在文本中额外区分画面没有体现的强弱。
- `HiddenIntent`、`UnknownIntent`、意图容器隐藏、透明或正在淡入淡出时，按实际呈现状态处理，不能透过它们输出被隐藏的具体动作。

本次样本的红色向下箭头可以表达为负面效果类意图。接口不直接提供其效果层数和后续行动。

## 状态图标、房间、首领和其他 UI

| 内容 | 当前版本来源 | 读取条件 |
| --- | --- | --- |
| 角色或敌人的状态图标 | `Creature.Powers` 关联 `NCreatureStateDisplay` 下 `%PowerContainer` 中的 `NPower` | `NPowerContainer.Add` 先过滤 `PowerModel.IsVisible`；模型集合中确实可能有隐藏状态，不可全部导出 |
| 状态名称与数字 | `NPower.Model.Title.GetFormattedText()`、`%AmountLabel` | `NPower.RefreshAmount` 仅在 `StackType == Counter` 时显示 `DisplayAmount`；其他类型不附送原始 `Amount` |
| 当前房间类别 | `NTopBar.RoomIcon` 的 `Icon` 纹理，以及 `NTopBarRoomIcon.UpdateIcon` 的映射 | 映射结合地图点、`RunState.BaseRoom` 等信息；不能简单把 `CurrentRoom.RoomType` 当作图标结果，事件内战斗等情况可能不同 |
| 首领身份 | `NTopBar.BossIcon` 当前图像，对应 `Act.BossEncounter` 或 `SecondBossEncounter` 的名称 | `RefreshBossIcon` 与 `ShouldOnlyShowSecondBossIcon` 决定当前图像；仅报告实际显示的首领，不把整章中未显示的首领信息全返回 |
| 结束回合按钮 | `NCombatRoom.Ui.EndTurnButton` 的 `Visuals/Label`，以及 `IsEnabled` | 标签可能变为撤销结束回合等文字，不能只根据回合号自行拼接；本次不实现点击工具 |
| 地图、牌组、设置入口 | `NRun.GlobalUi.TopBar` 的 `Map`、`Deck`、`Pause` | 记录可见和显示状态，不打开对应界面取隐藏内容 |
| 版本、Mod 提示及种子 | `NDebugInfoLabelManager` 中 `%ReleaseInfo`、`%ModdedWarning`、`%DebugSeed`，以及 `NRun` 的 `%DebugSeed` | 只读当前显示标签；`NRun._Ready` 将 `Rng.StringSeed` 写入标签，但该模型值并非无条件可导出的观察字段 |
| 其余可见覆盖层文字 | 当前场景实际显示的 Label/RichTextLabel，按所属区域识别 | 类型和文字是否存在不等于可见；例如 Mod 错误详情容器平时隐藏，不连带导出 |

节点定位可使用 `GetNodeOrNull`、已公开的节点属性以及 `GetChildren().OfType<T>()`，多数内容不需要反射访问私有字段。路径和节点类型均需按版本维护，不能在路径失效时退回无限制序列化模型。

## 采样时机与剩余验证

建议继续在主线程采样，优先验证 `RenderingServer.FramePostDraw` 附近读取已完成一帧的 UI 结果；该事件已通过绑定访问编译检查，但尚未实测其在当前游戏的渲染模式下的触发与采样时序。现有 `SceneTree.ProcessFrame` 处理请求的时机不等于画面已完成更新。

`IsVisibleInTree()` 只是第一层检查，还需考虑父节点透明度、视口与裁剪、卡牌重叠及 Shader 效果。节点存在或 `Visible == true` 都不足以直接证明用户看见了内容。

后续实现前的建议验证顺序：先在独立实例中读取名称、最大生命、能量上限、金币、槽位和计数；再加入手牌标签、外框和当前意图；最后核对隐藏、过渡与遮挡场景。应重点覆盖费用为 `X`、无费用标签、遗物无计数、隐藏状态、金币动画以及手牌悬停切换。运行中的正式对局不用于自动触发这些验证情形。

当前没有发现必须先引入社区库或 OCR 才能取得的核心字段。OCR 或截图可以作为可见性核对手段，但本次没有设计新的截图工具、查看手牌效果工具或动作协议。
