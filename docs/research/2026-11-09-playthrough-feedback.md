# 静默猎手游玩反馈核验与修复

当前状态：已完成。共 4 项，已完成 4 项；两项反馈缺陷已修复，伤害数字已确认正常，毒／灾厄血条预示已接入并验证。无剩余实施项。

## 基线与证据

核对日期为 2026-11-09，代码基线为 `8fb0bde`；游戏 Linux release `v0.107.1`、构建 `59260271`，RitsuLib `0.6.10` 兼容运行时。上游依据为游戏目录 `data_sts2_linuxbsd_x86_64/sts2.dll` 中的 `NAncientEventLayout`、`NHealthBar`、`PlayCardAction`、`PoisonPower`、`DoomPower`、`Creature` 与 `HauntedShip`。

原局文件响应保存在本地 `.tmp/live/ipc/responses/`；截图位于 `.sts2-agent/screenshots/`。原始请求由 mailbox 消费，以下以响应 ID 和前后快照关联，不补造请求记录。

## 核验与实施要求

- [x] 页面就绪与提示：`9b935e341c6b489ab0bce6b96b55f9d2.json` 中 `ancient.status` 为 `not_ready`、三项祝福均 disabled；下一次 `a020ae9020a24851a9246ec28bc2dd21.json` 恢复 visible 与 `choose_ancient_option`。动作统一由 `AvailableTools` 计算；原生关闭覆盖页会触发 0.5 秒的名称横幅淡入。关闭等待应识别明确的页面未完成状态；精简回执保留已有 `notes.presentation`，说明动作列表也可能尚未齐全。`close_card_view` 的 full/default 以及观察的 actions_only/top_bar 均须覆盖。
- [x] 批量出牌原因：`8226a0657aa54c988600cfc753cc73aa.json` 的第三项 Strike 为 not_played；前态 `bb5be62be6c84e80ad2188bde76e31d2.json` 为 2 能量，前两张 Defend 各耗 1。原生 `PlayCardAction.ExecuteAction` 在入队后再次 `CanPlay`，失败调用 `Cancel`。记录该次检查的公开拒绝文本，供逐张结果使用；其他取消保留实际可确认的通用原因。
- [x] Haunted Ship 的 5 点掉血正常：`e172898928cb4ed4956faea58364eb29.json` 敌人为 8/63，随后 `9b934d14beb742b99de167f9ec24ceae.json` 记录 Neutralize 掉血 3、Strike 掉血 5、死亡及 `combat_won`，场景为 rewards。`Creature.LoseHpInternal` 的 `UnblockedDamage` 为前后生命差，事件 `hp_loss` 沿用该值。本项保留现有行为。
- [x] 血条预示：现有两种观察均未提供绿色／紫色段与致死字体颜色。增加共用 `hp_preview`，记录原生 `NHealthBar` 本次渲染使用的毒伤害与灾厄阈值，以及当前显示的致死类型；毒段按当前剩余生命封顶。缺少对应颜色段时该数值为 null；两段均无显示时整个对象为 null。full 保留 null，default 按通用规则过滤；summary 与对象筛选保留这些信息。数值跟随原生渲染记录，不额外模拟伤害或刷新 UI。

## 验证

实施验证使用独立游戏实例、临时 IPC 与测试存档。需覆盖关闭涅奥牌组后直接选择、精简提示保留、能量／星星不足与其他原生取消、普通／致死／复合毒灾厄、加速毒触发及隐藏显示边界。Python 检查覆盖契约、空值、筛选与坏响应。

交付版本为 Mod `0.83.0`、MCP `0.86.0`、观察 schema `49`。验证结果如下：

| 检查 | 结果与本地证据 |
| --- | --- |
| 修复前的真实游戏回归 | `red-close` 在关闭涅奥牌组后的动作断言失败，`red-energy` 在执行取消的原因断言失败；均位于 `.tmp/2026-11-09-playthrough-feedback/` |
| Mod 构建 | 通过，0 警告、0 错误；引用目标安装的 `sts2.dll` 与匹配 RitsuLib |
| Python 全量检查 | 860 项通过；含精简提示、动作提示合并、血条契约／空值／来源筛选和坏响应拒绝 |
| C# 纯检查 | 全部通过，按架构文档中的项目入口执行 |
| 关闭回归 | `green-close/report.json`：4 个测试局通过，涵盖涅奥、战斗、选牌与战场浏览；涅奥连续开关三次后可直接选择 |
| 未就绪提示 | `close-notes/report.json`：1 个测试局通过；原生部分展示夹具持续期间，full/default 关闭回执和 actions_only/top_bar 观察保留提示，恢复后可直接选择 |
| 批量出牌 | `batch-regression/report.json`：9 个测试局通过，覆盖入队前拒绝、外部限制、能量／星星不足、失效目标、随机消耗、手牌选择、胜利及原生提交拒绝 |
| 血条预示 | `health-previews/report.json`：1 个测试局覆盖 12 种原生显示；逐一核对两个工具的 full/default/summary，验证来源筛选并保存三种颜色截图 |

以上报告路径相对于 `.tmp/2026-11-09-playthrough-feedback/`。血条样例中，20 生命、7 毒与 15 灾厄返回 `{"poison_damage":7,"doom_threshold":15,"lethal":"doom"}`；7 毒配合两次额外触发预示 18 点掉血；30 毒对 20 生命预示 20 点实际可损失生命。无绿色／紫色段时 full 的 hp_preview 为 null，default 省略。

原局结论使用保留的响应及截图，验证使用独立测试局，未重打一整局静默猎手。正式游戏安装与存档未改动；使用新增字段须更新 Mod 并重启游戏及 MCP 服务。多人、第三方改写血条与全部状态组合未穷举。
