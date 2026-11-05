# 选牌拒绝与状态反馈实施计划

> 当前状态：实施中，共 3 项，已完成 2 项；前置拒绝和选中事件已验证，正在完成文档、独立审查与合入。暂无阻塞。
>
> 执行约定：使用 superpowers:executing-plans 逐项实施，按 superpowers:test-driven-development 验证；用户已确认设计并授权实施，无须重复确认执行方式。

**目标：** 修复 select_card 的明确未交互拒绝和公开原因，并在原生接受选中／取消时返回对应事件。

**架构：** 候选前置诊断独立于分派；原生持牌器信号仍由 SelectionActions 发出。独立 SelectionInputJournal 围绕真实输入记录同一选择实例的变化，在发送输入前预留事件顺序，以原生选中集合及已完成选择任务证明接受；不以最终页面的差集推断提交。

**技术栈：** C# / Godot / 游戏原生 UI、Python stdio MCP、现有有界事件缓冲与隔离 GUI 套件。

**规格：** [select_card 审阅及已确认事件设计](../../research/2026-11-05-select-card-review.md#设计定稿)。原始证据与 API 核对见[开发记录](../../research/2026-11-05-select-card-development-notes.md)。

## 全局约束

- 沿用 card_id、default/full 和紧凑回执，不新增 summary、批量选择或 selected_ids。
- 新事件严格为 sequence/type/card；type 为 card_selected 或 card_deselected，card 仅 id/name，名称不可读时保留 null；未知／锁定牌不补真实身份，保留同次快照的公开占位文字，default 不省略事件中的 null。
- 先取消旧牌、再选中新牌；自动提交仍记录最后选中，不把预览／提交／页面清理算作取消。原生未接受或拒绝不伪造事件。
- 事件记录使用输入前已公开的牌名及稳定 ID，不读取随机结果；确认预览返回造成的取消复用同一入口，卡包整包操作不冒充单张选中。
- 仅在快照有效且尚未定位／点击时保证 UI 未变；状态过期、交互后失败、异常或未知结果不得保留许可。
- 持续文档中文，代码注释英文；版本唯一基线在 README。完成后自行提交、合入 main、删除临时分支；不正式安装或推送。

## 审查重点

- 自动提交导致原页面移除，或下一次选择复用同一组牌：须依据原选择任务确认接受，不把新页面集合当旧页面变化。
- 手牌替换嵌套取消旧牌：恰好一次取消和一次选中，先后顺序正确。
- 预览克隆和未知身份：只引用原候选 ID，不泄露克隆或隐藏名称。
- 原生无效点击和滚动竞争：不生成选中事件；只有明确前置拒绝保留旧许可。
- 事件上限、异常及生命周期：沿用有界缓冲，不跨请求、跨局重放，不阻塞游戏线程。

## 任务 1：明确前置拒绝与具体原因

文件：新建 Actions/SelectionAvailability.cs；修改 Adapter/GameAdapter.Selection.cs；测试 tests/game/verifiers/verify_select_card_review.py。

接口：SelectionAvailability.UnavailableReason(CardSelection?, int cardId, CombatObservation) 返回固定公开原因或 null；原有 inspect_selection 文案独立保持。

- [x] 修改无选择、无效 ID、覆盖、卡包／结果页和确认预览检查：明确拒绝后可直接做合法动作，不再期待 observation_required；检查具体说明。
- [x] 使用旧 DLL 运行最小拒绝套件，保留因旧泛化提示或许可丢失而失败的证据。
- [x] 独立候选诊断，先验证当前快照，再将点击前已知拒绝使用 RejectedBeforeSubmission 并登记 unsubmitted_rejection_unchanged；固定原因公开；交互后失败使用固定安全说明，不公开异常 Message。
- [x] 构建并验证无效 ID 后直接选择有效牌、无选择后直接 end_turn、无初始许可不被拒绝创建许可；过期／未知仍清除许可。

## 任务 2：原生选中与取消事件

文件：新建 Events/SelectionInputJournal.cs；修改 Actions/SelectionActions.cs、Adapter/GameAdapter.Selection.cs、src/sts2_mcp/output/transition_details.py；新增 tests/python/test_selection_events.py，扩展 GUI 选牌检查及必要测试夹具。

接口：SelectionActions.Click 的可选输入包装委托只包围真实 Pressed 信号；SelectionInputJournal.Record 接受原选择、可选点击卡牌、同次公开快照、卡牌 ID 提供者和原生输入 Action。返回预览只包装取消按钮，其他按钮不据集合清理记录取消。

- [x] Python 检查新事件完整字段、未知名字 null、default 保留、非法额外字段拒绝、严格顺序；运行并确认缺少新事件导致失败。
- [x] GUI 检查 grid/hand/hand_upgrade 的选中、取消、替换，最后一张自动提交、确认预览返回、连续选择、头槌选中后移动的顺序；使用旧 DLL 确认空事件失败。
- [x] 实现独立记录入口：输入前保存原实例集合、公开身份和候选顺序并预留位置；输入后只按实际集合变化或原选择任务已成功完成的结果发布，不能凭请求假定成功。即时完成任务的结果仅验证所点候选是否被接受，不公开其他任务内容。
- [x] 接入公共事件校验及默认空值规则；验证未改变、不支持／失败输入、自动提交、预览与后续效果不重复、不伪造取消。

## 任务 3：交付与核销

文件：README、Mod/MCP 版本、持续接口文档、用户 TODO 已有错误处理进度、工具审阅与实施记录、修复后 JSON 示例。

- [ ] 运行完整 Python、C# 检查及 select_card 专项 GUI；涉及共用选择路径的 inspect_selection 和选牌预设按需要回归，保留失败记录并清理自有进程。
- [ ] 同步持续接口文档，原 91 份样例保持历史基线，新样例从修复后实际公共结果提取；更新工具清单与既有 TODO 进度，范围不扩张。
- [ ] 提交经过验证的实现，进行一次独立最终审查；处理重要问题，记录限制，合入 main 并删除临时分支，不重复无依据检查。
