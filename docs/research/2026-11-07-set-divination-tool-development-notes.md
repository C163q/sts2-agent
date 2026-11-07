# set_divination_tool 开发核验依据

> 当前状态：定稿已进入实施，当前验收见[实施记录](2026-11-07-divination-tool-view-implementation.md)；以下保留审阅基线。用户决策内容见[核验与建议](2026-11-07-set-divination-tool-review.md)。

## 问题依据

| 编号 | 优先级 | 依据与状态 |
| --- | --- | --- |
| DIVINATION-TOOL-01 | 中 | GameAdapter.Divination中页面／目标／参数拒绝使用FileMailbox.Error，没有action_submitted:false或ui_unchanged:true；注册虽effect:view，但requires_permission:true，且未开启相应明确拒绝恢复。实测拒绝后合法操作仍observation_required。待修复 |
| DIVINATION-TOOL-02 | 中 | 页面／目标检查没有public_message；MCP将两类内部错误都投影为通用illegal_action。无棋盘、覆盖和结束无法区分。待修复 |

明确拒绝发生于UiChanged/ForceClick之前。原始execution表明未交互、未观察到提交；拒绝前后snapshot_id相同。当前恢复协议要求显式未交互保证，单凭execution的false不授予许可，这一共用规则无须另建。

## 基线

- 项目bd493fc，核对日期2026-11-07；Mod0.76.1、MCP0.78.1、schema45。
- Linux游戏v0.107.1/release59260271，RitsuLib0.6.10、Godot4.5.1。
- 目标程序集相对路径data_sts2_linuxbsd_x86_64/sts2.dll，SHA-256再次核对为d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 构建及隔离运行时Sts2Agent.dll均为425c7f26cc59797f8475993a268f29a7d612e8f9395b6ae8604e0c256e41b247；没有重建、更新版本或正式安装。
- 新证据根`.tmp/2026-11-07-set-divination-tool-review/`；原生缓存`.tmp/2026-10-31-divination/source/`及`.tmp/2026-10-31-events/source/CrystalSphere.cs`。

## 原生与适配器

NCrystalSphereScreen._Ready将两个NDivinationButton.Released连接到SetBigDivination/SetSmallDivination。这两个方法更新双方SetActive，再调用CrystalSphereMinigame.SetTool；SetActive仅设置Outline.Visible，SetTool设置枚举并刷新已有悬停范围。没有扣次数、揭开、随机抽取或奖励发放；原生也允许重复点击当前已选工具。

扣次数在CellClicked中；物品全部占用格揭开后RevealItem进入已揭开列表，CompleteMinigame等待0.75秒再DoLocalCrystalSphereRewards，随后触发Finished。OnMinigameFinished隐藏工具、次数和教学，并启用proceed。因此已揭开物品还不等于已经打开奖励页；奖励／选牌覆盖验证须先耗尽次数。

[GameAdapter.Divination](../../src/Sts2Agent/Adapter/GameAdapter.Divination.cs)共享inspect_event、set_divination_tool和divine。切换参数严格校验后要求expected_state一致，再检查Ready、Playing及目标IsEnabled；UiChanged后ForceClick，最终走ActionObservation/NonCombatBoundary和TransitionSuccess。切换目前没有独立动作函数。

[DivinationInspection](../../src/Sts2Agent/Observation/DivinationInspection.cs)的Ready检查Exposed、单人、揭开／任务／资源动画、遗物和动作队列；Playing另排除Finished。Read.tools[].enabled仅合并ready与IsEnabled；[AvailableTools](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)则在Playing时一起列出set_divination_tool和divine。常规原生运行中两工具均显示且启用；切换审阅未发现自然流程中的按钮可用性矛盾。重构可将本工具的页面和单项原因共用，揭开独有条件留给divine审阅。

[工具注册](../../src/sts2_mcp/tool_registry.py)为category:action/effect:view、requires_permission:true、returns_transition:true、records_events:true。描述中的“action rules”并非参数新要求，而是当前会话策略。[当前文档](../development/mcp.md#调用和错误语义)已明确记录其例外，不能将这一已实现契约当作文档过时。

[set_selection_view](../../src/Sts2Agent/Adapter/GameAdapter.SelectionView.cs)是可参考的既有视图流程：不要求已有许可，先检查当前页面，必要时点击原生按钮，等待后核对上下文和实际视图，再返回Success；注册使用actions_only投影及unchanged_view_rejections。若采纳统一建议，切换分支应走这一类规则，检查切换后仍为相同棋盘且选中工具与请求一致；divine的expected_state与事件记录保持独立。

瞬态对白在ObservationSnapshot中从许可令牌计算排除；原始PNG也不是许可状态的一部分。直接原生审阅请求显式include_divination_image:false，避免将独立背景动画误判为玩法变化。

## 验证与样本

Python相关检查为test_divination、test_event_inspection_presets，共21项通过，0.694秒；日志python.log。未运行全套Python或C#、没有构建。

GUI审阅覆盖五类测试局：无棋盘、正常棋盘（含重复、切换、default、地图／牌组覆盖）、结束、奖励覆盖、奖励选牌覆盖。切换前后核对次数、棋盘与顶栏不变；成功回执为空事件、无图片，可直接连续切换。无棋盘／覆盖／结束拒绝前后令牌一致，后续合法动作仍要求观察。

首次进程前三类通过；第四类准备奖励样本时，在揭开完整药水后立即期望奖励页而失败。核对CompleteMinigame确认奖励统一在次数耗尽后发放。原失败及玩法状态保留在根目录evidence.json；剩余两类在remaining/的新证据中补齐，未修改产品代码或覆盖旧报告。

[十二份完整JSON](2026-11-07-set-divination-tool-examples/README.md)均来自实际MCP stdio，一份default，其余full；参数、来源行与SHA-256见manifest。奖品定位使用私有夹具选定覆盖目标，随后实际揭开并处理原生奖励；夹具的物品位置仅作为测试证据，公开样本为MCP投影后的返回。

五类场景均已完成现状核验，共六次场景尝试：初次前三类通过、奖励准备失败；remaining中的奖励和选牌两类通过。根report.json保留异常时的status:running及末项failed，脚本实际以1退出且进程已关闭，不能将该标记解释为仍有运行进程。两批时间为100.576434821秒与67.873195726秒；PID13108与13539均已退出。两批报告共77次MCP调用、19次直接原生检查，含失败尝试；运行器创建／重置请求不计。

“通过”表示成功确认当前行为，包括错误仍会清除许可，不表示两项问题已经修复。真正的忙碌中途请求、按钮异常隐藏／禁用、未知弹窗、多人、第三方内容和全部奖励组合未新增GUI验证；原生忙碌与结束规则按源码核对。

## 候选实现边界

若统一为视图工具，set_divination_tool应使用requires_permission:false、returns_transition:false、records_events:false、actions_only投影及unchanged_view_rejections；明确未交互拒绝提供ui_unchanged:true。成功仍生成当前快照供后续动作使用；失败的冷调用不生成许可，UI已经改变后的错误不恢复旧许可。

将工具切换与divine动作分开，并从GameAdapter.Resources.RecordedActions移除set_divination_tool；divine继续记录。沿用DivinationInspection共用页面检查及原生按钮，不新建通用许可机制。若维持现有动作策略，则改用已有未提交动作拒绝保证；两条路径由输出定稿决定，当前均未实施。
