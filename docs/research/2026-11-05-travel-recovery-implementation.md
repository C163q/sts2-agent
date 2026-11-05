# 地图旅行拒绝恢复与赐福鹿角验证

> 当前状态：已完成，共 1 项已完成 1 项。两项旅行修复、赐福鹿角验证、完整单元／GUI 检查与一次独立审查完成，cf0ba88 已快进合入 main，临时分支已删除，无遗留实现或阻塞。

依据为[已确认审阅](2026-11-05-travel-to-node-review.md)及[实施计划](../superpowers/plans/2026-11-05-travel-recovery.md)。起点提交 6dd7eb7，实现提交 cf0ba88 已合入 main；fix/map-travel-recovery 已删除，本地正式 Mod 未安装、未推送。

## 行为与范围

- node_id、default/full、原生选路与精简成功回执保持现有契约。
- 点击或滚动前的固定拒绝公开具体原因，并在已有许可且保证无交互时允许直接选择合法操作。无初始许可不发出动作；旧状态、超时、异常和未知结果仍要求观察。
- MapView.TravelUnavailableReason 统一旅行可用原因，MapInspection.Choices 复用同一判定；不在 Python 推算合法路线。
- 首次原生滚动之前标记 UI 交互；滚动后的失败只有固定公开原因，不附无交互保证。因此尚未点击节点也可能已经改变界面，不能恢复许可。
- 原有 run、graph、act、候选对象校验和原生异步入场等待保留。没有添加目标位置、随机插入点、牌序或额外选路事件。

生产入口为 [GameAdapter.Navigation.cs](../../src/Sts2Agent/Adapter/GameAdapter.Navigation.cs)、[MapView.cs](../../src/Sts2Agent/Observation/MapView.cs)、[MapInspection.cs](../../src/Sts2Agent/Observation/MapInspection.cs)及 [tool_registry.py](../../src/sts2_mcp/tool_registry.py)。未修改共用 GameSession 许可状态机或卡牌事件记录。

## 赐福鹿角

核对同一 Linux v0.107.1／release 59260271 游戏程序集，SHA-256 与[审阅依据](2026-11-05-travel-to-node-development-notes.md)一致。目标版本 BlessedAntler.BeforeHandDraw 仅在持有者首回合抽牌前创建三张 Dazed，通过 AddGeneratedCardsToCombat 加入 Draw，并用 CardCmd.PreviewCardPileAdd 展示。已核对的私有源码证据是 `.tmp/2026-10-31-ancients/source/BlessedAntler.cs`、`.tmp/decompiled/CardPileCmd.cs` 及 `.tmp/2026-11-02-card-add-destinations/source/CardCmd.cs`。

测试夹具只通过原生 RelicCmd.Obtain 获得遗物、准备可选战斗节点，后续由公开 travel_to_node 真正入场。测试没有直接向牌堆加眩晕。修改旅行行为之前的夹具构建已实测通过：三条 card_added，name 为 Dazed、pile 为 draw，三张 ID 各不相同；之后的抽牌事件可以引用同一张已加入的眩晕。现有 CardAdditionJournal 正确记录这一效果，无需修复。

这个结果只说明已展示的加入身份与方向，不输出内部 Random 插入位置或抽牌堆顺序。正常入场也不保证一定抽到眩晕；初次测试中的抽到结果不能写成遗物额外效果。

## 测试与失败记录

私有证据根 `.tmp/2026-11-05-travel-recovery/`。

- python-red.log：新增 3 项回归，预期 1 项失败，明确拒绝仍要求 get_observation；其余保守分支已经通过。
- build-fixture.log：仅新增遗物夹具时构建通过，0 警告／错误，DLL ff8b21d616159fca20dbad6170d853a9e389c3160ca346fbd778ea4229ab8c62。
- antler-before/report.json：行为修改前的遗物 GUI 通过，测试进程 120484 已退出，原始 JSON 保留。
- python-focused.log：52 项通过，3.220 秒。
- build.log：新增隔离测试入口使用 Environment 未加 System 限定，与 Godot.Environment 冲突，2 项编译错误；未使用失败产物运行后续游戏。修正类型限定后 build-corrected.log 通过，0 警告／错误，4.45 秒。
- python-full.log：706 项通过，38.242 秒；csharp.log：124 项通过。
- 最终构建与隔离运行时 DLL 均为 d43d0d187331cf38918f751d8bd9b7439f8d2e9b3683fd0540c178ceaf6f6671；最终 GUI 使用这一产物。
- [GUI 验证器](../../tests/game/verifiers/verify_travel_review.py)和[清单](../../tests/game/data/gui_suite_travel_review.json)包含原九类旅行、antler 与 scroll_failure。最终 11 类全部通过，289.074 秒，82 次真实 MCP 调用；进程 122341 已退出。加上 antler-before 的 5 次，共 87 次 MCP 调用。

scroll_failure 是双重测试门控下的扰动：先通过原生滚动使候选离屏，记录离屏候选 ID；在工具真实发出下一次滚动后禁用旅行，核对拒绝、执行事实与下一动作的 observation_required。清理时恢复原生开关并移除测试补丁，再正常旅行离开夹具奖励页。它用于检验中途变化，不代表自然游玩已经出现相同故障。

[9 份修复后真实完整 JSON](2026-11-05-travel-fixed-examples/README.md)包含许可保留／交互后撤销、default/full 和赐福鹿角。原审阅的 10 份 JSON 作为基线保留。

- gates/report.json：新增测试入口连同既有入口共 75 项，在关闭 testMode、关闭 suite 和场景配置两组条件下均拒绝；14.715 秒，进程 123275 已退出。核心 11 类 GUI 已先运行，门控另起独立实例补验；维护清单将门控步骤接在 antler 后，不把本次两份报告冒充一次连续运行。
- verification.json：新 9 份与原 10 份样本逐对象、参数和 SHA-256 匹配，最终 342 个相对文档链接通过；三个自有游戏进程均退出。初次运行私有校验脚本缺少仓库根 PYTHONPATH，导入 tests 失败；改用 PYTHONPATH=src:. 后完整校验通过，没有据初始化失败宣称成功。

## 验证边界与交付

多人、第三方地图、任意并发人工输入、所有入场遗物组合及自然完整 Boss 战不作穷举；入场任务、失败和许可边界结合源码核对。以已经定位的两项错误处理缺口和可见遗物效果为范围，不扩展卡牌事件模型或项目整体架构。

独立审查范围 6dd7eb7..cf0ba88：Critical 0、Important 0、Minor 0，可以合并，五项重点均核对。审查只读使用已有证据，没有重复运行构建、游戏或完整测试；不存在待修复审查项。结果保存在 `.tmp/2026-11-05-travel-recovery/review-result.md`。

执行取舍：复用当前工作区的临时分支和已有依赖，单一写入者实施；并发修改需要重新隔离与验证。已有用户确认覆盖方案、执行和本地合并，未重复请求确认。多人继续明确拒绝；第三方地图可能拒绝或超时；未测遗物组合可能需要追加实测；并发人工干预通过已有状态／身份检查保守中断；夹具 Boss 边界不代表自然完整 Boss 战。以上均不扩大行为保证，也不据未测范围新增实现或 TODO。

执行记录、任务完成检查和审查包已归档至 `.tmp/2026-11-05-travel-recovery/inline-workspace/`；逐文件哈希校验后仅清理本计划 workspace，其他任务目录保留。
