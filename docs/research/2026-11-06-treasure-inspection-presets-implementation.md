# 宝箱详情边界与 summary 实施记录

> 当前状态：已完成，共 1 项，已完成 1 项。三项修复、summary、约定验证及一次独立审查全部完成，2862318 已合入 main，临时分支已删除，无遗留实现任务。

规格见[已确认方案](2026-11-06-inspect-treasure-review.md)，步骤见[计划](../superpowers/plans/2026-11-06-treasure-inspection-presets.md)；原问题与证据见[审阅开发依据](2026-11-06-inspect-treasure-development-notes.md)。

## 范围与实现

- TreasureInspection 提供共用静态读取及详情扩展，查看拒绝原因与 available_actions 共用；纯读取保持现有许可恢复。
- 遗物显示使用 Displayed，保留隐藏、透明、容器裁剪和纹理检查；悬停使用 HoverAccess；点击另外保留 OnScreen、启用、动画和原生投票检查。loot_treasure/proceed 执行流程保持。
- full/default 详情只读取可悬停遗物的正文；不可悬停时保留 name/enabled，full 为 description:null、hover_tips:[]，公共 note 指向 treasure.relic；default 过滤普通 null。
- Python 完整校验场景、screen:visible 且无 view、宝箱内容及不可悬停来源，随后才生成 summary 和刷新许可。summary 复用基础观察静态宝箱格式，并省略悬停专用 note；无筛选参数。
- 可见宝箱的 relic:null 在 default/summary 保留。查看本身不要求房间 Ready；未开箱内容和隐藏遗物保持不读取。
- Mod 0.71.0、MCP 0.73.0、schema 41；正式 Mod 未安装。

## 基线与原生资料

项目基线 fac27bf，临时分支 feat/treasure-inspection-summary。核对日期 2026-11-06；游戏 Linux v0.107.1／release 59260271、RitsuLib 0.6.10。游戏安装相对路径 data_sts2_linuxbsd_x86_64/sts2.dll，SHA-256 d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03。

原生开箱、集合入场、焦点与悬停规则按审阅开发依据列出的目标版本本地源码核对。测试设施只在 testMode、STS2_AGENT_TEST_SUITE 和宝箱场景同时开启时开放；每次恢复原始坐标、输入、图标显示／透明及父容器裁剪，finally 和局间重置均调用恢复。注入条件用于验证边界，不作为自然游玩的复现。

证据根 `.tmp/2026-11-06-treasure-inspection-presets/`。

## RED 与构建记录

- python-red.log：6 项新测试，25 个子场景按预期失败，覆盖 summary 缺失、上下文矛盾、不可悬停及来源校验。
- python-focused.log：53 项通过，2.026 秒。
- 先仅增加测试设施并编译，以原生读取验证旧行为；build-fixture.log 零警告错误，4.23 秒，产物 689afb7bf63c105c48576dc78d450b736eeb2f9a60a1143d5f7692c2140d2c6e。gui-red 同时确认 no_hover 仍给正文、offscreen 返回空遗物，两项断言均失败；自有 PID 172701 已退出，保留现场。
- build.log 保留首次正式构建的 CS0136：诊断变量 reason 与稍后的解构变量同名。仅将诊断变量改名为 unavailable；build-corrected.log 零警告错误，4.01 秒。
- 最终 DLL 与隔离运行时均为 a6bc533839a22224adaa0c3564ddbc5936d8d4d31258647e417f3a4a58fd5b00，prepare.log 记录准备。

## 验证记录

- python-full.log：724 项通过，39.044 秒；C# 检查 124 项通过。
- gui/report.json：八类场景全部通过，186.788 秒，172 次 MCP；display 包含 no_hover、disabled、offscreen、hidden、transparent、clipped 六种注入条件，每种核对 full/default/summary、三种基础观察及点击拒绝，finally 恢复后正常领取。
- gui-regression/report.json：旧 basic/open 宝箱流程与原生测试门控三例全部通过，59.560 秒，39 次 MCP；两个禁用模式各 78 项均拒绝。
- 总计 211 次真实 MCP；主套件另含 12 次文件测试控制请求。自有 PID 172701、178050、178765 均已退出。
- [17 份新完整返回](2026-11-06-treasure-presets-examples/README.md)与原 14 份样本共 31 项来源／哈希通过，链接与产物一致性见证据根 verification.json。
- 一次独立审查通过：Critical 0、Important 0、Minor 0，无需追加修复。

## 独立审查与集成

审查者 /root/review_treasure_presets，gpt-6.1-sol/high，fresh context，只读审查 fac27bf..2862318，五项关注均通过；没有修改工作树、重跑构建或游戏。完整结论保存在证据根 review-result.md。

审查未判断多人、第三方宝箱及所有遗物组合的普遍兼容性；维持当前单人原型与明确实测范围，其他组合需要新增原生验证后才能声明兼容。测试设施提前构建只用于保留旧行为完成原生 RED，成本为额外一次 4.23 秒构建，需求与最终生产范围保持。

main 已快进合入 2862318，feat/treasure-inspection-summary 已删除；合并后交付校验通过，产物与实际游戏核验一致。本计划临时工作区按文件哈希核对后归档至证据根 inline-workspace/，原工作区已清理。

## 验证范围

opening 瞬态按源码及静态读取契约核对，未在普通 GUI 路径单独采样。多人、藏宝图、全部遗物组合及第三方宝箱未穷举。旧审阅 14 份样本保持基线。
