# 火堆拒绝恢复与遗物计数事件实施计划

> 当前状态：实施中，共1项，已完成0项；行为验收完成，剩余提交、独立审阅和合入，无阻塞。
> 执行方式：使用superpowers:executing-plans在当前会话实施，完成后进行一次独立审阅；不按步骤派发代理。

**目标：** 修复choose_rest_option的明确拒绝恢复及具体诊断，统一记录实际显示的遗物计数变化。
**架构：** 火堆模块共用页面／目标拒绝判断；独立RelicCounterJournal从原生标签刷新及观察采样接入同次ActionEventScope，不扩大RunInventoryJournal的职责。Python严格校验新增事件，继续使用现有精简动作回执。
**技术：** C#／Godot／Harmony、Python MCP、unittest、隔离GUI。
**规格：** [审阅定稿](../../research/2026-11-06-choose-rest-option-review.md#输出定稿)。

## 约束

- 保留option_id、default/full，无新增summary；复用原生按钮和等待流程。
- UiChanged前的明确拒绝保留已有许可；过期、未知或交互后失败不声明未执行。
- 事件relic_counter_changed使用relic:{name}、before、after；两端为整数或null，至少一端为整数且不相等。null表示图标可见时没有计数标签，default也保留。
- 数据仅从本地当前实际显示的遗物及标签读取，不以DisplayAmount补数。隐藏时丢基线，重新显示／取得／替换只建基线；独立动作或销毁后不重放。
- 记录标签刷新后已显示的连续变化，重复通知不重复；新取得和移除事件保持现有规则。
- 版本Mod0.73.0、MCP0.75.0、schema42，兼容历史schema样本。
- 不正式安装或推送；验证后提交并合入main、删除临时分支。

## 审阅重点

- 页面遮挡／过渡、无房间、未知ID、置灰、无焦点、离屏目标的诊断和许可恢复；旧工具边界不改变。
- 遗物同帧多次刷新与其他事件的顺序，不依赖模型通知到UI刷新之间的先后。
- 图标／顶栏隐藏、透明／裁剪、离屏以及标签从无到有／从有到无，隐藏期间不重放。
- 已取得／移除、持有者替换、别的玩家／非当前run与scope销毁，不能生成错误基线。
- 新事件的空值、数值类型、额外字段和混合事件经真实GameTools完整校验与预设输出。

### Task 1: 共用动作判断与可见遗物计数

**文件与职责：**
- RestSiteInspection.cs、GameAdapter.RestSite.cs、AvailableTools.cs：共用页面／目标判断，明确未点击拒绝。
- 新Events/RelicCounterChanges.cs：与Godot无关的基线、变化及顺序；新Events/RelicCounterJournal.cs：真实标签、可见性与原生刷新挂钩。
- GameAdapter.Resources.cs、GameObservation.cs、Infrastructure/BridgeMod.cs初始化入口：动作生命周期、采样、挂钩初始化。
- tool_registry.py、transition_details.py、inspection_details.py：许可声明及事件／schema校验。
- tests/python/test_rest_option_feedback.py、tests/csharp/Sts2Agent.Checks/RelicCounterChecks.cs及现有GUI审阅器：错误恢复、数据边界和实际行为。
- 文档、版本与新JSON样本：更新现状，原审阅JSON不改写。

**接口：**
- RelicCounterChanges<TKey>.Sample(TKey key,string name,int? counter)、ForgetExcept(IEnumerable<TKey>)、Clear()；共享TurnEventBuffer。
- RelicCounterJournal.Initialize()、Current、SampleVisibility()、Dispose()；private postfix在真实RefreshAmount结束时采样。
- RestSiteInspection.ActionUnavailableReason(room)、OptionUnavailableReason(button)；Clickable复用后者，可用列表和动作共用前者。

- [x] Step 1：编写Python用真实GameTools验证未提交拒绝恢复／反证、新事件严格形状和null保留；C#验证重复、连续、隐藏重建、null切换及共享顺序；GUI审阅器改为断言明确恢复与计数事件。先在旧实现运行，确认预期失败。
- [x] Step 2：实现两项共用判断／拒绝恢复，添加计数状态机与原生标签刷新采集，核对目标程序集方法后挂钩；按规格接入解析和版本。
- [x] Step 3：相关Python、C#与构建通过；准备隔离运行时，运行新动作GUI和显示／计数原生检查，补充战斗或其他动作的计数回归。
- [x] Step 4：运行完整Python及适用C#，同步持续文档、TODO已有两项覆盖、清单与实际新JSON；校验来源／哈希／相对链接、自有进程退出、运行时一致，保留失败现场。
- [ ] Step 5：通过验证后提交feature；执行task-done的证据校验脚本，记录结果和偏离决定。
## 最终收尾

- [ ] 一次独立全范围审阅；处理重要发现并补失败→通过验证，归档本计划工作区，合入main、删临时分支，交付结果和未验证范围。

验证命令：相关Python使用100秒、完整Python180秒超时的.tmp/mcp-venv/bin/python -m unittest；dotnet build限90秒、C#运行限45秒；GUI用scripts/gui_suite.py各设420秒有限超时，证据根.tmp/2026-11-06-rest-option-feedback/。最后task-done仅运行该证据根verify_delivery.py，校验已执行结果，不重复GUI。
