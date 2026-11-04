# 结束回合与可见牌堆移动实施记录

> 当前状态：实现、验证及独立审查完成，end_turn 已核销。TURN-01–03、MOVE-01 和 default 的 autoplay:false 精简已交付，手斧来源变体的审查问题已修复；最终十五局全部通过。仅遗留一项低优先级生成预览牌名缓存限制，详见下文。暂无阻塞。

## 范围与基线

依据[实施计划](../superpowers/plans/2026-11-04-turn-transitions.md)、[结束回合审阅](2026-11-04-end-turn-review.md)及[头槌核验](2026-11-04-headbutt-transition-review.md)，代码基线 bc62b0d。用户确认移动事件不提供 position：事件表达实际可感知方向，不把牌面或选择提示中的位置文字升级为此次动画公开的实际牌序。

核对游戏 Linux v0.107.1，release build 59260271；RitsuLib 0.6.10 兼容运行时。目标程序集相对路径 data_sts2_linuxbsd_x86_64/sts2.dll 的 SHA-256 为 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。最终版本统一见 [README](../../README.md#当前版本与前提)：Mod 0.62.0、MCP 0.64.0，基础观察 schema 保持 40；没有安装正式 Mod。

从同版本 PCK 的 localization/zhs/cards.json 核对：明耀打击为 ShiningStrike，无休手斧为 ThrummingHatchet，刀刃陷阱为 KnifeTrap；没有按英语名称猜卡。Headbutt、三张指定卡、CardPileCmd.Add／Shuffle、CardSelectCmd、NCard、NCardFlyVfx／NCardFlyShuffleVfx 的本地证据位于 `.tmp/2026-11-04-turn-transitions/source/` 及本计划明确引用的头槌证据目录，不纳入 Git。

## 实现

- [GameAdapter.EndTurn](../../src/Sts2Agent/Adapter/GameAdapter.EndTurn.cs) 统一结束回合可用性、安全原因与提交；available_actions 复用同一判断。覆盖、选牌、尚未就绪、不可见／禁用按钮等前置拒绝明确公开原因及未提交保证，MCP 沿用既有保留旧许可规则，不修改普通战斗就绪入口的含义。
- [共用动作解码](../../src/sts2_mcp/output/transition_details.py) 从当前完整校验快照保留合法且无需许可的查看工具，胜负、不完整等边界仍不续接游戏动作许可。支持的可见选择继续允许对应选择动作。
- [CardMovementJournal](../../src/Sts2Agent/Events/CardMovementJournal.cs) 独立配对移出／进入，等待真实手牌、出牌区或飞牌证据，再发布 card_moved。字段固定为 sequence/type/card.id/name/from_pile/to_pile，没有位置、牌序或随机结果。生成牌仍使用 card_added，不为既有抽牌／弃置／消耗及手牌入出牌区的同次事实重复记录。
- [CombatCardPiles](../../src/Sts2Agent/Observation/CombatCardPiles.cs) 供生成与移动共用可见端点规则，单张来源的 HUD 计数复用 CombatResources；公开牌名由同一战斗内已展示的手牌、候选及期间牌面记忆提供，不从隐藏模型构造名称。跨回执及战斗交接依照现有日志作用域重新接入／释放。
- [default 过滤](../../src/sts2_mcp/output/null_fields.py) 仅省略 card_played.autoplay:false；实际字段名为 autoplay。full 仍保留 false，自动出牌 true、其他 false 及事件 null 保留，完整解码先于精简。

匿名牌背只在有明确选择、已识别出发牌面，或本次调用开始时 UI 已显示唯一来源时关联；源堆在过程中变成最后一张不能凭内部移出顺序认定身份。洗牌用已核对的原生异步上下文抑制逐牌记录，隐藏／覆盖和同堆重排不回放。没有视觉的入堆也不能偷用之后另一张牌的动画作证。

现行契约以[结束回合与期间事件](../development/end-turn.md)及 [MCP 输出与许可](../development/mcp.md)为准；本记录保存实现依据与验证，不另立第二份接口定义。

## 游戏结果

| 场景 | 已核实行为 |
| --- | --- |
| 头槌空弃牌 | 无回收移动，不虚构事件；普通出牌返回弃牌的可见方向可记录 |
| 头槌单弃牌 | play_card 返回一次 discard→draw |
| 头槌多弃牌 | play_card 先停在 choice_required；真正恢复流程的 select_card 返回一次 discard→draw，误用 end_turn 被明确拒绝后可直接合法选择 |
| 明耀打击 | play→draw，与伤害／星星变化并存，没有 position |
| 无休手斧 | 先 play→discard；后续 end_turn 中 discard→hand，或经头槌放回后 draw→hand。只有真正的原生抽牌才去重，回手不误报成抽牌，不泄露随后洗牌逐牌顺序 |
| 刀刃陷阱 | 自动小刀的 autoplay:true 和 Knife Trap 来源保留，显示的 exhaust→play 被记录；原生跳过牌堆视觉的后续小刀不虚构移动，消耗事件各一次 |
| 战胜／战败 | available_actions 保留可直接用的遗物查看；再次 end_turn 仍需许可，详情可以直接读取 |
| 原生负例 | 无动画、隐藏计数、同堆重排、整页隐藏后恢复、匿名多牌及批量最后一张、洗牌、释放后续通知等边界均按所给证据约束 |

最终构建的 [25 份完整 JSON 与来源](2026-11-04-turn-transitions-examples/README.md)已归档，其中头槌选牌、手斧两种回手来源、刀刃陷阱 default／普通手动出牌 full、具体拒绝和直接续接均为实际 MCP 返回。数据与 text JSON 逐次比对，未补字段或删事件。

## 最终验证

证据根目录为 `.tmp/2026-11-04-turn-transitions/`。最终构建与隔离运行时 DLL 的 SHA-256 均为 `e120f0945cc392a37d6e9cd937f5cfb93e02a93ac2ab47a5ab68bacf627b058a`。

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 目标程序集构建 | 零警告、零错误 | build-reviewed.log |
| 全量 Python | 636 项通过 | python-delivery.log |
| C# 独立检查 | 91 项通过 | csharp-delivery.log |
| 最终 GUI | 15 局通过，约 375.33 秒 | gui-delivery/report.json |
| 真实 MCP | 88 次调用；预期拒绝也计入，text 与 structuredContent 一致 | gui-delivery 各案例 verify/evidence.json |
| 新原生检查 | 结束回合按钮 4 项、移动及真正抽牌去重 13 项通过 | gui-delivery/checks/verify/evidence.json |
| 原生成牌回归 | 31 项原生检查通过 | gui-delivery/generation_native_checks/verify/evidence.json |
| 旧行为交叉回归 | Anger 生成去向、原生成牌检查、结束回合中的战斗交接通过 | gui-delivery 的最后三例 |

最终套件包含头槌三分支、明耀打击、手斧从弃牌／抽牌堆回手、刀刃陷阱、胜负、原生边界、牌组／地图覆盖拒绝和非战斗事件误结束回合后的直接合法操作。不是将多次旧构建通过拼成一次最终通过；上述 15 局使用相同最终 DLL 和 MCP。

来源核对脚本校验样本与原始返回逐字段一致、校验值、链接、版本及各检查结果；结果见 verification.json。八个测试进程均已关闭：176992、178275、180330、181761、182568、184128、192678、193324。正式游戏及其存档未参与测试，未安装 Mod、推送或合并。

## 验证过程与限制

新增六项 Python 回归先观察到预期失败，再实现为通过；旧构建的头槌 GUI 也按预期失败。首轮全量 Python 的唯一失败来自历史测试仍假定 end_turn 不支持明确未提交保证，已将反例更新为无保证 end_turn 和未支持的 use_potion，保留保守恢复边界。

匿名批量负例额外复现了一个实现问题：最后移出的未知牌被当作单张来源。修复后只采信调用开始时的公开唯一计数，并使期间入堆／移出使该证据失效；保留 RED 证据 gui-anonymous-red。无动画后紧接另牌飞行的回归首次即通过：原生 skipVisuals 的移出采用 silent 通知，没有留下可被误配的移动候选；未为未复现的问题增加额外钩子，报告路径 gui-silent-red 的实际状态为 passed。

编译中发现并修正 CardPile 无 Owner 成员及测试检查遗漏命名空间导入两处实现错误，原失败日志保留；最终构建零警告、零错误。旧头槌回归 gui-red、匿名批量 gui-anonymous-red 和审查组合 gui-review-red 的失败均保留，不用后续成功覆盖失败现场。

## 独立审查

按 Codex 模型约定使用 gpt-6.1-sol／high、全新上下文完成只读审查。未发现 Critical，发现一项 Important 和一项 Minor。

- Important，已修复：最初按 draw→hand 一律去重，会漏掉手斧从抽牌堆直接回手。已用“打出手斧→头槌放回→结束回合”真实组合复现 RED，记录 gui-review-red；修复为保存原生 Draw 的异步结果，并依据本次移动之后的实际 CardDrawn 历史决定去重。组合 GUI 和原生“直接回手有移动／真正 Draw 只保留 card_drawn”均在最终十五局 GREEN，不派第二轮重复审查。
- Minor，延期：生成牌若仅通过预览公开后进入非手牌区域，CardAdditionJournal 的记忆回调尚未同步到新战斗级牌名缓存；跨回执后的移动可能保留同一 card_id 但 name:null。不会把隐藏身份补成已知；不影响四张指定卡的已验证路径。问题保存在本记录，未擅自新增用户 TODO。

审查员的同步投影专项两项及 diff 检查通过；异步专项在沙箱内挂起，已中断清理，不计作通过。审查未执行构建或游戏，也未判断仍在生成的样本／哈希；这些由本实施的最终构建、全量测试、真实 GUI 及来源校验补齐，不据审查意见替代实测。全部卡牌组合、多人及第三方 Mod 仍在已声明的未验证范围，不将其描述为已支持新保证。

未覆盖：所有角色／遗物组合、第三方直接改写字段、任意无视觉回堆、模态覆盖期间的外部操控及所有异常中断时机。原生负例是隔离测试检查，不冒充自然全流程；完整事件覆盖不由 complete:true 保证。正式 Mod 未安装。
