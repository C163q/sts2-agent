# Trial 确认响应修复后典型返回

以下十七份均为最终DLL下实际MCP stdio的完整structuredContent，十六份full、一份default。基线和验证范围见[实施记录](../2026-11-07-confirmation-response-recovery-implementation.md)。
两份按钮状态观察来自仅测试模式的原生按钮禁用夹具，用来验证可用操作及单项enabled一致；不代表正常原生流程已出现该状态。确认放弃仅作用于隔离测试局。
明确拒绝保留已有许可，合法后续取消、重开或结束回合直接执行。替换弹窗仍要求重新读取；未知来源弹窗仍需人工处理。

参数、来源行（从0开始）、原始响应路径及SHA-256见[manifest](manifest.json)。

| 完整JSON | 场景 |
| --- | --- |
| [cancel.full.json](cancel.full.json) | 取消并返回事件 |
| [cancel.default.json](cancel.default.json) | default取消回执 |
| [confirm.full.json](confirm.full.json) | 确认放弃并返回失败结算 |
| [no-dialog.full.json](no-dialog.full.json) | 没有确认框时给具体原因 |
| [end-turn-after-rejection.full.json](end-turn-after-rejection.full.json) | 拒绝后直接结束回合 |
| [already-closed.full.json](already-closed.full.json) | 取消后重复响应保留已有许可 |
| [reopen-after-rejection.full.json](reopen-after-rejection.full.json) | 拒绝后直接重开Trial确认框 |
| [unowned.full.json](unowned.full.json) | 未知来源提示人工处理 |
| [map-covered.full.json](map-covered.full.json) | 地图页面提示close_map |
| [deck-covered.full.json](deck-covered.full.json) | 牌组页面提示close_card_view |
| [replaced-popup.full.json](replaced-popup.full.json) | 替换弹窗后旧观察过期 |
| [cancel-fresh.full.json](cancel-fresh.full.json) | 重新读取后取消当前弹窗 |
| [both-disabled.full.json](both-disabled.full.json) | 两按钮均禁用时仍可读取，不提供响应工具 |
| [both-disabled-rejection.full.json](both-disabled-rejection.full.json) | 两按钮均不可用的具体拒绝 |
| [confirm-disabled.full.json](confirm-disabled.full.json) | 仅confirm禁用时仍允许响应cancel |
| [disabled-confirm.full.json](disabled-confirm.full.json) | 请求禁用按钮时给具体原因 |
| [cancel-after-disabled.full.json](cancel-after-disabled.full.json) | 拒绝禁用confirm后直接cancel |
