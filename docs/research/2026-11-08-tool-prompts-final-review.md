# 工具提示词收尾审阅

核对日期：2026-11-08。代码基线：`871939e`，MCP `0.83.0`、Mod `0.80.0`、协议 schema 47。审阅覆盖服务通用说明、43 个玩法工具和可选截图工具的描述及参数提示。

结论：工具职责和主要使用说明符合当前实现，适合保留现有划分。有 3 处文字准确性问题和 4 处表达改进建议，均可通过小范围文字修订处理。本文给出建议，尚未修改运行时提示词、参数约束或游戏行为。

## 应修正的准确性问题

### 1. 基础观察的预设说明扩大了适用范围

`get_observation.preset` 当前写着：

> All presets keep static event/divination summaries.

实际只有 full/default/summary 包含事件／占卜主体。actions_only 仅返回上下文、工具名及必要的选择类型／状态；top_bar 在此基础上增加顶栏。

建议替换为：

> full/default/summary use static event/divination summaries and group map nodes by type. summary further compacts cards, combat and top bars; actions_only returns context and available tool names; top_bar adds top-bar values without relic details.

许可刷新已在通用说明中解释，这里无需重复。

### 2. 通用说明对省略字段的解释过于绝对

当前通用说明仅列出遗物的两个 false 标记，随后声称其他省略绝不表示 false 或空集合。实际 default 还省略 `card_played` 事件的 `autoplay:false`；summary 会省略空的不可出牌标记、空状态列表等。

建议把预设相关的开头合并为：

> Output preset defaults to default: this tool's full content with ordinary null object fields omitted. Array positions, transition event nulls, card comparison sides and displayed treasure.relic:null remain. default also omits relic grayed_out/pulsing:false and card_played autoplay:false. Named presets have additional reductions described by each tool. Use full for explicit nulls and these false flags. Results are snapshots or action receipts, not incremental updates.

这里的 full 指各工具自身的内容范围；基础观察的 full 仍不包含卡牌正文和专用悬停详情。最后一句只说明返回结果不能作为沿用上次字段的增量，不能解释为动作回执含有完整状态。

### 3. UI 来源筛选容易被读成正文开关

`inspect_ui` 当前写着：

> summary lists titles and sources; sources selects descriptions.

实际上 sources 筛选提示来源，preset 决定是否带正文。使用 summary 时，即使传 sources，也不会返回 description。

建议替换为：

> Read hover help for exposed top-bar and combat UI. summary keeps titles and source paths; sources filters tips in any preset. Use default/full with sources to read selected descriptions. Use dedicated inspections for combatants, cards, potions and relics.

## 建议一并改善的表达

1. **基础观察明确所有卡牌正文的入口。** 当前仅强调普通手牌正文需专用查看，未概括选牌、商店、牌组／牌堆与结算卡同样使用无正文牌面。建议工具说明使用：`Read the current screen overview and available tool names. Card effects and hover help are available through dedicated inspections; exposed selections include all browsable candidates.` 预设差异由参数说明承担。
2. **战斗对象筛选增加少量示例。** `canonical paths` 对首次使用者不够具体。sources 参数可补充 `Examples: player, enemies, enemies.0, enemies.0.intents.0.`，并保留省略/null、空数组和位置映射规则。这些示例均为当前支持的路径形式，不增加筛选能力。
3. **连续出牌明确尚未提交的牌不会稍后补打。** 目前说明正确，但只说已入队卡牌可能恢复，容易忽略 not_submitted。建议：`Queue current hand cards in order using native rules. Invalidated plays may be skipped. Choices can pause or cancel queued plays; unsubmitted entries are not saved for later. Check card_plays for each card's status.` 手动手牌选择取消队列的具体差异仍由返回结果及开发指南解释，无需把全部游戏机制塞入描述。
4. **减少工具描述与参数提示的重复。** inspect_hand、inspect_selection、inspect_map 对 summary 和筛选的解释在两层重复。工具描述保留用途、页面副作用和后续入口；具体预设、ID 来源、空筛选和错误合并规则放在参数提示中。费用／目标、满药水槽、奖励放弃、页面持续打开、未知结果后重新读取等会影响操作的提示应保留。无需批量改写其他已经清楚的短描述。

## 分层与官方实践

建议延续现有分层：通用说明负责串行调用、信息边界及错误恢复；工具描述帮助选择工具，并说明其独特后果；参数提示说明取值、来源、默认值及相互关系。

这与 [OpenAI 函数调用指南](https://developers.openai.com/api/docs/guides/function-calling#best-practices-for-defining-functions)对用途、输入格式、输出含义和明确结构的建议一致。[Anthropic 工具设计实践](https://www.anthropic.com/research/writing-tools-for-agents)强调为首次接触工具的人写清楚输入输出，并用实际评测衡量描述调整。[MCP Tools 规范](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)分别定义 description、inputSchema 与 annotations；注解不能替代执行校验。

这些资料不支持单纯以字数最少作为目标。现有错误恢复、未知结果及信息读取说明有实测背景，应保留；文字修订不能代替错误校验，也不能证明模型表现已经改善。

## 核验依据和范围

- 工具目录来自 [tool_registry.py](../../src/sts2_mcp/tool_registry.py)，通用说明来自 [mcp_catalog.py](../../src/sts2_mcp/mcp_catalog.py)。44 个工具的全部对象参数均有非空描述，包含连续出牌的嵌套参数。
- 实际调用预设投影函数确认 actions_only/top_bar 不含事件主体、default 省略 autoplay:false、卡牌 summary 省略空不可出牌标记，以及 UI summary 加 sources 后仍无正文。对照 [空值规则](../../src/sts2_mcp/output/null_fields.py)、[观察预设](../../src/sts2_mcp/output/observation_presets.py)、[UI 预设](../../src/sts2_mcp/output/ui_presets.py)、[卡牌摘要](../../src/sts2_mcp/output/card_summary.py)与[连续出牌说明](../development/card-play.md)。
- 目录快照与直接投影检查保存在 `.tmp/2026-11-08-final-tool-prompts/catalog.json` 和 `audit.json`。通用说明 1617 字符，全部工具描述 7981 字符，含 schema、注解及通用说明的紧凑 JSON 为 38933 字符；这是 Python 字符统计，不是 token 数，尚无修改后对比。
- 工具注册、default、基础观察及 UI 预设的 49 项现有测试通过，结果见同目录 `related-tests.log`。未启动真实游戏，未执行模型游玩对比，未变更游戏调用、参数约束、行为注解或许可机制。

上述三处差异属于提示文字与当前实现不符；本报告保留差异和建议，待文字修订后再更新处理状态。没有据此修改 TODO。
