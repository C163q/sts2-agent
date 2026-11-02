# 战斗牌堆查看

Mod `0.34.1` 的文件操作与 MCP server `0.50.6` 的 `inspect_pile` 一起支持抽牌堆、弃牌堆、消耗牌堆。调用真实使用原生入口，默认返回整个可浏览列表的摘要，也支持完整正文和共享悬停解释。页面没有升级或排序控件，接口不提供对应参数。适用游戏为 Linux `v0.107.1`。

## 调用与页面行为

MCP 调用：

```text
inspect_pile(pile="draw")
inspect_pile(pile="discard", detail_level="full")
inspect_pile(pile="exhaust", detail_level="full")
close_card_view()
```

同一操作的文件客户端示例，须先按 [正常加载指南](live-game.md) 安装并重启游戏：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc inspect_pile --pile draw --detail-level full
```

MCP 另接受[通用 preset](mcp.md#输出预设)，默认省略普通空值，例如不可用时省略 cards；显式 full 保留 cards:null。`pile` 必填，只接受 `draw/discard/exhaust`；`detail_level` 可省略，默认 `summary`，另可选 `full`。未知参数、重复 JSON 字段、错误类型及非法枚举在 UI 操作之前拒绝。文件请求的参数放在 `arguments` 对象，`expected_state` 不需要。

非空牌堆实际打开原生页面，返回后保持打开；重复查看同一堆复用页面，信息档位每次独立选择。不同卡牌页共用一层：战斗牌堆按钮在其他卡牌页打开时被原生屏幕上下文禁用，所以跨页先通过原生返回按钮关闭当前页，复核当前状态，再点击目标牌堆。查看牌组也可以替换当前牌堆页。

只允许单人可行动战斗或当前受支持的卡牌查看页；地图、卡牌详情、选择页、其他覆盖层、瞄准/出牌及过渡期间不可穿透读取或点击。地图和卡牌页独立，但地图挡住战斗牌堆入口时，本调用返回 `illegal_action`。关闭沿用 [`close_card_view`](deck-inspection.md)，不会顺带关闭地图。

## 三种结果

| `status` | 行为与 `cards` |
| --- | --- |
| `opened` | 原生页面已打开；`cards` 是整个页面列表，包括滚动区域外卡牌 |
| `empty` | 确实点击了可见且启用的空堆入口，产生原生角色气泡，未打开卡牌页；`cards: []` |
| `unavailable` | 入口不在画面或禁用，未点击目标入口；`cards: null`，`reason` 为 `entry_not_visible/entry_disabled` |

这三种情况均是成功的查看结果，不使用 `error` 包装。其他非法场景、打开失败或等待期间界面变化仍返回结构化错误。隐藏的消耗入口只表示无法查看，不读取内部牌堆来补成空列表；在另一个卡牌页中请求隐藏入口时，也保留当前页。

空抽牌堆与空弃牌堆沿用原生点击气泡；如果此前开着其他卡牌页，先原生返回再点击空堆，结果停在战斗画面。正常空消耗入口隐藏，无须额外 UI 反馈；目标版本没有为空消耗按钮配置气泡，若异常出现可见空消耗入口则拒绝，避免原生空引用错误。

空弃牌堆示例：

```json
{
  "scene": "card_pile",
  "pile": "discard",
  "detail_level": "summary",
  "status": "empty",
  "screen": {"status": "visible"},
  "message": "My Discard Pile is empty.",
  "cards": []
}
```

隐藏消耗入口示例：

```json
{
  "scene": "card_pile",
  "pile": "exhaust",
  "detail_level": "summary",
  "status": "unavailable",
  "screen": {"status": "visible"},
  "message": "The pile button is not visible.",
  "cards": null,
  "reason": "entry_not_visible"
}
```

## 卡牌内容与信息边界

`screen` 是操作后的实际页面状态；非空抽牌堆为 `{"status":"covered","view":"draw_pile"}`，另两堆对应 `discard_pile/exhaust_pile`。`message` 在已打开时是页面底部原生帮助，在空堆时是角色气泡的英语文字，在入口不可用时说明原因。

Mod 0.49.1 起，浏览覆盖不再使实际可见的顶栏整体隐藏；相应药水／遗物可只读查看，战斗动作仍受覆盖限制。规则见[基础观察](observation.md#mcp-输出预设)。

卡牌摘要包含 `id/name/type/rarity/visual_card_pool/energy_cost/star_cost`，语义与 [牌组字段](deck-inspection.md) 一致。`full` 为每张牌增加 `description`，并把附带解释在根级 `hover_tips` 按完整标题和正文去重，以 `card_ids` 关联；可读空列表的完整模式保留 `hover_tips: []`，不可用时不返回解释字段。所有文字使用英语，不切换游戏语言；不附送手牌、敌人意图、动作列表或数值 notes。

抽牌堆沿用原生页面的稀有度及卡名重排结果，绝不返回真实抽牌顺序。弃牌和消耗堆沿用各自原生页面顺序；ID 不表达将来抽取顺序。`pile:` ID 与手牌和永久牌组 ID 分开，同一场战斗内按同一原卡实例稳定，也可跨牌堆对应。新 ID 仅在浏览原生显示列表时分配。

费用、正文、升级后已有数值、战斗临时修改、附魔和关键词使用实际牌堆上下文，不套用手牌瞄准预览。实现读取完整网格列表并使用隔离克隆格式化；线程局部作用域只为当前克隆保留原牌堆上下文，不把克隆放入真实牌堆，不修改持有卡牌。

文件默认 JSON 与 MCP full 一致，均去掉传输控制信息并共享提示。文件客户端加 `--raw` 才保留状态令牌等原始信息及每张牌的解释列表。

## 生命周期与验证

UI 操作在游戏线程执行，异步等待不阻塞游戏。等待期间被人关闭、遮挡或换页时拒绝读取，不自动重开或关闭新页面。界面点击更新状态令牌中的 UI 代次，防止浏览后旧动作令牌重新有效。MCP 在成功校验查看结果后刷新状态令牌，包括空堆或入口不可见的成功结果；打开的牌堆仍须先关闭，才能操作下层界面。非法参数在 IPC 前被拒绝时不清除原权限。超时或取消不自动重试或发清理操作，应重新观察。

文件验证脚本只执行 UI 操作，不出牌或结束回合：

```sh
python3 -m tests.game.verifiers.verify_piles --ipc-dir .tmp/live/ipc --output-dir .tmp/live/piles
```

真实 stdio MCP 验证：

```sh
.tmp/mcp-venv/bin/python -m tests.game.verifiers.verify_mcp_piles --ipc-dir .tmp/live/ipc --output-dir .tmp/live/mcp-piles
```

独立实例用 `run_roundtrip.py --windowed --capture --check-piles` 开启原生测试场景，再运行 `verify_piles.py --ipc-dir .tmp/roundtrip/ipc --output-dir .tmp/roundtrip/piles --exercise-cases`。原生检查覆盖空堆、隐藏入口、非空消耗、整堆及顺序、原卡/RNG/语言不变、跨页替换、同页复用、地图遮挡和异步期间人的操作。测试场景仅允许独立目录，不能在 Steam 正式游戏设置测试标志。

当前实现与验证进度、原生 API 依据及样本位置见 [本次实施记录](../research/2026-10-29-pile-inspection.md)。正式 Mod 0.11.0 已在重启后验证：抽牌堆 7 张、空弃牌堆和隐藏消耗入口均与文件 JSON 一致，完整抽牌堆有 6 条共享解释；查看前后玩法观察相同，未推进回合。正式样本位于 `.tmp/live/mcp-piles/`；非空弃牌/消耗与空抽牌堆由独立夹具覆盖。
