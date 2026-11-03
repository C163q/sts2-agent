# 共享卡牌格式实施记录

> 当前状态：已完成。共 4 项，已完成 4 项；Affliction、附魔空值、小范围重构、全部卡牌迁移、浏览预设及手牌资源字段均已交付，并完成联合验证与独立只读审阅。暂无阻塞；未逐一实测的边界见下文。

## 依据与边界

执行[卡牌覆盖定稿](2026-11-03-card-format-coverage.md)和[手牌核验](2026-11-03-inspect-hand-review.md)，工具核销沿用[工具清单](2026-11-02-mcp-tool-review.md)。原生端负责可见性、完整采样与游戏线程，Python 负责校验、筛选和输出投影。实卡与隔离网格克隆分别读取，共享字段组装；不重算持有卡牌，不暴露抽牌顺序，不修改正式安装。

## 实施顺序

- [x] **1. Affliction 与外观空值。** 在 `Observation/CardAppearance.cs` 集中实卡外观读取与模型预览字段组装；`CombatObservation` 共用手牌枚举，`BrowsedCard` 接入。Python 卡牌结构接受 nullable enchantment/affliction，共享摘要保留可见 affliction.name。先用 `tests/python/test_card_enchantments.py` 验证全预设、共存、非法值与过滤前校验；原生检查覆盖隐藏、透明、离屏和未知牌，实测魂缚／烟雾。
- [x] **2. 统一牌面与浏览参数。** Python 提供固定 face/full/summary 卡牌入口；展开候选、比较及结算采样完整悬停解释，保留侧别。牌组／牌堆移除 detail_level，公开 preset 为 default/full/summary，CLI 复用投影。先补统一格式、浏览参数和比较解释回归，再修改原生读取、校验、共享提示、工具描述及文档。
- [x] **3. 手能量与星星。** 提取独立 HUD 读取和共用资源摘要，inspect_hand 增加 energy/max_energy/stars；full 保留 null，default 过滤，summary 合并完整能量对并保留 stars:0。先验证空筛选、全部缺失、隐藏／不完整计数和错误结果，再实现。
- [x] **4. 联合验证与交付。** 执行完整 Python、纯 C# 检查及编译；准备隔离运行时，通过真实 stdio MCP 验证外观、选择比较、牌组／牌堆、资源及动作回执。审查差异，更新持续维护文档和版本基线，独立审阅后提交。

各项按“补回归并观察失败 → 最小实现 → 相关检查与图形验证 → 同步文档 → Conventional Commit”执行。完整用例及证据放在 `.tmp/2026-11-03-card-format-implementation/`，失败目录保留，不覆盖重跑。

## 重点复核

- 未知卡和不可读覆盖不泄露 Affliction、附魔身份或悬停解释。
- 比较两侧共用原牌 ID，但保留各自解释与 null；随机 after:null 不被补出。
- 动作回执和页面工具也接入共享格式，商店基础观察仍无正文。
- 牌组／牌堆默认现在提供完整内容；旧 detail_level 在 UI 操作前拒绝。
- 资源读取独立于玩家身体是否可见，空筛选照常返回计数，不凭角色补星星。

## 执行与验证

实施前工作区干净，基线提交 `9bb583b`。详细检查结果将在各阶段完成后补入本节。

### 阶段 1

- Python 新回归先在旧实现失败（nullable 附魔被拒绝，Affliction 未校验），实现后完整 498 项通过；纯 C# 60 项通过，编译无警告／错误。
- `phase1-gui` 中魂缚／烟雾及原有六张附魔场景均通过真实 stdio MCP；原生检查覆盖隐藏、透明、离屏、未知／锁定与共存，采样前后状态完整相等。已人工查看 Affliction 截图。其他五种覆盖仅沿用已核对资源与共用读取，未逐一进行 GUI 实测。
- 证据：`.tmp/2026-11-03-card-format-implementation/phase1-python.log`、`phase1-gui/report.json` 及各例 evidence。测试进程 PID 39998 已结束。

### 阶段 2

- 共用 `card_format.py` 固定五种内容模式；严格基础投影移至 `value_shapes.py`，避免结算结构与卡牌结构循环依赖。实卡完整正文及提示由 `CardPresentation` 共用；网格克隆上下文保持独立。
- 展开候选、所有比较及结算卡牌现在保留悬停解释；商店基础观察和半隐藏手牌不提供正文。比较提示保留在对应 before/after 中。
- 牌组／牌堆移除 detail_level 及回显；MCP 和 CLI 默认完整 default，支持 full/summary，CLI 使用相同校验与投影。旧请求在 UI 之前拒绝；升级、排序、稳定 ID、空堆／不可用和关闭行为保留。
- 新回归先在旧实现失败；迁移后完整 Python 503 项通过。随后 CLI／统一格式专项 6 项通过。编译无警告／错误。
- `phase2-gui` 共 9 个隔离局通过：牌组与三堆、40 张候选及升级、手牌升级、锻造、事件附魔、随机变牌、卡牌包、结果确认；原生比较解释、null、ID 和只读状态均按专项断言验证。自有进程 PID 43925 已结束。
- 最初完整检查的两项失败是旧契约断言仍要求丢弃展开候选及结算卡牌解释；按已确认的新边界修订，并增加比较两侧解释关联回归。原始失败日志保留。
- 证据：`.tmp/2026-11-03-card-format-implementation/phase2-python-fixed.log`、`phase2-formats.log`、`phase2-gui/report.json`。

### 阶段 3 与最终验证

- inspect_hand 增加 energy/max_energy/stars；原生 `CombatResources` 和 Python `resource_summary` 与基础观察共用。full 保留 null，default 过滤，summary 合并完整能量对；stars:0 不丢弃。成功空筛选和全部无效 ID 保留可读资源，错误仍只有 error。
- 资源回归先在未实现时失败，接入后定向 34 项通过；最终完整 Python **507 项通过**，纯 C# **60 项通过**，编译无警告／错误。
- 最终 `final-gui` 的 Affliction 和六张附魔两局通过；资源辅助检查随后因把原生星星 MegaRichTextLabel 当成 Label 而中止。重新核对目标程序集 NEnergyCounter/NStarCounter 后，仅修正测试辅助的取节点类型，生产采样无需修改；失败日志完整保留。
- `final-resources-gui` 的铁甲战士、储君及浏览三局全部通过。原生检查验证标签值来源、隐藏计数不补模型、玩家身体隐藏仍能 inspect_hand、UI 恢复；真实 MCP 验证空筛选、无效 ID、成对能量字符串与星星。进程 PID 46594、47875 均已结束。
- 最终格式／资源成功场景合计 5 局，另补充 1 局全新隔离进度的实际胜利与解锁流程；连同前两阶段为 17 个通过的隔离测试局。失败辅助检查另计，不把中止套件标为通过。最新运行证据、采样 DLL 哈希及耗时见三个 GUI report；正式安装未改变。
- 独立只读审阅覆盖 9bb583b 至最终工作区，未发现可确认的 Critical/Important/Minor；其纯投影复核检查输入不变、固定 face、比较侧别与空值、空筛选及 stars:0。GUI 与最终检查结果由主执行者核对。未逐一重现全部动画竞态、其他五种 Affliction 外观、自定义 Mod 外观及所有未知牌场景，不把共用代码或编译当作这些实测。
- 当前版本统一更新为 README 中的 Mod 0.51.0、MCP 0.52.0、底层 schema 34。阶段提交：`95f8b15`（外观）、`d2fd40d`（格式／浏览）；资源与交付记录随本阶段提交。
- 持续维护文档按新契约同步，包括可见边界中明确允许已展开卡牌携带原生悬停解释；没有修改用户 TODO，也没有核销牌组／牌堆等未完成独立核验的工具。

## 实测示例

同一手牌的 [full](2026-11-03-card-format-implementation-examples/afflictions-hand.full.json)、[default](2026-11-03-card-format-implementation-examples/afflictions-hand.default.json)、[summary](2026-11-03-card-format-implementation-examples/afflictions-hand.summary.json) 来自最终版本的真实 MCP。完整来源和证据下标见 [manifest](2026-11-03-card-format-implementation-examples/manifest.json)。隔离夹具能量为 20/3，用于验证读取实际 UI，不表示正常开局配置。

补充结算验证的首次启动包装误用 STS2_AGENT_IPC_DIR，而验证器读取 STS2_AGENT_VERIFY_IPC_DIR，导致请求发往默认测试目录并超时；目标游戏没有收到请求。已修正包装，在新目录运行，原始 ending-gui 日志保留。

补充结算验证已在 `ending-gui-corrected` 通过完整 victory_unlock 流程：正常胜利、汇总、时间线、实际卡牌解锁页（每页三张）及返回主菜单。新增断言确认基础观察与 inspect_run_result 的完整卡牌相同，并均保留逐牌 hover_tips、enchantment 和 affliction 字段；summary 仍不含正文／解释。原始 IPC 配置失败不计作通过，两个自有进程均已结束。

最终 DLL 与准备运行时 SHA-256 一致：`b3a45c778dc6194682848c1e3d661cd8e064a845e61b83680fd01a71902619f1`。实测样本逐份对照原始证据完全相等，修改文档的本地链接目标检查通过，git diff --check 通过。
