# Trial 确认响应恢复实施记录

> 当前状态：已完成，共1项，已完成1项；实现、验收及独立审阅完成，长期断言缺口已补齐，已归档并合入main，无剩余步骤或阻塞。

定稿见[响应审阅](2026-11-07-respond-to-confirmation-review.md#输出定稿)，步骤见[实施计划](../superpowers/plans/2026-11-07-confirmation-response-recovery.md)。原错误与十二份旧JSON见[开发核验](2026-11-07-respond-to-confirmation-development-notes.md)。

## 行为与职责

- option仍仅confirm/cancel，default/full；来源绑定、模态实例代次与原生按钮流程保留。取消返回事件，确认等待原生放弃完成、返回run_lost及实际结算查看工具，不自动推进结算。
- 无受支持确认框、未知来源、地图／牌组覆盖、等待及按钮不可交互给具体原因。当前状态匹配且明确点击前拒绝保留已有许可；冷调用、过期、已交互、未知／坏响应和矛盾保证不恢复。
- 页面／动作／按钮检查集中于EventConfirmation，Ready独立；执行、options.enabled及available_actions共用，至少一个按钮可交互才提供响应工具。两按钮均禁用的可见确认框仍能读取。
- verify_confirmation.py迁移到共享IPC／ensure_run流程，支持套件同一测试局及独立隔离实例；使用精简回执、事件摘要及当前终态工具，不依赖截图工具。原场景、替换／未知来源及私有核对保留。

[EventConfirmation](../../src/Sts2Agent/Actions/EventConfirmation.cs)新增PageUnavailableReason、ActionUnavailableReason及ButtonUnavailableReason，Clickable复用单按钮检查；[适配器](../../src/Sts2Agent/Adapter/GameAdapter.Confirmation.cs)仅在点击前使用RejectedBeforeSubmission，[注册](../../src/sts2_mcp/tool_registry.py)开启已有unsubmitted_rejection_unchanged策略。

私有set_test_confirmation_buttons只在test_mode、Trial场景及本地玩家存在时执行，严格接受两个bool，复用目标版本NClickableControl.SetEnabled；在Testing.TestRequestBeforeCapture中处理，与既有UI夹具相同，未加入公共参数白名单或MCP目录。两个禁用按钮的旧列表矛盾通过该夹具复现；夹具状态不代表正常原生流程已经出现同类禁用。

## 基线与证据

- 基于70d6655；Linux游戏v0.107.1/release59260271，RitsuLib0.6.10、Godot4.5.1；原生及程序集证据见开发核验，未更换目标。
- Mod0.77.2、MCP0.79.2，schema45不变；旧Mod缺少未提交保证时仍要求观察。
- 最终构建及隔离运行时DLL均为b5096c3ebd44c7f814aeac561c222327ba742e6ec6706e9a0d4312fb9eda41ad。证据根`.tmp/2026-11-07-confirmation-response-recovery/`；没有正式安装或推送。

## 验证

| 检查 | 结果与证据 |
| --- | --- |
| Python RED | 新5项中full/default两处恢复断言失败，0.062秒；python-red.log |
| 初次夹具 | 仅夹具构建5.62秒、零警告错误；45fda904…6ee。入口放在通用参数检查后，GUI请求被“本操作不接受参数”拒绝，18.658853201秒；PID30428已退出，gui-red/report.json；不能算作公共行为RED |
| 有效GUI RED | 修正夹具入口后，仅夹具中间DLL27c9d496…6c42；两个禁用按钮仍列respond_to_confirmation，MCP将矛盾观察判为transport_error；19.098684643秒，PID30952已退出，gui-red-wired/report.json |
| Python GREEN | 新5项通过，0.056秒；python-green.log |
| 完整Python | 796项通过，38.433秒；python-full.log |
| 审阅补充回归 | 新2项：空工具列表、混入玩法动作及错误场景三个变异先被旧断言漏过，0.001秒；补齐后2项通过，0.001秒；review-python-red-valid／green-valid.log |
| 最终完整Python | 798项通过，39.751秒；python-final-fixed.log |
| C# | 145项通过；csharp.log |
| 最终构建 | 3.86秒，零警告／错误；build.log |

为有效RED，三个产品文件补丁保存后暂时撤回，仅用修正接线的测试夹具构建检查旧公共行为；RED结束且进程退出后重新应用，再构建最终DLL。中间构建及失败均保留，未用中间DLL代替最终验收。

Python在原生通信边界使用替身，测试真实GameTools与会话策略。明确保证后可直接取消并重开；缺少保证、仅视图保证、过期／异常、已提交／已交互、矛盾证据和坏成功响应均撤销许可。首次调用不发送动作，本地非法参数保留已有许可。

## GUI与未验证范围

专项为无确认框、取消、替换、未知来源、地图／牌组覆盖、确认放弃与按钮状态七类；补充原生门控及事件进入确认框两类回归。原始读取不刷新MCP许可，拒绝前后核对令牌、未提交与未交互证明，再直接执行合法操作。

按钮场景先禁用两个按钮，读取确认框并确认没有可响应工具；再仅禁用confirm，错误保留许可，随后直接cancel。确认放弃核对IsAbandoned／RunLost、任务完成及HP0；私有真值只作验证，不进入公开JSON。

最终九类在同一进程一次通过，165.307071069秒，gui/report.json；PID32353已退出，全部加载最终b5096c3e…41ad。私有门控检查84项操作，在test_mode关闭和suite／场景关闭两种条件下均拒绝；新按钮入口包含在内。初次接线失败与有效RED保留。

独立启动分支另通过，43.687635437秒，standalone/report.json：自有实例先停在主菜单，配置Trial后清除复用标记，由迁移后的验证器调用ensure_run创建新测试局并完成cancel场景；启动前run_id为空、之后为同一进程的新run_id。该模式也由GameSession管理启动器和清理，未连接默认IPC或正式游戏；PID33302已退出。四个自有GUI进程均已退出，独立入口与套件均使用同一最终DLL。

## 实际返回

[十七份修复后JSON](2026-11-07-confirmation-response-fixed-examples/README.md)包括十六份full、一份default，均来自最终DLL的实际MCP；原十二份JSON另存保留。每份参数、源报告行及SHA-256独立核对。

取消后重复响应的完整错误为：

```json
{
  "error": {
    "code": "illegal_action",
    "message": "No supported Trial confirmation is open. Use the current screen's available actions.",
    "recovery": "choose_legal_action"
  }
}
```

随后直接选择Trial的DoubleDown成功。两按钮禁用观察保留标题／正文／options及两个enabled:false，available_actions为空；只禁用confirm时仍提供respond_to_confirmation，错误后可直接cancel。终态仍保留原生失败及结算查看工具，未将确认放弃当作普通完成。

verify_delivery.py核对已运行日志、RED／GREEN、三批GUI、进程退出、DLL、版本、十七份JSON及相对链接，不重复构建。

## 独立审阅与补齐验证

独立只读审阅范围70d6655..f32e88b，原分级Critical0、Important0、Minor1，结论可合入。未发现产品缺陷；唯一发现是长期GUI验证器确认分支缺少终态查看工具断言，当前样本与交付检查已有该证据。

最终处理将此项按已确认的“迁移旧验证器终态断言”视为需要补齐的交付验证缺口，在唯一修复回合中完成：从既有run_lost检查抽出实际GUI使用的validate_confirmation_outcome，以已保存的真实回执作输入；空列表、混入玩法动作及错误场景三个变异先失败，再增加结算场景、inspect_run_result存在及无玩法动作断言。未修改Mod／MCP生产代码或重新构建。

首次抽取函数的缩进错误导致review-python-red／green导入失败，不计为有效RED；python-final.log为797项、1个导入错误，gui-review-confirm也在导入处失败，14.518266834秒，PID34821已退出。这些失败全部保留。修正缩进并还原旧断言后得到上述有效RED→GREEN；最终798项通过，确认GUI单场复查25.399057854秒通过，PID36095已退出、同一最终DLL。没有重复九类套件或独立启动场景，没有第二次独立审阅。

裁决按记录顺序为：

1. 终态断言属于已确认迁移内容，需补齐后交付；若此判断过严，代价仅是额外回归验证时间。
2. 多人及其他来源弹窗的自动响应保持规格范围，未知来源拒绝已有实测；若范围判断不符，其他来源仍需人工处理。
3. shell参数入口及完全不使用suite启动器的方式不作已实测宣称；已验证自有GameSession管理的非复用分支，纯CLI或非suite封装仍可能需要单独修正。

没有剩余暂缓项；审阅摘要见证据根final-review.md。初始四个及审阅复查两个自有GUI进程均已退出，最终产品DLL保持b5096c3e…41ad。

实现f32e88b及终态回归补齐a57affd已快进合入main，临时分支fix/confirmation-response-recovery已删除，工具清单核销为38/44。任务工作目录5份文件复制并逐份校验SHA-256后归档至证据根inline-workspace，原件已清理，兄弟目录未改；既有TODO仅同步已覆盖工具，未新增待办。未正式安装Mod或推送。

## 未验证范围

真正忙碌中途、任意人工并发切页、异常离屏／隐藏、多人与第三方弹窗未新增GUI验证；源码中的来源、就绪与生命周期检查保持。禁用状态仅由测试夹具覆盖，不据此宣称自然原生流程已复现该状态。
