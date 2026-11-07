# choose_ancient_option 开发核验依据

> 当前状态：审阅完成；四项问题待确认处理范围，未修改产品或测试代码。11类玩法场景中10类完成现状核验；致死馈赠经两次MCP和一次有效原生鼠标点击复现，根因未定。鼠标补查见[对照记录](2026-11-07-ancient-native-click-recheck.md)，下文验证统计保留原审阅基线。用户决策内容见[核验与建议](2026-11-07-choose-ancient-option-review.md)。

## 基线与证据

- 代码e4b1979，核对日期2026-11-07；Mod0.78.0、MCP0.80.0、schema46。
- Linux游戏v0.107.1/release59260271，RitsuLib0.6.10、Godot4.5.1。
- 游戏程序集相对路径data_sts2_linuxbsd_x86_64/sts2.dll，再次核对SHA-256为d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 编译产物与全部隔离运行时DLL保持dcee25a818d107d90f22860fcd7e98d59185142eef6712ac3adc6932b9cc4b22；没有重建、版本更新或正式安装。
- 证据根`.tmp/2026-11-07-choose-ancient-option-review/`，包含首批、remaining、manual-input、manual-input-fixed和lethal-repeat五个隔离实例的日志及记录。
- 原生缓存沿用`.tmp/2026-10-31-ancients/source/`的NEventOptionButton、NEventRoom、EventSynchronizer、EventOption、AncientEventModel、DistinguishedCape、LostCoffer、ScrollBoxes等。RelicCmd另见`.tmp/2026-10-31-treasure/source/`；CreatureCmd、RunManager、NRunHistory、RunHistoryUtilities的死亡／结算分支由既有目标版本缓存核对。

## 问题依据

| 编号 | 优先级 | 核验结论与状态 |
| --- | --- | --- |
| ANCIENT-CHOICE-01 | 中 | [AncientRequest](../../src/Sts2Agent/Adapter/GameAdapter.Ancient.cs)的参数、页面及按钮拒绝使用FileMailbox.Error，未提供action_submitted:false，注册也没有unsubmitted_rejection_unchanged。实测明确拒绝时执行标记均未交互／未提交、前后snapshot_id相同，下一项合法动作仍observation_required；待修复。 |
| ANCIENT-CHOICE-02 | 中 | 页面／按钮两类illegal_action没有public_message，MCP统一为通用消息。无房间、无效ID、已领取、对话中段、禁用及地图／牌组／选牌／奖励覆盖均不能区分；待修复。 |
| ANCIENT-CHOICE-03 | 中 | ScrollBoxes领取进入bundle时回执events为空，同次原始观察top_bar已列出Scroll Boxes。相同最终DLL的前一项GUI验证也出现相同结果；是可见获取反馈缺口，尚未修复。 |
| ANCIENT-CHOICE-04 | 高；根因待定 | cape_lethal夹具最大生命9，当前可见且启用的DistinguishedCape带true警告；选择后游戏stdout出现“Fatal error. Invalid Program: attempted to call a UnmanagedCallersOnly method from managed code.”，MCP无原生回执，最终timeout。全新实例首局独立复现，非多次重置特有现象；未定位到具体组件。 |

## 原生执行与已接入记录

NEventOptionButton.OnRelease先检查IsLocked；单人WillKillPlayer为true时显示红框并继续执行，不拒绝致死选择。NEventRoom.OptionButtonClicked对普通选项清理布局，再由EventSynchronizer.ChooseLocalOption使用原生列表位置执行EventOption.Chosen。Chosen标记WasChosen，调用BeforeChosen并等待OnChosen；EventSynchronizer保存任务，后续流程可在选牌／奖励处等待输入。

AncientEventModel.RelicOption使用RelicCmd.Obtain，再调用Done；原生Obtain先加入遗物、触发顶栏动画，再等待AfterObtained。ScrollBoxes在AfterObtained中生成包、等待选包，再把卡加入永久牌组；LostCoffer等待额外卡牌／药水奖励。DistinguishedCape通过CreatureCmd.LoseMaxHp减少最大生命，随后生成三张Apparition；原生LoseMaxHp先对超过新上限的当前生命造成损失，可能先进入死亡流程。

当前工具在同次快照校验expected_state，查找稳定ID映射，再检查Ready、Clickable及Continue。UiChanged标记首次交互，ForceClick进入上述原生释放回调。ActionObservation等待同一对局／同一先古模型的NonCombatBoundary，否则报告interrupted；该边界支持choice_required、额外奖励、完成及run_lost。此次没有取得致死成功回执，因此不能声称已验证该动作的run_lost分支。

choose_ancient_option已列入RecordedActions，使用共用资源、物品、遗物计数及战斗交接记录。普通营养牡蛎的遗物／最大生命／生命事件，欧洛巴斯之触的馈赠／移除／获得事件均正常；变牌到达choice_required。打开卡牌包时不应提前报告尚未选定的卡牌加入，问题是已经显示的遗物获取事件也缺失。

## 卡牌包事件缺口的调查范围

本任务bundle的choose_full原始成功响应包含top_bar.relic_count:2，以及Burning Blood、Scroll Boxes两项遗物，但公开transition.events为[]。前一项独立实例的`.tmp/2026-11-07-ancient-inspection-presets/gui/bundle/verify/evidence.json`中direct_choice及其原生响应相同，DLL哈希一致；不需要重复运行已获得的同类证据。

[RunInventoryJournal](../../src/Sts2Agent/Events/RunInventoryJournal.cs)在RelicObtained时预留记录，后续采样从可见图标读取名称；Defer中的publish会在顶栏或区域暂不可读时移除挂起记录。[RunResourceJournal](../../src/Sts2Agent/Events/RunResourceJournal.cs)又在CardSelection.Current存在但尚不可读时返回TopBarVisible:false。结合页切换，怀疑挂起记录在入场中被丢弃；这是源码支持的候选原因，尚未通过逐帧探针证明具体发生顺序。实施应保留真正隐藏内容的边界，同时验证同次动作结束前重新出现的可见图标反馈。

这里没有新增“根据已获得模型直接公开名称”的处理；仅依据可见UI补事件，不能绕过图标披露。也未对所有物品与所有页面切换宣称存在同一缺口。

## 验证结果

test_ancients、test_ancient_inspection_presets、test_event_option_recovery共25项通过，0.656秒，python.log。包含严格参数、本地拒绝、先古详情、旧观察及相邻动作恢复规则。未运行全套Python、C#或构建。

首批GUI使用真实MCP stdio，九类现状检查完成：无先古房间、普通馈赠、多行对话、地图／牌组覆盖、禁用、遗物替换、变牌、卡牌包及嵌套奖励。致死场景未取得成功回执，原脚本因预期成功而中止；报告保持failed，不能概括为全部GUI通过。251.569190803秒，PID49060退出。

remaining补齐旧观察：外部通过原生工具领取后，原MCP连接的选择正确报stale_state，后续动作要求读取；刷新后proceed成功。随后尝试对自有窗口发送一次鼠标点击作致死对照，但前后仍为相同先古页面，HP和选项不变，没有证据表明选中馈赠。70.551940627秒，PID49951退出；该尝试不能证明原生点击路径正常。

第二个鼠标探针在mousemove --sync等待已相同坐标时超时，尚未按下；49.419740806秒，PID50461退出。移除此等待的第三个探针完成按下／松开及截图，仍未引起选择，49.560226675秒，PID50715退出。全部失败和未触发记录保留，不以这几次操作归因崩溃；不再继续同类无效探针。

lethal-repeat在全新实例首局使用MCP选择一次致死斗篷，仍有相同致命日志，得到timeout；诊断客户端等待缩短为12秒，首批为默认40秒。41.591618426秒，PID51104退出。报告标记expected_failure_reproduced，表示问题重现，不表示产品通过。没有重试任何结果未知的原对局。

主审、旧观察及致死复现记录共139次MCP调用、28次直接原生核对；运行器创建／重置及三个鼠标探针的状态读取、截图另计。所有五个自有进程均退出，使用同一运行时DLL。[16份实际JSON](2026-11-07-choose-ancient-option-examples/README.md)逐份保留参数、来源行和SHA-256；致死错误样本是实际MCP错误，没有伪造run_lost成功输出。

交付检查通过：16份样本、25项Python记录、10类非致死场景核验、两次致命错误、五个进程退出、两个DLL哈希和196个相对链接均已核对，见final-verification.log；原failed报告与三个无有效选择的鼠标探针保持原样。

## 崩溃尚未确定的部分

日志在致命错误前有“How did the game end??”，对应NRunHistory.GetGameOverType无法从记录判定结束类型的分支。RunHistoryUtilities从地图历史读取死因，当前隔离夹具使用直接进入事件房间的准备方式；需要核验历史准备和真实对局是否一致。该提醒不是崩溃调用栈，不能直接当作根因。

原审阅没有取得有效原生鼠标选择对照。用户授权后的[补查](2026-11-07-ancient-native-click-recheck.md)已核对第一项悬停并通过原生点击复现相同致命错误，进程SIGABRT退出；无需choose_ancient_option专有调用路径也会发生。尚未测试不加载Mod／RitsuLib的实例或自然推进至低最大生命先古房间的对局，因此仍需区分共用Mod／结算、本地化Hook、依赖、游戏及夹具。后续应取得可靠调用栈或进一步对照，再决定修复位置。

其他未穷尽范围包括所有先古／角色／遗物组合、多人、第三方UI，以及人工打断时序。现有选牌和奖励工具继续处理后续输入，未新增批量选择或summary需求。

## 建议实现边界与文档

先古读取、选择和推进目前共用一个适配器分支，但只读已拥有具体诊断，动作仍使用旧合并拒绝。建议集中页面、选择动作与单项不可用原因，让执行、选项enabled和available_actions复用；只对已确认未点击／未改UI的choose_ancient_option拒绝提供保证及注册恢复策略。stale、已交互和不确定输出保持撤销。advance_dialogue的完整动作审阅仍留后续。

参数维持option_id和default/full。文档已同步上述已核实缺口，避免把尚未覆盖的事件或死亡流程写成完整支持；差异记录`.tmp/2026-11-07-choose-ancient-option-documentation-report.md`。四项发现属于当前工具审阅，未擅自加入用户TODO。
