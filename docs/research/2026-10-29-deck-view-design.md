# 牌组查看设计与接口来源

本文记录牌组查看的已确认要求、原生接口核查和工具设计。对应文件接口已在 Mod 0.9.0 实现，使用方式及当前限制见 [牌组查看与关闭](../development/deck-inspection.md)；独立和正式游戏均已完成采样，结果见实施记录。

## 已确认要求

- 专门查看调用一次返回整个可浏览牌组，包括当前滚动区域外的卡牌；不要求自动逐屏滚动。基础观察仍遵守当前静态画面边界。
- 调用时真实打开原生牌组页，让人知道 LLM 正在看牌组。
- 支持原生“查看升级”预览；可选排序参数省略时沿用游戏内默认行为。
- 需要让调用者控制描述信息量，默认 `summary`，可切换 `full`；通过显式 `close_deck()` 关闭页面。

## 核对基线与证据

核对日期 2026-10-29；本机 Linux 游戏 `v0.107.1`、main、commit `59260271`，Godot MegaDot 4.5.1.m.12，证据为游戏安装目录的 `release_info.json` 和 `data_sts2_linuxbsd_x86_64/sts2.dll`。截图为本机 `~/Pictures/STS2_battle-6.png`；只作页面内容参考，不把截图中状态与其他时间的 IPC 混合。

本地反编译文件保存在被忽略的 `.tmp/decompiled/`，对应下列完整类型与成员：

| 类型和成员 | 核实到的行为 |
| --- | --- |
| `MegaCrit.Sts2.Core.Nodes.TopBar.NTopBarDeckButton.OnRelease` | 牌组未打开时调用 `NDeckViewScreen.ShowScreen(_player)`；已打开时通过原生容器关闭 |
| `MegaCrit.Sts2.Core.Nodes.Screens.NDeckViewScreen.ShowScreen` | 创建并交给 `NCapstoneContainer.Open`；不是读取后台牌组的纯函数 |
| `NDeckViewScreen._EnterTree/_Ready/DisplayCards` | 使用 `PileType.Deck`，读取整个牌组到原生页面并交给网格排序；不是当前抽牌堆 |
| `NDeckViewScreen` 构造函数 | 原生排序优先级依次为获得顺序、类型、费用、名称的升序；获得顺序优先时保留牌组列表顺序 |
| `NDeckViewScreen.OnObtainedSort/OnCardTypeSort/OnCostSort/OnAlphabetSort` | 将所选排序提升为首要排序，保留其他排序的优先级 |
| `MegaCrit.Sts2.Core.Nodes.CommonUi.NCardViewSortButton.OnRelease/IsDescending` | 更新按钮方向和视觉状态；单独改变导出数组顺序会使 JSON 与页面不一致 |
| `MegaCrit.Sts2.Core.Nodes.Screens.NCardsViewScreen.ToggleShowUpgrades/AfterCapstoneOpened` | 原生复选框控制 `_grid.IsShowingUpgrades`，新开页面时默认关闭 |
| `MegaCrit.Sts2.Core.Nodes.Cards.Holders.NGridCardHolder.UpdateCardModel/SetIsPreviewingUpgrade` | 克隆可升级卡牌后调用 `UpgradeInternal`，在基础卡与升级预览之间切换；不能对实际牌组模型调用升级 |
| `MegaCrit.Sts2.Core.Nodes.Cards.NCardGrid.CurrentlyDisplayedCardHolders` | 网格只实例化部分滚动区条目，不能把这个集合当作全牌组 |
| `NCardGrid.SetCards/SortingAlgorithms` | 顺序取决于页面排序优先级；名称排序使用游戏当前语言及文化环境，不一定符合英语 JSON 的字母顺序 |
| `MegaCrit.Sts2.Core.Nodes.Screens.Capstones.NCapstoneContainer.Open/CloseInternal` | 单人打开页面会暂停战斗，关闭后恢复；打开其他页面可能替换原页面，因此须校验当前界面 |
| `NCardsViewScreen.AfterCapstoneClosed` | 隐藏并释放页面；不能持有关闭后失效的节点引用 |

以上是当前版本内部实现，不是承诺稳定的官方 Mod API。打开、升级、排序、关闭及等待期间的页面变化已在独立中文图形实例验证，结果见 [实施记录](2026-10-29-deck-view-plan.md)。

## 工具设计

`inspect_deck` 打开或复用原生牌组页，应用显式提供的选项，等待页面就绪，再返回整个可浏览牌组。界面已经打开时，不重建页面或复位未指定的选项；新打开时使用原生默认值。结果带当前实际的升级预览、主要排序和信息档位。牌组条目标识使用 `deck:` 前缀，与战斗手牌标识分开，排序和升级预览不改变原卡标识。

| 参数 | 语义 |
| --- | --- |
| `detail_level: "summary" \| "full"` | 默认 `summary`；控制输出信息量，不改变游戏画面 |
| `view_upgrades: boolean` | 省略则沿用当前页面；新页面采用原生默认关闭；仅预览下一次可用升级，不能升级的卡维持原样 |
| `sort_by: "obtained" \| "type" \| "cost" \| "name"` | 可选，指定时同步改变原生页面排序及输出顺序 |
| `descending: boolean` | 可选，仅与显式排序键一起使用；显式指定排序键但省略方向时采用升序 |

`summary` 保留卡牌标识、名称、费用及星费、类型、稀有度、实际外观卡池；不包含正文和附带解释。外观卡池不等于当前玩家或独占角色，不能用拥有者角色替代。`full` 在相同基础字段上增加正文和共享悬停解释，继续使用既有去重约定。省略描述时不使用 `null` 冒充不可读正文。重复卡牌保留独立条目，升级预览不改变原卡的标识。

费用和描述须遵循原生牌组页面的 `PileType.Deck` 预览，不能沿用手牌或瞄准目标时的战斗计算，也不能返回抽牌顺序。整个牌组可浏览的授权不扩展到隐藏模型、未知卡牌身份或未来随机结果。

## 页面关闭方式与取舍

1. 采用显式 `close_deck()`：查看结果返回后页面继续显示，LLM 看完主动关闭，随后重新观察战斗再行动。便于人查看页面及继续切换预览；需要额外一次调用。
2. 读取完成自动关闭：每次调用自行返回战斗，但显示时间受调用速度影响，人可能只看到页面闪过；继续查看升级或排序时需要重新打开。

不推荐定时自动关闭，因为会在 LLM 思考或人查看时自行切换界面。关闭只能作用于当前牌组页，不能调用通用关闭接口而误关商店、奖励或事件。人手动返回也可结束查看；随后调用必须读取实际页面状态。

真实打开页面会改变 UI 和单人暂停状态，应在工具描述中明确，不能继续当作完全无界面副作用的读取。打开、关闭及显示选项变化使旧战斗动作令牌失效；关闭后须显式重新观察，不自动授权动作。不能为了下一次结束回合而静默替用户关闭页面。

## 实施与验证范围

先实现文件 JSON 并验证原生页面行为，随后按既有流程单独接入 MCP。默认信息档位为 `summary`，显式 `close_deck()` 关闭，不定时或隐式关闭。

至少需要独立图形实例验证：牌组页真实打开及暂停/关闭恢复；全牌组包含滚动区外卡牌；升级预览不改实际模型；不可升级与已升级卡；原生排序及中文环境名称排序；重复卡身份；两档信息投影；页面被人关闭或替换、战斗过渡、失败及取消时的状态与动作授权。正式游戏操作范围应限于已明确请求的页面浏览。
