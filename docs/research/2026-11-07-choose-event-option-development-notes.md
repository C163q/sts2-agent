# choose_event_option 开发核验依据

> 当前状态：定稿已进入实施，当前验证进度见[实施记录](2026-11-07-event-option-recovery-implementation.md)；以下保留审阅基线。用户决策内容见[审阅与建议](2026-11-07-choose-event-option-review.md)。

## 问题依据

| 编号 | 优先级 | 核实依据及状态 |
| --- | --- | --- |
| EVENT-CHOOSE-01 | 中 | GameAdapter.Event 的参数／页面／目标拒绝使用 FileMailbox.Error，没有 action_submitted:false；工具注册未启用 unsubmitted_rejection_unchanged。实际 raw execution 表明拒绝前未交互、未观察到提交，但当前恢复要求显式未提交保证。随后合法动作得到 observation_required。已复现，待修复 |
| EVENT-CHOOSE-02 | 中 | 页面检查合并为通用单人事件提示，Find/Clickable 合并不同目标原因；未提供 public_message，Python 又替换成统一 illegal_action 文案。已复现，待修复 |

两项共同影响拒绝诊断和恢复，没有证据表明这些拒绝实际点击了错误选项。basic 场景中的原始 get_state 与缺失 ID 拒绝后紧随的 get_observation 原始完整 state 逐字段相同，snapshot_id 也相同。

## 基线与来源

- 核对日期 2026-11-07，项目提交 450a041；Mod 0.76.0、MCP 0.78.0、schema 45。
- Linux 游戏 v0.107.1/release59260271，RitsuLib 0.6.10；Godot 4.5.1。
- 游戏程序集相对安装目录为 data_sts2_linuxbsd_x86_64/sts2.dll，SHA-256 为 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 已构建与隔离运行时 Sts2Agent.dll 的 SHA-256 均为 6f78f19889b30fb3c862d442c80c8a13a544017b56ad5f64c00a1a96be50ad04。沿用已有产物，没有重建、更新版本或正式安装。
- 新鲜证据根为 `.tmp/2026-11-07-choose-event-option-review/`；原生源码缓存为 `.tmp/2026-10-31-events/source/` 及 `.tmp/2026-11-03-architecture-refactor/NClickableControl.cs`。

## 当前执行与输出链路

- [GameAdapter.Event](../../src/Sts2Agent/Adapter/GameAdapter.Event.cs)：校验单个 Int32 option_id，然后核对 expected_state，检查当前事件、Exposed、单人、Ready 和 Find/Clickable；在 UiChanged 后 ForceClick。原始参数拒绝也没有未提交保证；MCP 本地参数拒绝不经过该分支。
- [EventInspection](../../src/Sts2Agent/Observation/EventInspection.cs)：排除先古之民、建筑师、第三方事件及非 Default/Combat 布局；静态选项使用 Displayed，不作视口截断，动作另保留 OnScreen。ID 绑定 EventOption 对象，翻页更换对象后生成新 ID；完成事件的原生 PROCEED 由 IsProceed 单独识别，Find 排除它。没有在此审阅中发现旧 ID 点击新选项的情况。
- [AvailableTools](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)：当前已复用 Ready/Clickable 来宣告 choose_event_option；问题不是一套完全独立条件，而是缺少可供动作与列表共同使用的具体原因入口。inspection 的原因入口已经存在，可以提取共用页面部分，另加动作忙碌与选项检查，避免复制完整检查。
- [EventTaskTracker](../../src/Sts2Agent/Actions/EventTaskTracker.cs)：追踪 Chosen、事件开始、进入及 Resume 等 Task；可操作子选牌／奖励边界允许先返回，父任务结束仍由后续动作等待。
- [RecordedActions](../../src/Sts2Agent/Adapter/GameAdapter.Resources.cs) 为事件选择建立资源、物品、遗物计数、药水和战斗记录；[ActionObservation](../../src/Sts2Agent/Adapter/GameAdapter.ActionObservation.cs) 统一等待可操作边界、状态稳定及相关动画。进入战斗由 CombatJournalScope 接管停止原因。
- [NonCombatBoundary](../../src/Sts2Agent/Adapter/GameAdapter.Rewards.cs) 处理选牌、奖励、占卜、确认框、事件就绪和整局失败；事件更换对局返回 interrupted。
- [工具注册](../../src/sts2_mcp/tool_registry.py)与[event_arguments](../../src/sts2_mcp/output/event_details.py)只接受一个非负 Int32 option_id，再由通用层解析 default/full；reader 为 end_turn_details。
- [GameSession](../../src/sts2_mcp/game_session.py)先完整解码再决定许可；[action_result](../../src/sts2_mcp/output/action_output.py)将公开结果精简为 actions_only 上下文加 transition，必要时附选择类型／状态及 notes。因此 full 也不包含完整页面主体；default 仅另执行共用过滤。

## 原生选择语义

NEventOptionButton.OnRelease 拒绝 IsLocked，单人可选择带死亡警告的选项，随后调用 NEventRoom.OptionButtonClicked。ForceClick 自身跳过悬停、焦点及暂停检查，适配器必须先检查实际交互条件。

NEventRoom.OptionButtonClicked 对 IsProceed 直接调用 option.Chosen；普通选项交给 EventSynchronizer.ChooseLocalOption，非共享事件先清除页面按钮。EventSynchronizer 按原生 Index 找当前 CurrentOptions，再执行 Chosen。公开 option_id 先映射到真实按钮，并非直接把公开 ID 当原生数组下标。

EventOption.Chosen 根据 DisableOnChosen/WasChosen 防止禁用选项重复执行；可重复使用的选项由原生显式允许。NEventRoom.SetOptions 在 IsFinished 时创建专门的 PROCEED，普通选项即使内部带 IsProceed 也不必然是该独立前进按钮。

BrainLeech.Rip 先损失生命、再 OfferCustom 卡牌奖励；ShareKnowledge 先等网格选择，再向永久牌组加牌。PotionCourier 两种选项都先 OfferCustom 药水奖励，等待处理后完成事件。因此打开这些页面不应提前生成 card_added/potion_obtained。

DenseVegetation.Rest 治疗并生成 Fight 选项；Fight 进入战斗。新鲜实测使用带 ChoicesParadox 的夹具，确认首回合抽牌及能量事件在 choice_required 前记录。战斗外进入首场战斗不生成 combat_started，与[既有边界定义](../development/end-turn.md#动作完成与画面稳定)一致；player_ready 普通分支本轮仅按源码核对。

## 新鲜验证与样例

- Python：test_events、test_event_confirmation、test_resource_events、test_event_inspection_presets，共 34 项通过，1.366 秒；日志 python.log。预期错误探针的警告保留在日志。
- GUI：audit.py 在一个自有隔离进程中运行 11 个独立测试局，全部符合现状断言，186.040522369 秒；报告记录 70 次实际 MCP 调用、3 次直接原生检查，另有 11 行每局身份记录。创建／重置测试局的运行器内部请求不计入这些检查次数。PID 5966 已退出。
- 11 类场景：非事件战斗、Abyssal Baths 普通翻页／完成、锁定、升级选牌、卡牌奖励、Trial 确认框、占卜、进入战斗的首回合选择、死亡、瓶中精灵复活、满药水槽奖励。
- 直接原生检查覆盖当前快照、过期 token 和多余参数。过期 token 被拒；多余参数被拒，但也缺少明确未提交保证。原始响应保留在 game/ipc/responses，MCP 报告逐次链接对应原始文件。
- 明确拒绝后继续选择、end_turn、select_card、claim_reward、取消确认框及切换占卜工具均因许可清除而返回 observation_required。close_map 是不要求已有许可的页面操作，因此地图覆盖拒绝后仍能关闭；不能把这一成功误写为许可已保留。
- 本地布尔值 ID 在发送前拒绝；随后的 inspect_map 成功。正常事件翻页、完成、选牌、奖励、确认框、占卜、死亡和复活的停止原因均符合预期；没有 timeout。
- [十六份完整公开 JSON](2026-11-07-choose-event-option-examples/README.md)为十五份 full、一份 default；来源、行号、调用参数及 SHA-256 见 manifest。坏 ID、锁定和页面覆盖的错误现状特意保留，不是目标接口。

套件“通过”表示成功复现当前约定的现状，包括两项错误；不表示错误已经修复。未运行全量 Python、C# 检查或构建，没有产品代码变更。没有新增牌组覆盖、真实超时、未知弹窗、多人、第三方事件、任意人工并发切页以及全部原生事件／遗物组合的 GUI 验证。

## 建议的小范围整理

在 EventInspection 中共享页面原因，并添加动作忙碌与单项原因，使 Read.enabled、AvailableTools 和 EventRequest 使用一致条件；Ready 保持独立，避免原因函数与 Ready 相互递归。检查中继续区分静态显示、悬停与可点击性，不能将视口限制重新加回静态读取。

执行前拒绝使用现有 RejectedBeforeSubmission，并在注册启用 unsubmitted_rejection_unchanged；保持 stale_state、点击后的异常与未知结果不续接许可。原始请求参数错误也应使用明确未交互的拒绝；无需新建另一套许可机制。

上述建议已纳入输出定稿；实现与验收另见实施记录，TODO清单保持原有范围。
