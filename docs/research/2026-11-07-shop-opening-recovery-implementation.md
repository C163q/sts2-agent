# 商店打开拒绝恢复与诊断实施记录

> 当前状态：实现和全部约定验收完成，等待独立最终审阅及合入。暂无阻塞。

依据[输出定稿](2026-11-07-open-shop-review.md#输出定稿)和[实施计划](../superpowers/plans/2026-11-07-shop-opening-recovery.md)。旧问题与原生证据见[审阅开发核验](2026-11-07-open-shop-development-notes.md)。

## 变更

- 打开操作、available_actions及基础观察open.enabled共用ShopInspection.OpenUnavailableReason；页面覆盖检查供详情和打开共用，动作活动等待供Ready和打开共用。详情读取仍独立于输入阻挡／购买就绪。
- 明确点击前拒绝返回固定英文原因和action_submitted:false；MCP仅对open_shop启用已有未提交恢复协议，保留已有许可并给出choose_legal_action。首次未观察仍拒绝，stale及交互后／未知错误不恢复许可。
- OpenShopRequest在共用检查后才UiChanged并调用原生Merchant.ForceClick，独立于购买监听；等待当前run和商店Owner仍一致，否则interrupted。正常完成继续使用精简回执及transition，不新增参数或summary。
- 原始接口多余参数也给出明确点击前拒绝；MCP本地非法参数继续保留许可。原始参数校验仍早于动作状态检查，MCP会在本地拒绝此类参数。
- 已核对NMerchantButton.OnRelease：IsLocalPlayerDead时仅产生对白，不能展开商品页，因此打开检查明确拒绝该状态。没有新增此状态的GUI扰动，依据目标源码；现有单人商店正常路径不受影响。
- 关闭和购买行为不迁移；共享Ready条件保持原有含义，详情原有诊断保持原文。没有新测试操作或夹具，现有双重门控数量保持81。

关键代码：[ShopInspection](../../src/Sts2Agent/Observation/ShopInspection.cs)、[商店动作](../../src/Sts2Agent/Adapter/GameAdapter.Shop.cs)、[可用工具](../../src/Sts2Agent/Adapter/GameAdapter.AvailableTools.cs)、[参数入口](../../src/Sts2Agent/Adapter/RequestDispatcher.cs)、[工具注册](../../src/sts2_mcp/tool_registry.py)。

## 基线及证据

- 任务基线b376bd2；Mod0.74.0→0.74.1、MCP0.76.0→0.76.1，schema43不变。
- Linux游戏v0.107.1/release59260271、RitsuLib0.6.10；目标程序集和原生证据沿用审阅核验的SHA-256及路径。
- 原始证据根`.tmp/2026-11-07-shop-opening-recovery/`。
- 最终已构建／隔离运行时DLL均为09a61eedf19dcf26669a476bbca8174d613aa71484130ad7793b8b3ff535e788。没有正式安装或推送。

## 验证

1. 四项新Python在旧实现RED：两个预设子用例因get_observation而非choose_legal_action失败，0.047秒；其他未知／过期／交互证据及首次无许可边界通过。
2. 旧DLL的GUI RED在无商店拒绝后恢复断言失败，gui-red保留报告；PID54594已退出，使用旧DLL163a3ee0db90a7ef238c80c05320e5c756ffeb0ccd89fc0bb791138e106ad209。
3. 针对性33项Python通过，2.064秒；全量755项通过，46.160秒。131项C#通过；构建6.39秒、零警告／错误。
4. 五类专项GUI全部通过，137.050471277秒，PID58516已退出。包含无商店、普通／假商人、删牌、阳伞，核对准确原因、原生未提交证明、无中间观察直接继续，以及full/default和立即观察库存。普通场景另测原始接口非法参数；无商店场景另测stale不带未提交证明。
5. 普通购买、送货员补货、删牌、药水瞄准及详情显示五类回归全部通过，171.050876340秒，PID59977已退出；显示包含16组扰动及两种禁用模式各81个测试入口门控。输入阻挡期间的静态详情仍可读。
6. 专项67次MCP、11次直接原生操作；回归166次MCP、52次直接原生操作、10次库存夹具检查、1次瞄准取消及4条建局记录。绿色共233次MCP；另有RED的3次MCP／1次原生检查，不能合称全绿。counts.json保留分类统计。
7. 验收脚本逐份核对25份新旧样本与原始响应、SHA-256及406条相对链接，同时核对测试日志、三个自有PID退出、DLL／运行时清单、门控和清单完成数。

测试入口：[Python行为](../../tests/python/test_shop_opening.py)、[专项GUI](../../tests/game/data/gui_suite_open_shop_review.json)与[验证器](../../tests/game/verifiers/verify_open_shop_review.py)。受控原生响应只用于Python会话协议测试，不能替代真实GUI结果。

十五份[修复后完整JSON](2026-11-07-shop-opening-fixed-examples/README.md)与原始响应逐份相等；旧十份样本不改写。导出附调用、来源行与SHA-256，公开结果不包含内部提交证明或状态令牌。

## 验证边界

多人、第三方商店、任意人工并发切页、真实超时和中途退出不新增GUI穷举；死亡商人及其他活动等待原因按目标源码和共用条件核对。Python覆盖未知、stale、明确已交互及矛盾证据无法恢复许可。源代码中的动画等待和房间身份检查继续使用原生生命周期；不以编译成功替代上述游戏行为验收。
