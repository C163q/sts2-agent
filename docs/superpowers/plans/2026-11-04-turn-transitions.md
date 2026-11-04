# 结束回合与可见牌堆移动实施计划

> 当前状态：完成，共 3 项，已完成 3 项。实现、最终十五局 GUI、636 项 Python、91 项 C# 及独立审查修复均已交付，见[实施记录](../../research/2026-11-04-turn-transitions-implementation.md)。仅遗留一项低优先级生成预览牌名缓存限制，已记录且未扩展用户 TODO。暂无阻塞。

依据[结束回合审阅](../../research/2026-11-04-end-turn-review.md)和[头槌核验](../../research/2026-11-04-headbutt-transition-review.md)，代码基线 bc62b0d。用户已确认合并处理 TURN-01–03、MOVE-01，不增加 position；并验证明耀打击、无休手斧、刀刃陷阱，default 省略 card_played.autoplay:false。采用当前 feature 分支原地实施，保留 .tmp 证据，不安装 Mod、不推送或合并。

## 定稿与职责

- end_turn 保持 default/full、单次提交及精简动作回执。专用 EndTurnUnavailableReason 同时用于 available_actions 和提交前拒绝；共用 CanEndTurn 的就绪含义不改。前置拒绝只在明确未提交且未交互时保留已有许可；stale_state、已交互、异常、取消及旧 Mod 无保证仍按原规则处理。
- 共用动作解码在胜负、不完整等无法续接动作的边界保留当前快照中合法、无需许可的查看工具，不授予游戏动作许可；已支持选择仍允许对应选择操作。
- card_moved 固定提供 sequence/type/card.id/name/from_pile/to_pile；只记录已有牌可感知的跨战斗牌堆移动，不提供位置、牌序或随机结果。已有 card_drawn、card_discarded、card_exhausted 及手牌进入出牌区的 card_played 不重复报告同一次移动。普通出牌结算区到弃牌堆的可见移动也由公共入口表达。
- 新移动记录器单独负责移出／进入配对、渲染证据、取舍和释放，借用 TurnJournal 的缓冲和公开身份。只在真实可见手牌／结算区或飞牌动画证实后发布；匿名牌背飞行动画只接受明确选择或唯一来源牌，不能从多个匿名背面中偷读身份。洗牌在原生异步上下文内抑制逐牌记录，防止泄露抽牌顺序。隐藏／覆盖、无动画、同堆重排不补记。
- autoplay 是现有字段名。完整原生结果先校验；default 只省略 card_played.autoplay:false，保留 true、full 的 false、其他 false 及事件 null。不得通过精简掩盖坏字段。

## 1. 回归、协议与结束回合

- [x] Python 回归先 RED：end_turn 明确未提交拒绝后直接合法动作；旧／矛盾／无旧许可；终态保留查看但不授权动作；card_moved 严格字段／牌堆／类型及未知位置剔除；default autoplay 的精确局部过滤与不变性。
- [x] 实现 GameAdapter.EndTurn 专用拒绝入口及分派，注册已有未提交保证；共用解码保留无需许可的查看工具，添加移动契约及 default 局部规则，专项检查 GREEN。

## 2. 可见移动与实际游戏

- [x] 建立 GUI 失败回归：头槌零／一／多弃牌、明耀打击回抽牌、无休手斧回手、小刀消耗后经刀刃陷阱自动出牌；具体拒绝／直接续接及胜负后查看。保留旧构建失败证据。
- [x] 实现 CardMovementJournal、渲染钩子及异步洗牌抑制；TurnJournal 只负责接入与公共卡牌身份，选择入口提供本次公开选择身份，不按卡名分支。原生负例覆盖隐藏、无视觉、匿名多牌、同堆重排、洗牌及释放；GUI 复测 GREEN。审查后补无休手斧从抽牌堆直接回手的来源变体，以实际 Draw 历史去重，RED→GREEN。

## 3. 同步、验证与交付

- [x] 更新 Mod／MCP 版本和 README，观察 schema 保持 40；全部 Python／C#、专项 GUI 与受影响的旧事件／交接／自动出牌检查通过。只为新问题扩大验证。
- [x] 同步事件、输出预设、错误恢复、原 TODO 覆盖范围及核销清单；保留旧示例并导出 25 份新真实 JSON，记录兼容基线、哈希和未验证范围。
- [x] 最终独立只读审查，修复重要问题，核对链接／来源／diff，提交英文 Conventional Commit。结论区分实测与源码覆盖，保留失败证据及八个自有进程清理记录。

## 重点边界

缺少保证不能凭 false 执行事实恢复许可；完整解码先于 default 过滤；不能借 card_moved 暴露洗牌顺序；跨选牌回执重新接入后只能记录期间真实移动；刀刃陷阱的非首张小刀可能跳过原生移动视觉，不得因此补出隐藏动画或重复消耗事件。

证据目录：`.tmp/2026-11-04-turn-transitions/`。执行进度与设计判断同步在此计划及同目录 progress.md；最终审查按项目 Codex 模型选择规则执行。
