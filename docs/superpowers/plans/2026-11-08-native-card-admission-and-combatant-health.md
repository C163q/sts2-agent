# 原生出牌接受与战斗对象生命实施计划

> 当前状态：实施中，共 2 项，已完成 1 项。原生出牌接受已通过验证；正在补齐战斗对象生命／格挡，无阻塞。
>
> **For agentic workers:** 使用 superpowers:executing-plans 在当前会话逐项实施，按 RED→GREEN 验证；完成后一次独立审阅。

**Goal:** 由原生调用决定出牌是否接受，并让战斗对象详情提供当前可见生命与格挡。

**Architecture:** 参数、场景及引用校验留在适配层；可打出判断由 TryManualPlay 执行，返回 false 后才读取公开拒绝原因。生命／格挡纳入 CombatantInspection 共用读取，基础观察组装其他资源；Python 共用生命摘要格式。

**Tech Stack:** C#／Godot／Harmony，Python MCP，原生 GUI 与 Python／C# 检查。

**Spec:** [中期反馈复核](../../research/2026-11-08-mid-playtest-feedback-review.md)及[开发依据](../../research/2026-11-08-mid-playtest-feedback-development-notes.md)，用户已确认实施两项建议。

## Global Constraints

- 保持原生快速连续入队，不预支资源、不等待前项结算后补发；能量事件合并规则保持。
- 保留参数、场景、卡牌身份及可见目标范围校验；原生 false 不发布提交事实，保留具体公开原因。
- full/default 增加 hp、max_hp、hp_display、block；同伴按需增加 block_shared_with。summary 用 health，隐藏生命显式 null；既有状态和提示过滤保持。
- sources 可选择新增静态字段；省略／null 全部，[] 空，原始位置映射保持。先完整验证再筛选。
- 对旧响应保留无新增字段兼容；新 schema 48 要求生命字段完整。版本 Mod 0.82.0、MCP 0.85.0，README 统一维护。
- 不安装正式 Mod、不修改 TODO；沿用当前工作区临时分支，验证后自行合入 main。

## Review Focus

- 费用不足也应实际调用一次原生入口；其拒绝不能变成通用错误或丢失旧许可。
- 原生接受、取消、选择、目标失效与未知结果仍按已有事实判断，不能绕过原生队列。
- 隐藏生命不可用模型补齐，summary 的 health:null 在过滤后仍保留。
- 只筛 hp／block 不应附送其他状态或悬停说明；筛选前坏数据仍失败。
- 奥斯提共享格挡、无限／死亡生命、基础观察原有输出及旧 Mod 响应均应保持各自含义。

### Task 1: 原生出牌决定接受与拒绝

**Files:** `GameAdapter.CardPlayRules.cs`、`ManualPlayBatch.cs`、测试 CardPlayRejectionFixture／TestRequestDispatcher、verify_play_cards.py、card-play.md。

**Interfaces:** 保持 CardSubmissionReason 签名但只校验身份与目标；ManualPlayBatch.Submit 的原生 false 使用只读拒绝诊断。

- [x] Step 1: 扩展仅测试模式原生入口观察，验证 0 能量单张与批量都实际到达 TryManualPlay，仍拒绝且可立即 end_turn；旧实现必须失败。
- [x] Step 2: 删除入队前的 CanPlay／CanPlayTargeting 门控，原生 false 后读取 TargetInspection.Reason 或通用原因。
- [x] Step 3: GUI 核对拒绝、Normality、正常队列、选择续接；Python 全套与 C# 检查通过，更新文档后提交。

### Task 2: 共用生命读取与战斗对象输出

**Files:** `CombatantInspection.cs`、`CombatObservation.cs`、combatant_details.py／combatant_presets.py／combat_fields.py／observation_presets.py、版本与文档、相关 Python 和 GUI 验证器。

**Interfaces:** 共用静态对象新增生命字段；共用 Python health_summary 格式化 health，get_observation 保持既有外部结构。

- [ ] Step 1: Python 先覆盖完整／摘要生命、静态字段筛选、空筛选校验坏数据及旧响应；当前实现失败。GUI 断言新增生命与基础观察一致。
- [ ] Step 2: 共用原生生命读取及同伴关系；投影与校验新增字段，summary 共用格式，sources 接入新增字段；新 schema 要求完整字段，旧响应仅在包含字段时校验。
- [ ] Step 3: 新增隐藏生命／格挡原生检查；运行 basic／osty／blade／orbs／selection 与任务 1 回归 GUI；Python 全套、C# 检查通过。
- [ ] Step 4: 更新持续文档、版本和实际 JSON 样本；记录验证证据并提交。

## 收尾

两任务完成后一次独立全分支审阅；重要问题一次 RED→GREEN 修复，轻微建议另记。保存证据，清理自有测试进程和本计划临时技能目录，合入 main 并删除分支。
