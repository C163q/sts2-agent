# 终章、胜负结算与解锁核对

核对目标为 Linux `v0.107.1`（分支同名、提交 `59260271`，发布日期 2026-06-18）、Godot 4.5.1、RitsuLib 0.6.10 / compat 0.107.1。游戏程序集为安装目录下 `data_sts2_linuxbsd_x86_64/sts2.dll`，SHA-256 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。反编译、测试存档、截图及报告保留在忽略目录 `.tmp/2026-10-31-run-ending/`；不纳入 Git。

## 源码结论

- `Runs.RunManager.EnterNextAct/WinRun`：第三幕后先进入 `Models.Events.TheArchitect`，其最后选项调用原生跨幕同步器。处于胜利房间时才执行 `OnEnded(true)`，再杀死所有玩家进入结算。
- `Models.Events.TheArchitect`：按角色/访问条件选择对话，`PlayCurrentLine` 显示单个永久气泡。当前行产生 Continue/Respond 或最后的 Proceed；仅最后动作触发胜利。对话的分数伤害动画不是普通战斗操作。
- `Nodes.Screens.GameOverScreen.NGameOverScreen.InitializeBannerAndQuote`：胜利用 `BANNER.falseWin`，伤害包含本次、本人成绩及可用时的全球值。死亡随机选择横幅/语句；工具必须保留已显示选择，不能读取时重新抽签。
- `OpenSummaryScreen/AnimateRunSummary`：两页结算，后页依次显示分数行、徽章、解锁进度与发现图标。`AnimateScoreBar` 的部分分支创建本地补间后直接返回，按钮就绪仍可能早于数字稳定；实现额外跟踪此结算节点创建的原生补间。
- `NRunSummary.GetDiscoveryBodyText`：最多展示十个名称，余项用省略号；工具不越过该边界。
- `OnMainMenuButtonPressed`：有本局发现的 Epoch 时先进入时间线，否则返回主菜单。`NGame.GoToTimeline/ReturnToMainMenu` 负责清理本局。
- `NTimelineScreen/NTimelineTutorial/NEpochSlot/NEpochInspectScreen/NUnlockScreen`：首次教程、点击待揭示章节、章节继续、若干解锁确认、时间线展开、返回菜单。最后一个待揭示条目完成前原生返回按钮禁用。离屏条目用原生 `NSlotsContainer.LerpToSlot` 展示后再点击。
- `NClickableControl.ForceClick` 发送原生 `Released`；章节翻页按钮监听 `MouseReleased`，单独复用它的原生鼠标释放信号。`DebugPress/DebugRelease` 要求焦点，不能当作通用无焦点点击入口。

## 图形比对及修复

实际以中文窗口、英文 MCP 输出逐页对比。已发现并修正：结算首屏的空汇总容器不能用于判断已进入第二页；分数进度的方括号不是 BBCode；原生分数条局部异步动画、人物解锁文字延迟需要等待；未揭示条目可能离屏；发现列表与解锁牌面需要保留完整英文及原生显示上限。

早期无保存调试场景缺少角色统计，导致原生徽章保存失败；测试构造已改为专用隔离存档和可保存对局。此修正限于测试入口，不修改正式存档或原生结算逻辑。原生日志中的资源缓存及测试存档删除提示不能作为正式游戏已经完成验证的证据。

## 验证结果

- 全量 Python 260 项通过（原基线 251 项，新增 9 项终章契约/stdio 测试）；24 项 C# 纯逻辑检查通过；最终构建 0 警告、0 错误。
- `gui-review-green.json`：83 次实际 MCP 调用，第三幕 Boss→建筑师当前两句对话→胜利首屏→汇总→计分跨门槛 `[130/500]`→首次时间线教程→章节、卡牌/遗物/药水/人物解锁→人工返回菜单。随后普通重开时间线仍为非结算入口，结算工具拒绝操作。含两张独立卡牌解锁页，每页均断言三张牌、英文正文及详情；首次未悬停的时间线详情已有相应原生说明。
- `gui-event-final.json`：38 次实际 MCP 调用，事件选项致死、`run_lost`、死亡首屏、汇总、必要解锁、工具返回菜单。
- `gui-death-click.json`：36 次实际 MCP 调用，战斗死亡、两页结算与必要解锁后返回菜单；此轮早于最终时间线生命周期修复，不能替代该修复的专项验证。
- `check-review-evidence.py` 对旧 `gui-victory-all.json` 明确失败（解锁牌面漏读、未悬停说明缺失），对 `gui-review-green.json` 通过；人工返回后普通重开的旧 `gui-scope-red.json` 复现错误识别，新图形场景通过相同检查。独立只读审阅提出 3 项 Important、0 Critical、0 Minor，三项均已针对性修复并验证。

截图与 JSON 在同名报告目录，例如 `gui-review-green/03-summary.png`、`05-unlock-16-unlock.png`、`05-unlock-19-unlock.png`、`06-main-menu.png`；已实际查看图像并与对应数值、卡牌、人物文字核对。截图保持中文，MCP 输出英文；原生资源缓存和清理阶段的 StringName 日志仍存在，未声称游戏日志无警告。

相邻图形回归 `regressions/results.json` 三项通过：茶师动态英文及原生事件前进、第三幕 Boss 到建筑师边界、Trial 确认放弃的 `run_lost`。Markdown 96 份、453 个文件链接无缺失；`git diff --check` 通过。

正式游戏进程未用于构造场景或操作；正式重启加载、所有角色/访问台词、每日挑战榜单、原生当前禁用的查看本局入口、全部历史分页和多人均未完成图形覆盖。相关入口只在原生启用并可见时提供，不强行打开。
