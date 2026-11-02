# 用户后续待办

> 当前状态：共 5 项，已完成 0 项，均留待后续安排；本清单不表示已授权立即实施。

本文件仅记录用户明确提出、留待后续处理的事项。Agent 不得擅自新增待办或扩大范围；调研建议、自行发现的问题和当前任务进度另记所属任务文档。仅按用户要求维护本清单。

- [ ] **占卜文字观察**：研究让 LLM 不依赖图片也能理解已揭开的物品与局部图案。后续同时更新 `get_observation` 与当前专门查看入口 `inspect_event`，保持已揭示信息与图文语义一致；两者目前仍依赖棋盘 PNG。设计须区分完整揭示与局部可见，不能用内部模型补齐雾下身份或未来奖励。见[现行占卜接口](divination.md)。
- [ ] **地图覆盖的内容与 summary**：核验 `inspect_map` 时，一并设计 `get_observation` 地图覆盖的实际内容与摘要，替换当前主体复用 default 的占位。见[浏览覆盖后续接入](../research/2026-11-02-get-observation-browsing.md#本阶段定稿与后续接入)。
- [ ] **牌组／牌堆覆盖的内容与 summary**：核验 `inspect_deck`、`inspect_pile` 的摘要时，一并设计 `get_observation` 对应覆盖页的内容与摘要；共用顶栏摘要已经实现。见同一份[浏览覆盖记录](../research/2026-11-02-get-observation-browsing.md#本阶段定稿与后续接入)。
- [ ] **商店详情改进**：核验 `inspect_shop` 时设计当前金币等购买上下文的直接返回，以及该工具的参数与摘要；商品卡正文继续由专门查看提供。见[商店核验记录](../research/2026-11-03-get-observation-shop-ancient-event.md)。
- [ ] **游玩知识库**：提供官方术语和必要的开局知识；目前仅有方向记录。见[知识库计划](../research/2026-11-01-knowledge-base-plan.md)。
