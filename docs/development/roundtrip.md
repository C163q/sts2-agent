# 最小流程验证指南

适用于 `spikes/roundtrip/` 中的 Linux 验证原型。已验证的游戏基线为 `v0.107.1`，验证内容是读取状态、通过正常动作队列结束回合、读回下一回合状态。本文说明底层文件协议；agent 接入使用 [本地 MCP server](mcp.md)，当前不是完整的自动游玩工具。

## 前提与构建

- 自行安装 Linux 版《杀戮尖塔 2》，按 [README 配置路径](../../README.md#开发与运行入口)，在当前终端加载 `.env`。游戏路径通过 `Sts2Dir` 和 `--game-dir` 传入。
- 安装 .NET 9 SDK；本次使用 `9.0.122`，仓库的 `global.json` 允许同系列更高功能带。需要 .NET 9 引用包，单独安装运行时不足以编译。
- 安装 Python 3；本文原有文件客户端和验证脚本只使用标准库，MCP 服务的额外依赖见接入指南。
- 从 [RitsuLib 0.6.10 官方发布](https://github.com/BAKAOLC/STS2-RitsuLib/releases/tag/v0.6.10) 下载 `STS2.RitsuLib.Compat.0.107.1.0.6.10.github.zip`，解压到自行选择的目录并配置 `RitsuLibDir`。目录须直接包含 `RitsuLib.References.props`、`mod_manifest.json`、根 DLL、`assets.zip`、`shared/` 和 `compat/0.107.1/`，不能只复制根 DLL。发布包 SHA-256：`3c7dafb8a8d36d66891abd6c601aec6f43de9890693d1b583e67e2c6d71ebfb5`。
- 构建引用上述本地库与游戏自带程序集，不下载 NuGet 包，原型目录的 NuGet 配置不启用远程源。

在仓库根目录执行：

```sh
env DOTNET_CLI_HOME=/tmp/sts2-agent-dotnet NUGET_PACKAGES=/tmp/sts2-agent-nuget DOTNET_CLI_TELEMETRY_OPTOUT=1 dotnet build spikes/roundtrip/Sts2Agent.csproj -p:Sts2Dir="${Sts2Dir:?请先配置并加载 .env}" -p:RitsuLibDir="${RitsuLibDir:?请先配置并加载 .env}"
```

```sh
python3 scripts/prepare_roundtrip.py --game-dir "${Sts2Dir:?请先配置并加载 .env}" --ritsu-lib-dir "${RitsuLibDir:?请先配置并加载 .env}"
```

准备脚本把可执行文件、本项目 Mod 和完整 RitsuLib 运行时复制到 `.tmp/roundtrip/runtime/`，用符号链接读取原游戏资源，写入独立测试设置。它不在原游戏目录安装 Mod。重新准备前先停止测试实例。运行目录通过 `installation.json` 绑定首次使用的安装位置；更换位置或发现缺少安装记录的非空运行目录时会拒绝操作，应先保留验证证据再重建 `.tmp/roundtrip`。

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
| `inspect_ancient` | 只读当前先古之民选项及悬停解释 |
| `choose_ancient_option` | 带 `expected_state` 和非负整数 `option_id`，点击一个启用的先古选项 |
| `advance_dialogue` | 带 `expected_state`，点击原生对话继续区域一次 |
| `inspect_rewards` | 只读当前可浏览奖励及悬停说明 |
| `claim_reward` | 带 `reward_id` 和 `expected_state`，点击一项奖励 |
| `proceed` | 带 `expected_state`，点击奖励页或宝箱房跳过/前进、休息处、先古之民或关闭商品页后的商店前进 |
| `open_shop` / `close_shop` | 带 `expected_state`，点击商人或返回按钮 |
| `inspect_shop` | 只读当前已打开商品页的全部详情 |
| `buy_item` | 带 `expected_state`，参数 `item_id` 为非负整数，购买一个当前商品 |
| `inspect_treasure` | 只读暴露的宝箱房和可见遗物悬停说明 |
| `loot_treasure` | 带 `expected_state`，可选布尔 `open_only`；默认开箱并领取，不前进 |
| `inspect_rest_site` | 只读当前休息处选项及动态说明 |
| `choose_rest_option` | 带 `option_id` 和 `expected_state`，点击一个启用的休息处选项 |
| `get_state` | 读取主菜单、战斗、[奖励](rewards.md)、[休息处](rest-site.md)、[宝箱房](treasure.md)、[商店](shop.md)或[先古之民](ancients.md)状态及 `available_actions`；未识别场景归为 `loading_or_noncombat` |
| `inspect_hand` | 只读、无须动作令牌；一次读取全部当前可见手牌的英语正文和悬停解释，格式见 [手牌详情](hand-inspection.md) |
| `inspect_targets` | 参数 `card_id` 或 `potion_slot` 二选一，只读查询可见手牌或药水的可用性与目标范围，见 [出牌](card-play.md) 和 [药水](potion-actions.md) |
| `play_card` | 需最新令牌，参数 `card_id` 与必要的 `target_id`；提交一次原生手动出牌，后续选择单独操作 |
| `use_potion`、`discard_potion` | 需最新令牌，槽位参数 `potion_slot`；使用时仅按查询要求提供 `target_id`，返回事件并停在交互边界 |
| `inspect_ui` | 只读、无须动作令牌；读取当前可见战斗入口与资源图标的英语提示，排除药水、遗物、powers 和敌人意图解释，格式见 [界面说明](ui-inspection.md) |
| `inspect_potions` | 只读、无须动作令牌；读取药水正文和共享解释，保留空槽位置，通用槽位说明只出现一次，格式见 [药水详情](potion-inspection.md) |
| `inspect_combatants` | 只读、无须动作令牌；合并查看当前双方 powers 与敌人意图的英语悬停解释，格式见 [战斗对象详情](combatant-inspection.md) |
| `inspect_relics` | 只读、无须动作令牌；读取当前可见遗物的正文、屏幕计数与共享附带解释，格式见 [遗物详情](relic-inspection.md) |
| `inspect_deck` | 无须动作令牌；真实打开牌组页并保留，返回全牌组，支持信息档位、升级预览和排序，格式见 [牌组查看](deck-inspection.md) |
| `inspect_pile` | 无须动作令牌；实际点击并查看抽牌、弃牌或消耗堆，支持摘要/完整；区分空堆与隐藏入口，见 [战斗牌堆查看](pile-inspection.md) |
| `inspect_map` | 无参数，无须动作令牌；真实打开/复用整个当前幕地图，返回节点连线和当前原生可选节点，见 [地图查看](map-inspection.md) |
| `close_map` | 无参数，无须动作令牌；仅在原生返回按钮可用且地图未被覆盖时关闭，不穿透卡牌页 |
| `close_card_view` | 无须动作令牌；显式关闭当前原生卡牌查看页，返回基础观察；保留下层地图，不关闭其他页面或自动授权战斗动作 |
| `close_deck` | 仅为旧文件客户端兼容保留，只关闭牌组；MCP 使用通用 `close_card_view` |
| `start_test_combat` | 仅测试模式且无进行中的对局时，在主菜单创建临时对局并用游戏开发入口进入指定战斗；该操作不是正常游玩的动作 |
| `inspect_selection` | 当前原生选择的全部可浏览候选与详情；见 [选牌接口](card-selection.md) |
| `select_card`、`selection_option` | 需最新状态令牌，参数分别为 `card_id`、`option_id`，提交一次原生选择输入 |
| `set_selection_view` | 参数 `view` 为 `battlefield` 或 `selection`，显式点击眼睛 |
| `end_turn` | 单人战斗、玩家可行动阶段且非暂停状态下，提交 `EndPlayerTurnAction`，返回期间事件，到下一可行动回合、已识别的选择或战斗结束时停止；见 [结束回合](end-turn.md) |

请求写入 `requests/<id>.json`，其中 `id` 是不带连字符的 UUID；先写临时文件再原子重命名为 `.json`。请求体包含 `id`、`operation`；动作另带 `expected_state`，有参数操作的选项放在 `arguments` 对象中。响应写入 `responses/<id>.json`，成功包含 `ok: true` 和 `state`，失败包含 `ok: false` 和 `error.code`、`error.message`。

- 文件读写和等待在后台进行，状态读取与动作提交在 Godot 主线程进行；当前串行处理请求。
- `snapshot_id` 根据当前导出的观察内容、进程会话、战斗代次、工具界面操作代次、选择实例代次及药水实例代次生成。动作在主线程核对令牌和合法性后提交，选牌若跨帧滚动还会在点击前核对候选、已选和数量规则；通过工具查看并关闭牌组后旧令牌不会恢复，须重新观察。这不是对所有游戏内部状态或两次请求之间全部人工 UI 操作历史的完整版本标识。
- 相同请求 ID 且缓存响应仍在时返回原结果。重复请求不分配新 ID；删除响应缓存后不再保证同一 ID 不会再次执行。
- `stale_state` 表示缺少或不匹配的状态令牌，`illegal_action` 表示当前不可执行，`invalid_request` 表示请求格式有误，`expired_request` 表示执行前已过期，`game_error` 表示游戏调用异常。
- `timeout` 或客户端超时后，动作是否已执行可能不确定。应先重新观察，不能自动换一个 ID 重试动作。创建测试场景过程中发生错误也可能已经部分推进游戏。

## 验证边界

底层动作流程已在独立实例中实测；无头启动存在 FMOD 音频初始化、音频资源及虚拟渲染器警告，不覆盖声音。图形观察的验证范围另见战斗观察说明，不能将无头验证描述为没有运行警告。

原型已扩展可见战斗观察，字段与验证方式见 [战斗观察 JSON](observation.md)，范围按 [可见信息边界](../observation.md) 维护；未展开的手牌效果由专门查看调用提供。动作支持结束回合、出牌、使用/丢弃药水和已接通的选牌；stdio MCP 的当前工具范围见 [接入指南](mcp.md)。地图推进、多玩家、断线恢复和异常退出恢复尚未覆盖。通信目录假设仅由可信的本地程序访问，不作为远程服务。

API 核对依据与实测结果见 [验证记录](../research/2026-10-28-roundtrip-validation.md)。
