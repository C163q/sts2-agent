# 出牌与目标查询验证

当前状态：本次功能与验证完成，既有结束回合的真实 MCP 回归通过。已通过 137 项 Python 测试、8 项纯 C# 检查、26 个原生场景和 5 个图形场景；构建为零警告、零错误。

## 基线与实现

基于仓库 `e2c9a81`、Linux 游戏 `v0.107.1`（分支同名，提交 `59260271`）、RitsuLib `0.6.10` 的 `0.107.1` 兼容运行时。程序集 SHA256 与 [调研](2026-10-30-card-play-targeting.md) 相同。交付版本为 Mod `0.15.0`、MCP server `0.12.0`，固定 18 个工具；契约见 [出牌与目标查询](../development/card-play.md)。

游戏执行使用 `CardModel.TryManualPlay` 和原生动作队列，后续选择复用已有工具。只读查询不调用会推进随机数的 RitsuLib `GetTargets`。本地脚本和测试数据保存在不入库的 `.tmp/2026-10-30-play-card/`；游戏及依赖二进制不纳入 Git。

## 验证结果

| 层次 | 结果与证据 |
| --- | --- |
| Python | 全部 137 项通过，包含 10 项新增协议与权限测试；`python-final.log` |
| 纯 C# | 8 项停止条件与事件缓冲检查通过；`csharp-checks.log` |
| Mod 构建 | 0 警告、0 错误；`build-final.log` |
| 原生游戏 | 下列 26 个场景分别在全新隔离实例通过，各自保存 `<scenario>.json` 和游戏日志 |
| 图形游戏 | `basic`、`discovery`、`charge3`、`glimmer`、`test_subject` 通过；证据及截图在 `windowed/` |
| 真实 stdio MCP | 18 工具、版本、紧凑文本与 structuredContent 一致；目标查询不产生但可保留许可、出牌消耗许可、指定/自身出牌、参数拒绝与查看页面边界通过；`stdio.json` |
| 既有 MCP 回归 | 回合 1→2、正常观察/详情、缺省及错误参数、重复/过期动作、读回与去重通过；`mcp-regression.json` |

原生场景分组：

- `basic`：打击指定对象、防御省略目标、缺省/错误/自身目标拒绝、原始 JSON 参数类型、过期令牌。
- `discovery`、`charge0`、`charge1`、`charge2`、`charge3`、`glimmer`：先出牌再生成或抽取候选；少量候选自动完成；进入选择、眼睛查看、返回并继续结算。
- `random`、`random_empty`、`aoe`、`multi_hit`、`x_cost`：随机、群体、多段及 X 费；连续五次随机目标查询前后 RNG counter、能量、瞄准和队列状态一致。
- `energy`、`stars`、`unplayable`、`card_logic`、`ally`、`hook`：资源不足、不可打出关键词、谢幕自身条件、单人无队友及凡庸限制；查询与提交一致。
- `victory`、`death`、`thorns_death`：群攻击杀、自身失血致死和反伤致死，返回原生确认的胜负及期间事件。
- `test_subject`、`no_target`：实验体正常、死亡待复活和复活后；单体攻击无合法对象，自身、随机及群体牌仍按原生流程允许提交，复活后恢复同一个目标 ID。
- `unsupported`：武装触发尚未支持的手牌升级，及时返回 `choice_required` 与明确未支持状态，不等待超时或代选。
- `cancel`：测试入口在原生入队时改变资源条件，原生执行前自行取消；工具返回 `action_canceled`，不伪造已经打出事件。
- `unhittable`：使用原版 `MockUnhittablePower` 构造存活但不可命中的敌人，查询排除该对象，显式单体指定被拒绝，群体与随机仍交由原生结算。此场景是分支验证，不是自然对局机制演示。

## 已核实的边界

出牌的 `player_ready` 可以发生在同一回合，不要求下一回合通知；`end_turn` 保留下一回合要求。实际入队动作被独立跟踪，原生取消通知不会因随后状态变为 `Finished` 而丢失。选择出现时不等待整张卡牌的完成任务，因此发现、冲锋！！、微光可继续使用已有选择工具。

实验体死亡动画会继续改变生命条等可见内容。若调用间画面变化，Mod 返回 `stale_state` 且不输入；测试只对这一明确拒绝重读状态，核对同一战斗、回合、手牌和目标后再作相同决定。不重试超时或其他未知结果。

原生目标指示范围不等于完整效果预测。`unhittable` 初次测试额外假定群攻不会伤害测试对象，实际观察到随机攻击和群攻仍造成伤害。源码 `AttackCommand.Execute` 与 `CreatureCmd.Damage` 在这些路径检查存活，没有统一排除 `ShouldAllowHitting == false`。修正了测试中的错误预测，保留目标查询、单体拒绝和原生提交断言；产品不裁剪或改写原生效果。

对目标程序集的 MethodDef 检索确认，本版本只有 `AbstractModel.ShouldAllowTargeting` 基类方法和 `Hook.ShouldAllowTargeting` 调用入口，没有原版内容覆写。因此“单体禁止指定但仍可被群攻”的 Hook 分支只核对了源码及规则分离，没有声称通过原版机制触发。其他 Mod 的实际覆盖仍需专项适配。

## 测试与审阅修复

- 初始 Python 测试证明工具与 reader 缺失；旧 Mod 原生场景也以 `Native play_card action is missing` 失败，随后接入通过。
- 原始文件请求的字符串卡牌 ID 最初触发 `game_error`；原因是未先判断 JSON 数字类型。增加类型检查后，原生测试确认返回 `invalid_request`，不提交动作。
- 并发测试复现非法目标查询抢先返回、随后观察恢复许可；将参数校验移入同一会话锁后通过。证据为 `python-race-red.log` 与 `python-race-green.log`。
- 一次独立审阅核对源码与全部当前变更，未发现 Critical、Important 或 Minor 实现问题。审阅提出的存活不可命中覆盖已通过 `unhittable` 补齐；不进行重复审阅。
- 同步 MCP 与文件协议文档中旧的“动作仅结束回合”描述，以及共享事件中同一回合继续的含义；属于现行说明未随既有选牌能力更新，未发现相应代码退化。

## 未验证范围

真实多人、药水使用、任意第三方自定义目标、全部卡牌组合、断线恢复和声音不在本次通过范围。专门升级等选牌仍需手动完成。沿用期间事件记录的已知限制，不承诺覆盖所有资源变化、召唤或任意 Mod 效果。无图形实例有既有 FMOD、Steamworks、Sentry 与调试端口告警，不能据此声称音频验证通过；正式对局未用于构造测试。
