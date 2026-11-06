# 商店关闭恢复与共用按钮流程实施记录

> 当前状态：已完成全部约定实现、验收及独立最终审阅，功能提交38f4c58已合入main。无未完成步骤或阻塞。

依据[输出定稿](2026-11-07-close-shop-review.md#输出定稿)及[计划](../superpowers/plans/2026-11-07-shop-closing-recovery.md)。旧问题及原生证据见[审阅开发核验](2026-11-07-close-shop-development-notes.md)。

## 实现

- ShopInspection.CloseUnavailableReason集中关闭检查，供执行、available_actions及已显示shop.back.enabled使用。共用PagePurpose枚举区分详情／打开／关闭，原有打开和详情诊断保持原文；活动等待继续复用既有函数。
- 明确点击前拒绝公开具体原因并返回action_submitted:false；close_shop注册已有未提交拒绝协议，保留旧许可并返回choose_legal_action。首次无许可、stale、未知结果及已交互／矛盾证据不恢复许可。
- ShopViewRequest共用打开／关闭的原生按钮、UiChanged、run／Owner检查和ActionObservation；关闭从购买监听分开。原生Close、动画等待、期间事件及精简成功回执保留，购买行为不迁移。
- 参数仍为default/full、无操作参数，工具说明精简。原始接口多余参数提供明确未提交拒绝；参数校验仍先于动作状态检查，MCP本地会先拦截此类参数。
- 原生返回按钮会滑入／滑出并支持快捷键；保留当前显示范围及启用规则，没有新增坐标过滤或把未复现差异改成产品限制。没有新增测试操作／夹具，既有双重门控仍为81。

关键代码：[ShopInspection](../../src/Sts2Agent/Observation/ShopInspection.cs)、[商店动作](../../src/Sts2Agent/Adapter/GameAdapter.Shop.cs)、[可用工具](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)、[参数入口](../../src/Sts2Agent/Adapter/RequestDispatcher.cs)、[工具注册](../../src/sts2_mcp/tool_registry.py)。

## 基线与证据

- 任务基线965d338；Mod0.74.1→0.74.2、MCP0.76.1→0.76.2，schema43不变。
- Linux游戏v0.107.1/release59260271、RitsuLib0.6.10，原生程序集及源码位置沿用审阅开发核验中的SHA-256和证据。
- 证据根`.tmp/2026-11-07-shop-closing-recovery/`；最终构建与隔离运行时DLL均为da3c5d00ce7c97c1eeead86622a9c4ebd6aff922ee7756347aebb8569ad812fb。未正式安装或推送。

## 验证

1. 新Python四项在旧实现RED：两个预设子用例因get_observation而非choose_legal_action失败，0.038秒。旧DLL的无商店GUI在同一恢复断言失败；gui-red保留证据，PID69463已退出，使用旧DLL09a61eedf19dcf26669a476bbca8174d613aa71484130ad7793b8b3ff535e788。
2. 针对性37项Python通过，2.273秒；全量759项通过，43.298秒；131项C#通过；构建6.17秒、零警告／错误。
3. 六类专项GUI全部通过，155.205103601秒，65次MCP、37次记录内直接原生操作；PID70199已退出。覆盖无商店、普通／假商人、删牌、子奖励和阳伞，核对公开原因、未提交证明、原始参数拒绝、显示按钮一致性及直接合法续接。
4. 打开五类、普通／送货员／删牌及详情显示共九类回归全部通过，268.762395671秒；PID71729已退出。包含输入阻挡、鼠标／控制器、离屏价格与商品等16组显示，双重禁用模式各81个测试入口均拒绝。
5. 回归222次MCP、63次记录内原生操作、8次库存夹具检查及3条建局记录；绿色共287次MCP、100条原生操作。RED另有3次MCP／1条原生操作，不合称全绿；counts.json保留分类统计。
6. 交付脚本核对27份新旧样本的来源／哈希、413条相对链接、全部日志、三个自有PID退出、DLL／运行时版本及门控，均通过。

测试入口：[Python恢复](../../tests/python/test_shop_closing.py)、[六类专项GUI](../../tests/game/data/gui_suite_close_shop_review.json)、[验证器](../../tests/game/verifiers/verify_close_shop_review.py)。受控原生响应仅用于验证MCP会话协议，真实UI行为另由GUI核验。

## 信息与范围

[十五份修复后JSON](2026-11-07-shop-closing-fixed-examples/README.md)附调用、来源行及SHA-256，旧十二份不变；关闭后的直接原生读回只核对页面和资源，不刷新MCP许可，后续打开／前进可验证真实续接。子奖励由测试夹具注入召唤铃铛触发，不代表普通商店商品。

多人、第三方商店、任意人工并发切页、真实超时和中途退出不新增穷举。动画及按钮生命周期按目标源码核对；Python覆盖未知／stale／已交互／矛盾证据无法恢复许可，不能据此声称这些异常在游戏中均已实测。

## 最终审阅与合入

独立审阅者review_shop_closing以gpt-6.1-sol high和独立上下文审阅965d338..38f4c58：Critical0、Important0、Minor0，可以合入，无本范围内进一步重构要求。独立核对27份样本及哈希／原始行、全部已记录GUI报告和日志；没有重启游戏、构建或测试。

审阅排除范围按定稿处理：不扩展多人／第三方兼容；不声明任意人工并发切页穷举；真实超时与中途退出未新增GUI扰动；buy_item完整设计留待单独审阅。对应兼容性、特殊切页和异常游戏表现仍有验证限制，购买自身的错误恢复或其他边界仍可能有缺口。没有延期小问题。

功能提交38f4c58已快进合入main，清理已合并临时分支；收尾仅更新记录，不重建已验收DLL。任务工作目录六文件已复制至证据根inline-workspace，逐份SHA-256相等后只删除本任务目录，校验记录为workspace-archive-verification.json。没有推送或正式安装Mod。
