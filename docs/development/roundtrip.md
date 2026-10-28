# 最小流程验证指南

适用于 `spikes/roundtrip/` 中的 Linux 验证原型。已验证的游戏基线为 `v0.107.1`，验证内容是读取状态、通过正常动作队列结束回合、读回下一回合状态。本文说明底层文件协议；agent 接入使用 [本地 MCP server](mcp.md)，当前不是完整的自动游玩工具。

## 前提与构建

- 自行安装 Linux 版《杀戮尖塔 2》。游戏路径通过 `Sts2Dir` 和 `--game-dir` 传入。
- 安装 .NET 9 SDK；本次使用 `9.0.122`，仓库的 `global.json` 允许同系列更高功能带。需要 .NET 9 引用包，单独安装运行时不足以编译。
- 安装 Python 3；本文原有文件客户端和验证脚本只使用标准库，MCP 服务的额外依赖见接入指南。
- 本原型没有 NuGet 包依赖，配置仅使用本地游戏的 `sts2.dll` 与 `GodotSharp.dll`；关闭未使用的传递框架引用下载，原型目录的 NuGet 配置不启用远程源。

在仓库根目录执行：

```sh
env DOTNET_CLI_HOME=/tmp/sts2-agent-dotnet NUGET_PACKAGES=/tmp/sts2-agent-nuget DOTNET_CLI_TELEMETRY_OPTOUT=1 dotnet build spikes/roundtrip/Sts2Agent.csproj -p:Sts2Dir="$HOME/.local/share/Steam/steamapps/common/Slay the Spire 2"
```

```sh
python3 scripts/prepare_roundtrip.py --game-dir "$HOME/.local/share/Steam/steamapps/common/Slay the Spire 2"
```

准备脚本把可执行文件和本项目 Mod 复制到 `.tmp/roundtrip/runtime/`，用符号链接读取原游戏资源，写入独立测试设置。它不在原游戏目录安装 Mod。重新准备前先停止测试实例。运行目录通过 `installation.json` 绑定首次使用的安装位置；更换位置或发现缺少安装记录的非空运行目录时会拒绝操作，应先保留验证证据再重建 `.tmp/roundtrip`。

## 启动与验证

终端一执行：

```sh
python3 scripts/run_roundtrip.py
```

启动脚本设置独立的 `XDG_DATA_HOME`，配合 `override.cfg` 将用户数据放在 `.tmp/roundtrip/userdata/sts2_agent-roundtrip/`。使用已核对的 `--force-steam off` 禁用 Steam 初始化；此实例不使用正式存档或 Steam 云存档。日志写入 `.tmp/roundtrip/stdout.log` 和 `.tmp/roundtrip/game.log`。按 Ctrl+C 停止。

终端二执行：

```sh
python3 scripts/verify_roundtrip.py --ipc-dir .tmp/roundtrip/ipc --report .tmp/roundtrip/evidence.json
```

验证脚本要求从新启动实例的主菜单执行，检查非法动作，创建不保存对局的铁甲战士史莱姆测试战斗，结束一次回合，再核对恰好推进一回合、状态读回、旧状态拒绝及重复请求不再次执行。脚本成功时输出 `PASS`；原始请求结果保存在指定的 JSON 报告中。启动后若仍处于加载阶段，可等待日志出现主菜单完成提示再执行验证。再次运行完整验证前应先重启测试实例。

需要直接观察时：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/roundtrip/ipc get_state
```

准备脚本的安装路径隔离回归检查可单独运行，无须启动游戏：

```sh
python3 scripts/test_prepare_roundtrip.py
```

原型中 `start_test_combat` 和 `end_turn` 都需要 `--expected-state`，其值为最近一次 `--raw` 观察返回的 `state.snapshot_id`；调用形式可参考客户端的 `--help`。动作返回的是执行结束后的状态，而不是仅提交队列时的状态。

## 原型接口

`STS2_AGENT_IPC_DIR` 指定文件通信目录；未设置时，Mod 仅报告加载成功，不启用工具接口。准备脚本与启动脚本面向独立验证实例，启动脚本会设置该变量并启用 `STS2_AGENT_TEST_MODE=1`。

| 操作 | 适用条件与结果 |
| --- | --- |
| `get_state` | 读取主菜单或战斗的有限状态和 `available_actions`；其他场景暂归为 `loading_or_noncombat` |
| `start_test_combat` | 仅测试模式且无进行中的对局时，在主菜单创建临时对局并用游戏开发入口进入指定战斗；该操作不是正常游玩的动作 |
| `end_turn` | 单人战斗、玩家可行动阶段且非暂停状态下，提交 `EndPlayerTurnAction`，等待下一可行动回合或战斗结束 |

请求写入 `requests/<id>.json`，其中 `id` 是不带连字符的 UUID；先写临时文件再原子重命名为 `.json`。请求体包含 `id`、`operation`；动作另带 `expected_state`。响应写入 `responses/<id>.json`，成功包含 `ok: true` 和 `state`，失败包含 `ok: false` 和 `error.code`、`error.message`。

- 文件读写和等待在后台进行，状态读取与动作提交在 Godot 主线程进行；当前串行处理请求。
- `snapshot_id` 根据当前导出的观察内容、进程会话和战斗代次生成。动作在同一主线程片段中核对令牌和合法性后提交，避免使用旧观察执行动作；这不是对所有游戏内部状态的完整版本标识。
- 相同请求 ID 且缓存响应仍在时返回原结果。重复请求不分配新 ID；删除响应缓存后不再保证同一 ID 不会再次执行。
- `stale_state` 表示缺少或不匹配的状态令牌，`illegal_action` 表示当前不可执行，`invalid_request` 表示请求格式有误，`expired_request` 表示执行前已过期，`game_error` 表示游戏调用异常。
- `timeout` 或客户端超时后，动作是否已执行可能不确定。应先重新观察，不能自动换一个 ID 重试动作。创建测试场景过程中发生错误也可能已经部分推进游戏。

## 验证边界

底层动作流程已在独立实例中实测；无头启动存在 FMOD 音频初始化、音频资源及虚拟渲染器警告，不覆盖声音。图形观察的验证范围另见战斗观察说明，不能将无头验证描述为没有运行警告。

原型已扩展可见战斗观察，字段与验证方式见 [战斗观察 JSON](observation.md)，范围按 [可见信息边界](../observation.md) 维护；未展开的手牌效果以后由专门查看调用提供。动作仅支持结束回合；已增加并验证 stdio MCP 工具桥接，出牌、地图推进、多玩家、断线恢复和异常退出恢复尚未覆盖。通信目录假设仅由可信的本地程序访问，不作为远程服务。

API 核对依据与实测结果见 [验证记录](../research/2026-10-28-roundtrip-validation.md)。
