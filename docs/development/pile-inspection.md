# 战斗牌堆查看

版本与依赖基线见[项目 README](../../README.md#当前版本与前提)。

文件操作及 MCP 工具 `inspect_pile` 支持抽牌堆、弃牌堆、消耗牌堆。调用真实使用原生入口，默认 default 返回整个可浏览列表的完整正文与共享悬停解释，也支持手牌共用摘要。页面没有升级或排序控件，接口不提供对应参数。

## 调用与页面行为

MCP 调用：

```text
inspect_pile(pile="draw")
inspect_pile(pile="discard", preset="full")
inspect_pile(pile="discard", preset="summary", card_ids=["pile:3"])
inspect_pile(pile="exhaust", preset="full")
close_card_view()
```

同一操作的文件客户端示例，须先按 [正常加载指南](live-game.md) 安装并重启游戏：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_pile --pile draw --preset full
```

MCP 另接受[通用 preset](mcp.md#输出预设)，默认省略普通空值，例如不可用时省略 cards；显式 full 保留 cards:null。`pile` 必填，只接受 `draw/discard/exhaust`；`preset` 默认 `default`，另可选 `full/summary`；不回显该参数。`card_ids` 可选，规则见下文。旧 `detail_level` 请求在 UI 操作前拒绝。未知参数、重复 JSON 字段、错误类型及非法枚举在 UI 操作之前拒绝。底层文件请求的 `arguments` 只含 pile，始终读取完整内容；preset／card_ids 由 MCP／文件 CLI 投影。`expected_state` 不需要。

## 卡牌筛选

`card_ids` 使用当前战斗的 `pile:N` 字符串；省略或 null 取全部，[] 不取卡牌，重复 ID 去重，结果保持原生页面顺序。它们与手牌整数、永久牌组 `deck:N` 分开。筛选只裁剪返回内容，仍打开／复用目标页；不改变页面列表、抽牌顺序或后续基础观察。

可读取的目标堆中，存在的 ID 正常返回；不在目标堆的 ID 合并为 `errors:[{"code":"cards_not_in_pile","card_ids":["pile:99"]}]`，整体仍成功。一个 ID 在其他牌堆存在也计为不在当前堆。共享 hover_tips 同步裁剪，引用仍为原卡 ID。完整原生回复先校验，空筛选或 summary 不能掩盖坏卡。

empty 的已知集合为 []，因此指定 ID 会报告不在该堆；unavailable 表示集合未知，不检查成员、不附缺失 ID 错误，也不读取隐藏内容。非法 ID 语法／类型始终在 UI 操作之前拒绝。

普通文件 CLI 同样支持 `--card-ids pile:3 pile:8`；仅写 `--card-ids` 表示 []，省略取全部。

## 页面行为

非空牌堆实际打开原生页面，返回后保持打开；重复查看同一堆复用页面，信息档位每次独立选择。不同卡牌页共用一层：战斗牌堆按钮在其他卡牌页打开时被原生屏幕上下文禁用，所以跨页先通过原生返回按钮关闭当前页，复核当前状态，再点击目标牌堆。查看牌组也可以替换当前牌堆页。

只允许单人可行动战斗或当前受支持的卡牌查看页；地图、卡牌详情、选择页、其他覆盖层、瞄准/出牌及过渡期间不可穿透读取或点击。地图和卡牌页独立，但地图挡住战斗牌堆入口时，本调用返回 `illegal_action`。关闭沿用 [`close_card_view`](deck-inspection.md)，不会顺带关闭地图。

scene/screen 遵循[统一上下文](observation.md#场景上下文)；打开页使用 screen.view 的 draw_pile/discard_pile/exhaust_pile，scene 保留当前战斗场景。

## 三种结果

| `status` | 行为与 `cards` |
| --- | --- |
| `opened` | 原生页面已打开；`cards` 是整个页面列表，包括滚动区域外卡牌 |
| `empty` | 确实点击了可见且启用的空堆入口，产生原生角色气泡，未打开卡牌页；`cards: []` |
| `unavailable` | 入口不在画面或禁用，未点击目标入口；`cards: null`，`reason` 为 `entry_not_visible/entry_disabled` |

这三种情况均是整体允许牌堆浏览时的成功查看结果，不使用 `error` 包装；整体门控允许复用已暴露且就绪的当前牌堆页；打开其他页面时还要求至少一个牌堆入口可用或能在关闭当前页后操作。所有入口都不可用、其他非法场景、打开失败或等待期间界面变化仍返回结构化错误。隐藏的消耗入口只表示无法查看，不读取内部牌堆来补成空列表；在另一个卡牌页中请求隐藏入口时，也保留当前页。

空抽牌堆与空弃牌堆沿用原生点击气泡；如果此前开着其他卡牌页，先原生返回再点击空堆，结果停在战斗画面。正常空消耗入口隐藏，无须额外 UI 反馈；目标版本没有为空消耗按钮配置气泡，若异常出现可见空消耗入口则拒绝，避免原生空引用错误。

空弃牌堆示例：

```json
{
  "scene": "combat",
  "pile": "discard",
  "status": "empty",
  "screen": {"status": "visible"},
  "message": "My Discard Pile is empty.",
  "cards": []
}
```

隐藏消耗入口示例：

```json
{
  "scene": "combat",
  "pile": "exhaust",
  "status": "unavailable",
  "screen": {"status": "visible"},
  "message": "The pile button is not visible.",
  "cards": null,
  "reason": "entry_not_visible"
}
```

## 卡牌内容与信息边界

`screen` 是操作后的实际页面状态；非空抽牌堆为 `{"status":"covered","view":"draw_pile"}`，另两堆对应 `discard_pile/exhaust_pile`。`message` 在已打开时是页面底部原生帮助，full/default 保留，summary 省略；空堆气泡和入口不可用原因在所有预设保留。

浏览覆盖不再使实际可见的顶栏整体隐藏；相应药水／遗物可只读查看，战斗动作仍受覆盖限制。规则见[基础观察](observation.md#mcp-输出预设)。

full/default 卡牌沿用[共用完整格式](hand-inspection.md#格式)，包括正文、费用和可见外观，并把附带解释在根级 `hover_tips` 按完整标题和正文去重，以 `card_ids` 关联；summary 沿用[共用卡牌摘要](hand-inspection.md#参数与返回范围)，省略正文、稀有度、卡池及解释。可读空列表的完整模式保留 `hover_tips: []`，不可用时不返回解释字段。所有文字使用英语，不切换游戏语言；不附送手牌、敌人意图、动作列表或数值 notes。

抽牌堆沿用原生页面的稀有度及卡名重排结果，绝不返回真实抽牌顺序。弃牌和消耗堆沿用各自原生页面顺序；ID 不表达将来抽取顺序。`pile:` ID 与手牌和永久牌组 ID 分开，同一场战斗内按同一原卡实例稳定，也可跨牌堆对应。新 ID 仅在浏览原生显示列表时分配。

费用、正文、升级后已有数值、战斗临时修改、附魔和关键词使用实际牌堆上下文，不套用手牌瞄准预览。实现读取完整网格列表并使用隔离克隆格式化；线程局部作用域只为当前克隆保留原牌堆上下文，不把克隆放入真实牌堆，不修改持有卡牌。

文件 CLI 和 MCP 使用相同预设投影，均去掉传输控制信息并共享提示。文件客户端加 `--raw` 才保留状态令牌等原始信息及每张牌的解释列表。

## 已打开牌堆的基础观察

get_observation 在当前牌堆页已暴露、就绪且底部说明可读时返回 pile、cards、message；full/default/summary 的卡牌分别使用 face_full／face_default／共用 summary，均不含正文或悬停解释。完整列表、当前顺序、卡牌 ID 与专用查看共用原生读取器，固定 message 在 full/default 保留、summary 省略。

基础观察仅只读当前页，不点击入口，不继承先前 card_ids 筛选；未打开、被更高层遮挡或关闭后不附缓存列表。actions_only/top_bar 不增加这三个字段。其余观察与顶栏规则见[基础观察](observation.md#mcp-输出预设)。

## 生命周期与验证

UI 操作在游戏线程执行，异步等待不阻塞游戏。等待期间被人关闭、遮挡或换页时拒绝读取，不自动重开或关闭新页面。界面点击更新状态令牌中的 UI 代次，防止浏览后旧动作令牌重新有效。MCP 在成功校验查看结果后刷新状态令牌，包括空筛选、空堆或入口不可见的成功结果；打开的牌堆仍须先关闭，才能操作下层界面。非法参数在 IPC 前被拒绝时不清除原许可；原生明确保证该请求未进行 UI 交互时，也保留已有许可并给出安全具体原因。没有旧许可不会因失败而获得许可；关闭旧页／点击目标后的失败、矛盾证据、过期、超时或取消不能恢复旧许可。超时／取消不自动重试或发清理操作，应重新观察，完整语义见[MCP 错误规则](mcp.md#调用和错误语义)。

文件验证脚本只执行 UI 操作，不出牌或结束回合：

```sh
python3 -m tests.game.verifiers.verify_piles --ipc-dir .tmp/live/ipc --output-dir .tmp/live/piles
```

真实 stdio MCP 检查三堆与预设，并将 close_card_view 和共享 actions_only 投影比较：

```sh
.tmp/mcp-venv/bin/python -m tests.game.verifiers.verify_mcp_piles --ipc-dir .tmp/live/ipc --output-dir .tmp/live/mcp-piles
```

独立实例用 `run_roundtrip.py --windowed --capture --check-piles` 开启原生测试场景，再运行 `verify_piles.py --ipc-dir .tmp/roundtrip/ipc --output-dir .tmp/roundtrip/piles --exercise-cases`。原生检查覆盖空堆、隐藏入口、非空消耗、整堆及顺序、原卡/RNG/语言不变、跨页替换、同页复用、地图遮挡和异步期间人的操作。测试场景仅允许独立目录，不能在 Steam 正式游戏设置测试标志。

源码依据及历史独立／正式游戏采样见[牌堆实施记录](../research/2026-10-29-pile-inspection.md)，后续可用性范围见[工具可用性修复](../research/2026-11-02-available-actions-fix.md)。验证记录仅覆盖其注明的代码基线和测试场景。

筛选、基础观察与错误恢复的专项使用 [pile_inspection GUI 清单](../../tests/game/data/gui_suite_pile_inspection.json)；实现与验证证据见[牌堆输出实施](../research/2026-11-04-pile-inspection-implementation.md)。
