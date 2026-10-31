# 在正常游戏中加载 Mod 并读取状态

当前原型可以响应 `get_state` 请求，以英语 JSON 输出可见战斗数值、敌人名称与意图、手牌名称及费用、状态图标和顶栏；Mod 0.4.0 起提供 [手牌详情调用](hand-inspection.md)，0.5.0 起提供 [界面悬停说明](ui-inspection.md)，0.6.0 起提供 [药水详情](potion-inspection.md)，0.7.0 起提供 [双方 powers 与敌人意图详情](combatant-inspection.md)，0.8.0 起提供 [遗物详情](relic-inspection.md)，0.9.0 起提供真实打开页面的 [全牌组查看及显式关闭](deck-inspection.md)。0.11.0 起提供三类 [战斗牌堆查看](pile-inspection.md)，含真实空堆反馈。它按请求返回 JSON，不会持续自动输出；基础字段及限制见 [战斗观察 JSON](observation.md)。

以下步骤适用于 Linux Steam 游戏 `v0.107.1`，依据已核对的 Mod 加载器和现有接口整理。独立无头实例已完成验证；正常游戏中的读取已有 [响应与截图样本](../research/2026-10-29-battle-observation-audit.md)，该样本使用旧版结构；新版按 [静态画面信息边界](../observation.md) 过滤，已增加独立图形实例的验证。

## 安装文件

Mod 0.12.0 新增 [地图查看与独立关闭](map-inspection.md)，文件接口与 MCP 均可用。

按 [README](../../README.md#开发与运行入口) 配置游戏目录并在当前终端加载 `.env`。退出游戏后，把构建产物中的 `Sts2Agent.dll` 与 `Sts2Agent.json` 放入：

```text
<游戏安装目录>/mods/Sts2Agent/
```

需要重新构建时，先按 [验证指南](roundtrip.md) 的构建步骤生成产物，再在项目根目录分别执行以下两条命令：

```sh
mkdir -p "${Sts2Dir:?请先配置并加载 .env}/mods/Sts2Agent"
```

```sh
cp spikes/roundtrip/bin/Debug/net9.0/Sts2Agent.dll spikes/roundtrip/bin/Debug/net9.0/Sts2Agent.json "${Sts2Dir:?请先配置并加载 .env}/mods/Sts2Agent/"
```

该 Mod 清单声明依赖 RitsuLib `0.6.10` 的 `0.107.1` 兼容运行时。已经通过 Steam 创意工坊安装并启用兼容版本时，保留创意工坊管理的安装，不再手工复制第二套。

只有采用手工安装 RitsuLib 的方式时，才按[构建指南](roundtrip.md#前提与构建)获取完整发布包，将整个解压目录放入 `<游戏安装目录>/mods/STS2-RitsuLib/`，保留 `shared/`、`compat/`、`assets.zip` 等全部内容，不要只复制根 DLL。在游戏内启用依赖后重启，再加载本项目。结束回合事件及选择停止边界见[接口说明](end-turn.md)。

## Steam 启动配置

在 Steam 游戏库中打开游戏的“属性 → 通用 → 启动选项”，加入下列配置，将 `/absolute/path/to/sts2_agent` 替换为项目目录的实际绝对路径。移动项目后应同步修改：

```text
env STS2_AGENT_IPC_DIR="/absolute/path/to/sts2_agent/.tmp/live/ipc" %command%
```

`%command%` 保留 Steam 原有启动命令，在它前面通过 `env` 设置通信目录；Steam 启动选项的包装方式参见 [Steam 官方支持说明](https://help.steampowered.com/en/faqs/view/145A-FE54-F37B-278A)。已有启动选项时应合并保留原设置。

正常启动不设置 `STS2_AGENT_TEST_MODE=1`。此流程使用游戏自身的 Mod 存档规则，与独立测试实例的临时存档不同。

启动游戏后，在游戏的 Mod 界面完成首次加载提示并启用 `STS2 Agent Roundtrip Spike`；按游戏提示重启，使其在启动时加载。游戏不会在运行中直接加载刚复制进去的 DLL。

## 读取敌人

进入战斗后，在项目根目录执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc get_state
```

默认成功结果中，`scene` 为 `combat`，`enemies` 列出敌人；每项包含可见身份、生命、格挡、状态图标与当前意图；名称使用英语。战斗被详情页、教学等覆盖时 `screen.status` 为 `covered`，暂不返回战斗数据。主菜单没有战斗敌人，返回 `enemies: null` 属于正常情况。需要原始响应与状态令牌时，在命令后增加 `--raw`。

每运行一次命令读取一次当前状态。只调用 `get_state` 不会提交游戏动作。

如果请求超时，先检查 Mod 是否已启用并重启、Steam 启动选项是否生效，以及客户端与 Mod 是否使用同一个通信目录。日志出现 `[Sts2Agent] Main-thread pump attached.` 表示通信处理入口已连接；若出现 `STS2_AGENT_IPC_DIR is unset, bridge disabled.`，则表示环境变量没有传入游戏。

Mod `0.14.0` 接通 [选牌与显式查看战场](card-selection.md)，需同时更新外部 MCP 脚本；RitsuLib 也可由 Steam 创意工坊管理，无须另复制一套。

Mod `0.15.0` 增加 [出牌与目标查询](card-play.md)，需更新外部脚本并重新连接 MCP；替换游戏目录中的 Mod 后，完整重启游戏才能加载新程序集。

Mod `0.16.0` 增加 [使用与丢弃药水](potion-actions.md)，目标查询复用 `inspect_targets`，含战斗外顶栏读取。需同时更新 MCP server 至 `0.13.0`；创意工坊已管理 RitsuLib 时保留现有安装，无须另复制一套。

Mod `0.17.0` 与 MCP server `0.14.0` 增加[可配置截图存档](screenshots.md)，默认关闭；更新 Mod 后完整重启游戏，再按配置重启 MCP 连接。保留创意工坊管理的 RitsuLib。

Mod `0.18.0` 修复[动作返回早于牌堆可见计数更新](end-turn.md#动作完成与画面稳定)，保留原有工具与参数。替换 DLL 后须完整重启游戏，重连 MCP 以读取更新的公共提示。

Mod `0.19.0` 与 MCP server `0.15.0` 接通武装等[手牌升级选择](card-selection.md#手牌升级)，包括预览、取消、改选、确认与眼睛查看战场。更新后仍须重启游戏和 MCP；运行中的旧 Mod 不会热更新。

Mod `0.20.0` 统一[可见卡牌名称](observation.md#手牌与身份)，目标查询及事件保留牌面升级后缀，并修复选牌确认后的事件名称缓存。MCP 工具和参数不变；替换 DLL 后完整重启游戏。

MCP server `0.16.0` [复用完整成功动作的观察](mcp.md#调用和错误语义)，可以连续决策与执行。Mod 仍为 `0.20.0`；只需重连 MCP 加载新脚本及公共说明，无须重启或替换游戏内 Mod。

当前 Mod `0.24.0`、MCP `0.20.0` 支持[战后搜刮与前进](rewards.md)、[休息处选项与锻造](rest-site.md)、[宝箱房](treasure.md)及[商店](shop.md)。需替换 Mod DLL/清单并完整重启游戏，同时重连 MCP；RitsuLib 仍由创意工坊管理。
