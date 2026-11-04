# 头槌的牌堆移动事件核验

> 当前状态：核验、实现及验证完成，MOVE-01 已与 TURN-01–03 合并交付，见[实施记录及新返回](2026-11-04-turn-transitions-implementation.md)。下述 8 份旧返回保留缺口基线；定稿明确不提供 position。暂无阻塞。

## 优先关注的问题

| 编号 | 优先级 | 已核实问题 | 影响与处理状态 |
| --- | --- | --- | --- |
| MOVE-01 | 中；可见事件缺失 | 头槌确实把已有牌从弃牌堆放回抽牌堆，但 transition.events 不记录这次移动；多候选时，选牌并结算后的 select_card 甚至直接返回 events:[]；只有一张弃牌、原生自动选择时同样缺失 | 审阅基线问题；已接入共用 card_moved 修复，最终结果见实施记录。不是 card_added 目的地报错，也不是 end_turn 本身漏掉后来才发生的事情 |

## 基线及证据

- 日期：2026-11-04；代码 `ca96b78` 加仅测试场景补充。Mod `0.61.0`、MCP `0.63.0`、schema `40`；当前版本统一见 [README](../../README.md#当前版本与前提)。
- 游戏 Linux `v0.107.1`，release build `59260271`；RitsuLib `0.6.10` 兼容运行时。游戏安装目录相对路径 `data_sts2_linuxbsd_x86_64/sts2.dll` 的 SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- 核对目标程序集的 `Headbutt.OnPlay`、`CardSelectCmd.FromCombatPile`、`CardPileCmd.Add`、`NCardFlyVfx`；本地反编译证据位于 `.tmp/2026-11-04-headbutt-review/source/`，不纳入 Git。
- 构建与隔离运行时的 DLL 均为 `c48321d25316460196960c5e1025ec69b87d0f6fe1f5282591929c6710407820`。只在 [PlayFixture](../../src/Sts2Agent/Testing/Fixtures/PlayFixture.cs) 及[测试白名单](../../tests/game/data/test_scenarios.json)增加 headbutt，以原生卡牌 API 准备手牌；生产日志代码没有变化。不把这个测试构建冒充上一轮 DLL，不安装正式 Mod。
- GUI 原始返回、截图及报告位于 `.tmp/2026-11-04-headbutt-review/`；[8 份完整 JSON](2026-11-04-headbutt-transition-examples/README.md)及 [manifest](2026-11-04-headbutt-transition-examples/manifest.json)记录真实参数、来源条目与哈希。候选事件另列于下文，未混入实际返回。

## 原生流程与 UI

未升级头槌的基础伤害为 9，之后通过 `CardSelectCmd.FromCombatPile` 从本地玩家弃牌堆选择一张牌，最后对同一个 CardModel 执行 `CardPileCmd.Add(card, PileType.Draw, CardPilePosition.Top)`。它不创建新牌、不加入永久牌组，也不是 card_drawn；抽牌堆增加不表示进入手牌。

`FromCombatPile` 在零候选时直接返回空集合；当不要求人工确认且候选数不超过最少选择数时直接选择，故只有一张弃牌时没有选择界面。多候选时才显示原生战斗牌堆选择。

实测多候选的原生提示为“选择一张牌放到你的抽牌堆顶。”，inspect_selection 对应的英语 prompt 为 `Choose a card to put on top of your Draw Pile.`。截图已人工核对，位置 `.tmp/2026-11-04-headbutt-review/multiple/selection.png`。提示仍作为选择文字返回；移动事件只表达实际可感知方向，不能把文字中的位置机制转换为动画直接证明的 position。

移动动画经当前 `CardPileCmd.Add` 源码核对：对已有的堆内牌，根据实际 NCard 是否仍在场景中，使用牌节点与 NCardFlyVfx，或以 NCardFlyShuffleVfx 从旧牌堆到新牌堆播放移动。实测读取动画前后的可见计数与显式打开的原生牌堆内容；没有另外录制完整逐帧动画，不将源码核对写成逐帧目测。

## 实测分支

三局均从仅测试模式创建的头槌、防御、打击手牌开始，抽牌堆和弃牌堆为空。通过真正的 play_card 打出防御／打击来准备弃牌，不在待核验动作期间直接改写牌堆。

| 初始弃牌 | 实际流程 | 当前事件 | 最终 UI／原生浏览 |
| --- | --- | --- | --- |
| 0 张 | 头槌伤害后直接结束，原生没有可回收牌 | 能量、card_played、damage；没有选择和回收事件，符合此分支 | 抽牌 0，弃牌 1；弃牌为打出的头槌 |
| 1 张防御 | 原生自动选择防御，直接完成 | 同样只有能量、card_played、damage，缺少防御移动 | 抽牌 1，弃牌 1；原生抽牌浏览确认为防御 |
| 防御、打击两张 | play_card 先返回 choice_required；选防御后恢复结算 | play_card 包含伤害等此前事件；select_card 返回 player_ready／complete:true，但 events:[] | 抽牌 1，弃牌 2；原生抽牌浏览只有防御，弃牌只有头槌、打击 |

防御在初始手牌与选择候选中均为战斗 card_id `6`。牌堆浏览使用自己的 `pile:N` 命名空间，不能把浏览 ID 和战斗 ID 当作同一字段比较；原生头槌对同一个已选择模型执行 Add，加上前后原生浏览和计数，可确认是移动已有牌而非新生成同名牌。

多候选的 `select_card` 当前 transition 完整片段：

```json
{
  "stop_reason": "player_ready",
  "complete": true,
  "events": []
}
```

完整上下文见 [select-card.full.json](2026-11-04-headbutt-transition-examples/select-card.full.json)。缺项不影响停止原因的正确性；complete 表示到达正常边界且缓冲未截断，不代表事件覆盖完整。

## 根因及相关范围

[TurnJournal.SubscribePiles](../../src/Sts2Agent/Events/TurnJournal.cs) 订阅入堆，但目前只补充抽牌历史、手牌到弃牌的 card_discarded，以及进入消耗堆的 card_exhausted。进入抽牌堆不生成已有牌的移动事件。

[CardAdditionJournal](../../src/Sts2Agent/Events/CardAdditionJournal.cs) 只为真实 CardGeneratedEntry 等生成事实建立 card_added，再用公开牌面和飞牌证据补初次去向。头槌没有生成事实，因此普通入堆通知不会变成 card_added；这里没有把卡错误地当成新牌，缺少的是另一类事实。

已有移动回执也没有通用来源／目的地表示。源码判断，同一缺口可能影响弃牌回手、手牌放回抽牌堆、消耗堆回手等未被现有专用事件覆盖的移动；这些只确认共用记录器缺少对应通道，未逐张卡实测。不能为头槌写死一条事件，或把所有 CardPile.CardAdded 都改报 card_added。

## 输出定稿

共用日志增加 `card_moved`，表达已有牌的公开移动；保留 card_added 表示新增牌，不重复发已有 card_drawn／card_discarded／card_exhausted 及手牌进入出牌区的 card_played 已表达的同次移动。下面是定稿字段示意；新的完整实际返回见实施记录，不能将旧的空 events 样本当作修复结果：

```json
{
  "sequence": 1,
  "type": "card_moved",
  "card": {"id": 6, "name": "Defend"},
  "from_pile": "discard",
  "to_pile": "draw"
}
```

from_pile／to_pile 与已有 hand、draw、discard、exhaust、play 的牌堆术语一致。不添加 position，连 null 字段也不生成；不返回内部索引、随机插入位置、洗牌结果或整个抽牌顺序。牌名只复用实际公开身份，不能从多个匿名牌背中读取身份。

范围为共用移动记录、实际展示取证、跨 play_card／选牌回执的生命周期、公开校验与去重；并核验明耀打击、无休手斧、刀刃陷阱。不按内部牌堆差量无条件补全历史。default 还省略 card_played.autoplay:false，full 保留；这项局部精简不改变事件空值或其他 false。

## 验证与交付范围

构建零警告、零错误；三局 GUI、25 次真实 MCP 调用均完成，所有文字 JSON 与 structuredContent 一致。测试断言确认停止分支、可见计数、已有候选身份、原生牌堆内容及当前缺项；这些证明缺口存在，不表示已修复。完整日志与验证总结果保存在本项 .tmp 目录。

新增的测试场景只准备三张手牌，非测试模式无法启用；未新增公开工具或修改生产事件类型。50 项相关 Python 检查、91 项 C# 检查通过，日志为 python.log、csharp.log；构建记录为 build.log。交付核对 verification.json 校验完整样本与原始返回一致、链接有效及测试构建哈希。自有游戏 PID 170075 已关闭；不操作正式存档或其他游戏进程。

未验证范围：第三方 Mod、多人、被覆盖或完全隐藏的移动、随机转移及其他具体卡牌；没有把通用日志的源码缺口当作所有卡牌都已实测的结论。
