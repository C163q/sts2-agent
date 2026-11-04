# 连续出牌实施计划

> 当前状态：完成。共 4 项，已完成 4 项；接口、三项问题及重要边界修复均已通过验证，遗留集成验证范围见实施记录。无阻塞。
>
> 执行方式：按 superpowers:executing-plans 在当前功能分支自行实施，完成后由一个独立审查者检查本任务差异；不分派实现子任务。

**目标：** 新增遵循原生队列的 play_cards，修复 PLAY-01–03，并保留可靠的逐张及跨选牌回执。

**架构：** 独立解析和逐张进度模型；共用出牌校验和原生生命周期追踪，单张调用保持形状，批量调用通过同一动作观察器返回。跨选择只跟踪已入队对象，不保存未来执行列表。

**技术：** C#／Godot／目标游戏程序集与 RitsuLib；Python MCP、unittest、现有隔离 GUI 套件。

**规格：** [实施规格](../../research/2026-11-04-play-cards-design.md)，包含全部输入、状态、信息边界及版本要求；[原调研](../../research/2026-11-04-play-card-review.md)仅用于核对已引用证据。

## 全局约束与重点

- 现有分支 feat/potion-inspection-presets，基线 ecd071e；继续当前已授权工作区，不创建或切换分支。
- 只通过 TryManualPlay 提交；游戏线程执行，不等待 LLM 选择，不读取隐藏牌堆／预测结果。
- 全部输入整体验证后才产生副作用；后续动态失败继续，选择或终态停止新增提交。
- Finished 不等于实际打出；自动出牌、隐藏 UI、暂停、异常及同牌多次效果均须独立测试。
- 默认过滤前完整校验；缺失／错配回执、未知结果不恢复动作许可。
- 单张成功返回形状及 action_canceled 许可规则不变；44 项工具、Mod 0.63.0／MCP 0.65.0／schema 40。

## Task 1: 输入与输出契约

**文件：** Python card_play_details、独立 card_batch_details、tool_registry、action_output；新增 tests/python/test_play_cards.py；C# 新增 Actions/CardPlayOptions.cs、Actions/CardPlayProgress.cs 及独立检查。

**接口：** CardPlayOptions.Parse(JsonElement?, bool multiple) 返回 CardPlayInput[]；CardPlayProgress 仅记录提交、开始、真实出牌、取消、结束／失去追踪；batch_arguments 规范化输入，card_batch_details 验证 card_plays。

- [x] 先写严格数组／ID／目标类型与进度语义的失败测试，运行确认 RED；包含取消后 Finished、没有真实出牌、隐藏出牌及异常。
- [x] 实现纯解析／进度模型和 Python 严格解码、注册 play_cards、动作投影保留 card_plays；允许后续动作回执中的合法更新。
- [x] 运行相关 Python 和独立 C# 检查为 GREEN，核对工具列表变化及本地错误不清除已有许可。

## Task 2: 原生诊断与单张重构

**文件：** GameAdapter.CardPlay、独立 GameAdapter.CardPlayRules、Actions/ManualPlayBatch、TargetInspection、Localization/CardPlayFailureText。

**接口：** CardPlayUnavailableReason(bool allowQueued=false)；共享初始引用／按项校验；ManualPlayBatch 构造订阅／Submit／Read／Dispose 只追踪对应原生动作与生命周期。

- [x] 用 GUI 回执断言 PLAY-01 的选择／地图／牌组拒绝及 PLAY-02 Normality 来源提示，保留 RED 证据。
- [x] 实现原生 UI 原因读取、PLAY-03 文案，共用阶段原因及局部单张提交器，单张保持现有回执。
- [x] 构建并运行原有单张正常、费用、选择、取消和终态回归；确认阶段拒绝及 0 能量后 end_turn 仍正确。

## Task 3: 连续提交与选择续接

**文件：** GameAdapter.CardPlay、GameAdapter.Resources、RequestDispatcher、AvailableTools、输出批次验证、GUI verify_play_cards、原生队列夹具。

**接口：** adapter 持有至多一个未完成 ManualPlayBatch；记录动作成功回执附加 card_plays；新局及外部替换释放旧引用，终结回执发布后释放订阅。

- [x] 先写真实 MCP play_cards 的 RED 测试，覆盖整批前置拒绝、动态失败继续、同步选择停止未提交、选择恢复及原生取消。
- [x] 接入批量编排、同局／战斗／回合防护、显式未提交保证、pending 追踪及完整输出；不在单项失败后返回整批未执行。
- [x] 图形验证正常顺序、费用／星能、目标死亡、随机消耗、手动／自动手牌选择、发现、头槌、胜负及后续回执；复用既有观测稳定机制。

## Task 4: 验收与交付

**文件：** README、card-play.md、mcp.md、架构／文件接口相关说明、工具清单、实施报告及真实 JSON 样本。

- [x] 运行完整 Python、独立 C#、必要 GUI 回归；校验跨回执关联、未知结果／取消、异常日志隔离及所有输入形状；版本和目录同步。
- [x] 独立审查本任务差异，按严重程度处理发现，重要修复各有 RED→GREEN；记录未验证范围。
- [x] 核验 JSON、文档链接、进程清理与 staged diff；创建 Conventional Commits 英文提交，报告结果，不安装 Mod。
