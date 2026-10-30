# 本地 MCP 接入

Linux 本地 stdio MCP server 在游戏外运行，通过文件 IPC 与 Mod 通信。服务不调用模型 API，不负责启动游戏或创建战斗；模型由 agent 客户端调用。

## 通信方式与连接状态

```mermaid
flowchart LR
    A["LLM 客户端"] <-->|"stdio / MCP"| B["Python MCP server"]
    B <-->|"本地 JSON 文件"| C["游戏内 Mod"]
    C <-->|"Godot 主线程读取与动作"| D["游戏状态及原生流程"]
```

游戏启动时，Mod 读取环境变量 `STS2_AGENT_IPC_DIR`；Python 服务使用 `--ipc-dir`。双方须指向同一个目录，它是配置的通信位置，不是自动发现的游戏进程。未设置游戏侧环境变量时，Mod 会加载但关闭通信入口；Python 服务不会因此阻止 MCP 握手或列出工具。

一次 `get_observation` 的流程如下：

1. Python 将其转换为文件操作 `get_state`，生成新的 UUID 请求 ID，先写临时文件再原子发布到 `requests/<id>.json`。
2. Mod 的后台任务约每 20 毫秒检查请求目录，将请求排入主线程队列；图形游戏在渲染帧后处理，无窗口实例在 `ProcessFrame` 处理。
3. 游戏线程读取当前可见状态，或在动作请求中核对令牌与合法性并调用原生流程。等待结算时通过异步帧继续推进游戏，不阻塞主线程等待外部文件或 LLM。
4. 后台将结果原子写入 `responses/<id>.json`；Python 等待匹配 ID 的响应，校验并过滤字段，再返回 MCP JSON 给客户端。

动作请求还携带 MCP 会话保存的观察令牌，防止依据过期观察执行操作；该令牌不交给 LLM。协议字段与重复请求语义见[文件接口](roundtrip.md#原型接口)，动作等待边界见[动作观察说明](end-turn.md#动作完成与画面稳定)。

当前没有进程扫描或独立心跳。MCP 初始化及工具发现成功只能证明 Python 服务可用；使用新请求成功读取观察，才说明游戏内 Mod 在该次请求中能够响应。Python 默认等候最多 40 秒；超时可能是游戏未运行、Mod 未启用、通信目录不同或游戏停止响应，不能仅凭超时区分原因。动作超时也不能证明动作未执行，须重新观察，禁止自动补发。排查入口见[正常游戏读取](live-game.md#读取敌人)。

## 工具范围

默认公开 23 个工具，可按[启动配置](screenshots.md#启动配置)增加 `capture_screenshot`，共 24 个。单个连接的目录固定，不按场景增删；调用时检查合法性。`available_actions` 表示当前可执行的游戏动作，不是 MCP 工具目录。

| 工具 | 用途 |
| --- | --- |
| `inspect_rewards()` | [当前可浏览奖励及悬停说明](rewards.md) |
| `claim_reward(reward_id)` | 逐项点击奖励，后续选牌复用现有选择工具 |
| `proceed()` | 点击奖励页当前原生跳过/前进按钮 |
| `get_observation()` | 读取当前可见基础状态，刷新当前动作令牌 |
| `inspect_hand()` | [全部可见手牌正文及共享解释](hand-inspection.md) |
| `inspect_targets(card_id 或 potion_slot)` | 查询[手牌](card-play.md)或[药水](potion-actions.md)可用性、是否须指定目标及范围，不进入瞄准或抽随机数 |
| `play_card(card_id, target_id?)` | [提交一次原生手动出牌](card-play.md)，后续选牌单独操作 |
| `inspect_ui()` | [当前战斗界面与资源帮助](ui-inspection.md) |
| `inspect_potions()` | [药水正文、空槽位置和共享解释](potion-inspection.md) |
| `use_potion(potion_slot, target_id?)` | [使用药水](potion-actions.md)，遇到后续选择立即返回 |
| `discard_potion(potion_slot)` | 原生丢弃，遵守禁止移除药水的限制 |
| `inspect_combatants()` | [双方 powers 与当前敌人意图解释](combatant-inspection.md) |
| `inspect_relics()` | [遗物正文、可见计数与共享解释](relic-inspection.md) |
| `inspect_deck(...)` | [打开或复用全牌组页面](deck-inspection.md)，可选信息档位、升级预览和排序 |
| `inspect_pile(...)` | [打开或复用战斗牌堆](pile-inspection.md)，必填 `pile`，可选 `detail_level` |
| `close_card_view()` | 关闭顶层牌组/牌堆查看页，保留下层地图 |
| `inspect_map()` | [打开或复用当前幕地图](map-inspection.md)，返回实际可选节点 |
| `close_map()` | 通过可用的原生返回入口关闭地图，不穿透卡牌页 |
| `inspect_selection()` | [整个可浏览候选及详情](card-selection.md) |
| `select_card(card_id)` | 点击一张候选，保留原生多选和确认流程 |
| `selection_option(option_id)` | 点击选择页面列出的启用按钮 |
| `set_selection_view(view)` | 点击原生眼睛，切换选牌与战场查看 |
| `capture_screenshot(filename?)` | 可选：[保存当前游戏视口 PNG](screenshots.md)，返回文件路径与尺寸，默认不注册 |
| `end_turn()` | 结束一次玩家回合，返回期间事件、停止原因及最终观察，见 [结束回合](end-turn.md) |

有参数工具的格式见各自接口说明，其余工具无参数。截图只记录当前画面，不授予动作权限；成功且状态不变时保留旧权限。基础观察、纯详情和原生页面的边界见 [可见信息约定](../observation.md)；选路尚未实现。动态工具发现的候选与版本约束见 [专项核查](../research/2026-10-29-mcp-tool-availability.md)，尚未实现。

## 安装与游戏前提

需要 Python 3.10 或以上版本、Mod `0.21.0` 及其 RitsuLib 依赖，以及支持 stdio MCP 的客户端。MCP server 当前为 `0.17.0`，支持[手牌升级选择](card-selection.md#手牌升级)及复用成功动作返回的观察；动作的停止边界与 `complete` 含义见[动作观察说明](end-turn.md#动作完成与画面稳定)。首次使用须匹配 Mod 与外部脚本；本次奖励功能须同时更新 Mod 和 MCP，并完整重启游戏、重连 MCP。本次使用 Python `3.14.8`、官方 Python SDK `mcp==1.26.0` 和游戏 `v0.107.1`。标准库文件客户端不需要 MCP SDK。

在仓库根目录创建虚拟环境并安装依赖：

```sh
python3 -m venv .tmp/mcp-venv
```

```sh
.tmp/mcp-venv/bin/python -m pip install -r requirements-mcp.txt
```

本机也可使用已安装的 uv：

```sh
uv pip install --python .tmp/mcp-venv/bin/python -r requirements-mcp.txt
```

正常 Steam 游戏的 Mod 安装和启动变量见 [正常游戏加载与读取](live-game.md)。游戏的 `STS2_AGENT_IPC_DIR` 必须与 MCP 的 `--ipc-dir` 指向同一目录，例如 `.tmp/live/ipc`。MCP server 不负责启动游戏或创建战斗。

## 接入 Codex

在仓库根目录执行以下命令，注册本地工具。命令使用绝对路径，后续不要求从仓库目录启动 Codex：

```sh
codex mcp add sts2 -- "$PWD/.tmp/mcp-venv/bin/python" "$PWD/scripts/mcp_server.py" --ipc-dir "$PWD/.tmp/live/ipc"
```

```sh
codex mcp list
```

重新启动或重新加载客户端的 MCP 连接后，确认 `sts2` 提供 `get_observation`、`inspect_hand`、`inspect_ui`、`inspect_potions`、`inspect_combatants`、`inspect_relics`、`inspect_deck`、`inspect_pile`、`close_card_view`、`inspect_map`、`close_map`、`inspect_selection`、`select_card`、`selection_option`、`set_selection_view`、`inspect_targets`、`play_card`、`use_potion`、`discard_potion`、`end_turn`、`inspect_rewards`、`claim_reward` 和 `proceed`；此前手动禁用的连接需先重新启用，更新脚本不会自动启用。CLI 可用 `/mcp` 查看连接；具体入口和配置方式以 [Codex 官方说明](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) 为准，此前核对本机 CLI 0.165.0 的命令帮助。

对应的 TOML 配置示例为：

```toml
[mcp_servers.sts2]
command = "/absolute/path/sts2_agent/.tmp/mcp-venv/bin/python"
args = ["/absolute/path/sts2_agent/scripts/mcp_server.py", "--ipc-dir", "/absolute/path/sts2_agent/.tmp/live/ipc"]
tool_timeout_sec = 60
```

`end_turn` 标为会改变游戏的动作，Codex 可能要求授权。交互会话可按客户端提示批准；非交互 `codex exec` 默认不能弹出批准请求，未经授权时会报 `MCP tool call requires approval, but approval policy is never`。已明确授权自动结束回合时，可仅为这个工具增加以下配置，或通过 `-c 'mcp_servers.sts2.tools.end_turn.approval_mode="approve"'` 对单次会话生效：

```toml
[mcp_servers.sts2.tools.end_turn]
approval_mode = "approve"
```

该设置只预先批准这个工具，不改变其他工具或沙箱策略。配置字段见 [官方配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)。本次真实 Codex 验证使用临时覆盖，不在用户配置中持久保存动作授权。

其他 agent 使用相同的可执行文件、参数和 stdio 传输配置，配置文件格式由各客户端决定。服务默认等待游戏响应最多 40 秒，可通过 `--timeout` 调整；客户端工具超时应留出余量。

## 调用和错误语义

首次往返可以让 agent 执行：

> 使用 sts2 工具读取当前战斗，结束一次回合，再读取状态，说明回合和生命值的变化。只结束一次回合。

首次行动先 `get_observation`。每次动作消耗当前令牌，成功返回的完整观察在满足以下条件时提供新的动作令牌，可直接据此选择下一动作：

- `transition.complete == true`，并且过滤后的 `available_actions` 非空。
- 停止原因为 `player_ready` 或 `action_completed` 时，普通动作画面可见且没有待处理选择；`choice_required` 则要求受支持的选择界面可见。

例如 `get_observation → play_card → play_card → end_turn`，或 `use_potion → inspect_selection → select_card`，中间无需为了取得许可再次读取相同观察。每一步都根据上一返回结果重新决策，按需查询卡牌或目标；不得把同一观察复用成预先排队的一组动作。服务拒绝用请求排队后才产生的新观察授权该请求；同一连接的操作仍串行执行。

Mod 仍在执行前重新计算并核对状态令牌和合法性；玩家或其他客户端使状态改变时返回 `stale_state`，不自动刷新或重试。失败、非法参数、坏响应、超时、取消、不完整结果、无可执行动作、未支持选择及胜负停止均不续接动作许可，须先重新观察再决定。取消不能撤回已提交给游戏的操作。状态令牌留在 MCP 内部，不增加模型参数，也不回放未收到的动作结果。

纯详情不会准备动作。已有令牌仅在成功读取且采样令牌未变时保留；失败、格式错误或取消会清除它。牌组、牌堆、地图及关闭操作会清除令牌；看完显式关闭相应页面，再 `get_observation` 后行动。`close_card_view` 可保留下层地图，须继续 `close_map` 才能回到战斗。这些页面操作有 UI 副作用，客户端按自己的策略处理授权。

成功时 `structuredContent` 是玩法对象，`content` 同时提供相同对象的紧凑 JSON 文本。正文中的换行和空格保留；终端与证据文件使用两空格缩进。对象本身没有排版属性，客户端决定如何转换为模型输入。协议、文本、显示的区别及官方依据见 [项目审阅](../research/2026-10-29-project-review.md#mcp-json-与官方实践)。

输出递归过滤未知字段，不转发原始响应包装、状态令牌或测试入口；`available_actions` 只保留已公开的 `end_turn`、`play_card`、`use_potion`、`discard_potion`、`select_card`、`selection_option`、`claim_reward` 和 `proceed`。MCP 对基础观察和动作结果检查全部顶层观察字段，对已提供的嵌套字段检查类型；错误结果不保存动作令牌。原始文件协议见 [原型接口](roundtrip.md#原型接口)。

业务错误为 `isError: true`，包含 `error.code/message/recovery`；执行结果未知时另带 `outcome: unknown`。内部异常写入标准错误，不交给模型；标准输出专用于 MCP 消息。

| 错误 | 恢复方式 |
| --- | --- |
| `observation_required` | 调用 `get_observation` |
| `controller_busy` | 断开占用控制权的连接，再观察；当前连接仍可握手和发现工具 |
| `stale_state`、`illegal_action`、`expired_request` | 重新观察并核对当前动作或页面是否合法 |
| `invalid_request` | 对照工具 schema 修正参数 |
| `timeout`、`game_error` | 先观察结果，禁止自动重试动作 |
| `transport_error` | 检查游戏、Mod、IPC 路径、权限与响应格式，再观察 |

## 控制进程与生命周期

每个 IPC 目录只允许一个实际控制游戏的 MCP 连接。初始化和工具发现不占锁；首次游戏请求获取 `.mcp-controller.lock` 系统锁，持有到服务进程退出。其他连接返回 `controller_busy`，不向游戏发请求；原连接断开后可在同一连接重新尝试。不要通过删除锁文件抢占控制权。

连接内部请求串行执行。文件锁只约束本项目 MCP server，不能阻止玩家或直接文件客户端操作，因此 Mod 仍在主线程核对状态令牌与合法性。当前不支持多个 agent 同时控制同一对局。历史启动锁修复见 [记录](../research/2026-10-29-mcp-startup-lock.md)。

## 验证与范围

无需游戏的自动检查见 [代码结构与验证](architecture.md#无需游戏的验证)。独立游戏验证须先按 [往返指南](roundtrip.md) 启动新的测试实例，再在主菜单执行：

```sh
.tmp/mcp-venv/bin/python scripts/verify_mcp.py --report .tmp/roundtrip/mcp-evidence.json
```

该脚本只允许仓库的独立 IPC 目录，会创建临时战斗并推进回合以检查正常动作、连续执行及过期观察，不能用于正式存档。

完整动作链验证先启动新的图形测试实例 `python3 scripts/run_roundtrip.py --windowed --play-scenario armaments_free --potion-scenario skill`，再运行 `.tmp/mcp-venv/bin/python scripts/verify_action_observations.py --report .tmp/action-chain/run.json`。它会连续出牌、使用/丢弃药水、完成选择并切换查看页面，报告目录须全新；结果与范围见[动作观察复用记录](../research/2026-10-30-action-observations.md)。

详情及页面的真实 stdio 验证分别使用 `verify_mcp_hand.py`、`verify_mcp_ui.py`、`verify_mcp_potions.py`、`verify_mcp_combatants.py`、`verify_mcp_relics.py`、`verify_mcp_deck.py`、`verify_mcp_piles.py`、`verify_mcp_map.py`；参数见各脚本 `--help` 和上表对应指南。页面检查会真实打开、切换及关闭页面。

已有独立游戏与正式游戏的只读采样，及真实 Codex 模型结束一次回合的验证。历史环境、样本和未覆盖项见 [首次 MCP 往返](../research/2026-10-29-mcp-plan.md)、[牌组](../research/2026-10-29-mcp-deck-inspection.md)、[牌堆](../research/2026-10-29-pile-inspection.md) 和 [地图](../research/2026-10-29-mcp-map-inspection.md) 等阶段性记录。

历史外部层兼容重构的检查、样本回放与当时未重新执行的游戏内验证范围见[项目审阅](../research/2026-10-29-project-review.md)。当前只提供 stdio，其他客户端、HTTP 服务及完整自动游玩尚未实测或实现。
