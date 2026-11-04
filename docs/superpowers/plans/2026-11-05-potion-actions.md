# 药水动作与地图显示状态实施计划

> 当前状态：实现与验证完成，共 3 项，已完成 3 项；34 类用药情形和三组既有工具回归通过，独立审查的重要问题已修复。用户已确认五项用药修复及地图 status:covered，不新增 summary，不处理地图内容。暂无阻塞。
> 执行方式：使用 superpowers:executing-plans 在当前工作区逐项实施，最后进行一次独立审查。

**目标：** 用药拒绝能说明原因且明确未执行时可直接继续，槽位独立判断，公开药水变化不漏记；地图与牌组采用相同 covered 含义。

**依据：** [用户说明](../../research/2026-11-04-use-potion-review.md)、[开发核验](../../research/2026-11-04-use-potion-development-notes.md)及用户确认：地图先统一 covered；五项全部处理；不增加 summary。已获执行授权，不再重复设计确认。

**约束：** 保留原生用药、目标、选择、取消与战斗交接；不预测效果、重试未知结果或读取隐藏内容。inspect_map 参数及 get_observation.map 内容维持现状。旧审阅样本冻结。

## 1. 参数、错误恢复与共用动作判断

- [x] 在 tests/python/test_potion_recovery.py 添加 RED：use/discard 明确未提交拒绝后可直接 end_turn；无旧读取、stale_state、矛盾执行事实及未知错误不恢复；参数错误给出字段与合法类型。
- [x] 新增 GameAdapter.PotionRules.cs，集中 PotionStageUnavailableReason；PotionActions 负责单槽、移除、使用及目标诊断。拒绝只在 UI 交互开始之前给出明确未提交保证；登记对应 MCP 恢复契约。
- [x] 精简 inspect_targets/target_id 说明，解释原槽位映射。full/default 参数不变。
- [x] 专项 Python RED→GREEN，运行完整 Python 集合。

## 2. 展示、单槽交互、事件与地图

- [x] 新建 verify_potion_recovery.py 与 gui_suite_potion_recovery.json，先以旧 DLL 复现 slot_boundary、journal_boundary 及地图状态失败。
- [x] PotionInspection 提供保持原下标的原始槽位、单槽展示及交互判断；观察维持整栏未知规则，动作和事件不再因为无关槽位的交互能力失败。去掉槽位视口截断，保留真实隐藏／裁剪检查。
- [x] PotionJournal、RunInventoryJournal 使用展示判断；增加获得药水的 disabled/offscreen 边界验证。隐藏槽位及隐藏顶栏仍不得补记，取消不伪造使用。
- [x] ObservationContext.Visibility 在地图暴露时返回 covered；保留其他 scene、view、地图主体及操作逻辑。
- [x] 构建、C# 检查、GUI 验证 RED→GREEN；覆盖普通与特殊目标、资源变化、选择、取消、胜负、战斗外、父任务等待奖励、槽位替换、旧令牌及原生丢弃回归。

## 3. 文档与交付

- [x] 同步现行药水、观察、MCP 与 GUI 文档；记录新行为和实测范围，不覆盖旧样本；主清单仅核销 use_potion。
- [x] 运行完整 Python、C#、链接／样例来源检查；进行一次独立整体验证审查，修复重要问题，保留低优先级未覆盖范围。
- [x] 提交已验证变更，说明实测结果、未验证范围及正式 Mod 未安装。

## 审查重点

- 新局、隐藏或未准备就绪时不能因失败创建操作许可。
- 交互开始／原生已入队后异常不得当作安全拒绝；取消仍须重新读取。
- 查询正常显示但不能悬停的槽位，应返回说明而不是影响别的槽位；具体药水须受自身原生限制。
- 用药、自动触发及获得事件只记录已经展示的内容；禁用不等于隐藏。
- 地图 covered 不改变顶栏可读性、战斗外地图用药、建筑师或结算页面的操作范围。
