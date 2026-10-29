# 牌组查看与关闭

文件操作 `inspect_deck`、`close_deck` 适用于 Linux 游戏 `v0.107.1`、Mod `0.9.0`。查看时真实打开原生牌组页，一次返回整个可浏览牌组，包括滚动区域外的卡牌；结果返回后页面保持打开，直到显式关闭或人手动返回。本次尚未提供 MCP 工具。

当前仅支持单人可行动战斗中打开牌组，或复用当前未被覆盖的牌组页。打开页面会沿用原生暂停行为，关闭后恢复战斗；这些操作会改变 UI，不是完全无界面副作用的读取。不会出牌、升级实际卡牌、推进回合或自动关闭其他页面。

## 调用

按 [正常游戏加载](live-game.md) 安装并重启。在项目根目录执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_deck
```

默认只返回摘要。查看完整正文与原生升级预览：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_deck --detail-level full --view-upgrades
```

按费用降序排列，关闭升级预览：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_deck --sort-by cost --descending --no-view-upgrades
```

看完后显式返回：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc close_deck
```

`close_deck` 返回关闭后的基础观察，不自动授权下一次战斗动作。关闭后须重新观察，再选择行动。调用不需要 `expected_state`；文件参数校验及当前页面复核仍然生效。页面已经关闭、被其他页面替换或被卡牌详情覆盖时，`close_deck` 返回 `illegal_action`，不会关闭其他页面。

## 参数

文件请求增加可选的 `arguments` 对象，旧调用省略该字段即可。

| JSON 参数 | CLI 参数 | 行为 |
| --- | --- | --- |
| `detail_level` | `--detail-level summary/full` | 默认 `summary`，每次调用独立决定信息量 |
| `view_upgrades` | `--view-upgrades` / `--no-view-upgrades` | 可选布尔值，控制原生升级预览复选框 |
| `sort_by` | `--sort-by obtained/type/cost/name` | 可选主排序：获得顺序、类型、费用、名称 |
| `descending` | `--descending` / `--ascending` | 需同时指定 `sort_by`；省略时显式排序采用升序 |

省略升级或排序参数时，沿用当前页面；新页面采用原生默认的获得顺序升序和不查看升级。指定主排序时保留原生其他排序优先级。名称排序使用游戏当前语言，因此中文界面中的“拼音顺序”不保证对应英语输出的字母顺序。费用排序沿用原生基础卡排序，升级预览降低费用后，显示的预览费用不保证仍按数值排序。

未知字段、错误类型、非法枚举、重复字段或只给排序方向，均返回 `invalid_request`，在打开或修改页面之前拒绝。`close_deck` 及其他既有操作不接受非空参数。首次打开限于可行动战斗，卡牌瞄准/打出、其他详情或覆盖层、过渡期间不可打开；升级控件隐藏或禁用时不能强行切换。

## 返回格式

| 字段 | 内容 |
| --- | --- |
| `scene` | `deck` |
| `detail_level` | 本次 `summary` 或 `full` |
| `view_upgrades` | 页面当前实际的升级预览状态 |
| `sort.by/descending` | 页面当前实际的主排序及方向 |
| `deck[]` | 原生页面完整排序列表；重复卡牌保留独立条目 |
| `deck[].id` | `deck:` 前缀的标识，同一对局内对原卡实例稳定；与战斗手牌 ID 分开 |
| `deck[].name/type/rarity/visual_card_pool` | 英语名称、类型、稀有度及实际外观卡池；卡池不等于持有者角色 |
| `deck[].energy_cost/star_cost` | 与牌组页面相同的费用文字，包括 `X`；没有对应费用图标时为 `null` |
| `deck[].description` | 仅 `full`：英语正文，使用牌组页面或升级预览上下文 |
| `hover_tips[]` | 仅 `full`：共同去重后的附带解释，通过 `card_ids` 关联 |

`summary` 不返回正文或解释字段；`full` 即使没有解释，也保留 `hover_tips: []`。不添加手牌或敌人意图的数值 notes。原始响应保留各卡的解释，默认文件客户端合并到平级列表。加 `--raw` 可查看状态令牌等控制信息。

升级预览仅显示下一次可用升级；不能再升级的卡保持原样，卡牌 ID 不变。描述和数值沿用牌组页面，不套用当前手牌或瞄准目标的预览。实现使用网格的完整排序列表，在隔离克隆上调用原生预览流程；不会修改实际牌组或读取抽牌顺序。

## 生命周期及验证

操作发生在游戏线程，等待页面及帧绘制采用异步流程。等待期间页面被关闭、覆盖或替换会返回 `illegal_action`，不重开页面、不撤销人的操作，也不自动关闭新页面。基础 `get_state` 在牌组覆盖时仍保守返回 `screen.status: covered`，不自动附送整牌组；其他详情调用沿用遮挡拒绝规则。

Mod 将界面操作代次加入状态令牌。通过工具打开、显式切换显示选项或关闭牌组后，即使战斗玩法数值相同，浏览前的令牌仍失效；`ui_generation` 只在原始控制数据中，不交给 LLM。文件 IPC 不支持撤回已经执行的 UI 操作；请求超时或调用方放弃等待后应重新观察当前界面，再决定是否关闭，不能自动重试或假定页面已恢复。

下面脚本会打开、切换升级预览并显式关闭页面，只改变界面；执行期间不要手动操作游戏：

```sh
python3 scripts/verify_deck.py --ipc-dir .tmp/live/ipc --output-dir .tmp/live/deck
```

独立测试实例使用 `scripts/run_roundtrip.py --windowed --capture --check-deck`，完整参数检查另加 `verify_deck.py --exercise-options`，该参数仅接受仓库的独立 IPC 目录。测试入口准备 28 张牌，包括重复卡、已升级卡和不能升级的诅咒，并补齐原生加牌完成通知。不要为正式游戏设置测试标志。来源、结果与未验证范围见 [设计](../research/2026-10-29-deck-view-design.md) 和 [实施记录](../research/2026-10-29-deck-view-plan.md)。

已通过 73 项 Python 回归；独立中文实例的 12 项牌组不变式和 5 项生命周期检查均通过，原有观察与五类详情全部回归通过。摘要、完整和升级样本位于 `.tmp/roundtrip/deck/`；读取了全部 28 张牌，正文及费用的升级预览正确，显式关闭后玩法数值不变且旧令牌被拒绝。

正式游戏重启后也已完成 12 张牌的摘要、完整和升级预览采样。完整模式有 6 条共享解释；Strike、Defend 和 Bash 正确显示升级预览，不能升级的 Ascender's Bane 及已升级的 True Grit+ 保持原样。页面显式关闭后恢复战斗，前后玩法观察相同、控制令牌不同，未推进回合。JSON 和完整响应证据位于 `.tmp/live/deck/`，与独立样本分开保存。
