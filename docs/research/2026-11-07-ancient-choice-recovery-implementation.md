# 先古馈赠选择恢复与反馈修复

> 当前状态：实现与18组GUI验收完成；计划共1项，已完成0项，剩余提交、独立审阅及合并清理。无阻塞。

依据[输出定稿](2026-11-07-choose-ancient-option-review.md#输出定稿)及[实施计划](../superpowers/plans/2026-11-07-ancient-choice-recovery.md)。当前接口见[先古指南](../development/ancients.md)；[24份修复后返回](2026-11-07-ancient-choice-fixed-examples/README.md)与[原审阅样本](2026-11-07-choose-ancient-option-examples/README.md)分开保存。

## 实现结果

- 明确点击前拒绝使用已有RejectedBeforeSubmission保证，注册choose_ancient_option的恢复策略；已有有效许可可直接续接改选、推进对话、选牌、奖励、关闭覆盖页及前进。首次动作、stale、未知、已交互或坏响应仍不授予许可。
- AncientInspection集中页面、选择动作及选项不可用原因；执行入口、options.enabled及available_actions共用。具体提示区分无房间、覆盖、等待、对话未完成、已领取、无效ID、锁定、禁用和不可交互。advance_dialogue仍保留原错误恢复策略，动作执行继续走原生ForceClick及事件同步器。
- 修正RunResourceJournal的顶栏可见性：已知原生选择页在进入／退出时，CardSelection对象存在但尚不能接受输入，不代表仍画出的顶栏不可读。移除这个过早返回，继续要求当前玩家、真实显示的顶栏、无场景切换／地图／牌组／模态覆盖及已识别原生选择页面；RunInventoryJournal的隐藏清理、延迟发布和名称披露条件保持原样。

旧代码在选牌入场过渡中清掉挂起遗物记录；只修正顶栏判断后，Scroll Boxes到达可见bundle时返回一次relic_obtained，且不提前报告未选定的卡牌。没有从持有模型补造隐藏名称，没有保留真实隐藏期间的变化等待回放。

参数维持option_id、default/full，默认default；成功为原有精简回执，schema46不变。Mod0.78.1、MCP0.80.1，版本集中维护README。

用户要求已记录为TODO第9项：游戏升级至v0.111后，对照原版及Mod环境复测低最大生命下选择瓦库卓越斗篷的崩溃；共9项／已完成4项。本次没有升级游戏、重新触发致死场景或修改致死行为，也没有正式安装或推送。

## 基线与测试先行

代码基线da5edf8；游戏v0.107.1/release59260271、RitsuLib0.6.10、Godot4.5.1。原生API与审阅证据见[开发核验](2026-11-07-choose-ancient-option-development-notes.md)。证据根`.tmp/2026-11-07-ancient-choice-recovery/`。

Python新增4个会话测试方法，使用实际GameTools和外部原生响应替身：RED为1处恢复断言失败，0.047秒；GREEN4项，0.046秒。分别见python-red.log、python-green.log。

在旧DLLdcee25a818d107d90f22860fcd7e98d59185142eef6712ac3adc6932b9cc4b22中，原生GUI先复现bundle已显示Scroll Boxes、获取事件却为0；预期为1。43.526415669秒，PID59462退出，gui-red/report.json保留为expected_failure。没有先修改物品记录逻辑来掩盖该失败。

完整Python811项通过，39.178秒，python-full.log；C#145项通过，csharp.log。最终构建5.65秒，零警告／错误，build.log。编译产物及隔离运行时均为6cb15bec6745bc9ef8c81bbbd683527732a774e6013089fbe0422263d04f4e7a；构建后没有修改C#或重复构建。

## 游戏内验证

新verify_ancient_choice_recovery使用实际MCP stdio、原生操作及原始快照核对，明确拒绝均验证未交互／未提交且前后令牌相同；后续合法动作在同一连接直接提交，没有夹入公开读取。

最初运行器在启动前拒绝不支持的旧inventory场景名event，未启动游戏；修正为已有upgrade回归，原gui.log保留。新gui-fixed目录的16组一次通过：383.102402855秒，PID60947；报告gui-fixed/report.json，最终DLL6cb15bec…f4e7a。

| 验证组 | 结果 |
| --- | --- |
| no_ancient／basic／default | 无房间、无效ID、本地与原始参数错误后可直接合法操作；普通领取事件正确，default/full保留原回执；完成后重复领取提示proceed并可直接前进 |
| dialogue／covered | 未完成对话拒绝后直接advance_dialogue；地图／牌组覆盖给关闭工具，允许直接关闭 |
| disabled／offscreen／hidden | 禁用、离屏与隐藏选项拒绝，不穿透点击；可直接改选另一项 |
| stale | 外部选择使旧观察过期；stale不恢复许可，刷新后继续 |
| transform／bundle／nested | 各自停在原生选择／奖励边界；错误重复馈赠后可直接选牌、预览包或处理奖励；bundle记录已显示遗物一次，未选定卡牌不提前加入 |
| touch | 馈赠获取、旧起始遗物移除及增强遗物获取顺序保持原样 |
| inventory_visibility | 原RunInventoryChecks的19项检查全部通过，包含隐藏／中断获取不公开、恢复不回放和释放订阅 |
| legacy_stability／event_inventory | 原生换幕入先古后延迟仍可直接选择；既有事件升级的物品／卡牌反馈保持有效 |

同一bundle路径另补两项隐藏顶栏／遗物栏负例：领取前真正隐藏UI，不记录获取；恢复后预览不回放。首次探针在外部隐藏UI后未刷新快照，正确触发stale_state，属于准备错误；原gui-hidden报告保持failed，20.306680464秒，PID61909退出。修正私有隐藏／恢复后的读取后，两项在gui-hidden-fixed一次通过，42.124476196秒，PID62366退出。对应运行器Python12项通过，1.040秒。

补查只增加验证器分支和配置，未修改产品或重跑已通过16组。两批18组成功用例及这次失败尝试都使用同一最终DLL；加上旧DLL的RED，共四个自有游戏进程均退出。交付检查另核对原始响应中的实际隐藏字段，确保负例没有在UI已恢复时误判通过。

24份实际MCP返回为23份full、一份default，逐份记录参数、原始证据行／响应路径及SHA-256；未裁剪或拼造成功回执。

## 文档、审阅与剩余范围

先古接口、期间事件、工具清单及既有错误恢复待办范围随实现同步，旧审阅记录保留基线。已知原版崩溃只记录用户明确要求的版本后复测，不作为三项项目整改的前置。

进行一次独立整分支审阅，重要问题按测试先行修复，轻微建议记录；不安排复审。之后归档并核对本计划技能目录，合入main、删除临时分支。多人／第三方UI、advance_dialogue自身的动作恢复及尚未审阅工具继续保留既有范围。

交付检查核对811项Python、145项C#、18组GUI、19项隐藏／物品检查、24份样本与12份原生成功响应重放、四个进程退出、TODO9/4及v0.111门槛、版本、DLL和345个相对链接。原始失败及准备错误保持记录，未据此宣称产品已修复原版崩溃。
