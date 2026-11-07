# 基础观察卡牌与展示完成状态核验

> 当前状态：源码调研及基础观察face规则确认完成；产品尚未修改。统一展示完成状态仍为待设计事项，不能把content_complete写成已有接口。

本记录对应a7e8a0d基线，承接[结算详情审阅](2026-11-07-inspect-run-result-review.md)。本轮没有启动游戏、构建或修改工具参数，只核对源码、文档与当前卡牌投影。

## 已确认的基础观察卡牌规则

get_observation的所有标准卡牌对象在full/default中统一使用face_full/face_default，不返回卡牌description或逐牌hover_tips；summary使用共用卡牌摘要。包括手牌、已打开牌组／牌堆、商店商品、选牌候选、卡包、升级／附魔／变牌比较和结算／解锁卡牌。

专门查看工具的完整牌面继续使用full/default。卡牌ID、比较两侧及after:null等选择上下文保持；普通事件选项、故事或奖励文字由各自字段规则处理，不当作卡牌对象投影。

## 当前实现差异

[card_format.py](../../src/sts2_mcp/output/card_format.py)的format_game_cards由[observation_details.py](../../src/sts2_mcp/output/observation_details.py)调用，目前存在两套映射：

| 基础观察路径 | 当前内部格式 | 与统一face目标的关系 |
| --- | --- | --- |
| player.hand[] | face_full，再由default过滤 | 已符合 |
| shop.items[].card | face_full，再由default过滤 | 已符合 |
| deck[]、顶层cards[]牌堆 | 调用显式指定face_full，再由default过滤 | 已符合 |
| selection.cards[]、bundles[].cards[] | full | 待统一 |
| selection.upgrade_preview及upgrade_previews中的before/after | full | 待统一 |
| selection.enchant_previews／transform_previews中的before/after | full | 待统一 |
| run_result.cards[] | full | 待统一 |

原生[SelectionInspection.cs](../../src/Sts2Agent/Observation/SelectionInspection.cs)和[RunResultInspection.cs](../../src/Sts2Agent/Observation/RunResultInspection.cs)也会为基础观察采样完整牌面；Python当前没有将这些位置裁成face。不能只修改结算而宣称所有基础观察卡牌已统一。

现有文档和测试确实保留展开候选、比较和结算使用full的旧映射。应如实保留当前行为说明，将上述统一face规则标为已确认但未实现的迁移目标，不能把代码现状解释为应继续保留的原则。原有阶段性证据不改写为已经实现face。

本地证据`.tmp/2026-11-08-observation-consistency-review/card-routes.json`：使用受控卡牌输入调用实际format_game_cards，核对10个代表路径，前四个去掉正文和解释，后六个保留；变牌after:null保持。该检查只证明当前投影路径，不作为原生可见性或新GUI验证。此前12种实际原生响应预设重放见`.tmp/2026-11-08-result-content-design/preset-checks.json`，结算卡牌full/default确有正文和逐牌解释。

## content_complete是否已有

src和tests中没有content_complete、content_status或display_complete字段；content_complete仍是结算审阅中提出的候选，仅拟在run_result主体供get_observation及inspect_run_result共用。尚未实现，也不是已有的全项目通用状态。

其他页面已有局部展示／操作状态。以下为源码分类，没有新增逐场景动画时序GUI核验：

| 场景 | 当前处理 | 对内容完整性的表达 |
| --- | --- | --- |
| 普通事件 | [EventInspection](../../src/Sts2Agent/Observation/EventInspection.cs)未打完正文时description为null，外层仍visible；按钮按Ready禁用 | 无独立完成保证；summary还会主动省略正文 |
| 先古之民 | [AncientInspection](../../src/Sts2Agent/Observation/AncientInspection.cs)读取已显示行、称号／说明，动画及任务影响按钮enabled，外层仍visible | 无独立完成保证 |
| 建筑师 | [EpilogueInspection](../../src/Sts2Agent/Observation/EpilogueInspection.cs)打字未完时不返回整句；就绪前status=not_ready | 包含文字、任务和按钮等条件，不能等同内容完整 |
| 结算 | [RunResultInspection](../../src/Sts2Agent/Observation/RunResultInspection.cs)读取已显示内容，全部就绪前status=not_ready | 包含文字／计分／补间及可点击按钮，不能等同内容完整 |
| 占卜 | [DivinationInspection](../../src/Sts2Agent/Observation/DivinationInspection.cs)使用phase=settling／playing／finished，淡入中的格子保留遮挡，未打完对白暂不返回 | 已有局部进度，但同时关联揭示、奖励和操作就绪 |
| 商店 | [ShopInspection](../../src/Sts2Agent/Observation/ShopInspection.cs)使用view=opening／closing等，开关动画中不返回库存，外层仍visible | 已有局部开关状态，无通用完成字段 |
| 宝箱 | [TreasureInspection](../../src/Sts2Agent/Observation/TreasureInspection.cs)使用chest=closed／opening／open和按钮enabled | 已有开箱状态，不能把未打开宝箱当作数据缺失 |
| 奖励／火堆 | [RewardInspection](../../src/Sts2Agent/Observation/RewardInspection.cs)、[RestSiteInspection](../../src/Sts2Agent/Observation/RestSiteInspection.cs)读取已显示条目，外层visible，动作受Ready约束 | 没有独立的整页展示完成保证 |

transition.complete仅表示动作到达既定停止边界，不能作为观察内容完整性标记；enabled表示按钮可操作，也不能代替展示完成判断。

## 统一设计的边界（尚未定稿）

content_complete不宜成为只为结算增加、却未经其他页面核验的局部通用字段。应先统一“当前页面／区域是否仍在分阶段展示”的含义及判断入口，get_observation与对应inspect工具复用；各页面使用经核实的原生展示信号，不能直接套用Ready或按钮enabled。

该语义描述当前已打开页面的展示过程。占卜尚有未揭格子、宝箱尚未打开或未来尚有其他解锁，并不自动表示当前观察不完整；持续变化的战斗也不能简单用一个全局complete判断整场内容。适用范围、字段位置及与现有状态枚举的关系仍待讨论和原生时序核验。

本轮只记录已确认的face迁移目标和上述候选范围，没有擅自扩展TODO或实施跨场景接口变更。
