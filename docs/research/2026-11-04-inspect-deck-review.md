# inspect_deck 场景与参数核验

> 当前状态：场景与现有格式核验已记录，进入设计讨论；尚未定稿或修改工具行为。优先问题为具体拒绝原因、未操作 UI 的前置拒绝恢复，以及关闭牌组后基础观察丢字段；基础观察中的牌组内容仍是已登记的待设计范围。工具尚未核销。总流程见[工具核验清单](2026-11-02-mcp-tool-review.md)。

## 优先关注的问题

| 编号 | 优先级 | 问题与影响 | 依据及候选处理范围 |
| --- | --- | --- | --- |
| DECK-01 | 中；错误准确性 | 入口不可用、控件不可用、打开失败及读取期间页面变化，原生已有不同的 message，但未公开；MCP 均退化为 `The requested action is unavailable.` | [浏览请求](../../src/Sts2Agent/Adapter/GameAdapter.Views.cs)、[原生错误构建](../../src/Sts2Agent/Adapter/ResponseBuilder.cs)及[公开错误](../../src/sts2_mcp/output/error_output.py)。候选：公开经过选择的安全原因，区分前置拒绝与打开后的失败；不公开异常诊断 |
| DECK-02 | 中；错误恢复 | 尚未操作 UI 的明确前置拒绝也清除旧许可，导致原本可执行的后续动作被 `observation_required` 阻挡 | 工具固定为 effect:view；[GameSession](../../src/sts2_mcp/game_session.py)的保留条件只覆盖纯读取与专门保证未执行的出牌拒绝。候选：原生明确证明前置拒绝且 UI 未改变，再由共用层保留旧许可；已有交互、过期或未知结果仍须重新读取 |
| DECK-03 | 中；关闭后的观察完整性 | close_card_view 只投影八个基础字段，丢掉当前事件／火堆／宝箱／奖励／地图等内容；full 连缺少内容的 null 也不保留。在非战斗场景中，LLM 看不到关闭后应该出现的房间数据 | [closed_card_view](../../src/sts2_mcp/output/deck_details.py)使用旧字段白名单，未走完整 observation_details；真实事件、火堆、宝箱及奖励的关闭返回均确认缺失。候选：关闭结果接入现行基础观察校验／投影；不据此核销 close_card_view 的其余行为 |

DECK-02 不能靠将工具改成 read，或遇到 illegal_action 一律保留许可来处理。打开页面、排序及切换升级预览均会改变 UI；失败也可能发生在这些操作之后。`execution` 中的 false 只表示没有记录到相应证据，现有协议明确不将它定义为“确定没有执行”。需要补足实际保证，而非放宽所有浏览工具。

另有一项**已登记、尚未实现的功能缺口**：打开牌组后，get_observation 仍只返回 `screen.view:deck` 和可见顶栏等基础内容，不返回牌组列表、排序或升级预览。其 summary 也仍是页面主体的 default 占位。该项属于[用户 TODO](../development/TODO.md)与[浏览覆盖约定](2026-11-02-get-observation-browsing.md#本阶段定稿与后续接入)，应随本工具设计一并确定，不能当作已经解决。

没有发现新的牌组离屏截断：实现从原生网格完整排序列表读取，保留重复卡的独立身份；当前 summary 已复用共用卡牌摘要。原先浏览卡的附魔缺口已由[共享卡牌实现](2026-11-03-card-format-implementation.md)接入 CardAppearance.Preview，不能继续列为待修问题。

## 核对基线及来源

- 核对日期：2026-11-04；代码 `a9d729a`，Mod `0.57.0`、MCP `0.59.0`、schema `38`。现行版本统一见 [README](../../README.md#当前版本与前提)。
- 游戏 Linux `v0.107.1`、release build `59260271`，RitsuLib `0.6.10` 兼容运行时；重新校验 `data_sts2_linuxbsd_x86_64/sts2.dll` 的 SHA-256：`d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 采样的构建 DLL 与隔离运行时 DLL 均为 `4a735cf4bfb7a943ee6d9aeb5a9188344ad91dcb5ea6b8c973aa1a30e6804210`；没有重新构建或安装正式 Mod。
- 原生：[DeckInspection](../../src/Sts2Agent/Observation/DeckInspection.cs)、[DeckView](../../src/Sts2Agent/Observation/DeckView.cs)、[CardView](../../src/Sts2Agent/Observation/CardView.cs)、[BrowsedCard](../../src/Sts2Agent/Observation/BrowsedCard.cs)、[外观读取](../../src/Sts2Agent/Observation/CardAppearance.cs)、[参数校验](../../src/Sts2Agent/Actions/DeckOptions.cs)、[浏览请求](../../src/Sts2Agent/Adapter/GameAdapter.Views.cs)、[可用工具](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)。
- Python：[工具注册](../../src/sts2_mcp/tool_registry.py)、[牌组校验](../../src/sts2_mcp/output/deck_details.py)、[共用卡牌格式](../../src/sts2_mcp/output/card_format.py)、[共用装配](../../src/sts2_mcp/output/public_output.py)、[参数归一化](../../src/sts2_mcp/request_arguments.py)、[会话](../../src/sts2_mcp/game_session.py)。
- 重新从该程序集反编译 `NDeckViewScreen`、`NCardGrid`、`NCardsViewScreen`、`NTopBarDeckButton`，证据位于 `.tmp/2026-11-04-inspect-deck-review/source/`，不纳入 Git。重点核对 ShowScreen、DisplayCards、SetCards、IsShowingUpgrades、ToggleShowUpgrades、OnControllerStateUpdated 及顶栏按钮流程。
- 当前持续维护契约见[牌组指南](../development/deck-inspection.md)。本记录区分实现现状与下方候选设计，不替代该指南。

## 当前参数与职责

```json
{"preset":"full","view_upgrades":true,"sort_by":"cost","descending":true}
```

| 参数 | 当前行为 |
| --- | --- |
| preset | default／full／summary，默认 default；每次调用独立选择，不写入页面状态 |
| view_upgrades | 可选布尔值；省略沿用当前页面；新页默认 false；原生控件不可用时不能强制切换 |
| sort_by | obtained／type／cost／name；省略沿用；新页默认 obtained |
| descending | 可选布尔值，必须同时指定 sort_by；显式排序且省略方向时采用升序 |

当前没有卡牌筛选参数。`card_ids` 会被本地校验明确拒绝；不能套用 inspect_hand 的整数 ID。

该工具真实打开／复用原生永久牌组页，替换现有牌堆页；地图是另一层，关闭牌组可返回地图。它不要求事先观察，成功结果可更新动作许可，但不允许在覆盖页执行下层动作。查看后页面保持打开，须调用 close_card_view 返回；这个关闭工具另行核验，不因本记录而核销。

省略排序和升级参数的连续调用沿用设置；关闭并重新打开后使用原生新页默认值。排序是原生 UI 操作，筛选若获采用则只应裁剪输出，两者不能混成同一种作用。

`screen.status:covered` 表示底层战斗／房间受牌组覆盖，不表示牌组本身不可读。screen.view:deck 与成功返回的列表共同表达当前页面。

当前提示词：

```text
Open/reuse the native full-deck page when its entry is available and read the entire browsable deck. Upgrade preview does not upgrade owned cards. Leaves the page open; close with close_card_view.
```

职责表达准确，长度适中。升级、排序和 preset 的省略语义已有参数说明，不需要重复写入工具正文。

## 返回字段与信息边界

| 字段 | full | default | summary |
| --- | --- | --- | --- |
| scene／screen | 当前房间／结算背景；screen.view 为 deck | 同 full | 同 full |
| view_upgrades | 页面实际升级预览状态 | 同 full，false 保留 | 同 full |
| sort.by／descending | 当前主排序及方向 | 同 full，false 保留 | 同 full |
| deck[].id | `deck:N` 字符串；同局中对原卡实例稳定 | 同 full | 同 full |
| name／type／energy_cost | 当前普通或升级预览牌面 | 普通 null 省略 | 共用卡牌摘要 |
| star_cost／费用颜色 | 有相应图标或颜色时返回；full 的普通空值保留 | 普通 null 省略 | 同 default |
| enchantment／affliction | 共用浏览牌外观；无内容为 null | 普通 null 省略 | 保留实际存在的外观 |
| rarity／visual_card_pool | 完整详情 | 同 full | 不返回 |
| description | 英语正文，按永久牌组及升级预览上下文格式化 | 同 full | 不返回 |
| hover_tips | 按 title／description 去重，以 card_ids 关联；无提示仍为 [] | 同 full | 不返回 |
| notes.selection | 仅存在待处理选择且被浏览页遮挡等相应状态时出现 | 同 full | 同 full |

不回显 preset，不增加 available_actions 或 transition。基础观察可提供当前可用操作。牌组列表为空时可返回 deck:[]；这是成功结构，与入口不可用的拒绝不同。

每张重复牌有独立 ID；排序改变位置，不改变该实例的 ID。它与手牌整数 ID、牌堆 `pile:N` ID 分开，不能拿来出牌或直接选择其他界面中的卡。

卡牌摘要沿用[手牌摘要](../development/hand-inspection.md#参数与返回范围)；不是给网格补上不存在的手牌状态。网格没有 unplayable_markers 或 outline 时不生成这些字段，也不会制造“不可出牌”的标志。附魔的 dimmed:false 不受遗物 grayed_out／pulsing 的局部 false 精简影响。

浏览读取在隔离克隆上预览下一次可用升级，不升级实际持有牌；不能再升级的牌保持原样。名称排序使用游戏语言，中文界面的拼音排序不等于英语输出的字母排序；费用排序按原生原卡排序，开启升级预览后，显示费用不保证重新按预览费用排序。这些属于 UI 语义，不是需要纠正的排序错误。

## 场景与完整示例

完整返回、实际参数、来源及校验值见[示例目录](2026-11-04-inspect-deck-examples/README.md)。其中游戏实测、源码核对和实现整理分别标识；不会把整理的空牌组冒充自然实测。

适用场景分为以下结构分支，卡牌内容不同不另造协议：

1. 可操作战斗：首次打开、复用、升级预览及四类主排序。
2. 事件、火堆、宝箱、奖励、商店、先古之民、占卜及建筑师背景：同一牌组主体，scene 保留所属场景；覆盖页不会把 scene 改成 deck。
3. 地图上打开牌组：相同主体；关闭回到原地图，不自动关闭地图。
4. 从战斗牌堆替换为牌组、隐藏战斗选择后从战场打开牌组：同一主体；待处理选择可另带 notes.selection。
5. 空牌组：deck:[]、full 的 hover_tips:[]。
6. 主菜单、直接覆盖的选牌页、确认弹窗、卡牌详情、非行动阶段或过渡等入口不可用状态：illegal_action；不存在“成功返回空牌组”来代替拒绝。
7. 非法枚举、类型、未知参数和缺少 sort_by 的方向：本地 invalid_request；不发送游戏请求、不改变页面和已有许可。
8. 等待期间关闭、覆盖、替换页面或更换玩家：原生重新核实后拒绝，不自动重开、恢复排序或关闭人的新页面；超时与取消不自动重试。

## 候选设计，待用户确认

- **summary 保持现有共用卡牌摘要**。上下文、view_upgrades、sort 有助于理解实际页面，应保留；description、稀有度、卡池和所有悬停解释继续省略。没有证据支持另做一套牌组摘要字段。
- **可选卡牌筛选**：若需要聚焦单张或少量牌，建议使用 `card_ids:["deck:3"]`；省略／null 全部、[] 为空，与其他工具的筛选约定一致。按原生排序输出，合并报告不在当前牌组的 ID，保留有效条目；共享提示也只保留所选牌的关联。已有稳定 ID，通常不再需要位置映射。这是新参数候选，尚未实现。
- **基础观察的牌组内容**：推荐打开后读取同一完整网格，get_observation.full/default 使用共用完整卡牌格式，summary 使用共用卡牌摘要；包括当前升级模式及排序。专用工具和观察共用读取／投影，避免在基础观察中再次打开或切换页面。具体容器字段仍待决定；地图与三类牌堆的内容不能借此宣称已完成。
- **先修正确性，再接参数与观察内容**：优先 DECK-01–03；以浏览请求的执行阶段和共用观察投影为边界做小范围重构。当前原生、Python 卡牌格式和共享提示已有明确分工，未发现再次进行大范围架构重构的必要。
- **关闭结果复用完整观察**：DECK-03 的范围包括牌组和牌堆共用的关闭返回；应使用现行观察入口代替旧字段名单，保留关闭后的实际页面与遮挡规则，不补回仍被覆盖的内容。

## 验证及尚未覆盖范围

现有牌组、共用卡牌、文件投影和浏览摘要专项测试共 **39 项通过**，日志 `.tmp/2026-11-04-inspect-deck-review/python.log`。检查覆盖非法参数不发送、三预设、重复调用、排序／升级状态保留、字段校验、成功关闭后的行动、非法原生回复／超时／取消后的许可处理；模拟传输不能替代游戏内样本。

真实 GUI 与 stdio MCP 采样覆盖战斗、事件、火堆、宝箱、奖励、商店、先古之民、占卜、建筑师、主菜单拒绝和选牌覆盖拒绝，导出 **27 份完整 JSON**，其中 26 份为真实返回、1 份为空牌组的实现整理。战斗包含升级、四种主排序、地图叠加、返回地图和参数拒绝；其他房间属于相同返回结构的场景变体。参数、来源文件／条目、基线和校验值见示例 manifest。

- DECK-01：主菜单和火堆选牌覆盖的真实拒绝均只显示通用错误；原生源码有具体原因但未 opt-in 公开。
- DECK-02：火堆锻造候选已显示时，inspect_deck 被前置拒绝；紧接着调用已经读取到的有效 selection_option，被 MCP 的 observation_required 阻挡。重新观察后同一按钮可成功执行。证据 `.tmp/2026-11-04-inspect-deck-review/remaining/selection/evidence.json`。
- DECK-03：四个真实房间响应的同一原生快照分别走 get_state 与 close_card_view 解码，后者固定缺失 13 个字段，实际非空的 event／rest_site／treasure／rewards 也丢失。回放见 `.tmp/2026-11-04-inspect-deck-review/close-probes.json`；真实关闭返回另见示例。牌组指南原先笼统声称返回基础观察，已补实际缺口说明，并保留完整观察的待修要求，没有把缺口改写成设计目标。

采样分三批，不能将前两批报告写成通过：第一批取得六类场景样本，奖励页清理超时；第二批完成选牌拒绝／恢复复现，随后奖励收尾过早调用尚未列入 available_actions 的 proceed 而失败。原生奖励流程需要结束 Offer，关闭牌组后其按钮还会短暂等待恢复。最后一批采用现有验证脚本的做法：按 available_actions 等待恢复，再跳过奖励并选路离房；五个测试局全部采样、正常清理通过，报告为 `.tmp/2026-11-04-inspect-deck-review/final/report.json`。没有放宽生产门控或修改奖励实现；三个自有游戏进程均已关闭。

未重新穷举：读取期间关闭／替换／覆盖的生命周期中断、空牌组、超过一屏的长牌组、全部卡牌及附魔／Affliction 内容、手柄隐藏升级控件、双人／第三方页面与其他瞬态。长列表读取和隔离克隆由当前源码及已有 DeckInspectionChecks 核对；这份记录的新测试局永久牌组均为 10 张，不能称为新的长列表实测。换幕尚无房间的 unrecognized 牌组、从非空牌堆替换和选择战场视图的独立新样本也未补采，按共用门控列入后续验证范围；没有把历史结果当作新采样。

没有修改生产工具、公开 schema、版本、正式安装或用户 TODO；保持当前逐工具审阅阶段。
