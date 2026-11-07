# 占卜工具视图切换实施记录

> 当前状态：实现与验收完成，共1项，已完成1项；9类GUI和样本核对通过。独立最终审阅及合入待完成，无阻塞。

定稿见[工具切换审阅](2026-11-07-set-divination-tool-review.md#输出定稿)，步骤见[实施计划](../superpowers/plans/2026-11-07-divination-tool-view.md)。原错误及十二份旧JSON保留于[开发核验](2026-11-07-set-divination-tool-development-notes.md)。

## 行为与职责

- 可在当前可交互棋盘上直接调用set_divination_tool，无需先取得观察许可。成功仅返回scene、screen、available_actions，刷新许可；不返回transition、事件或图片。重复选择当前工具成功且不重复点击，不消耗次数或改变棋盘／资源。
- 明确未交互的无棋盘、覆盖、等待、已结束及参数拒绝公开具体原因，保留已有许可；首次失败不授权揭开。UI已交互、上下文改变、未知／坏响应及矛盾执行保证不恢复旧许可。
- 执行、tools[].enabled与available_actions共享检查；成功前确认仍属同一对局、棋盘及所选工具。divine仍核对状态令牌、消耗次数、记录变化并返回动作回执。
- tool枚举与default/full保留，不新增summary、操作参数或测试专用原生路由。文字棋盘、图案识别及图片策略保持。

[GameAdapter.Divination](../../src/Sts2Agent/Adapter/GameAdapter.Divination.cs)拆出SetDivinationTool：参数和前置条件拒绝提供ui_unchanged:true，必要时UiChanged后原生ForceClick，SettledObservation后再核对上下文和工具，返回Success。切换从RecordedActions移除；divine沿原分支执行。

[DivinationInspection](../../src/Sts2Agent/Observation/DivinationInspection.cs)共用PageUnavailableReason，另提供ToolSwitchUnavailableReason、ToolUnavailableReason与SelectedTool。Ready独立，保持揭开／任务／资源等待；按钮交互使用有效鼠标／焦点状态。详情静态显示范围保持。[工具注册](../../src/sts2_mcp/tool_registry.py)为无需已有许可的view，使用actions_only投影及现有unchanged_view_rejections，公共JSON不暴露执行证明。

## 基线与证据

- 项目基于e460a03；Linux游戏v0.107.1/release59260271，RitsuLib0.6.10、Godot4.5.1。目标程序集路径及哈希见开发核验，未更换目标。
- Mod0.77.0、MCP0.79.0、schema45；基础观察形状不变。新MCP与Mod配套使用；旧Mod仍要求工具切换的expected_state，会拒绝无旧令牌的请求。
- 最终构建及隔离运行时DLL均为f811e016623541167b17fdbc6edab13fb6cba2f95273be225126b0dea7901c4d。证据根`.tmp/2026-11-07-divination-tool-view/`；没有正式安装或推送。

## 验证

| 检查 | 结果与证据 |
| --- | --- |
| Python RED | 新5项出现4处失败，0.055秒，旧策略阻止冷切换或拒绝恢复；python-red.log |
| GUI RED | 旧DLL的playing首次公开切换返回observation_required，21.481180198秒；PID15069已退出，gui-red/report.json |
| Python GREEN | 新5项通过，0.057秒；python-green.log |
| 首轮完整Python | 786项中9处旧预期失败，38.098秒；default/stdio仍期望transition共6处，形状检查仍把transition当必填共2处，文件客户端预期包含transition共1处；python-full.log |
| 最终完整Python | 按视图定稿迁移断言后786项通过，39.046秒；python-final.log。冻结JSON未改，畸形检查转为必需观察字段 |
| C# | 145项通过；csharp.log |
| 构建 | 5.73秒，零编译警告／错误；build.log |

新Python验证直接冷切换→揭开、actions_only、明确拒绝保留已有许可、冷拒绝不授权、本地非法参数、过期／未知／已交互／矛盾保证和坏响应清除许可。公共契约及文件客户端旧样本只迁移预期，不覆盖历史JSON。

GUI专项为无棋盘、正常棋盘、结束、奖励和选牌覆盖。正常棋盘由测试在MCP会话创建前原生打开，第一次公开调用即切换，随后直接divine；另核对重复请求不点击／令牌不变、default、无效参数、地图／牌组覆盖和连续切换。原始视图请求不依赖旧令牌；divine继续使用严格令牌。

奖励和选牌由实际揭开并耗尽次数后产生；私有夹具用于选择覆盖目标。直接原生读回明确关闭图片，不刷新MCP许可，核对被拒请求的令牌不变。相关回归覆盖事件详情、自然揭开与发奖、事件选择恢复及媒体捕获失败后已改变UI的错误。

最终9类GUI在同一自有进程全部通过，264.576863063秒；142次MCP、47次直接原生检查，运行器创建／重置请求不计。PID16739已退出；gui/report.json及各verify/evidence.json保留过程与公开／原生结果。

[十三份实际样本](2026-11-07-divination-tool-view-examples/README.md)为十二份full、一份default；逐份核对源报告行和SHA-256。verify_delivery.py核对日志、最终DLL、版本、相对链接及进程退出，未重复构建。

## 未验证范围与交接

没有新增多人、第三方棋盘、任意人工并发切页、真实超时及工具按钮异常隐藏／禁用的GUI验证；相关就绪和生命周期检查按源码核对。没有穷尽全部奖励组合，未知结果不自动重试。

独立最终审阅及合入待完成，工具尚未核销；只更新既有错误恢复／提示待办的已覆盖工具范围，未增加用户TODO。
