# 查看工具错误与动作许可修复

> 当前状态：已完成，共 4 项，已完成 4 项。TARGET-01／02、四工具同类路径与出牌前置拒绝已修复，521 项 Python、60 项纯 C#、构建及两组隔离游戏验证通过，文档已同步，inspect_targets 已按约定范围核销。其他工具的完整错误审阅仍留在用户 TODO；正式游戏 Mod 未安装。暂无阻塞。

## 范围与定稿

依据 [inspect_targets 审阅](2026-11-03-inspect-targets-review.md)的 TARGET-01／02，修复 inspect_targets，并回查已审阅的 get_observation、inspect_ui、inspect_hand。inspect_targets 继续只有 default/full，不增加 summary，不改变费用不足时的范围或原生指示语义。用户已授权本轮实施；其余工具的完整错误审阅仍留在用户 TODO，不以这次共用层修复宣称全部完成。

核对基线为提交 `31c6774`，Mod 0.51.0、MCP 0.52.0、观察 schema 34；目标游戏与依赖沿用 [inspect_targets 的证据基线](2026-11-03-inspect-targets-review.md#核对基线与证据)。本次不新增游戏 API，优先使用现有失败分支及原生动作流程。

### 根因与边界

1. `player_output.player_result` 把所有原生 message 替换成按 code 查到的模板。四个工具的明确不可用原因因此丢失；异常详情原本也靠这一层隔离，不能无条件透传所有 message。
2. `GameTools._inspect` 在参数校验前清除旧令牌，get_observation 自己再实现一遍清除逻辑；inspect_hand／inspect_ui 的本地参数检查却在调用共用层前返回，造成不一致。
3. `_action` 不区分未提交与结果未知的失败。仅凭 illegal_action 不能判断所有动作是否已经改变 UI；牌组／地图等入口甚至可能在打开／切换页面后失败，不能全局恢复旧令牌。
4. SERVER_INSTRUCTIONS 要求任何错误后先观察，与修复后的恢复契约冲突；已改为遵循 error.recovery，choose_legal_action 允许按已有信息决策，按需查看。

### 错误输出

- 提取 `src/sts2_mcp/output/error_output.py`，负责当前公开错误结构与本地参数错误，player_result 复用它，不改成功玩法投影。
- 原生必须以 `public_message` 显式标记可公开的固定拒绝说明，且仅在 illegal_action／invalid_request 时采用；普通 message 不透传。game_error、transport_error、timeout、未知错误及原生解析异常继续使用固定模板，即使夹带 public_message 也不公开。其他未知字段与控制标记不进入 MCP JSON。
- 四个工具本地参数错误指出相关字段及允许的形状／范围；preset 错误由公共包装层统一描述，不回显任意输入内容。
- 成功查询的 reason 保持原契约；不把费用不足变成空 targets，也不删除 target_type。

### 许可与恢复

- 四个纯读取操作（原生 get_state／inspect_targets／inspect_ui／inspect_hand）发送前参数错误保留原许可；收到明确 invalid_request／illegal_action／expired_request 时同样保留原许可。成功仍使用完整校验后的新令牌。
- 保留只是沿用已经观察过的状态，不由错误生成新许可。若外部使状态改变，后续动作仍由 Mod 拒绝 stale_state，不自动读取或重试。
- 坏响应、传输失败、超时、游戏异常、取消、控制器冲突等仍清除许可；不将结果未知当作明确未执行。
- play_card 的原生前置拒绝增加内部 `action_submitted:false` 标记，仅在调用原生提交及改变 UI 之前提供；Python 只有在该标记明确为布尔 false、错误码为 invalid_request／illegal_action 且已有令牌时恢复原许可。缺少标记的旧 Mod 或其他动作失败继续沿用保守规则。
- play_card 分别反馈缺少／多余目标、不在当前范围、费用／卡牌条件不满足。费用原因复用 TargetInspection.Reason；不附送内部阻止者身份或未来结算。
- 已保留许可的 illegal_action／expired_request 改为 choose_legal_action 恢复提示，不再固定要求先观察；参数错误仍为 correct_request。首次失败、stale_state 和未知结果继续引导读取或检查连接。
- 并发操作仍串行。排队动作不能借用稍后才产生的新观察；不自动补发动作。

## 实施步骤

### 1. 回归测试

- [x] 新增 `tests/python/test_inspection_errors.py`：四个工具的参数与原生拒绝保留原许可、首次失败不授权、异常清除、外部变更仍 stale_state、并发／取消，以及安全错误输出。
- [x] 覆盖 play_card 明确未提交与未知结果的区别、0 能量拒绝后直接 end_turn，以及缺失／伪造类型的标记不恢复许可。
- [x] 运行新测试，确认旧实现确实因原因丢失与许可清除失败；保存输出于 `.tmp/2026-11-03-inspection-error-recovery/`。

### 2. 共用修复

- [x] 提取 error_output；更新 game_tools、presets、四工具参数校验与 CardPlayRequest／FileMailbox 的明确拒绝标记，保持成功输出及目标语义。
- [x] 新测试通过，调整旧测试中已被新契约替代的“参数错误必须清除许可”断言；不放宽坏响应、stale_state、超时或取消测试。

### 3. 集成与游戏验证

- [x] 最终全量 Python 521 项、现有纯 C# 检查 60 项与构建通过，包含独立审查建议的补充测试。
- [x] 新增隔离 GUI 验证：四工具完整 MCP 往返、参数失败和错误恢复、0 能量 play_card 后 end_turn；记录返回 JSON、进程清理和未验证范围，不操作正式存档。

### 4. 文档与交付

- [x] 更新 MCP 许可／错误语义、相关接口说明和版本；更新 inspect_targets 审阅与总清单，按实际范围说明未取样分支，不凭错误修复核销未验证能力。
- [x] 用户 TODO 保留其他工具的后续范围，并交叉链接本次已处理部分；校验文档与示例、检查差异，以英文 Conventional Commit 交付。

## 四工具复查结果

| 工具 | 原问题与已处理内容 | 验证边界 |
| --- | --- | --- |
| get_observation | 本地参数错误无说明且清除许可；改为字段说明及保留原许可，并复用 _inspect 读取路径，消除另一份许可管理 | GUI 验证非法字段后仍可提交原生请求；读取阶段坏响应、明确拒绝和异常分别由 Python 回归覆盖，未在游戏中人为制造 Observe 异常 |
| inspect_ui | 本地参数错误原本已保留许可，但说明笼统；实际拒绝仍丢弃说明并清除许可。现统一处理 | GUI 验证非法 sources 与覆盖页的正常帮助读取；原生 UI 不可读分支由 Python 边界测试，未新增 GUI 隐藏 UI 实验 |
| inspect_hand | 本地参数错误原本已保留许可；补字段说明，并修复读取被拒后的说明与许可 | GUI 验证非法 card_ids，以及牌组覆盖导致的原生读取拒绝；不把覆盖读取失败当作空手牌 |
| inspect_targets | 参数错误与原生拒绝均清除许可且说明丢失；修复定位、preset 与目标参数说明，保留明确拒绝前的许可 | GUI 验证不存在手牌、空／越界药水槽、覆盖战斗不可查询、缺少／多余／无效出牌目标、零能量拒绝后结束回合 |

四工具所有预设走同一错误路径；default、full 与 summary 不删除或压缩顶层错误。inspect_targets 不增加 summary，卡牌与药水的成功目标结构、reason 和指示范围没有改变。

## 验证记录

证据根目录为不入库的 `.tmp/2026-11-03-inspection-error-recovery/`。

- `red.log`：修复前新增 11 项测试出现 24 个失败子项，直接复现原因丢失、许可清除及下一请求被挡在 MCP 的问题。
- `python-first.log`：第一次全量 518 项出现 27 个失败子项。其中部分是已替换的旧许可契约；其余私有错误隔离断言证明普通 message 不能直接转发。因此增加 public_message 显式许可，没有删除这些隔离测试。
- `python-second.log`：518 项通过。最终补充原生 invalid_request 未提交恢复、异常 public_message 忽略、控制器冲突等检查；`python-final.log` 为 521 项通过，命令为 `timeout 120s .tmp/mcp-venv/bin/python -m unittest discover -s tests -t . -p 'test_*.py'`。
- `build.log`：`dotnet build Sts2Agent.sln -m:1 ... --no-restore` 成功，0 警告、0 错误；`csharp.log` 的纯 C# 检查 60 项通过。构建启动时有 .NET workload 校验提示，不影响项目构建。
- GUI 使用 [inspection_errors 清单](../../tests/game/data/gui_suite_inspection_errors.json)和[验证器](../../tests/game/verifiers/verify_inspection_errors.py)。`gui/report.json` 为 passed：一个独立游戏进程、两个独立测试局；energy 8 次 MCP 调用，basic 27 次，共 35 次。各局只成功结束一次回合，均到达下一玩家回合。
- 自有游戏 PID 15646 已关闭；构建与隔离运行时 DLL SHA-256 为 `3dbcd6fd019826352f48f7265aea72372f4a8049c69b8ad2cf226de0fb464bc1`。没有更新正式 Steam Mod。
- 独立只读审查使用 gpt-6.1-sol/high，无已确认正确性、并发或隐私缺陷；提出的两项非阻塞测试已补充。审阅者用系统 Python 尝试测试时因缺少 anyio/mcp 未执行，不计作通过证据；父代理的上述测试使用项目虚拟环境。
- 最终仅再修正 SERVER_INSTRUCTIONS 文案，没有改动许可或游戏逻辑；`instructions-final.log` 通过真实 stdio 握手确认新说明、MCP 版本与关闭截图后的 42 个工具。检查助手初次遗漏必填 ipc-dir，第二次继承本机截图配置而错误断言工具数；分别保留在 instructions.log／instructions-corrected.log，补齐独立 IPC 和显式配置后通过，未把助手错误当作项目故障。

### 真实 MCP 错误示例

以下逐字取自 `gui/energy/verify/evidence.json` 中 play_card 的公开返回；随后直接调用 end_turn，成功返回 player_ready，没有插入观察或查看：

```json
{
  "error": {
    "code": "illegal_action",
    "message": "Not enough Energy.",
    "recovery": "choose_legal_action"
  }
}
```

以下取自 `gui/basic/verify/evidence.json` 的 inspect_hand 参数拒绝；后续实际到达原生 play_card 拒绝分支，而非被 observation_required 挡在 MCP：

```json
{
  "error": {
    "code": "invalid_request",
    "message": "card_ids must be an array of integer hand IDs from 0 to 2147483647.",
    "recovery": "correct_request"
  }
}
```

### 未验证与留待后续范围

未新增 AnyPlayer／AllAllies／Osty 卡牌分支、真正多人、第三方目标类型或全部卡牌条件的 GUI 验证；不改变原审阅记录的源码核对边界。四工具的原生 invalid_request／expired_request、游戏异常、超时、取消和坏响应由 Python 协议边界测试覆盖，没有逐一在实际游戏里注入。未安装到正式游戏，也没有宣称其他工具的错误与恢复已全面核验；剩余范围仍见[用户 TODO](../development/TODO.md#当前工具审阅结束后处理)。
