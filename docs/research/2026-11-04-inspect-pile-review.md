# inspect_pile 场景与参数核验

> 当前状态：场景核验完成，进入设计讨论；27 项 Python 检查、四局 GUI／54 次 stdio 调用和 30 项原生检查完成，已导出 31 份完整示例。五项问题及候选参数／基础观察接入尚未定稿，未修改工具行为。inspect_pile 未核销，暂无阻塞。

## 优先关注的问题

| 编号 | 优先级 | 问题与影响 | 依据及建议处理范围 |
| --- | --- | --- | --- |
| PILE-01 | 中；错误准确性 | 非战斗、页面遮挡、当前页不可替换、切页后状态变化及读取中断，原生有不同原因，但没有公开 `public_message`；MCP 最终都只说 `The requested action is unavailable.` | [浏览请求](../../src/Sts2Agent/Adapter/GameAdapter.Views.cs)、[错误公开](../../src/sts2_mcp/output/error_output.py)。建议沿用牌组的安全具体原因机制；隐藏内部异常诊断 |
| PILE-02 | 中；错误恢复 | 即使入口门控在任何 UI 操作前明确拒绝，inspect_pile 仍按 effect:view 清除已有许可，下一次原本合法的操作会被 observation_required 阻挡 | [工具注册](../../src/sts2_mcp/tool_registry.py)、[会话](../../src/sts2_mcp/game_session.py)。建议接入已有显式 ui_unchanged 保证，只保留已有许可；关闭旧页、点击目标等交互之后不能作此保证 |
| PILE-03 | 中；已登记的观察缺口 | 已打开抽牌／弃牌／消耗页时，get_observation 仍只有 screen.view、可读顶栏等上下文，没有当前列表，summary 也仍为占位 | [原生快照](../../src/Sts2Agent/Observation/GameObservation.cs)、[浏览摘要](../../src/sts2_mcp/output/observation_presets.py)。属于[用户 TODO](../development/TODO.md)已有范围；建议沿用牌组的 face_full／face_default／summary 和同一身份表，只读已打开页 |
| PILE-04 | 中；验证设施 | verify_mcp_piles 仍断言 close_card_view 返回完整 observed，但该工具已按定稿返回 actions_only，正确返回也会使旧脚本失败 | [旧断言](../../tests/game/verifiers/verify_mcp_piles.py)。应同步到共用 actions_only 投影，并继续验证关闭后的页面与合法行动；不能据此恢复旧生产输出 |
| PILE-05 | 低；工具提示词 | 工具正文承诺不可用入口返回 cards:null，但默认 default 会省略 cards，summary 也一样；提示与最常用返回不一致 | 真实 hidden-exhaust 三预设样本及公共空值规则确认。建议正文改为说明 status:empty／unavailable，null 细节放到 full 契约，不改变已有默认空值规则 |

五项均尚未修复；不把参数设计或修改文档算作问题解决。没有发现新的卡牌离屏截断：读取来自完整原生网格列表。附魔与 Affliction 已由共用 BrowsedCard／CardAppearance 接入，不再重复登记历史缺口。

## 核对基线与来源

- 核对日期：2026-11-04；代码 `e8a0b18`，Mod `0.58.0`、MCP `0.60.0`、原生 schema `39`。现行版本统一见 [README](../../README.md#当前版本与前提)。
- 游戏 Linux `v0.107.1`，release build `59260271`；RitsuLib `0.6.10` 兼容运行时。重新核对游戏目录内 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 已有构建和隔离运行时 Mod DLL 均为 `40e3ba694e13236c862d8f80dff3c6c6294861ab5569eebd36e50125601c3ed6`。本审阅不重建、不安装正式 Mod。
- 原生实现：[PileOptions](../../src/Sts2Agent/Actions/PileOptions.cs)、[PileInspection](../../src/Sts2Agent/Observation/PileInspection.cs)、[CardView](../../src/Sts2Agent/Observation/CardView.cs)、[BrowsedCard](../../src/Sts2Agent/Observation/BrowsedCard.cs)、[浏览请求](../../src/Sts2Agent/Adapter/GameAdapter.Views.cs)、[可用工具](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)和[响应装配](../../src/Sts2Agent/Adapter/ResponseBuilder.cs)。
- Python：[参数与响应校验](../../src/sts2_mcp/output/pile_details.py)、[共用卡牌](../../src/sts2_mcp/output/card_format.py)、[共享说明](../../src/sts2_mcp/output/public_output.py)、[参数归一化](../../src/sts2_mcp/request_arguments.py)、[工具注册](../../src/sts2_mcp/tool_registry.py)及[会话](../../src/sts2_mcp/game_session.py)。
- 从上述目标程序集重新反编译 NCardPileScreen、NCombatCardPile、NDrawPileButton、NDiscardPileButton、NExhaustPileButton，证据位于 `.tmp/2026-11-04-inspect-pile-review/source/`，不纳入 Git。重点核对 OnPileContentsChanged、OnRelease、空堆气泡、消耗入口展示及原生页面控件。
- 当前接口唯一说明见[战斗牌堆指南](../development/pile-inspection.md)。下述为核验基线的实际行为与候选设计，不能替代现行接口。

## 当前参数与职责

```json
{"pile":"draw","preset":"full"}
```

| 参数 | 已实现行为 |
| --- | --- |
| pile | 必填；draw／discard／exhaust，仅战斗牌堆 |
| preset | default／full／summary，省略为 default；每次只影响输出，不改变页面状态 |

目前没有 card_ids，传入会在 IPC 前以 invalid_request 拒绝。旧 detail_level、sort_by、descending、view_upgrades 也都拒绝。牌堆 ID 是 `pile:N` 字符串，不能套用 inspect_hand 的整数或 inspect_deck 的 `deck:N`。

调用真实打开／复用原生页面，属于 view，不要求预先观察；成功结果会刷新许可。成功查看不表示能穿透覆盖页出牌：非空页面保持打开，须先 close_card_view；空堆点击显示原生气泡，页面不打开。整体门控允许浏览时，隐藏／禁用的目标入口是成功的 unavailable 结果，不读取内部牌堆补齐内容；所有入口都不可用时整体拒绝，而非返回 unavailable。

同页读取复用页面，不重复点击以免原生按钮把它关闭。换堆先关闭当前卡牌页再点目标入口，原生点击后重新核对战斗、玩家和画面。目标入口隐藏时保留旧卡牌页；非空牌组可替换牌堆，反向亦可。地图、直接显示的选牌、详情、模态及非玩家可行动阶段不能穿透。

原生 NCardPileScreen 没有牌组页的升级预览或四类排序控件。抽牌堆按稀有度及模型条目名重排，绝不返回真实抽取顺序；弃牌及消耗堆沿用各自原生浏览列表顺序。不要为接口一致而给牌堆增加 UI 中不存在的排序或升级模式。

当前提示词：

```text
Open/reuse a combat draw, discard or exhaust page, replacing another card page. Returns the entire pile in display order, never draw order. Leaves an opened page until close_card_view. Empty piles return cards=[]; unavailable entries return cards=null.
```

职责基本准确，但 cards:null 只适用于 full；default／summary 会省略普通 null。后续应将末句改成描述 status:empty／unavailable，避免与默认输出矛盾。card_ids 若采用，只在参数说明及一句简短的输出筛选提示中表达。

## 当前返回与信息边界

| 字段 | full | default | summary |
| --- | --- | --- | --- |
| scene／screen | 同次快照；scene:combat，页面是 draw_pile／discard_pile／exhaust_pile | 同 full | 同 full |
| pile | 请求的 draw／discard／exhaust | 同 full | 同 full |
| status | opened／empty／unavailable | 同 full | 同 full |
| message | 页面原生帮助、空堆原生气泡或入口不可用原因；英语 | 同 full | 目前仍保留 |
| cards | opened 为完整列表；empty 为 []；unavailable 为 null | 普通 null 省略 | 可读列表采用共用卡牌摘要；不可用时省略 |
| cards[].id | 战斗内按原卡实例稳定的 pile:N，可跨牌堆对应 | 同 full | 同 full |
| name／type／energy_cost／star_cost／费用颜色／enchantment／affliction | 共用完整牌面，普通 null 保留 | 普通 null 省略 | 共用摘要，保留实际存在的费用和外观 |
| rarity／visual_card_pool／description | 实际牌堆上下文的完整信息 | 同 full | 省略 |
| hover_tips | 根级按 title＋description 去重，以 card_ids 关联；可读空列表为 []，不可用不生成 | 同 full | 省略 |
| reason | 仅 unavailable：entry_not_visible／entry_disabled | 同 full | 同 full |

不附送手牌、敌人、available_actions 或 transition；需要操作列表时通过 get_observation 获知。牌堆网格不生成手牌专有的 outline／unplayable_markers。full 中无附魔、无 Affliction 均保留 null；summary 的普通 null 及空不可出牌标记走共用规则。

pile ID 在本场战斗的牌堆实例间稳定，换战斗清空；分配来源是实际网格浏览列表，不是内部真实抽取顺序。费用、正文、动态数值和临时战斗修改使用原牌堆上下文，在隔离克隆上格式化，不向真实牌堆写入模型或改变 RNG。summary 当前仍让原生读取完整内容，再由 Python 精简；这属于可评估的性能范围，不应为它再建立一套卡牌格式。

## 场景目录

完整调用与返回见[示例目录](2026-11-04-inspect-pile-examples/README.md)及[来源清单](2026-11-04-inspect-pile-examples/manifest.json)，其中 29 份为真实 stdio 返回、1 份为原生测试响应的当前 full 投影、1 份为实现整理的禁用入口。示例均保留实际字段；错误返回没有人为补上 scene／screen。

| 分支 | 完整 full 示例 |
| --- | --- |
| 非空三堆 | [抽牌](2026-11-04-inspect-pile-examples/draw.full.json)、[弃牌](2026-11-04-inspect-pile-examples/discard.full.json)、[消耗](2026-11-04-inspect-pile-examples/exhaust.full.json)；同目录另有 default／summary |
| 可见空入口 | [空抽牌](2026-11-04-inspect-pile-examples/empty-draw.full.json)、[空弃牌](2026-11-04-inspect-pile-examples/empty-discard.full.json) |
| 隐藏或禁用 | [隐藏消耗](2026-11-04-inspect-pile-examples/hidden-exhaust.full.json)为真实返回；[禁用入口](2026-11-04-inspect-pile-examples/constructed-disabled.full.json)为实现整理 |
| 跨页行为 | [抽牌替换牌组](2026-11-04-inspect-pile-examples/draw-replaces-deck.full.json)、[空弃牌关闭抽牌](2026-11-04-inspect-pile-examples/empty-closes-draw.full.json)、[隐藏消耗保留牌组](2026-11-04-inspect-pile-examples/hidden-keeps-deck.full.json) |
| 长列表／上下文费用 | [长抽牌列表](2026-11-04-inspect-pile-examples/long-draw.full.json)，原生夹具响应投影，不是自然生成的牌堆 |
| 已打开后的基础观察 | [抽牌](2026-11-04-inspect-pile-examples/observation-draw.full.json)、[弃牌](2026-11-04-inspect-pile-examples/observation-discard.full.json)、[消耗](2026-11-04-inspect-pile-examples/observation-exhaust.full.json)，均仍缺列表；[关闭](2026-11-04-inspect-pile-examples/closed.full.json)则是已定稿的 actions_only |
| 拒绝与恢复 | [主菜单](2026-11-04-inspect-pile-examples/error-main-menu.json)、[事件](2026-11-04-inspect-pile-examples/error-event.json)、[地图](2026-11-04-inspect-pile-examples/error-map.json)、[选牌覆盖](2026-11-04-inspect-pile-examples/error-selection.json)、[拒绝后许可丢失](2026-11-04-inspect-pile-examples/error-after-rejection.json)、[尚不支持 card_ids](2026-11-04-inspect-pile-examples/error-filter.json) |

1. 玩家可行动战斗：非空抽牌、弃牌、消耗页；首次打开和同页复用。
2. 抽牌／弃牌为空：实际点击已显示且启用的入口，显示对应气泡，cards:[]，回到战斗画面。
3. 消耗入口隐藏或其他入口禁用：status:unavailable；不把隐藏牌堆解释成已知空堆。
4. 已有牌组／其他牌堆：非空目标替换当前页；可见空目标关闭旧页并产生气泡；隐藏目标保留旧页。
5. 待处理选择切到战场后浏览：使用该视图中的原生牌堆按钮；不能因此完成选择或在下层出牌。详情页及直接显示选择时拒绝。
6. 地图、事件／火堆／奖励等非战斗、主菜单、转场／瞄准／出牌中：拒绝，不返回假空列表。
7. 非法参数：本地拒绝、不发 IPC、不清除已有许可。
8. 读取期间人为关闭、遮挡或换页：拒绝，不重新打开或清理人的新页面；超时／取消不自动重试。

场景 3 的禁用入口、场景 5 的待处理选择、特殊卡面和异常可见空消耗入口仍须区分源码核对与真实样本，不能把其存在推演成已自然实测。

## 候选设计，尚未定稿

建议保持已实现三种状态和 summary 卡牌格式，先处理 PILE-01–05，再补以下范围：

- **card_ids**：沿用牌组规则，取当前目标页的 `pile:N`；省略／null 全部、[] 为空，去重后按原生列表顺序返回，关联解释一起裁剪。合法但不在目标堆的 ID 合并为 errors，例如 cards_not_in_pile；一个 ID 在另一堆存在也不能穿透读取。筛选不能用于出牌，也不改变 UI 或后续基础观察。
- **空／不可用组合**：建议保留 pile／status／message／reason。成功空堆的已知集合为 []，筛选非空 ID 时可明确报不在该堆；不可用入口的集合未知，不能把请求 ID 全部伪报不存在。建议 unavailable 不执行成员判断、不生成假卡或 not_found 错误，先以 status／reason 表达当前不可检查。非法 ID 语法仍在操作前拒绝。
- **基础观察**：只读当前暴露且就绪的牌堆页，full/default/summary 分别走 face_full／face_default／共用 summary，无正文或悬停解释；复用同一 PileInspection 身份表、完整网格顺序及 pile 标识，不包含不存在的升级／排序控件。关闭／遮挡后不附缓存，不继承 inspect_pile 的输出筛选；actions_only／top_bar 维持原契约。
- **字段组织**：优先复用专门工具的 pile＋cards，页面状态仍由 screen 表达；是否把原生帮助 message 放入基础观察及是否从专门工具 summary 省略，留待讨论。直接嵌入专门工具完整对象会重复 scene／screen／status，也会夹带悬停正文，不推荐。
- **小范围重构**：让快照与专门查看共用牌堆读取／身份表，增加明确的静态／完整读取参数；滤选和预设投影留在 Python。前置原因与 available_actions 复用同一门控入口；未交互保证沿用已落地的牌组机制，不把整个 inspect_pile 改成 read。

不建议将 ID 筛选写成新的游戏页面操作，或仅因 status 为 illegal_action 就保留许可；切换牌堆可能已经关闭旧页或点击目标。

## 验证记录

已运行 tests.python.test_mcp_piles、test_browsing_observation_summary、test_inspection_context、test_deck_inspection，共 **27 项通过**，日志 `.tmp/2026-11-04-inspect-pile-review/python.log`。覆盖预设、共享提示、非法参数本地拒绝、三种牌堆状态、身份、畸形回复、超时／取消及既有牌组共用契约；模拟传输不代表实际 UI 行为。

四局 GUI／54 次真实 stdio 调用及主菜单检查通过，正常局清理完成，报告 `.tmp/2026-11-04-inspect-pile-review/verified/report.json`。包含空抽牌／弃牌、隐藏消耗、非空三堆的三预设、跨页替换、基础观察缺口、主菜单／非战斗／地图／选牌拒绝及恢复。火堆选牌覆盖时 inspect_pile 在前置门控拒绝；紧接着调用此前可用的 selection_option 却得到 observation_required，重新观察后同一选项可成功执行，确认 PILE-02。

独立原生检查 **30 项通过**，报告 `.tmp/2026-11-04-inspect-pile-review/native/report.json`。包含完整长列表及滚动区域外卡牌、原生重排而非抽牌顺序、稳定身份与跨堆对应、临时能量／星数费用、Corruption 上下文、卡牌／RNG／语言不变，以及读取期间页面被关闭／详情遮挡／替换后的拒绝且保留新页面。夹具恢复原牌堆检查通过；这些是主动构造的边界，不等同于自然游玩全覆盖。该实例退出时在 terminate 等待后强制关闭自有进程，exit_code 为 -9；检查通过不表示正常退出验证通过。

旧 verify_mcp_piles 在实际游戏中按预期失败，日志 `native/legacy-verifier.log` 精确落在 `assert await call("close_card_view") == observed`，确认 PILE-04；没有把它计为通过。此前两批采样也不计为整批通过：根目录脚本误以为刀刃之舞会进入弃牌，final 批脚本尝试关闭第 0 层的强制地图。前者由实际牌面及 transition 的消耗记录定位，后者按夹具原生规则改用正常 suite reset 收尾；失败证据均保留，未为测试调整生产门控。所有自有游戏进程已关闭。

尚未新增实际样本的范围：所有候选类型的战场视图、禁用入口和异常可见的空消耗入口、全部附魔／Affliction、敌方回合／瞄准／跨房间瞬态、多人及第三方页面。对应门控与共用格式已核对源码；31 份示例不能作为这些分支均已实测的证明。

持续维护文档补充已核实的旧验证脚本问题及链接，并明确 unavailable 的前提是整体浏览门控已通过，避免把所有入口禁用时的拒绝误解为成功状态。没有修改生产工具、公开参数、版本或用户 TODO，没有重建／安装 Mod。后续实现须重新运行更新后的牌堆专项验收。
