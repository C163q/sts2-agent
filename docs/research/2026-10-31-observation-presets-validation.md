# 观察预设与当前可用工具核查

当前状态：验证完成。275 项 Python、24 项 C# 检查及 15 类隔离图形场景、228 次真实 MCP 调用通过；Mod 0.31.0 已备份安装，正式游戏重启加载未验证。

## 基线与证据

核对日期为 2026-10-31 至 2026-11-01；代码基线 `ad66933`。目标 Linux 游戏 `v0.107.1`，游戏安装目录下 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`，RitsuLib `0.6.10`。交付版本 Mod `0.31.0`、MCP `0.27.0`、schema `16`，工具目录仍为默认 42 项、启用截图后 43 项。

全部临时证据位于 `.tmp/2026-10-31-observation-presets/`，不纳入 Git。现行接口以[观察输出预设](../development/observation.md#mcp-输出预设)及[MCP 语义](../development/mcp.md#调用和错误语义)为准。

## 核查结论

原实现按游戏实时状态列出动作，但没有列出详情、眼睛与页面关闭工具，Python 又限制为游戏动作白名单。原版真实 MCP 的 `gui-red.json` 在普通战斗中复现 9 个查看工具缺失。新实现将这部分判断集中到 `GameAdapter.AvailableTools.cs`，手牌、双方状态、地图、牌组和牌堆的可用性条件与实际调用入口复用。

`actions_only` 是完整状态校验之后的 MCP 输出投影，不改变底层文件读取、游戏 UI、动作输出或内部令牌。占卜原图仍在内部校验，精简结果不携带图像。列表扩展后，动作续接改为必须包含实际游戏动作，防止只有详情工具时仍因列表非空而续接；对应 `python-permission-red.log` 到 `python-permission-green.log`。

独立只读审阅发现 0 Critical、1 Important、0 Minor。Important 是非战斗地图的药水详情/目标查询由游戏端列出，却被 Python 地图专属白名单拒绝。`python-map-red.log` 与 `python-map-epilogue-red.log` 复现后，白名单与游戏端入口统一，地图清理列表不再抹掉合法药水操作。建筑师对话保留相同的原生顶栏工具；其视觉战斗背景允许当前可见界面、对象和遗物详情，不放行普通出牌。图形复验另发现 `close_map` 的旧返回校验未接受 `epilogue` 查看页，已补充恢复当前对话的回归，见 `python-close-epilogue-red.log` 与 `python-close-epilogue-green.log`。战斗药水提交还同步检查现有 RitsuLib 激活前提，目标查询不要求该依赖。

原生页面依据沿用当前目标版本的调用入口与反编译产物：`NMapScreen.Open/Close`、`NTopBar`、`NPotionHolder`、`NPlayerHand`、卡牌选择屏幕、`TheArchitect` 与 `NGameOverScreen`。地图、选牌和终章源码位置另见[地图验证](2026-10-31-map-travel-validation.md)、[选牌验证](2026-10-30-card-selection-validation.md)及[终章验证](2026-10-31-run-ending-validation.md)。本次还核对 `source/CombatManager.cs:IsPlayerReadyToEndTurn`，确认视觉战斗背景的界面详情读取不会依赖活跃战斗回合。本次没有猜测新游戏 API。

## 自动检查

- 原基线 260 项 Python 检查通过；新增 15 项后，全套 275 项通过，见 `python-final-delivery.log`。
- 新增检查覆盖默认与显式 full 兼容、手牌选择精简上下文、完整校验、非法预设不请求游戏并清除令牌、精简后实际动作/过期状态、占卜图像投影、公开工具过滤去重、地图与结算专属边界，以及真实 stdio schema/结果。
- C# 无游戏检查 24 项通过，见 `csharp.log`；最终编译 0 警告、0 错误，见 `build-final.log`。

## 图形验证

只启动自有隔离测试进程，使用测试数据目录及 IPC；每例由启动脚本在 finally 清理自己的游戏进程。截图使用独立目录，不覆盖旧文件。

`matrix.json` 与 `verified-reports.json` 记录全部 15 类成功场景及 228 次调用：战斗、普通选牌、武装升级、奖励、休息处、宝箱、商店、先古之民、事件、确认框、占卜、选路地图、胜负结算、地图药水和建筑师。对应 `gui-*.json` / `gui-final-*.json` / `gui-ready-*.json` / `gui-complete-*.json` 记录真实 stdio MCP 调用，截图目录与报告同名。每个页面核对 full/actions_only 上下文及工具列表一致，所有已列出的无参数详情工具实际调用成功。战斗另外真实打开/关闭牌组、牌堆、地图；选牌和武装升级另外核对查看战场、覆盖页与返回候选。

验证脚本的前提错误均保留证据：Trial 初始页没有致死警告，须先 Reject，再进入拒绝分支；修正后首次续跑复用截图路径被工具正确拒绝 `file_exists`。最终改用全新 `gui-final-*` 路径，并增加报告/截图目录存在性保护。非战斗地图药水夹具还会触发原生入幕动画，须仅读等待 `inspect_map` 就绪后再断言稳定页面；动画期间保留可用药水工具，不虚构地图入口。以上均未通过修改生产逻辑规避。

## 限制

没有连续完成整局游戏，也未穷尽全部事件、遗物、选牌与遮挡组合；任意第三方页面和多人不在本次保证范围。RitsuLib 失活的异常分支按现有入口条件核对，未注入运行时验证。正式游戏加载需要完整重启，MCP 更新需要重连。

安装前核对旧 0.30.0 与已测新产物哈希，备份位于 `.tmp/mod-backups/2026-11-01-002316-observation-presets/`。DLL SHA-256 为 `a3fc780b320df870c58e59a4dfe7e2adec2137857b583d2c4332e95b03fe9e8b`，清单为 `295363102575655d8104238430645ec42a89e887b11cb871d0070d794a0c2bfc`；未修改 RitsuLib、正式存档或操作正式对局。
