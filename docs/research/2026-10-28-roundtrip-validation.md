# 状态与动作最小流程验证记录

核对日期：2026-10-28。当前结论：最小流程已在真实游戏的独立无头实例中通过。覆盖 Mod 加载、外部状态读取、合法结束回合及结果读回；未覆盖出牌、完整对局和 LLM 接入。

## 核对基线

- 游戏：Linux Steam 安装，`release_info.json` 记录 `v0.107.1`，分支 `v0.107.1`，提交 `59260271`。
- 引擎：本地可执行文件 `--help` 和启动日志报告 `MegaDot 4.5.1.m.12.mono.custom_build`。
- 工具：.NET SDK `9.0.122`，ILSpyCmd 与反编译器 `11.2.0.10050`；Python 脚本使用标准库。
- 实现：`spikes/roundtrip/` 的 C# DLL，使用原生 Mod 加载，不引入 BaseLib、RitsuLib 或 Harmony 补丁。
- 游戏副本、符号链接、反编译结果、运行日志及测试存档均位于 Git 忽略的 `.tmp/` 下。

## 目标版本接口依据

下列类型均从本地游戏安装目录的 `data_sts2_linuxbsd_x86_64/sts2.dll` 定向反编译核对，未将反编译源码纳入仓库。Godot 绑定通过同目录的 `GodotSharp.dll` 编译和运行核验。

| 类型或成员 | 核对结果及本次用途 |
| --- | --- |
| `ModManifest`、`ModManager.TryLoadMod` | 清单可设置 `has_dll: true`、`has_pck: false`；DLL 文件名与 Mod ID 一致 |
| `ModInitializerAttribute`、`ModManager.CallModInitializer` | 标注类型并指定静态初始化方法，由游戏加载时调用 |
| `ModSettings`、`SettingsSave` | `mod_settings.mods_enabled` 为启用加载的设置；本版本设置结构版本为 5 |
| `NGame.InitializePlatform` | `--force-steam off` 可跳过 Steam 初始化，用于独立测试实例 |
| `UserDataPathProvider` | 用户数据在 `user://` 下按平台、用户、Mod 状态和配置档分层；实测根目录由独立启动配置确定 |
| `SceneTree.ProcessFrame` | 主线程处理外部请求；后台任务仅做文件通信 |
| `CombatManager.DebugOnlyGetState`、`LocalContext.GetMe` | 获取当前战斗与本地玩家；仅用于读取 |
| `NEndTurnButton.CallReleaseLogic` | 游戏按钮通过 `ActionQueueSynchronizer.RequestEnqueue` 提交 `EndPlayerTurnAction` |
| `EndPlayerTurnAction` | 构造参数为玩家和回合号；执行时再次核对回合号，再交给游戏正常结束回合流程 |
| `NGame.StartNewSingleplayerRun` | 可指定 `shouldSave: false`，用于创建测试对局 |
| `RunManager.EnterRoomDebug`、`CombatState` | 开发入口可进入指定遭遇；`CombatState` 要求可变遭遇实例，测试入口使用 `ToMutable()`；此入口不用于正常游玩 |

## 实测结果

构建结果：0 个警告、0 个错误。准备脚本、启动脚本和客户端均在仓库根目录执行；复现命令见 [验证指南](../development/roundtrip.md)。

| 检查项 | 结果 |
| --- | --- |
| Mod 加载 | 日志确认发现清单、加载 DLL、调用初始化方法，成功加载 1 个 Mod，并连接主线程处理入口 |
| 数据隔离 | 日志中的用户数据根目录为 `.tmp/roundtrip/userdata/sts2_agent-roundtrip`；Steam 初始化已跳过 |
| 主菜单读取 | 返回 `main_menu` 与测试场景创建动作 |
| 主菜单结束回合 | 返回 `illegal_action` |
| 临时战斗读取 | 铁甲战士，玩家回合 1，生命 80，能量 3，5 张手牌；敌人为 3 只史莱姆 |
| 无效令牌 | 返回 `stale_state`，随后观察的状态未改变 |
| 合法结束回合 | 游戏日志显示敌人正常行动；玩家回合从 1 推进到 2，生命从 80 变为 73 |
| 执行后读取 | 再次读取的 `snapshot_id` 与动作响应中的状态一致 |
| 旧状态动作 | 使用回合 1 的令牌返回 `stale_state` |
| 重复请求 | 重用已完成请求的 ID 返回缓存结果，随后读回仍为回合 2 |
| 安装位置变更 | 回归检查确认更换游戏安装位置时准备脚本拒绝操作，原可执行文件、资源链接和安装记录均保持原样 |

本地原始证据为 `.tmp/roundtrip/evidence.json`、`.tmp/roundtrip/game.log` 和 `.tmp/roundtrip/stdout.log`。这些文件不纳入 Git；重复执行会更新它们。

## 限制

无头环境存在 FMOD 音频初始化与资源警告，以及虚拟渲染器警告；没有验证声音和画面。测试使用开发入口准备战斗，然后通过正常动作队列结束回合；没有证明从主菜单完整推进一局的自动化能力。当前观察仅包含有限字段，尚不足以完整支持 LLM 决策，其他游戏版本及社区库兼容性也未验证。
