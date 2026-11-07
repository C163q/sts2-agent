# 结算选项修复后的典型返回

共20份实际MCP JSON，19份full、1份default，保留原样字段。[实施与验证](../2026-11-08-result-option-recovery-implementation.md)记录版本及边界；[原审阅样例](../2026-11-08-run-result-option-examples/README.md)保留旧基线。

| 场景 | 实际返回 |
| --- | --- |
| 战斗误用，具体拒绝并保留已有许可 | [full](wrong-room.full.json) |
| 当前页仍在展示 | [full](partial.full.json) |
| 按钮全部禁用 | [full](disabled.full.json) |
| 选项不存在 | [full](unknown-option.full.json) |
| 外部操作后的过期状态 | [full](stale.full.json) |
| 胜利首屏进入汇总 | [full](outcome-continue.full.json) |
| main_menu按钮先进入教程 | [full](summary-main-menu.full.json) |
| 教程继续进入时间线 | [full](tutorial.full.json) |
| 同一epoch:0揭晓前与揭晓后 | [Reveal](timeline-before-reveal.full.json)、[View](timeline-after-reveal.full.json) |
| 使用原ID重读及实际正文 | [动作full](reopen-epoch.full.json)、[详情full](reopened-epoch-details.full.json) |
| 原生下一章与翻页后正文 | [动作full](chapter-page.full.json)、[详情full](chapter-after-page.full.json) |
| 上一动作后直接确认解锁 | [default](direct-confirm.default.json) |
| 滚动中目标失效与随后要求观察 | [拒绝full](scroll-changed.full.json)、[后续full](after-scroll.full.json) |
| 原生详情导航夹具返回汇总 | [full](history-back.full.json) |
| 实际返回主菜单 | [full](timeline-to-menu.full.json) |
| 普通菜单时间线无本局关联 | [full](unowned-timeline.full.json) |

[manifest](manifest.json)记录工具、参数、原始报告行号、原生响应文件、运行DLL与样例SHA-256。样例全部来自四类通过的GUI运行，没有生成／裁剪返回。详情页返回由测试模式下的原生资源及有效菜单栈核验；正式游戏的View Run按钮仍禁用。
