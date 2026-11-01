# 动作事件第五阶段：永久牌面直接变化

第五阶段已完成：364 项 Python、60 项纯 C# 和最终 DLL 的 7 个中文图形用例全部通过，包含 23 项原生边界与生命周期检查。遗传算法永久成长、基础能量费用及附魔直接数值已接入；独立审阅指出的字段边界及补测发现的临时升级名称问题均已修复并回归。充能球专用事件、更多直接存储字段和战斗间交接仍留待后续。

## 范围与基线

代码基线 `458283a`，延续[覆盖审查](2026-11-01-transition-event-coverage.md)。核对日期为 2026-11-01；Linux 游戏 `v0.107.1`、release `59260271`，RitsuLib `0.6.10` 兼容运行时。实现版本 Mod `0.40.0`、MCP `0.38.0`、原始观察 schema `22`。未更改正式安装、正式存档或其他 agent 的游戏进程。

新增 `card_stats_changed`、`card_energy_cost_changed`，复用 `card_enchantment_changed` 表达附着实例数量／基础变量直接变化。只提供公开卡牌身份与永久范围，不自动返回新旧数值、内部变量名或未展开正文。现行字段和合并规则以[事件契约](../development/end-turn.md#事件语义)为准；需同时更新 DLL／清单和 Python，完整重启游戏并重连 MCP。

## 目标版本依据

重新反编译安装目录 `data_sts2_linuxbsd_x86_64/sts2.dll`；证据位于未纳入 Git 的 `.tmp/2026-11-01-permanent-card-events/source/`：

| 类型或成员 | 已核实行为 |
| --- | --- |
| `GeneticAlgorithm.OnPlay/BuffFromPlay/CurrentBlock` | 原生出牌后分别增长战斗副本及 `DeckVersion` 的永久格挡；通过基础变量赋值实现，不触发升级通知 |
| `DynamicVar.BaseValue/PreviewValue/EnchantedValue` | 基础值与两类预览／附魔结果不同，只有基础值直接修改属于此采集入口；`_owner` 可定位卡牌或附魔所属实例 |
| `CardEnergyCost.SetCustomBaseCost/GetWithModifiers` | 自定义基础费用有原生入口；`CostModifiers.None` 排除临时及全局费用修正 |
| `EnchantmentModel.Amount/HasCard/Card` | 已附着实例数量可直接改变，没有对应数量通知；初次绑定前的数量设置不能当作额外变化 |
| `CardModel.UpgradeInternal/DowngradeInternal`、`EnchantmentModel.ModifyCard` | 升级、降级和附魔重算会修改基础变量，需要按卡牌抑制低层重复，保留已有高层事件 |
| `CardModel.BaseStarCost/UpgradeStarCostBy` | 基础星星费用的已核对修改流程属于升级，已有升级事件表达；没有本轮需另接入的独立公开基础费用入口 |
| `Player.PopulateCombatState` | 通过原生 `CloneCard` 建立战斗副本并设置 `DeckVersion`，身份关联不能按名称匹配 |
| `NCard.UpdateVisuals` | 实际卡面更新包含名称、费用、附魔与正文；显式详情／牌组查看继续沿用现有流程 |

## 实现与边界

`PermanentCardCapture` 在主线程且动作记录器存在时捕获已核对入口的实际数值改变；生产代码不改写值、刷新 UI 或调用额外游戏动作。`RunInventoryJournal` 再核对本地永久牌组成员身份，复用名称缓存、延后公开位置和共享缓冲。同张永久牌同类直接变化在单动作合并一次，保持首次采集位置；这是类别日志，不是逐值差量或变化次数日志。

升级／降级和附魔附加／清除／重算使用按卡牌的同步嵌套计数抑制重复，并在 Harmony finalizer 中释放；同一回调对另一张永久牌的实际修改不受抑制。战斗副本、临时费用、脱离牌组的克隆及升级预览不生成永久直接变化事件。附魔直接数量与附魔自身基础变量均使用附魔变化类别；本轮没有把不可叠加的 Sharp 当作原生叠加玩法。

可见战斗副本只在 `DeckVersion` 和模型身份均匹配时提供永久原牌的基础名称，不带入战斗临时升级后缀，也不覆盖已经直接展示过的永久原牌名称。未知身份先保留位置，实际预览后才发布；隐藏取消，恢复不补发。永久原牌与战斗副本是不同实例，事件 `pile:deck` 的 ID 不保证等于手牌 ID，不能把它直接用于出牌；牌组页使用独立的浏览 ID。

Python 对三种身份型变化事件精确限制 `sequence/type/card/pile`，不能借通用事件 schema 中的 `before/after/name/source` 等字段传出额外信息。动作许可与错误恢复仍沿用现有规则，不增加每步观察或自动重试。

## RED、审阅与修复

证据根目录 `.tmp/2026-11-01-permanent-card-events/`：

- `python-red.log`：旧协议拒绝两种新类型；新增类型、永久范围及公开身份校验随后通过。
- `genetic-red-gui/`：旧 DLL 真实打出遗传算法，只返回耗能、出牌、获得 1 格挡和消耗，没有永久成长事件。
- `green-gui/`：遗传算法、基础能量费用及附魔数量的三条真实 MCP 用例通过。遗传算法使用正常出牌；另外两项使用测试夹具回调调用原生修改入口，不声称存在对应天然卡牌玩法。回执后直接 `end_turn`，再打开永久牌组读回遗传算法格挡 4 和修改后的基础费用。
- `checks-gui/`：初轮 20 项原生检查通过，覆盖去重、未变值、临时变化、升级预览、升级／降级、附魔数量、未知身份、延后公开位置、隐藏取消、异常释放和共享上限。
- `python-fields-red.log`：独立只读审阅发现身份事件仍可夹带通用 schema 已声明的数值／变量名等字段。18 个子用例均失败；精确字段集校验后 `python-fields-green.log` 通过。
- `final-gui/`：第一次最终候选的 7 个中文图形用例通过，包含新增的另一张牌不被抑制及 Spiral 附魔基础变量检查；这不是下述名称修复后的最终 DLL 证据。
- `copy-name-red-gui/`：补充检查确认，临时升级战斗副本后，永久原牌事件错误显示 `Genetic Algorithm+`，但永久原牌并未升级；23 项中只有该项失败。修改映射为同模型的基础名称，保留直接公开的原牌名称。

独立审阅确认协议字段边界问题，未发现其他确认的采集身份泄露或异常抑制残留；提出的附魔基础变量检查已补充。审阅没有运行游戏、测试或 IPC。第三方 Mod 的可叠加附魔组合没有实测；不据此宣称全部附魔调用分支已覆盖。

## 最终验证与剩余范围

`verified-gui/` 在同一个自有游戏进程中完成 7 局，全部通过，耗时 161.986 秒：遗传算法、永久基础费用、附魔数量、23 项原生检查，以及锻造升级、事件附魔和武装临时升级回归。原生检查包含 Spiral 附魔基础变量、同一升级回调对另一张永久牌的修改、未知身份延后公开、隐藏取消、异常释放及缓冲上限；临时升级的战斗副本不再把“+”继承给永久原牌。

最终 DLL SHA-256 为 `a8862e47c5b39a48b3bb8216e4f1c90990cb1a49e9230265185d6888cfcc422c`，与构建产物和隔离运行时一致。`build-verified.log` 零警告、零错误；`python-final.log` 为 364 项通过，耗时 33.109 秒；`csharp-final.log` 为 60 项通过。所有自有隔离进程已退出；失败目录保留，未在原目录覆盖重跑。本轮未执行整个默认冒烟清单、完整自主通关、任意第三方 Mod 组合或正式安装。

实际 MCP 回执保存为 `genetic-receipt.json`：永久成长事件为 `sequence:4/type:card_stats_changed/card:{id:9,name:Genetic Algorithm}/pile:deck`，没有新旧数字或正文；本次出牌和消耗使用战斗副本 `id:7`。同一连接可直接结束回合，再显式打开永久牌组读到成长后的格挡 4，样本为 `grown-deck.json`。

此阶段覆盖已核对的基础变量、基础能量费用和附着附魔修改入口，不能据此承诺任意直接存储字段、反射写入或其他 Mod 自定义数值均会产生事件。充能球专用生成／激发／槽位日志，以及已有战斗到下一场战斗的统一采集交接仍留待后续；`complete:true` 仍不证明覆盖全部效果。
