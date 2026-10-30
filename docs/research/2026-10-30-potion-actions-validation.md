# 药水动作接入验证

验证日期：2026-10-30。游戏及依赖基线见 [源码依据](2026-10-30-potion-actions.md)，现行接口见 [使用与丢弃药水](../development/potion-actions.md)。交付版本为 Mod `0.16.0`、MCP server `0.13.0`、20 个工具。

## 验证结果

| 检查 | 结果与范围 |
| --- | --- |
| Python | 147 项通过，包含新药水参数、混合定位拒绝、响应过滤、目标类型、事件、一次许可及原有 stdio 回归 |
| C# 检查 | 8 项通过，覆盖现有交互边界与事件缓冲；不替代真实游戏验证 |
| 构建 | .NET 9 构建通过，0 警告、0 错误 |
| 原生药水场景 | 下列 25 个隔离实例通过 |
| 图形与真实 stdio | 4 个场景通过；20 个工具、紧凑文本与结构化返回一致、观察许可、错误拒绝及选择切换正常 |
| 旧出牌 | `basic/discovery/random` 通过，覆盖指定目标、自用、选择与随机数不变性 |
| 旧结束回合 | 真实 stdio 验证回合 1→2、事件、非法/缺失/重复/旧令牌拒绝及读回一致性通过 |
| 独立审阅 | 未发现 Critical、Important 或 Minor 问题；审阅未代替运行验证 |

原生场景：

- `basic`：火焰药水、格挡药水、自动药水拒绝及丢弃，空槽、越界、错误目标和参数拒绝。
- `fruit_combat`、`noncombat_event/rest/shop/map/reward`：战斗内及五类战斗外页面的果汁、血瓶和丢弃；战斗外目标无需指定。
- `skill/attack/power/colorless/memories/gamblers`：小型候选、弃牌堆及手牌选择；药水动作停在选择边界，原有选择工具继续；眼睛查看期间不提供药水动作。
- `merchant/merchant_map/merchant_inventory`：实际商人目标与加金币，地图、库存遮挡时拒绝投掷。
- `aoe/victory/death/fairy_rescue`：群体伤害、原生胜负、瓶中精灵自动救命及两瓶药水的公开使用事件。
- `blocked/cancel/replace/unhittable/entropic`：禁止移除、原生取消、同槽同名换瓶的旧令牌拒绝、不可命中目标过滤、随机补满槽位。

图形与真实 stdio 场景为 `basic/noncombat_reward/skill/merchant`，已复核截图。奖励页使用实际非空药水奖励，断言奖励按钮保持可见，验证满背包时使用和丢弃；不能用会自动关闭的空奖励页证明该范围。选择场景验证 `choice_required`、眼睛切换、只读药水详情、禁止普通动作及返回后选牌。商人点击区自身透明，但子图像正常可见，读取按实际绘制与遮挡判断。

## 证据与限制

本地证据保存在不纳入 Git 的 `.tmp/2026-10-30-potions/`：各场景 JSON 与游戏日志、`stdio/` 的协议结果和截图、`play-regression/` 的旧出牌结果、`mcp-regression.json`、`python-final.log`、`build-final.log`、`review.md`。验证入口在 [药水指南](../development/potion-actions.md#验证)；状态配置仅在独立测试模式开启，不是 MCP 工具，不作用于正式对局。

查询前后核对了状态令牌、随机目标计数、瞄准状态、队列及槽位不变。动画导致的 `stale_state` 只表示明确未提交；验证脚本重新观察并核对相同决定后才再次请求，不重发未知结果动作。

未验证真正多人、全部药水与遗物/power 组合、第三方自定义目标、假商人事件的完整交互、声音及其他游戏版本。本轮图形验证使用英语 UI，中文 UI 未在本次重新逐项验证。无头实例仍有已知 FMOD、虚拟渲染及 RitsuLib 运行环境警告；不将其描述为无运行警告。

安装只替换本项目的 DLL 与清单，保留 Steam 创意工坊管理的 RitsuLib；构建文件与隔离运行时文件核对一致。安装后的磁盘文件需要完整重启游戏才能加载，MCP 客户端须重新连接才能发现新工具。
