# 对话推进拒绝恢复实施与验证

> 当前状态：实现与验收完成，共1项，完成1项；独立审阅和合入main尚未完成。暂无阻塞。

## 范围和基线

实施依据为[输出定稿](2026-11-07-advance-dialogue-review.md#输出定稿)及[计划](../superpowers/plans/2026-11-07-dialogue-advance-recovery.md)，分支起点53f577f。保持零操作参数和default/full；不改变普通翻句的精简回执、原生馈赠选择和建筑师最终前进。

交付版本Mod0.78.2、MCP0.80.2，schema46保持。目标Linux游戏v0.107.1、release59260271、RitsuLib0.6.10；目标程序集及原生流程依据见[开发核验](2026-11-07-advance-dialogue-development-notes.md)。证据目录为`.tmp/2026-11-07-dialogue-advance-recovery/`。

## 实际修改

- 两类对话的明确点击前拒绝使用RejectedBeforeSubmission；MCP的advance_dialogue注册未提交恢复策略。已有许可可继续用于合法动作，首次、过期、已交互、结果不确定及坏响应不授予许可。
- AncientInspection和EpilogueInspection各提供DialogueUnavailableReason；执行、continue.enabled及available_actions共用。先古页面判断在现有入口内复用用途参数，不新增项目级对话框架。
- 错误区分无对话房间、无对局、非单人、地图／牌组／选牌／奖励覆盖、等待原生流程、已展开／已领取馈赠及建筑师最终按钮，给出相应工具提示。
- 底层多余参数在分发前明确拒绝；正常按钮点击前仍UiChanged，点击后的异常和状态过期不进入未提交恢复路径。
- 成功继续沿原生Released／事件回调与ActionObservation执行；先古最后一句交给choose_ancient_option，建筑师最后一句交给proceed。

维护文档同步到[先古之民](../development/ancients.md)、[终章](../development/run-ending.md)及[共用错误语义](../development/mcp.md#调用和错误语义)。共用动作保证清单同时补齐已实现的choose_ancient_option，避免其现有能力只在专题中描述。旧审阅JSON保留原基线，修复后的返回另行存放。

## 验证记录

| 检查 | 证据及结果 |
| --- | --- |
| Python失败再通过 | 新增test_dialogue_recovery.py的4个方法。RED在先古／建筑师两种恢复断言失败，0.048秒；GREEN 4项通过，0.052秒。 |
| 原生失败复现 | 旧DLL的wrong_room拒绝仍公开通用原因，新增GUI用例失败；gui-red保留原报告及日志，PID72245已退出。 |
| 完整Python | 815项通过，38.473秒；包括过期、提交、不确定、缺失及矛盾证据、本地参数、cold不授予许可等负例。 |
| C#检查 | 145项通过。 |
| 构建 | 5.53秒，零警告／错误。 |
| 先古及错误房间 | 七类GUI全部通过，193.122秒；错误房间、馈赠前后、full／default逐句推进、地图／牌组覆盖、卡牌包选择、额外奖励及外部推进过期；拒绝后直接使用相应合法动作。 |
| 建筑师 | 独立终章验收通过，61.565秒；地图／牌组拒绝、直接关闭、底层参数拒绝、逐步推进、最终拒绝后直接proceed及run_won；原生死亡事件与最终玩法许可保持原规则。 |

最终构建及隔离运行时DLL SHA-256均为`ad21eaffa973c04429980467bf860ad4c13e409a9cea294e46ffd164d6a7ebd1`。正式Mod安装未更新，未推送。

24份[修复后的实际MCP返回](2026-11-07-dialogue-recovery-examples/README.md)已导出，23份full和1份default，未裁剪；11份成功原生响应经当前解析和投影重验相同。交付检查确认版本、DLL、352个相对文件链接，以及三个游戏PID72245、73823、73900与终章验证器73981均已退出。旧DLL的失败复现保留，实施期间没有新增准备失败。

## 独立审阅与交付

独立审阅及合入main仍待完成。

## 验证边界

多人、第三方页面、所有角色／随机台词分支以及其他游戏版本未新增GUI证据；按原生可用性检查及公开不确定结果处理。致死斗篷仍按用户TODO留待v0.111复测，没有在本任务触发或绕过。
