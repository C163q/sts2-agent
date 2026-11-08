# 房间资源与结算文字修复实施

> 当前状态：两项实现及验证已完成，2/2；待一次独立审阅及合入 main。验证夹具的已知清理限制见下文。

实施基线 `4646de9`，依据[用户反馈复核](2026-11-08-early-playtest-feedback-review.md)及[两阶段计划](../superpowers/plans/2026-11-08-room-resource-and-result-text.md)。交付 Mod `0.81.0`、MCP `0.84.0`，观察 schema 保持 47；当前兼容基线仍统一见 README。

## 资源记录

[RunResourceJournal](../../src/Sts2Agent/Events/RunResourceJournal.cs)保留原生通知订阅和公开顶栏采样；新增纯状态类 [RoomResourceChange](../../src/Sts2Agent/Events/RoomResourceChange.cs)，负责已有公开基线、事件位置和延迟显示确认。地图移动、原生房间进入任务及换幕提供已知过渡范围，普通隐藏／覆盖不扩大读取。

通知到达时先在动作的同一缓冲中保留位置；目标画面显示对应端点后才发布 gold_changed／hp_changed／max_hp_changed。一次遮挡期间未显示的中间数值合并为公开端点，分别显示的增减保留为独立事件；恢复后只建立基线，不回放真正隐藏的变化。战斗日志负责的可见生命变化及伤害不重复记录。

[ActionObservation](../../src/Sts2Agent/Adapter/GameAdapter.ActionObservation.cs)等待这些待确认记录，包括需要返回选择的边界。缓冲位置上限、连续 sequence、现有事件字段和信息边界保持一致，没有为特定遗物添加生产补丁。

## 结算文字

[RunResultInspection](../../src/Sts2Agent/Observation/RunResultInspection.cs)在同次采样中收集结构字段及其原生文字来源，交给 [RunResultText](../../src/Sts2Agent/Observation/RunResultText.cs)排除对应控件的文本。texts 不再重复横幅、计分行、发现数量和普通按钮文字，保留未结构化正文、故事、总分进度及可滚动内容。

去重按节点归属进行；独立正文即使与横幅同字也保留。章节槽的 Reveal／View 只表达操作，不把槽位本身的说明视为已结构化文字。基础观察及专用查看的三种内容预设继续复用同一原生读取器，字段结构与工具参数不变。

## 验证

目标游戏为 Linux `v0.107.1`、release 构建 `59260271`，RitsuLib `0.6.10`；游戏程序集 SHA-256 与[开发核验](2026-11-08-early-playtest-feedback-development-notes.md)一致。证据目录为 `.tmp/2026-11-08-room-resource-and-result-text/`。

- 旧资源逻辑的休息处与问号房实际选路均返回 events:[]，新验证器因此失败；原生数值已变为金币 112、问号房 HP 65。两份失败证据分别保存在 resource-red 和 resource-red-unknown。
- 资源状态检查先因 RoomResourceChange 尚不存在而编译失败，完成后共 155 项纯 C# 检查通过，覆盖公开端点、动画中间值、独立多次变化、隐藏取消、无基线和缓冲上限。
- 结算旧读取在原生检查中因重复横幅／按钮而失败，见 text-red-ending-ready；修复后独立同字正文、计分去重及完整正文检查通过。
- 完整 Python 回归 844 项通过，构建零错误、零警告。

最终产物的四份通过报告：

| 报告目录 | 范围 |
| --- | --- |
| final-resources | 五局：休息处、问号房、战斗入场、隐藏顶栏后恢复、选牌覆盖；同时验证原有资源可见性检查 |
| text-green-death | 失败、汇总、后续解锁及返回主菜单 |
| text-green-victory | 胜利、汇总、时间线教程／章节、各类解锁及返回主菜单 |
| history-isolated | 构造的原生历史页、滚动、完整正文及三种预设 |

合计八类通过的 GUI 场景，56 项原生文字检查，354 份成功原生响应按当前公共解码／预设路径重新投影，与原 MCP 返回完全一致。公开汇总样本仍包含总分进度；横幅和按钮通过对应结构读取。七份完整实测 JSON 见[样例目录](2026-11-08-room-resource-and-result-text-examples/README.md)。

四份通过报告使用同一 Sts2Agent.dll，SHA-256：`a7b382db0eac2aacae42ebb53e769171ee8710b7d47b7f3f1987fe0959b0cf8f`。构建目录与隔离运行时一致；提交／快进合并不重新构建该产物。核验汇总在 verification.json。

## 保留的失败证据与范围

普通 play:death 夹具没有建立角色统计，进入汇总时原生 AnimateScoreLines 抛出 KeyNotFoundException；text-red 保留日志，后续改用已有专用 ending 夹具，没有添加产品绕过。第一次专用控制脚本未等待启动时的 unrecognized 就断言主菜单，证据保留在 text-red-ending；修正等待后使用新目录复测。

组合套件 final-gui 的五个资源场景及历史页验证器均通过，但历史页夹具随后 reset_test_run 返回主菜单时，原生 NInputSettingsEntry.Create 发生数组越界并崩溃，组合报告保留为 failed。未断言该清理故障已解决，也未据此修改输入配置或产品代码。改用历史页独立进程验收并退出，同时将资源套件独立完整运行；正常胜利／失败返回主菜单均通过。

该构造历史页来自私有测试夹具；目标游戏的普通 View Run 入口仍禁用。人工历史页复用测试进程的清理路径仍存在上述限制，不代表已验证正常玩家入口。第三方自定义房间／资源控件、所有遗物组合及所有换幕效果未穷尽实测。

未修改用户 TODO、正式存档或已安装 Mod；游戏测试全部使用独立目录和自有进程。
