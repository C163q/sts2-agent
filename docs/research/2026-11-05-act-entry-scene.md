# 第一幕 Boss 后地图场景识别

> 当前状态：已复现并定位，已按确认方案补原生 MapRoom 的统一识别；修复后的即时观察、跨工具上下文与普通战斗回归均通过。归入[地图分类任务](2026-11-05-map-summary-implementation.md)，不新增 TODO。

## 复现结果

隔离导航夹具以原生 Boss 胜利流程准备第一幕战后奖励。调用 proceed 后不插入其他游戏请求，立即调用 get_observation，再按 0.25 秒和 1 秒间隔读取。首次完整观察距离 proceed 返回约 0.256 秒，随后约 0.738 秒和 1.971 秒，三次均为：

```json
{
  "scene": "unrecognized",
  "screen": {"status": "covered", "view": "map"},
  "map": {
    "status": "visible",
    "act": 2,
    "current_node": null,
    "can_travel": true
  }
}
```

这是摘录，原样本还含分类、候选、顶栏、note 等。原生地图已经可操作，选择其公开候选后正常进入 ancient。延迟读取不改变结果，因此本次复现并非 proceed 提前返回未完成的地图动画。

复现证据 `.tmp/2026-11-05-map-summary/gui-act-entry/act_entry_immediate/verify/evidence.json`；完整样本见[修复前 JSON](2026-11-05-map-summary-examples/act-entry-before-fix.full.json)。该局验证与清理通过，但它验证的是旧识别缺口能稳定重现。Mod 目标版本 0.68.0、MCP 0.70.0、schema 41，复现 DLL 为 `9e888a603c0a3d78ecdb6e8f38858b0641e7ba9535fcac77c9aa4feccbdc9844`。

## 源码原因与确认修复

游戏基线 Linux v0.107.1、release 59260271；目标程序集 `data_sts2_linuxbsd_x86_64/sts2.dll` SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。本地 `.tmp/decompiled/RunManager.cs` 的 EnterAct 先退出旧房间并切幕，随后 EnterRoomInternal(new MapRoom())，再完成 FadeIn；真正的先古之民房间在选择起点后进入。

[NonCombatBoundary](../../src/Sts2Agent/Adapter/GameAdapter.Rewards.cs) 已等待 NavigationTasks.ChangingAct 与 MapView.Ready。缺口在 [ObservationContext.Scene](../../src/Sts2Agent/Observation/ObservationContext.cs)：未识别 MapRoom，落入 unrecognized。

已确认的修复是仅将原生 MapRoom 识别为 scene:map，所有工具通过同一场景入口取得此值。战斗、事件、奖励等房间上打开地图仍分别使用 combat/event/rewards，screen.view:map 只表示当前地图页面；不依据打开了地图就将任意房间改为 map。Python 场景白名单同步加入 map。

## 验证范围

- Python 新场景回归先失败，再接入原生分类与公共白名单；旧测试中把 map 当非法值的两项断言改用仍不合法的 deck，其他结构校验不变。
- 修复后验证 proceed 回执、紧接与延时 get_observation、inspect_ui/potions/relics/map、牌组打开／关闭均保留 scene:map；实际进入先古之民后变为 ancient。同时回归普通战斗上下文，避免扩大为所有地图页面都改 scene。
- 尚未测试第三方替代 MapRoom、多人或完整第一幕逐场战斗；夹具准备 Boss 战后状态，后续推进、观察和选路走原生流程。

最终结果及样本见地图任务交付记录；没有通过固定 sleep 修改生产等待逻辑。
