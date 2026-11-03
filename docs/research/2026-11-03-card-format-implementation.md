# 共享卡牌格式实施记录

> 当前状态：实施中。共 4 项，已完成 1 项；已完成 Affliction、附魔空值及相关小范围重构；正在迁移卡牌格式与浏览参数，随后补充手牌资源字段并完成联合验证。暂无阻塞。

## 依据与边界

执行[卡牌覆盖定稿](2026-11-03-card-format-coverage.md)和[手牌核验](2026-11-03-inspect-hand-review.md)，工具核销沿用[工具清单](2026-11-02-mcp-tool-review.md)。原生端负责可见性、完整采样与游戏线程，Python 负责校验、筛选和输出投影。实卡与隔离网格克隆分别读取，共享字段组装；不重算持有卡牌，不暴露抽牌顺序，不修改正式安装。

## 实施顺序

- [x] **1. Affliction 与外观空值。** 在 `Observation/CardAppearance.cs` 集中实卡外观读取与模型预览字段组装；`CombatObservation` 共用手牌枚举，`BrowsedCard` 接入。Python 卡牌结构接受 nullable enchantment/affliction，共享摘要保留可见 affliction.name。先用 `tests/python/test_card_enchantments.py` 验证全预设、共存、非法值与过滤前校验；原生检查覆盖隐藏、透明、离屏和未知牌，实测魂缚／烟雾。
- [ ] **2. 统一牌面与浏览参数。** Python 提供固定 face/full/summary 卡牌入口；展开候选、比较及结算采样完整悬停解释，保留侧别。牌组／牌堆移除 detail_level，公开 preset 为 default/full/summary，CLI 复用投影。先补统一格式、浏览参数和比较解释回归，再修改原生读取、校验、共享提示、工具描述及文档。
- [ ] **3. 手能量与星星。** 提取独立 HUD 读取和共用资源摘要，inspect_hand 增加 energy/max_energy/stars；full 保留 null，default 过滤，summary 合并完整能量对并保留 stars:0。先验证空筛选、全部缺失、隐藏／不完整计数和错误结果，再实现。
- [ ] **4. 联合验证与交付。** 执行完整 Python、纯 C# 检查及编译；准备隔离运行时，通过真实 stdio MCP 验证外观、选择比较、牌组／牌堆、资源及动作回执。审查差异，更新持续维护文档和版本基线，独立审阅后提交。

各项按“补回归并观察失败 → 最小实现 → 相关检查与图形验证 → 同步文档 → Conventional Commit”执行。完整用例及证据放在 `.tmp/2026-11-03-card-format-implementation/`，失败目录保留，不覆盖重跑。

## 重点复核

- 未知卡和不可读覆盖不泄露 Affliction、附魔身份或悬停解释。
- 比较两侧共用原牌 ID，但保留各自解释与 null；随机 after:null 不被补出。
- 动作回执和页面工具也接入共享格式，商店基础观察仍无正文。
- 牌组／牌堆默认现在提供完整内容；旧 detail_level 在 UI 操作前拒绝。
- 资源读取独立于玩家身体是否可见，空筛选照常返回计数，不凭角色补星星。

## 执行与验证

实施前工作区干净，基线提交 `9bb583b`。详细检查结果将在各阶段完成后补入本节。

### 阶段 1

- Python 新回归先在旧实现失败（nullable 附魔被拒绝，Affliction 未校验），实现后完整 498 项通过；纯 C# 60 项通过，编译无警告／错误。
- `phase1-gui` 中魂缚／烟雾及原有六张附魔场景均通过真实 stdio MCP；原生检查覆盖隐藏、透明、离屏、未知／锁定与共存，采样前后状态完整相等。已人工查看 Affliction 截图。其他五种覆盖仅沿用已核对资源与共用读取，未逐一进行 GUI 实测。
- 证据：`.tmp/2026-11-03-card-format-implementation/phase1-python.log`、`phase1-gui/report.json` 及各例 evidence。测试进程 PID 39998 已结束。
