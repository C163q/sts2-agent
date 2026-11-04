# 手牌查看补充牌堆计数

> 当前状态：实现与验证完成，批准范围无遗留；630 项 Python、91 项 C#、两局 GUI 及原生显示边界检查通过，未安装正式 Mod。暂无阻塞。

用户已确认 inspect_hand 增加与 get_observation 相同的抽牌／弃牌／消耗牌数，继续沿用 default／summary 过滤规则。代码基线 `66d3e82`；Mod `0.61.0`、MCP `0.63.0`，观察 schema 仍为 `40`，现行版本以 [README](../../README.md#当前版本与前提)为准。

三项为顶层 draw_count／discard_count／exhaust_count，可空整数，独立于 card_ids。full 保留 null，default／summary 省略 null，0 保留；仅从实际显示的入口计数标签读取，不打开牌堆、不读取内容，也不从内部牌数补齐隐藏标签。完整响应先校验，空筛选与 summary 不能遮蔽坏计数；旧回复未提供新字段时继续兼容。

小范围重构将 get_observation 原有三处计数读取并入 CombatResources.Read，观察和手牌详情共同使用；能量／星数格式与卡牌预设不变。目标游戏仍为 Linux `v0.107.1`、release build `59260271`，RitsuLib `0.6.10`。沿用已核对的 NCombatCardPile.CountContainer/Count（MegaLabel）及 VisibleUi.Number；目标程序集 SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。

验证包括三预设与 null／[]／无效 ID、0 和 null、错误类型拒绝及兼容旧回复；原生 HandResourceChecks 补充可见标签覆盖值、隐藏标签／入口和玩家身体隐藏时的独立读取，结束后恢复所有测试 UI。专项使用 [hand_pile_counts GUI 清单](../../tests/game/data/gui_suite_hand_pile_counts.json)，隔离存档与 IPC，不安装正式 Mod。

完整契约见[手牌指南](../development/hand-inspection.md#参数与返回范围)。执行日志位于 `.tmp/2026-11-04-hand-pile-counts/`。

## 验证结果

新增三项 Python 回归先失败后转绿；全套 **630 项通过**（37.060 秒），**91 项 C# 通过**，构建无警告／错误。两局 GUI（铁甲战士的非零抽牌堆、储君的星数 HUD）及各自12项原生检查通过，标签覆盖值、隐藏标签／入口、身体隐藏和最终状态恢复均符合预期；读取前后完整原生状态相等。

最终 Mod DLL SHA-256 为 `4504a65c32e0d03fe3068cf13307a5642da3945cc3c6bab01cb8572d46565d14`，源码构建、隔离运行时与 GUI 报告一致。自有游戏进程已关闭；未穷举非空消耗入口、所有选牌来源及第三方 UI，现有可见性与卡牌信息边界不变。

实际 `inspect_hand({"preset":"summary","card_ids":[]})` 返回如下，来源 `.tmp/2026-11-04-hand-pile-counts/gui/pile_counts_ironclad/verify/evidence.json` 第 6 个条目（从0计）：

```json
{
  "draw_count": 3,
  "discard_count": 0,
  "hand": [],
  "scene": "combat",
  "screen": {
    "status": "visible"
  },
  "energy": "20/3"
}
```

消耗入口隐藏时字段省略，弃牌0保留；full 对应 exhaust_count:null。空筛选不影响计数。
