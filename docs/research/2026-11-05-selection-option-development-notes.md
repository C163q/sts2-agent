# selection_option 开发核验记录

> 当前状态：现状核验完成，待设计确认。25 组不同游戏情形、42 项相关 Python 检查通过，81 份 full 样例已提取；两项错误处理问题未修复，工具未核销。仅添加审阅资料、验证代码和已核实的文档更正。用户说明见[审阅](2026-11-05-selection-option-review.md)。

## 已定位问题

| 编号 | 优先级 | 代码依据与影响 | 状态 |
| --- | --- | --- | --- |
| OPTION-01 | 中；错误恢复 | `GameAdapter.SelectionRequest` 的按钮前置拒绝使用普通 `FileMailbox.Error`，`selection_option` 未登记 `unsubmitted_rejection_unchanged`；`GameSession` 因没有明确未交互保证而清除已有许可 | 已复现，待确认修复范围。不得把 `UiChanged` 后的失败标为未交互 |
| OPTION-02 | 中；错误原因 | 前置拒绝没有 `publicMessage:true`，公共错误输出替换具体原因；不存在及禁用按钮还合并在同一检查中 | 已复现，待定稿。使用固定公开诊断，不透传任意异常字符串 |

## 核对基线

- 项目提交 `33c4c21`；Mod `0.66.0`、MCP `0.68.0`、schema 40；现行基线统一见[README](../../README.md#当前版本与前提)。
- Linux 游戏 v0.107.1、release build 59260271，安装目录相对路径 `data_sts2_linuxbsd_x86_64/sts2.dll`；本轮重算 SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- RitsuLib 0.6.10；按钮沿用游戏 `NClickableControl.ForceClick`，不新增库 API。
- 复用已准备的隔离测试运行时；构建与运行时 DLL 均为 `239a0fd5c1c244044dc1ec308951aa339c0efb051b257e5d5b6e693f78faeacd`。没有重新编译或安装正式 Mod。
- 原生证据：`.tmp/2026-11-05-selection-option-review/source/`。奖励替代生成、奖励主体、捕梦网、佩尔之翼、浮木、变牌与确认按钮重新定向反编译；其余选择页从同一程序集哈希的前项证据复制。逐文件哈希见 `source/manifest.json`。

## 调用链与原生依据

| 范围 | 已核对行为 |
| --- | --- |
| 参数与公开描述 | `output/selection_details.py`、`tool_registry.py`：准确的 offered ID，非空白字符串，128 字符上限，公共 default/full；本地参数错误在发送前返回，不清除已有许可 |
| 选择与按钮读取 | `Actions/CardSelection.cs`：当前页 `Options()` 的原生按钮和启用状态，与基础观察、详情及 available_actions 共用；按钮 ID 是适配标识，显示名称是独立 text |
| 交互前复核 | `GameAdapter.Selection.cs`：本地支持、同一快照、选择可见以及实际存在且启用的按钮；之后同步 `UiChanged` 和 `ForceClick`，这两者之间不等待帧 |
| 原生点击 | `NClickableControl.ForceClick` 调用 OnRelease 并发射 Released，跳过自身鼠标／焦点／暂停检查。因此适配层的可见、启用、覆盖与状态复核不能省略 |
| 原生确认显示 | `NConfirmButton.OnDisable` 把按钮移至隐藏位置，禁用点击和热键；`NSimpleCardSelectScreen` 在手动确认且达到 MinSelect 后才 Enable。稳定未满足条件时 options 为空可以是正确读取 |
| 预览返回 | 普通移除、升级、附魔、变牌页的 CancelSelection 清空原已选集合并返回原列表。现有 SelectionInputJournal 仅包裹 cancel_preview，按实际取消记录；整包分支被明确排除 |
| 确认与关闭 | 各页原生任务完成，实际后续效果由调用方继续；手牌用当前选择集合完成任务；结果页仅关闭；不把生命周期清理转成取消事件 |
| 动作等待与投影 | `ActionObservation` 与共享事件范围继续等待边界；`action_output` 投影为 actions_only 并保留 transition。是否续接由完整已验证状态决定，不以紧凑字段猜测 |

按钮前置诊断宜与 `SelectionAvailability` 共享基础状态判断，保留 card 与 option 各自的合法性分支。当前适配函数同时容纳查看、切换视图、点击卡牌和点击按钮；此次只抽取涉及按钮的判断与固定原因，不重复大范围迁移。

## 奖励按钮名称与旧注释

`CardRewardAlternative.Generate` 实际先按 CanSkip 添加 Skip，再按 CanReroll 添加 REROLL，最后由模型 Hook 修改。`PaelsWing.TryModifyCardRewardAlternatives` 添加 SACRIFICE；`CardReward` 按 AfterSelected 判断是结束并完成奖励、结束但不完成，还是继续生成候选。基础观察的 alternative:N 使用 `_extraOptions` 中的位置，`text` 从该条 Title 的英语本地化取得；不能把某个编号固定绑定到献祭。

`CardRewardAlternative` 的类型注释仍举出 “Heal +2 (for Dream Catcher)”，但重新反编译的 `DreamCatcher` 只有休息奖励和额外休息说明逻辑，未实现卡牌奖励替代按钮的 Hook。已核实的该遗物行为是休息后提供卡牌奖励；该注释不足以支持“当前有治疗按钮”的能力描述。

已修正持续维护的 `card-selection.md` 和旧设计中“已核实”列表的相同误述，保留更正依据链接。没有把这项说明差异算作工具行为修复，也不据此断言任意第三方模型都不能添加其他按钮。

## 验证与边界

验证日志、完整响应、失败尝试和自有进程记录保存在 `.tmp/2026-11-05-selection-option-review/`。专项清单为 [selection_option_review](../../tests/game/data/gui_suite_selection_option_review.json)，验证器为 [verify_selection_option_review.py](../../tests/game/verifiers/verify_selection_option_review.py)。

| 执行证据 | 结果与范围 |
| --- | --- |
| `python-final.log` | gui_suite、selection、session_policy 共 42 项通过；清单加载及实际样例的逐项验证另见 `verification.json` |
| `gui/` | 无选择与错误 ID 两组通过；第三组因脚本误以为禁用确认按钮仍会列出而失败。20 次 MCP，50.465 秒；失败证据保留 |
| `gui-remaining/` | 条件不足、战场视图、覆盖页和可跳过三选一四组通过；卡牌奖励跳过的验证器通过，但局间清理超时，整个用例不计通过。33 次 MCP，74.139 秒 |
| `gui-rest/` | 修正奖励列表退出后，从该用例继续剩余 18 组，全部通过；182 次 MCP，380.594 秒 |
| `gui-shop/` | 真实商店删牌的返回预览、最终确认和实际扣款／移除通过；12 次 MCP，26.928 秒 |

累计 25 组不同情形通过，成功场景共 241 次 MCP；包括失败尝试共 247 次。通过表示准确记录当前行为，包括已知缺陷，不代表 OPTION-01/02 已修复。所有组使用同一份已准备 DLL，未重新构建；没有以旧版本样本替换当前采集。

失败原因均已追溯：确认按钮未满足条件时由原生移动到隐藏位置，原脚本的“必然列出禁用 confirm”假设错误，改为检查不存在启用 confirm；奖励候选 skip 后仍等待奖励集完成，清理等待的夹具任务不会自行结束，脚本记录结果后用原生 proceed 退出奖励列表。两项都只更正验证流程，不改变生产等待策略，不重试已成功的玩法动作。样例导出首次在套件尚未结束时缺少最终 DLL 哈希而停止，改为只导出已完成报告后继续，未修改游戏记录。

原生错误响应同时记录 `ui_interaction_started:false` 和 `action_submission_observed:false`，但没有动作专用的明确未交互保证；公共返回为笼统 illegal_action，直接重试为 observation_required。没有初始许可时的拒绝和空白、数字、null、超长 option_id 的本地拒绝属于正确行为，单独验证，不列为恢复问题。

[81 份样例](2026-11-05-selection-option-examples/README.md)包含 51 份按钮调用与 30 份详情上下文。每份与来源记录逐字结构比对，manifest 保存实际发送的 full 参数与文件哈希；原生快照、执行证据、测试检查不进入公共样例。奖励替代验证器的原始记录未写公共 preset，但其 `full_output_arguments` 实际发送 full，manifest 记录实际参数。

`verify_delivery.py` 核对 25 项清单与通过证据、81 份样例及请求参数、260 个相对链接、未变的 DLL 哈希和仍为 16/44 的核销数。四个自有游戏 PID 均已退出，结果记录在 `processes.json`。`git diff --check` 通过；未运行全量 Python 或重新编译 C#，因为只改核验设施和说明，玩法代码与测试 DLL 未变。

普通 deck 和 grid_manual 夹具只启动选择任务，不执行所选择牌的移除或消耗，确认后的空事件不构成遗漏；真实商店删牌另有样例，记录 gold_changed 和 card_removed。整包选择／返回使用空事件，确认后才返回 card_added；没有将整包误报为逐张 card_selected。

可变数量牌组移除／附魔的中间确认、变牌的 RequireManualConfirmation 分支、不可跳过的三选一、未支持页面和非单人拒绝为源码核对范围，未新增各自的游戏调用样例。控制器、任意第三方页面和真实跨局竞争未实测。没有扩大用户 TODO，也未对尚未审阅的 set_selection_view 作全面修复。
