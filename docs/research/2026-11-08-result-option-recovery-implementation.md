# 结算选项操作实施与验证

> 当前状态：代码、验收和一次独立审阅完成。共3项，已完成2项；剩余记录归档、核销及合入main。暂无阻塞。

实施基线0d2aa20；要求见[输出定稿](2026-11-08-run-result-option-review.md#输出定稿)，步骤见[计划](../superpowers/plans/2026-11-08-result-option-recovery.md)。证据根目录`.tmp/2026-11-08-result-option-recovery/`。游戏及原生程序集基线沿用[开发核验](2026-11-08-run-result-option-development-notes.md)，未升级游戏或RitsuLib。

## 实现范围

- RunResultInspection集中操作级和单项拒绝原因，Ready、enabled、available_actions和执行共用条件；只读查看仍允许展示中的静态内容。
- run_result_option的明确未交互拒绝提供公开原因和action_submitted:false；注册已有的未提交恢复策略，不放宽过期、不确定、已交互或坏响应。
- 在首次滚动／点击前记录交互；滚动完成后核对原根页面、当前同ID对象、可点击和屏内状态。
- Obtained及Complete章节都提供稳定epoch ID，分别显示Reveal／View。NotObtained的操作范围不扩大，使用原生首次揭晓、重读、分页及解锁队列。
- 普通翻页保持精简transition，解锁进度不报告为本局获得物品。option_id及default/full不变。

## 原生详情资源与夹具

核对了游戏PCK v3／Godot4.5.1的目录和MD5。`scenes/screens/run_history_screen/run_history_screen_via_game_over_screen.tscn`存在，大小675字节、MD5为`90b7a8932c91e88158c3c6dd2b8d966c`；内容仅有Control根、Backstop和普通NRunHistory实例。目标NGameOverScreen.OpenRunHistoryScreen只添加该根，没有SetStack或Push。原版View Run仍禁用。

原审阅夹具将普通历史页直接添加到结算，返回按钮依赖的_stack为null。修正后加载原生结算包装资源，将其中的历史页交给当前空闲NRunSubmenuStack.Push；原生Pop后清理包装根。准备失败时退出该夹具导航并清理，不修改生产入口。

操作共用判断同时防止无有效返回导航的历史页被执行；读取保留当前静态内容及visible状态，不把导航缺失误报为展示未完成。14项原生检查覆盖资源包装、有效菜单栈、无导航拒绝及禁用按钮、完整浏览、滚动位置、隐藏与透明边界。没有在正常游戏启用View Run，也不把夹具成功描述为正常入口可达。

## 测试记录

Task1：新Python许可模块6项先RED（2处失败、2处错误），修正注册及明确拒绝后36项相关测试GREEN；全量834项通过，39.658秒。编译零警告／错误，5.65秒。提交d48dd56。

Task2：新GUI使用旧运行DLL实测RED，reopen-red在85.107秒后确认已揭晓epoch仍有提示来源但不在options；原样保留失败报告。旧历史页返回的已观察崩溃沿用本次审阅证据，未重复触发。

新实现编译零警告／错误，5.86秒；运行DLL与构建产物SHA-256均为`2a87d3a18c4c34dca800132ed4cdb489f4ac8e20dc1e9ec3bfb6be84cfb4a1b5`。gui-suite的basic、history两类通过；basic验证原生拒绝后直接end_turn和本地参数纠正，history验证实际back返回汇总。私有入口双重门控包含新故障夹具；原生浏览／导航14项检查通过。

最终全量Python834项通过，40.498秒；C#145项检查通过。四类GUI使用同一2a87 DLL，全部通过：

| 类型 | 验证内容 |
| --- | --- |
| basic | 冷调用、错误房间后直接end_turn、本地参数错误后直接继续；87个私有入口在testMode关闭及suite／scenarios关闭时分别全部拒绝 |
| history | 原生包装资源、原生Push／Pop生命周期、缺失导航保护、14项浏览／导航检查；back实际返回summary |
| flow | 胜利建筑师与终局读取要求、Reveal变View后原ID重读、实际下一章正文改变、原生解锁队列、直接default confirm、滚动中目标失效及后续需读取、返回主菜单及无关联时间线拒绝 |
| errors | 失败结算展示中、全部禁用、未知ID和未提供的View Run具体拒绝；连续纠正、真正过期、正常重读及解锁、主菜单关联边界 |

flow用时159.848秒，errors82.413秒。stage2-verification.json再次校验136次实际MCP调用及109份成功原生响应重放一致。旧RED进程118754、新suite进程119355、flow119748、errors120102均已退出，日志及原始响应保留。

最新版本为Mod0.80.0、MCP0.82.0、schema47；20份[修复后实际JSON](2026-11-08-result-option-fixed-examples/README.md)包括19份full及1份default，参数、报告行号、原生文件和SHA记录在manifest。原审阅样例不覆盖，保持旧基线。

现行文档把旧的“原生拒绝总要读取”改为明确未交互拒绝可直接纠正；历史页的浏览验证也与原生入口可达性、有效返回导航分开说明。没有启用原版View Run或加入用户TODO。正常入口、每日挑战榜单、多人、第三方页面、全部角色／随机解锁组合仍不在新增GUI保证范围。

## 独立审阅

review_result_option_recovery使用gpt-6.1-sol/high、新上下文只读核对0d2aa20..b0f417b，结论可合入；Critical和Important均无，Minor1项。未重建、重跑GUI或重复全量检查，无修复轮及二次派审。

非阻断M1：verify_result_option.py首次重读分支如果已有分页按钮，只点击并设paginated，没有比较翻页后的正文。另一处分支有完整正文比较，本次真实flow走了后者，当前验收结果有效；前者保留为后续测试覆盖改进，不增加用户TODO或夹带实现修改。

审阅搁置范围及裁定：

| 范围 | 裁定与依据 | 剩余影响 |
| --- | --- | --- |
| 正常View Run入口可达性 | 保持原版禁用，只认可正确夹具与生产保护 | 原生未来启用该入口后仍需重验加载和返回 |
| 榜单／多人／第三方页面 | 未修改，保持单人守卫，不新增兼容保证 | 这些环境可能需要单独适配或人工操作 |
| 全部角色和随机解锁组合 | 代表胜利／死亡、重读／分页／队列实测通过，不扩大为穷举保证 | 稀有内容分支仍需补测 |

滚动故障直接实测了按钮禁用；隐藏、替换目标或根页面变化的分支由静态审阅核对，没有新增相应GUI注入模式。正式安装、用户TODO和个人存档未修改。
