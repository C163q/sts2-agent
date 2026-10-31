# sts2_agent

通过《杀戮尖塔 2》（Slay the Spire 2）的 Mod，向大语言模型提供游戏观察与合法动作接口，逐步实现自主游玩。

## 当前能力

当前为 Linux 游戏 `v0.107.1` 的验证原型：Mod `0.26.0` 通过本地文件 IPC 与 Python stdio MCP server 通信，模型调用由外部 agent 客户端负责。已有真实游戏及 Codex 模型的观察、结束回合和读回验证；尚未支持地图选路或完整自动游玩。

| 能力 | 接口与说明 |
| --- | --- |
| 基础观察 | 当前静态画面的英语 JSON，包含角色、手牌名称与费用、敌人当前意图、状态图标及顶栏；见 [观察格式](docs/development/observation.md) |
| 按需详情 | 查看 [手牌](docs/development/hand-inspection.md)、[界面帮助](docs/development/ui-inspection.md)、[药水](docs/development/potion-inspection.md)、[双方 powers 与意图](docs/development/combatant-inspection.md)、[遗物](docs/development/relic-inspection.md) |
| 原生页面 | 查看 [全牌组](docs/development/deck-inspection.md)、[战斗牌堆](docs/development/pile-inspection.md) 和 [当前幕地图](docs/development/map-inspection.md)，保留页面直到显式关闭 |
| 游戏动作 | [出牌与目标查询](docs/development/card-play.md)，一次提交卡牌及必要目标；[结束回合](docs/development/end-turn.md)，返回期间事件、停止原因及最终观察；遇到选择时返回；通过 [选牌工具](docs/development/card-selection.md) 操作候选、确认及跳过，支持显式查看战场 |
| 药水动作 | [使用、丢弃与目标查询](docs/development/potion-actions.md)，支持单人战斗和符合原生条件的战斗外使用，后续选牌单独处理 |

战后支持[逐项搜刮、跳过与前进](docs/development/rewards.md)，奖励卡牌复用选牌工具；搜刮期间可以查看地图。支持[休息处选项](docs/development/rest-site.md)、锻造升级与烹饪选牌，帐篷下逐项操作。支持[宝箱房开箱、领取与跳过](docs/development/treasure.md)，默认一次调用开箱并领取遗物。支持[商店开关、商品详情、逐项购买与删牌](docs/development/shop.md)。

已接通[先古之民房间](docs/development/ancients.md)：逐句对话、选择遗物、后续选牌与前进。支持[通用问号事件](docs/development/events.md)的正文与选项、致死红框、后续选牌/奖励、战斗及返回事件；占卜和特殊确认弹窗明确停在人工输入边界。

MCP 默认提供 36 个工具，可通过启动配置增加[截图存档工具](docs/development/screenshots.md)，完整目录及调用语义见 [MCP 接入](docs/development/mcp.md)。基础观察不自动展开详情；隐藏对象、牌堆中的未来抽取顺序和未发生的随机结果不对模型开放，规则见 [可见信息边界](docs/observation.md)。

## 开发与运行入口

- [最小流程验证指南](docs/development/roundtrip.md)：.NET 9 构建、独立游戏实例和文件协议。
- [正常游戏加载与读取](docs/development/live-game.md)：安装 Mod、配置游戏启动和读取正式战斗。
- [本地 MCP 接入](docs/development/mcp.md)：依赖安装、Codex 配置、工具与错误恢复。
- [代码结构与验证](docs/development/architecture.md)：模块职责、修改入口和无需游戏的检查。

需要自行安装 Linux 游戏、.NET 9 SDK 和 Python 3；MCP 另需 [requirements-mcp.txt](requirements-mcp.txt)。先复制 [配置示例](.env.example)：

```sh
cp .env.example .env
```

根据机器环境编辑 `.env`，将 `Sts2Dir` 填为游戏安装目录的绝对路径，`RitsuLibDir` 填为完整 RitsuLib `0.6.10`、游戏 `0.107.1` 兼容运行时的解压目录；获取方式见 [构建指南](docs/development/roundtrip.md#前提与构建)。`.env` 不纳入 Git，也不会自动读取；在执行构建、准备或安装命令的终端中先运行：

```sh
. ./.env
```

## 正常游戏使用顺序

以下命令从仓库根目录执行；先完成上述路径配置并加载 `.env`。

1. **编译 Mod**：

   ```sh
   dotnet build spikes/roundtrip/Sts2Agent.csproj -p:Sts2Dir="${Sts2Dir:?请先配置并加载 .env}" -p:RitsuLibDir="${RitsuLibDir:?请先配置并加载 .env}"
   ```

   产物位于 `spikes/roundtrip/bin/Debug/net9.0/`。依赖获取和构建前提见[构建指南](docs/development/roundtrip.md#前提与构建)；正常使用不需要运行独立实例的准备脚本。
2. **安装并启用**：退出游戏，将产物中的 `Sts2Agent.dll` 和 `Sts2Agent.json` 复制到 `<游戏安装目录>/mods/Sts2Agent/`，在游戏 Mod 界面启用后按提示重启。已有 Steam 创意工坊管理的兼容 RitsuLib 时保留该安装，不再复制另一套；文件及加载步骤见[安装说明](docs/development/live-game.md#安装文件)。
3. **配置游戏通信目录**：在 Steam 启动选项中设置 `STS2_AGENT_IPC_DIR`，例如：

   ```text
   env STS2_AGENT_IPC_DIR="/absolute/path/to/sts2_agent/.tmp/live/ipc" %command%
   ```

   将示例路径替换为实际路径，已有启动选项须保留；设置后完整重启游戏，详见[启动配置](docs/development/live-game.md#steam-启动配置)。
4. **接入 LLM 客户端**：按[MCP 接入](docs/development/mcp.md#安装与游戏前提)安装 Python 依赖，将 `scripts/mcp_server.py --ipc-dir <相同通信目录>` 配置为客户端的 stdio MCP 服务。脚本应使用已安装依赖的 Python 解释器启动；Codex 等客户端的完整参数示例见该指南。截图工具按[启动配置](docs/development/screenshots.md#启动配置)单独启用。
5. **验证并游玩**：启动游戏后先调用 `get_observation`，成功返回当前画面才说明游戏内接口能够响应。正常使用自行进入对局与战斗；LLM 根据当前观察按需查看详情、目标或选牌，完整成功的动作结果可直接用于下一动作；失败或切换查看页面后重新观察，详见[MCP 调用规则](docs/development/mcp.md#调用和错误语义)。更新 DLL 后须完整重启游戏，更新 MCP 脚本或配置后须重连 MCP。

MCP 不扫描游戏进程，也不负责启动游戏。客户端与 Mod 通过配置好的同一目录交换请求和响应；列出工具只说明 MCP 服务已启动，不能证明游戏已运行或 Mod 已连通。交互过程及超时含义见[通信方式](docs/development/mcp.md#通信方式与连接状态)。

仓库不包含游戏程序集、资源、第三方库二进制、存档或密钥。当前依赖 [RitsuLib](https://github.com/BAKAOLC/STS2-RitsuLib) `0.6.10` 的 `0.107.1` 兼容运行时，不依赖 BaseLib 或 Godot 编辑器。升级游戏或依赖前须重新核对 API 和兼容性。声音、其他游戏版本及完整游玩尚未验证。

## 协作与证据

- [协作约定](AGENTS.md)、[文档规范](docs/documentation.md)、[Codex 环境约定](docs/ai/codex.md)、[Cursor 模型选择](docs/ai/cursor-model-selection.md)。
- [问号房与事件调研](docs/research/2026-10-31-events.md)：57个注册事件、战斗往返、致死红框、占卜与确认弹窗；当前已实现范围见[事件接口](docs/development/events.md)。
- [通用事件验证](docs/research/2026-10-31-events-validation.md)：33个事件场景用例、相邻回归、英文来源修复及未覆盖范围。
- [项目审阅与重构](docs/research/2026-10-29-project-review.md)：输出边界、提示词、JSON 格式、官方实践及验证范围。
- [结束回合事件与交互边界调研](docs/research/2026-10-29-end-turn-events.md)：战斗历史、RitsuLib 与选择暂停的设计依据；实际行为见 [接口说明](docs/development/end-turn.md)。
- [选牌与查看战场验证](docs/research/2026-10-30-card-selection-validation.md)：候选、确认、跳过、第一回合遗物、信息边界及审阅修复。
- [出牌接入验证](docs/research/2026-10-30-card-play-validation.md)：原生提交、目标范围、随机数不变性、后续选择及胜负边界。
- [药水接入验证](docs/research/2026-10-30-potion-actions-validation.md)：战斗外使用、原生丢弃、目标查询、后续选牌及真实 MCP。
- [出牌与目标选择调研](docs/research/2026-10-30-card-play-targeting.md)：原生提交、目标合法性、后续选牌与接口设计依据。
- [结束回合接入验证](docs/research/2026-10-29-end-turn-validation.md)：复杂机制、图形界面、真实 MCP 往返和未覆盖范围。
- [最小往返验证](docs/research/2026-10-28-roundtrip-validation.md)、[基础画面核对](docs/research/2026-10-29-battle-observation-audit.md)、[地图 MCP 验证](docs/research/2026-10-29-mcp-map-inspection.md)：阶段性证据，当前接口以开发指南为准。
