# 丢弃药水排队实施计划

> 当前状态：实施中，共 3 项，已完成 2 项；原生接入与 33 类隔离场景、671 项 Python、124 项 C# 检查通过，正在处理文档、完整样例及最终审查。暂无阻塞。
>
> 执行方式：superpowers:executing-plans，当前会话逐项实现，最后进行一次独立代码审查；用户已确认设计和执行，不重复请求批准。

**目标：** 支持原生选牌边界的丢弃排队，区分请求结果与实际事件，并保持错误恢复与信息边界。

**架构：** 使用／丢弃共用基础阶段条件，单独判断选择和忙碌队列；复用原生槽位等待标记防重复，不额外维护跨请求队列。单次请求使用纯状态记录与可见移除见证生成 potion_discard；Python 单独验证此结果，再通过共用动作投影与许可逻辑输出。

**技术：** C#/.NET 9、Godot 游戏线程、已核对的原生 DiscardPotionGameAction；Python 真实 stdio MCP 与 unittest。

**规格：** [已确认契约](../../research/2026-11-05-discard-potion-review.md#已确认契约)，源码与前台原生证据见[开发核验](../../research/2026-11-05-discard-potion-development-notes.md)。

## 全局约束

- 保留 potion_slot 与 preset:default/full，无 summary；只在 discard_potion 自身成功回执提供顶层 potion_discard。
- queued 停于 choice_required，不提前生成事件；discarded 要有本次请求的公开移除证据；not_discarded 表示确认未丢弃，unknown 不续接玩法许可。
- 复用原生排队和移除流程；调用时重查归属、原槽位、展示和交互状态。禁止用模型删除代替正常操作。
- 默认支持当前稳定且暴露的已知选择类型；view_cards、未知、遮盖、预览不可操作、切换中页面，以及牌组／牌堆／战斗地图和非玩家阶段保持拒绝，实际选择变体由源码和实测核对。
- 不更改 use_potion 的阶段、目标和自动药水规则；不安装正式 Mod，不推送远端；验证后合入 main 并清理临时分支。
- 当前分支从 210b2b8 开始；复用现有工作目录与独立测试运行时。当前游戏与依赖基线唯一来源 README；本轮仍核对游戏程序集哈希。

## 审查重点

1. 原生取消后 GameAction 最终可能变 Finished，不能丢失取消见证。
2. 隐藏移除、事件截断、异常和超时不能误报 discarded 或恢复动作许可。
3. 选牌只是改变已选项时仍可能未执行丢弃，多次操作不能重复提交原槽位。
4. 同名替换、重新开局和原生外部排队不能让旧请求身份或等待状态污染下一次调用。
5. 允许 discard_potion 的选择回执必须同步 available_actions 和许可；use_potion、隐藏视图和未知选择不得因此放开。

## 任务 1：请求结果与共用许可契约

接口：PotionDiscardProgress 暴露 Submit/ObserveDiscard/Cancel/Finish/Abandon 和 Status；Python discard_potion_details(state, arguments) 输出已验证的 potion_discard；potion_discard_requires_observation(payload) 用于许可判断。

- [x] 编写 C# 状态检查和 Python 回执测试，覆盖 queued、discarded、取消、异常、无可见证据、严格字段校验、slot 对照、default/full、后续选择不附带该字段、unknown 不续接，以及选择中的可用丢弃。
- [x] 运行失败测试，保留 RED 日志；仅 mock 游戏 I/O，不 mock 投影／许可实现。
- [x] 在 Actions/PotionDiscardProgress.cs 和 output/potion_discard_output.py 实现单次进度与专用读取；在 tool_registry.py、action_output.py、transition_details.py、game_session.py 接入。ResponseBuilder.WithTransition 增加可选 potionDiscard 参数。
- [x] 运行完整 Python 和 C# 检查并提交独立契约变更；暂不改正式运行时。

## 任务 2：原生接入、阶段与防重复

接口：PotionStageUnavailableReason 保留原使用判断；DiscardPotionStageUnavailableReason 提供丢弃判断；PotionInspection.Pending(holder) 读取已核对的原生等待标记；PotionJournal.DiscardObserved 只在公开记录成功时通知单次请求。

- [x] 新增 GUI 断言，先在旧 DLL 复现 choose_one 丢弃应 queued 却被拒绝；保存独立 RED 目录。
- [x] 修改 GameAdapter.Potions/PotionRules/AvailableTools，复用共同基础检查，允许稳定暴露的受支持选择；绑定确切 DiscardPotionGameAction 对象，防止匹配无关同玩家动作。只靠原生槽位标记跨请求防重复，监听器随本次请求释放。
- [x] 根据 PotionDiscardProgress、公开移除和最终状态生成结果；选择不由工具自动完成，未知结果不提供继续操作。原生日志和后续事件沿用共用 Journal。
- [x] 隔离实测 choose_one、手牌／牌堆选择、战斗外选择、立即丢弃、多个槽位、重复提交、skip／confirm、取消／隐藏见证、同名替换及局间清理；复用已有药水场景，新增必要的双重门控夹具。
- [x] 构建、运行 C#、完整 Python 和必要的用药／丢弃回归，采用新的证据目录，不覆盖审阅基线；提交已验证原生实现。

## 任务 3：文档、完整样例与交付

- [ ] 更新 README 版本、potion-actions/mcp/card-selection/gui-testing 当前契约；保持审阅基线 JSON 原样，保存修复后完整样例和原始来源。
- [ ] 按最终验证范围更新审阅清单与实施记录，核对链接、JSON、样例哈希及测试进程退出，不向用户 TODO 添加事项。
- [ ] 按执行技能进行一次独立最终审查；重要问题以 RED→GREEN 与完整回归修复，不进行重复审查。
- [ ] 提交、合入 main、清理临时分支；交付说明验证结果、未验证范围及必要的实现取舍。
