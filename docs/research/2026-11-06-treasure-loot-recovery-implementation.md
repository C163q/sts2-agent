# 开箱动作拒绝恢复实施记录

> 当前状态：已完成，共1项，已完成1项。两项修复、约定验证、独立审查与本地集成完成，c86fe22 已合入main，临时分支已删除，无遗留实现任务。

规格见[定稿](2026-11-06-loot-treasure-review.md)，步骤见[计划](../superpowers/plans/2026-11-06-treasure-loot-recovery.md)；原问题证据见[审阅开发依据](2026-11-06-loot-treasure-development-notes.md)。

## 范围与实现

- TreasureInspection.LootUnavailableReason 解析本次点击目标，提供无房间／覆盖／单人／队列／遗物效果／开箱中／已开箱／无可领取遗物／离屏／禁用／未就绪的固定原因；CanLoot及available_actions复用同一判断。
- 查看与动作共用页面原因，查看仍按暴露条件判断，动作保留Ready与原生点击条件；proceed的原前置检查保持。
- 初始参数或动作前置拒绝使用明确未提交证明，Python启用现有恢复机制；没有新许可时仍先读状态。过期、已交互、未知或矛盾证据仍清除许可。
- 一旦UiChanged/ForceClick发生，后续不返回未交互证明；第二阶段仅在原有边界、同一房间及新目标仍可领取时执行，仍共用25秒预算。
- open_only默认false、default/full、精简回执和可见事件保持，无新字段或summary；说明文字明确遇输入边界停止，处理后若遗物仍在则再次调用。
- Mod0.71.1、MCP0.73.1、schema41；正式Mod未安装。

## 基线与原生资料

基线46e5fd1，分支fix/treasure-loot-recovery。核对日期2026-11-06；游戏Linux v0.107.1／release59260271、RitsuLib0.6.10。游戏安装相对路径data_sts2_linuxbsd_x86_64/sts2.dll，SHA-256 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。

原生源码沿用审阅开发依据列出的NTreasureRoom.OpenChest、集合选择与取得流程。无新增游戏API或测试路由，复用已有宝箱、额外奖励、变牌、延迟效果及显示扰动；人工注入不当作自然复现。

证据根`.tmp/2026-11-06-treasure-loot-recovery/`。

## 验证记录

- python-red.log：3项新测试，2个明确拒绝续接子场景按预期失败。
- python-focused.log：46项通过，1.132秒。
- gui-red：旧产物a6bc533839a22224adaa0c3564ddbc5936d8d4d31258647e417f3a4a58fd5b00的wrong_scene仍为笼统原因/recovery:get_observation，新断言按预期失败；PID186668已退出，现场保留。
- python-full.log：727项通过，38.549秒；csharp.log：124项通过；build.log：零警告错误，4.69秒。
- 最终构建与隔离运行时DLL均为da9c1c694042b244cf5672eb4231db8048eac3b5337f84f27c33a572d3249331，prepare.log记录准备。
- gui/report.json：十类GUI全部通过，219.722秒，108次MCP及22次文件辅助请求；包含原生参数拒绝与过期优先、拒绝后直接领取/继续/奖励领取/选牌/旅行，原正常边界及显示扰动保持。
- gui-regression/report.json：旧basic/open及宝箱查看拒绝三例通过，71.195秒，44次MCP。合计152次真实MCP，自有PID186668、191909、192556均已退出。
- [19份新完整返回](2026-11-06-loot-treasure-fixed-examples/README.md)含拒绝与直接续接；原17份样本保持基线。36项样本来源/哈希及链接、产物一致性通过，见证据根verification.json。
- 一次独立审查通过，Critical0/Important0/Minor0，无需追加修复。

## 独立审查与集成

审查者/root/review_treasure_loot_recovery，gpt-6.1-sol/high，fresh context，只读审查46e5fd1..c86fe22；五项关注均通过，无拒绝判断项、无新增问题或TODO。审查另核对13类GUI共152次MCP、36份样本来源/哈希及最终产物一致；未重跑构建或游戏。完整结论保存在证据根review-result.md。

main已快进合入c86fe22，fix/treasure-loot-recovery已删除；合并后交付校验通过，保持实际测试产物。临时工作区按逐文件哈希校验后归档至证据根inline-workspace/，原目录已清理。

## 未验证范围

真实超时、对局中途退出、多人、教程、藏宝图和全部遗物组合未新增游戏实测；超时、已交互失败及矛盾证明由协议测试与源码路径核对。既有预算及第二阶段停止条件保留，无新增故障注入设施。
