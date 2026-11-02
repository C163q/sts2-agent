# 牌组查看与关闭

文件操作及 [MCP 工具](mcp.md) `inspect_deck`、`close_card_view` 适用于 Linux 游戏 `v0.107.1`、Mod `0.44.0`。查看时真实打开原生牌组页，一次返回整个可浏览牌组，包括滚动区域外的卡牌；结果返回后页面保持打开，直到显式关闭或人手动返回。MCP full 返回相同玩法 JSON，默认 default 省略普通空值；当前服务版本为 `0.50.3`。

牌组、抽牌堆、弃牌堆和消耗牌堆共用单一卡牌查看层，打开其中一种会替换当前卡牌页；地图是独立界面。支持单人可行动战斗及原生牌组按钮可用的非战斗页面，包括事件、先古之民、火堆、宝箱、奖励和商店；也可从地图或战斗牌堆页打开，并复用当前未被覆盖的牌组页。三类牌堆通过 [战斗牌堆查看](pile-inspection.md) 访问，保留原生空堆反馈，仍使用同一个关闭工具。打开与关闭沿用原生暂停/恢复行为；地图上打开牌组时，关闭卡牌页仍保留地图，不自动再关闭地图。这些操作会改变 UI，不是完全无界面副作用的读取。不会出牌、升级实际卡牌、推进回合或自动关闭其他页面。

## 调用

按 [正常游戏加载](live-game.md) 安装并重启。在项目根目录执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_deck
```

detail_level 默认只返回摘要，与[通用 preset](mcp.md#输出预设)独立；需要保留空值时传 `preset:"full"`。查看完整正文与原生升级预览：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_deck --detail-level full --view-upgrades
```

按费用降序排列，关闭升级预览：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_deck --sort-by cost --descending --no-view-upgrades
```

看完后显式关闭顶层卡牌查看页：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc close_card_view
```

`close_card_view` 同时支持原生牌组、抽牌堆、弃牌堆和消耗牌堆查看页，返回关闭后的基础观察；MCP 可直接使用该成功结果继续操作当前界面，无需再次观察。调用不需要 `expected_state`；文件参数校验及当前页面复核仍然生效。当前没有受支持的卡牌查看页，或页面被卡牌详情等更高层界面覆盖时，`close_card_view` 返回 `illegal_action`，不会关闭其他页面。

## 参数

文件请求增加可选的 `arguments` 对象，旧调用省略该字段即可。

| JSON 参数 | CLI 参数 | 行为 |
| --- | --- | --- |
| `detail_level` | `--detail-level summary/full` | 默认 `summary`，每次调用独立决定信息量 |
| `view_upgrades` | `--view-upgrades` / `--no-view-upgrades` | 可选布尔值，控制原生升级预览复选框 |
| `sort_by` | `--sort-by obtained/type/cost/name` | 可选主排序：获得顺序、类型、费用、名称 |
| `descending` | `--descending` / `--ascending` | 需同时指定 `sort_by`；省略时显式排序采用升序 |

省略升级或排序参数时，沿用当前页面；新页面采用原生默认的获得顺序升序和不查看升级。指定主排序时保留原生其他排序优先级。名称排序使用游戏当前语言，因此中文界面中的“拼音顺序”不保证对应英语输出的字母顺序。费用排序沿用原生基础卡排序，升级预览降低费用后，显示的预览费用不保证仍按数值排序。

未知字段、错误类型、非法枚举、重复字段或只给排序方向，均返回 `invalid_request`，在打开或修改页面之前拒绝。`close_card_view` 及其他既有操作不接受非空参数。首次打开须满足当前原生按钮可见且启用，以及受支持页面的遮挡规则；卡牌瞄准/打出、选牌页、模态弹窗、其他详情或过渡期间不可打开。结算页不属于可打开牌组的对局页面；升级控件隐藏或禁用时不能强行切换。

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

非战斗查看及可用工具一致性的实现与验证范围见[修复记录](../research/2026-11-02-available-actions-fix.md)。

操作发生在游戏线程，等待页面及帧绘制采用异步流程。等待期间页面被关闭、覆盖或替换会返回 `illegal_action`，不重开页面、不撤销人的操作，也不自动关闭新页面。基础 `get_state` 在牌组覆盖时仍保守返回 `screen.status: covered`，不自动附送整牌组；手牌和战斗对象详情仍沿用遮挡拒绝规则，Mod 0.49.1 起实际可见顶栏及可悬停的药水／遗物可只读查看，见[观察边界](observation.md#mcp-输出预设)。

Mod 0.10.0 在 `screen.view` 标记 `deck/draw_pile/discard_pile/exhaust_pile/map` 等受支持查看页。只关闭最上面的卡牌页：战斗叠地图叠牌组时，返回地图；地图单独打开时调用通用关闭会拒绝。当前版本原生容器关闭会调用 `Unpause`，即使地图仍打开；本项目不增加自定义暂停计数，地图仍按遮挡页面处理，不能据此执行战斗动作。

旧文件操作 `close_deck` 仅为兼容保留，仍只关闭牌组，不注册为 MCP 工具。

Mod 将界面操作代次加入状态令牌。通过工具打开、显式切换显示选项或关闭牌组后，即使战斗玩法数值相同，浏览前的令牌仍失效；`ui_generation` 只在原始控制数据中，不交给 LLM。文件 IPC 不支持撤回已经执行的 UI 操作；请求超时或调用方放弃等待后应重新观察当前界面，再决定是否关闭，不能自动重试或假定页面已恢复。

下面脚本会打开、切换升级预览并显式关闭页面，只改变界面；执行期间不要手动操作游戏：

```sh
python3 -m tests.game.verifiers.verify_deck --ipc-dir .tmp/live/ipc --output-dir .tmp/live/deck
```

独立测试实例使用 `scripts/run_roundtrip.py --windowed --capture --check-deck`，完整参数检查另加 `verify_deck.py --exercise-options`，该参数仅接受仓库的独立 IPC 目录。测试入口准备 28 张牌，包括重复卡、已升级卡和不能升级的诅咒，并补齐原生加牌完成通知。不要为正式游戏设置测试标志。来源、结果与未验证范围见 [设计](../research/2026-10-29-deck-view-design.md) 和 [实施记录](../research/2026-10-29-deck-view-plan.md)。

已通过 73 项 Python 回归；独立中文实例的 12 项牌组不变式和 5 项生命周期检查均通过，原有观察与五类详情全部回归通过。摘要、完整和升级样本位于 `.tmp/roundtrip/deck/`；读取了全部 28 张牌，正文及费用的升级预览正确，显式关闭后玩法数值不变且旧令牌被拒绝。

正式游戏重启后也已完成 12 张牌的摘要、完整和升级预览采样。完整模式有 6 条共享解释；Strike、Defend 和 Bash 正确显示升级预览，不能升级的 Ascender's Bane 及已升级的 True Grit+ 保持原样。页面显式关闭后恢复战斗，前后玩法观察相同、控制令牌不同，未推进回合。JSON 和完整响应证据位于 `.tmp/live/deck/`，与独立样本分开保存。

通用关闭新增的 7 项独立原生检查已通过，涵盖三类牌堆、地图单独不关闭、地图上打开牌组及返回地图。新版真实 MCP 在独立实例完成 28 张牌浏览，Python 全套 84 项通过。Mod 0.10.0 的正式 MCP 采样也已通过：12 张牌，连续查看、升级及显式通用关闭均正常，前后玩法观察一致，样本位于 `.tmp/live/mcp-deck/`。实施证据见 [MCP 接入记录](../research/2026-10-29-mcp-deck-inspection.md)。

Mod 0.11.0 增加 [战斗牌堆查看](pile-inspection.md) 后，既有牌组真实 stdio MCP 已在独立实例回归通过：28 张牌、摘要/完整/升级、重复查看和通用关闭均正常，样本位于 `.tmp/roundtrip/mcp-deck-0.11/`。
