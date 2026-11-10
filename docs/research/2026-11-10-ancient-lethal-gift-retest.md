# v0.111.0 致死馈赠崩溃复测

当前状态：复测完成。原版鼠标与 Mod／MCP 四组对照均未复现旧领取崩溃；斗篷正常获得，Sere Talon 正常进入死亡结算。对应用户待办已核销，产品代码及版本保持不变。测试进程已清理；主动终止时的退出异常单列于下文。

## 结论

旧问题发生于 v0.107.1：生命／最大生命均为 9 时领取 Distinguished Cape，隔离环境出现 `Fatal error. Invalid Program: attempted to call a UnmanagedCallersOnly method from managed code.` 并以 SIGABRT 退出；用户也曾报告原版可复现。原始证据见[原生鼠标对照](2026-11-07-ancient-native-click-recheck.md)。

v0.111.0 的斗篷已无最大生命代价；原有 9 点代价移至 Sere Talon。此次同时复测原斗篷和承接代价的馈赠，四组领取前均核对为 9/9：

| 环境与输入 | 馈赠 | 实际结果 |
| --- | --- | --- |
| 原版 `--nomods`，窗口鼠标事件 | Distinguished Cape | 获得遗物、2 张诅咒及 3 张 Apparition，牌组 10 → 15，生命保持 9/9，出现 Proceed 并能打开地图 |
| 当前 Mod，真实 stdio MCP | Distinguished Cape | 相同获得结果；`action_completed / complete:true`，随后 `proceed` 成功 |
| 原版 `--nomods`，窗口鼠标事件 | Sere Talon | 生命变为 0/1，进入 Defeated 页面；Continue 可打开汇总，死亡说明指向 Vakuu |
| 当前 Mod，真实 stdio MCP | Sere Talon | 相同死亡结果；`run_lost / complete:true`，可读取结算并通过 `run_result_option` 进入汇总 |

四组在领取及后续交互取证后仍存活，日志均无旧 `UnmanagedCallersOnly` 致命错误。本次样本可以核销升级后复测事项；未定位旧版底层根因或具体上游修复提交。

## 基线与方法

- 日期：2026-11-10；项目源码 `5fecce4`。Linux 游戏 `v0.111.0 / 41cef1ea`，Godot 4.5.1；与[迁移核验](2026-11-10-v0.111-migration-investigation.md)同一程序集及资源。
- Mod `0.87.0`、MCP `0.89.1`、schema `50`，依赖 RitsuLib `0.6.10 / compat/0.111.0`。运行 DLL SHA-256：`62bf4236cdcff15f60c33ac13cb0d2f3bb99524cabc733940505d4721ea761e4`。
- 原版实例通过 `--nomods` 跳过全部 Mod 初始化，日志确认该入口；Mod 对照仅加载本项目及 RitsuLib。四组各有独立用户目录与 IPC，禁用 Steam 初始化。
- 先在全新原版单人局沿地图进入第一房间，取得原生 `current_run.save`；复制其存档，将玩家 `current_hp/max_hp` 从 80/80 调整为 9/9。审计确认该存档副本只有这两个字段变化，正式存档不变。
- 载入四份副本后，用已核对的原生控制台命令 `ancient VAKUU DISTINGUISHED_CAPE` 或 `ancient VAKUU SERE_TALON` 进入馈赠。命令调用 `RunManager.EnterRoom` 并补写原生地图历史，见目标程序集的 `AncientConsoleCmd.Process`。
- 原版通过 X11 向对应窗口发送 Motion／ButtonPress／ButtonRelease，悬停与目标画面经截图核对；领取不经过项目动作入口。Mod 组通过真实 MCP 的 `get_observation`、`choose_ancient_option` 及后续工具执行，原生控制台仅用于布置房间。

原版窗口的 Wayland 缩放使普通指针定位不可靠，最终有效输入采用目标窗口事件。控制台中未成功的输入不作为领取证据；有效命令由游戏日志及最终选项共同确认。

## 回执与证据

Sere Talon 的关键回执：

```json
{
  "scene": "run_result",
  "screen": {"status": "visible", "view": "run_result"},
  "transition": {
    "stop_reason": "run_lost",
    "complete": true,
    "events": [
      {"relic": {"name": "Sere Talon"}, "type": "relic_obtained", "sequence": 1},
      {"target": {"id": 0, "kind": "player", "name": "The Ironclad"}, "before": 9, "after": 0, "type": "hp_changed", "sequence": 2},
      {"target": {"id": 0, "kind": "player", "name": "The Ironclad"}, "before": 9, "after": 1, "type": "max_hp_changed", "sequence": 3}
    ]
  }
}
```

证据目录为 `.tmp/2026-11-10-ancient-crash-recheck/`：

- `report.json`：四组结果、领取后的进程存活记录及 DLL 身份；`verification.json`：存档差异、结算续接断言及证据文件哈希。
- `baseline/`：原始与 9/9 存档副本；各组 `launch.json`、`stdout.log`、`game.log` 保存启动参数与游戏日志。
- `vanilla-cape/final.png`、`vanilla-talon/final.png`：原版领取后的地图及死亡汇总；各组 `after-run-save.json` 保存原生获得／死亡后的存档。
- `mod-cape/mcp.json`、`mod-talon/mcp.json`：完整 MCP 调用及回执；对应 `before.png/after.png` 保存领取前后画面。`mod-talon/summary.json/summary.png` 验证死亡后的汇总交互。

## 主动关闭及验证范围

领取、前进和死亡汇总取证完成后，对四个自有进程发送 SIGTERM。此时四组均出现 Godot `Unreferenced static string` 退出回收错误：两个斗篷实例最终以 134 退出，两个死亡实例未及时退出并以 SIGKILL 清理，见 `cleanup.json`。这些错误出现在主动终止之后，领取后的存活、交互和无旧致命错误证据已提前保存；退出问题未在本任务修复。

本次为同一初始存档的四组对照，各执行一次目标领取；房间由原生控制台构造，未自然推进完整对局到 Vakuu。未重建或安装 Mod、未改动产品代码，未重复与此复测无关的 Python／C# 全套检查。
