# close_card_view 场景与参数核验

> 当前状态：现状核验完成，进入设计讨论；29 项 Python、7 组本地探针、四局 GUI／43 次真实 MCP 调用完成，已导出 20 份完整示例。成功 actions_only 保持原定稿，CLOSE-01–02 尚未修复，close_card_view 未核销。暂无阻塞。

## 优先关注的问题

| 编号 | 优先级 | 问题与影响 | 证据及建议范围 |
| --- | --- | --- | --- |
| CLOSE-01 | 中；错误准确性 | 没有受支持的浏览页、被更高层遮挡、返回按钮不可用等前置拒绝，原生只有同一个内部 message；没有 public_message，MCP 进一步退化为 `The requested action is unavailable.`，无法判断应该返回选择、关闭详情还是当前根本没有浏览页 | [请求入口](../../src/Sts2Agent/Adapter/RequestDispatcher.cs)、[CardView](../../src/Sts2Agent/Observation/CardView.cs)、[错误公开](../../src/sts2_mcp/output/error_output.py)。建议复用统一的关闭可用性／安全原因入口，区分上述条件，异常诊断继续私有 |
| CLOSE-02 | 中；错误恢复 | 前置拒绝发生在 UiChanged／ForceClick 之前，确定没有关闭任何页面，却仍清除旧 MCP 许可，原本合法的动作被 observation_required 阻挡 | [工具注册](../../src/sts2_mcp/tool_registry.py)、[会话](../../src/sts2_mcp/game_session.py)。close_card_view 尚未登记显式未交互拒绝；即使模拟回复提供 ui_unchanged:true 也不会恢复旧许可。建议沿用牌组／牌堆已落地机制，仅明确未交互时保留已有许可 |

两项尚未修复，属于用户既有“错误原因与恢复提示”“工具报错后的观察前置要求”范围。完整观察先校验、成功最小投影及未知结果清除许可均已成立，没有把这些已处理行为重复列为问题。

## 核对基线与证据

- 日期：2026-11-04；代码 `86750da`，Mod `0.59.0`、MCP `0.61.0`、schema `40`；现行版本统一见 [README](../../README.md#当前版本与前提)。
- 游戏 Linux `v0.107.1`，release build `59260271`，RitsuLib `0.6.10` 兼容运行时。重新核对游戏安装目录内 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 原生：[RequestDispatcher](../../src/Sts2Agent/Adapter/RequestDispatcher.cs)、[CardView](../../src/Sts2Agent/Observation/CardView.cs)、[可用工具](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)、[等待／采样](../../src/Sts2Agent/Adapter/GameAdapter.Settling.cs)、[响应装配](../../src/Sts2Agent/Adapter/ResponseBuilder.cs)。
- Python：[注册](../../src/sts2_mcp/tool_registry.py)、[请求归一化](../../src/sts2_mcp/request_arguments.py)、[完整观察校验](../../src/sts2_mcp/output/observation_details.py)、[公共预设](../../src/sts2_mcp/output/observation_presets.py)、[会话](../../src/sts2_mcp/game_session.py)、[文件 CLI](../../src/sts2_mcp/roundtrip_client.py)。
- 从目标程序集重新反编译 NCapstoneContainer、NDeckViewScreen、NCardPileScreen，证据 `.tmp/2026-11-04-close-card-view-review/source/` 不纳入 Git。重点核对 Close／CloseInternal／OnReturnButtonPressed／AfterCapstoneClosed。
- 构建与隔离运行时 DLL 均为 `09e9ea505f49b918b20ae3b558ea55628753a588d2097e8251d4116dc5ed7788`。本审阅不重建、不安装正式 Mod。

## 当前参数与成功返回

```json
{"preset":"full"}
```

公开参数只有通用 preset：default（默认）／full；两者输出相同。summary／actions_only／top_bar、目标页面、card_ids 等额外参数不接受。原生文件请求无业务参数；MCP 和普通 CLI 消费 preset，--raw 保留原始完整响应。

成功固定返回与 get_observation.actions_only 相同的当前上下文：scene、screen、available_actions；存在待处理选择时附 selection.type/status。完整原生观察先校验，随后才精简；不返回牌面、顶栏、正文、notes、图片或 transition。没有任何字段需要额外的 summary，也无需增加返回内容参数。

调用不要求已有观察／动作许可；成功会刷新许可，因此关闭后可以直接执行仍合法的动作。动作可用性与关闭对象分别判断：关闭支持的当前页，不额外要求它的入口按钮仍可见或要求玩家可出牌。

工具提示词：

```text
Close the top deck/draw/discard/exhaust browsing page and return actions_only context. Preserves an underlying map; cannot close card selections or other screens.
```

职责及长度合适，成功输出已与定稿一致。建议保持当前参数和提示主体，不为该操作增加 summary 或页面类型筛选。

## 完整返回示例

[20 份示例与来源](2026-11-04-close-card-view-examples/README.md)中，19 份为专项新采样，消耗堆关闭复用相同 Mod／MCP、相同构建 DLL 的既有真实 stdio 返回。没有将合成样例或旧版输出当作新实测。

| 分支 | 完整示例 |
| --- | --- |
| 返回战斗 | [牌组 full](2026-11-04-close-card-view-examples/deck.full.json)、[牌组 default](2026-11-04-close-card-view-examples/deck.default.json)、[抽牌](2026-11-04-close-card-view-examples/draw.full.json)、[弃牌](2026-11-04-close-card-view-examples/discard.full.json)、[消耗](2026-11-04-close-card-view-examples/exhaust.full.json) |
| 返回覆盖层下的实际页面 | [地图](2026-11-04-close-card-view-examples/map.full.json)、[待处理选择的战场视图](2026-11-04-close-card-view-examples/battlefield.full.json)、[事件](2026-11-04-close-card-view-examples/event.full.json) |
| 没有可关闭页面 | [主菜单](2026-11-04-close-card-view-examples/error-main-menu.json)、[战斗](2026-11-04-close-card-view-examples/error-no-view.json)、[重复关闭](2026-11-04-close-card-view-examples/error-repeat.json)、[只有地图](2026-11-04-close-card-view-examples/error-map-only.json)、[选牌](2026-11-04-close-card-view-examples/error-selection.json) |
| 非法参数 | [summary](2026-11-04-close-card-view-examples/error-summary.json)、[未知字段](2026-11-04-close-card-view-examples/error-unknown-field.json) |
| 前置拒绝后的恢复缺口 | [结束回合被观察前置阻挡](2026-11-04-close-card-view-examples/error-next-turn.json)、[选择按钮被阻挡](2026-11-04-close-card-view-examples/error-next-selection.json)、[重新观察后同一选项成功](2026-11-04-close-card-view-examples/continued-selection.full.json) |
| 成功关闭刷新许可 | [直接出牌](2026-11-04-close-card-view-examples/direct-play.full.json)、[直接返回选择](2026-11-04-close-card-view-examples/direct-selection-view.full.json) |

## 场景与生命周期

1. 牌组、抽牌堆、弃牌堆、消耗牌堆：点击当前页原生返回按钮，只关闭这一层，返回下层实际场景和可用工具。不同房间仅改变 scene／available_actions，不产生新的输出结构。
2. 战斗、事件、先古之民、火堆、宝箱、奖励、商店、占卜及建筑师的牌组页：scene 保留所属房间／结算语义。牌堆页只在受支持战斗中存在。
3. 战斗／非战斗地图上叠牌组：关闭后保留地图，screen.view:map，不连带调用 close_map；是否可继续选路仍由原生地图状态决定。
4. 选择切到战场后打开牌组／牌堆：关闭返回选择的战场视图，附 selection.type/status；不能据此跳过选择或执行被 pending selection 禁止的动作。
5. 主菜单、普通房间／战斗但无浏览页、单独地图、直接显示的选牌、卡牌／遗物详情等覆盖、返回按钮隐藏／禁用：前置 illegal_action，不关闭其他界面。连续两次 close 的第二次不是幂等成功。
6. 未知参数／非法 preset：本地 invalid_request，不发送 IPC，不清旧许可。
7. 超时、取消、坏回复：不自动重试、不发送额外关闭，不保留旧许可。超时可能发生在原生返回已经点击之后，必须重新读取实际画面。

关闭逻辑与查看等待需要区分：CardView.Current／CanClose 在同一游戏线程复核后，ForceClick 同步触发 NCapstoneContainer.CloseInternal，将 CurrentCapstoneScreen 设为 null，执行原生 Unpause、ShowOverlays 及 AfterCapstoneClosed，然后才进入第一次 await。后续 SettledObservation 仅采样：连续约 250ms 稳定即返回，最多约 2s 返回最后一份快照；并非等待任意异步流程全部结束。

因此它没有“等待后再去关闭原页面”的窗口，也不会因新页面在采样期间出现而继续关闭它。当前返回所采样的实际上下文，不对后续新界面作同页身份要求；这一行为不同于 inspect_deck／inspect_pile 等必须继续读取原目标页的查看请求。建议保持该关闭语义，并将持续维护文档中的笼统“等待中变页即拒绝”限定为查看请求。

## 当前验证

tests.python.test_mcp_deck、test_deck_inspection、test_response_pipeline 共 **29 项通过**，日志 `.tmp/2026-11-04-close-card-view-review/python.log`。覆盖成功后的直接动作、最小输出／地图／选择上下文、格式校验、超时、取消、未知结果和不自动重试；部分门控使用模拟传输，不代替实际游戏。

**7 组本地探针通过**，来源 `.tmp/2026-11-04-close-card-view-review/probes.json`：非法 preset／额外字段不发 IPC 且保留许可；明确拒绝清旧许可，正向 ui_unchanged 保证尚未登记也不恢复；交互证据与保证矛盾时按 transport_error 处理；没有旧观察时成功关闭仍可授权直接 end_turn；最终省略的 player.hp 若为错误布尔类型也先校验失败，不会被 actions_only 掩盖。探针使用当前 GameTools 与传输替身，非自然游戏实测。

四局 GUI（战斗、火堆选择、选择战场视图、事件）及主菜单，共 **43 次真实 MCP 调用**通过预期断言，报告 `.tmp/2026-11-04-close-card-view-review/report.json`；同一实例的各局正常 reset、进程清理完成。完整 text JSON 与 structuredContent 在每次调用中核对一致。战斗无浏览页时关闭被拒后，end_turn 先被 observation_required 阻挡；重新观察的公开状态与拒绝前完全相同。火堆选牌时的关闭拒绝也导致此前可用的 selection_option 被阻挡，重新观察后同一按钮成功，确认 CLOSE-02。所有真实前置拒绝均只有通用原因，确认 CLOSE-01。

成功关闭牌组、抽牌／弃牌页后仅返回 actions_only；可直接使用已知手牌出牌。地图底下保留，不自动选路或关闭；选择战场视图返回 selection.type/status，并能直接 set_selection_view 返回选择。default/full 实际结果相同。消耗堆成功关闭的既有样本使用相同 DLL，其来源与校验值独立记录，不计入新 43 次调用。

探针脚本首轮把 FakeGame 的覆盖字典误当完整观察而产生 KeyError，修正构造后 7 组全部通过；原日志 probes-first.log 保留。这是验证脚本错误，没有调整生产解码或断言。所有自有游戏进程已关闭。

尚未新建游戏样本：返回火堆／宝箱／奖励／商店／先古之民／占卜／建筑师等其余牌组背景、返回按钮隐藏／禁用、浏览页上覆盖卡牌／遗物详情或模态弹窗、关闭后反馈等待期间再开页面、多人或第三方页面。它们按当前 CardView、原生 CloseInternal 和共享观察规则核对源码，不声称全部自然实测；已有查看工具的关闭样本不等于这些关闭专用边界都已穷举。

本阶段只更新审阅、完整实际示例、核验进度及文档表述；不修改生产工具、版本、正式安装或用户 TODO。

## 待确认的处理范围

建议维持 default/full、现有提示词及成功 actions_only，不增加新参数或 summary。先处理 CLOSE-01–02：关闭可用性与安全原因保持同一个入口，原生在 UiChanged／ForceClick 之前明确拒绝时提供 ui_unchanged:true，MCP 登记该工具以保留已有许可；一旦点击、结果未知、证据矛盾或没有旧许可，继续按原有规则处理，不能用错误码或两个 false 执行事实推断未交互。

关闭在首个 await 前完成、后续只采样且不继续关闭新界面的语义保持原样；持续维护文档已明确这一点，把“等待期间换页则拒绝”限定为查看请求。后续修复应补直接拒绝后合法动作续接、具体原因与无旧许可／交互／超时边界，并复用完整观察先校验和当前最小输出，不扩展为通用关闭全部 UI。
