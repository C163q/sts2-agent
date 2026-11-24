# 最小流程验证指南

本指南说明 Mod 的构建、独立实例验证及底层文件接口。版本与依赖见[项目 README](../../README.md#当前版本与前提)，agent 接入见[本地 MCP server](mcp.md)。

## 前提与构建

- 自行安装 Linux 或 Windows x64 版《杀戮尖塔 2》。游戏路径通过 `Sts2Dir` 和 `--game-dir` 传入，构建从安装目录识别对应平台的程序集。
- 按 [global.json](../../global.json) 安装 .NET 10 SDK，并在 .NET 安装根目录的 `packs/` 下提供 .NET 9 目标框架引用包（`Microsoft.NETCore.App.Ref` 9.0.x）。Mod 编译为 `net9.0`，由游戏自带的 .NET 9 运行时加载。
- 安装 Python 3；本文原有文件客户端和验证脚本只使用标准库，MCP 服务的额外依赖见接入指南。
- `RitsuLibDir` 指向兼容 RitsuLib 的完整目录，可直接使用 Steam 创意工坊安装。目录须直接包含 `RitsuLib.References.props`、`mod_manifest.json`、根 DLL、`assets.zip`、`shared/` 和匹配的 `compat/` 子目录。
- 构建引用上述本地库与游戏自带程序集，不下载 NuGet 包；[NuGet.Config](../../src/Sts2Agent/NuGet.Config)不启用远程源。

构建目标和依赖版本见[兼容基线](../../README.md#当前版本与前提)。RitsuLib 对游戏 `v0.111.1` 沿用 `compat/0.111.0`。手工获取时，从[作者发布页](https://github.com/BAKAOLC/STS2-RitsuLib/releases/tag/v0.6.15)选择包含该目标的完整兼容包，解压后将目录设为 `RitsuLibDir`。

### 路径配置

在 Linux 仓库根目录复制[配置示例](../../.env.example)。

```sh
cp .env.example .env
```

根据机器环境编辑 `.env`，将 `Sts2Dir` 填为游戏安装目录的绝对路径，`RitsuLibDir` 填为完整兼容运行时的目录。在执行构建、准备或安装命令的终端中加载配置：

```sh
. ./.env
```

在 Windows PowerShell 中设置同名环境变量，并将示例路径替换为实际路径。

```powershell
$env:Sts2Dir = 'C:\Program Files (x86)\Steam\steamapps\common\Slay the Spire 2'
$env:RitsuLibDir = 'C:\Program Files (x86)\Steam\steamapps\workshop\content\2868840\3747602295'
```

### 构建与测试准备

在 Linux 仓库根目录构建 Mod。

```sh
env DOTNET_CLI_HOME=/tmp/sts2-agent-dotnet NUGET_PACKAGES=/tmp/sts2-agent-nuget DOTNET_CLI_TELEMETRY_OPTOUT=1 dotnet build src/Sts2Agent/Sts2Agent.csproj -p:Sts2Dir="${Sts2Dir:?请先配置并加载 .env}" -p:RitsuLibDir="${RitsuLibDir:?请先配置并加载 .env}"
```

在 Windows 仓库根目录的 PowerShell 中构建。

```powershell
dotnet build src/Sts2Agent/Sts2Agent.csproj
```

正常游戏安装继续按[加载指南](live-game.md#安装文件)操作。需要独立测试实例时，再执行：

```sh
python3 scripts/prepare_roundtrip.py --game-dir "${Sts2Dir:?请先配置并加载 .env}" --ritsu-lib-dir "${RitsuLibDir:?请先配置并加载 .env}"
```

Windows 使用 PowerShell 执行同一准备脚本。

```powershell
python scripts/prepare_roundtrip.py --game-dir $env:Sts2Dir --ritsu-lib-dir $env:RitsuLibDir
```

准备脚本核对游戏版本后，在 `.tmp/roundtrip/runtime/` 放置游戏可执行文件、Mod 和完整的 RitsuLib，并写入测试设置。Linux 链接原游戏资源，Windows 复制资源。重新准备前先停止测试实例。游戏安装更新后应重建隔离运行时，以使可执行文件和资源保持同版。运行目录通过 `installation.json` 绑定首次使用的安装位置。更换位置或使用缺少安装记录的非空目录时，先保留验证证据再重建 `.tmp/roundtrip`。

## 启动与验证

以下命令用于单用例验证。Linux 批量回归使用[图形测试套件](gui-testing.md)。在 Windows 将命令中的 `python3` 换成 `python`，图形验证从已登录的桌面终端启动并加 `--windowed`。

终端一执行：

```sh
python3 scripts/run_roundtrip.py
```

启动脚本为游戏进程设置独立的 `XDG_DATA_HOME`（Linux）或 `APPDATA`（Windows），配合 `override.cfg` 将用户数据放在 `.tmp/roundtrip/userdata/sts2_agent-roundtrip/`。`--force-steam off` 禁用 Steam 初始化。日志写入 `.tmp/roundtrip/stdout.log` 和 `.tmp/roundtrip/game.log`。按 Ctrl+C 停止。

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
| 输出预设及筛选 | 不接受 MCP 的 `preset`、`card_ids`、`relic_indices` 或地图 `max_steps`；底层文件响应保留完整空值。CLI 的 --preset、--card-ids、--sources、--slot-indices 支持范围见各工具指南，均在 Python 层投影 |
| 原生参数 | 牌堆 pile、牌组排序／升级模式，以及 `inspect_selection.view_upgrades` 按各工具定义传入 arguments；牌组／牌堆 CLI 的 --preset 只在 Python 投影，不传入 Mod |
| 兼容操作 | `close_deck` 仅关闭牌组，不注册为 MCP；公开工具使用 `close_card_view` |
| 截图 | 文件 `capture_screenshot` 返回图像载荷；可选 MCP 工具负责文件名和存盘，见[截图接口](screenshots.md)；普通 CLI 不公开此操作 |
| 测试入口 | `start_test_combat` 仅测试模式、主菜单且无进行中对局可用，需要令牌；不是公开玩法工具。套件专用入口见[图形测试](gui-testing.md#生命周期与证据) |

请求写入 `requests/<id>.json`，其中 `id` 是不带连字符的 UUID；先写临时文件再原子重命名为 `.json`。请求体包含 `id`、`operation`；动作另带 `expected_state`，有参数操作的选项放在 `arguments` 对象中。响应写入 `responses/<id>.json`，成功包含 `ok: true` 和 `state`，失败包含 `ok: false` 和 `error.code`、`error.message`。

明确拒绝可带 `error.public_message`，表示经适配器确认可公开的原因；普通 message 保留诊断用途。游戏动作在尚未提交且 UI 未变化的前置拒绝中可带 `error.action_submitted:false`；页面工具在本请求尚未交互时可带 `error.ui_unchanged:true`。恢复策略由[工具登记](../../src/sts2_mcp/tool_registry.py)声明，MCP 核对标记类型及其与执行事实是否一致，完整条件见[MCP 错误处理](mcp.md#调用和错误语义)。保证作用于本请求，外部输入仍可能改变状态。控制字段留在内部协议，LLM 仅接收公开原因与恢复指引。

战斗对象、药水和遗物详情支持内部 `arguments.level:full/summary`，默认 full；summary 仅读取静态展示。具体原生参数、不可悬停来源与公开投影分别见[战斗对象](combatant-inspection.md#文件入口与验证)、[药水](potion-inspection.md#文件客户端)和[遗物](relic-inspection.md)。

内部请求包装可带 `response_options:{"include_divination_image":false}`，与游戏 `arguments` 分开。省略时按文件协议的默认行为捕获当前可见占卜棋盘；显式布尔值控制是否附加 PNG，结构化采样和逻辑令牌保持一致。未知选项、重复键和非布尔值会被拒绝。MCP 仅在 `inspect_event({"include_image":true})` 时请求占卜图片；基础观察、动作回执和关闭页面结果均使用文字输出。普通文件 CLI 的 close_card_view 显式关闭棋盘媒体；其他调用沿用文件协议默认行为，`--raw` 也保留该默认行为。媒体参数由[请求规范化](../../src/sts2_mcp/request_arguments.py)与[文件客户端](../../src/sts2_mcp/roundtrip_client.py)处理。

适配器响应根部另有私有 `execution` 正向事实：`ui_interaction_started` 表示开始过 UI 交互，`action_submission_observed` 表示观察到原生动作提交，`state_captured` 表示完成过完整快照采样。后者不保证采样晚于最后一次动作或当前仍有效；所有 false 只表示未记录正向事实，不是“未执行”证明。异常、媒体或序列化失败保留已经记录的事实。MCP 会话校验这些控制字段，不转发给模型，也不据此自动重试或续权；矛盾的未提交标记作为坏响应拒绝。

新协议详情携带同次快照的 `schema_version/snapshot_id/scene/screen`；前两项为私有控制信息，公开上下文见[MCP 约定](mcp.md#成功结果的场景上下文)。

- 文件读写和等待在后台进行，状态读取与动作提交在 Godot 主线程进行；当前串行处理请求。
- `snapshot_id` 根据当前导出的观察内容、进程会话、战斗代次、工具界面操作代次、选择实例代次、药水实例代次及模态弹窗实例代次生成。动作在主线程核对令牌和合法性后提交，选牌若跨帧滚动还会在点击前核对候选、已选和数量规则；通过工具查看并关闭牌组后旧令牌不会恢复，须重新观察。占卜的动态图像及临时对白不纳入令牌，次数、工具、格子和可操作状态仍纳入；见[占卜接口](divination.md)。这不是对所有游戏内部状态或两次请求之间全部人工 UI 操作历史的完整版本标识。
- 相同请求 ID 且缓存响应仍在时返回原结果。重复请求不分配新 ID；删除响应缓存后不再保证同一 ID 不会再次执行。
- `stale_state` 表示缺少或不匹配的状态令牌，`illegal_action` 表示当前不可执行，`invalid_request` 表示请求格式有误，`expired_request` 表示执行前已过期，`game_error` 表示游戏调用异常。
- `timeout` 或客户端超时后，动作是否已执行可能不确定。应先重新观察，不能自动换一个 ID 重试动作。创建测试场景过程中发生错误也可能已经部分推进游戏。

## 验证边界

底层动作流程已在独立实例中实测；无头启动存在 FMOD 音频初始化、音频资源及虚拟渲染器警告，不覆盖声音。图形观察的验证范围另见战斗观察说明，应按日志记录这些环境限制。

基础观察、游戏动作和浏览工具的当前范围见[MCP 接口目录](mcp.md#工具范围)，字段与显示条件由各专题维护。多人、断线恢复和异常退出恢复尚未覆盖。通信目录供可信本地程序访问，当前实现仅用于本地通信。

API 核对依据与实测结果见 [验证记录](../research/2026-10-28-roundtrip-validation.md)。

终章专用验证使用 `--ending-scenario victory_unlock`、`death` 或 `event_death`，配合 `tests/game/verifiers/verify_run_ending.py`；每次启动单独创建 `.tmp/roundtrip/ending-userdata-*`，只复制测试设置，不继承其他测试存档。此模式创建可保存的隔离对局以验证原生结算、历史与解锁；测试标志和构造操作不作为公开 MCP 工具。 胜利回执允许保留只读工具，脚本验证没有玩法动作和连续玩法许可，再继续检查结算、解锁及返回菜单；完整回归见[前进修复记录](../research/2026-11-06-proceed-recovery-implementation.md)。
