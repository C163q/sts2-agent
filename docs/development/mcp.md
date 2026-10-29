# 本地 MCP 接入

本项目提供 Linux 本地 stdio MCP server，供支持 MCP 的 agent 读取《杀戮尖塔 2》并结束回合。服务在游戏外运行，通过现有文件 IPC 与 Mod 通信；不调用模型 API，也不需要在游戏里配置模型密钥。

当前固定公开十二个工具；`inspect_deck` 接受显示选项，`inspect_pile` 必填牌堆并可选信息档位，其余工具无参数：

当前工具列表固定，不按场景增删，调用时核对合法性。动态发现的版本约束及 agent 侧场景过滤建议见 [工具列表与场景可用性核查](../research/2026-10-29-mcp-tool-availability.md)，这些候选尚未实现。

| 工具 | 行为 |
| --- | --- |
| `get_observation()` | 读取当前静态画面的英语玩法 JSON，并在服务内保存本次观察对应的动作令牌 |
| `inspect_hand()` | 只读查看全部当前可见手牌的完整正文和共享悬停解释，不授予动作权限 |
| `inspect_ui()` | 只读查看当前可见战斗界面入口和资源图标的悬停说明，不授予动作权限 |
| `inspect_potions()` | 只读查看当前可见药水栏位、完整说明和共享解释，不使用药水或授予动作权限 |
| `inspect_combatants()` | 只读合并查看双方 powers 与敌人当前意图的悬停说明，不授予动作权限 |
| `inspect_relics()` | 只读批量查看当前可见遗物的英语正文、屏幕计数和共享附带解释，不授予动作权限 |
| `inspect_deck(...)` | 真实打开或复用牌组页，返回全牌组；可选摘要/完整正文、升级预览与排序，保留页面并清除战斗动作令牌 |
| `inspect_pile(...)` | 实际点击并浏览抽牌堆、弃牌堆或消耗牌堆，摘要或完整；区分空堆与隐藏入口，保留原生反馈并清除动作令牌 |
| `close_card_view()` | 仅关闭顶层牌组、抽牌堆、弃牌堆或消耗牌堆查看页；保留下层地图，返回基础观察并清除战斗动作令牌 |
| `inspect_map()` | 真实打开或复用整个当前幕地图，返回节点连线、当前位置、已走路线与原生可选节点；不选路，保留地图并清除动作令牌 |
| `close_map()` | 仅在地图未被卡牌页覆盖、原生返回按钮可用时关闭；返回基础观察并清除动作令牌 |
| `end_turn()` | 消耗最近一次显式观察的令牌，通过游戏正常动作队列结束回合，等待执行结果并返回新观察 |

[手牌详情](hand-inspection.md) 返回平级的 `hand`、共享 `hover_tips` 及适用的 `notes.card_values`，以 `card_ids` 关联解释和手牌。[界面说明](ui-inspection.md) 返回 `scene` 和共享 `hover_tips`，以 `sources` 关联基础观察字段，不附带数值解读 notes。[药水详情](potion-inspection.md) 返回单份 `slot_tip`、保留空槽位置的 `potion_slots` 和以 `slot_indices` 关联的共享 `hover_tips`，不附带数值 notes。[战斗对象详情](combatant-inspection.md) 返回玩家与敌人的 powers、当前敌人意图，以及通过 `sources` 关联的共享说明；包含意图时附带 `notes.enemy_attack_intents`。[遗物详情](relic-inspection.md) 返回 `relics` 和以 `relic_indices` 关联的共享 `hover_tips`，不附带数值 notes。除战斗对象详情外，其他查看不附送敌人意图，所有详情均不附送 `available_actions`；界面说明还排除药水、遗物、powers 和手牌效果。出牌、使用或丢弃药水及其他场景动作尚未实现。基础观察继续遵循 [可见信息边界](../observation.md)，字段见 [战斗观察 JSON](observation.md)。

## 安装与游戏前提

需要 Python 3.10 或以上版本、已构建并加载的 Mod，以及支持 stdio MCP 的客户端；地图查看及关闭要求 Mod 0.12.0，战斗牌堆查看要求 Mod 0.11.0，牌组查看及通用关闭要求 Mod 0.10.0，遗物详情要求 Mod 0.8.0，战斗对象详情要求 Mod 0.7.0，药水详情要求 0.6.0，界面说明要求 0.5.0，手牌详情要求 0.4.0，原有观察和结束回合仍兼容 0.3.0。MCP server 当前为 0.9.0，本次实际使用 Python 3.14.8、官方 Python SDK `mcp==1.26.0` 和游戏 `v0.107.1`。原有标准库客户端不需要安装 MCP 依赖。

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

重新启动或重新加载客户端的 MCP 连接后，确认 `sts2` 提供 `get_observation`、`inspect_hand`、`inspect_ui`、`inspect_potions`、`inspect_combatants`、`inspect_relics`、`inspect_deck`、`inspect_pile`、`close_card_view`、`inspect_map`、`close_map` 和 `end_turn`；此前手动禁用的连接需先重新启用，更新脚本不会自动启用。CLI 可用 `/mcp` 查看连接；具体入口和配置方式以 [Codex 官方说明](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) 为准，此前核对本机 CLI 0.165.0 的命令帮助。

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

可用以下指令验证接入：

> 使用 sts2 工具读取当前战斗，结束一次回合，再读取状态，说明回合和生命值的变化。只结束一次回合。

## 调用和错误语义

调用顺序为 `get_observation → end_turn → get_observation`。每次动作前都必须显式观察；动作返回的新观察用于读取结果，不会自动授权下一次动作。这能阻止未重新观察的重复调用连续结束两个回合。动作失败或通信异常同样消耗令牌，服务不会自动重新观察、重试动作或换一个请求 ID 重发。读取过程中被取消的观察不会保存动作令牌；取消工具调用不能撤回已经提交给游戏的动作，仍须重新观察结果。

`inspect_hand`、`inspect_ui`、`inspect_potions`、`inspect_combatants` 和 `inspect_relics` 可以直接调用，但不能代替战斗观察授权动作。也可以使用 `get_observation → inspect_hand/inspect_ui/inspect_potions/inspect_combatants/inspect_relics → end_turn`：详情读取返回的状态令牌与已有观察一致时保留原动作权限；状态变化、读取失败或取消时清除原令牌。详情响应不会自动保存新的动作令牌，必须重新调用 `get_observation` 后才能行动。没有动作权限时 `end_turn` 仍返回 `observation_required`，不会发送游戏动作。

`inspect_deck`、`inspect_pile`、`close_card_view`、`inspect_map` 与 `close_map` 会改变界面，不按只读详情的令牌保留规则处理：每次发送 UI 请求前清除旧权限，成功、失败、超时或取消后均不恢复。关闭返回的基础观察也不自动授权行动。非法参数在 IPC 前拒绝，不改变界面或此前有效权限。详细参数及省略规则见 [牌组查看](deck-inspection.md)。

```json
{"detail_level": "full", "view_upgrades": true, "sort_by": "cost", "descending": false}
```

连续调用 `inspect_deck` 会复用当前页面；省略升级和排序选项沿用当前值，省略 `detail_level` 则使用摘要。看完调用 `close_card_view()`；仅关闭顶层卡牌查看页，地图保持打开时 `screen.view` 为 `map`，不会另发地图关闭请求。这些工具声明 UI 副作用，客户端可能按其策略要求授权；本项目不持久化这类授权。切换页面不会改变 MCP 工具列表。

战斗牌堆例如 `inspect_pile(pile="draw", detail_level="full")`；`pile` 另可选 `discard/exhaust`，省略信息档位则用摘要。结果包含 `status: opened/empty/unavailable` 和实际 `screen`；空堆经过原生点击并返回 `cards: []`，隐藏入口不点击并返回 `cards: null`，这些是成功结果。详情、原生空堆反馈和跨页行为见 [战斗牌堆查看](pile-inspection.md)。

地图使用 `inspect_map()` 打开或复用，`close_map()` 单独关闭；参数为空对象。整图包含屏幕外可滚动浏览节点，候选遵循原生界面，飞鞋可能允许未连接节点；查看不会选择节点、消耗遗物次数或读取未来幕。关闭不穿透卡牌页，也不会强制关闭原生要求停留的起点地图。字段、空值和页面规则见 [地图查看](map-inspection.md)。

成功时，MCP `structuredContent` 直接包含玩法 JSON，`content` 同时提供同样的 JSON 文本。模型不会收到 `snapshot_id`、原始响应包装或开发测试入口；`available_actions` 只保留已公开的 `end_turn`。协议层仍保留 MCP 自身必需的消息字段。

业务失败返回 `isError: true`，并提供英语结构化错误，例如：

```json
{
  "error": {
    "code": "observation_required",
    "message": "Call get_observation before each action. Actions consume the previous observation.",
    "recovery": "get_observation"
  }
}
```

| 错误 | 处理方式 |
| --- | --- |
| `observation_required` | 尚未观察或上次令牌已消耗，调用 `get_observation` |
| `controller_busy` | 另一个 MCP 连接已取得控制权，断开该连接后重新观察；当前连接可继续握手和发现工具 |
| `stale_state` | 玩家操作、场景变化等使旧观察失效，重新观察后决策 |
| `illegal_action` | 当前不允许结束回合、某类详情不可读，或目标页面/入口不可操作；重新观察并核对页面，关闭地图不能穿透上层卡牌页 |
| `invalid_request` | 工具名或参数有误；`inspect_deck` 仅接受四个显示选项，`inspect_pile` 仅接受必填 `pile` 和可选 `detail_level`，其余工具无参数 |
| `expired_request` | 请求在执行前已过期，重新观察 |
| `timeout`、`game_error` | 执行结果未知，重新观察；不得自动重复动作 |
| `transport_error` | 检查游戏进程、Mod、IPC 目录和读写权限，恢复连接后重新观察 |

内部异常只写入服务标准错误，不传给模型；标准输出专用于 MCP 消息。游戏侧检查和文件请求的原始语义见 [原型接口](roundtrip.md#原型接口)。

## 控制进程与生命周期


每个 IPC 目录只允许一个实际控制游戏的 MCP 连接。初始化握手、发现工具和 Codex 后台预热不会获取控制锁；首次发起游戏请求时尝试取得 `.mcp-controller.lock` 的系统文件锁，随后持有到该服务进程退出。其他连接仍可初始化和发现工具，读取游戏时返回结构化 `controller_busy`，不会发送游戏请求，也不会关闭连接；原控制者断开后可在同一连接重新读取。

客户端断开、服务退出后锁自动释放，无须删除锁文件；同一客户端内部的请求会串行执行。MCP server 0.1.1 修复了先前在启动时加锁、使后台预热阻断新会话握手的问题。若仍有旧版进程占锁，须先断开旧连接，再重新加载 MCP；不要删除锁文件来抢占控制权。

文件锁只约束本项目 MCP server，不能阻止玩家或手动文件客户端操作。因此执行动作前仍须由 Mod 校验原观察令牌及当前合法性。当前不支持多个 agent 同时控制同一对局；切换 agent 时应先断开旧连接。

## 独立验证

Python 自动检查包括真实 stdio 握手和临时文件 IPC，不需要运行游戏：

```sh
.tmp/mcp-venv/bin/python -m unittest discover -s scripts -p 'test_*.py'
```

游戏验证使用 [最小流程验证指南](roundtrip.md) 的独立运行目录。从新启动实例的主菜单执行：

```sh
.tmp/mcp-venv/bin/python scripts/verify_mcp.py --report .tmp/roundtrip/mcp-evidence.json
```

该脚本只接受仓库的 `.tmp/roundtrip/ipc`，通过原有测试入口创建临时战斗，再由真实 MCP server 执行观察、结束回合和读回；还会推进一个回合以验证过期观察被拒绝。开发入口不会注册为 MCP 工具。验证会改变独立测试对局，不可用于正式存档。

Codex 沙箱若禁止本地 socketpair 写入，Python `asyncio` 的线程唤醒和 stdio 测试可能挂起；须按 [Codex 环境约定](../ai/codex.md) 单独申请在沙箱外运行相应命令。此限制与 MCP 是否使用网络端口无关。

当前已通过 100 项 Python 自动检查，覆盖真实 stdio 握手与十二工具发现、牌组参数传输和 UI 操作的令牌清除、控制权竞争、五类详情的令牌保留或失效、取消处理、格式错误、来源路径及输出字段边界，并包含文件客户端的共享提示投影。正式游戏已完成真实 stdio MCP 的只读手牌、界面说明、药水、战斗对象和遗物采样，读取前后状态一致，未执行动作；脚本如下：

```sh
.tmp/mcp-venv/bin/python scripts/verify_mcp_hand.py --ipc-dir .tmp/live/ipc --output .tmp/live/mcp-hand-inspection.json --report .tmp/live/mcp-hand-evidence.json
```

```sh
.tmp/mcp-venv/bin/python scripts/verify_mcp_ui.py --ipc-dir .tmp/live/ipc --output .tmp/live/mcp-ui-inspection.json --report .tmp/live/mcp-ui-evidence.json
```

```sh
.tmp/mcp-venv/bin/python scripts/verify_mcp_potions.py --ipc-dir .tmp/live/ipc --output .tmp/live/mcp-potion-inspection.json --report .tmp/live/mcp-potion-evidence.json
```

药水脚本核对输出与原始文件读取一致、通用槽位说明只有一份、空槽位置不变，以及共享解释的槽位关联。正式采样为 Skill Potion 和空槽；重复 Block 解释及中间空槽由自动检查覆盖。

```sh
.tmp/mcp-venv/bin/python scripts/verify_mcp_combatants.py --ipc-dir .tmp/live/ipc --output .tmp/live/mcp-combatant-inspection.json --report .tmp/live/mcp-combatant-evidence.json
```

战斗对象脚本核对文件和 MCP 输出一致、双方 powers 及敌人意图与基础观察对应、所有共享提示来源可解析，且前后状态未变。正式采样取得两个敌人、三条共享说明。MCP 严格投影约定字段，不转发额外嵌套信息；sources 只能指向本次实际存在的 power/intent，格式错误或来源无效时返回 transport_error 并清除旧动作权限。

```sh
.tmp/mcp-venv/bin/python scripts/verify_mcp_relics.py --ipc-dir .tmp/live/ipc --output .tmp/live/mcp-relic-inspection.json --report .tmp/live/mcp-relic-evidence.json
```

遗物脚本核对文件与 MCP JSON 一致、名称及计数与基础观察对应、共享解释关联完整且前后状态不变。正式采样为 Burning Blood 和计数 2 的 Silver Crucible，无额外解释；重复解释及同名异文由自动检查覆盖。MCP 对原始条目和附带提示逐层投影，不转发内部字段；格式错误返回 `transport_error` 并清除旧动作权限。

此前首次接入完成独立游戏的 MCP 回合往返，以及真实 Codex 模型的观察、结束一次回合和读回：游戏验证从回合 1 到 2，Codex 接续从回合 3 到 4、生命值从 61 到 54，动作结果与读回完全一致。本次遗物详情扩展未修改用户禁用的 Codex MCP 配置，未重新进行模型自动游玩验证。

牌组工具已在 Mod 0.10.0 独立中文实例完成真实 stdio 浏览：28 张牌，摘要、完整、升级预览及重复查看与文件 JSON 一致；显式通用关闭后玩法观察不变、旧令牌不同，工具列表始终九项。样本为 `.tmp/roundtrip/mcp-deck/`；用户重启后，正式 Mod 0.10.0 也完成相同的 MCP 浏览及显式通用关闭，取得 12 张牌，完整与升级模式各 6 条共享解释；与文件输出一致，前后玩法观察相同、原始令牌不同。正式样本为 `.tmp/live/mcp-deck/`。

```sh
.tmp/mcp-venv/bin/python scripts/verify_mcp_deck.py --ipc-dir .tmp/live/ipc --output-dir .tmp/live/mcp-deck
```

该脚本会真实打开、切换预览并关闭卡牌页面，只执行 UI 操作，不出牌或结束回合。地图叠层及其他牌堆通用关闭由独立原生检查覆盖。非战斗界面尚不支持。

证据与范围见 [牌组 MCP 实施记录](../research/2026-10-29-mcp-deck-inspection.md)、[遗物 MCP 实施记录](../research/2026-10-29-mcp-relic-inspection.md)、[战斗对象 MCP 实施记录](../research/2026-10-29-mcp-combatant-inspection.md)、[药水 MCP 实施记录](../research/2026-10-29-mcp-potion-inspection.md)、[界面说明 MCP 实施记录](../research/2026-10-29-mcp-ui-inspection.md)、[手牌 MCP 实施记录](../research/2026-10-29-mcp-hand-inspection.md)、[首次 MCP 实施记录](../research/2026-10-29-mcp-plan.md) 和 [启动锁修复记录](../research/2026-10-29-mcp-startup-lock.md)。当前 Mod 为 0.12.0，支持整幕地图；此前三类战斗牌堆也已在正式游戏重启后验证：抽牌堆 7 张、空弃牌堆和隐藏消耗入口均正确，文件与 MCP JSON 一致，未推进回合；样本位于 `.tmp/live/mcp-piles/`。仅提供 stdio，未实现 HTTP 服务或完整自动游玩；其他 agent 客户端尚未实测。

三类战斗牌堆的 MCP 验证使用：

```sh
.tmp/mcp-venv/bin/python scripts/verify_mcp_piles.py --ipc-dir .tmp/live/ipc --output-dir .tmp/live/mcp-piles
```

整幕地图的真实 stdio 验证使用：

```sh
.tmp/mcp-venv/bin/python scripts/verify_mcp_map.py --ipc-dir .tmp/live/ipc --output-dir .tmp/live/mcp-map
```

正式 Mod 0.12.0 战斗已通过：第一幕 64 个节点、76 条连线，Boss 为 Ceremonial Beast，当前无可选节点。MCP 与文件 JSON 一致，重复读取、错误参数拒绝、地图遮挡下的基础观察与显式关闭均正常，前后玩法观察一致、控制令牌不同。样本为 `.tmp/live/mcp-map/`，未选路、出牌或结束回合。飞鞋、双 Boss、已揭晓问号及跨幕的严格投影已对照隔离原生样本，不将其表述为本次正式对局中的对应实测。详见 [地图 MCP 实施记录](../research/2026-10-29-mcp-map-inspection.md)。

脚本只执行原生查看和关闭，核对摘要/完整、同页复用、文件与 MCP JSON 一致及玩法观察不变。独立场景和当前验证结果见 [牌堆实施记录](../research/2026-10-29-pile-inspection.md)。
