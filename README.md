# sts2_agent

通过《杀戮尖塔 2》（Slay the Spire 2）的 Mod 接入游戏，向大语言模型（LLM）提供读取状态和执行动作的工具，逐步实现自主游玩。

## 当前状态

项目已有针对 Linux 游戏 `v0.107.1` 的最小验证原型：C# Mod 通过本地文件接口提供状态读取和结束回合动作，游戏外的 stdio MCP server 向 agent 提供同一套能力，已在独立游戏实例中完成真实 Codex 模型的观察、结束回合和读回验证。当前未覆盖出牌或完整游玩流程。

复现方式见 [最小流程验证指南](docs/development/roundtrip.md)，实测结果及接口依据见 [验证记录](docs/research/2026-10-28-roundtrip-validation.md)。较早的 [Mod 接入基线调研](docs/research/2026-10-28-modding-baseline.md) 保留初步调查时的版本证据。

## 接入方向

整体方向由三部分组成；当前原型提供最小工具范围：

| 部分 | 职责 |
| --- | --- |
| 游戏内 Mod | 读取当前状态，在游戏允许的时机执行合法动作，并返回结果 |
| 工具接口 | 对外提供结构化状态、可用动作、参数约束和错误反馈，隔离游戏内部对象 |
| LLM 客户端 | 根据观察选择动作、调用工具，持续记录决策与执行结果 |

当前原型使用 C# DLL Mod、后台文件请求处理和 Godot 主线程动作执行，不依赖社区库或 Godot 编辑器。外部采用 Python stdio MCP server，复用已有文件 IPC；[MCP 接入指南](docs/development/mcp.md) 提供安装和 Codex 配置方式。模型调用由 agent 客户端负责。

[BaseLib](https://github.com/Alchyr/BaseLib-StS2) 是社区 Mod 基础库，[RitsuLib](https://github.com/BAKAOLC/STS2-RitsuLib) 提供生命周期、补丁和其他共享功能。它们是待评估的依赖，不等于现成的 LLM 控制接口，也不预设必须同时引入。应先核对原生能力和目标版本，再按实际需要选择依赖。

## 首个验证结果

已在单人临时战斗中完成以下验证；测试战斗通过单独启用的开发入口创建，不代表已经实现从主菜单正常推进到战斗的自动游玩：

1. 游戏成功加载最小 Mod，输出初始化及主线程处理入口的日志。
2. 外部程序读取角色、手牌、敌人、回合和可用动作。
3. 外部程序提交结束回合，Mod 校验状态与合法性，通过游戏动作队列执行。
4. 回合从 1 推进到 2，读回状态与动作响应一致；非法、旧状态及重复请求的处理通过检查。

基础观察现已扩展为 [英语战斗 JSON](docs/development/observation.md)，覆盖当前意图、手牌名称与费用、状态图标和顶栏，使用稳定卡牌 ID 并精简给 LLM 的控制与显示字段，并按 [可见信息边界](docs/observation.md) 过滤。文件接口和 MCP 均提供 [全部当前可见手牌详情](docs/development/hand-inspection.md)、[当前界面悬停说明](docs/development/ui-inspection.md) 和 [药水详情](docs/development/potion-inspection.md)；药水详情保留空槽位置并共享重复解释。文件接口和 MCP 也提供 [双方 powers 与敌人意图详情](docs/development/combatant-inspection.md)，支持共享悬停解释。文件接口和 MCP 也提供 [遗物详情](docs/development/relic-inspection.md)。MCP 目前提供 `get_observation()`、`inspect_hand()`、`inspect_ui()`、`inspect_potions()`、`inspect_combatants()`、`inspect_relics()` 和 `end_turn()`；出牌等动作及其他场景后续扩展。完整游玩仍是长期目标。

## 本地游戏与开发前提

本机 Linux Steam 安装位置为：

```text
~/.local/share/Steam/steamapps/common/Slay the Spire 2
```

此路径仅作为本机参考，后续实现应允许配置。开发与运行需要自行安装游戏；仓库不包含游戏程序集、资源或存档。游戏及依赖更新后，应重新核对兼容性，不能直接以社区库的最新版本适配本地旧版本。

原型使用 .NET 9 SDK 和 Python 3；验证指南提供构建及启动命令。原有文件客户端只使用 Python 标准库，MCP server 另需安装 [requirements-mcp.txt](requirements-mcp.txt) 中的依赖。无头环境下观察到音频和渲染警告。当前已用独立图形实例核对中文界面与英语观察；声音、其他游戏版本及完整游玩兼容性尚未验证。

## 文档入口

- [AGENTS.md](AGENTS.md)：精简的项目协作约定。
- [文档编写与维护规范](docs/documentation.md)：文档职责、日期命名与维护要求。
- [Codex 环境约定](docs/ai/codex.md)：沙箱权限、命令拆分及子代理模型选择入口。
- [Cursor 模型选择](docs/ai/cursor-model-selection.md)：Cursor 环境适用的约定。
- [最小流程验证指南](docs/development/roundtrip.md)：构建、独立实例启动、客户端调用及协议边界。
- [正常游戏加载与读取](docs/development/live-game.md)：Steam 安装位置、启动配置和读取敌人的操作步骤。
- [本地 MCP 接入](docs/development/mcp.md)：战斗观察、手牌详情、结束回合、Codex 配置和错误恢复。
- [战斗观察 JSON](docs/development/observation.md)：英语字段、显示条件、保存与独立验证。
- [手牌详情 JSON](docs/development/hand-inspection.md)：一次读取当前手牌的正文、悬停解释及数值说明。
- [可见信息边界](docs/observation.md)：基础观察的信息范围与当前实现差距。
- [战斗画面与 JSON 对照](docs/research/2026-10-29-battle-observation-audit.md)：正常游戏读取样本与对应截图的逐项核对。
- [观察字段获取方式](docs/research/2026-10-29-observation-data-sources.md)：模型成员、UI 节点、显示规则及尚需运行验证的范围。
- [最小流程验证记录](docs/research/2026-10-28-roundtrip-validation.md)：当前版本 API 依据和真实游戏验证结果。
- [Mod 接入基线调研](docs/research/2026-10-28-modding-baseline.md)：本地版本证据、上游资料及待验证事项。
