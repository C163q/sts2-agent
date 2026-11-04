# select_card 开发核验记录

> 当前状态：场景核验完成，24 类组合场景、58 项相关 Python 检查通过，91 份公共返回已归档。两项错误处理问题及选中反馈缺口共三项待处理，事件方案待确认；工具行为未改，未核销。用户说明见[审阅与建议](2026-11-05-select-card-review.md)。

## 优先问题

| 编号 | 优先级 | 原因与影响 | 状态 |
| --- | --- | --- | --- |
| SELECT-01 | 中；错误恢复 | `SelectionRequest` 的点击前拒绝使用普通 `FileMailbox.Error`，没有 `ui_unchanged:true`。`GameSession` 对动作仅在明确未提交且 UI 未变的证据下保留旧许可，因此无效 ID 等无交互拒绝也清掉许可 | 已复现，待确认修复。不能给整个异常捕获统一加未交互保证，因为 `SelectionActions.Click` 可能已经滚动并等待帧 |
| SELECT-02 | 中；错误原因 | 没有选择、覆盖及候选／按钮不可用的拒绝没有 `publicMessage:true`，具体内部原因被公共输出的统一提示替换；候选检查本身也把多种情况合并 | 已复现，待确认修复。公开固定且准确的前置原因，不公开任意异常 Message |
| SELECT-03 | 中；UI 反馈 | `action_output` 将 selection 投影为 type/status；选中／取消没有日志来源，完整状态中的 selected_ids 也不随回执公开。现有 grid、hand、hand_upgrade 的连续选中和取消均返回空 events | 已有实测证据；候选方案为新增 card_selected/card_deselected，待确认，不改动历史样例 |

## 核对基线

- 项目提交 `7237b78`；Mod `0.65.1`、MCP `0.67.1`、schema 40；现行基线见 [README](../../README.md#当前版本与前提)。本项只添加审阅和验证资料，不改版本或玩法代码。
- Linux 游戏 v0.107.1、release build 59260271；安装目录相对路径 `data_sts2_linuxbsd_x86_64/sts2.dll`，重新计算 SHA-256：`d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- RitsuLib 0.6.10；本项使用游戏原生持牌器信号，不新增该库 API 调用。
- 复用已准备的只读隔离运行时；构建目录与运行时 DLL SHA-256 均为 `db6d8a1b47521ffb2955ca94138abf12a58b2f928c352cb08fa5b869087a462f`，未重新构建、未正式安装。
- 原生证据在 `.tmp/2026-11-05-select-card-review/source/`：基础网格、小型三选一、普通网格、战斗牌堆、手牌、持牌器及选择命令重新反编译；牌组、升级、附魔、奖励、卡包和结果页复用同一程序集哈希下的已反编译文件，来源为 `.tmp/2026-11-05-inspect-selection-review/source/`。逐文件哈希见 `source/manifest.json`。

## 调用链与原生依据

| 范围 | 证据与结论 |
| --- | --- |
| 参数 | `tool_registry.py` 的 `select_card` 使用公共 default/full，`selection_details.selection_arguments` 校验单个非负整数，额外字段、布尔值等本地拒绝 |
| 观察许可 | `GameSession.execute` 在提交前取走许可；明确前置拒绝须有 `UNSUBMITTED_UNCHANGED` 才能恢复；成功按完整校验后的实际边界续接，不以紧凑输出推断 |
| 前置检查 | `Adapter/GameAdapter.Selection.cs` 检查本地支持、同一快照、选择可见及候选可选；调用 `UiChanged` 之后才进入定位／点击 |
| 候选定位 | `Actions/SelectionActions.cs` 保存页面实例、候选、已选、数量和确认规则，按原生网格行定位，等待虚拟持牌器分配，每帧重新核对后发送 `NCardHolder.Pressed` |
| 原生网格 | `NCardGridSelectionScreen` 将 HolderPressed 转给具体页面；`NSimpleCardSelectScreen` 和 `NCombatPileCardSelectScreen` 按数量及 RequireManualConfirmation 选择／取消或完成 |
| 三选一与奖励 | `NChooseACardSelectionScreen.SelectHolder` 完成原生选择任务，有短暂开场防误触；`NCardRewardSelectionScreen.SelectCard` 提交实际奖励候选的索引 |
| 手牌 | `NPlayerHand.OnHolderPressed` 根据 SimpleSelect／UpgradeSelect 调用原生操作；取消已选手牌由原生已选区／预览信号处理，不直接改列表 |
| 确认预览 | 原生牌组移除、升级、附魔达到对应数量后打开预览；`CardSelection.InPreview` 禁止再选候选，按钮由 selection_option 负责 |
| 完成边界与事件 | `ActionObservation`、`CombatJournalScope`、`NonCombatBoundary` 共同等待 UI／游戏动作稳定；同一次动作的共用资源／物品／战斗日志负责实际变化，单纯 UI 选中不伪造事件 |
| 公开回执 | 完整原生结果先校验及处理许可，再由 `action_output` 投影成 actions_only 加 transition；`preset:full` 不改变这一职责 |

## 验证与范围

原始证据根目录：`.tmp/2026-11-05-select-card-review/`。GUI 使用真实 stdio MCP、独立进程、IPC 和存档，共享运行时只读；不操作正式对局。

十二种选择类型均已核对。额外覆盖无初始许可、无选择、无效 ID、覆盖、四十张候选滚动、连续同外观选择、滚动期间选择变化、选择后胜败及战斗进入；头槌通过真实卡牌流程验证选择后的 `discard -> draw` 移动，不返回位置。普通 combat_pile 和 grid_scroll 夹具仅等待选择命令，没有后续执行牌面效果，不能用其空事件证明实际移动日志覆盖。

首次 Python 命令误用了不存在的 `test_game_session` 模块，46 项实际检查通过、一个模块导入错误；原日志 `python.log` 保留。这是检查命令错误，已改为仓库实际的 `test_session_policy`；不列为工具故障。

| 证据 | 结果与范围 |
| --- | --- |
| `python-final.log` | selection、selection_presets、selection_upgrades、gui_suite、session_policy 共 58 项通过 |
| `gui-0/` | 11 类通过，65 次 MCP 调用；197.759 秒 |
| `gui-1/` | 前四类：火堆、多张升级、单张及多张附魔通过。第五类变牌因脚本错误假设失败，原证据保留；全组 49 次调用、115.353 秒，不将整个组计为通过 |
| `gui-1-corrected/` | 修正单张变牌已进入预览、不能再点牌取消的假设；仅继续原组剩余七类，全部通过，42 次调用、148.723 秒 |
| `gui-combat-pile/` | 战斗牌堆实际选中及完成边界通过，4 次调用、19.287 秒 |
| `gui-headbutt/` | 真实头槌选牌和有方向的移动事件通过，12 次调用、28.012 秒 |

合计 24 个不同组合场景通过，对应成功场景 166 次 MCP 调用；包含脚本失败尝试共 172 次。通过表示已准确记录包括已知缺陷在内的当前行为，不表示 SELECT-01/02 已修复。五个自有游戏进程均已退出，PID 与检查结果保存在 `processes.json`。

[91 份 full 样例](2026-11-05-select-card-examples/README.md)逐份从通过场景的原始公共结果提取；`manifest.json` 记录精确参数、证据位置、记录序号及文件哈希。没有将内部快照、内部检查或测试事件伪装成公开返回。火堆示例在用户报告中的 JSON 与对应样本一致。

交付检查 `verify_delivery.py` 验证 91 份样例与原始记录完全一致、24 例套件与通过证据逐项对应、227 个相对文档链接存在、44 项工具中仍为 15 项核销，以及 DLL 哈希未变；结果保存在 `verification.json`。选中反馈方案补充后重新执行此资料检查及 `git diff --check`，未重复运行玩法测试。

## 复现与修复范围

- 无效 ID 的拒绝前后完整原生快照相同，公开拒绝却要求 `get_observation`，下一次有效选牌得到 `observation_required`。未选择、卡包、结果页和确认预览也分别复现；原生错误附 `ui_interaction_started:false`、`action_submission_observed:false`，但没有 `ui_unchanged`。
- 本地布尔 ID 被 `invalid_request` 拒绝后可直接结束回合；没有初始许可时直接选牌被正确拒绝。不能把这两种正确行为当作 SELECT-01。
- 具体错误在 C# 拒绝点已经确定，Python 只公开显式 `public_message`，因此固定前置原因未到达 LLM。修改公共泛化文案不能恢复各分支差异。
- 建议把候选动作前置诊断独立为小入口，沿用共用明确未交互协议；在当前快照有效、尚未定位／点击时才能保证 UI 未变。状态过期、滚动后变化和任意异常仍清除许可。`SelectionActions.Click` 的异常不得整段标记为未交互，也不得直接公开任意异常字符串。
- 仅审阅 `select_card`；涉及 `selection_option` 的调用用于验证预览边界、有效动作被错误阻断和后续实际事件，不代替该工具未来的完整审阅。

未实测控制器交互、第三方未支持页面和真实跨局竞争；滚动竞争使用现有双重门控的原生测试检查，验证有外部选择后停止第二次点击，不把该内部检查作为公开 MCP 错误样本。没有重新编译或正式安装 Mod，没有扩大用户 TODO 范围。

## 选中反馈的补充核对

现有 `gui-0/grid`、`gui-0/hand`、`gui-0/hand_upgrade` 已验证 native_action_state 的 selected_ids 在选中和取消时确实变化，而公开回执 events 为空；不需要通过新的测试改变状态才能确认缺口。原生证据沿用上文相同程序集：`NSimpleCardSelectScreen.OnCardClicked` 先更新选中集合，达到数量时可能立即 `CompleteSelection`；`NDeckUpgradeSelectScreen.OnCardClicked` 可能立即打开预览；`NPlayerHand.SelectCardInSimpleMode/SelectCardInUpgradeMode` 还会先取消旧牌再加入新牌。

候选实现应独立负责同一原生选择实例内的真实选中／取消记录，与现有有界事件缓冲及公开卡牌身份读取协作。不能仅用最终 `CardSelection.Current` 的差集生成事件：自动提交会移除原页面，连续选择可能复用同一批牌，手牌替换也会一次改变两个项目。采集点及 UI 可见发布时机仍须在实施时核对；记录原生实际接受的变化，不记录预览克隆、拒绝请求或页面生命周期清理。

待确认的公开格式与边界集中在[用户说明的设计范围](2026-11-05-select-card-review.md#建议的设计范围)，不在此重复定义。这里只补充设计调研，尚未新增日志、测试断言或修改当前接口；既有 24 例／58 项验证及 91 份样例仍对应 `7237b78` 的原始行为。
