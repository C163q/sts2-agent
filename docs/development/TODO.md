# 用户后续待办

> 当前状态：共 8 项，已完成 4 项；其中错误恢复与错误信息两项按下文明细记录已处理工具的相关拒绝与诊断，地图及牌组／牌堆覆盖已实现；剩余范围仍在当前逐项审阅结束后处理。本清单不表示已授权立即实施其他事项。

本文件仅记录用户明确提出、留待后续处理的事项。Agent 不得擅自新增待办或扩大范围；调研建议、自行发现的问题和当前任务进度另记所属任务文档。仅按用户要求维护本清单。

- [x] **占卜文字观察**：get_observation与inspect_event已共用文字棋盘、s/S及可见部位，默认无需图片；完整图案及局部方向按原生UI转译，inspect_event可选附图。见[现行接口](divination.md)及[实施与验证](../research/2026-11-07-event-inspection-text-implementation.md)。
- [x] **地图覆盖的内容与 summary**：基础观察 full/default/summary 统一提供整幕类型分组的节点 ID 与连接省略 note；inspect_map.summary 接入相同分组，保留深度筛选。见[地图实施与验证](../research/2026-11-05-map-summary-implementation.md)。
- [x] **牌组／牌堆覆盖的内容与 summary**：牌组已接入完整静态牌面及共用摘要，随当前升级／排序设置读取，见[牌组实施](../research/2026-11-04-deck-inspection-implementation.md)。战斗牌堆也已接入完整静态牌面、共用摘要和固定帮助精简，见[牌堆实施](../research/2026-11-04-pile-inspection-implementation.md)；共用顶栏摘要已实现。原约定见[浏览覆盖记录](../research/2026-11-02-get-observation-browsing.md#本阶段定稿与后续接入)。
- [x] **商店详情改进**：inspect_shop已提供共用摘要顶栏、summary、item_ids/kinds筛选，静态商品与get_observation共用格式；商品卡正文仍由详情提供，右键升级另列待办。见[商店定稿](../research/2026-11-06-inspect-shop-review.md#输出定稿)。
- [ ] **统一卡牌右键详情与升级预览**：核对商店、选牌等场景的原生右键查看能力，统一设计inspect_shop、inspect_selection等相关工具的升级对照、页面打开／切换／返回和实际UI反馈；本项留待后续处理，不能仅计算升级结果却声称画面已切换。见[商店审阅](../research/2026-11-06-inspect-shop-review.md#输出定稿)。
- [ ] **游玩知识库**：提供官方术语和必要的开局知识；目前仅有方向记录。见[知识库计划](../research/2026-11-01-knowledge-base-plan.md)。

## 当前工具审阅结束后处理

以下为用户实测反馈，详细记录由用户保存，后续处理时再对照。已按用户要求提前修复的部分见[查看错误与许可记录](../research/2026-11-03-inspection-error-recovery.md)、[战斗对象实施](../research/2026-11-03-combatants-implementation.md)、[药水实施](../research/2026-11-04-potion-inspection-implementation.md)及[遗物实施](../research/2026-11-04-relic-inspection-implementation.md)，尚未覆盖其他工具的完整审查，因此两项仍不勾销。

- [ ] **工具报错后的观察前置要求**：已提前处理 get_observation、inspect_ui、inspect_hand、inspect_targets、inspect_combatants、inspect_potions、inspect_relics、inspect_event 的本地参数错误与明确读取拒绝，inspect_deck／inspect_pile／inspect_map／close_card_view／close_map／set_selection_view 显式保证未交互的拒绝，以及 end_turn 明确未提交／未交互拒绝；并完成 play_card／play_cards 的共用诊断与明确未提交恢复，验证 0 能量或原生最终拒绝后可直接选择合法动作；use_potion／discard_potion 的共用明确未执行拒绝也已处理，包含地图动作的连续续接。inspect_selection 的明确未交互前置拒绝也已修复，可带升级参数直接纠正或继续合法操作；select_card 的无效候选及 selection_option 的无效／不可用按钮等明确点击前拒绝也保留已有许可，可直接纠正或改用合法操作；travel_to_node 的明确滚动／点击前拒绝也保留已有许可，滚动后的失败仍要求观察；inspect_rewards 的新预设／筛选已验证纯读取拒绝及本地参数错误保留已有许可；claim_reward 的明确滚动／点击前拒绝也保留已有许可，地图／选牌覆盖或无效奖励 ID 被拒后可直接继续合法操作；inspect_treasure 已验证纯读取拒绝保留已有许可，矛盾响应会清除许可；loot_treasure 的首次点击前明确拒绝也保留已有许可，支持直接领取／继续／选择，已点击后的失败仍须观察；proceed 的明确点击前拒绝也保留已有许可，覆盖页、活动未完成或错误工具被拒后可直接选择合法操作；inspect_rest_site已验证纯读取与本地参数拒绝保留已有许可，矛盾上下文或说明来源会清除许可；choose_rest_option的明确点击前拒绝也保留已有许可，支持直接改选、取消选择或结束回合；inspect_shop已验证本地参数与明确读取拒绝保留已有许可、坏响应清除许可，筛选不影响该规则；open_shop的明确点击前拒绝保留已有许可，可直接关闭商店、取消选择或结束回合；close_shop的明确点击前拒绝也保留已有许可，可直接打开、取消选择或继续奖励；buy_item的明确点击前拒绝也保留已有许可，原生领取失败继续由正常回执表达；choose_event_option的明确点击前拒绝也保留已有许可，可直接改选、处理选牌／奖励／确认框或继续占卜；set_divination_tool已统一为可直接调用的视图，明确未交互拒绝保留已有许可；divine的明确点击前拒绝也保留已有许可，可直接改选覆盖格或处理当前奖励／选择／前进；respond_to_confirmation的明确点击前拒绝也保留已有许可，可直接取消、重开或继续当前合法动作；剩余工具仍需结合用户记录审查动作许可失效与恢复流程；未知结果与状态过期不能当作明确未执行。
- [ ] **错误原因与恢复提示的准确性**：已审阅工具提供固定拒绝原因与恢复指引，原生公开原因与异常诊断分开；药水阶段、槽位和目标拒绝的具体原因见[药水修复记录](../research/2026-11-05-potion-actions-implementation.md)；选牌查看见[选牌查看修复](../research/2026-11-05-selection-inspection-implementation.md)，点击候选的具体拒绝及恢复见[选牌反馈实施](../research/2026-11-05-selection-feedback-implementation.md)，按钮点击见[按钮恢复实施](../research/2026-11-05-selection-option-recovery-implementation.md)，眼睛视图见[视图恢复实施](../research/2026-11-05-selection-view-results-implementation.md)；其他工具仍需结合用户记录逐项审查，让 LLM 能判断发生了什么、为何被拒绝，以及如何继续；共用层修复不代表全部工具的错误原因与恢复提示均已核验。 travel_to_node 已公开未开地图、覆盖、绘图、未就绪、非候选及准备中变化的固定原因。inspect_rewards 已补齐无奖励、覆盖与等待状态的具体原因。claim_reward 已补齐相同页面原因、奖励 ID 已不存在及不支持类型等固定说明，见[领取修复](../research/2026-11-05-claim-reward-recovery-implementation.md)。inspect_treasure 已提供无宝箱、覆盖、预览与过渡的具体诊断，见[宝箱详情修复](../research/2026-11-06-treasure-inspection-presets-implementation.md)。loot_treasure 已提供已开箱、无可领取遗物、禁用、离屏及未就绪等原因，见[开箱动作修复](../research/2026-11-06-treasure-loot-recovery-implementation.md)。proceed 的场景、覆盖、活动／对白未完成和错误工具原因已统一，见[前进修复](../research/2026-11-06-proceed-recovery-implementation.md)。inspect_rest_site已公开无火堆、地图／牌组／选牌／奖励覆盖、预览和过渡原因，见[火堆详情实施](../research/2026-11-06-rest-site-inspection-presets-implementation.md)。choose_rest_option已共用页面／目标具体原因，明确点击前拒绝可直接继续，见[火堆动作实施](../research/2026-11-06-rest-option-feedback-implementation.md)。

inspect_shop已集中公开无商店、覆盖、关闭及动画原因，查看的成功上下文和完整数据先校验再筛选，见[商店定稿](../research/2026-11-06-inspect-shop-review.md#输出定稿)。

open_shop已统一页面覆盖与打开条件，具体提示及明确拒绝恢复见[打开商店修复](../research/2026-11-07-shop-opening-recovery-implementation.md)。

close_shop已统一关闭条件及页面覆盖、已关闭、活动等待原因，恢复与验证见[关闭商店修复](../research/2026-11-07-shop-closing-recovery-implementation.md)。

buy_item已集中页面／单品原因，校验购买结果ID，增加pending并等待选择边界的金币动画，见[购买反馈修复](../research/2026-11-07-shop-purchase-feedback-implementation.md)。

choose_event_option已共用页面／动作／单项检查，公开覆盖、完成、无效ID与锁定等具体原因；验证见[事件选择修复](../research/2026-11-07-event-option-recovery-implementation.md)。

set_divination_tool已共用页面、忙碌及按钮检查，公开无棋盘、覆盖和结束原因；恢复与冷切换见[工具切换实施](../research/2026-11-07-divination-tool-view-implementation.md)。

divine已共用页面、揭开及目标格检查，公开覆盖、结束和已清除等原因；恢复与原生结算验证见[揭开实施](../research/2026-11-07-divination-recovery-implementation.md)。

respond_to_confirmation已共用页面、动作及按钮检查，公开未知来源、覆盖、等待与按钮原因；验证器已迁移共享隔离流程，见[确认响应实施](../research/2026-11-07-confirmation-response-recovery-implementation.md)。
