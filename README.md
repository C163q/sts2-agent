# sts2_agent

通过《杀戮尖塔 2》（Slay the Spire 2）的 Mod，向大语言模型提供游戏观察与合法动作接口，逐步实现自主游玩。

项目以尽可能还原人类玩家的操作过程与 UI 反馈为目标，优先保证 LLM 获得的信息与玩家能从 UI 中获得的信息一致，而非追求最高的游戏操控效率。工具设计与信息取舍遵循这一原则，具体规则见[可见信息边界](docs/observation.md)。

## 工作方式

当前为 Linux 单人游戏的验证原型，需要在本机运行游戏、MCP 服务和 agent 客户端：

- **游戏内 Mod**：安装本项目 Mod 及其依赖 RitsuLib，读取可见信息并执行游戏操作。
- **MCP 服务**：运行项目提供的 Python 服务，通过本地通信目录与 Mod 交换请求和结果，向客户端提供游戏工具。
- **agent 客户端**：使用支持 stdio MCP 的客户端连接服务，由模型根据观察选择下一步操作。

游戏侧与 MCP 服务须配置为同一个通信目录，安装步骤见下文。

## 当前能力

工具以英语 JSON 提供观察与操作结果，游戏界面可以继续使用中文。当前支持以下游玩环节：

| 范围 | 能力与说明 |
| --- | --- |
| 观察与查询 | [读取当前画面](docs/development/observation.md)，包括毒／灾厄血条预示；按需查看手牌、战斗对象、药水、遗物及界面帮助；专项工具见[查看说明](docs/development/README.md#专门查看) |
| 战斗 | [单张或连续出牌、查询目标](docs/development/card-play.md)，[结束回合并读取期间变化](docs/development/end-turn.md)，[使用或丢弃药水](docs/development/potion-actions.md) |
| 选牌与浏览 | [选择、确认或跳过卡牌](docs/development/card-selection.md)，查看[全牌组](docs/development/deck-inspection.md)和[战斗牌堆](docs/development/pile-inspection.md) |
| 地图与奖励 | [查看地图并选路](docs/development/map-inspection.md)，[领取、跳过战后奖励及前进](docs/development/rewards.md) |
| 房间交互 | 操作[休息处](docs/development/rest-site.md)、[宝箱房](docs/development/treasure.md)、[商店](docs/development/shop.md)与[先古之民房间](docs/development/ancients.md)，包括相应选择、交易和对话 |
| 事件 | 阅读并选择[事件选项、处理确认弹窗](docs/development/events.md)，操作[占卜小游戏](docs/development/divination.md)；占卜支持文字棋盘和按需附图 |
| 一局结算 | [建筑师对话、胜负结算、解锁及返回主菜单](docs/development/run-ending.md) |

可按需启用[截图存档工具](docs/development/screenshots.md)。各环节的操作条件与验证范围见对应说明；遇到尚未支持的界面或弹窗时，需要人工处理。

## 当前版本与前提

当前组件版本及已核对的兼容基线如下；其他游戏版本、多人及声音尚未验证。

| 项目 | 当前版本或要求 |
| --- | --- |
| 游戏 | Linux `v0.107.1`，release 分支，构建 `59260271` |
| 本项目 Mod | `0.84.0` |
| MCP 服务 | `0.87.0` |
| RitsuLib | `0.6.10`，使用游戏 `0.107.1` 的兼容运行时，获取方式见[构建指南](docs/development/roundtrip.md#前提与构建) |
| .NET | 9 SDK，用于从源码构建 Mod |
| Python | 3.10 或以上，按[MCP 接入指南](docs/development/mcp.md#安装与游戏前提)安装依赖 |

另需支持 stdio MCP 的 agent 客户端。

## 安装与使用

1. 按[构建指南](docs/development/roundtrip.md#前提与构建)准备依赖、配置本机路径并构建 Mod。
2. 退出游戏，按[安装说明](docs/development/live-game.md#安装文件)复制产物，启用 Mod 和依赖并重启。
3. 按[启动配置](docs/development/live-game.md#steam-启动配置)设置 `STS2_AGENT_IPC_DIR`。
4. 按[MCP 接入](docs/development/mcp.md#安装与游戏前提)安装依赖并配置客户端，`--ipc-dir` 须与游戏侧一致。
5. 启动游戏并进入单人对局，让 agent 读取当前观察，再根据可用动作逐步游玩。

以成功读取当前游戏观察作为连通检查。工具调用与错误恢复见[MCP 调用规则](docs/development/mcp.md#调用和错误语义)，更新与排错见[正常游戏指南](docs/development/live-game.md#更新与排错)。

## 更多文档

- [工具与场景说明](docs/development/README.md)：各项操作的参数、输出和适用范围。
- [开发流程与协作约定](AGENTS.md)：参与项目开发的阅读入口、实施与验证要求。
