# play_card 完整 full 返回

> 当前状态：现状采集完成，公开行为未修改；本目录展示现有单张工具，不是多张出牌接口。工具问题及连续出牌方案仍在[专项审阅](../2026-11-04-play-card-review.md)讨论。

基线为 d46406c 上增加测试设施的构建，Mod 0.62.0、MCP 0.64.0、schema 40；各构建的精确 DLL 摘要、参数、来源数组下标（从 0 起）和每份 JSON 摘要见 [manifest.json](manifest.json)。

所有 .full.json 均逐字提取自真实 stdio MCP structuredContent，已与文本 JSON 相等性核验。error 没有独立 preset 格式；示例请求同样使用 full。未附送原生包装、状态令牌或基础观察。

| 场景 | 调用参数 | 完整返回 | 当前结果 |
| --- | --- | --- | --- |
| 普通出牌／参数与目标错误 | `{"preset":"full","card_id":true}` | [basic-01.full.json](basic-01.full.json) | card_id must be integer. |
| 普通出牌／参数与目标错误 | `{"preset":"full","card_id":5,"target_id":null}` | [basic-02.full.json](basic-02.full.json) | target_id must be integer. |
| 普通出牌／参数与目标错误 | `{"preset":"full","card_id":2147483647}` | [basic-03.full.json](basic-03.full.json) | No supported visible hand card has that ID. |
| 普通出牌／参数与目标错误 | `{"preset":"full","card_id":5}` | [basic-04.full.json](basic-04.full.json) | This card requires target_id from inspect_targets.targets. |
| 普通出牌／参数与目标错误 | `{"preset":"full","card_id":5,"target_id":4294967295}` | [basic-05.full.json](basic-05.full.json) | The specified target is not currently available for this card. |
| 普通出牌／参数与目标错误 | `{"preset":"full","card_id":5,"target_id":2}` | [basic-06.full.json](basic-06.full.json) | player_ready |
| 普通出牌／参数与目标错误 | `{"preset":"full","card_id":6,"target_id":0}` | [basic-07.full.json](basic-07.full.json) | This card does not accept target_id; omit it. |
| 普通出牌／参数与目标错误 | `{"preset":"full","card_id":6}` | [basic-08.full.json](basic-08.full.json) | player_ready |
| 能量不足 | `{"preset":"full","card_id":5,"target_id":2}` | [energy-01.full.json](energy-01.full.json) | Not enough Energy. |
| 星能不足 | `{"preset":"full","card_id":5,"target_id":2}` | [stars-01.full.json](stars-01.full.json) | Not enough Stars. |
| 不可打出 | `{"preset":"full","card_id":5}` | [unplayable-01.full.json](unplayable-01.full.json) | This card cannot be played now. |
| 卡牌条件未满足 | `{"preset":"full","card_id":5}` | [card_logic-01.full.json](card_logic-01.full.json) | This card cannot be played now. |
| 入队后取消 | `{"preset":"full","card_id":5,"target_id":2}` | [cancel-01.full.json](cancel-01.full.json) | action_canceled |
| 入队后取消 | `{"preset":"full","card_id":6}` | [cancel-02.full.json](cancel-02.full.json) | Read current state with get_observation or a relevant inspection before acting. |
| 手牌升级选择 | `{"preset":"full","card_id":5}` | [hand_choice-01.full.json](hand_choice-01.full.json) | choice_required |
| 手牌升级选择 | `{"preset":"full","card_id":7}` | [hand_choice-02.full.json](hand_choice-02.full.json) | Normal card play is unavailable. |
| 发现牌选择 | `{"preset":"full","card_id":5}` | [choose_one-01.full.json](choose_one-01.full.json) | choice_required |
| 发现牌选择 | `{"preset":"full","card_id":7}` | [choose_one-02.full.json](choose_one-02.full.json) | Normal card play is unavailable. |
| 弃牌堆选择（头槌） | `{"preset":"full","card_id":6}` | [combat_pile-01.full.json](combat_pile-01.full.json) | player_ready |
| 弃牌堆选择（头槌） | `{"preset":"full","card_id":7,"target_id":2}` | [combat_pile-02.full.json](combat_pile-02.full.json) | player_ready |
| 弃牌堆选择（头槌） | `{"preset":"full","card_id":5,"target_id":2}` | [combat_pile-03.full.json](combat_pile-03.full.json) | choice_required |
| 弃牌堆选择（头槌） | `{"preset":"full","card_id":7}` | [combat_pile-04.full.json](combat_pile-04.full.json) | Normal card play is unavailable. |
| 战斗胜利 | `{"preset":"full","card_id":5}` | [victory-01.full.json](victory-01.full.json) | combat_won |
| 战斗失败 | `{"preset":"full","card_id":5}` | [death-01.full.json](death-01.full.json) | combat_lost |
| 牌组覆盖 | `{"preset":"full","card_id":5}` | [covered-01.full.json](covered-01.full.json) | Normal card play is unavailable. |
| 地图覆盖 | `{"preset":"full","card_id":5}` | [covered-02.full.json](covered-02.full.json) | Normal card play is unavailable. |
| 随机攻击 | `{"preset":"full","card_id":5}` | [random-01.full.json](random-01.full.json) | player_ready |
| X 费用 | `{"preset":"full","card_id":5}` | [x_cost-01.full.json](x_cost-01.full.json) | player_ready |
| 事件中请求出牌 | `{"preset":"full","card_id":0}` | [noncombat-01.full.json](noncombat-01.full.json) | Normal card play is unavailable. |
| Normality 阻止出牌 | `{"preset":"full","card_id":5}` | [hook-01.full.json](hook-01.full.json) | player_ready |
| Normality 阻止出牌 | `{"preset":"full","card_id":6}` | [hook-02.full.json](hook-02.full.json) | player_ready |
| Normality 阻止出牌 | `{"preset":"full","card_id":7}` | [hook-03.full.json](hook-03.full.json) | player_ready |
| Normality 阻止出牌 | `{"preset":"full","card_id":8}` | [hook-04.full.json](hook-04.full.json) | This card cannot be played now. |

## 原生队列诊断

[native-queue-traces.json](native-queue-traces.json) 是 12 种隔离原生探针的压缩诊断，不是 LLM 可调用工具或未来批量接口的响应。index 从 0 起，submissions 按尝试顺序记录接受结果及当时第一项的状态；paused 表示选择出现时，actions 表示结束时，played 来自实际 card_played 事件，canceled 来自独立取消通知。

immediate_death 刻意直接调用原生 API 证明其不足以替代 UI／终态门控；后两项发生在死亡之后，不能作为合法快速出牌样例。其他连续探针记录了后项提交时前项仍为 Executing。

state 为 Finished 而 played 为 false 是实际原生行为：执行包装结束不等于牌生效；费用／目标取消还可能同时出现 canceled:true。完整原始观察及事件留在不纳入 Git 的测试目录，未把诊断字段加入公开 MCP。
