# 地图选路与跨幕调研、验证

当前记录：功能、11 个导航图形场景和 3 个相邻回归均已完成；正在提交及备份安装。正式游戏重新加载尚未验证。

## 目标版本与源码证据

核对日期 2026-10-31；Linux 游戏 v0.107.1，分支 v0.107.1，提交 59260271，Godot 4.5.1，RitsuLib 0.6.10。游戏目录相对程序集 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。反编译仅保留于 Git 忽略目录，不作为上游稳定 API 承诺。

| 证据 | 核对结论 |
| --- | --- |
| `.tmp/decompiled/NMapScreen.cs`：RecalculateTravelability、OnMapPointSelectedLocally、TravelToMapCoord | 原生节点状态决定候选；点击发起 VoteForMapCoordAction，旅行包含动画、EnterMapCoord、房间入场与清理 |
| `.tmp/2026-10-31-rewards/source/Nodes.Screens.Map.NMapPoint.cs`：OnRelease | ForceClick 仍经过原生地图合法性判断；绘图与旅行期间不选路 |
| `.tmp/decompiled/MapTravel.cs` 与 `.tmp/2026-10-31-ancients/source/WingedBoots.cs` | 飞鞋开启自由选路 Hook，提供下一排全部节点；原生 AfterRoomEntered 只对离开原连线的路线消耗次数 |
| `.tmp/decompiled/NRewardsScreen.cs`：OnProceedButtonPressed | 双 Boss 第一个 Boss 后走普通地图；每幕最后 Boss 后通过 ActChangeSynchronizer 前进 |
| `.tmp/2026-10-31-map-travel/source/ActChangeSynchronizer.cs` | 原生单人投票后异步 EnterNextAct，复用原按钮即可触发跨幕 |
| `.tmp/decompiled/RunManager.cs`：EnterNextAct、EnterAct、ProceedFromTerminalRewardsScreen | 下一幕先进入 MapRoom；最后幕后进入 TheArchitect；普通事件战斗可返回父事件 |
| `.tmp/2026-10-31-map-travel/source/EventSynchronizer.cs`：Events、GetLocalEvent | EventRoom 已切换而 Events 尚为空时直接读 LocalMutableEvent 会越界；观察器须先检查当前玩家事件槽位已建立 |
| `.tmp/2026-10-31-map-travel/source/ScrollHelper.cs` | 鼠标滚轮固定每次 40，忽略 Factor；触控板 Delta.Y 按 50 倍转换为原生滚动距离 |

## 接口与边界

现行契约以[地图接口](../development/map-inspection.md#地图选路)为准：新增 travel_to_node，基础观察提供候选摘要，完整地图仍按需查看。公开动作点击原生节点，不直接写路线或进入房间；未领取奖励由离房流程放弃。

跨幕实测曾暴露两项问题：新幕地图入场未 Ready 时误判人工界面；事件房初始化前读取玩家事件导致越界。前者区分已展开地图与未知页面，后者统一使用有界的当前玩家事件读取，覆盖先古、普通事件和假商人。记录保留在 `.tmp/2026-10-31-map-travel/boss1-run1.json`、`boss1-diagnostic.json`；前两幕修复验证为 `event-init-green-boss1.json`、`event-init-green-boss2.json`。

## 验证范围

完整 Python 检查已由 244 项增加至 251 项；新增规范 ID、地图摘要过滤、候选一致性、飞鞋非连线候选、许可续接、损坏输出和错误参数拒绝。完整日志 `.tmp/2026-10-31-map-travel/python-final.log`；C# 24 项通过，见 `csharp.log`。

图形验证使用一次性独立游戏与真正 stdio MCP，原生中文 UI，面向模型输出英语。第一幕与第二幕 Boss 使用隔离夹具通过原生击杀结束战斗后，实测前进进入下一幕并点击起点进入先古之民。第三幕空奖励前进到 TheArchitect 已确认 manual_input_required。飞鞋最后一次非连线旅行和耗尽后限制已确认，证据 `flight-run1.json`。11 个导航场景共记录 199 次调用，汇总见 `.tmp/2026-10-31-map-travel/gui-cases.json`。

| 图形场景 | 实际验证 |
| --- | --- |
| boss1 / boss2 | 原生 Boss 奖励前进，等新幕地图就绪，拒绝旧令牌/旧幕 ID，并进入先古之民 |
| boss3 | 空终结奖励页前进到 TheArchitect，返回 manual_input_required |
| double | 第一 Boss 后地图仅允许第二 Boss，滚动露出并点击；第二 Boss 胜利后进入下一幕 |
| basic / flight | 保留奖励时打开地图，关闭/绘图/旧状态拒绝，真实滚动后选路；未领奖励放弃、金币未增加；连线不耗飞鞋，最后跳线耗尽后恢复连线限制 |
| combat / choice | 原生进入战斗；ChoicesParadox 首回合选牌及时返回，选择后 player_ready |
| shop / treasure / unknown | 进入商店、未开宝箱和实际问号事件，返回各自可操作观察；不自动购买/开箱/选择事件 |

双 Boss 初次滚动失败记录为 `event-init-green-double.json`；修复后 `navigation-green-double.json` 通过。滚动改用目标版本触控板事件，保留原生缓动与边界，不直接挪动地图容器或改写游戏状态。数组/标量原始参数由既有 FileMailbox 在入队前拒绝，新图形覆盖也已确认。

普通事件、占卜查看/关闭地图和 Trial 确认取消的 3 个相邻图形回归通过，证据为 `.tmp/2026-10-31-map-travel/regressions/results.json`。编译 0 警告、0 错误；运行日志仍有原生资源未缓存、退出时静态 StringName 清理提示等，不能据此宣称游戏日志无警告或错误。

独立只读代码审阅未发现 Critical、Important 或 Minor 问题，独立运行地图摘要 4 项通过；没有独立启动游戏、编译或重跑全套测试。不把源码核对、夹具胜利或编译通过表述为 LLM 已自主完成整场 Boss 战。

尚未验证：正式游戏重启后的加载、LLM 自主跨幕试玩、完整自然 Boss 战、多人及所有遗物组合。终章 TheArchitect 与结局操作仍未实现。
