# 用户后续待办

> 当前状态：共 7 项，已完成 1 项；其中错误恢复与错误信息两项已提前处理十七个工具的相关拒绝与诊断，牌组／牌堆覆盖已实现；剩余范围仍在当前逐项审阅结束后处理。本清单不表示已授权立即实施其他事项。

本文件仅记录用户明确提出、留待后续处理的事项。Agent 不得擅自新增待办或扩大范围；调研建议、自行发现的问题和当前任务进度另记所属任务文档。仅按用户要求维护本清单。

- [ ] **占卜文字观察**：研究让 LLM 不依赖图片也能理解已揭开的物品与局部图案。后续同时更新 `get_observation` 与当前专门查看入口 `inspect_event`，保持已揭示信息与图文语义一致；两者目前仍依赖棋盘 PNG。设计须区分完整揭示与局部可见，不能用内部模型补齐雾下身份或未来奖励。见[现行占卜接口](divination.md)。
- [ ] **地图覆盖的内容与 summary**：核验 `inspect_map` 时，一并设计 `get_observation` 地图覆盖的实际内容与摘要，替换当前主体复用 default 的占位。见[浏览覆盖后续接入](../research/2026-11-02-get-observation-browsing.md#本阶段定稿与后续接入)。
- [x] **牌组／牌堆覆盖的内容与 summary**：牌组已接入完整静态牌面及共用摘要，随当前升级／排序设置读取，见[牌组实施](../research/2026-11-04-deck-inspection-implementation.md)。战斗牌堆也已接入完整静态牌面、共用摘要和固定帮助精简，见[牌堆实施](../research/2026-11-04-pile-inspection-implementation.md)；共用顶栏摘要已实现。原约定见[浏览覆盖记录](../research/2026-11-02-get-observation-browsing.md#本阶段定稿与后续接入)。
- [ ] **商店详情改进**：核验 `inspect_shop` 时设计当前金币等购买上下文的直接返回，以及该工具的参数与摘要；商品卡正文继续由专门查看提供。见[商店核验记录](../research/2026-11-03-get-observation-shop-ancient-event.md)。
- [ ] **游玩知识库**：提供官方术语和必要的开局知识；目前仅有方向记录。见[知识库计划](../research/2026-11-01-knowledge-base-plan.md)。

## 当前工具审阅结束后处理

以下为用户实测反馈，详细记录由用户保存，后续处理时再对照。已按用户要求提前修复的部分见[查看错误与许可记录](../research/2026-11-03-inspection-error-recovery.md)、[战斗对象实施](../research/2026-11-03-combatants-implementation.md)、[药水实施](../research/2026-11-04-potion-inspection-implementation.md)及[遗物实施](../research/2026-11-04-relic-inspection-implementation.md)，尚未覆盖其他工具的完整审查，因此两项仍不勾销。

- [ ] **工具报错后的观察前置要求**：已提前处理 get_observation、inspect_ui、inspect_hand、inspect_targets、inspect_combatants、inspect_potions、inspect_relics 的本地参数错误与明确读取拒绝，inspect_deck／inspect_pile／close_card_view 显式保证未交互的拒绝，以及 end_turn 明确未提交／未交互拒绝；并完成 play_card／play_cards 的共用诊断与明确未提交恢复，验证 0 能量或原生最终拒绝后可直接选择合法动作；use_potion／discard_potion 的共用明确未执行拒绝也已处理，包含地图动作的连续续接。inspect_selection 的明确未交互前置拒绝也已修复，可带升级参数直接纠正或继续合法操作；select_card 的无效候选等明确点击前拒绝也保留已有许可，可直接纠正或改用合法操作；剩余工具仍需结合用户记录审查动作许可失效与恢复流程；未知结果与状态过期不能当作明确未执行。
- [ ] **错误原因与恢复提示的准确性**：已为上述十七个工具的已审阅拒绝补具体说明，原生公开原因与异常诊断分开；药水阶段、槽位和目标拒绝的具体原因见[药水修复记录](../research/2026-11-05-potion-actions-implementation.md)；选牌查看见[选牌查看修复](../research/2026-11-05-selection-inspection-implementation.md)，点击候选的具体拒绝及恢复见[选牌反馈实施](../research/2026-11-05-selection-feedback-implementation.md)；其他工具仍需结合用户记录逐项审查，让 LLM 能判断发生了什么、为何被拒绝，以及如何继续；共用层修复不代表全部工具的错误原因与恢复提示均已核验。
