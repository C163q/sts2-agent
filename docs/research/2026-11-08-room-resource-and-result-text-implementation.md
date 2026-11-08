# 房间资源与结算文字修复实施

> 当前状态：两项实现及验证已完成，2/2；独立审阅的一项重要问题已单轮修复并验证，产品修改已合入 main（`8e19563`），临时分支已清理。验证夹具的已知清理限制见下文。

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
| review-order-death | 审阅修复后的失败、汇总、后续解锁、各预设英文输出及返回主菜单 |
| review-order-victory | 审阅修复后的胜利、汇总、时间线教程／章节、各类解锁、各预设英文输出及返回主菜单 |
| history-isolated | 构造的原生历史页、滚动、完整正文及三种预设 |

合计八类通过的 GUI 场景，89 项原生文字检查，354 份成功原生响应按当前公共解码／预设路径重新投影，与原 MCP 返回完全一致。公开汇总样本仍包含总分进度；横幅和按钮通过对应结构读取。八份完整实测 JSON 见[样例目录](2026-11-08-room-resource-and-result-text-examples/README.md)。

资源及历史页验证使用审阅前产物 `a7b382db0eac2aacae42ebb53e769171ee8710b7d47b7f3f1987fe0959b0cf8f`。审阅修复只改变英文来源绑定及对应检查；修复后的两条完整终局流程使用交付产物 `d27202e6e103e0d3ce83e8e577da5d9bc6f74dee4722d7d61e5d3fe799507e3d`。后者在构建目录和隔离运行时一致；提交／快进合并不重新构建。样例 manifest 按条目注明实际产物，核验汇总在 verification.json。

## 独立审阅及单轮修复

唯一独立审阅检查 `4646de9..b7a1beb`，没有发现资源记录及控件去重的确定阻断缺陷，提出一项 Important：涅奥的杂项解锁正文仍为中文。这是原有英文来源缺口，非去重引入的退化；按英文输出契约修复，未归为范围外。没有 Minor。

目标程序集显示 NeowEpoch.QueueUnlocks 生成本地化文字，经 QueueMiscUnlock／SetUnlocks 暂存，NUnlockMiscScreen._Ready 直接写入标签。[EnglishRunResultText](../../src/Sts2Agent/Localization/EnglishRunResultText.cs)现在在实际生成／排队／赋值时保留来源，通过 [EnglishEventText](../../src/Sts2Agent/Localization/EnglishEventText.cs)向标签复制稳定绑定，读取不重新运行解锁或改写原生文字。先安装被调用的小方法挂钩，再重建调用者；首版相反顺序在实测中仍失败，调整顺序后两条正常流程通过。

新增公开正文语言断言先对真实中文回执观察 RED，见 review-i1-red.log；修复后两条终局流程的全部 full/default/summary 正文均通过检查，跨越近期文字缓存刷新仍正确，并检查原生标签文字保持不变。涅奥提示返回 `Neow will now greet you at the start of each run...`。完整 Python／纯 C# 回归再次通过。失败的 review-green-death／review-green-victory 与首版绑定 DLL 均保留；没有安排第二次审阅。

审阅中搁置的范围均明确保留：人工历史页复用清理、普通调试死亡夹具缺少角色统计未修复；所有遗物组合、换幕、第三方房间／控件没有穷尽验证；每日榜单没有新增 GUI 证据，普通 View Run 在目标版本禁用；终局等待策略按用户要求保持现状。各自影响见下文，不把替代验证表述为原路径已修复。

## 保留的失败证据与范围

普通 play:death 夹具没有建立角色统计，进入汇总时原生 AnimateScoreLines 抛出 KeyNotFoundException；text-red 保留日志，后续改用已有专用 ending 夹具，没有添加产品绕过。第一次专用控制脚本未等待启动时的 unrecognized 就断言主菜单，证据保留在 text-red-ending；修正等待后使用新目录复测。

组合套件 final-gui 的五个资源场景及历史页验证器均通过，但历史页夹具随后 reset_test_run 返回主菜单时，原生 NInputSettingsEntry.Create 发生数组越界并崩溃，组合报告保留为 failed。未断言该清理故障已解决，也未据此修改输入配置或产品代码。改用历史页独立进程验收并退出，同时将资源套件独立完整运行；正常胜利／失败返回主菜单均通过。

该构造历史页来自私有测试夹具；目标游戏的普通 View Run 入口仍禁用。人工历史页复用测试进程的清理路径仍存在上述限制，不代表已验证正常玩家入口。第三方自定义房间／资源控件、所有遗物组合及所有换幕效果未穷尽实测。

未修改用户 TODO、正式存档或已安装 Mod；游戏测试全部使用独立目录和自有进程。
