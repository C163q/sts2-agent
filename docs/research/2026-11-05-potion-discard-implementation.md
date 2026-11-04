# 丢弃药水排队与结果：实施及验证

> 当前状态：实现、验证与独立审查完成，共 3 项，已完成 2 项；35 类组合场景、673 项 Python、124 项 C# 检查通过，两项重要审查发现已修复，保留一项低优先级清理事项。正在完成合入收尾，暂无阻塞。已确认要求见[审阅契约](2026-11-05-discard-potion-review.md#已确认契约)，执行进度见[计划](../superpowers/plans/2026-11-05-potion-discard-queue.md)。

本文保存开发证据；当前接口规则维护在[药水动作](../development/potion-actions.md)。

## 实现与信息边界

- PotionRules 共用基础前提，分别提供使用与丢弃阶段。丢弃允许已暴露、稳定、受支持且不是预览／view_cards 的选择；战斗中还要求本地玩家处于 Play 阶段。其他卡牌页、战斗地图、隐藏选择、战场窥视、未知选择及普通忙碌状态仍拒绝。没有通过模型删除替代原生动作。
- PotionInspection.Pending 读取同版本 NPotionHolder._disabledUntilPotionRemoved，作为跨请求防重复依据。原生处理移除、取消和对局清理；没有新增第二套常驻排队列表。RemovalReason 由操作、查询与可用工具复用，已排队槽位也不能再次使用。
- 单次请求的 PotionDiscardProgress 只记录确切提交、公开丢弃、取消和不确定性。构造好的 DiscardPotionGameAction 以对象身份匹配 ActionEnqueued，避免绑定无关同玩家动作；动作与 Journal 的监听在请求结束时释放，队列更换时的解绑源遗留见下文。选择后的实际事件由新的 Journal 自然捕获。
- PotionJournal.DiscardObserved 仅在原槽位身份与展示允许公开记录、且记录未被截断时通知本次请求。请求结果的槽位与名称在提交前从已显示信息保存；不在后续未知上下文重新查隐藏身份。
- 可见移除还须发生在确切请求动作已经开始、State 为 Executing 时，外部入队回调先移除同一对象只进入事件，不能确认本次请求成功。提交动作的 Exception 非空时停止于 interrupted，即使已经公开移除，也不续接下一次动作。
- ResponseBuilder 只给 discard_potion 附加顶层 potion_discard。Python 专用读取验证字段、原请求槽位、状态与实际事件，拒绝 discarded 缺少公开移除证据或 queued 没有完整可见选择的响应。内部字段继续过滤。
- choice_required 的共用回执过滤保留原生确实列出的 discard_potion；GameSession 允许 queued 继续选择。unknown／not_discarded 不续接许可；明确未提交拒绝仍沿用安全恢复。后续 select_card／selection_option 只返回实际 potion_discarded 事件，没有新的顶层结果。
- inspect_targets 在允许丢弃的选择中可读取药水，分别报告不可使用的阶段原因和 discardable；不把“允许丢弃”改成“允许饮用”。

queued 表示请求已接受且仍在等待当前选择，不保证以后一定执行。立即移除时即使选择尚未结束，也返回 discarded 与 choice_required；战斗外火堆实测覆盖了此分支。

## 基线与原生依据

- 修改基线 210b2b8；Mod 0.65.0、MCP 0.67.0，观察 schema 40 不变。当前兼容表唯一维护在 [README](../../README.md#当前版本与前提)。
- 游戏 Linux v0.107.1、release build 59260271。重新核对安装目录相对路径 data_sts2_linuxbsd_x86_64/sts2.dll，SHA-256：d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 原生按钮与队列证据继承[开发审阅](2026-11-05-discard-potion-development-notes.md#基线与原生证据)。补充 .tmp/2026-11-05-potion-discard-queue/GameAction.cs：Execute 的 finally 可能在 Cancel 后写回 Finished，所以保留取消通知，不能只看最终枚举。
- RitsuLib 0.6.10，本地源码 .tmp/ritsulib-end-turn-review，提交 772f280964f2efc7c7e2f29fc59844e68616dd57。没有新增对社区库的调用或修改依赖。
- 原始日志、完整响应与每次构建证据保存在 .tmp/2026-11-05-potion-discard-queue/；不覆盖前一轮审阅的 62 份 JSON 或前台探查。

## 已执行的验证

1. Python 新增 8 项请求结果与许可测试先失败，再通过。覆盖严格形状、原槽位、公开移除事件、选择续接、default/full、后续回执不附带顶层结果、unknown 和取消的许可，以及提交后坏响应。
2. C# 状态与 ResponseBuilder 检查先因缺少实现失败，再通过；总计 124 项。覆盖 Cancel 后 Finished、隐藏移除、失败、上下文丢失、公开移除后其他钩子失败，以及不伪造事件。
3. 完整 Python 在契约接入后首先暴露旧模拟响应缺少结果的差异；只调整调用包装，冻结的 tests/data/tool_contracts JSON 保持原样。旧通用动作没有丢弃见证，明确附 unknown 并不续接许可，不能凭旧通用事件假造丢弃成功。
4. 旧 DLL 7f04d0ee3ba6588e69e250bdeb8445f1f48f44f48470a84015d53dfad6582875 的 gui-red 复现 choose_one 中缺少 discard_potion。新原生接入的发现牌、手牌、牌堆和火堆四例随后通过。
5. 第一版取消夹具直接在 ActionEnqueued 回调中 Cancel，原生 GetReadyAction 移除它后没有完成 IsEmpty 的等待对象，导致测试超时。该条件不代表普通原生执行取消；gui-remaining 保留失败。改为仅测试的 ExecuteAction 前缀取消并返回完成任务，使原生 finally／PopAction 正常清理，再验证取消最终变 Finished 的实际路径。没有修改生产队列来迁就夹具。
6. 首轮完整 Python 671 项通过（python-final.log，53.663 秒）；构建无警告／错误，C# 124 项通过。gui-final 组合 33/33 通过（724.481 秒），包含 14 类新增场景、15 类既有丢弃及 4 类用药回归。该轮 DLL 为 a0c8ea33e1f97447d927f6f3d223614c70da580119a3f998fd5521abf364e6d1，另保留 before-review/Sts2Agent.dll；不将它当作审查修复后的构建。
7. 审查两项重要发现各自先复现：gui-review-fault-red 返回错误的 player_ready／complete:true；gui-review-foreign-red 将外部先移除误报为本次 discarded。修复异常停止及确切动作执行见证后，在相同场景得到 interrupted／complete:false 和 unknown，实际已见事件均保留。
8. 最终完整 Python 673 项通过（python-review-final.log，59.734 秒），C# 124 项通过。35 个不同配置分成两个独立游戏进程的 17／18 例，全部通过，包含 16 类新增边界、15 类丢弃、4 类用药。最终 DLL 为 2cc9d5d3ecee7c3dc5298dcf45c6dc2b1d3eb7edf526a5b12ee82239bb9af385；新样例全部来自该构建，之后不重建替换证据。

## GUI 场景与观察结论

新专项包括 choose_one、hand、pile、noncombat_upgrade、immediate、cancel、hidden、multiple、skip、pending_reset、after_reset、card_choice、card_pile、hand_upgrade。卡牌触发的选择分别使用发现、头槌和武装；既有药水触发的选择覆盖技能药水、赌徒佳酿和液态记忆。

- 选择中的请求返回 queued，重复请求具体拒绝且不丢失选择许可；可以直接选择、确认或跳过。不同槽位可连续排队，实际移除事件保持原生顺序。
- 原生取消返回 not_discarded，药水仍在；隐藏移除返回 unknown，不泄漏丢弃事件，恢复显示后不回放。两者都不能直接继续玩法。
- 火堆选择未占用原生动作队列时可立即丢弃：返回 discarded、potion_discarded 和仍待处理的 choice_required，之后选牌不重复报告旧事件。
- 带着未完成选择及排队丢弃清理对局后，下一局的同名药水和槽位可正常使用，没有跨局待执行状态或旧事件。

审查补充 fault、foreign 两类边界。实际 stdio 的 [126 份完整返回](2026-11-05-potion-discard-queue-examples/README.md)及[来源清单](2026-11-05-potion-discard-queue-examples/manifest.json)已导出，逐项保留请求、原始记录位置和构建哈希。最终记录包含 271 次 MCP 调用；不把重复执行的首轮验证累计为新场景。

## 独立审查与遗留

只进行一次只读独立审查，范围为 210b2b8..49b2de0，执行代理 review_potion_discard_queue。Critical 0、Important 2、Minor 1。两项 Important 的修复在同一轮完成，每项先取得上述 RED，再完成相同场景及完整回归的 GREEN，不重复派发审查。原始审查摘要保存在任务目录 review-findings.md。

**低优先级保留事项：** 订阅与 finally 解绑各自读取当前 ActionQueueSet；若请求尚未结束就切换新局，队列可能已经更换，旧队列上的 ActionEnqueued 监听可能没有解绑。旧队列整体不可达时可由 GC 回收；普通“请求返回后再清理新开局”的已测流程不受影响。后续清理范围是捕获订阅时队列并始终向该实例解绑。这项没有混入两项重要修复，也没有追加到用户 TODO。

审查不另行运行测试，验证以任务的原始日志和哈希为准；真实多人、第三方药水、自然超时和全部未知选择的动态表现仍在未验证范围内，保持原有保守处理，没有新增支持承诺。

## 实现取舍与未验证范围

沿用现有工作目录的临时分支和已准备的独立运行时，最终自动合入 main 并清理分支；没有另外建立 worktree。初始工作区干净，相关测试始终使用各自的新存档和 IPC。

未扩展到战场窥视、卡牌预览／结果页、未支持选择、普通卡牌浏览覆盖或敌人回合。取消、隐藏、外部移除与丢弃后失败均为双重测试门控下注入的条件；没有声称自然游玩已出现对应故障。真实多人、第三方目标类型、RitsuLib 缺失、自然超时及所有插件异步恢复组合未新增游戏内实测；异常注入只验证所记录的一种原生丢弃后失败，不代表第三方兼容保证。
