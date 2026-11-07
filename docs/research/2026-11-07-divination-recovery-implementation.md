# divine 拒绝恢复实施记录

> 当前状态：已完成，共1项，已完成1项；15类GUI及十八份JSON核对通过，独立最终审阅通过并合入main，无剩余步骤或阻塞。

定稿见[揭开审阅](2026-11-07-divine-review.md#输出定稿)，步骤见[实施计划](../superpowers/plans/2026-11-07-divination-recovery.md)。原错误与十七份旧JSON保留于[开发核验](2026-11-07-divine-development-notes.md)。

## 行为与职责

- divine的x/y、default/full、原生大小范围与精简动作回执保持；文字棋盘和新次数按需观察，成功可直接继续揭开。
- 无棋盘、覆盖、未就绪、结束、已清除或不可交互格分别给具体原因。当前状态匹配、点击前且UI未改变的明确拒绝保留已有许可；冷调用、过期、已交互、未知／坏响应和矛盾保证不恢复。
- 共用页面／交互就绪检查；执行与available_actions复用揭开检查，至少有一个可交互格才列出divine。格子输入条件保持原生鼠标／焦点与覆盖状态，不用图标透明度判断点击区域。
- 原生扣次数、动画等待、诅咒立即入牌组、普通奖励展示与领取时机沿现有流程，不增加动作结果字段或媒体。

[DivinationInspection](../../src/Sts2Agent/Observation/DivinationInspection.cs)的InteractionUnavailableReason复用PageUnavailableReason供工具切换和揭开使用，Ready保持独立；新增RevealUnavailableReason及CellUnavailableReason。[适配器](../../src/Sts2Agent/Adapter/GameAdapter.Divination.cs)明确点击前拒绝使用RejectedBeforeSubmission，UiChanged仍在所有检查之后；[注册](../../src/sts2_mcp/tool_registry.py)使用已有unsubmitted_rejection_unchanged策略。未新增共用许可机制。

## 基线与证据

- 基于a712e1f；Linux游戏v0.107.1/release59260271，RitsuLib0.6.10、Godot4.5.1，目标程序集与原生依据见开发核验，未更换目标。
- Mod0.77.1、MCP0.79.1，schema45不变；旧Mod缺少未提交保证时仍要求重新观察。
- 最终构建及隔离运行时DLL均为754f17436a7ecdaa477b5a8131774c8922f35681842eef6b3d3e1c0709260f8c。证据根`.tmp/2026-11-07-divination-recovery/`；未正式安装或推送。

## 验证

| 检查 | 结果与证据 |
| --- | --- |
| Python RED | 新5项中full/default两处恢复断言失败，0.058秒；python-red.log |
| GUI RED | 旧DLL重复揭开时仍为通用错误及get_observation，在具体原因断言失败；25.811111211秒，PID22666已退出，gui-red/report.json |
| Python GREEN | 新5项通过，0.056秒；python-green.log |
| 完整Python | 791项通过，38.623秒；python-full.log |
| C# | 145项通过；csharp.log |
| 构建 | 5.65秒，零警告／错误；build.log |

Python以原生通信边界替身测试真实GameTools／会话恢复；明确保证后可连续揭开，缺少保证、仅ui_unchanged、过期／异常、已提交／已交互、矛盾证据与坏成功响应均清除许可。首次调用不发送动作，本地非法坐标不影响已有许可。

## 实际返回

[十八份修复后JSON](2026-11-07-divination-recovery-examples/README.md)包括十七份full、一份default，均核对实际MCP来源；旧样本保留。

重复揭开的完整错误为：

```json
{
  "error": {
    "code": "illegal_action",
    "message": "This divination cell is already uncovered. Choose a # cell; inspect_event shows the board.",
    "recovery": "choose_legal_action"
  }
}
```

随后直接揭开合法格成功；样本同样覆盖拒绝后直接end_turn、proceed、skip，以及先腾出药水槽再领取奖励。公共JSON只返回原因与恢复建议，内部未提交保证及执行证明留在原始通信证据中。

## GUI与未验证范围

专项包括无棋盘、小／大范围、重复清除、地图／牌组覆盖、结束、奖励／选牌覆盖、诅咒、金币、遗物及直接连续揭开12类。拒绝前后用不刷新MCP许可的原生读取核对snapshot_id；原始错误须有action_submitted:false及未交互证据，后续合法操作直接执行。原始读回显式关闭图片，避免独立背景动画干扰比较。

金币与遗物核对divine展示奖励时没有获得事件、实际claim_reward才记录；诅咒则在揭开时记录card_added、pile:deck。rewards覆盖验证先直接丢弃一瓶药水，再领取奖励；卡牌选择覆盖验证直接skip。补充工具切换、事件详情与事件选择3类回归。

首批no_board通过，small在非法参数遍历时覆盖了命令行参数变量，写报告出现AttributeError。仅改验证器循环变量名，保留原报告与异常，未改产品或重建DLL；剩余14类在新目录一次通过。两批共15类完成、16次尝试，执行阶段分别48.729382489秒和405.448854013秒；gui/report.json、gui-remaining/report.json保留结果，PID24123与24529均已退出，均加载最终754f1743…0f8c。

样本逐份核对来源行及SHA-256；verify_delivery.py检查RED／GREEN、完整测试与构建日志、三批进程退出、DLL、版本、十八份JSON、直接连续揭开和相对链接，不重新构建。

尚未新增真正忙碌中途、异常隐藏／禁用格、人工并发切页、多人、第三方内容、超时及全部奖励组合的GUI验证；这些条件按源码核对。卡牌选择覆盖由claim_reward产生，不能作为divine直接返回choice_required的实测。

## 独立审阅与合入

独立只读审阅范围a712e1f..c126b20，结论可合入：Critical0、Important0、Minor1，Declined to judge为空。唯一Minor是工具清单阶段文字尚未更新，已在原计划的最终核销中同步；没有进入产品修复回合，无剩余暂缓项或设计裁决。审阅逐份核对十八份JSON及来源／参数／SHA，并核对原生、测试和GUI证据，没有重新构建或启动游戏；摘要见证据根final-review.md。

实现提交c126b20已快进合入main，临时分支fix/divination-recovery已删除，工具清单核销为37/44。任务工作目录5个文件复制并逐份校验SHA-256后归档至证据根inline-workspace，原件已删除，兄弟目录未改。既有TODO仅更新相关工具覆盖范围，未新增用户待办；未正式安装Mod或推送。
