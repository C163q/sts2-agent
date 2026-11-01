# 先古之民入场稳定性修复

## 核对基线

2026-11-01 核对 Linux 游戏 `v0.107.1`（发布提交 `59260271`）、RitsuLib `0.6.10`、代码基线 `30254bc`。问题版本为 Mod `0.34.1`、MCP `0.29.1`；修复版本为 Mod `0.34.2`，MCP 版本与公开工具合同不变。

用户证据位于外部 `playtest-2026-11-01-v5/resume-evidence-final.json` 第 343–347 步：旅行到第二幕佩尔返回正常完成，`inspect_ancient` 中佩尔之血 ID 为 2 且启用；紧接着选择却返回 `stale_state`。失败后只读观察中选项未变，称号由 `null` 变为 `Melting Dragon`。原始对局没有服务端指纹，不能单凭这组回执断言具体字段是根因。

## 原因与复现

隔离实例经原生第一幕 Boss 奖励、前进跨幕及地图旅行进入佩尔房间。旅行返回 `action_completed/complete=true` 时，`AncientInspection.Ready` 已允许选择，但名称横幅的原生动画尚未结束。完整状态随后在没有输入的情况下改变：除指纹外，只有 `ancient.epithet` 从 `null` 变为 `Melting Dragon`。

- `.tmp/2026-11-01-ancient-stability/travel-red-gui/`：真实跨幕捕获到上述变化。详情调用恰好跨过称号出现阈值，随后选择成功，因此该次本身不算动作失败复现。
- `travel-diff.json`：同目录上级保存旅行回执与随后基础状态的完整差异。
- `travel-action-red-gui/`：保存旅行返回的动作令牌，跨过入场窗口后直接选择 ID 2，旧代码实际返回 `stale_state`。这证明已完成旅行返回了尚会自行失效的令牌。
- `red-gui/`：直接构造佩尔房间的对照测试通过；构造完成时动画已经结束，不能作为该问题的失败复现。

目标程序集证据：游戏安装目录下 `data_sts2_linuxbsd_x86_64/sts2.dll` 的 `NAncientEventLayout.InitializeVisuals/ShowNameBanner/SetDialogueLineAndAnimate` 与 `NAncientNameBanner.AnimateVfx`。横幅有独立的 `_tween` 和 `_moveTween`，称号延迟淡入，之后淡出并移动至固定位置再淡入；页面切换另有 `_bannerTween`。原条件只检查布局 `_contentTween`。本次从隔离运行时程序集重新反编译的布局代码保存在 `.tmp/2026-11-01-ancient-stability/NAncientEventLayout.cs`，横幅代码保存在 `/tmp/sts2-ancient-banner.cs`；均与此前核对的同版本源码一致。

## 修复行为

`AncientInspection.Ready` 统一检查布局内容、说明、横幅显隐及名称横幅自身的有限补间。现有 `NonCombatBoundary` 和 `ActionObservation` 会继续推进帧，直至到达正确可行动边界并满足既有稳定区间。入场过程中不会仅因选项按钮可点击就报告可行动。

称号仍从实际可见画面读取，指纹保留所有原字段；不提前暴露尚未显示的信息，不固定睡眠，不自动重新观察或重试动作。详情成功提供新令牌、外部输入使旧令牌失效、覆盖页和重复领取拒绝等规则保持。选牌及父任务暂停仍使用原有 `choice_required` 路径。

持续维护说明原先把“动画时不能选择”描述得宽于实现：原代码只识别内容滚动，漏掉独立横幅。已同步[先古之民说明](../development/ancients.md#状态与验证)和实际等待条件。

## 验证

新建真实 stdio MCP 验证器 `scripts/verify_ancient_stability.py`：

- `travel` 从原生跨幕、旅行及 `inspect_ancient` 续接选择。
- `travel_action` 从精确旅行回执续接，原始回执只为测试提供夹具选项 ID。
- 两者在 0、0.5、1.5、3、5、7、9 秒附近只读采样底层状态，诊断请求不刷新 MCP 令牌；检查旅行与详情令牌稳定、成功领取且无重复遗物，再检查真实外部前进导致 `stale_state`，覆盖页与重复领取返回 `illegal_action`。全程不调用 `get_observation`。
- 原先古验证器适配隔离套件复用，保留对话、多选预览、确认和后续战斗效果断言。

构建通过（0 警告、0 错误）；新 DLL SHA-256 为 `862e6b411ec203275560eb98af26d3228f97a2f9a8e0222c70ba83c4a1064a68`。完整 Python 回归 301 项、无游戏 C# 检查 27 项通过。

首轮 `green-gui/` 中两条旅行及对话共三场通过；佩尔之牙场景的旧验证器在首个观察仍 `enabled=false`、只列查看工具时就断言存在选择动作而失败，没有提交领取动作。验证器改为初始化时限十秒，只读等待公开输入工具出现，原有预览、取消、确认和战斗效果断言保留。`remaining-gui/` 中该场景及此前尚未执行的十四场全部通过。两次运行分别启动一个隔离游戏进程，同一 DLL，合计覆盖默认清单全部 18 个场景、19 个步骤；不是一次完整套件无失败通过。汇总为 `.tmp/2026-11-01-ancient-stability/gui-summary.json`。首轮场景执行 153.69 秒，后续 495.61 秒；两次自有进程均已退出。

独立只读审阅未发现需修复的问题。新增初始化等待不会改变专门旅行测试保留旧令牌九秒且不调用 `get_observation` 的断言。

已核对修改后的 Python 语法、文档相对链接、清单 JSON 及 `git diff --check`。工具名称、参数、提示词和 MCP 版本未修改。

本次只构建并更新隔离测试运行时，未替换正式游戏安装的 Mod；使用修复须退出游戏后安装 `0.34.2` 的 DLL/清单，再完整启动，现有 MCP `0.29.1` 无须为此重连。未推进用户的正式对局，不实现 summary 建议；完整自由游玩通关、其他先古之民的全部动画速度及所有第三方 Mod 组合未验证。
