# 事件选项拒绝恢复实施记录

> 当前状态：实现与验收完成，共1项，已完成1项；17类GUI及样本核对通过。独立最终审阅和合入待完成，无阻塞。

定稿见[choose_event_option审阅](2026-11-07-choose-event-option-review.md#输出定稿)，执行步骤见[实施计划](../superpowers/plans/2026-11-07-event-option-recovery.md)。原错误与十六份旧样本保留于[开发核验](2026-11-07-choose-event-option-development-notes.md)，不覆盖历史证据。

## 最终行为与范围

- 非事件、覆盖页面、等待结算、事件完成、无效／旧ID、锁定及已用选项的前置拒绝提供具体原因及对应工具提示。
- 相同快照下，明确点击前拒绝返回未提交保证，已有MCP许可得以保留。合法后续动作可以直接继续；首次无许可、过期状态、已交互／未知或矛盾证据不续接。
- 单个非负Int32 option_id、default/full、原生按钮与现有精简回执保持；无需summary。选择、奖励、占卜、确认框、战斗进入和死亡／复活使用现有结算等待及变化记录。
- 小范围重构限于EventInspection页面／动作／单项检查和对应调用点；未改动通用许可、结算或事件记录机制，未新增测试专用原生操作。

## 代码职责

[EventInspection](../../src/Sts2Agent/Observation/EventInspection.cs)的PageUnavailableReason共用覆盖判断，InspectionUnavailableReason继续用于详情与其可用性；ActionUnavailableReason额外检查已完成和Ready；OptionUnavailableReason区分锁定、已用、禁用／动画和点击可见性，Clickable复用它。Read.enabled和[AvailableTools](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)使用同一动作条件。

Ready仍独立检查任务、文字、预览、资源、动作队列及按钮动画。完成后的proceed不使用“可选择事件选项”的条件，以免被IsFinished拒绝；仍按原先Ready与Clickable判断。静态列表使用Displayed，悬停检查与点击范围分别保留。

[EventRequest](../../src/Sts2Agent/Adapter/GameAdapter.Event.cs)在UiChanged/ForceClick前使用RejectedBeforeSubmission；stale_state仍独立拒绝。[工具注册](../../src/sts2_mcp/tool_registry.py)开启已有unsubmitted_rejection_unchanged。异常消息继续由通用错误边界处理，不直接公开堆栈或私有对象。

## 验证基线与证据

- 基于e050428，目标Linux游戏v0.107.1/release59260271、RitsuLib0.6.10、Godot4.5.1。游戏程序集相对路径及哈希见上述开发核验，目标程序集已再次核对。
- Mod0.76.1、MCP0.78.1、schema45。最终构建与隔离运行时DLL均为425c7f26cc59797f8475993a268f29a7d612e8f9395b6ae8604e0c256e41b247。
- 新证据根`.tmp/2026-11-07-event-option-recovery/`；旧审阅证据与JSON保持不变。不正式安装或推送。

| 检查 | 结果与证据 |
| --- | --- |
| Python RED | 新4项中1项失败，0.042秒；旧注册不保留明确拒绝后的许可，python-red.log |
| GUI RED | 旧DLL在no_event拒绝恢复断言失败，16.499790468秒；PID8352已退出，gui-red/report.json |
| Python GREEN | 新4项通过，0.041秒；明确拒绝、冷调用、本地非法参数、过期／未知／已提交／矛盾证据，python-green.log |
| 全量Python | 781项通过，39.377秒；python-full.log，预期坏响应探针日志保留 |
| C# | 145项通过；csharp.log |
| 最终构建 | 3.96秒，零编译警告／错误；build-final.log；首个build.log为动作／查看用途文案收敛前的编译 |

GUI专项覆盖非事件、普通翻页／完成、锁定、升级、奖励、确认、占卜、战斗进入（普通回合及首回合选择）、死亡、复活和满药水槽奖励。普通事件另核对地图／牌组覆盖、无效ID、旧ID、完成后拒绝与直接proceed。直接原生状态读回明确关闭附图且不刷新MCP许可，用于确认拒绝前后玩法状态完全相同。

首个新DLL套件前6类通过，第7类占卜在“完整原始state相等”断言失败。逐字段诊断只发现divination_image的PNG随背景动画变化；snapshot_id及玩法字段完全相同。原始接口默认可附图，测试现显式关闭图片，继续严格比较其余完整状态。失败证据保留于gui/crystal，不修改产品逻辑或重建。

后续10类GUI通过；最后default_event在业务检查前因验证器仍写死42个工具而失败，当前公开玩法工具已有43个。去掉重复维护总数的断言，保留所需工具及所有已列工具的default预设检查；工具完整清单已有Python覆盖。仅单独重跑该项，保留原失败证据，产品DLL不变。

三个新DLL进程合计完成17类不同场景的验收：第一批前6类通过，第二批前10类通过，最后单独的default_event通过；包括两次保留的断言失败在内，共19次场景尝试。三批证据共143次MCP调用、38次直接原生检查，均含失败尝试的记录，运行器创建／重置请求不计。三批分别为135.863940770、207.230156248、24.898933531秒；PID9856、10500、11270均已退出。各批报告为gui、gui-remaining、gui-default/report.json。

回归覆盖事件详情、离屏／隐藏／透明／已选／不可悬停的显示规则、proceed及default预设。[十八份修复后JSON](2026-11-07-event-option-fixed-examples/README.md)逐份对照报告行和SHA-256，其中十七份full、一份default。verify_delivery.py另核对相对链接、版本、日志、DLL哈希、进程退出及保留的失败。

## 未验证范围

没有新增多人、第三方事件、未知弹窗、真实超时及任意人工并发切页的GUI验证，也不声称穷尽所有原生事件和遗物组合。等待结算、不可点击及重复使用规则另按原生源码核对；已用／离屏等显示夹具不等于自然游玩出现同类状态。未知结果不自动重试。

## 最终审阅与交接

独立最终审阅及合入尚待完成；工具仍未核销，未增加用户TODO项目。
