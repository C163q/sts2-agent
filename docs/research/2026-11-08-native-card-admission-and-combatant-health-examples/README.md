# 原生出牌接受与战斗对象生命样例

八份样本均为隔离图形测试取得的实际 MCP 返回，保留对应完整 JSON，不是手工拼接。核对日期 2026-11-08，Mod 0.82.0、MCP 0.85.0、schema 48；来源、参数、行号和实际 DLL 哈希见 [manifest.json](manifest.json)。[实施与验证](../2026-11-08-native-card-admission-and-combatant-health-implementation.md)说明范围。

- [完整战斗对象](combatants.full.json)、[默认空值过滤](combatants.default.json)、[生命摘要](combatants.summary.json)。
- [筛选 HP 和格挡](combatants.hp-filter.full.json)、[筛选生命摘要](combatants.health-filter.summary.json)。
- [奥斯提与共享格挡](combatants.osty.summary.json)。
- [原生费用不足的单张错误](admission.single-error.full.json)、[批量逐项拒绝](admission.batch.full.json)。
