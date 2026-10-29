# sts2_agent

通过《杀戮尖塔 2》（Slay the Spire 2）的 Mod，向大语言模型提供游戏观察与合法动作接口，逐步实现自主游玩。

## 当前能力

当前为 Linux 游戏 `v0.107.1` 的验证原型：Mod `0.12.0` 通过本地文件 IPC 与 Python stdio MCP server 通信，模型调用由外部 agent 客户端负责。已有真实游戏及 Codex 模型的观察、结束回合和读回验证；尚未支持出牌、使用药水、地图选路或完整自动游玩。

| 能力 | 接口与说明 |
| --- | --- |
| 基础观察 | 当前静态画面的英语 JSON，包含角色、手牌名称与费用、敌人当前意图、状态图标及顶栏；见 [观察格式](docs/development/observation.md) |
| 按需详情 | 查看 [手牌](docs/development/hand-inspection.md)、[界面帮助](docs/development/ui-inspection.md)、[药水](docs/development/potion-inspection.md)、[双方 powers 与意图](docs/development/combatant-inspection.md)、[遗物](docs/development/relic-inspection.md) |
| 原生页面 | 查看 [全牌组](docs/development/deck-inspection.md)、[战斗牌堆](docs/development/pile-inspection.md) 和 [当前幕地图](docs/development/map-inspection.md)，保留页面直到显式关闭 |
| 游戏动作 | 结束一次回合；执行前校验观察令牌与合法性，通过游戏现有动作队列执行 |

MCP 固定提供 12 个工具，完整目录及调用语义见 [MCP 接入](docs/development/mcp.md)。基础观察不自动展开详情；隐藏对象、抽取顺序和未来随机结果不对模型开放，规则见 [可见信息边界](docs/observation.md)。

## 开发与运行入口

- [最小流程验证指南](docs/development/roundtrip.md)：.NET 9 构建、独立游戏实例和文件协议。
- [正常游戏加载与读取](docs/development/live-game.md)：安装 Mod、配置游戏启动和读取正式战斗。
- [本地 MCP 接入](docs/development/mcp.md)：依赖安装、Codex 配置、工具与错误恢复。
- [代码结构与验证](docs/development/architecture.md)：模块职责、修改入口和无需游戏的检查。

需要自行安装 Linux 游戏、.NET 9 SDK 和 Python 3；MCP 另需 [requirements-mcp.txt](requirements-mcp.txt)。游戏路径可通过构建参数 `Sts2Dir` 和准备脚本 `--game-dir` 配置。本机 Steam 安装位置仅供参考：`~/.local/share/Steam/steamapps/common/Slay the Spire 2`。

仓库不包含游戏程序集、资源、存档或密钥。当前不依赖社区库或 Godot 编辑器；[BaseLib](https://github.com/Alchyr/BaseLib-StS2) 和 [RitsuLib](https://github.com/BAKAOLC/STS2-RitsuLib) 仅为待评估依赖。升级游戏或依赖前须重新核对 API 和兼容性。声音、其他游戏版本及完整游玩尚未验证。

## 协作与证据

- [协作约定](AGENTS.md)、[文档规范](docs/documentation.md)、[Codex 环境约定](docs/ai/codex.md)、[Cursor 模型选择](docs/ai/cursor-model-selection.md)。
- [项目审阅与重构](docs/research/2026-10-29-project-review.md)：输出边界、提示词、JSON 格式、官方实践及验证范围。
- [最小往返验证](docs/research/2026-10-28-roundtrip-validation.md)、[基础画面核对](docs/research/2026-10-29-battle-observation-audit.md)、[地图 MCP 验证](docs/research/2026-10-29-mcp-map-inspection.md)：阶段性证据，当前接口以开发指南为准。
