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
cp src/Sts2Agent/bin/Debug/net9.0/Sts2Agent.dll src/Sts2Agent/bin/Debug/net9.0/Sts2Agent.json "${Sts2Dir:?请先配置并加载 .env}/mods/Sts2Agent/"
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

当前 Mod `0.45.0`、MCP `0.45.0` 支持[战后搜刮与前进](rewards.md)、[休息处选项与锻造](rest-site.md)、[宝箱房](treasure.md)、[商店](shop.md)、[先古之民](ancients.md)、[通用事件](events.md)及[终章结算](run-ending.md)。Mod 等待战斗卡牌预览、手牌描边、先古之民入场横幅及遗物入栏和计数等有限过渡结束，避免成功动作后的许可自行过期。需退出游戏后替换 Mod DLL/清单，再完整启动；RitsuLib 仍由创意工坊管理。只更新 Mod 不要求重连 MCP；更新 Python 脚本时须重连客户端。

MCP `0.29.1` 允许依据成功的专项详情及页面操作直接行动，不再要求额外 `get_observation`。从更早的 MCP 版本更新脚本后，须重连客户端加载新规则。

MCP `0.30.0` 增加[地图返回预设及前瞻子图](map-inspection.md#返回范围参数)，默认仍为全图。此功能只修改 Python 输出，不要求更换 Mod；重连 MCP 后即可使用。

MCP `0.31.0` 为 [手牌详情](hand-inspection.md#参数与返回范围)增加 `preset` 与 `card_ids`，支持精简字段及有效结果与无效 ID 合并报告。只需更新 Python 并重连 MCP，不要求更换 Mod。

Mod `0.36.0` 与 MCP `0.32.0` 为[基础手牌观察](observation.md#手牌与身份)和两种手牌详情预设增加可见附魔名称、显示计数及置灰表现。需更新 DLL 并完整重启游戏，再重连 MCP；未显示的计数不会由模型补齐。

工具说明来自 Python，不能据此确认游戏内 DLL 已更新。若 full 能读到附魔悬停效果，而基础观察和 summary 都没有结构化附魔字段，先核对安装的 Mod 清单与原始观察 schema；旧游戏端也能提供 full 的悬停效果。[r9 核查](../research/2026-11-02-r9-enchantments.md)记录了新 Python 搭配旧 DLL 的实例。

MCP `0.33.0` 为 `inspect_selection` 增加[完整与摘要预设](card-selection.md#mcp-输出预设)，所有候选、包内卡牌及预览均可使用手牌摘要字段；默认完整输出不变。预设功能只改 Python，无须为此替换 DLL，更新脚本后重连 MCP 即可。

MCP `0.42.0` 为同一工具增加 `card_ids`，按当前卡牌 ID 筛选候选、包内卡牌和已经展开的预览，保留选择提示与按钮；规则见[选择输出参数](card-selection.md#mcp-输出预设)。只需重连 MCP，Mod `0.43.0` 无须替换。

Mod `0.44.0` 与 MCP `0.44.0` 扩大遗物详情的非战斗场景，并支持原生入口可用的非战斗牌组查看；详情返回格式保持不变。需更新 DLL/清单和 Python，重启游戏并重连 MCP；范围与验证见[可用工具修复](../research/2026-11-02-available-actions-fix.md)。

MCP `0.43.0` 为 `inspect_relics` 增加 `preset: full/summary` 和 `relic_indices`，详情见[遗物参数](relic-inspection.md#mcp-参数)。使用当前未筛选详情列表的下标，不作为稳定 ID；只需重连 MCP，无须替换 Mod。

Mod `0.42.1` 与 MCP `0.40.0` 的[动作事件记录](end-turn.md#事件语义)包含可见玩家 HP、最大生命、金币、遗物与药水变化，永久牌组入组、离组、升级、降级、基础变量／能量费用直接变化和附魔变化，以及公开能量／星星、最大能量和蜡制遗物熔化、充能球生成／激发／离栏及槽位变化；战斗外入战及同次动作战斗替换统一接入日志，`combat_started` 分隔新战斗的 ID 作用域，底层 schema 为 `24`。需同时更新 DLL/清单和 Python，完整重启游戏并重连 MCP；旧客户端不认识新增事件类型。充能球观察及悬停分工见[第四阶段记录](../research/2026-11-01-capacity-and-orbs.md)；永久变化边界见[第五阶段记录](../research/2026-11-01-permanent-card-events.md)，充能球日志边界见[第六阶段记录](../research/2026-11-01-orb-events.md)，战斗间交接及本阶段实测见[第七阶段记录](../research/2026-11-01-combat-handoff.md)。

Mod／MCP `0.45.0`、schema `26` 修正建筑师胜利结算的停止原因，胜利结算就绪后返回 `run_won`，保留剧情死亡的生命变化和原生标题；后续结算翻页仍为 `action_completed`。需更新 DLL／清单和 Python，重启游戏并重连 MCP，见[终章结算](run-ending.md)。
