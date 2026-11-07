# inspect_ancient 开发核验依据

> 当前状态：审阅完成，待确认修复与参数设计；未修改产品代码或测试代码。用户决策内容见[核验与建议](2026-11-07-inspect-ancient-review.md)。

## 基线与证据

- 项目831975d，核对日期2026-11-07；Mod0.77.2、MCP0.79.2、schema45。
- Linux游戏v0.107.1/release59260271，RitsuLib0.6.10、Godot4.5.1。
- 游戏程序集相对路径data_sts2_linuxbsd_x86_64/sts2.dll，重新计算SHA-256为d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。
- 编译产物及隔离运行时DLL均为b5096c3ebd44c7f814aeac561c222327ba742e6ec6706e9a0d4312fb9eda41ad；没有重建、更新版本或正式安装Mod。
- 证据根为`.tmp/2026-11-07-inspect-ancient-review/`，含三个独立实例的原始请求／响应、日志、截图、脚本及报告；不纳入Git。
- 原生源码使用`.tmp/2026-10-31-ancients/source/`缓存的AncientEventModel、EventOption、NAncientEventLayout、NAncientDialogueLine、NAncientDialogueHitbox、NEventOptionButton、NClickableControl及各先古／遗物类型。初始来源和适用程序集见[先古之民调研](2026-10-31-ancients.md)。

## 问题依据

| 编号 | 优先级 | 依据 |
| --- | --- | --- |
| ANCIENT-INSPECT-01 | 中 | [AncientRequest](../../src/Sts2Agent/Adapter/GameAdapter.Ancient.cs)将无上下文、覆盖和非单人合并为FileMailbox.Error；没有public_message，公开错误被统一替换。五类覆盖／误用实际复现。 |
| ANCIENT-INSPECT-02 | 中 | [inspect_ancient_details](../../src/sts2_mcp/output/ancient_details.py)只检查scene和ancient结构，通用scene_context仅校验screen字段类型／枚举。实际原始成功包只改screen为covered/map、covered/deck、visible/selection、not_ready，四种均通过decode_success。正常原生分支会拒绝覆盖页，尚未发现自然流程产出这些矛盾包。 |
| ANCIENT-INSPECT-03 | 中 | Vakuu.Pool2为DistinguishedCape调用ThatDecreasesMaxHp(9m)；EventOption将WillKillPlayer设为MaxHp<=9；NEventOptionButton使用同一判断显示致死红框。AncientInspection.Read及ANCIENT_OPTION没有lethal_warning，基础观察与详情均丢失该UI信息。 |
| ANCIENT-INSPECT-04 | 中；读取边界 | [AncientInspection](../../src/Sts2Agent/Observation/AncientInspection.cs)的Shown、Continue及文字读取使用OnScreen／Text；Read(full:true)直接枚举模型帮助，没有原生悬停可用判断。NClickableControl.RefreshFocus和NEventOptionButton.OnFocus实际受启用、焦点及IsLocked等条件限制。未做异常离屏／裁剪／禁用探针，正常GUI没有证实内容泄露。 |

建议先集中InspectionUnavailableReason与可读／可悬停条件。不要将Ready直接用于详情拒绝：读取已经显示的内容可以早于允许操作。读取保留已揭示、真实可见的节点，取消视口矩形条件；仍须区分隐藏、透明、真实裁剪及尚未揭示的对话。点击合法性属于独立动作检查，不能随读取放宽。

原生NAncientDialogueLine._Ready预先填充所有台词但将Modulate设为透明；SetDialogueLineAndAnimate按进度揭示当前行，已显示旧行降到0.25透明度，并允许悬停回看。不得用“全部节点已创建”替代已经揭示的判断。

致死警告应复用目标版本现有WillKillPlayer回调，不从效果文本或遗物名称推算。建议full/default保留false，summary省略false，与普通事件规则一致；基础观察同步静态格式。

## 正常链路与会话恢复

工具注册为effect:read、无需许可、成功刷新许可，不返回transition。AncientRequest的inspect分支绕过expected_state校验及动作Ready门槛，要求Current、Exposed和Singleplayer，调用InspectionSuccess绑定同次快照上下文。

Current绑定实际事件模型和NAncientEventLayout；Exposed排除地图、覆盖层、牌组、模态框及场景过渡。Read保留已显示内容，Ready另看事件／领取任务、预览、资源动画、目标选择、动作队列、正文与名称横幅补间。选项enabled还要求无继续对话和按钮Clickable。入场或返回浏览页时Read成功但enabled:false是允许的读取中间态。

EventOption.FromRelic使用遗物标题／DynamicEventDescription及HoverTipsExcludingRelic；原生按钮OnFocus使用Option.HoverTips。当前EnglishRelicText.ExtraTips为TouchOfOrobas、ArchaicTooth、DustyTome重建已披露的英文引用，其余采用HoverTipsExcludingRelic。GUI确认当前角色的BurningBlood／BlackBlood与Bash／Break，无随机领取结果预读。

[GameSession](../../src/sts2_mcp/game_session.py)已保留确定性read拒绝之前的许可；本工具不需要动作类的unsubmitted_rejection_unchanged注册。实测无先古房间的illegal_action后可直接end_turn，地图／牌组覆盖拒绝后可直接关闭对应页面；恢复字段为choose_legal_action。空会话成功详情后，在enabled:true时可直接choose_ancient_option。

本项不修改choose_ancient_option或advance_dialogue的动作错误恢复；这两个工具仍在清单后续范围。

## 文档核对

[先古指南](../development/ancients.md)原将“成功详情后可直接选择”写成无条件结论，实际过渡中也可读取成功，选项仍为false。已明确须按当前enabled选择，并补充同次scene/screen、full/default和确定性读取拒绝恢复的现状说明。产品规则未修改；差异记录另存`.tmp/2026-11-07-inspect-ancient-documentation-report.md`。

## 验证结果与限制

Python首次命令误列两个不存在的测试模块：先古12项通过，但整条命令因两项导入错误失败，原python.log保留。改为实际存在的test_ancients、test_inspection_context、test_inspection_errors后，31项通过，0.773秒，python-fixed.log。没有运行全套Python、C#或构建。

GUI使用真实MCP stdio及自有隔离游戏。共七类场景、九次尝试：

1. 首批无先古房间检查通过；basic准备错误地假定读取成功就有enabled选项，从空的可选集合取值导致StopIteration。68.205924761秒，PID38568退出。
2. 第二批等到入场选项启用，随后打开并关闭浏览页；脚本沿用浏览前的可选状态，在返回过渡中选择，被原生拒绝。47.208502149秒，PID39156退出。
3. 仅修正审阅脚本，在选择前依据当前enabled等待；basic、dialogue、touch、transform、bundle、nested六类全部通过，149.322131739秒，PID39578退出。

两次失败均是审阅脚本对已有接口的错误假设，没有修改产品。原脚本、失败日志和原始响应保留。最终六类没有重复运行；前一批已通过的无先古场景也未重跑。所有实例使用同一b5096c3e…41ad运行时。

| 场景 | 核验结果 |
| --- | --- |
| 无先古房间 | 非法读取为通用错误；已有许可保留，直接end_turn成功 |
| 普通馈赠 | 冷调用成功；读取前后HP、牌组、遗物及任务等私有核对字段不变；full与基础观察的静态选项一致；default省略普通null；不支持summary；地图／牌组覆盖拒绝后可直接关闭；就绪详情后直接领取，领取后只剩Proceed |
| 多行对话 | 未揭示后文未返回；继续后出现新台词；对话结束返回可选择馈赠 |
| 欧洛巴斯 | 悬停包含当前角色的遗物／卡牌引用；领取后可再次查看 |
| 变牌／卡牌包 | 选择覆盖期间拒绝inspect_ancient，inspect_selection仍能读取当前选择 |
| 嵌套奖励 | scene为rewards，inspect_ancient拒绝，inspect_rewards可读取 |

三个批次合计87次MCP调用、16次直接原生核对；运行器的创建／重置和私有截图请求不计在这16次内。另用首批实际成功包执行五种screen变体的离线校验：正确上下文与四种矛盾上下文均被接受，结果见context-mutations.json。这是输出校验缺口的重现，不是实际游戏发生覆盖穿透。

[16份实测样本](2026-11-07-inspect-ancient-examples/README.md)逐份记录参数、证据行、原生文件及SHA-256。GUI覆盖常规单人原生页面；未穷尽全部先古／角色／遗物组合、多人、第三方UI，未构造致死上限、异常布局及无法悬停按钮。未将源码检查描述为这些边界的GUI通过。

交付检查通过：16份样本为14份full、一份default和一份不支持summary的错误，194个相对链接有效，三个自有进程均退出，两个DLL哈希保持不变。初次样本计数检查将被拒绝的summary误计为full，断言失败记录保留；已修正文档分类、文件名与清单，复查见final-verification-fixed.log。

## 候选参数接入

summary应共用静态先古投影，保留页面说明、对话、馈赠正文和按钮，仅移除hover_tips及false警告；get_observation三个完整预设继续使用该静态主体。

option_ids可复用整数筛选约定：省略/null为全部，[]为空，限制非负Int32、去重、页面顺序；缺失ID合并errors。选项已有稳定id，不建立筛选后位置编号。完整响应先校验，再进行筛选和摘要；不可悬停note引用原生选项id，并随筛选同步缩小。
