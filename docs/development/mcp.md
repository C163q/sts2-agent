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

默认公开 43 个工具，可按[启动配置](screenshots.md#启动配置)增加 `capture_screenshot`，共 44 个。单个连接的目录固定，不按场景增删；调用时检查合法性。`available_actions` 列出当前可用的查看与操作工具名，不含参数；省略观察、截图和测试入口。完整语义与精简预设见[观察输出预设](observation.md#mcp-输出预设)。

当前详情调用不返回 `available_actions`，可用 `get_observation({"preset":"actions_only"})` 获取。遗物查看读取当前已显示的遗物栏，不能悬停时保留静态字段并说明缺少帮助；牌组查看也支持原生按钮可用的非战斗页面。适用范围见[遗物详情](relic-inspection.md)和[牌组页面](deck-inspection.md)。

| 工具 | 用途 |
| --- | --- |
| `inspect_run_result()` | [终章结算](run-ending.md)当前页、发现与徽章悬停说明、解锁物品详情 |
| `run_result_option(option_id)` | 点击当前结算按钮或待揭示解锁条目，逐页操作至主菜单 |
| `respond_to_confirmation(option)` | 明确确认或取消[当前 Trial 事件确认框](events.md#事件确认弹窗)，确认会结束本局 |
| `set_divination_tool(tool)` | [占卜](divination.md)切换大小工具，不消耗次数；可直接调用，返回actions_only |
| `divine(x,y)` | 点击仍覆盖的占卜格子；棋盘及图像按需观察 |
| `inspect_event(preset?, include_image?)` | [当前通用事件](events.md)正文、选项与悬停解释；summary 为静态摘要；占卜默认文字，include_image:true 按需附图 |
| `choose_event_option(option_id)` | 点击一个启用的事件选项，保留原生后续流程与致死警告 |
| `inspect_ancient(preset?, option_ids?)` | [当前先古之民](ancients.md)的对话、馈赠与悬停解释；支持静态summary及选项ID筛选 |
| `choose_ancient_option(option_id)` | 点击一个已显示且启用的先古选项 |
| `advance_dialogue()` | 推进先古之民或建筑师的一句原生对话，不选择遗物 |
| `open_shop()` / `close_shop()` | 点击[商店](shop.md)的商人或返回按钮，实际展开/收回商品页 |
| `inspect_shop(preset?, item_ids?, kinds?)` | [完整／静态商品及购买顶栏](shop.md#打开观察与详情)，按ID与分类筛选 |
| `buy_item(item_id)` | 购买一个当前商品；补货使用新 ID，删牌复用选牌工具 |
| `inspect_rewards(preset?, reward_ids?)` | [当前奖励、静态 summary 和按稳定奖励 ID 筛选](rewards.md) |
| `claim_reward(reward_id)` | 逐项点击奖励，后续选牌复用现有选择工具 |
| `proceed()` | [当前原生跳过／前进](#前进与跳过)，保留奖励、房间、换幕与终章各自后续流程 |
| `loot_treasure(open_only?)` | [宝箱房开箱并领取](treasure.md)，可先开后决定；不自动前进 |
| `inspect_treasure(preset?)` | 当前可见宝箱遗物及悬停说明 |
| `inspect_rest_site(preset?, option_ids?)` | [火堆完整说明／静态summary及按原生ID筛选](rest-site.md) |
| `choose_rest_option(option_id)` | 点击一个启用的休息处选项，后续选牌单独处理 |
| `get_observation(preset?)` | 默认 `default`；`full` 保留空值；`summary` 精简战斗、卡牌与顶栏；full/default/summary 的事件和占卜主体均使用专门详情的静态摘要；`actions_only` 仅返回上下文与工具名；`top_bar` 再附顶栏和遗物数量，各预设均刷新动作令牌 |
| `inspect_hand({preset?, card_ids?})` | [手牌完整详情或摘要及当前能量／星星，可按 ID 筛选卡牌](hand-inspection.md) |
| `inspect_targets(card_id 或 potion_slot)` | 查询[手牌](card-play.md)或[药水](potion-actions.md)可用性、是否须指定目标及范围，不进入瞄准或抽随机数 |
| `play_card(card_id, target_id?)` | [提交一次原生手动出牌](card-play.md)，后续选牌单独操作 |
| `play_cards(cards)` | [按顺序连续入队](card-play.md#连续出牌)，逐张结果及选择续接见 card_plays |
| `inspect_ui(preset?, sources?)` | [可见顶栏与战斗通用悬停帮助](ui-inspection.md)，summary 省略正文，sources 精确筛选来源 |
| `inspect_potions(preset?, slot_indices?)` | [药水完整／静态摘要及原槽位筛选](potion-inspection.md)，筛选同时裁剪关联提示并返回位置映射 |
| `use_potion(potion_slot, target_id?)` | [使用药水](potion-actions.md)，遇到后续选择立即返回 |
| `discard_potion(potion_slot)` | [原生丢弃及选牌期间的排队](potion-actions.md#丢弃结果与排队)，顶层 potion_discard 报告本次结果 |
| `inspect_combatants(preset?, sources?)` | [战斗对象、意图、球与悬浮剑；summary 为静态信息，sources 筛选对象](combatant-inspection.md) |
| `inspect_relics(preset?, relic_indices?)` | [遗物完整／摘要与下标筛选](relic-inspection.md#mcp-参数)，默认保留正文、可见计数与共享解释 |
| `inspect_deck(...)` | [打开或复用全牌组页面](deck-inspection.md)，支持预设、card_ids 筛选、升级预览和排序 |
| `inspect_pile(...)` | [打开或复用战斗牌堆](pile-inspection.md)，必填 `pile`，支持 full/default/summary 与输出 card_ids 筛选 |
| `close_card_view()` | 关闭顶层牌组/牌堆查看页，保留下层地图，返回 actions_only 上下文并刷新许可 |
| `inspect_map(preset?, max_steps?)` | [打开或复用当前幕地图](map-inspection.md)，可返回全图、前瞻子图、按类型分类的节点 ID 或实际可选节点详情 |
| `travel_to_node(node_id)` | [按当前候选选路](map-inspection.md#地图选路)，离开房间并放弃未领取奖励；飞鞋由原生流程处理 |
| `close_map()` | 通过可用原生返回入口关闭地图，返回 actions_only 内容，不穿透卡牌页 |
| `inspect_selection(preset?, card_ids?, view_upgrades?)` | [整个可浏览候选及详情](card-selection.md#mcp-输出预设)，默认完整，摘要与 ID 筛选统一作用于候选、包内与预览卡牌，可显式切换原生升级复选框 |
| `select_card(card_id)` | 点击一张候选，保留原生多选和确认流程 |
| `selection_option(option_id)` | 点击选择页面列出的启用按钮 |
| `set_selection_view(view)` | 点击原生眼睛，切换选牌与战场查看 |
| `capture_screenshot(filename?)` | 可选：[保存当前游戏视口 PNG](screenshots.md)，返回文件路径与尺寸，默认不注册 |
| `end_turn()` | 结束一次玩家回合，返回期间事件、停止原因及当前交互状态，见 [结束回合](end-turn.md) |

除截图外，全部工具均接受可选的 `preset`；上表未重复列出通用参数，特有参数见各接口说明。截图只记录当前画面，不授予动作权限；成功且状态不变时保留旧权限。基础观察、纯详情和原生页面的边界见 [可见信息约定](../observation.md)；地图选路使用 `travel_to_node`。动态工具发现的候选与版本约束见 [专项核查](../research/2026-10-29-mcp-tool-availability.md)，尚未实现。

## 安装与游戏前提

需要支持 stdio MCP 的客户端，并安装[当前基线](../../README.md#当前版本与前提)中的 Mod、依赖与 Python。安装、更新及两端版本排错见[正常游戏指南](live-game.md#更新与排错)。MCP 的 Python 依赖由 [requirements-mcp.txt](../../requirements-mcp.txt)定义；标准库文件客户端不需要 MCP SDK。

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

重新启动或重新加载客户端的 MCP 连接后，确认 `sts2` 提供上方[工具范围](#工具范围)中的完整目录；此前手动禁用的连接需先重新启用，更新脚本不会自动启用。CLI 可用 `/mcp` 查看连接；具体入口和配置方式以 [Codex 官方说明](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) 为准，历史核对环境见[首次接入记录](../research/2026-10-29-mcp-plan.md)。

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

该设置只预先批准这个工具，不改变其他工具或沙箱策略。配置字段见 [官方配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)。历史 Codex 验证的授权方式及环境见[首次接入记录](../research/2026-10-29-mcp-plan.md)。

其他 agent 使用相同的可执行文件、参数和 stdio 传输配置，配置文件格式由各客户端决定。服务默认等待游戏响应最多 40 秒，可通过 `--timeout` 调整；客户端工具超时应留出余量。

场景与覆盖页面统一遵循[观察上下文](observation.md#场景上下文)；工具类型不改写 scene。

## 输出预设

全部 43 个玩法 JSON 工具接受可选的 `preset`：

| 预设 | 行为 |
| --- | --- |
| `default`（默认） | 与本工具 full 的内容范围一致，递归删除普通对象字段中的 `null`，以及下述指定字段的 false |
| `full` | 保留本工具原有完整输出及其中的空值；动作仍返回精简回执，不附送完整观察 |
| 专用预设 | summary 继承 default 后进一步精简；selectable、actions_only 按各工具契约返回 |

过滤保留以下例外：所有数组的 `null` 元素；`transition.events` 中已有的全部空值；选牌已展开的升级、附魔、变牌比较中 before / after 两侧的全部内容与空值。后者包括随机变牌的 `after:null`，但未展开的整个 `upgrade_preview:null` 可以省略。宝箱房 `treasure.status:"visible"` 时，保留已有的 `relic:null`，明确当前没有展示可领取遗物；covered 时仍省略，不据此推断隐藏内容。

`0`、`false`、空字符串、空数组、空对象通常保留。仅省略根 `relics[]` 和 `top_bar.relics[]` 的 `grayed_out/pulsing:false`，以及 `transition.events[]` 中 `type:card_played` 的 `autoplay:false`；自动出牌的 true、其他 false（包括 melted）及事件 null 不受影响。数组长度、顺序和引用下标不变；过滤后为空的对象仍保留。省略不表示沿用上次值；普通省略字段不表示零、否或空集合，上述局部字段按各自契约解释。结果不是状态增量；需要明确空值和上述 false 时使用 full。

例如普通遗物的 `counter:null`、`melted:null` 在 default 中省略，蜡质遗物的 `melted:false/true` 保留。遗物 summary 同样省略普通空值与两个 false 图标字段。`inspect_deck` / `inspect_pile` 同样使用 full/default/summary，默认完整内容；旧 detail_level 已移除。

各工具专用预设的完整字段规则由对应接口维护：`get_observation` 的 summary／top_bar 见[观察预设](observation.md#mcp-输出预设)，UI 帮助、手牌、选牌、药水和遗物摘要见各工具说明。不要把 default 保留空数组的公共规则套用到明确精简空列表的专用 summary。

该参数只控制 Python 公开输出，不转发给 Mod；先完整校验响应，再进行原有筛选与统一空值过滤；许可依据完整状态判断，公开投影成功后才发布。部分成功的 `errors`、顶层错误及显式请求的占卜图片保留。截图工具不提供 preset。其他标准库文件调用继续保留原有空值；牌组／牌堆 CLI 的 --preset 共用上述 Python 投影，底层 Mod 始终采样完整卡牌。

可选筛选 `sources`、`card_ids`、`relic_indices` 统一接受省略或 `null` 表示全部，`[]` 表示空集合；重复项去重、原生顺序不变。有效与无效项并存时保留成功内容，并用 `errors` 合并缺失项。位置引用以当前未筛选列表为准，遗物通过顶层 `relic_indices` 对应压缩结果。工具登记与参数职责见[代码结构](architecture.md#工具登记与参数)。

## 成功结果的场景上下文

玩法 JSON 的成功结果统一包含 `scene` 和 `screen`，分别表示当前房间／结算场景及覆盖页，与同次基础观察一致；详情不按工具名重建场景。手牌、目标、药水和遗物也遵循该规则。截图存盘结果保持文件信息格式。

原生详情从本次完整快照复制上下文、令牌及协议标识；Python 对新协议要求完整上下文，再进行筛选与预设。历史片段样本的兼容读取不补造场景，不能据此宣称旧 Mod 已提供新字段。原生请求与执行元数据见[文件协议](roundtrip.md#原型接口)，不进入 LLM 结果。

## 调用和错误语义

首次往返可以让 agent 执行：

> 使用 sts2 工具读取当前战斗，结束一次回合，再读取状态，说明回合和生命值的变化。只结束一次回合。

`get_observation`、专项详情及查看/关闭/切换页面的成功结果都会刷新内部动作令牌；首次也可直接读取相关详情。只要已有足够信息，就不必额外调用 `get_observation`。例如 `inspect_map → travel_to_node`、`inspect_hand → play_card`、`close_card_view → end_turn`；覆盖页仍须显式关闭，工具不会穿透页面行动。

每次动作消耗当前令牌，服务完整校验动作后的状态，在满足以下条件时保存新的动作令牌并返回精简回执，可直接据此选择下一动作：

- `transition.complete == true`，并且 `available_actions` 包含实际游戏动作；若该动作结果只列出详情或页面查看工具，则不续接动作许可。
- 停止原因为 `player_ready` 或 `action_completed` 时，普通动作画面可见且没有待处理选择；`choice_required` 则要求受支持的选择界面可见。

连续出牌结果中，只要有一项 `status` 为 `unknown`，表示工具无法确认该牌的执行结果。此时须先用 `get_observation` 或相关查看工具读取当前状态，再提交下一次动作；如果选牌窗口已经显示，可以直接读 `inspect_selection`。正常的 `queued`（排队中）或 `resolving`（正在处理，可能等待选牌）不触发这条额外读取要求，可以按当前选牌界面继续操作。

discard_potion 的顶层 potion_discard.status 为 queued 时，可以直接继续当前选择；unknown 或 not_discarded 不续接动作许可，须先读取。该结果与实际事件的关系见[丢弃结果与排队](potion-actions.md#丢弃结果与排队)。

战斗外地图上的用药／丢弃成功返回 action_completed、complete:true 且仍有合法动作时，也可直接继续。此时 screen.status:covered 表示下层房间被地图覆盖；地图自身仍可操作，不要求额外读取。战斗中打开地图不因此允许出牌或用药。

例如 `get_observation → play_card → play_card → end_turn`，或 `use_potion → inspect_selection → select_card`，中间无需为了取得许可再次读取相同观察。每一步根据上一返回结果重新决策，按需查询卡牌或目标。连续入队使用 play_cards 在一次已授权请求中逐项复查并提交；多个独立请求仍不能借用排队后才产生的新观察，同一连接的操作串行执行。

Mod 仍在执行前重新计算并核对状态令牌和合法性；玩家或其他客户端使状态改变时返回 `stale_state`，不自动刷新或重试。坏响应、超时、游戏异常、取消、不完整结果、无可执行动作、未支持选择及胜负停止均不续接动作许可，须先重新读取当前状态再决定。取消不能撤回已提交给游戏的操作。状态令牌留在 MCP 内部，不增加模型参数，也不回放未收到的动作结果。

所有工具的本地参数错误都在发送前拒绝，保留此前已有许可，不生成新许可。纯读取（基础观察及不改变 UI 的详情）遇到原生明确的 `invalid_request/illegal_action/expired_request` 也保留已有许可；首次读取失败不会生成许可。外部状态改变后，下一动作仍须通过 Mod 的 stale_state 校验。控制器冲突、坏响应、连接失败、超时、异常或取消清除许可。

`inspect_selection` 省略 `view_upgrades` 时属于纯读取；显式提供该参数则可能改变 UI，与地图、牌组、牌堆及查看页切换一样，不能仅凭明确拒绝的错误码恢复许可。inspect_deck／inspect_pile／inspect_map／close_card_view／close_map／set_selection_view／set_divination_tool 的已审查拒绝另有原生“本请求未交互”保证；只有显式保证为 true、证据不矛盾且已有许可时保留，返回 choose_legal_action。缺少保证、已交互或未知结果仍要求观察；该例外不推广到其他页面工具。这些页面操作不要求已有动作许可。`set_divination_tool`仅切换当前占卜工具，成功返回actions_only并刷新许可，不记录玩法事件；具体检查见[占卜接口](divination.md#动作覆盖与结算)。MCP annotations不代替注册的执行策略。

游戏动作仅在原生证明“未提交且 UI 未改变”时保留旧许可。`play_card`、`play_cards`、`end_turn`、`use_potion`、`discard_potion`、`select_card`、`selection_option`、`travel_to_node`、`claim_reward`、`choose_rest_option`、`loot_treasure`、`proceed`、`open_shop`、`close_shop`、`buy_item`、`choose_event_option`、`choose_ancient_option`、`advance_dialogue`、`divine` 与 `respond_to_confirmation` 的已审查前置拒绝提供这一保证；费用、目标和选择／覆盖／按钮状态会给具体提示，例如能量不足被拒后可直接结束回合，选牌期间误用 end_turn 被拒后可直接继续合法选择，无效候选或按钮被拒后可直接改用有效候选或按钮。travel_to_node 在地图未开、被覆盖、绘图或目标非候选等明确拒绝时可直接纠正；claim_reward 的奖励 ID 无效、页面覆盖或尚未就绪等明确拒绝也可直接纠正，具体契约见[奖励领取](rewards.md#领取与后续选择)。loot_treasure 在首次点击前的已开箱、无遗物或覆盖等明确拒绝也可直接纠正；已经开箱后的第二阶段不具备整次请求未交互保证。proceed 在地图／牌组／选牌／确认框覆盖、未完成活动或对白、商品页展开等点击前拒绝时保留已有许可，并提示相应工具。open_shop在商品页已打开、地图／牌组／选择覆盖及未就绪等点击前拒绝时保留已有许可，提示inspect_shop、close_shop或当前页面工具；具体条件见[商店接口](shop.md#打开观察与详情)。close_shop在商品页已关闭、覆盖或未就绪等点击前拒绝时保留已有许可，可直接打开或处理当前选择／奖励；同见商店接口。buy_item的页面、ID、单品交互及金币等明确前置拒绝也保留许可；进入原生购买后不能把领取失败当作未交互，pending表示继续当前选择／奖励。结果ID与请求一致后才可续接，见商店接口。地图与奖励的滚动已经属于交互，滚动后的失败不会恢复许可。批量部分提交后的失败不具备整批未提交保证。缺少标记的旧 Mod、其他动作拒绝或执行结果未知时不恢复许可。占卜等操作返回 `screenshot_unavailable` 仍可能已经改变游戏，返回 `outcome:"unknown"` 并要求观察，不能把图像失败当作玩法未执行。

许可同时记录令牌和代次。排队动作只能使用调用开始时已有的那一代许可，即使后来读取返回相同字符串，也不能借用；取消会使等待／在途请求无法重新发布已撤销的许可。执行证据与公开 JSON 分开保存，不向模型暴露控制字段。用户保存的实测记录尚未逐条对照，[两项待办](TODO.md#当前工具审阅结束后处理)仍保留。

专项详情会使用本次成功读取的新令牌，不要求它与旧令牌相同。页面操作先清除旧令牌，完整校验成功响应后保存新令牌；空牌堆或入口不可用的成功结果也按返回时的实际状态刷新。页面操作失败、格式错误或取消不保存新令牌。截图只在状态未变时保留已有令牌，不提供新令牌。`close_card_view` 可保留下层地图，须继续 `close_map` 才能回到战斗。这些页面操作有 UI 副作用，客户端按自己的策略处理授权。

顶层错误仍使用 `error.code/message/recovery`。Mod 只有显式标记为可公开的拒绝说明才进入 message；原始异常、路径及未知诊断字段不转发。本地参数错误指出字段和允许的类型／范围。`recovery:"correct_request"` 表示修正参数；已有许可被保留时，明确拒绝使用 `choose_legal_action`，可根据已有信息选择合法操作，按需再观察；没有已有许可可保留时，`illegal_action/expired_request/stale_state` 要求读取当前状态；`correct_request` 只表示修正请求，尚无许可时仍须先成功读取状态。内部公开说明和提交标记不进入 LLM JSON。

结构化读取直接续接动作的实现与验证范围见[验证记录](../research/2026-11-01-observation-sources.md)。

成功时 `structuredContent` 是玩法对象，`content` 同时提供相同对象的紧凑 JSON 文本。[占卜](divination.md)基础观察和详情默认返回文字棋盘，inspect_event可用include_image:true附带独立PNG内容块；图片不进入文字JSON，也不依赖截图工具配置。get_observation没有图片参数，actions_only/top_bar及动作回执不返回棋盘。正文中的换行和空格保留；终端与证据文件使用两空格缩进。对象本身没有排版属性，客户端决定如何转换为模型输入。协议、文本、显示的区别及官方依据见 [项目审阅](../research/2026-10-29-project-review.md#mcp-json-与官方实践)。

输出递归过滤未知字段，不转发原始响应包装、状态令牌或测试入口；`available_actions` 只保留当前可用的公开查看与操作工具，省略观察、截图及测试入口并去重。MCP 与非 raw 文件客户端共用按原生操作的成功解码；基础观察和动作结果检查全部必需顶层观察字段，对已提供的嵌套字段检查类型，再进行输出精简；错误结果不生成新动作令牌，只有上述明确拒绝会保留旧许可。原始文件协议见 [原型接口](roundtrip.md#原型接口)。

## 前进与跳过

`proceed()` 点击当前已显示、启用且可交互的原生 Skip/Proceed。适用奖励、宝箱、火堆、已完成事件、先古之民、占卜结束、商品页已关闭的商店和建筑师最后一行；它可能打开地图、结束子奖励、恢复父事件、换幕或进入结算。后续选择由对应工具处理。对话中段使用 `advance_dialogue`，选牌按钮使用 `selection_option`，结算页使用 `run_result_option`。

[GameAdapter.Proceed.cs](../../src/Sts2Agent/Adapter/GameAdapter.Proceed.cs)集中目标选择、具体拒绝原因和原生点击，执行与 `available_actions` 使用同一判断。保留事件战斗日志、先古之民／宝箱的上下文检查和各原生后续流程；状态过期在目标判断前拒绝，第一次点击前才可证明未提交。参数为 `preset:default/full`，默认 default；返回下述精简动作回执。

## 动作返回格式

出牌、药水、结束回合、选牌、购买、搜刮、选项、选路及结算等游戏动作统一返回以下内容：

| 字段 | 内容 |
| --- | --- |
| `scene`、`screen` | 当前场景、覆盖状态及已识别的查看页 |
| `available_actions` | 当前可用的查看和操作工具名称 |
| `transition` | 原有停止原因、完成标记及完整事件序列，字段见[期间事件](end-turn.md) |
| `potion_discard` | 仅 discard_potion 提供本次请求的槽位、名称及结果；排队与实际事件的关系见[药水动作](potion-actions.md#丢弃结果与排队) |
| `selection` | 仅有待处理选择时出现，只含 `type` 和 `status` |
| `notes` | 仅在需要时提供选牌查看/返回或人工输入提示 |
| `purchase_result`、`reward_result` | 原生流程有相应结果时保留，区分成功、失败及未获得 |
| `card_plays` | 连续出牌及其未完成批次的后续动作返回逐张状态，通过 batch_id 关联；详见[逐张结果](card-play.md#逐张结果) |

实现与单次结果体积对照见[动作回执精简验证](../research/2026-11-01-compact-actions.md)。

回执不附送玩家、敌人、手牌、顶栏、候选牌、升级预览、场景正文、占卜图像或无关空字段。事件不是完整状态差量；最新能量、费用、可出牌标记等不能仅靠战报还原。普通动作可以依据已有信息续接；抽牌、随机生成、费用变化、回合切换或需要新决策信息时，按需使用 `get_observation` 或专项详情。

例如 `play_card → inspect_selection → select_card → inspect_selection → selection_option` 分别读取候选与确认预览，详情同时刷新状态令牌。`get_observation` 的完整内容、`actions_only` 预设、纯详情和切换查看页工具的格式不受动作精简影响。底层文件 IPC 仍保留完整状态和事件，等待稳定及过期校验也使用完整状态。

业务错误为 `isError: true`，包含 `error.code/message/recovery`；执行结果未知时另带 `outcome: unknown`。内部异常写入标准错误，不交给模型；标准输出专用于 MCP 消息。

| 错误 | 恢复方式 |
| --- | --- |
| `observation_required` | 读取当前状态，可用 `get_observation` 或相关专项详情；`recovery` 提供通用的 `get_observation` 恢复入口 |
| `controller_busy` | 断开占用控制权的连接，再观察；当前连接仍可握手和发现工具 |
| `stale_state` | 读取当前状态，再核对动作或页面是否合法 |
| `illegal_action`、`expired_request` | 按 recovery 继续；choose_legal_action 表示已有许可保留，可据已有信息决策，其他情况先观察 |
| `invalid_request` | 对照 schema 修正参数；已有许可按上述规则保留，没有许可时仍须先读取状态 |
| `timeout`、`game_error` | 先观察结果，禁止自动重试动作 |
| `transport_error` | 检查游戏、Mod、IPC 路径、权限与响应格式，再观察 |

## 控制进程与生命周期

每个 IPC 目录只允许一个实际控制游戏的 MCP 连接。初始化和工具发现不占锁；首次游戏请求获取 `.mcp-controller.lock` 系统锁，持有到服务进程退出。其他连接返回 `controller_busy`，不向游戏发请求；原连接断开后可在同一连接重新尝试。不要通过删除锁文件抢占控制权。

连接内部请求串行执行。文件锁只约束本项目 MCP server，不能阻止玩家或直接文件客户端操作，因此 Mod 仍在主线程核对状态令牌与合法性。当前不支持多个 agent 同时控制同一对局。历史启动锁修复见 [记录](../research/2026-10-29-mcp-startup-lock.md)。

## 验证与范围

无需游戏的自动检查见 [代码结构与验证](architecture.md#无需游戏的验证)。独立游戏验证须先按 [往返指南](roundtrip.md) 启动新的测试实例，再在主菜单执行：

```sh
.tmp/mcp-venv/bin/python -m tests.game.verifiers.verify_mcp --report .tmp/roundtrip/mcp-evidence.json
```

该脚本只允许仓库的独立 IPC 目录，会创建临时战斗并推进回合以检查正常动作、连续执行及过期观察，不能用于正式存档。

完整动作链验证先启动新的图形测试实例 `python3 scripts/run_roundtrip.py --windowed --play-scenario armaments_free --potion-scenario skill`，再运行 `.tmp/mcp-venv/bin/python -m tests.game.verifiers.verify_action_observations --report .tmp/action-chain/run.json`。它会连续出牌、使用/丢弃药水、完成选择并切换查看页面，报告目录须全新；结果与范围见[动作观察复用记录](../research/2026-10-30-action-observations.md)。

详情及页面的真实 stdio 验证分别使用 `verify_mcp_hand.py`、`verify_mcp_ui.py`、`verify_mcp_potions.py`、`verify_mcp_combatants.py`、`verify_mcp_relics.py`、`verify_mcp_deck.py`、`verify_mcp_piles.py`、`verify_mcp_map.py`；参数见各脚本 `--help` 和上表对应指南。页面检查会真实打开、切换及关闭页面。

战斗对象专项验证已同步当前结构及工具清单，预设与筛选的完整 GUI 覆盖见[战斗对象验证](combatant-inspection.md#文件入口与验证)。

已有独立游戏与正式游戏的只读采样，及真实 Codex 模型结束一次回合的验证。历史环境、样本和未覆盖项见 [首次 MCP 往返](../research/2026-10-29-mcp-plan.md)、[牌组](../research/2026-10-29-mcp-deck-inspection.md)、[牌堆](../research/2026-10-29-pile-inspection.md) 和 [地图](../research/2026-10-29-mcp-map-inspection.md) 等阶段性记录。

历史外部层兼容重构的检查、样本回放与当时未重新执行的游戏内验证范围见[项目审阅](../research/2026-10-29-project-review.md)。当前只提供 stdio，未实现 HTTP 服务；客户端及场景的实际覆盖以对应验证记录为准。

全部工具的说明、参数提示与官方实践核查见[工具提示词审阅](../research/2026-11-01-mcp-tool-prompts.md)。维护入口和说明分层见[代码结构的变更入口](architecture.md#变更入口)。

统一预设的语义审查、实现与验证范围见[空值语义记录](../research/2026-11-02-default-preset-null-audit.md)。

工具场景、参数与摘要字段的逐项核验清单及工作流程见[工具核验记录](../research/2026-11-02-mcp-tool-review.md)。
