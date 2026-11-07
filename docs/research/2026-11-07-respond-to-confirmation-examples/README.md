# respond_to_confirmation 典型返回

以下十二份是项目d4d1cef、Mod0.77.1与MCP0.79.1下实际MCP stdio返回的完整structuredContent，十一份full、一份default。六类场景与未验证范围见[开发核验](../2026-11-07-respond-to-confirmation-development-notes.md)。
确认放弃只作用于隔离测试局；非Trial来源弹窗由私有夹具创建，用于确认工具会拒绝。公开样本不包含来源绑定或私有核对数据。地图／牌组页面误用得到同样的通用错误，未为相同结构重复保存样本。
cancel与default样本无普通null字段，内容一致；confirm到达run_lost后保留无需玩法许可的结算查看工具。after-rejection与reopen-after-rejection展示当前许可恢复缺口。

参数、来源行（从0开始）、原始响应路径和SHA-256见[manifest](manifest.json)。

| 完整JSON | 场景 |
| --- | --- |
| [cancel.full.json](cancel.full.json) | 取消并回到Trial |
| [cancel.default.json](cancel.default.json) | 再次取消，default回执 |
| [confirm.full.json](confirm.full.json) | 确认放弃，进入失败结算 |
| [no-dialog.full.json](no-dialog.full.json) | 没有确认框时拒绝 |
| [after-rejection.full.json](after-rejection.full.json) | 拒绝后结束回合仍要求观察 |
| [already-closed.full.json](already-closed.full.json) | 取消后重复响应拒绝 |
| [reopen-after-rejection.full.json](reopen-after-rejection.full.json) | 重复响应拒绝后，合法重开仍要求观察 |
| [unowned.full.json](unowned.full.json) | 非Trial来源同类弹窗拒绝 |
| [replaced-popup.full.json](replaced-popup.full.json) | 同文案新弹窗使旧观察过期 |
| [cancel-fresh.full.json](cancel-fresh.full.json) | 读取新弹窗后成功取消 |
| [cold-call.full.json](cold-call.full.json) | 首次无许可响应拒绝 |
| [invalid-option.full.json](invalid-option.full.json) | 布尔option在MCP本地拒绝 |
