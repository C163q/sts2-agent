# inspect_run_result 开发核验

## 基线与证据

核验日期2026-11-07，代码基线9b95886，Mod0.78.2、MCP0.80.2、schema46；Linux游戏v0.107.1、release构建59260271，RitsuLib0.6.10。决策说明见[审阅报告](2026-11-07-inspect-run-result-review.md)，实际返回见[样例目录](2026-11-07-inspect-run-result-examples/README.md)。

本地证据根目录为`.tmp/2026-11-07-inspect-run-result-review/`。安装目录下`data_sts2_linuxbsd_x86_64/sts2.dll`的SHA-256为`d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`；本轮运行时及构建产物DLL均为`ad21eaffa973c04429980467bf860ad4c13e409a9cea294e46ffd164d6a7ebd1`。未改产品代码、版本或安装，未重建DLL。

目标程序集重新反编译的NGameOverScreen、NBadge、NDiscoveredItem、NEpochSlot、NEpochInspectScreen和NTimelineScreen保存在证据目录source/，不提交源码或游戏数据。

## 当前链路

| 职责 | 入口与核对 |
| --- | --- |
| 注册／预设 | [tool_registry.py](../../src/sts2_mcp/tool_registry.py)：NO_ARGUMENTS，effect=read，无前置许可，default/full；不返回transition或记录事件。 |
| 原生执行 | [GameAdapter.RunEnding.cs](../../src/Sts2Agent/Adapter/GameAdapter.RunEnding.cs)的RunResultRequest同时处理查看和动作；查看仍要求Current、Exposed及Ready，失败返回私有FileMailbox.Error，成功使用InspectionSuccess复制同次上下文。 |
| 生命周期和读取 | [RunResultInspection.cs](../../src/Sts2Agent/Observation/RunResultInspection.cs)：Current识别胜负页及嵌套本局详情／榜单；Leaving和原生菜单栈绑定后识别教程、时间线、章节和解锁；菜单栈退出即解除关联。 |
| 操作就绪 | Ready同时要求实际单人、无遮挡、所有可浏览RichTextLabel显示完整、根补间／结算计分动画结束、时间线InputBlocker关闭，以及至少一个Clickable选项。 |
| Python解析 | [run_ending_details.py](../../src/sts2_mcp/output/run_ending_details.py)的inspect_result_details要求scene=run_result及主体status=visible；[inspection_details.py](../../src/sts2_mcp/output/inspection_details.py)随后合入scene_context，但没有检查screen与主体的对应关系。 |
| 恢复 | [game_session.py](../../src/sts2_mcp/game_session.py)的纯读取拒绝策略保留已有许可；冷读取失败不授予许可，成功详情发布当前令牌。 |
| 工具列表 | [GameAdapter.AvailableTools.cs](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)同样仅在Ready时列inspect_run_result；not_ready基础观察只列实际可读的顶栏等工具。 |

[run-ending.md](../development/run-ending.md)当前说明与原生页面识别、正常成功返回相符。本轮没有发现需要以改文档掩盖的正常界面错配。

## 原生信息边界

- NGameOverScreen.OpenSummaryScreen随后异步执行AnimateRunSummary，依次创建／显示分数、徽章、解锁进度和发现；原生View Run在当前版本被Disable，工具没有启用它。
- NBadge在Ready中建立原生标题／描述悬停；NDiscoveredItem使用原生传入的HoverTip。工具转写既有提示，不扩展发现名称上限。
- NEpochSlot.OnFocus对Complete使用IsRevealed=true，其余使用false构造当前标题与解锁要求。工具采用相同条件；hover_tips包括已获得、未获得和已完成的可浏览图标，options只列可揭晓条目及可用导航。这些来源ID不都对应当前可点击选项，不能为修复校验而简单要求每个epoch提示都匹配options。
- 文本与物品使用VisibleUi.Browsable，原生本局详情的滚动范围完整读取；隐藏、透明、内层裁剪及非滚动画外内容仍排除。按钮保留原生可点击判断。卡牌要求ModelVisibility.Visible并沿用BrowsedCard的完整格式；未揭示解锁不补真实内容。
- 截图与结构化调用顺序采样，不宣称同一原子时刻。已查看胜利汇总、时间线及本局详情截图；其文字／图标与对应页面类型一致。本局详情由测试夹具AddChild原生页面，底层汇总仍绘制，不能据此声称正常版本入口可用。

## 已确认的问题与原因

### 1. 公开原因丢失

查看与动作共用的RunResultRequest将Current缺失、页面覆盖和Ready失败合为“The run result is unavailable.”；没有public_message，公开层替换为统一illegal_action。战斗、主菜单及无关时间线的实际MCP结果已复现。纯读取恢复本身正常，修复应集中详情可用性与具体原因，不扩大成通用许可放宽。

### 2. 上下文及full字段校验不足

response-probes.json使用本轮失败首屏的真实原生详情响应作为基线，保留有效内容及令牌，通过外部响应边界副本注入实际GameTools：

| 变体 | 当前公开结果 |
| --- | --- |
| 有效基线 | 接受并发布许可，作为对照。 |
| screen=covered/deck，主体仍visible | 接受、返回矛盾页面并发布许可。 |
| screen=visible/shop | 同上。 |
| screen缺view | 接受并发布许可。 |
| 当前schema的full主体缺hover_tips | 接受缺少字段的详情并发布许可。 |
| hover_tips条目缺description | 接受不完整提示并发布许可。 |

这是故障响应检查，不是正常游戏已输出错误页面的证据。scene_context仅校验通用枚举；inspect_result_details没有跨字段校验。result_details的project会保留已声明且存在的字段，但只检查RESULT基本顶层字段，未要求full新增字段和各条目的完整键集。修复需复用同次上下文及当前协议所需字段，并保留既有旧片段兼容范围的明确边界；完整校验应发生在未来摘要／筛选前。

### 读取与动作就绪共用的限制

not-ready-probe.log用真实汇总副本设为not_ready并禁用选项：基础观察接受，详情解析拒绝。原生执行及工具列表也通过Ready拒绝。该差异由源码及受控副本确认，没有专门动画时序GUI注入。若批准拆开，仍须核对动画中哪些图标已经可悬停；徽章提示当前用全部NBadge节点的位置，基础badges只取可浏览项，也应核验隐藏／淡入节点存在时的来源对应关系，不能直接假设所有动画中内容都可公开。

## 验证结果及失败准备记录

相关Python检查33项通过，0.897秒，覆盖结算输出／摘要及读取错误恢复。首条命令误写了不存在的test_result_observation，30项实际检查通过但整体导入失败；原python.log保留，改用实际test_run_result_summary后通过，未改产品。

GUI读取覆盖7个phase：outcome、summary、tutorial、timeline、epoch、unlock、history；unlock实测包括卡牌、药水、遗物及非物品提示。共五个自有实例：

| 实例 | 核验结果 |
| --- | --- |
| combat／PID80210／53.288秒 | 冷读取错误不授予许可；已有许可的错误读取后直接end_turn成功。之后脚本误以为测试局地图返回按钮可用，close_map被原生禁用而失败；已读结果保留，不将该报告改为通过。 |
| death／PID80209／38.851秒 | 失败首屏及default读取成功；随后错误调用未启用suite的历史准备接口，落入普通拒绝而失败。该实例不算历史核验。 |
| death-pages／PID80721／49.765秒 | 失败首屏、汇总及原生文字不变检查完成；点击文字为Unlock的main_menu后实际进入教程，脚本误判已经回菜单，预期拒绝却得到合法教程详情，因此整体报告失败。 |
| victory_unlock-pages／PID80635／156.709秒 | 胜利首屏、汇总及全部教程／时间线／章节／物品解锁完成；每页详情前后snapshot相同，查看后可直接选择；最终主菜单及重新打开的无关时间线明确拒绝。整体通过。 |
| history-pages／PID81016／68.719秒 | 通过suite的navigation:boss3进入结算，再使用现有原生本局详情夹具；历史读取及10项滚动／隐藏／裁剪／恢复观察检查通过，整体通过。 |

五个进程均已退出；失败报告及日志保留，只将各自完成的读取范围计入证据，未重复已确认的失败首屏及汇总。33项Python、19份真实JSON、有效对照与5种异常响应、not_ready副本检查和10项原生浏览检查分别记录，不合并为“全部GUI报告通过”。

## 未验证边界

未新增每日挑战榜单、多人、所有角色／故事组合、实际模态覆盖、动画时序和禁用悬停故障注入。leaderboard仅依据原生类与当前实现识别；没有本轮完整JSON。右键查看／升级仍按用户TODO留待统一设计，未在本工具提前实现。没有新增TODO、未改工具行为或预设。
