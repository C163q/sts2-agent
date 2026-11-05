# proceed 核验与设计建议

> 当前状态：现状核验完成，进入设计讨论。110项Python、15类GUI及23份完整返回已整理；总计180次MCP包含两次测试前提／断言失败的现场。待确认两项拒绝修复、旧终章断言修正及共用前置判断方案；尚未修改工具行为，本项尚未核销。

总流程见[工具清单](2026-11-02-mcp-tool-review.md)。源码、问题编号与详细证据见[开发核验](2026-11-06-proceed-development-notes.md)。

## 优先问题

| 问题 | 优先级与影响 | 建议 | 状态 |
| --- | --- | --- | --- |
| 明确点击前拒绝仍会要求重新观察 | 中：奖励被覆盖、宝箱未打开、火堆未操作、商品页未关闭、事件／对话未完成等拒绝后，下一次合法动作被 observation_required 拦截 | 首次点击前明确拒绝保留已有许可；已交互、状态过期、超时和未知结果仍要求观察 | 八条分支源码与对应GUI确认，待讨论修复 |
| 具体原因未公开且判断分散 | 中：缺少按钮、被覆盖、尚未完成、错误工具等情况均显示“操作不可用”；各场景分别检查，后续维护容易遗漏 | 集中当前应点击哪个按钮、为何不可用的判断，让执行与可用工具列表共用；提示相应的关闭、选择、对话或结算工具 | 实测确认，待讨论修复 |
| 旧终章脚本要求终态操作列表为空 | 低：当前终局可保留只读查看工具，旧脚本却断言 available_actions:[]，会把有效 run_won 判为失败 | 改为禁止玩法动作及连续玩法许可，保留旧脚本其余验证并实际回归 | 源码与实际响应对照确认；新审阅脚本已纠正自己的同类断言，旧脚本尚未修复 |

前两项属于已有[错误恢复与诊断待办](../development/TODO.md#当前工具审阅结束后处理)。已测正常前进没有发现重复点击、选择错误按钮、跳过建筑师对白或错误胜负停止原因的问题。

## 当前参数与返回

当前仅接受 preset:default/full，默认default。动作回执包含scene、screen、available_actions、transition；需要选择时另有selection的type/status，不附送整页观察。首次可用任何相关成功观察取得许可，不限于get_observation。

proceed 点击当前实际的房间跳过／前进按钮。选牌内的确认／跳过使用selection_option，对话中段使用advance_dialogue，结算页面使用run_result_option；它不是所有写着“继续”的按钮的通用入口。

## 各场景的实际含义

| 场景 | 当前行为与返回 | 核对范围 |
| --- | --- | --- |
| 普通战斗奖励 | Skip或Proceed打开地图；不会选路。普通终结奖励的最终放弃随原生离房处理 | 未领完、空列表GUI |
| 嵌套奖励 | 结束当前子奖励，返回父页面或继续原生父流程 | Calling Bell子奖励返回父奖励GUI |
| 宝箱 | 未开箱不能前进；开箱后可Skip遗物，领取后Proceed。Skip会提交原生放弃选择 | 未开／未领／已领GUI，放弃提交源码 |
| 火堆 | 处理选项后离开；帐篷还有可选项时也可按原生按钮离开 | 普通休息及Miniature Tent GUI |
| 商店 | 商品页关闭后离开；打开商品页时应先close_shop | 关闭／展开GUI |
| 普通事件 | 点击事件真正完成后生成的前进按钮；普通继续、离开或战斗选项仍用choose_event_option | Abyssal Baths完成GUI |
| 先古之民 | 先完成馈赠／对白，再使用原生前进 | 馈赠、后续对白及离开GUI |
| 占卜棋盘 | 结束占卜后才点击前进；尚有次数时不能直接结束 | 只用可见网格消耗次数后前进GUI，无后台物品定位 |
| Boss奖励 | 可进入下一幕；第三幕最后Boss进入建筑师 | 第一幕换幕、第三幕进入终章GUI；双Boss等变体源码 |
| 建筑师 | 对话中段须advance_dialogue，最后proceed进入结算并返回run_won | 独立全新进度GUI |
| 战斗返回父事件 | 某些奖励页的前进会恢复父事件，可能继续其效果 | 恢复分支源码。所测Battleworn Dummy已在战斗结束时自动恢复，proceed随后离开事件 |
| 结算页 | 使用run_result_option；proceed会被拒绝 | GUI |

打开地图和前往下一节点是不同操作。complete:true表示已到达stop_reason所述边界；嵌套奖励返回父页面和建筑师终局的含义不同，应结合scene/screen及可用操作判断。

建筑师终局的available_actions可包含只读工具，例如inspect_run_result；这不会给出连续玩法许可。其HP归零事件与run_won按现有结算契约保留。

## 典型完整返回

[23份JSON与调用参数](2026-11-06-proceed-examples/README.md)包含22份full、一份default。建议先看：

- [奖励Skip](2026-11-06-proceed-examples/reward-skip.full.json)、[嵌套返回](2026-11-06-proceed-examples/nested-return.full.json)、[宝箱Skip](2026-11-06-proceed-examples/treasure-skip.full.json)。
- [帐篷剩余选项](2026-11-06-proceed-examples/tent.full.json)、[商店](2026-11-06-proceed-examples/shop.full.json)、[事件](2026-11-06-proceed-examples/event.full.json)、[占卜](2026-11-06-proceed-examples/divination.full.json)。
- [进入下一幕](2026-11-06-proceed-examples/next-act.full.json)、[进入建筑师](2026-11-06-proceed-examples/architect-entry.full.json)、[run_won](2026-11-06-proceed-examples/run-won.full.json)。
- [商店拒绝](2026-11-06-proceed-examples/shop-rejected.full.json)及[随后合法关闭仍被要求观察](2026-11-06-proceed-examples/after-rejection.full.json)。

## 参数与重构建议

建议维持零操作参数和default/full；回执已经精简，无需新增summary或场景参数。按钮含义随原生场景变化是正常行为，当前状态令牌及按钮合法性检查负责防止误用。

需要集中的是八条分支的前置判断与明确拒绝，保留各场景自己的原生后续流程、等待条件和事件记录。建议先形成单一前进入口，统一选择实际按钮及固定原因；现有场景动作可继续复用。覆盖奖励、选牌、地图、商品页、未完成对白及结算页面须有准确提示。

双Boss、教程、真实超时、对局中途退出、多人及全部事件／遗物组合未穷举；奖励前进触发父事件恢复未新增独立GUI样本。验证限制及两次测试修正的说明见开发记录。
