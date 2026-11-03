# 开发与接口文档索引

本目录说明当前实现。项目定位、当前版本及兼容基线统一见[项目 README](../../README.md#当前版本与前提)；文档维护遵循[文档规范](../documentation.md)。带日期的调研、样本和验证记录保留各自基线，不代表当前全部行为或本机已安装版本。

## 运行与开发

| 需要 | 入口 |
| --- | --- |
| 构建及隔离游戏实例、底层文件协议 | [最小流程验证指南](roundtrip.md) |
| 正常游戏安装、更新与排错 | [正常游戏加载与读取](live-game.md) |
| Python 依赖、客户端配置、工具目录及公共调用规则 | [MCP 接入](mcp.md) |
| 模块职责、变更入口及无需游戏的检查 | [代码结构与验证](architecture.md) |
| 图形套件、场景配置、进程与证据管理 | [图形测试](gui-testing.md) |

## 观察与动作

| 范围 | 入口 |
| --- | --- |
| 信息允许读取到什么程度 | [可见信息边界](../observation.md) |
| 基础字段、各场景 summary、actions_only 与 top_bar | [游戏基础观察 JSON](observation.md) |
| 出牌合法性及目标查询 | [出牌](card-play.md) |
| 选择、预览、筛选及查看战场 | [选牌](card-selection.md) |
| 使用、丢弃及药水目标查询 | [药水动作](potion-actions.md) |
| 停止原因、画面稳定和共享 transition 事件 | [结束回合与期间事件](end-turn.md) |

## 专门查看

| 范围 | 入口 |
| --- | --- |
| 卡牌 | [手牌](hand-inspection.md)、[永久牌组](deck-inspection.md)、[战斗牌堆](pile-inspection.md) |
| 战斗对象与界面 | [生物、充能球和悬浮剑](combatant-inspection.md)、[界面悬停说明](ui-inspection.md) |
| 物品 | [药水](potion-inspection.md)、[遗物](relic-inspection.md) |
| 地图 | [地图查看、子图及选路](map-inspection.md) |
| 图像存档 | [可选截图工具](screenshots.md) |

## 房间与结算

[奖励](rewards.md)、[休息处](rest-site.md)、[宝箱房](treasure.md)、[商店](shop.md)、[先古之民](ancients.md)、[通用事件及确认框](events.md)、[占卜](divination.md)、[建筑师与结算](run-ending.md)。

## 延期事项与核验工作

- [用户后续待办](TODO.md)：只按用户明确要求维护，记录不等于授权实施。
- [工具逐项核验清单及流程](../research/2026-11-02-mcp-tool-review.md)：本轮参数与摘要设计的阶段性工作记录；当前接口仍以本目录为准。
- [工具共用链路重构计划](../superpowers/plans/2026-11-03-tool-architecture-refactor.md)：第 1–2 阶段已完成，固定行为与 Python 共用输出链路见[实施记录](../research/2026-11-04-refactor-stages-1-2.md)；筛选、上下文和遗物悬停调整仍按后续阶段推进。
