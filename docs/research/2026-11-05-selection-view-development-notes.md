# set_selection_view 开发核验记录

> 当前状态：修复、输出精简及一次独立审查完成，已核销并合入 main，见[实施记录](2026-11-05-selection-view-results-implementation.md)。下文 8 个场景、62 项 Python 及 6 份 full 样例保留为修复前基线，不作为当前接口契约。用户说明见[审阅与定稿](2026-11-05-selection-view-review.md)。

## 已定位问题

| 编号 | 优先级 | 依据与影响 | 状态 |
| --- | --- | --- | --- |
| VIEW-01 | 中；恢复 | 审阅基线在不支持选择、CanPeek 为 false 时返回普通错误，未登记 `unchanged_view_rejections`；GameSession 无法仅凭 illegal_action 判断未交互 | 已修复验证，见实施记录 |
| VIEW-02 | 中；原因 | 审阅基线没有公开固定原因，CanPeek 把覆盖、无眼睛、隐藏及禁用合并 | 已提供固定诊断并验证；不公开任意异常 Message |

## 基线与原生依据

- 项目提交 `35f9aec`，Mod 0.66.1、MCP 0.68.1、schema 40；现行基线统一见[README](../../README.md#当前版本与前提)。
- Linux 游戏 v0.107.1、release build 59260271；安装目录相对程序集 `data_sts2_linuxbsd_x86_64/sts2.dll` 重新计算 SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。
- RitsuLib 0.6.10；本工具使用原生 NPeekButton，不新增 RitsuLib API。构建目录与隔离运行时 DLL 均为 `50de6a77d5866847bf4fcd7c8e72d932f242bbb970b8628f86e378fc60c9ec38`，没有重新构建或正式安装。
- 原生源码证据在 `.tmp/2026-11-05-selection-view-review/source/`：NPeekButton 重新定向反编译，其余原生选择页与手牌从同一程序集哈希的已核对证据复制；逐文件哈希见 manifest.json。

| 代码／成员 | 已核对行为 |
| --- | --- |
| `NPeekButton._Ready/OnDisable` | 战斗未进行时禁用；禁用同时隐藏按钮 |
| `NPeekButton.SetPeeking` | 同值立即返回；切换原生 backstop，保存并隐藏原本可见的 targets，返回时恢复这些对象；发出 Toggled |
| `NPeekButton.OnOverlayStackChanged` | 覆盖页移除后按原查看状态重新处理 backstop，不自行完成选择 |
| `NCardGridSelectionScreen.SetPeekButtonTargets` | 网格和各页面特定控件共同作为隐藏目标；关闭页面时原生复位 peeking |
| `NPlayerHand.OnPeekButtonToggled` | 查看战场时禁用确认、更新卡牌显示及控制器导航；返回时刷新确认可用性，不清空已选集合 |
| `CardSelection.CanPeek` | 支持、暴露、原生眼睛存在且启用并位于屏幕；用于当前 available_actions 与实际请求前置检查。固定输入按钮的可见性检查不等同于被取消的可浏览内容截断 |
| `SelectionRequest` | 仅当目标不同才 UiChanged + ForceClick；之后等待观察，检查相同选择实例、仍暴露且目标视图相符。重复目标不点击，但仍要求 CanPeek |
| `SettledObservation` | 观察连续 250 毫秒稳定或至 2 秒截止，等待逐帧推进；不是战斗结算等待，不产生 transition |
| `ToolSpec/GameSession` | view 类型，无初始许可要求，成功经完整观察校验后刷新许可；返回当前完整观察，普通 default 过滤在统一投影执行 |

## 定稿接入的实现依据

前置拒绝应使用 view 专用的 `ui_unchanged:true` 及 `unchanged_view_rejections`；不能机械套用按钮动作的 action_submitted 登记，因为该查看工具不传动作许可令牌。只保留原来已有的许可，首次拒绝不生成许可；切换后选择改变、异常和执行证据矛盾不能标记为未交互。

视图切换允许 `battlefield` 和 `visible` 两种选择状态，不能直接套用拒绝 battlefield 的候选／按钮检查。可新增聚焦眼睛的前置判断或独立适配方法，继续让 AvailableTools 和执行共享相同可用条件。非战斗／结果页仍按实际原生入口判断，不以直接改 peeking 状态替代按钮。

紧凑返回在完整解码之后复用 `actions_only_result`，不改变底层文件完整状态或许可刷新；default/full 的公共空值语义仍由统一入口处理。最终输出见[设计定稿](2026-11-05-selection-view-review.md#设计定稿)，这里保留接入依据，不再独立定义公共字段。

## 验证与边界

原始目录 `.tmp/2026-11-05-selection-view-review/`；专项清单 [selection_view_review](../../tests/game/data/gui_suite_selection_view_review.json)，验证器 [verify_selection_view_review.py](../../tests/game/verifiers/verify_selection_view_review.py)。场景选择基于不同原生控件和恢复分支，不追求每个选择来源各一份 JSON。

典型切换记录包含公开返回及另列的原生执行证据，用于证明实际切换有交互、重复目标没有点击；后者不进入公开示例。before/after 比较使用同一种 get_observation 静态格式，避免把 inspect_selection 的悬停聚合差异误当作视图改变。

| 证据 | 实际结果 |
| --- | --- |
| `python.log` | gui_suite、selection、session_policy、default_presets 共 62 项通过，2.332 秒 |
| `gui/` | 无选择、首次无许可的弹出候选视图两例通过；第三例 grid 因比较详情和基础观察的不同卡牌格式而失败。21 次 MCP，53.608 秒；整个失败组不计全过 |
| `gui-remaining/` | 改为比较同一种基础观察，从 grid 继续剩余 6 例全部通过：网格、手牌升级、牌组覆盖、地图覆盖、非战斗锻造、结果页。59 次 MCP，104.754 秒 |

总计 8 个典型场景通过，成功场景 72 次 MCP；含失败尝试 80 次。失败比较来自已加载旧脚本的 grid 进程：inspect_selection 的悬停说明聚合方式不同于基础观察，不能据此要求 cards 逐字段相等。只改验证比较来源，未改玩法代码或重跑已通过的两例；修正后静态卡牌、已选 ID 和预览的保留检查均通过。

已核实的正确行为：视图调用无初始许可也可以成功，成功返回可以直接继续选牌；重复 battlefield／selection 请求的原生交互标记均为 false，返回未改变；实际往返标记为 true。候选隐藏时不泄露 cards／selected_ids，战场的 available_actions 不允许普通出牌或结束回合。

已核实的缺口：无选择拒绝后 end_turn 被 observation_required 阻止；无眼睛结果页拒绝后合法确认也被阻止；锻造拒绝后合法选牌被阻止。牌组／地图覆盖时没有点击，却清除已有许可；关闭覆盖页后通过正常查看返回可以继续。公共错误没有转发原生固定原因，两个问题独立存在。

[6 份典型完整 JSON](2026-11-05-selection-view-examples/README.md)仅从通过场景的公共返回提取，每份与原始记录及实际 full 参数比对；manifest 保存来源、序号、产物与样例哈希。错误样例刻意保留相同的当前 message，展示诊断不足，不在审阅期间修复它们。两个自有游戏 PID 均已退出，见 processes.json。未重新构建或运行 C# 检查，因为只改核验代码和说明，游戏测试使用已准备的同一 DLL。

`verify_delivery.py` 检查 6 份样例、8 项清单与通过证据、原生交互标记、62 项 Python 日志、文档链接、未变的 DLL 哈希和进程退出状态；工具核销数保持 17/44。`git diff --check` 通过。核验流程只要求典型 JSON，不要求每种场景重复一份，也不把未实测分支包装为已覆盖。

未实测控制器输入、眼睛被第三方修改、真实并发替换选择、未支持选择与非单人拒绝。其他已识别原生页面按是否包含共同眼睛控件作源码核对，不表示一定允许查看战场，也不据典型成功样例宣称所有卡牌和事件均已实测。
