# 三类战斗牌堆查看

当前状态：已完成。共 4 项，已完成 4 项；Mod、文件接口与 MCP 已实现、安装并通过正式游戏重启验证。独立原生 30 项及真实 stdio MCP 均通过，独立审阅无遗留问题；最终 Python 回归结果见下。暂无阻塞。

## 范围与契约

一次实现抽牌堆、弃牌堆、消耗牌堆的文件接口与 MCP，统一使用 `inspect_pile(pile, detail_level="summary")`。`pile` 必填，仅 `draw/discard/exhaust`；信息档位仅 `summary/full`。不提供游戏页面没有的升级或排序选项。无效参数在改变界面之前拒绝。

返回 `scene: card_pile`、`pile`、`detail_level`、`status`、当前 `screen`、英语 `message` 及 `cards`。不同卡牌页之间切换时，原生 `NCombatRoom.OnActiveScreenUpdated` 会禁用底层牌堆按钮；工具先点击当前卡牌页的原生返回，再确认目标入口可见、启用且游戏状态有效，才点击目标牌堆。不会强行点击禁用按钮。

三种结果：

- `opened`：真实点击可见且启用的原生入口，返回原生网格的整个列表；页面保持打开。再次查看同一牌堆复用页面，避免原生按钮的再次点击关闭行为。卡牌字段与牌组两档一致，使用独立的 `pile:` ID；ID 在同一场战斗内按卡实例稳定。不同牌堆互相替换，牌组与牌堆也可互换。
- `empty`：仅在可见、启用的入口经原生点击且确认无卡牌页打开后返回 `cards: []`；`message` 为原生空堆气泡的英语文本。包括原生点击关闭此前卡牌页的副作用，不伪造一个空页面。
- `unavailable`：入口不在画面时不点击，返回 `cards: null`、`reason: entry_not_visible`，仅解释入口不可见，不读取隐藏牌堆来断言为空。入口存在但禁用则 `reason: entry_disabled`。其他界面遮挡、出牌/瞄准或不支持的游戏阶段仍按 `illegal_action` 拒绝，不读背后的内容。

`full` 时仅实际读到列表（包括空列表）才返回共享 `hover_tips`，按完全相同的标题和正文去重并以 `card_ids` 关联。`summary` 不含正文与解释。`message` 在已打开时来自页面底部原生说明，包含抽牌堆显示顺序的解释。输出固定英语，不改变游戏语言。

抽牌堆必须使用原生页面排列后的列表，不能返回模型的真实抽牌顺序，也不能根据真实顺序分配新 ID。弃牌、消耗牌沿用各自页面列表和上下文。卡牌读取使用隔离克隆，不重算实际持有卡；不生成随机选项，不推进回合。原生卡牌页关闭使用已有 `close_card_view`，保留下层地图；地图挡住战斗牌堆入口时不得穿透点击。

所有 UI 点击递增已有 UI 代次，旧动作令牌失效。MCP 的有效查看调用无论成功、空堆、入口不可见或失败，均清除之前动作授权；参数在 IPC 前被拒绝时保留已有授权。沿用全局串行锁、控制连接租约和超时/取消不自动重试、不关闭页面的规则。

## 原生依据

核对日期：2026-10-29；游戏 Linux `v0.107.1`、main、提交 `59260271`。程序集位于安装目录 `data_sts2_linuxbsd_x86_64/sts2.dll`；反编译证据仅留本地 `.tmp/decompiled/`。

- `NCombatUi.DrawPile/DiscardPile/ExhaustPile` 提供三个实际按钮；`NCombatCardPile.OnRelease` 负责非空打开、同堆再次点击关闭、空堆关闭卡牌页并创建 `NThoughtBubbleVfx`。
- `NDrawPileButton._Ready` 使用 `combat_messages/OPEN_EMPTY_DRAW`；`NDiscardPileButton._Ready` 使用 `OPEN_EMPTY_DISCARD`。可见空消耗按钮没有原生空堆气泡配置，若出现该异常状态则拒绝调用，不触发原生空引用错误。
- `NExhaustPileButton._Ready/Initialize/AddCard` 初始隐藏并禁用，非空初始化或原生加牌完成时显示及启用；不能强行 `ForceClick` 隐藏按钮。
- `NCardPileScreen.OnPileContentsChanged` 将抽牌堆按稀有度、内部卡名顺序重排，再交 `NCardGrid.SetCards`；其他牌堆保留页面列表顺序。读取网格 `_cards`，不读取真实抽牌顺序。
- `NCardPileScreen._Ready` 使用 `gameplay_ui/DRAW_PILE_INFO`、`DISCARD_PILE_INFO`、`EXHAUST_PILE_INFO`，没有升级或排序控件。
- `NCardGrid` 完整列表包含当前滚动区域外卡牌；`NCard.UpdateVisuals` 接受实际牌堆上下文。
- `CardModel.Pile` 根据原卡在持有者牌堆中的成员关系返回结果，隔离克隆不在真实牌堆中；对本次读取的唯一克隆用线程局部作用域保留原牌堆上下文，结束后必定恢复。该补丁对其他卡牌及正常 UI 不生效，用于保持战斗费用、正文和关键词语义，仍不把克隆加入实际牌堆。

## 实施与验证

1. 已完成：参数/投影/共享解释测试，以及独立原生场景验证脚本先行；旧实现分别因缺少 MCP 方法、文件操作不接受参数而按预期失败。
2. 已完成：Mod 牌堆查看、稳定身份、卡牌上下文和原生入口交互；覆盖空堆与隐藏入口，扩展牌组和牌堆相互替换。
3. 已完成：接入单一 MCP 工具，补 SDK 协议及错误/超时/取消测试；回归旧工具发现列表。服务为 0.8.0，共 10 工具；未更改用户禁用的 Codex 连接配置。
4. 已完成：构建、全套 Python、独立中文游戏、原生检查、真实 stdio MCP 及独立审阅均通过；持续文档已同步，Mod 0.11.0 已安装、重启并在正式对局完成读取。最终构建再跑原生 30 项，无 Godot ERROR；既有牌组 MCP 的 28 张牌、升级和关闭也回归通过。

重点验证：空弃牌堆气泡及关闭旧页面；空抽牌堆点击；隐藏消耗不触发点击、不暴露内容；非空消耗；跨页替换及同页复用；抽牌堆排序而非真实抽牌顺序；已打开页面在异步等待中被关闭/替换/遮挡时拒绝且不干涉新页；地图及其他遮挡拒绝穿透；读取不改变原卡、语言、RNG 或回合。

## 验证证据

- `dotnet build` 通过，零警告、零错误；Mod 为 0.11.0。
- Python 全套 91 项通过（17.448 秒），包括 7 项新增牌堆行为测试、真实 stdio 十工具发现、三类参数调用、连接竞争、清除动作权限、格式错误投影、超时和取消；日志 `.tmp/piles-all-tests.log`。
- 中文独立实例原生 30 项全部通过，证据 `.tmp/roundtrip/pile-checks.json`。测试生成足够多的卡以覆盖屏外列表，确认原生显示排序与真实抽牌顺序不同；临时能量费用 0、星数费用 2 及 Corruption 对技能的费用归零均与真实渲染一致，读完原卡、RNG 和语言不变。
- 原生空抽/弃牌堆气泡和非空三类页面截图保存在 `.tmp/roundtrip/piles-*.png`；面向 LLM 的各类 JSON 样本位于 `.tmp/roundtrip/piles/`。测试气泡仍使用游戏中文，返回内容使用英语。
- 真实官方 Python SDK stdio MCP 已通过，服务 0.8.0，协议 2025-11-25，工具列表固定 10 项；摘要/完整与文件 JSON 一致，重复查看、空弃牌堆及隐藏消耗均正确，浏览关闭前后玩法观察一致、旧控制令牌不同。证据 `.tmp/roundtrip/mcp-piles/`。
- 生命周期测试以原生 `RenderingServer.FramePreDraw` 在等待期间注入人的关闭/覆盖/换页；三种情况均返回 `illegal_action`，保留新界面，不发送自动清理。
- 独立代码审阅没有 Critical/Important；最初指出临时费用验证不足，补上临时能量/星数和 Corruption 后复审无遗留问题。

测试过程中发现两处测试夹具问题并修正：`CardPileCmd.Add(skipVisuals:true)` 不发送原生动画完成通知，夹具须逐卡补齐通知；`SceneTree.ProcessFrame` 不保证早于当前帧绘制后读取，生命周期检查改用已核实的 `FramePreDraw`。最终夹具避免重复解绑静态绘制信号。均仅影响隔离检查，不在正常游戏开启。

未验证范围：其他游戏版本、多人、全卡池/其他 Mod 的自定义卡牌及非战斗页面。没有进行模型自动游玩、出牌或结束回合。

## 正式对局采样与安装

Mod 0.11.0 已用编号备份方式安装，安装 DLL 与最终构建的 SHA256 均为 `effdf76e0014881b9b2fc63e0ca9603d1ffbb168d21708dcc11860a19546c262`，manifest 均为 `70605bad2b317a8728e835ecbb018e481d1e80af50af4bb9094b41e809b5e78a`。用户重启后，通过真实 SDK stdio MCP 完成正式对局采样：

- 抽牌堆 7 张，摘要/完整及重复查看正常，完整模式 6 条共享解释，页面保持到显式关闭。
- 弃牌堆为空，原生点击后返回 `empty`、`cards: []` 和英语气泡内容；完整模式有空的 `hover_tips`。
- 消耗入口隐藏，返回 `unavailable`、`entry_not_visible`、`cards: null`，不点击或补出隐藏内容。
- 文件与 MCP JSON 一致，三类各有摘要/完整样本；前后玩法 JSON 相同，控制令牌不同，没有出牌或结束回合。

正式样本与原始证据位于 `.tmp/live/mcp-piles/`，与独立夹具样本分开。非空弃牌堆、非空消耗及空抽牌堆由独立原生场景覆盖，本次正式场景没有这些状态。
