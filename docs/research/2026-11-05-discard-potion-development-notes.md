# discard_potion 开发核验记录

> 当前状态：审阅任务共 3 项，已完成 3 项；下述内容保存修复前基线。DISCARD-01 已按确认契约实现、完成独立审查并合入 main，35 类组合场景通过，工具已核销；验证与低优先级遗留见[实施记录](2026-11-05-potion-discard-implementation.md)。用户说明见[审阅与建议](2026-11-05-discard-potion-review.md)。

## 已确认问题与核验边界

审阅基线确认一项能力缺口，审阅提交未修改玩法代码；之后的修复见实施记录。前一轮错误恢复、单槽操作和可见移除事件修复已由独立 discard 调用复验。

| 编号 | 优先级 | 问题与影响 | 证据及处理范围 |
| --- | --- | --- | --- |
| DISCARD-01 | 中；原生操作覆盖 | 选牌期间原生可提交 DiscardPotionGameAction，选择完成后执行；PotionStageUnavailableReason 共用的 CardSelection 检查将其完全拒绝，available_actions 也遗漏该能力 | 前台技能药水 choose_one 实测：菜单饮用禁用、丢弃启用；点击后仍保留原槽，select_card 完成后槽清空并生成 potion_discarded。建议分开使用／丢弃阶段规则，补可用操作、已排队回执、防重复和选择续接；具体契约待定稿，尚未修复 |

| 项目 | 核对结果与状态 |
| --- | --- |
| 错误后的观察前置要求 | 本地参数错误与原生明确未操作拒绝保留已有许可；可直接丢其他药水、结束回合或继续选牌。没有初始读取时仍 observation_required，不凭错误创建许可 |
| 错误准确性 | 空槽、越界、禁止移除、目标槽位不可交互、隐藏、选牌及覆盖页有具体原因。stale_state 清除旧许可；同名替换通过实际测试 |
| 槽位与事件 | 原始槽位稳定，筛选结果不重编号；potion_discarded 只记录实际丢弃的槽位及名称，不生成 potion_used |
| 原生阶段差异 | NPotionPopup 的 discard 按钮没有使用药水的全部阶段检查；ActionQueueSet 在 GatheringPlayerChoice 时等待执行。前台操作证实按钮可达，且丢弃排队等候选择结束，形成 DISCARD-01 的有效证据 |
| 支持范围 | 请求和 available_actions 仍使用共同 PotionStageUnavailableReason，丢弃还要求支持的目标类型；原版已核对目标类型范围，未验证第三方自定义药水。若将来扩展排队丢弃，应先拆分使用／丢弃的阶段规则与等待边界，不直接删除检查 |

现有移除、使用、目标诊断已经分开；需要小范围重构的是仍共用的阶段判断与等待条件。支持 DISCARD-01 时还须核对 transition_details 对 choice_required 可用操作的过滤、GameSession 选择续接许可，以及同槽请求的排队身份；不能仅放开 PotionRequest 的一个分支。

## 基线与原生证据

- 代码 `2a7b9a3`，Mod 0.64.0、MCP 0.66.0、schema 40；当前兼容基线统一见 [README](../../README.md#当前版本与前提)。
- 2026-11-05 核对 Linux 游戏 v0.107.1、release build 59260271；安装目录相对路径 data_sts2_linuxbsd_x86_64/sts2.dll，SHA-256 为 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 使用既有隔离运行时，未重建或安装 Mod。实测 DLL SHA-256 为 7f04d0ee3ba6588e69e250bdeb8445f1f48f44f48470a84015d53dfad6582875。
- RitsuLib 0.6.10，用户提供源码 .tmp/ritsulib-end-turn-review，提交 772f280964f2efc7c7e2f29fc59844e68616dd57；AfterPotionDiscardedLifecyclePatch 仅在原生钩子后发布生命周期通知，没有改用药流程。
- 本轮重新反编译证据位于 .tmp/2026-11-05-discard-potion-review/source/：NPotionPopup._Ready/RefreshButtons/OnDiscardButtonPressed、DiscardPotionGameAction.ExecuteAction/CancelAction、PotionCmd.Discard、ActionQueueSet.GetReadyAction/PauseActionForPlayerChoice、ActionExecutor.ExecuteActions、NPotionContainer、NTopBar。类型名通过程序集列表核对，types.txt 保留。
- PotionModel.Discard 与 Player.DiscardPotionInternal 沿用同一程序集的 .tmp/decompiled/MegaCrit.Sts2.Core.Models.PotionModel.decompiled.cs 及 .tmp/2026-10-30-potions/Player.cs；先清除原槽位，再通知 PotionDiscarded，不移动其他槽位。PotionCmd.Discard 维护原生日志并调用 AfterPotionDiscarded，不执行 OnUse。

## 审阅基线链路

tool_registry 中 discard_potion 使用 POTION_SCHEMA 与通用 default/full，登记 unsubmitted_rejection_unchanged。potion_action_details.potion_arguments 仅接受 potion_slot；结构错误不发往游戏。

GameAdapter.PotionRequest 在交互前核对当前快照、阶段、具体槽位展示、归属、目标类型及 RemovalReason。只有 use 分支核对手动可用性和目标，自动药水、战斗外不可饮用的药水仍能被正常丢弃。开始交互后禁用对应槽位，并提交 DiscardPotionGameAction；没有直接调用模型删除替代原生动作。

PotionJournal 用此前已显示的身份和仍暴露的槽位记录移除，避免要求已删除的图标继续存在；end_turn_details 共用精简回执与事件校验，default 再经过公共空值过滤。药水事件没有需过滤的空字段，所以普通成功的 default/full 格式相同。

## 实测范围

入口为 [discard_potion_review 清单](../../tests/game/data/gui_suite_discard_potion_review.json)，验证器为 [verify_discard_potion_review.py](../../tests/game/verifiers/verify_discard_potion_review.py)。通过真实 stdio MCP 调用；测试扰动与原始状态对照仅使用双重门控的原生测试 IPC。

15 类配置均通过：basic、default、automatic、fruit、blocked、replace、covered、display、skill、noncombat_event、noncombat_rest、noncombat_shop、noncombat_map、noncombat_reward、merchant_inventory。

- basic 验证缺参、布尔、负数、浮点、字符串、null、整数越界、多余 target_id、未知参数及不支持 summary；另验证实际槽位越界、空槽、筛选后的原槽位、连续丢弃和丢空后的可用工具。
- automatic 丢弃瓶中精灵；fruit 丢弃果汁；merchant_inventory 在商品页丢弃恶臭药水；没有用药事件或使用产生的生命、最大生命、金币变化。
- blocked 复验不能移除的具体原因，随后直接 end_turn；replace 复验同名药水对象替换导致 stale_state，接下来 end_turn 为 observation_required，读取后恢复。
- covered 分别确认牌组、弃牌堆和战斗地图的具体拒绝；skill 在真实选牌页拒绝丢弃后，直接 select_card 成功，之后可丢弃。
- display 分别将第 2 槽禁用、禁止悬停、隐藏或移出视口：目标不可交互时拒绝，隐藏无关槽位时第 0 槽仍能丢弃，移出视口的第 2 槽仍按原编号丢弃；扰动在 finally 中恢复。
- noncombat_map 连续丢弃三瓶，中间没有 get_observation 或 inspect_*；noncombat_reward 先确认满栏领取未改变药水，再丢弃血液药水、直接重新领取，事件及最终槽位证明新药进入第 1 槽。
- 成功丢弃逐槽比较原生静态栏位，以及 HP、最大 HP 和金币；所有成功均精确检查一项 potion_discarded，没有 potion_used。

原始证据根目录为 .tmp/2026-11-05-discard-potion-review/。gui-first 的六个用例通过；covered 失败原因是测试误要求调试战斗的强制初始地图可关闭。修正为遵循实际 available_actions 后，在新目录 gui-remaining 复验 covered 并继续；其中七例通过，noncombat_reward 的丢弃、领取及槽位均正确，但测试误要求最后一项领取自动关页后还能 proceed。根据实际 scene 修正清理后，gui-final 两例通过。仅采用 6+7+2 个通过用例，各场景采用一次，两个失败报告均保留；没有以重发动作代替问题调查。

62 份公开返回逐项复制自通过用例的实际结果，参数、来源记录、SHA-256 和套件／用例状态见[来源清单](2026-11-05-discard-potion-examples/manifest.json)。来源套件失败不表示其中独立通过用例被改记为整套通过。

Python 完整回归 663 项通过（python.log，49.790 秒）。仅新增审阅验证器、清单及编排注册，未改 C#、玩法协议或版本，未重新构建或重复 C# 检查。测试脚本后续仅修正上述原生页面收尾假设，相应场景重新执行通过。

## 额外界面探查与未验证范围

native-ui 是单独拥有的隔离实例：真实进入技能药水选牌后，为 xdotool 准备了第 1 槽点击、聚焦及横向坐标偏移探查。游戏截图 1760×990，查询到的窗口几何为 1920×990。用户确认没有处理 xdotool 请求，且将游戏窗口置于后台；工具返回本身不能证明窗口实际收到鼠标事件。因此这些截图仅证明当时的选牌画面，没有形成有效的原生点击验证，菜单未显示不能用来支持阶段限制。没有把这项探查计入 15 类通过数，也没有据此修改规则。启动、截图辅助脚本、ready.json、mcp.json 和 closed.json 均保留在任务目录，预定操作限定到自有 PID 286254 的窗口 73400324；未尝试点击丢弃按钮。

用户随后明确允许前台测试。新证据全部保存在 native-ui-foreground，不覆盖旧探查：自有 PID 291110、窗口 58720260。先用 import -window 保存实际窗口画面，再通过悬停提示校准桌面缩放；window-potion-menu.png 清楚显示选牌与原生药水菜单并存，饮用禁用、丢弃启用。点击丢弃后 window-after-discard.png 显示药水置灰；before-native-discard.json、after-native-discard.json 都保持选择及第 1 槽格挡药水。正常 select_card 选择 id 8，finish-selection.json 的 transition 依次包含 card_added、potion_discarded(slot_index:1)，after-selection.json 显示选择消失且该槽为空。verification.json 对这些状态及事件作了独立断言，证明排队后执行而非仅有可点击外观。

该补测使用原生鼠标输入与文件 IPC，不冒充额外的 stdio MCP 用例；工具对应拒绝来自已保存的 skill-05-full-error.json。15 类工具测试仍验证当前行为，而非 DISCARD-01 已修复。随后在牌组页的两次药水点击未打开菜单，不作该页支持原生丢弃的肯定结论；不从 choose_one 推广到所有覆盖页或选择类型。

真实多人、第三方药水、自然取消或超时、提交后被其他流程替换、对局死亡／结束、父事件忙碌、模态和敌人回合均未新增独立丢弃实测；相关路径按共用门控和原生源码核对。已开始操作、结果不明或过期仍不能套用“明确未操作”的恢复保证。上述未实测范围不表示已发现缺陷。

审阅没有操作正式对局、存档和正式 Mod 安装，不增加用户 TODO；后续实现的交付与核销见实施记录。
