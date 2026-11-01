# 选择详情输出预设验证

本次验证完成：Python 完整回归 344 项通过，13 个独立图形场景通过；两次奖励场景清理失败已定位并修正验证器，失败证据保留。生产改动仅涉及 Python 预设、schema 与分派。

## 基线与实现范围

核对日期为 2026-11-01；Linux 游戏 `v0.107.1`、release `59260271`，Mod `0.35.0`，RitsuLib `0.6.10`，MCP server `0.33.0`，Python `3.14.8` 与 MCP SDK `1.26.0`。本次只改 Python 输出，不新增游戏 API 调用或修改 Mod DLL。测试沿用已经构建的隔离 DLL，SHA-256 为 `c7b0f7e4590069dfa834ac0bbd80a560be2160cb2578b10be10bbdecda3242d2`。

公开契约见[选择预设](../development/card-selection.md#mcp-输出预设)。`card_summary.py` 统一手牌与选择详情的卡牌字段；`selection_presets.py` 处理参数及全部卡牌路径，完整原生数据仍先经 `inspect_selection_details` 验证。底层无参数请求、状态令牌、UI 及动作合法性规则保持原有职责。

## 自动检查

新增 9 项测试先在旧实现失败：旧 `inspect_selection` 不接受参数，stdio schema 也没有预设。实现后全部通过，完整 Python 回归共 344 项通过，耗时 43.419 秒。

检查包括默认及显式完整输出兼容、全部候选与包内卡牌、单牌和多牌预览结构、随机变牌 `after:null`、可见附魔及隐藏计数、无星耗省略、空结果页、非法参数不请求游戏、原生错误、损坏完整数据拒绝，以及摘要后直接选择。真实 stdio 校验工具 schema、分派、42 个工具数量及文本/结构化 JSON 一致。

独立只读审阅未发现 P0–P3 问题；另行直接投影检查通过。审阅者的独立异步测试受沙箱事件循环限制未完成，不能计入通过数量；完整测试由主执行环境在沙箱外限时运行。

## 图形证据

使用 `verify_selection_presets.py` 和全新隔离运行目录，真实 stdio MCP 驱动原生选择，不连接正式游戏、IPC 或存档。每个输入边界对照默认完整与显式完整，再核对摘要；通过场景的读取前后完整原生状态相同，摘要直接授权下一次选择或确认。

13 个场景最终均通过，覆盖当前 12 类选择：小型候选、奖励、网格、战斗牌堆、牌组、手牌、手牌升级、牌组升级、附魔、随机变牌、卡牌包及结果页。奖励分别验证献祭和重掷；网格使用 40 张牌并点击末尾候选，手牌升级检查眼睛隐藏时摘要被拒绝、返回后可以继续确认，多张附魔检查三个预览。火堆预览已确认后实际完成锻造，不只检查输出存在。

首轮 `gui/` 的前 7 场景通过，献祭步骤也通过，但局间清理超时；第二轮 `remaining-gui/` 增加前进后仍在同一清理处超时。新验证器最初只处理两份奖励中的一份，原生终端奖励前进只打开地图，未离房时 `RewardsSet.Offer()` 仍等待剩余项；`GameAdapter.Testing.cs` 会等待该夹具任务结束。验证器改为正常领取第二份奖励后再前进，与既有奖励验证器一致；没有修改 Mod 清理逻辑或重试失败动作。两个失败目录均保留，剩余场景在第三个新目录 `completed-rewards-gui/` 执行。原生依据为目标版本 `sts2.dll` 的 `NRewardsScreen.OnProceedButtonPressed`、`RewardsSetSynchronizer.CompleteRewardsSetIfNecessary/BeforeLeavingRoom`，已有对应反编译证据位于 `.tmp/2026-10-31-rewards/source/`。

共启动三个隔离进程；成功用例分布在首轮的 7 个与第三轮的 6 个，第三轮套件整体通过。不能将首轮、第二轮的整体结果称为通过。各进程均已退出，未替换测试 DLL。

证据位于未纳入 Git 的 `.tmp/2026-11-01-selection-presets/`：

- `python-red.log`、`python-green.log`、`python.log`：失败基线、新增测试和完整回归。
- `suite.json`、`gui/report.json`、`remaining-gui/report.json`、`completed-rewards-gui/report.json`：图形清单及结果；各场景 `verify/evidence.json` 与 `screenshots/` 保留调用和画面。
- `smith-summary-preview.json`：火堆选中痛击后，尚未确认锻造的完整 MCP 摘要 JSON。此时 `cards:[]`，两侧原牌 ID 相同，正文均省略，返回和确认按钮可用。对应 `gui/smith/verify/screenshots/preview.png`。

未执行完整默认图形冒烟集、完整自主通关或任意第三方选择页测试；摘要投影不扩大原先已支持的选择类型，也不补齐基础观察或随机结果。正式安装目录未更新。
