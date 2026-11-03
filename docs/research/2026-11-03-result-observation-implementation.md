# 结算文字修复与观察摘要实施

> 当前状态：本轮交付完成，共 2 阶段，已完成 2 阶段；文字缺口、兜底改名及结算卡牌 summary 均已验证，独立代码审查和文档／样本检查通过。无阻塞；未更新正式游戏 Mod。

## 最终要求与依据

- 基线 c8306ab，MCP 0.50.6、Mod 0.49.2、schema 31；目标游戏及原始 47 full 见[16–17 组核验](2026-11-03-get-observation-result-menu.md)。原样保留基线文件，不覆盖为修复后结果。
- 修复结算死亡原因、本局详情结果句及日期的英文转写，保留原生当前已显示文字的来源；不重新抽取语句、不更改区域／语言、不修改原生 UI 或历史。
- 兜底 scene 改为 unrecognized，覆盖未知及加载过渡，不扩大商店等已识别场景。更新原生 schema、Python 校验、当前测试及持续维护说明；旧场景名在当前观察校验中拒绝；不新增通用协议版本协商。历史证据及文档中的旧标识保留为原始基线。
- summary 的结算主体沿用 default，保留 texts、options、分数、徽章、发现和当前空列表；当前已显示的 cards 复用共用 card_summary，正文、rarity、visual_card_pool 由 inspect_run_result 按需查看。full/default/详情工具保留现有卡牌字段。菜单和 unrecognized 主体沿用 default，共用顶栏摘要独立复用。
- 地图／牌组覆盖、占卜文字观察及 inspect_shop 的用户后续待办不在本轮实施范围，不新增或扩大 TODO。

## 实施顺序

### 阶段 1：文字来源与场景名称

职责：在 Localization 新建独立结算文本模块，接入初始化；EnglishEventText 只提供复合来源保留／标签绑定的共用能力，不在 RunResultInspection 混入原生历史重建。时间输入在原生设置当前日期标签时捕获，按同一时间与精度转写。scene 改名在原生与公共校验同时切换。

- [x] 添加真实 MCP 图形回归，覆盖失败 summary、history 夹具、全 preset／详情、重复观察不改变原生文字和语言；先在旧实现观察到混合语言失败。补充 unrecognized 的公开调用和动作连续性回归，旧标识应被当前观察校验拒绝。
- [x] 核对目标程序集的死亡句、标签赋值、时间格式成员及调用点，实施最小修复；保留跨延迟赋值的复合文本来源。补充缓存压力及历史日期校验。
- [x] 运行相关 Python、构建、C# 检查及隔离 GUI，确认基础观察与详情一致、中文 UI 未改变、地图上下文仍可读取；同步版本及文档，独立交付。

### 阶段 2：结算卡牌 summary

接口：消费阶段 1 的完整已验证观察。只在 Python observation_summary 中投影 run_result.cards，不改变来源读取、权限、详情或原生 schema。

- [x] 添加公开 GameTools 回归：已显示解锁卡牌的 summary 使用字符串 card:N ID、名称、类型、费用；保留 texts/options/空列表及已有顶栏规则，full/default/inspect_run_result 保留正文；畸形 full 在投影前拒绝。先确认新增测试在原实现失败。
- [x] 复用 card_summary，实现并运行相关／全套 Python；隔离 GUI 核对实际解锁牌、章节正文和菜单，保存修复后 full/summary 例子。
- [x] 同步研究记录、接口说明、两份审查入口和完成数；记录未覆盖范围。最终审查与提交另记下文。

## 验证重点与接口核对

- 两阶段共享原始全量观察：阶段 1 修复来源与 schema，阶段 2 仅做校验后的摘要；阶段 2 不覆盖或重新构造已显示句子。
- 来源保留不能依赖最近 128 次渲染仍存在；原生整句缓存及标签绑定应持续有效，不能因同名中文映射串源。
- 日期格式不得增加 UI 未显示精度；重复观察不得改变本地化变量、UI 文本、区域或随机状态。
- 未知页名称变化不得影响已识别房间和地图／选牌的许可；旧场景标识不能被当作新名称接受。
- 结算卡牌 ID 为字符串；摘要不能以手牌整数 ID 重写它，也不能删除当前页的故事、进度、按钮或已显示物品。

执行证据放 `.tmp/2026-11-03-observation-final-implementation/`；混合语言问题沿用并更新[问题记录](../../.tmp/2026-11-03-observation-final-review-report.md)。

## 阶段 1 验证

- 版本：Mod 0.49.3、MCP 0.50.7、schema 32。Native 结果字段结构不变，场景兜底改名；不新增协议协商或兼容旧场景标识的别名。
- 根因：原生预编译的格式化调用可能绕过通用来源钩子，且死亡句先缓存再延迟赋值，短期最近渲染列表不能保证整句仍存在。定点重绑原生调用，并以字符串对象身份弱引用保留复合来源；标签绑定后不依赖最近列表。日期的 Date/Time 变量在生成标签前按中文区域固化，现于同一原生设置点按相同时间、时区和显示精度保留英文表示。
- 独立模块 EnglishRunResultText 负责结算特定钩子与日期；共用 EnglishEventText 增加来源保留和绑定，RunResultInspection 的读取、可见性、动作及历史数据均不修改。
- 有效 RED：red-death 在 summary 断言中复现混合语言；red-history 在 history 断言中复现中文结果句与日期；rename-red 的两个公开工具测试在旧实现产生 6 个预期断言失败。初次命名 RED 使用了后置存在性断言而触发 KeyError，已调整为直接行为断言后重跑，不把该命令错误当作有效 RED。
- 构建零警告／错误，C# 60 项通过，相关 Python 27 项通过，全套 Python 476 项通过，31.796 秒。日志为本地 build-fix.log、fix-csharp.log、fix-related.log、fix-python.log。
- green-death、green-history 两类 GUI 均通过，共 35 次真实 MCP、6 次显式原生检查；含全部五预设、详情、重复观察及 256 次无关本地化渲染压力。中文原生标签与区域前后逐值一致，原生可见 UI 未改变；本局详情仍为受门控原生夹具，未启用普通 View Run 入口。
- 修复后真实返回：[失败 summary full](2026-11-03-result-observation-implementation-examples/death-summary.full.json)、[本局详情 full](2026-11-03-result-observation-implementation-examples/history.full.json)。来源、下标、DLL 哈希和自有 PID 清理记录见本地 fix-verification.json，原始截图在各 GUI verify/screenshots。失败句为 `“The Ironclad was felled by a Group of Slimes.”`；历史日期已按英文格式转写。
- 未穷举所有死亡来源、语言、时区和每日榜单；未替换正式游戏 Mod。加载过渡的实际新 scene 采样随阶段 2 一并记录。

## 阶段 2 验证

- 版本：MCP 0.50.8，Mod 0.49.3、schema 32 不变。共用卡牌摘要仅接入观察投影，不更改底层读取或 inspect_run_result。
- 有效 RED：3 个新增公开工具测试中，卡牌摘要预期在原实现产生 1 个断言失败；非卡牌页面及畸形正文拒绝原本已经通过。实现后相关 Python 39 项通过，全套 479 项通过，31.518 秒，日志为 summary-related.log、summary-python.log。
- summary-gui 沿原生胜利、首次教程、多个 epoch、卡牌／药水／遗物／角色／功能解锁及返回菜单完成 29 组实际 full/summary 对照，共 140 次真实 MCP 和 4 次显式原生测试调用。卡牌用字符串 ID 与费用摘要，其他结算主体逐字段保持；普通主菜单时间线仍不获得本次结算权限。
- 同次游戏启动实际捕获新 unrecognized；没有将其当作商店等非战斗房间，也未制造不能可靠判断的 loading 状态。自有 PID 37312 已关闭，源码及运行时 DLL 与阶段 1 相同。
- 原始来源、下标和数量见本地 summary-verification.json；基线 47 份 full 未改写，用户 TODO 和正式 Mod 未改。每日挑战榜单、所有死亡来源／语言及章节翻页组合仍未穷举。

| 实测场景 | 完整返回 |
| --- | --- |
| 启动兜底 | [full](2026-11-03-result-observation-implementation-examples/unrecognized.full.json)、[summary](2026-11-03-result-observation-implementation-examples/unrecognized.summary.json) |
| 已显示解锁卡牌 | [get_observation full](2026-11-03-result-observation-implementation-examples/unlock-cards.full.json)、[get_observation summary](2026-11-03-result-observation-implementation-examples/unlock-cards.summary.json)、[随后 inspect_run_result full](2026-11-03-result-observation-implementation-examples/unlock-cards-inspection.full.json) |
| 章节与主菜单 | [章节 summary](2026-11-03-result-observation-implementation-examples/epoch.summary.json)、[主菜单 summary](2026-11-03-result-observation-implementation-examples/menu.summary.json) |

## 提交与最终审查

阶段 1 提交：46e1a47，fix(observation): retain result text provenance and clarify fallback scenes。阶段 2 实现、验证与最终独立只读审查均已完成，摘要提交标题为 feat(mcp): summarize displayed run result cards。


独立审查由 review_result_observation（gpt-6.1-sol，high）完成，范围为 c8306ab 至最终 src/tests 工作区，含新增回归；核对原生目标版本源码、来源绑定、日期精度、schema 和摘要边界。Critical／Important／Minor 均无具体发现；未修改文件、未另启游戏或运行整套测试。

对审查者未另行判断的范围，处理如下：本轮实际构建、60 项 C#、479 项 Python 及 3 类 GUI 的证据由实施者核验，不重复同一全套检查；其他游戏版本、全部语言／时区／死亡来源和每日榜单仍明确为未穷举；最终文档完成状态由实施者另查链接及样本来源。未将这些范围写成已验证能力或擅自加入用户 TODO。

本轮共 175 次真实 MCP 与 10 次显式原生检查，3 类成功 GUI 的自有 PID 均已关闭。9 份新增 JSON 均逐对象匹配对应响应，结构按工具与预设校验；运行时 DLL 与构建产物一致，SHA-256 为 501d8ee982c64a77115565623d79b0154a6955b379dd2999a5efaa8e4a5f889e。最终 Markdown、链接及差异检查通过；旧基线样本、AGENTS.md 和用户 TODO 未改。
