# 动作事件第四阶段：最大能量、蜡制遗物与充能球观察

第四阶段已完成：361 项 Python、60 项纯 C# 和最终 DLL 的 7 个中文图形用例全部通过，包含 36 项原生可见性与生命周期检查。已补齐容量／熔化事件、充能球基础观察与两类悬停工具，独立审阅指出的问题已修复并通过原生回归。永久牌面数值、附魔直接数值、充能球专用事件及战斗间交接仍留待后续。

## 范围与基线

代码基线 `45a646e`，延续[覆盖审查](2026-11-01-transition-event-coverage.md)。核对日期为 2026-11-01；Linux 游戏 `v0.107.1`、release `59260271`，RitsuLib `0.6.10` 兼容运行时。实现为 Mod `0.39.0`、MCP `0.37.0`、原始观察 schema `21`。生产流程不改写游戏状态，未更新正式安装。

新增事件字段以[现行事件契约](../development/end-turn.md#事件语义)为准；充能球结构见[基础观察](../development/observation.md#玩法字段)，悬停分工见[战斗对象详情](../development/combatant-inspection.md)及[界面帮助](../development/ui-inspection.md)。新增事件需要同时更新 DLL／清单与 Python，完整重启游戏并重连 MCP。

## 目标版本依据

重新反编译安装目录 `data_sts2_linuxbsd_x86_64/sts2.dll`，证据位于未纳入 Git 的 `.tmp/2026-11-01-resource-capacity/source/`：

| 类型或成员 | 已核实事实 |
| --- | --- |
| `PlayerCombatState.MaxEnergy`、`NEnergyCounter.RefreshLabel` | 容量由 hook 计算，无独立通知；原生计数标签实际显示 `Energy/MaxEnergy` |
| `RelicCmd.Melt`、`Player.MeltRelicInternal` | 仅蜡制遗物可熔化；留在玩家栏位，设置熔化及 Disabled，调用 `AfterRemoved`；不同于真正移除 |
| `RelicModel.UpdateTexture`、`NRelicInventoryHolder.RefreshStatus` | 蜡制 shader 为 `is_wax`，熔化实际显示暗红色；已 Disabled 后熔化可没有新状态通知 |
| `RelicModel.Title`、`LocString.Add(string, LocString)` | 蜡制前缀先把内层名称按当前 UI 语言格式化成字符串，可能导致英文前缀嵌中文名称 |
| `NOrbManager._orbs`、`EvokeOrbAnim` | UI 列表保留激发顺序；已移出列表的球图像仍可淡出，不能枚举所有子节点当作当前槽位 |
| `NOrb.UpdateVisuals/OnFocus` | 普通球平时只显示被动数字，暗球显示两个数字，等离子球不显示数字；悬停使用对应实例 `HoverTips`，空槽使用通用帮助 |
| `OrbCmd` | 增槽、减槽、生成及激发有现成原生流程，可直接用于隔离验证 |
| `GeneticAlgorithm.OnPlay/UpdateBlock` | 出牌后同时增加战斗副本和永久版本自身格挡数值，不触发升级通知；本阶段没有新增此类永久数值日志 |

## 实现与读取边界

最大能量复用纯 C# 可见资源状态机，比较实际分母；没有变化不保留事件位置，隐藏清除基线，恢复不补发。其位置代表采样时刻，不能描述为所有内部容量变化的完整通知日志。

蜡制遗物熔化在原生状态通知及观察采样时检查真实图标，只有已有公开未熔化基线且图标实际变为熔化表现才发布。普通禁用不会生成该事件。顶栏及遗物详情提供可见 `melted`。蜡制名称通过分离的本地化变量重建英语前缀内的基础名，不更改原生标题、缓存或 UI 语言；同一规则用于事件来源、物品日志、顶栏及详情。

充能球读取原生 UI 管理器列表，依次检查空槽外框或非空球命中框、实际球图像、缩放、视口及祖先裁剪。数字只从实际可见标签读取；没有显示的激发数字不从模型补齐。已生成球的原生正文关联到 `inspect_combatants` 的 `player.orb_slots.N`，空槽通用帮助由 `inspect_ui` 合并提供；读取不会调用悬停事件或改变标签。矩形与图像锚点检查仍不能判断任意逐像素遮挡。

## 失败证据与修复

证据根目录 `.tmp/2026-11-01-resource-capacity/`：

- `python-red.log`、`python-expanded-red.log`：旧投影缺少槽位／熔化字段，旧校验拒绝新增事件；新增协议检查随后通过。
- `csharp-red.log`：原可见资源状态机缺少分母采样入口；新增检查验证公开端点、隐藏恢复、不变容量不占缓冲及上限。
- `resources-red-gui/`：旧 DLL 经原生取得、移除及熔化流程，没有最大能量或熔化事件，已有移除事件仍能正确区分。
- `orbs-red-gui/`：旧 DLL 的实际故障机器人对局准备五个槽位，基础观察没有球槽字段。
- `green-gui/`：容量与熔化行为通过；一个检查错误预期普通遗物名称，实际蜡制名称有 `Wax` 前缀。修正夹具预期，没有删除前缀。
- `orbs-green-gui/`：真实 MCP 混合球观察、悬停工具分工、激发、增槽、生成及暗球回合增长通过。
- `orb-mask-red-gui/`：独立审阅指出固定 Bounds 不能证明球图像可见；原生零缩放和只移动图像的两项检查失败，其余隐藏、裁剪、空槽与玻璃球检查通过。修正为同时检查实际球图像几何。
- `final-gui/`：中文运行暴露 `Wax 贤者之石`／`Wax 灯笼` 的混合语言名称，容量及熔化行为通过。核对前缀的嵌套格式化后，重建分离的英语名称变量，并增加名称及原生语言不变检查。

独立只读审阅确认图像几何缺口，未发现其他确认问题；提出的已 Disabled 蜡制遗物无通知重绘路径已补原生检查。审阅未运行图形或访问正式游戏。

## 验证范围

最终 `verified-gui/` 在同一个自有游戏进程中完成 7 局，全部通过，耗时 196.454 秒：容量／熔化的 18 项嵌入检查，真实出牌熔化回执及直接续接，故障机器人的球序／悬停／激发／增槽／生成／暗球回合增长，充能球 18 项可见性检查，以及 TURBO、首次星星和假商人药水入战回归。基础观察覆盖雷、冰、暗、等离子、玻璃五种球，悬停正文及空槽帮助在中文 UI 下仍为英语。无通知重绘检查确认：已 Disabled 的蜡制遗物熔化后，只要图标尚未刷新，就不会根据模型提前发布；原生图标实际重绘后恰好记录一次。

最终 DLL SHA-256 为 `273ad270aea8f7a66b05949f6af189015b01baffca2fe84b6a4acc6b4802f070`，与构建产物和隔离运行时一致。`build-verified.log` 零警告、零错误；`python-final.log` 为 361 项通过，耗时 34.422 秒；`csharp-final.log` 为 60 项通过。所有自有隔离进程已退出。失败目录完整保留，没有在原目录覆盖重跑；本轮未执行整个默认冒烟清单。

真实 MCP 样本保存为 `orbs-observation.json`、`orb-details.json`、`orb-ui.json` 及 `melt-receipt.json`。普通雷球摘要为 `name:Lightning/passive:3/evoke:null`，显式详情才提供激发 8 伤害的原生说明。熔化回执包含一次 `relic_melted`、最大能量 `4→3`，没有 `relic_removed`，可直接接 `end_turn`；后续顶栏和详情仍保留该遗物并显示熔化。

未运行完整自主通关、任意第三方 Mod 组合或正式游戏安装。充能球生成／激发／槽位变化仍没有专门 transition 类型；永久费用、牌面自身增长及附魔直接数值仍待后续阶段。
