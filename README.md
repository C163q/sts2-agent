# sts2_agent

通过《杀戮尖塔 2》（Slay the Spire 2）的 Mod，向大语言模型提供游戏观察与合法动作接口，逐步实现自主游玩。

项目以尽可能还原人类玩家的操作过程与 UI 反馈为目标，优先保证 LLM 获得的信息与玩家能从 UI 中获得的信息一致，而非追求最高的游戏操控效率。工具设计与信息取舍遵循这一原则，具体规则见[可见信息边界](docs/observation.md)。

## 当前能力

当前为 Linux 单人游戏的验证原型：游戏内 Mod 通过本地文件 IPC 与 Python stdio MCP server 通信，模型调用由外部 agent 客户端负责。支持逐步游玩、地图选路和终局结算；各项真实游戏验证及未覆盖范围见对应接口文档。

| 能力 | 接口与说明 |
| --- | --- |
| 基础观察 | 当前静态画面的英语 JSON，包含角色、友方召唤物、悬浮君王之剑身份、手牌名称与费用、敌人当前意图、状态图标及顶栏；见 [观察格式](docs/development/observation.md) |
| 按需详情 | 查看 [手牌](docs/development/hand-inspection.md)、[界面帮助](docs/development/ui-inspection.md)、[药水](docs/development/potion-inspection.md)、[战斗对象、充能球与悬浮剑](docs/development/combatant-inspection.md)、[遗物](docs/development/relic-inspection.md) |
| 原生页面 | 查看 [全牌组](docs/development/deck-inspection.md)、[战斗牌堆](docs/development/pile-inspection.md) 和 [当前幕地图](docs/development/map-inspection.md)，保留页面直到显式关闭 |
| 游戏动作 | [出牌与目标查询](docs/development/card-play.md)，一次提交卡牌及必要目标；[结束回合](docs/development/end-turn.md)，返回期间事件、停止原因及当前交互状态；遇到选择时返回；通过 [选牌工具](docs/development/card-selection.md) 操作候选、确认及跳过，支持显式查看战场 |
| 药水动作 | [使用、丢弃与目标查询](docs/development/potion-actions.md)，支持单人战斗和符合原生条件的战斗外使用，后续选牌单独处理 |

战后支持[逐项搜刮、跳过与前进](docs/development/rewards.md)，奖励卡牌复用选牌工具；搜刮期间可以查看地图，并用 [travel_to_node 选路](docs/development/map-inspection.md#地图选路)；选路会放弃未领取奖励。每幕最后 Boss 后的前进沿原生流程进入下一幕，双 Boss 之间仍需选路；支持[建筑师对话、胜负结算及解锁后返回主菜单](docs/development/run-ending.md)。支持[休息处选项](docs/development/rest-site.md)、锻造升级与烹饪选牌，帐篷下逐项操作。支持[宝箱房开箱、领取与跳过](docs/development/treasure.md)，默认一次调用开箱并领取遗物。支持[商店开关、商品详情、逐项购买与删牌](docs/development/shop.md)。

已接通[先古之民房间](docs/development/ancients.md)：逐句对话、选择遗物、后续选牌与前进。支持[通用问号事件](docs/development/events.md)的正文与选项、致死红框、后续选牌/奖励、战斗及返回事件；[占卜](docs/development/divination.md)支持棋盘图像、大小工具与逐格揭开。[Trial 确认弹窗](docs/development/events.md#事件确认弹窗)支持明确确认或取消；未知弹窗仍停在人工输入边界。

默认提供 42 个 MCP 工具，可通过启动配置增加[截图存档工具](docs/development/screenshots.md)。完整目录、输出预设和调用语义见 [MCP 接入](docs/development/mcp.md)；各工具与场景说明见[开发文档索引](docs/development/README.md)。

## 当前版本与前提

本表统一维护当前代码版本与已核对的兼容基线。

| 项目 | 当前版本或要求 | 核对入口 |
| --- | --- | --- |
| 游戏 | Linux `v0.107.1`，release 分支，构建 `59260271` | [目标程序集核对与验证](docs/research/2026-11-03-result-observation-implementation.md) |
| Mod | `0.53.0` | [Mod 清单](src/Sts2Agent/Sts2Agent.json) |
| MCP server | `0.54.0` | [服务入口](src/sts2_mcp/mcp_server.py) |
| 底层观察 schema | `34` | [观察序列化](src/Sts2Agent/Adapter/GameAdapter.cs) |
| RitsuLib | `0.6.10`，须使用游戏 `0.107.1` 兼容运行时 | [获取与构建](docs/development/roundtrip.md#前提与构建) |
| .NET | 9 SDK；版本选择见 [global.json](global.json) | [构建指南](docs/development/roundtrip.md#前提与构建) |
| Python | 3.10 或以上；MCP 另需安装依赖 | [requirements-mcp.txt](requirements-mcp.txt) |

手工获取 RitsuLib 时，使用[作者发布的兼容包](https://github.com/BAKAOLC/STS2-RitsuLib/releases/tag/v0.6.10) `STS2.RitsuLib.Compat.0.107.1.0.6.10.github.zip`，完整解压后作为 `RitsuLibDir`。已核对的发布包 SHA-256 为 `3c7dafb8a8d36d66891abd6c601aec6f43de9890693d1b583e67e2c6d71ebfb5`；已有创意工坊管理的兼容安装可直接使用。

不依赖 BaseLib 或 Godot 编辑器。其他游戏版本、多人及声音不属于已验证范围。

## 安装与使用

1. 按[构建指南](docs/development/roundtrip.md#前提与构建)编译 Mod；正常使用无须准备独立测试实例。
2. 退出游戏，按[安装说明](docs/development/live-game.md#安装文件)复制产物，启用 Mod 和依赖并重启。
3. 按[启动配置](docs/development/live-game.md#steam-启动配置)设置 `STS2_AGENT_IPC_DIR`。
4. 按[MCP 接入](docs/development/mcp.md#安装与游戏前提)安装依赖并配置客户端，`--ipc-dir` 须与游戏侧一致。
5. 启动游戏，成功读取观察后按当前工具及候选逐步操作；成功详情及满足条件的动作结果可直接续接，见[MCP 调用规则](docs/development/mcp.md#调用和错误语义)。

列出 MCP 工具只说明 Python 服务已启动；新请求成功取得观察才说明游戏内接口能够响应。更新与排错见[正常游戏指南](docs/development/live-game.md#更新与排错)。

## 开发与运行入口

- [图形测试套件](docs/development/gui-testing.md)：复用游戏进程执行多局，支持显式同局连续步骤。
- [最小流程验证指南](docs/development/roundtrip.md)：.NET 9 构建、独立游戏实例和文件协议。
- [正常游戏加载与读取](docs/development/live-game.md)：安装 Mod、配置游戏启动和读取正式战斗。
- [本地 MCP 接入](docs/development/mcp.md)：依赖安装、Codex 配置、工具与错误恢复。
- [代码结构与验证](docs/development/architecture.md)：模块职责、修改入口和无需游戏的检查。
- [开发文档索引](docs/development/README.md)：所有现行接口与测试说明。

生产源码位于 `src/Sts2Agent/`（C# Mod）和 `src/sts2_mcp/`（Python）；测试位于 `tests/`，`scripts/` 仅保留常用启动入口。C# 项目与纯检查项目可通过根 [Sts2Agent.sln](Sts2Agent.sln) 一起查看。

需要自行安装 Linux 游戏、.NET 9 SDK 和 Python 3；MCP 另需 [requirements-mcp.txt](requirements-mcp.txt)。先复制 [配置示例](.env.example)：

```sh
cp .env.example .env
```

根据机器环境编辑 `.env`，将 `Sts2Dir` 填为游戏安装目录的绝对路径，`RitsuLibDir` 填为完整兼容运行时的目录；获取方式见 [构建指南](docs/development/roundtrip.md#前提与构建)。在执行构建、准备或安装命令的终端中先运行：

```sh
. ./.env
```

## 后续计划

用户指定留待后续处理的事项统一见[用户后续待办](docs/development/TODO.md)；Agent 不自行追加事项或自动启动清单中的工作。

## 协作与证据

- [协作约定](AGENTS.md)、[文档规范](docs/documentation.md)、[Codex 环境约定](docs/ai/codex.md)、[Cursor 模型选择](docs/ai/cursor-model-selection.md)。
- 各接口文档链接对应的源码核对、验证报告和样本；带日期的记录保留当时基线。
- [工具核验清单及流程](docs/research/2026-11-02-mcp-tool-review.md)记录本轮逐项设计进度，当前行为以开发文档为准。
