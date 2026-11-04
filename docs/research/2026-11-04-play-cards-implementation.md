# 连续出牌实施与验证

> 当前状态：实现与验证完成。play_card／play_cards 已完成约定范围，PLAY-01–03 及两项重要边界修复均通过验证；核销清单更新为 44 项中完成 12 项。保留一项集成验证缺口，范围见文末。未安装正式 Mod，无阻塞。

## 交付内容

新增 `play_cards(cards, preset?)`，按数组顺序调用真正的 TryManualPlay 连续入队，允许上一张尚未结算；不自行执行效果。参数、初始手牌及目标引用整批预校验；费用和当前目标合法性逐项检查。动态拒绝继续后项，选择、终态或上下文变化停止新增提交；已经入队的牌由游戏决定暂停、取消或继续，不补发未提交项。

现行字段及行为由[出牌指南](../development/card-play.md)维护；全部实际请求与 56 份完整返回见[JSON 样本](2026-11-04-play-cards-examples/README.md)，[规格](2026-11-04-play-cards-design.md)与[计划](../superpowers/plans/2026-11-04-play-cards.md)保留实施依据。

批量结果 `card_plays` 保留原数组顺序及控制关联 batch_id，区分 not_submitted、queued、resolving、played、not_played、unknown。需要选择时及时返回，后续选牌／确认回执携带同一批次的更新；完成后释放订阅，新局不会回放旧批次。单张成功格式保持不变。

| 问题 | 最终行为与验证 |
| --- | --- |
| PLAY-01 | 出牌与目标查询共用阶段原因，明确选择、卡牌浏览、地图、过渡、无对局／战斗及未就绪状态。旧运行时的笼统拒绝已在 GUI RED 复现，新诊断通过真实页面验证。 |
| PLAY-02 | 英语作用域中复用原生拒绝气泡，保留 UI 的公开阻止来源；Normality 的查询和出牌拒绝均包含该名称。原生不可打出关键词／卡牌条件共用 UNPLAYABLE 的情况保持原样。 |
| PLAY-03 | 目标说明支持已有观察中的对象 ID；目标要求不清楚时再用 inspect_targets，不新增读取前置。批量实测直接使用观察中的敌人 ID。 |

## 小范围重构

- [CardPlayOptions](../../src/Sts2Agent/Actions/CardPlayOptions.cs) 只解析严格输入；[CardPlayProgress](../../src/Sts2Agent/Actions/CardPlayProgress.cs) 独立记录提交、开始、实际出牌、取消及结束，不把 Finished 当作成功。
- [CardPlayRules](../../src/Sts2Agent/Adapter/GameAdapter.CardPlayRules.cs) 共用 UI 阶段、引用及按项规则；[CardPlayFailureText](../../src/Sts2Agent/Localization/CardPlayFailureText.cs) 只读取原生公开气泡。
- [ManualPlayBatch](../../src/Sts2Agent/Actions/ManualPlayBatch.cs) 绑定本次原生动作与生命周期，单张局部使用，批量可跨选择保留；不持有未来补发计划。
- [CardPlay](../../src/Sts2Agent/Adapter/GameAdapter.CardPlay.cs) 编排校验、提交和共用 ActionObservation；[Resources](../../src/Sts2Agent/Adapter/GameAdapter.Resources.cs) 在动作回执附加批次更新及清理。
- Python 的结构校验在 card_batch_output，输入／请求绑定在 card_batch_details；共用 transition 解码和 action 投影保留批次结果，依赖图保持无环。没有另建卡牌结算器或通用工具批处理。

## 审查与重要修复

独立只读审查使用 gpt-6.1-sol／high，无实现分派、无复审；审查了相对 ecd071e 的当前差异和新增文件。结果为无 Critical、1 项 Important、1 项 Minor。实施者另在旧单张契约对照中发现一项 Important，均在同一修复阶段完成。

1. **unknown 选择回执可能重新发放许可**：直接解码及会话许可测试先 RED，修复后所有边界的 unknown 均保留结果／合法查看工具但不直接续接玩法许可；queued/resolving 的受支持选择仍可正常继续。已结束但未见过程的 unknown 与仍排队不同，不将前者误报成连接故障；它仍不会发放许可。
2. **原生最终拒绝被包装成单张成功**：一次性 TryManualPlay(false) 注入复现成功空回执的 RED。恢复单张明确拒绝；UI／提交事实在入队确认时记录，原生 false 分支无入队／UI 变化，保留已有许可。实测原始快照不变，随后直接批量调用无需额外读取；批量被拒项为 not_submitted，后项继续。

实际取消仍保留旧单张 action_canceled 策略；它与明确未提交的错误不同，不混入上述保证。坏响应、过期状态、异常或未知结果不以“没有收到”推断未执行。

## 验证结果

基线为 ecd071e。交付 Mod 0.63.0、MCP 0.65.0，观察 schema 40；默认 43 个玩法工具，启用截图后 44 个。游戏 Linux v0.107.1／build 59260271；RitsuLib 0.6.10 的对应兼容运行时，源码提交 772f280964f2efc7c7e2f29fc59844e68616dd57。游戏程序集 data_sts2_linuxbsd_x86_64/sts2.dll 摘要仍为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。

| 检查 | 结果 |
| --- | --- |
| 最终编译 | 0 警告／0 错误，6.91 秒 |
| 完整 Python | 653 项通过，39.33 秒；包含 schema、CLI、绑定、错误／未知许可及旧工具回归 |
| 独立 C# | 114 项通过；严格解析、取消后 Finished、未发生出牌、隐藏和异常的纯状态模型等 |
| GUI 主套件 | 17 局通过，457.67 秒 |
| GUI 补充回归 | 14 局通过，314.72 秒；default、单项、自动出牌隔离、跨局清理、原单张接口和门控 |
| GUI 最终修复回归 | 9 局通过，229.50 秒；原生最终拒绝、连续／部分、选择、死亡及单张取消 |
| 不同场景 | 上述共 40 次成功执行，覆盖 32 项不同场景／门控；所选证据共 198 次真实 MCP 调用 |
| 测试入口门控 | testMode 关闭与 suite 关闭时各 69 个测试入口被拒绝；测试注入不进入公开目录 |
| 实际 JSON | 56 份 structuredContent 与文本 JSON 一致，参数／来源下标／DLL 摘要独立记录 |

最终测试 DLL 与隔离运行时摘要均为 `2d66c65c5e84e514a19480c74b7df33f6316670c588652697d8456255ca37dba`。最终修复前主／补充套件使用 `581abcac30e08a85b9c5facd98bc73eb4cc042e0024eb7e217608bc5da005c8d`；变更影响的提交与拒绝分支由最后 9 局补测，每份样本记录实际构建，不声称全部来自同一次执行。

隔离日志和原始证据保存在 `.tmp/2026-11-04-play-cards-implementation/`。三个预期失败目录分别保留旧笼统诊断、旧 Mod 不支持批量以及原生最终拒绝的 RED；未知许可与兼容投影等 RED→GREEN 日志亦保留。首轮完整 Python 的缺登记及循环依赖未通过删除架构检查解决，历史 pre-refactor JSON 未被重写。

## 取舍与未验证范围

- 保留现有功能分支和提交历史；action_canceled 的直接续接仍未扩展，代价是这类单张已取消结果后仍需一次读取。
- 冻结历史基线，新增工具以独立契约和全局登记覆盖；拆分输出结构模块以保持 DAG，无额外依赖。
- **审查 Minor 留待后续**：ManualPlayBatch 层的隐藏出牌／异常、同一手动牌多次效果、timeout 后继续追踪尚无专门集成场景。纯状态模型、真实自动出牌隔离和选择续接不代替这些组合，未据此宣称完整生命周期覆盖。
- RitsuLib CardPlaying 非关键补丁缺失／降级未注入验证；当前固定程序集和运行时已验证真实生命周期，不将缺乏证据的降级当作已发生问题，也不承诺其结果保证。多人、第三方目标和全部卡牌／遗物组合仍未验证。
- 未新增用户 TODO；只同步既有错误恢复／提示两项的覆盖进度。截图文档的旧数量改为引用统一工具范围，避免再维护一份数量。

所有图形实例由套件管理独立 IPC、存档和清理；没有安装正式 Mod 或修改正式存档。
