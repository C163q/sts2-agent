# 早期全流程反馈开发核验

核对日期：2026-11-08。代码基线 `301ea8d`；Mod `0.80.0`、MCP `0.83.1`、schema 47。用户结论和处理建议见[复核报告](2026-11-08-early-playtest-feedback-review.md)。本记录不表示已完成所建议的修复。

## 目标和证据位置

- Linux 游戏 `v0.107.1`、release 构建 `59260271`，RitsuLib `0.6.10`。
- 游戏目录内 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256：`d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 当前构建目录和隔离运行时的 Sts2Agent.dll SHA-256 均为 `2a87d3a18c4c34dca800132ed4cdb489f4ac8e20dc1e9ec3bfb6be84cfb4a1b5`，未重新构建或安装。
- 原生类型从上述目标程序集核对；本次反编译文件在 `.tmp/2026-11-08-playtest-feedback-audit/source/`，包括 MawBank、Planisphere、AbstractRoom、RestSiteRoom。RunManager 的已有反编译入口为 `.tmp/decompiled/RunManager.cs`。
- 已查看截图 `23-after-pael.png`、`27-run-result.png`、`28-score.png`；静态图片只能确认画面内容，不能确定工具调用时点。

## 资源记录缺口

[RunResourceJournal](../../src/Sts2Agent/Events/RunResourceJournal.cs)在每个已登记动作的作用域内订阅 CurrentHpChanged、MaxHpChanged、GoldChanged，作用域由 [GameAdapter.Resources](../../src/Sts2Agent/Adapter/GameAdapter.Resources.cs)创建。

通知和显示的具体关系：

1. MawBank.AfterRoomEntered 调用 PlayerCmd.GainGold；Planisphere.AfterRoomEntered 对问号节点调用 CreatureCmd.Heal。
2. 以休息处为例，RestSiteRoom.EnterInternal 显示房间节点后等待 Hook.AfterRoomEntered。RunManager.EnterMapPointInternal 等待 EnterRoom 完成后，才清除 MapScreen.IsTraveling，随后 FadeIn。
3. [MapView.Current](../../src/Sts2Agent/Observation/MapView.cs)排除 IsTraveling；[RunUi.NonCombatVisible／TopBarReadable](../../src/Sts2Agent/Observation/RunUi.cs)对普通房间的顶栏判断也依赖移动／过渡状态。
4. 顶栏不可读时 RunResourceJournal 的 GoldDisplay／Health 返回 null。Gold 直接丢弃本次通知并清空 knownGold；Hp 丢弃通知并清空 healthKnown。
5. 每次观察调用 SampleVisibility；顶栏恢复后只重新建立基线，不发布先前丢弃的通知。因此当前仍存在“目标画面的数值已变，事件缺失”的路径。

现有 [RunResourceChecks](../../src/Sts2Agent/Testing/Checks/RunResourceChecks.cs)明确验证隐藏数值不会被补录。修复应区分已知房间切换与其他隐藏／覆盖情况，并保留这些边界；不能简单把所有丢弃通知恢复发布，也不能仅比较整个动作前后的总差值，掩盖中间多次变化。生命变化还须遵守战斗日志去重。

旧 `.tmp/live/ipc/responses/` 中保留了与截图相同一局的 schema 34 原生回执。提取了 314 份带 transition 的响应，保存为本次证据目录的 historical-actions.json；原请求文件已不在对应目录，不能仅凭响应断定每条的调用工具名。

其中 `8412e56ea654449490fc7e9164d2bf8c.json` 为第七层休息处、gold:33、events:[]，`ce01dcd4ec9b4f328b13af87e1f70f79.json` 为第八层商店、gold:45、events:[]。关键样本另保存在 historical-key-cases.json。本次未新增当前局的两遗物端到端检查。

## 当前游戏实测

探针复用 [tests/game/suite.py](../../tests/game/suite.py) 的 GameSession，使用独立 GUI、IPC 和存档，顺序运行 ancient:tooth 和 play:death；后者通过 end_turn 让原生敌人攻击产生死亡。

主证据目录 `.tmp/2026-11-08-playtest-feedback-audit/ready-probe/`：

- `current-evidence.json`：包含完整公开回执、对局身份、读取序列和退出结果。
- `gui/ipc/responses/`：原生响应，供复核执行事实和完整状态。
- `gui/stdout.log`、`gui/game.log`：游戏日志。

结果：

- Pael's Tooth 选择五张牌并 confirm 后为 action_completed／complete:true，actions 包含 proceed；随后直接 inspect_ancient 成功。
- end_turn 返回 combat_lost／complete:true，scene:run_result，actions 包含 inspect_run_result 等四个查看工具。
- 紧接着的 inspect_run_result 成功，为 not_ready／options:[]。继续调用同一查看工具后取得启用按钮，未插入 get_observation。
- 展示和交互没有合并：采样中出现过 status:visible 但按钮尚不可用的状态，后续动画也可重新进入 not_ready。

[ActionSettling](../../src/Sts2Agent/Actions/ActionSettling.cs)没有将 combat_lost 列入等待一般 motionPending 的停止原因；[TurnBoundary](../../src/Sts2Agent/Events/TurnBoundary.cs)在战斗确认结束后就给出 combat_lost。因此战斗结束早于完整结算展示的行为仍存在，当前通过可用查看工具及展示状态表达。

[RunResultInspection](../../src/Sts2Agent/Observation/RunResultInspection.cs)已分离 InspectionUnavailableReason、DisplayComplete、ActionUnavailableReason；[RunEnding 请求](../../src/Sts2Agent/Adapter/GameAdapter.RunEnding.cs)读取不要求动作许可或先调用 get_observation，展示中内容可读取。过渡遮挡、未知页面或模态覆盖仍可能合法拒绝。

佩尔的 [Ready／Busy](../../src/Sts2Agent/Observation/AncientInspection.cs)等待原生选项任务、遗物领取、卡牌预览和资源动画；选牌返回经 [NonCombatBoundary](../../src/Sts2Agent/Adapter/GameAdapter.Rewards.cs)等待对应场景就绪。[AvailableTools](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)与执行共用 ProceedUnavailableReason。当前实测已通过。

第一份 probe_current.py 在佩尔初始 not_ready 时错误地要求立即存在启用选项／继续按钮，主动断言失败。未修改产品；原 `current-probe.log`、`current-evidence.json` 和 `gui/` 保留。新 probe_ready.py 按原生显示状态等待，写入独立 ready-probe 目录，两项完成。两次自有游戏 PID 10387、10833 均已退出；验证摘要在 verification.json。

## 结算文字

RunResultInspection.Read 的 texts 对所有已展示 CanvasItem 后代调用 Text，仅排除 InsideCard，随后 Distinct。NScoreLine 的文字、横幅和按钮子文字仍进入数组；title、score_lines、options 分别另行读取。Distinct 只合并相同字符串，不能建立内容归属或阅读顺序。

[result_summary](../../src/sts2_mcp/output/run_ending_details.py)不裁剪 texts，因此三种内容预设均保留重复。基础观察也使用相同静态结算主体。现有实测[死亡汇总示例](2026-11-08-result-inspection-examples/death-summary.full.json)同时出现计分标签／数值、横幅、按钮和未结构化总分进度；它与当前读取代码一致。

建议依据控件归属排除已结构化内容，保留尚未表达的正文；涉及 outcome、summary、epoch、unlock、history 等页面，不能直接删除整个 texts 或只保留固定几个标签。

## 回归验证与限制

既有 test_turn_transition_updates、test_action_observations、test_run_result_summary、test_result_inspection_presets 共 30 项通过，日志 `.tmp/2026-11-08-playtest-feedback-audit/related-tests.log`。这批测试验证当前行为，并不证明资源漏记或 texts 重复已经修复。

本次未修改 C#、Python 产品代码、当前接口契约、正式游戏或 TODO。修复建议仍需按复核报告确定范围后实施。
