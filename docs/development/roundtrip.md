# 最小流程验证指南

适用于 `src/Sts2Agent/` 中的 Linux 验证原型。版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。本指南的最小验证内容是读取状态、通过正常动作队列结束回合、读回下一回合状态。本文说明底层文件协议；agent 接入使用 [本地 MCP server](mcp.md)，当前工具能力见[项目 README](../../README.md#当前能力)。

## 前提与构建

- 自行安装 Linux 版《杀戮尖塔 2》，按 [README 配置路径](../../README.md#开发与运行入口)，在当前终端加载 `.env`。游戏路径通过 `Sts2Dir` 和 `--game-dir` 传入。
- 按 [global.json](../../global.json) 安装兼容 SDK，需要对应的 .NET 引用包，单独安装运行时不足以编译。
- 安装 Python 3；本文原有文件客户端和验证脚本只使用标准库，MCP 服务的额外依赖见接入指南。
- `RitsuLibDir` 指向兼容 RitsuLib 的完整目录，可直接使用 Steam 创意工坊安装。手工获取时按[README 中的发布包说明](../../README.md#当前版本与前提)下载并解压；目录须直接包含 `RitsuLib.References.props`、`mod_manifest.json`、根 DLL、`assets.zip`、`shared/` 和匹配的 `compat/` 子目录，不能只复制根 DLL。
- 构建引用上述本地库与游戏自带程序集，不下载 NuGet 包；[NuGet.Config](../../src/Sts2Agent/NuGet.Config)不启用远程源。

在仓库根目录执行：

```sh
env DOTNET_CLI_HOME=/tmp/sts2-agent-dotnet NUGET_PACKAGES=/tmp/sts2-agent-nuget DOTNET_CLI_TELEMETRY_OPTOUT=1 dotnet build src/Sts2Agent/Sts2Agent.csproj -p:Sts2Dir="${Sts2Dir:?请先配置并加载 .env}" -p:RitsuLibDir="${RitsuLibDir:?请先配置并加载 .env}"
```

```sh
python3 scripts/prepare_roundtrip.py --game-dir "${Sts2Dir:?请先配置并加载 .env}" --ritsu-lib-dir "${RitsuLibDir:?请先配置并加载 .env}"
```

准备脚本把可执行文件、本项目 Mod 和完整 RitsuLib 运行时复制到 `.tmp/roundtrip/runtime/`，用符号链接读取原游戏资源，写入独立测试设置。它不在原游戏目录安装 Mod。重新准备前先停止测试实例。运行目录通过 `installation.json` 绑定首次使用的安装位置；更换位置或发现缺少安装记录的非空运行目录时会拒绝操作，应先保留验证证据再重建 `.tmp/roundtrip`。

## 启动与验证

批量图形回归可使用[复用进程的图形测试框架](gui-testing.md)，一个窗口运行多个新局，显式步骤可以复用同一局。以下仍是单用例启动方式。

终端一执行：

```sh
python3 scripts/run_roundtrip.py
```

启动脚本设置独立的 `XDG_DATA_HOME`，配合 `override.cfg` 将用户数据放在 `.tmp/roundtrip/userdata/sts2_agent-roundtrip/`。使用已核对的 `--force-steam off` 禁用 Steam 初始化；此实例不使用正式存档或 Steam 云存档。日志写入 `.tmp/roundtrip/stdout.log` 和 `.tmp/roundtrip/game.log`。按 Ctrl+C 停止。

终端二执行：

```sh
python3 -m tests.game.verifiers.verify_roundtrip --ipc-dir .tmp/roundtrip/ipc --report .tmp/roundtrip/evidence.json
```

验证脚本要求从新启动实例的主菜单执行，检查非法动作，创建不保存对局的铁甲战士史莱姆测试战斗，结束一次回合，再核对恰好推进一回合、状态读回、旧状态拒绝及重复请求不再次执行。脚本成功时输出 `PASS`；原始请求结果保存在指定的 JSON 报告中。启动后若仍处于加载阶段，可等待日志出现主菜单完成提示再执行验证。再次运行完整验证前应先重启测试实例。

需要直接观察时：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/roundtrip/ipc get_state
```

准备脚本的安装路径隔离回归检查可单独运行，无须启动游戏：

```sh
python3 -m tests.python.test_prepare_roundtrip
```

原型中 `start_test_combat` 和 `end_turn` 都需要 `--expected-state`，其值为最近一次 `--raw` 观察返回的 `state.snapshot_id`；调用形式可参考客户端的 `--help`。动作返回的是执行结束后的状态，而不是仅提交队列时的状态。

## 原型接口

`STS2_AGENT_IPC_DIR` 指定文件通信目录；未设置时，Mod 仅报告加载成功，不启用工具接口。准备脚本与启动脚本面向独立验证实例，启动脚本会设置该变量并启用 `STS2_AGENT_TEST_MODE=1`。

公开玩法工具目录及每项参数见[MCP 工具范围](mcp.md#工具范围)和对应接口指南。文件操作通常同名，但有以下差异：

| 范围 | 文件接口 |
| --- | --- |
| 基础观察 | 使用 `get_state`，对应 MCP 的 `get_observation` |
| 游戏动作 | 调用方自行保存最新 `state.snapshot_id`，以 `expected_state` 提交；MCP 会话内部管理令牌 |
| 详情及浏览页面 | 无须 `expected_state`，仍检查当前场景、遮挡、参数及原生合法性 |
| 输出预设及筛选 | 不接受 MCP 的 `preset`、`card_ids`、`relic_indices` 或地图 `max_steps`；底层文件响应保留完整空值；牌组／牌堆 CLI 另支持共用 --preset 投影 |
| 原生参数 | 牌堆 pile、牌组排序／升级模式，以及 `inspect_selection.view_upgrades` 按各工具定义传入 arguments；牌组／牌堆 CLI 的 --preset 只在 Python 投影，不传入 Mod |
| 兼容操作 | `close_deck` 仅关闭牌组，不注册为 MCP；公开工具使用 `close_card_view` |
| 截图 | 文件 `capture_screenshot` 返回图像载荷；可选 MCP 工具负责文件名和存盘，见[截图接口](screenshots.md)；普通 CLI 不公开此操作 |
| 测试入口 | `start_test_combat` 仅测试模式、主菜单且无进行中对局可用，需要令牌；不是公开玩法工具。套件专用入口见[图形测试](gui-testing.md#生命周期与证据) |

请求写入 `requests/<id>.json`，其中 `id` 是不带连字符的 UUID；先写临时文件再原子重命名为 `.json`。请求体包含 `id`、`operation`；动作另带 `expected_state`，有参数操作的选项放在 `arguments` 对象中。响应写入 `responses/<id>.json`，成功包含 `ok: true` 和 `state`，失败包含 `ok: false` 和 `error.code`、`error.message`。

已审阅入口的明确拒绝可另带 `error.public_message`，表示经适配器确认可公开的原因；普通 message 仍可含私有诊断，不能直接转发。`play_card` 在提交和 UI 变化之前被拒绝时另带布尔 `error.action_submitted:false`；缺省不表示 false。MCP 校验这些字段，只在对应条件下保留已有许可，不把控制标记交给 LLM；完整语义见[MCP 错误处理](mcp.md#调用和错误语义)。观察 schema 的版本不因这些可选错误字段改变。 inspect_combatants 的文件请求另支持可选 level:summary/full，默认为 full；客户端的 preset/sources 与底层级别不同，详见[战斗对象入口](combatant-inspection.md#文件入口与验证)。

- 文件读写和等待在后台进行，状态读取与动作提交在 Godot 主线程进行；当前串行处理请求。
- `snapshot_id` 根据当前导出的观察内容、进程会话、战斗代次、工具界面操作代次、选择实例代次、药水实例代次及模态弹窗实例代次生成。动作在主线程核对令牌和合法性后提交，选牌若跨帧滚动还会在点击前核对候选、已选和数量规则；通过工具查看并关闭牌组后旧令牌不会恢复，须重新观察。占卜的动态图像及临时对白不纳入令牌，次数、工具、格子和可操作状态仍纳入；见[占卜接口](divination.md)。这不是对所有游戏内部状态或两次请求之间全部人工 UI 操作历史的完整版本标识。
- 相同请求 ID 且缓存响应仍在时返回原结果。重复请求不分配新 ID；删除响应缓存后不再保证同一 ID 不会再次执行。
- `stale_state` 表示缺少或不匹配的状态令牌，`illegal_action` 表示当前不可执行，`invalid_request` 表示请求格式有误，`expired_request` 表示执行前已过期，`game_error` 表示游戏调用异常。
- `timeout` 或客户端超时后，动作是否已执行可能不确定。应先重新观察，不能自动换一个 ID 重试动作。创建测试场景过程中发生错误也可能已经部分推进游戏。

## 验证边界

底层动作流程已在独立实例中实测；无头启动存在 FMOD 音频初始化、音频资源及虚拟渲染器警告，不覆盖声音。图形观察的验证范围另见战斗观察说明，不能将无头验证描述为没有运行警告。

原型已扩展可见战斗观察，字段与验证方式见 [游戏基础观察 JSON](observation.md)，范围按 [可见信息边界](../observation.md) 维护；未展开的手牌效果由专门查看调用提供。动作支持结束回合、出牌、使用/丢弃药水和已接通的选牌；stdio MCP 的当前工具范围见 [接入指南](mcp.md)。支持地图选路和跨幕，具体范围见[地图接口](map-inspection.md)；多玩家、断线恢复和异常退出恢复尚未覆盖。通信目录假设仅由可信的本地程序访问，不作为远程服务。

API 核对依据与实测结果见 [验证记录](../research/2026-10-28-roundtrip-validation.md)。

终章专用验证使用 `--ending-scenario victory_unlock`、`death` 或 `event_death`，配合 `tests/game/verifiers/verify_run_ending.py`；每次启动单独创建 `.tmp/roundtrip/ending-userdata-*`，只复制测试设置，不继承其他测试存档。此模式创建可保存的隔离对局以验证原生结算、历史与解锁；测试标志和构造操作不作为公开 MCP 工具。
