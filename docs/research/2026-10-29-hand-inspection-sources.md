# 手牌正文与悬停解释的数据来源

核对日期：2026-10-29。游戏已有生成牌面正文和悬停解释的完整链路，无须依赖 OCR 或另建关键词词典。以下结论来自目标版本的程序集和资源核查；本次未新增手牌查看接口、修改 Mod 或调用运行中的游戏。

## 核对基线

- 游戏：Linux `v0.107.1`，分支 `v0.107.1`，提交 `59260271`，来自安装目录的 `release_info.json`。
- 程序集：`data_sts2_linuxbsd_x86_64/sts2.dll`，使用 `ilspycmd 11.2.0.10050` 定向反编译下述类型；本地产物位于 `.tmp/decompiled/`，不纳入 Git。
- 资源：同一安装的 `SlayTheSpire2.pck`，只读解析目录并读取 `localization/eng/`、`localization/zhs/` 下的 `cards.json` 和 `card_keywords.json`；未导出或提交资源表。
- 对照图片：用户提供的 `~/Pictures/STS2_battle-2.png`，悬停卡牌为“进阶之灾”（`Ascender's Bane`）。截图不是本次源码核查时的同步运行采样。

## 牌面正文

`MegaCrit.Sts2.Core.Models.CardModel.Description` 对应 `cards` 表的 `<卡牌条目>.description`，但原始文本不是完整显示结果。

实际 UI 链路为：

```text
NCard.UpdateVisuals(pileType, previewMode)
→ 更新动态数值预览
→ CardModel.GetDescriptionForPile(pileType, target)
→ NCard 的 %DescriptionLabel
```

`GetDescriptionForPile` 加入 `DynamicVars`、额外描述参数、升级状态、战斗和目标上下文，使用 `LocString.GetFormattedText()` 格式化，再拼接 `Enchantment`、`Affliction` 的额外正文、重放次数和当前关键词文字。关键词顺序由 `MegaCrit.Sts2.Core.Entities.Cards.CardKeywordOrder` 决定。

截图中的 `MegaCrit.Sts2.Core.Models.Cards.AscendersBane.CanonicalKeywords` 为 `Eternal`、`Unplayable`、`Ethereal`。英语 `ASCENDERS_BANE.description` 实际为空，中文表未定义该描述键，会回退英语。牌面“不能被打出。／虚无。／永恒。”由关键词生成，不是写在卡牌基础描述里的固定句子。

`CardModel.Keywords` 包含当前实例的关键词及战斗全局修正；不能用卡牌原型的 `CanonicalKeywords` 代替当前显示。

## 右侧悬停解释

实际 UI 链路为：

```text
MegaCrit.Sts2.Core.Nodes.Cards.Holders.NCardHolder.CreateHoverTips()
→ CardNode.Model.HoverTips
→ NHoverTipSet.CreateAndShow(...)
```

`CardModel.HoverTips` 汇集额外提示、`Enchantment` 和 `Affliction` 的提示、重放、激发、格挡和关键词解释，并去重。关键词经 `MegaCrit.Sts2.Core.HoverTips.HoverTipFactory.FromKeyword` 生成 `HoverTip`；标题、正文最终来自 `card_keywords` 表的 `<关键词>.title`、`<关键词>.description`。

截图对应关系为：

| 解释框 | 资源键前缀 | 出现原因 |
| --- | --- | --- |
| 永恒 | `ETERNAL` | 卡牌当前关键词 |
| 不能被打出 | `UNPLAYABLE` | 卡牌当前关键词 |
| 虚无 | `ETHEREAL` | 卡牌当前关键词 |
| 消耗 | `EXHAUST` | `CardModel.HoverTips` 遇到 `Ethereal` 时额外追加 |

最后一个解释框不是卡牌具有 `Exhaust` 关键词的证据。它解释“虚无”中提到的“消耗”；若只遍历卡牌关键词，或只扫描牌面文字，将漏掉它。后续工具应以游戏的提示集合为依据，不自行推断关键词之间的关联。

## 英语输出与实现约束

- 英语关键词的标题与解释已在 `res://localization/eng/card_keywords.json` 中核实；普通卡牌模板位于 `res://localization/eng/cards.json`。这些是游戏资源路径，不是安装目录下的独立 JSON 文件。
- `HoverTip.Title`、`Description` 在构造时已经通过 `LocString.GetFormattedText()` 生成，使用游戏当前语言。直接输出这些字符串不会自动得到英语。
- `LocString` 使用游戏配置的 SmartFormat 扩展处理动态变量。现有 `EnglishText.Name` 只支持简单名称替换，不足以格式化完整卡牌说明；英语动态正文的具体接入方式仍需实现和运行验证。
- 不为读取文本调用 `NCard.UpdateVisuals`：它会清除并重算动态预览变量。也不切换全局 `LocManager` 语言；那会影响游戏 UI 和本地化状态。
- 文本含颜色、格式和资源图标标记。导出时须保留图标表达的玩法含义，不能把所有标记及其内容一律删除。
- 本次只核实内置卡牌的来源链路，未验证其他 Mod 对本地化、描述和悬停提示的改写兼容性。

后续专门查看调用仍按 [观察约定](../observation.md) 一次返回全部当前手牌详情，并沿用稳定卡牌 ID；基础观察不自动附送这些效果和解释。该调用目前尚未实现。

## 数值预览的上下文

同日追加核查下列类型，基线与前文相同：

- `NCard.UpdateVisuals` 取 `_previewTarget ?? Model.CurrentTarget` 作为目标，再更新动态预览。`MegaCrit.Sts2.Core.Localization.DynamicVars.DamageVar.UpdateCardPreview` 将该目标、攻击者和卡牌传入 `Hook.ModifyDamage`；未对准目标与对准目标的数值可能不同。
- `MegaCrit.Sts2.Core.Models.Powers.ShrinkPower.ModifyDamageMultiplicative` 检查攻击者是否为状态所有者；`VulnerablePower.ModifyDamageMultiplicative` 检查目标是否为状态所有者。前者可影响未选目标时的牌面，后者需要对应受击目标。显示数字已经是预览结果，不应把已包含的效果再计算一次。
- `MegaCrit.Sts2.Core.MonsterMoves.Intents.AttackIntent.GetSingleDamage` 取得当前本地玩家，以其角色作为受击目标、意图所有者作为攻击者调用 `Hook.ModifyDamage`。`SingleAttackIntent.GetIntentLabel` 使用此结果；`NIntent` 将格式化结果写入 `%Value`。观察实现读取此标签，没有重新叠加状态。
- `MegaCrit.Sts2.Core.Models.Powers.TaintedPower.ModifyDamageAdditive` 对状态所有者承受的适用攻击增加伤害。中文 `powers.json` 的 `TAINTED_POWER.title` 已核实为“污染”；它和易伤均可参与意图预览。

本次在 `roundtrip_client.player_result` 加入固定数值解读说明，供普通玩法输出及 MCP 共用，具体字段见 [数值预览说明](../development/observation.md#数值预览说明)。未新增预览工具、刷新 UI、修改 Mod 或自动计算所有目标的伤害。上述行为依据目标程序集核实，未在运行游戏中重新构造“缩小 + 易伤”或“污染”场景。

输出转换修改后，18 项 Python 回归检查通过，包含真实 stdio MCP 与临时文件 IPC。另检查说明仅出现在成功的战斗结果、不改写原始响应，且各次结果的说明字典互不影响；这些检查未连接正式游戏。同步修正观察文档中“尚未接入正式 LLM 工具框架”的过时描述，实际 MCP 已复用同一转换入口。
