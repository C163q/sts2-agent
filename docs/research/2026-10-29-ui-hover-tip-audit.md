# 界面悬停说明覆盖核查

核查日期为 2026-10-29，项目基线为 `5878ce4`，Mod 为 `0.4.0`。本记录只核对信息范围和来源，尚未新增文件接口或 MCP 工具，也未验证批量读取的游戏内行为。

## 核对基线

游戏安装目录下 `release_info.json` 标记版本、分支均为 `v0.107.1`，提交为 `59260271`，主程序集散列标识为 `1692500715`。接口依据为 `data_sts2_linuxbsd_x86_64/sts2.dll` 的目标类型；本地反编译证据保存在未跟踪的 `.tmp/decompiled/<完整类型名>.decompiled.cs`。这些是游戏内部实现，不是承诺兼容的公开 API。

输入截图 `~/Pictures/STS2_battle-3.png` 只包含能量区域及其中文提示，不能用于确认其他位置是否同时可见。清单同时对照当前 [战斗观察字段](../development/observation.md) 和 [基础信息边界](../observation.md)。旧 `.tmp/live/observation.json` 仍是结构版本 2 的历史样本，本次字段映射以当前源码版本 3 为准。

## 覆盖清单

下表是候选工具的覆盖建议，不表示已实现。只有当前界面可见且能产生对应提示的对象才纳入；字段存在或模型存在不等于提示可用。

| 对象 | 当前基础观察的对应字段 | 已核实的提示来源及边界 |
| --- | --- | --- |
| 左上角角色头像及进阶 | `player.character`、`top_bar.ascension` | `MegaCrit.sts2.Core.Nodes.TopBar.NTopBarPortraitTip.Initialize/OnFocus` 调用 `AscensionHelper.GetHoverTip`，包含角色名称、当前累计进阶规则，并可能包含成就禁用提示。进阶大于 0 或成就禁用时才有提示；不应单独再复制一份进阶说明 |
| 顶栏生命 | `player.hp/max_hp` | `MegaCrit.sts2.Core.Nodes.TopBar.NTopBarHp.OnFocus`，`static_hover_tips` 的 `HIT_POINTS` |
| 金币 | `top_bar.gold` | `MegaCrit.sts2.Core.Nodes.TopBar.NTopBarGold.OnFocus`，`MONEY_POUCH` |
| 药水栏位 | `top_bar.potion_slots` | `NPotionHolder.OnFocus`：空槽为 `POTION_SLOT`，有药水时为当前药水的 `Model.HoverTips`，包括药水本身及关联解释；建议保留槽位关联并去重相同提示 |
| 顶栏房间类型，例如“敌人” | `top_bar.room_icon` | `MegaCrit.sts2.Core.Nodes.TopBar.NTopBarRoomIcon.OnFocus/GetHoverTipPrefixForRoomType`。依当前房间选择 `ROOM_ENEMY`、`ROOM_ELITE`、`ROOM_REST` 等；不是战斗中的敌人说明 |
| 楼层 | `top_bar.floor` | `MegaCrit.sts2.Core.Nodes.TopBar.NTopBarFloorIcon.OnFocus`，`FLOOR` |
| 首领，例如仪式兽 | `top_bar.bosses` | `MegaCrit.sts2.Core.Nodes.TopBar.NTopBarBossIcon.OnFocus`，按实际单首领、双首领和只显示第二首领的条件生成 `BOSS/DOUBLE_BOSS`，不提供未显示的首领 |
| 地图入口 | `top_bar.map_visible` | `NTopBarMapButton.OnFocus`，`MAP`；这里只取入口说明，不打开地图 |
| 主牌组入口 | `top_bar.deck_visible/deck_count` | `NTopBarDeckButton.OnFocus`，`DECK`；不返回牌组内容 |
| 设置入口 | `top_bar.settings_visible` | `NTopBarPauseButton.OnFocus`，`SETTINGS`；不打开设置 |
| 能量 | `player.energy/max_energy` | `NEnergyCounter._Ready/OnHovered`，`ENERGY_COUNT`，描述使用当前角色的能量图标参数 |
| 星星资源 | `player.stars` | `NStarCounter._Ready/OnHovered`，`STAR_COUNT`，仅图标当前显示时纳入；是原清单应补充的独立类型 |
| 抽牌、弃牌、消耗牌堆入口 | `player.draw_count/discard_count/exhaust_count` | `NCombatCardPile.OnFocus`，分别为 `DRAW_PILE/DISCARD_PILE/EXHAUST_PILE`；要求牌堆已绑定且入口可见，不返回内容或抽牌顺序 |
| 结束回合 | `buttons.end_turn` | `NEndTurnButton.OnFocus`，`END_TURN`；提示有玩家当前是否准备结束回合的条件，不能因按钮存在而无条件补齐 |
| 当前敌人意图 | `enemies[].intents` | `NIntent.OnHovered` 根据 `HasIntentTip` 调用当前意图的 `GetHoverTip(_targets, _owner)`。建议纳入当前可见意图的说明，并关联敌人 ID；不读取额外未来动作 |

没有确认到战斗生命条或格挡区域独立提供通用 `Block` 说明的逻辑。`NCreatureStateDisplay.OnHovered` 会显示名称并调用生物的组合提示，不能据此虚构一条格挡悬停说明。

## 生物提示与专门工具的边界

`MegaCrit.Sts2.Core.Entities.Creatures.Creature.HoverTips` 会合并怪物当前意图以及 powers 的提示；`NCreature.ShowCreatureHoverTips` 和生命条悬停会使用这个组合。因此不能直接把该集合当作本次通用界面说明，绕过 powers 的独立查看边界。候选范围只取基础观察已显示的意图对应说明；遗物与玩家、敌人的 powers 效果均留给后续专门工具。手牌继续使用现有 `inspect_hand`。

## 候选读取方式

建议用一个无参数、只读的 `inspect_ui` 一次返回当前场景可见对象的提示，提供标题、正文和对应基础观察字段或对象 ID；相同标题和正文去重，保留所有来源。字段路径如何表达、药水关联格式及错误结构仍属于实现设计，尚未确定接口契约。

读取应复用游戏的提示生成规则和已有英语格式化能力，但不能直接触发各节点的 `OnFocus/OnHovered`：这些方法还会显示窗口、闪烁手牌、播放声音、创建动画，药水悬停甚至会使用随机音效。只读取文本来源，避免改变鼠标、界面和随机状态。已缓存的提示可能使用中文，不能直接把其字符串当成英语结果；需核对重建与缓存边界。

目前 `GameAdapter.Observe` 仅在 `scene == combat` 时输出 `player/enemies/top_bar/buttons`，`CombatObservation.TopBar` 也要求战斗可见。地图等非战斗场景还没有对应的基础观察支持，不能宣称候选工具现已适配。以后应先扩展相应场景的观察和显示判断，再纳入该场景的提示；当前不会展示的战斗入口不自动出现在地图结果中。

后续实现仍需验证当前 UI 的可见、覆盖和交互条件，英语作用域不会改动游戏语言或缓存，批量读取前后状态不变，以及地图等界面扩展时的字段关联。当前结论来自截图与程序集静态核查，没有运行新工具或操作正式战斗。
