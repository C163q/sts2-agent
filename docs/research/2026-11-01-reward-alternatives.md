# 佩尔之翼献祭与浮木重掷核查

## 基线与原生接口

2026-11-01 核对代码 `edefba1`、Linux 游戏 `v0.107.1`（发布提交 `59260271`）、RitsuLib `0.6.10`、MCP `0.30.0`。原 Mod 为 `0.34.2`，本次修复为 `0.34.3`；工具数量、参数、schema 与 MCP 提示词不变。

当前游戏程序集 `data_sts2_linuxbsd_x86_64/sts2.dll` 的相关类型已重新反编译至 `.tmp/2026-11-01-reward-alternatives/source/`，未纳入 Git：

- `PaelsWing.TryModifyCardRewardAlternatives` 添加 `SACRIFICE`，其 `OnSacrifice` 累计献祭并在每两次时通过 `RelicCmd.Obtain` 获得遗物。
- `Driftwood.TryModifyRewardsLate` 为卡牌奖励设置 `CanReroll`；`CardRewardAlternative.Generate` 因此添加 `REROLL`。
- `CardReward.Reroll` 关闭当前奖励的重掷许可并重新生成候选；`NCardRewardSelectionScreen.RefreshOptions` 更新原生按钮与卡牌。
- 既有 `CardSelection.Options` 已正确读取原生替代选项和按钮，以 `skip` 或 `alternative:N` 输出；`SelectionRequest` 点击原生按钮。不需要新增专门的献祭或重掷工具。

## 实测发现与修复

两个按钮均能在基础观察和 `inspect_selection` 正确显示，并可通过 `selection_option` 点击。单独检查按钮存在性仍不足以发现后续状态问题：

旧生产实现加隔离夹具后的 `gui/` 测试中，第二次献祭已经移除卡牌奖励并获得遗物，返回 `action_completed/complete=true`；随后没有输入，佩尔之翼可见计数从 `2` 变为 `0`，指纹随之变化，其他观察字段不变。该用例因稳定性断言失败。进一步 `pael-red/` 保留原动作许可、只读采样后直接 `proceed`，实际返回 `stale_state`。

原因是 `PaelsWing.DoActivateVisuals` 独立设置 `_isActivating`，等待后恢复；`DisplayAmount` 在激活期间显示 `2`，结束后显示累计次数模二的进度。`NRelicInventoryHolder.OnDisplayAmountChanged` 立即刷新可见文本。原等待器只识别金币和药水资源过渡，没有涵盖这一独立任务。

`RunUi.ResourceMotionPending` 新增原生遗物入栏 `_obtainedTween`，以及佩尔之翼 `_isActivating` 的有限等待。读取位于游戏线程，检查 holder 已就绪且未待删除；不改写计数、不提前暴露值、不忽略指纹、不固定睡眠或自动刷新重试。普通完成沿用统一等待器，`choice_required` 仍先返回，不等待依赖玩家输入的父任务。

## 验证

新增 `reward:paels_wing`、`reward:driftwood` 测试夹具，实际获得对应遗物，再由原生 `RewardsSet` hook 处理两份卡牌奖励。没有手工设置重掷许可或模拟献祭结果。`RewardFixture.Read` 的累计次数只用于测试模式原始协议，不增加公开观察字段。

`green-gui/` 三个场景全部通过：

- 佩尔之翼：两份奖励均显示 `Skip` 与 `Sacrifice`；献祭不增加卡牌，累计次数为 1、2，第二次真实获得遗物；原始只读采样不刷新 MCP 许可，两次献祭后均保持令牌稳定，并能直接继续领取或前进。
- 浮木：显示 `Skip` 与 `Reroll`；每份奖励重掷一次，候选对象/ID 更新，按钮消失；旧按钮和旧卡 ID 返回 `illegal_action`。第二份重掷后跳过、重新打开仍只有 Skip；选择新卡时才加入牌组。
- 普通奖励：既有领取、跳过重开、选卡、遗物和前进流程回归通过。

已目视检查浮木重掷前后的截图，原生 `Reroll` 按钮及其消失与结构化输出一致；献祭截图经独立审阅确认实际显示 `Sacrifice`。截图在各场景 `verify/screenshots/`。

修复 DLL SHA-256：`1f19829fa10031423b2c8215ab092c1fea42afea56a0b458dff4ea2d985da3d3`。构建通过，0 警告、0 错误。`nested-gui/` 中额外的 Calling Bell 嵌套奖励及 Astrolabe 遗物后续选牌两场通过，确认共享资源等待不会阻塞这些父任务暂停时的玩家输入。与 `green-gui/` 合计五个场景、五个步骤通过，分别使用一个自有进程，同一修复 DLL；均已退出，汇总为 `gui-summary.json`。最终 Python 回归 318 项通过（41.112 秒），无游戏 C# 检查 27 项通过；日志分别为任务目录下的 `python-final.log`、`csharp-final.log`。独立只读审阅未发现需修复的问题。

## 组合及验证边界

两个遗物分别实测，不宣称合用已经通过。目标版本原生 `CardRewardAlternative.Generate` 对超过两项的替代列表抛异常；在默认允许 Skip、CanReroll 为 true 且佩尔之翼仍添加献祭的条件下会形成三项。这是原生生成逻辑的约束，未在本次隔离实测中组合触发，也不通过 MCP 隐藏或重写原生列表规避。

另一个 agent 的正式游戏、IPC 与已安装 `0.34.2` 均未修改，没有启动/停止其进程。新修复仅构建并用于隔离验证；须待正式游戏退出后再安装 `0.34.3`，MCP `0.30.0` 无须为此更换。未覆盖所有遗物组合、随机遗物后续界面或第三方 UI。
