# inspect_ui 场景核验与参数设计

> 当前状态：现状与完整示例已交付，进入设计讨论。已整理 14 组场景及错误、导出 12 份真实 full JSON，涵盖通用帮助、角色差异、选牌战场、建筑师背景与不可用页面；进阶、双首领等部分变体仅核对源码或历史证据，边界见下文。参数与摘要尚未定稿，未修改工具，本项尚未核销。

总清单及约定流程见[工具逐项核验](2026-11-02-mcp-tool-review.md)，现行接口见[界面悬停说明](../development/ui-inspection.md)。

## 核对范围与证据

- 代码基线：`b43c6ef`；Mod `0.49.3`、MCP `0.50.8`、原生 schema `32`。本记录对该次核验负责，当前兼容基线统一见[项目 README](../../README.md#当前版本与前提)。
- 游戏：Linux `v0.107.1`，release，build `59260271`；RitsuLib `0.6.10` 的该游戏兼容包。程序集为游戏目录下 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256：`d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 隔离运行时与当前构建的 Mod DLL 一致，SHA-256：`501d8ee982c64a77115565623d79b0154a6955b379dd2999a5efaa8e4a5f889e`。测试实例使用中文 UI，工具文本应为英语；夹具可能准备非正常开局的手牌、资源和角色状态，不能将样本视为正常开局配置。
- 原生实现：[UiInspection.Read](../../src/Sts2Agent/Observation/UiInspection.cs)、[CombatObservation.Status](../../src/Sts2Agent/Observation/CombatObservation.cs)、[请求处理](../../src/Sts2Agent/Adapter/GameAdapter.cs)、[可用工具](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)。
- MCP 实现：[工具注册](../../src/sts2_mcp/mcp_catalog.py)、[GameTools.inspect_ui](../../src/sts2_mcp/game_tools.py)、[完整返回校验](../../src/sts2_mcp/output/inspection_details.py)、[公共预设](../../src/sts2_mcp/output/presets.py)、[提示与错误投影](../../src/sts2_mcp/output/player_output.py)。
- 上游核对使用上述程序集的本地反编译结果，位于 `.tmp/decompiled/`：`NTopBarPortraitTip.Initialize/OnFocus`、`AscensionHelper.GetHoverTip`、`NTopBarRoomIcon.GetHoverTipPrefixForRoomType`、`NTopBarBossIcon.OnFocus`、`NEnergyCounter`、`NStarCounter.OnHovered`、`NCombatCardPile.OnFocus`、`NEndTurnButton.OnFocus`、`NClickableControl.AllowFocusWhileDisabled`。不将反编译产物纳入 Git。

## 当前参数与返回契约

```json
{"preset":"full"}
```

- 仅接受可选 `preset: default/full`，默认 `default`。尚无 `summary`、来源筛选、按名称筛选或分组参数。原生文件操作不接收 preset；由 MCP 在完整读取和校验后处理。
- 成功主体为 `scene:"combat"` 和 `hover_tips`。每条提示包含 `title`、`description`、`sources`；数据结构允许 full 保留 `title:null`，default 省略该普通空值；当前内置来源通常有标题。数组为空时两者都保留 `hover_tips:[]`。
- `sources` 是完整基础观察中的字段路径，说明提示对应哪里，不包含资源当前值。它不是以本次 get_observation 预设为准的路径：例如观察 summary 会合并生命字段，但这里仍使用 `player.hp/player.max_hp`。
- 相同标题且正文相同的提示合并，sources 去重并保持出现顺序；正文不同则不会合并。空充能球槽的共同帮助可以有多个来源下标。
- 读取原生悬停文本并清理颜色、字体等标记，保留换行、实际快捷键与 `<Energy>/<Star>` 图标占位符。不移动鼠标、不切换语言、不打开页面，也不返回截图。
- 成功的相关详情读取会刷新内部状态许可；不要求先调用 get_observation。无 `available_actions`、当前资源数值或动作 transition；查看下一步可用操作使用 get_observation。
- 选牌时切回战场，成功结果另有 `notes.selection`，提示选牌仍待处理；没有该情境时不添加此项。`scene` 由本工具固定为 combat，建筑师背景也不例外，不能将其当作当前对局仍在战斗的标志。

## 提示覆盖与来源

| 内容 | sources | 原生条件与边界 |
| --- | --- | --- |
| 角色头像、进阶与成就限制说明 | `player.character`、`top_bar.ascension` | 头像及提示入口可见，且原生 `ShowTip` 为真；普通进阶 0 且无成就限制时不返回头像提示 |
| 顶栏生命说明 | `player.hp`、`player.max_hp` | 说明死亡规则，不返回生命值；sources 沿用现有契约 |
| 金币说明 | `top_bar.gold` | 不返回金币值 |
| 当前房间图标说明 | `top_bar.room_icon` | 使用实际显示的房间图标对应模板；问号房间可有已揭示类型变体 |
| 楼层说明 | `top_bar.floor` | 不返回楼层值 |
| 本幕首领说明 | `top_bar.bosses` | 仅根据可见且可识别的首领图标组装，支持一个或两个首领；不补出尚未显示的首领 |
| 地图入口 | `top_bar.map_visible` | 返回帮助和实际快捷键，不读取地图内容 |
| 牌组入口 | `top_bar.deck_visible`、`top_bar.deck_count` | 返回帮助和快捷键，不读取整副牌 |
| 设置入口 | `top_bar.settings_visible` | 只返回入口说明，不打开设置 |
| 能量 | `player.energy`、`player.max_energy` | 当前可见能量计；不返回当前值 |
| 星星 | `player.stars` | 当前可见星星计；不由角色名称推断或补齐 |
| 空充能球槽 | `player.orb_slots.N` | 完整球槽栏可读，且对应空槽可悬停；下标从 0 起；已有球通过 inspect_combatants 查看 |
| 抽牌／弃牌／消耗堆入口 | `player.draw_count`、`player.discard_count`、`player.exhaust_count` | 已绑定的可悬停入口及快捷键，不读取牌堆内容或顺序 |
| 结束回合入口 | `buttons.end_turn` | 当前可悬停，且玩家尚未标记为准备结束回合；遵循原生 OnFocus 条件 |

按当前节点可见性、视口与裁剪，以及禁用控件是否允许聚焦决定是否提供帮助。这些是固定位置的 UI 入口，不是可滚动卡牌／遗物列表；不能据完整可浏览候选规则补出隐藏入口。不返回手牌、药水、遗物、能力、意图、已有球或悬浮君王之剑的效果；这些由专门查看工具负责，也不虚构原生没有的格挡帮助。

## 场景目录与完整 full 示例

所有调用均为 `inspect_ui({"preset":"full"})`，参数错误例外单列。样本来源逐项列于 [manifest.json](2026-11-03-inspect-ui-examples/manifest.json)。JSON 文件保留真实 MCP 返回的所有字段，无省略号；同一错误结构共用示例，场景不会被误写为成功空数组。成功样本同时检查文本 JSON 与 structuredContent 一致、重复读取一致、default 与公共空值投影一致、读取前后原生状态一致。本轮成功样本未出现普通 null 字段，因此各自 default 与 full 相同。

| 组 | 场景与差异 | 完整返回 |
| --- | --- | --- |
| 01 | 普通无遮挡战斗；通用资源与入口帮助，不含卡牌／意图正文 | [combat.full.json](2026-11-03-inspect-ui-examples/combat.full.json) |
| 02 | 故障机器人：四个已有球与一个空槽；这里只增加空槽的通用说明 | [defect-orbs.full.json](2026-11-03-inspect-ui-examples/defect-orbs.full.json) |
| 03 | 打出 Capacitor 后多个空槽：同文合并，sources 列出各槽位 | [defect-extra-empty-slots.full.json](2026-11-03-inspect-ui-examples/defect-extra-empty-slots.full.json) |
| 04 | 再生成一个球：已占用槽位从通用帮助的 sources 中消失 | [defect-after-channel.full.json](2026-11-03-inspect-ui-examples/defect-after-channel.full.json) |
| 05 | 储君：增加 Stars 帮助；悬浮君王之剑不加入本工具 | [regent.full.json](2026-11-03-inspect-ui-examples/regent.full.json) |
| 06 | 亡灵契约师与奥斯提：不为伙伴重复通用帮助，也不补入奥斯提攻击 | [necrobinder-osty.full.json](2026-11-03-inspect-ui-examples/necrobinder-osty.full.json) |
| 07 | 手牌升级选择中通过眼睛切回战场：可读取，附待完成选牌的 notes；不可悬停的入口不返回 | [hand-selection-battlefield.full.json](2026-11-03-inspect-ui-examples/hand-selection-battlefield.full.json) |
| 08 | 独立候选选牌中切回战场：主体相同，当前可悬停入口可进一步减少，仍附 notes | [grid-selection-battlefield.full.json](2026-11-03-inspect-ui-examples/grid-selection-battlefield.full.json) |
| 09 | 建筑师终章：战斗背景仍可见，返回当前可读帮助；本工具仍报告 scene:combat | [epilogue.full.json](2026-11-03-inspect-ui-examples/epilogue.full.json) |
| 10 | 地图／牌组／弃牌堆覆盖战斗；选牌页本身、从战场切回选牌页 | [unavailable.full.json](2026-11-03-inspect-ui-examples/unavailable.full.json) |
| 11 | 普通事件、火堆、商店人物页及商品页、奖励、先古之民、宝箱 | 同上，均为 illegal_action；不会只读取这些页面可见的顶栏帮助 |
| 12 | 主菜单、通关结果页 | 同上，均为 illegal_action |
| 13 | 不支持的 preset，例如 `{"preset":"summary"}` | [invalid-preset.full.json](2026-11-03-inspect-ui-examples/invalid-preset.full.json) |
| 14 | 额外筛选参数，例如 `{"preset":"full","sources":["player.energy"]}` | [invalid-filter.full.json](2026-11-03-inspect-ui-examples/invalid-filter.full.json) |

相同结构的内容变体不穷举所有名字、快捷键或房间实例。以下保留源码核验边界，不能冒充本轮游戏实测：

- 可悬停的头像进阶说明、成就限制警告、双首领及仅显示第二首领的变体、其他房间图标、可见消耗堆入口：更换对应标题、正文及 sources，不增加新顶层结构。早期正式进阶战斗的完整样本见 `.tmp/live/mcp-ui-inspection.json` 及[当时验证记录](2026-10-29-ui-inspection-plan.md#验证证据)，不作为本轮当前版本的新采样。
- 控件隐藏、透明、离屏、被裁剪、禁用或空槽不可悬停：按前述条件减少条目；空数组的允许结构如下，属于依据实现整理，不是实测整个页面没有帮助。

```json
{"scene":"combat","hover_tips":[]}
```

- 正在瞄准或敌人回合不单独构成 inspect_ui 的拒绝条件；仍由 `CombatObservation.Status()` 和每个入口的可悬停条件决定。未在本轮人工制造这些瞬时状态。
- 暂停菜单、卡牌／遗物详情覆盖、原生弹窗、过渡遮罩、战斗节点未准备好或隐藏：当前返回 illegal_action；未逐一手动制造每种覆盖。结算摘要、历史及解锁页也不满足可见战斗条件，本轮只新采集正常通关结果页。连接失败和超时属于共用协议错误，见 [MCP 错误语义](../development/mcp.md#调用和错误语义)。

## 验证与未覆盖范围

- 使用自有隔离游戏、中文 UI 与真实 stdio MCP；覆盖 12 个复用夹具局、主菜单和单独启动的通关终章。共完成 55 次 inspect_ui 调用，其中带场景标签的 full 返回 31 份：12 份成功、17 份 illegal_action、2 份 invalid_request。重复结构只选代表导出，未把错误响应合成空提示数组。
- 普通战斗为 11 条；故障机器人各样本为 12 条，多个空槽的共同正文只出现一次；储君 12 条、亡灵契约师 11 条；手牌升级战场 10 条、独立候选战场 8 条；建筑师为 6 条顶栏帮助。基础观察是否列出 inspect_ui 与各场景实际调用结果一致。
- 原始证据分布于 `.tmp/2026-11-03-inspect-ui-review/gui-2/`（战斗、球槽、储君、奥斯提、两类选择、事件、火堆）、`gui-3/`（商店、奖励）、`gui-4/`（先古之民、宝箱）、`ending-gui/`（建筑师和结算）；各目录保留 evidence.json、截图、游戏日志及任务结果。通关实例通过原生测试 start_test_combat 初始化，之后的观察和推进使用真实 MCP。
- 文档链接、内嵌 JSON、12 份示例与原始证据逐字段相等、公开参数 schema 已验证。记录见 `.tmp/2026-11-03-inspect-ui-review/validation.json` 与 `coverage.json`。本轮未改实现，因此未重新编译或运行全量测试，未安装正式 Mod。
- 采样曾因强制地图无返回按钮、失败读取清空动作许可而中断，均为专用脚本假设错误，已修正采样流程。另有未处理自定义奖励的测试局在返回菜单后等待夹具 Pending 超时；该隔离进程已关闭，未继续复用。奖励页 inspect_ui 响应及读取不变性核验在清理超时前已完成，不能将清理失败记为读取失败，也不能把该次整体任务记为全部通过。
- 测试设施清理的取消链未在本轮修复；具体证据、判断与后续核验范围见 `.tmp/2026-11-03-inspect-ui-sampling-report.md`。上节列出的源码／历史变体也不提升为本轮实测结论。

## 参数与摘要讨论

尚未形成调整定稿，保持当前实现。接下来根据用户关心的信息讨论筛选及是否需要 summary，必要时核对是否扩大至非战斗的可见顶栏帮助；候选方案不能视为已实现契约。
