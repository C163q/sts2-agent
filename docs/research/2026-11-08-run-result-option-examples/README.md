# run_result_option 典型实际返回

对应代码基线f033e35，参数和待确认事项见[审阅建议](../2026-11-08-run-result-option-review.md)，验证及限制见[开发核验](../2026-11-08-run-result-option-development-notes.md)。共15份原样MCP JSON，14份full、1份default；没有生成或裁剪示例。错误仍反映审阅基线，不代表整改后的目标输出。

| 场景 | 实际返回 |
| --- | --- |
| 胜利首屏continue进入汇总 | [full](outcome-to-summary.full.json) |
| 汇总main_menu先进入时间线教程 | [full](summary-to-tutorial.full.json) |
| 教程continue进入时间线 | [full](tutorial-to-timeline.full.json) |
| 时间线揭晓章节 | [full](timeline-to-epoch.full.json) |
| 章节继续进入解锁页 | [full](epoch-to-unlock.full.json) |
| 不再读取，直接确认解锁 | [default](unlock-confirm.default.json) |
| 时间线back实际返回主菜单 | [full](timeline-to-menu.full.json) |
| 战斗中误调用 | [full](wrong-room.full.json) |
| 上述拒绝后end_turn要求观察 | [full](wrong-room-next-action.full.json) |
| 缺少option_id | [full](invalid-arguments.full.json) |
| 重新打开已揭晓章节被拒绝 | [full](completed-epoch.full.json) |
| 外部操作后旧状态被拒绝 | [full](stale.full.json) |
| 普通历史页夹具返回崩溃，结果未知 | [full](history-back-timeout.full.json) |
| 主菜单没有本局结算 | [full](menu.full.json) |
| 普通菜单时间线没有本局关联 | [full](unowned-timeline.full.json) |

全部来源在[manifest](manifest.json)中，含原始报告、从0开始的行号、参数、原生文件及样例SHA-256。部分单次调用来自随后因脚本预期错误而停止的运行；成功返回只证明该调用，不将整份失败报告计为通过。历史页样例是夹具路径的失败，当前原版View Run入口禁用，不能外推为正常入口已复现崩溃。

同一成功回执中full/default没有需要区别的普通null，结构相同。default确认样例是在上一成功动作后直接调用，期间没有get_observation或inspect_run_result。
