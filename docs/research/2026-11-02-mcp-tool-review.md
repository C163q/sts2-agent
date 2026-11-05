# MCP 工具逐项核验与参数设计

> 当前状态：工具核验进行中，共 44 项，已核销 16 项：inspect_ui、inspect_hand、inspect_targets、inspect_combatants、inspect_potions、inspect_relics、inspect_deck、inspect_pile、close_card_view、play_card、play_cards、end_turn、use_potion、discard_potion、inspect_selection、select_card。selection_option 现状核验完成，25 组游戏情形及完整样例已交付，两项错误处理问题待设计确认，尚未修改玩法行为；get_observation 的地图覆盖仍待 inspect_map，整体未核销，其余 26 项尚未核销。暂无阻塞。

[共用链路重构计划](../superpowers/plans/2026-11-03-tool-architecture-refactor.md)的七阶段已完成，验收映射、范围及完整返回样例见[重构验收](2026-11-04-refactor-stage-7.md)。现在恢复下述逐工具内容审阅；结构重构不增加本清单完成数。

## 范围与基线

- 核对基线：提交 `ef9f34e`，MCP `0.48.0`；工具名称与数量依据 [mcp_catalog.py](../../src/sts2_mcp/mcp_catalog.py)。后续以每项核验时的实现为准，工具增删时同步本清单及总数。
- 逐项检查工具的适用场景、返回内容、参数及预设，目标是符合玩家实际可从 UI 获得的信息，并让 LLM 聚焦所关心的内容。遵循[可见信息边界](../observation.md)。
- 43 个玩法 JSON 工具已支持 `default/full`；现有专用预设包括界面帮助、手牌、选牌、药水、战斗对象、遗物的 `summary`、地图的 `selectable` 和基础观察的 `summary/top_bar/actions_only`。牌组与牌堆也已迁移为 full/default/summary，旧 detail_level 已移除。既有能力也须重新核验，不因此直接核销。
- `capture_screenshot` 按配置启用，不支持 preset；核验其现有参数与返回。统一预设的现行契约见 [MCP 输出预设](../development/mcp.md#输出预设)。

## 逐项工作流程

1. **指定工具**：由用户选择本轮工具，记录当前阶段与核验基线。
2. **梳理场景**：查阅工具实现及相关游戏源码，列出所有已识别的适用场景、特殊状态、覆盖页面与失败情况；区分返回结构相同的内容变体和真正不同的返回分支。场景过多时先提供目录，由用户选择本轮展开的场景，其余明确标记待核验。
3. **展示现状**：提供各场景的 `preset:"full"` 完整返回示例，保留空值及实际存在的提示、预览、事件、错误等字段。标明实测样本或依据实现整理，附调用参数与证据位置；整理示例不能冒充实测。图片内容单独说明。截图工具按其实际返回展示。
发现正确性问题时，在专项记录开头集中列出问题编号、优先级、影响、证据、处理状态与未解决范围；不能只埋在场景表或将缺口写成合理限制。先解决正确性与共用契约问题，再推进参数和摘要设计。

4. **讨论设计**：用户提出新增参数、`summary` 字段或其他调整；核对目标版本源码与 UI，反馈是否合理、是否有更好的设计。说明字段的信息来源、筛选范围、默认值、组合优先级和错误语义，逐步消除歧义，不在讨论期间提前修改工具行为。
5. **形成定稿**：记录最终字段与参数契约、保留或省略的原因、信息边界、与既有预设的关系，以及待验证事项。用户确认定稿后进入实现；尚未确认的内容保留为候选。
6. **实现与验证**：完成约定变更及相应检查，涉及 UI 行为时进行游戏内验证；同步持续维护的接口文档，创建本项 Git 提交。若定稿决定维持现状，记录判断依据及必要核验即可，不为核销制造代码变更。
7. **核销与交接**：补齐验证结果、未验证范围、提交及文档链接，更新本文件开头的总进度和下方清单。未完成场景或遗留问题须记录处理范围与去向，不能以展示过一个示例代替整个工具核验完成。

阶段依次为：待选 → 场景核验 → 设计讨论 → 待定稿 → 实现与验证 → 完成。阶段性暂停时记录当前步骤和下一步；只有本项约定范围完成后才勾选。后续各轮持续更新本文件，不仅在对话中记录。

## 工具核销清单

未勾选且未注明阶段的条目处于“待选”。开始某项后，在条目后附阶段及对应记录链接；完成后勾选。分组仅用于查找，不指定核验顺序。

### 基础观察与战斗详情（7 项）

- [ ] `get_observation`：当前画面的基础观察与可用操作。阶段：[07–09 组奖励、火堆与宝箱](2026-11-02-get-observation-rooms.md)现状核验和 summary 已交付，[10–12 组](2026-11-03-get-observation-shop-ancient-event.md)现状核验及 summary 已交付，[13–15 组](2026-11-03-get-observation-divination-confirmation-epilogue.md)现状核验已交付，建筑师牌组覆盖校验已修复，summary 已交付；[16–17 组结算、解锁与菜单](2026-11-03-get-observation-result-menu.md)现状及完整 full 已交付，summary 已交付；[地图与牌组／牌堆覆盖](2026-11-02-get-observation-browsing.md)的初次摘要占位已交付，[牌组内容与摘要](2026-11-04-deck-inspection-implementation.md)已实现，[牌堆内容与摘要](2026-11-04-pile-inspection-implementation.md)已实现，地图仍待核验；[全部选牌](2026-11-02-get-observation-selections.md)与[战斗主画面](2026-11-02-get-observation-combat.md)约定范围已交付，完整[场景目录](2026-11-02-get-observation-review.md)。
- [x] `inspect_ui`：可见顶栏、战斗 UI、资源及空充能球槽帮助。阶段：[修复与核验完成](2026-11-03-inspect-ui-review.md)，[统一上下文、summary、sources 筛选及验证](2026-11-03-ui-context-implementation.md)已交付；部分条件变体保留源码／历史核对边界。
- [x] `inspect_hand`：手牌详情。阶段：[核验及定稿](2026-11-03-inspect-hand-review.md)、[覆盖清单](2026-11-03-card-format-coverage.md)和[实现／验证](2026-11-03-card-format-implementation.md)已完成；新增可见 Affliction、统一附魔空值、资源计数及共用卡牌格式。后续补齐[手牌 HUD 牌堆计数](2026-11-04-hand-pile-counts.md)，不改变既有卡牌预设及筛选规则。
- [x] `inspect_targets`：指定手牌或药水的可用性与目标范围。阶段：[核验及输出定稿](2026-11-03-inspect-targets-review.md)、[错误修复与验证](2026-11-03-inspection-error-recovery.md)完成；维持 default/full，不新增 summary，不改原生指示范围。AnyPlayer／AllAllies／Osty 卡牌分支保留源码核对边界，未新增实际调用样本。
- [x] `inspect_combatants`：战斗对象、状态、意图、充能球及悬浮剑详情。[核验与定稿](2026-11-03-inspect-combatants-review.md)、[实现与验证](2026-11-03-combatants-implementation.md)完成：错误恢复、具体诊断、验证入口、公共 Summary/Full 读取、取消图标视口截断、静态 summary、对象及关联说明筛选。
- [x] `inspect_potions`：药水详情。[核验与输出定稿](2026-11-04-inspect-potions-review.md)、[实现与验证](2026-11-04-potion-inspection-implementation.md)完成：五项问题修复、共用静态读取、取消离屏截断、summary、原槽位筛选／位置映射、提示与 note 同步裁剪。
- [x] `inspect_relics`：已拥有遗物的详情。[核验与定稿](2026-11-04-inspect-relics-review.md)、[实现与验证](2026-11-04-relic-inspection-implementation.md)完成：具体拒绝、旧专项验证修复、共用置灰／发光读取、default／summary 的局部 false 精简，以及全部预设的原下标映射和关联裁剪。

### 卡牌浏览（3 项）

- [x] `inspect_deck`：打开并查看牌组。[定稿](2026-11-04-inspect-deck-review.md#输出定稿)及[实现／游戏验证](2026-11-04-deck-inspection-implementation.md)已完成，615 项 Python、91 项 C#、六局 GUI 及独立审查通过；包含 card_ids、明确拒绝恢复、最小关闭以及基础观察的静态牌面和当前排序／升级设置。
- [x] `inspect_pile`：打开并查看抽牌堆、弃牌堆或消耗堆。[核验及定稿](2026-11-04-inspect-pile-review.md)、[实现与验证](2026-11-04-pile-inspection-implementation.md)：具体拒绝／显式未交互恢复、card_ids、基础观察的静态卡牌、固定帮助精简、旧专项修复，以及选牌战场视图的当前页复用。
- [x] `close_card_view`：关闭牌组或牌堆浏览界面。[审阅及定稿](2026-11-04-close-card-view-review.md)、[实现与验证](2026-11-04-close-card-view-implementation.md)完成：关闭原因与合法性统一、明确未交互拒绝保留已有许可，成功维持 default/full 的 actions_only；627 项 Python、91 项 C#、三局 GUI／30 次 MCP 及独立审查通过。

### 战斗与药水操作（5 项）

- [x] `play_card`：单张手动出牌。[现状调研](2026-11-04-play-card-review.md)及[实现／验证](2026-11-04-play-cards-implementation.md)完成：PLAY-01–03、共用校验与原生提交追踪、最终拒绝恢复和单张回归；action_canceled 维持原策略。
- [x] `play_cards`：按原生规则连续入队。[参数／行为](2026-11-04-play-cards-design.md)及[交付](2026-11-04-play-cards-implementation.md)完成：原子前置校验、动态失败继续、边界停止、逐张及跨选择回执、unknown 不直接接受后续动作。32 项不同场景／门控、653 项 Python、114 项 C# 及独立审查的重要修复通过；集成验证剩余范围见交付记录。
- [x] `end_turn`：结束回合。[审阅](2026-11-04-end-turn-review.md)、[头槌补充核验](2026-11-04-headbutt-transition-review.md)及[实施／新返回](2026-11-04-turn-transitions-implementation.md)完成：TURN-01–03、无 position 的 card_moved、default 省略 autoplay:false；四张指定卡、手斧抽牌堆来源变体、错误直接续接及终态查看均已验证。636 项 Python、91 项 C#、最终十五局 GUI 通过；独立审查的重要问题已修复，低优先级生成预览牌名缓存限制留在实施记录。
- [x] `use_potion`：使用药水。[现状审阅](2026-11-04-use-potion-review.md)及[实现／验证](2026-11-05-potion-actions-implementation.md)完成：五项问题、单槽判断、事件可见性及地图 covered；34 类药水情形与三组既有工具回归通过，保持 default/full，不新增 summary。
- [x] `discard_potion`：丢弃药水。阶段：完成；[确认契约](2026-11-05-discard-potion-review.md#已确认契约)及[实施记录](2026-11-05-potion-discard-implementation.md)包含原生排队、防重复、顶层结果与选择续接；35 类组合场景、673 项 Python、124 项 C# 及一次独立审查通过，已合入 main，提供 [126 份完整返回](2026-11-05-potion-discard-queue-examples/README.md)。参数与 default/full 保留，无 summary；一项低优先级监听清理事项单列于实施记录。

### 卡牌选择（4 项）

- [x] `inspect_selection`：查看候选牌、按钮及预览。阶段：完成；[审阅及定稿](2026-11-05-inspect-selection-review.md)、[开发核验](2026-11-05-inspect-selection-development-notes.md)与[修复实施](2026-11-05-selection-inspection-implementation.md)记录三项修复、28 组 GUI 组合、676 项 Python、124 项 C# 和一次独立审查；保留原参数及 summary，补齐共用 prompt、明确拒绝与未交互恢复，提供 [27 份修复后返回](2026-11-05-selection-inspection-fixed-examples/README.md)。
- [x] `select_card`：点击候选牌。阶段：[核验与定稿](2026-11-05-select-card-review.md)及[三项修复与验证](2026-11-05-selection-feedback-implementation.md)及一次独立审查完成；保留参数与紧凑回执，补齐明确拒绝、许可恢复和原生选中／取消事件，提供[31 份修复后返回](2026-11-05-selection-feedback-examples/README.md)。27 个专项场景、9 个回归组合、682 项 Python、124 项 C# 和 6 项原生输入检查通过，已合入 main。
- [ ] `selection_option`：点击确认、取消、跳过等选择按钮。阶段：[现状核验完成，待设计确认](2026-11-05-selection-option-review.md)，[开发证据](2026-11-05-selection-option-development-notes.md)记录 25 组游戏情形、42 项相关 Python 检查及[81 份 full 返回](2026-11-05-selection-option-examples/README.md)；点击前拒绝后的许可丢失及错误原因缺失待修复，尚未修改玩法行为或核销。
- [ ] `set_selection_view`：切换选择界面与战场视图。

### 地图（3 项）

- [ ] `inspect_map`：打开并查看地图。核验时同步补充[基础观察的浏览内容与摘要](2026-11-02-get-observation-browsing.md#本阶段定稿与后续接入)；[共用地图 covered 状态](2026-11-05-potion-actions-implementation.md)已交付，地图参数及主体／摘要仍待核验。
- [ ] `close_map`：关闭地图。
- [ ] `travel_to_node`：前往可选节点。

### 奖励、宝箱与流程推进（5 项）

- [ ] `inspect_rewards`：查看奖励列表。
- [ ] `claim_reward`：领取一项奖励。
- [ ] `inspect_treasure`：查看宝箱房及已展示遗物。
- [ ] `loot_treasure`：打开宝箱或领取遗物。
- [ ] `proceed`：点击当前界面的跳过或继续按钮。

### 火堆（2 项）

- [ ] `inspect_rest_site`：查看火堆选项。
- [ ] `choose_rest_option`：选择火堆操作。

### 商店（4 项）

- [ ] `inspect_shop`：查看商品、价格与详情。
- [ ] `open_shop`：打开商店。
- [ ] `close_shop`：关闭商店。
- [ ] `buy_item`：购买商品或进入删牌选择。

### 事件（5 项）

- [ ] `inspect_event`：查看事件内容，含占卜棋盘及图片。
- [ ] `choose_event_option`：选择事件选项。
- [ ] `set_divination_tool`：切换占卜揭示范围。
- [ ] `divine`：执行一次占卜揭示。
- [ ] `respond_to_confirmation`：响应试炼事件的确认框。

### 先古之民与对话（3 项）

- [ ] `inspect_ancient`：查看先古之民对话与馈赠。
- [ ] `choose_ancient_option`：选择馈赠。
- [ ] `advance_dialogue`：推进先古之民或建筑师对话。

### 结算（2 项）

- [ ] `inspect_run_result`：查看结算页面及已揭示详情。
- [ ] `run_result_option`：点击结算按钮或解锁条目。

### 截图（1 项，按配置启用）

- [ ] `capture_screenshot`：保存当前游戏画面。

## 单项记录方式

已启动的单项记录见清单条目链接。每项开始时记录以下内容；篇幅较小时直接追加到本文件，示例较多时建立带日期的专项记录并从清单条目链接。

- **状态与范围**：工具、阶段、代码与游戏版本、当前步骤、剩余范围、阻塞情况。
- **场景与现状**：已识别场景、用户选择展开的场景、完整调用与返回示例、证据及未验证部分。
- **设计结论**：源码与 UI 核对结果、候选方案、最终参数与字段契约、待确认事项。
- **交付结果**：验证结果、遗留及去向、接口文档链接、提交；维持现状时记录结论依据。

本文件负责本轮核验的进度、依据和定稿记录；已交付的现行接口契约同步至对应开发指南，避免以阶段性记录替代使用文档。
