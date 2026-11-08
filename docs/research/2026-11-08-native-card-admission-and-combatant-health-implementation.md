# 原生出牌接受与战斗对象生命实现

> 当前状态：两项实现与验证完成，共 2 项，已完成 2 项。正在进行独立代码审阅，之后合入 main；无阻塞。

需求依据为[中期反馈复核](2026-11-08-mid-playtest-feedback-review.md)，步骤见[实施计划](../superpowers/plans/2026-11-08-native-card-admission-and-combatant-health.md)。开始基线为 `d2db4f0`；交付目标 Mod `0.82.0`、MCP `0.85.0`、底层观察 schema 48。游戏与 RitsuLib 源码依据沿用[开发核验](2026-11-08-mid-playtest-feedback-development-notes.md)。

## 行为变化

单张和批量出牌均由原生 TryManualPlay 决定卡牌是否可接受。Mod 保留场景、身份及可见目标范围校验，删除提前重复进行的 CanPlay／CanPlayTargeting 判断；原生拒绝后再读取公开原因。费用不足仍给出具体原因，明确拒绝后仍可直接提交其他合法动作。

批量工具保持快速连续入队。原生可以因回能尚未发生而拒绝后续高费牌；不预支未来资源，也不在回能后自动补发。能量事件的现有合并规则保持。

inspect_combatants 为玩家、敌人和友方召唤物提供可见生命与格挡：full/default 返回 hp、max_hp、hp_display、block；summary 使用 health，如 "70/80"、"∞"、"dead"、"unknown"，隐藏生命明确为 null。同伴共享本地玩家格挡时给出 block_shared_with:"player"。

sources 使用当前预设输出的路径：full/default 可选择 enemies.0.hp 或 enemies.0.block，summary 可选择 enemies.0.health。选择标量时保留敌人／友方身份，不附送其他未选中字段及悬停说明；原始位置映射继续保留。

## 小范围重构

生命、格挡及共享格挡关系进入现有 CombatantInspection 静态读取入口，get_observation 复用同一份数据，另行组装资源、手牌等字段。Python 的生命摘要也共用 health_summary；基础观察对外格式保持。

将生命读取纳入详情英语作用域时，原生死亡标签的当前语言比较会受到影响。新增原生检查明确复现后，由 LocalizedText 暂停英语改写完成标签比较，再恢复读取作用域；不修改游戏语言或界面文字。

schema 48 要求完整生命字段；旧响应没有这些字段时维持原格式。有字段但不完整、数值类型错误或生命显示状态不合法时，完整校验拒绝响应，不能以空 sources 掩盖。

## 验证记录

证据目录为 `.tmp/2026-11-08-native-card-admission-and-combatant-health/`。

- 原生入口 RED：旧实现下 0 能量请求在到达 TryManualPlay 前被拒，测试观察到调用次数为 0。修正后单张与批量均到达原生入口一次，具体拒绝原因和后续 end_turn 通过。
- 第一项：六项图形测试、844 项 Python 和 155 项 C# 检查通过，提交 `5cfe4fe`。图形场景包括原生拒绝、Normality、普通顺序、费用不足与选择续接。
- 新生命字段 RED：完整生命、摘要、筛选、坏数据断言在旧投影上失败；修正后专项 24 项通过。
- Python 全套首次新增后出现两项失败：旧 get_observation 不完整片段的摘要发生变化，已恢复原行为；旧测试将 hp 当私有字段，已改用未来生命字段检查过滤。随后 848 项通过。
- 原生生命检查：死亡文字比较断言先失败，修复后 43 项通过，包含隐藏生命条、隐藏数字和死亡显示，报告 `health-native-green/game/combatant-checks.json`。
- 最终图形回归 `health-gui/report.json` 九项全部通过：普通战场、充能球、奥斯提、悬浮剑、选择覆盖、零能量原生接受检查、批量费用、选择续接和原生拒绝。最终 848 项 Python、155 项 C# 通过。
- 源码构建与图形测试运行时 DLL 相同，SHA-256 为 `5cf2bf371b2f5767dee4678c3101e841a2ec95e183be8b119828b5fd6cdaedaa`。未在测试后重建产物。

八份[实际 JSON 样例](2026-11-08-native-card-admission-and-combatant-health-examples/README.md)包含 full/default/summary、静态字段筛选、奥斯提及费用拒绝；manifest 标注参数与原始证据位置。

一次沙箱内异步测试超时；外部有界运行成功取得真正的断言结果。一次原生检查启动方式错误，未传入原有检查开关而缺少报告；修正控制脚本后另建目录复测。失败日志保留，不视为通过。

## 交付范围

未修改 TODO、正式游戏存档或已安装 Mod。新增字段不从模型补齐隐藏生命；schema 48 的完整性要求只应用于新增版本响应。
