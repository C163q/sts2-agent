# 遗物详情正确性与图标状态交付

> 当前状态：实施与验收完成，3/3 项已完成；RELIC-01–03、原下标映射复核及所有预设已交付，inspect_relics 可核销。正式 Mod 未安装。暂无阻塞。

## 范围与基线

依据[输出定稿](2026-11-04-inspect-relics-review.md#输出定稿)及[实施计划](../superpowers/plans/2026-11-04-relic-inspection.md)处理 RELIC-01–03。代码基线 `b0f779c`，交付目标 Mod `0.57.0`、MCP `0.59.0`、原生 schema `38`；当前兼容表见 [README](../../README.md#当前版本与前提)。

核对 Linux 游戏 `v0.107.1`，release build `59260271` 与 RitsuLib `0.6.10` 兼容运行时。程序集 `data_sts2_linuxbsd_x86_64/sts2.dll` 的 SHA-256 为 `d13f3f150b1413b24c3a9c5575cdf5398dc74270877d55dec9a556dd8150bd03`。游戏证据和反编译成员沿用场景审阅；另核对同目录 GodotSharp.dll 的 Shader.GetShaderUniformList。

## 实现

- 原生拒绝区分未暴露顶栏与遗物栏不可用，显式公开安全原因；不公开异常正文。共用许可规则不变。
- RelicInspection.Static 统一提供 name／counter／melted／grayed_out／pulsing；详情继承静态结构并合并原生正文。基础观察使用同一入口，summary 不生成悬停内容。
- grayed_out 取图标的原生普通／置灰 Modulate 着色，未知着色为 null；pulsing 只读取实际 shader 已声明的 pulse uniform，0／1 分别为 false／true，其余未知为 null。熔化独立，模型状态不作为读取依据。
- 公共精简入口仅省略根 relics 和 top_bar.relics 两个新字段的 false；一般 null 规则不变，其他 false 与 transition.events 保留。
- 原 relic_indices 映射已经存在，继续保留显式数组时的原位置对照；所有预设、null／[]、重复、混合越界、共享解释及 note 均有检查。
- 两份旧遗物验证器改用共享断言，支持上下文、状态与不可悬停条目，stdio 工具目录按当前登记核验；保留只读、语言、提示去重、原生关联和前后快照一致性检查。

没有增加公开参数、打开遗物检查页、触发悬停动画或修改动作／事件边界。测试渲染扰动仅在双重测试门控下开放，finally 与局间重置恢复；不属于玩法工具。

## 验证证据

证据根目录：`.tmp/2026-11-04-relic-implementation/`。

- Python RED：新状态字段被丢弃、错误类型未被拒绝，见 python-red.log；实现后定向测试通过。
- 原生 RED：gui-red 中新增 4 个状态断言失败，既有 31 项通过；实现后首次 GUI 的 35 项原生检查全部通过。
- 旧文件验证器 RED：完整响应因新上下文被错误拒绝，见 verifier-red.log；修复后重放通过。
- 完整 Python 603 项通过，见 python-all.log；C# 91 项通过，见 csharp.log；build-final.log 为零警告、零错误。
- 首次 GUI 的状态、映射、具体拒绝均通过，后续 end_turn 测试失败：上一同局验证留下初始地图，首次快照已为 view=map 且没有 end_turn。属于验证编排前提错误；将验证拆为独立测试局，未放宽生产动作合法性。原失败证据保留在 gui/。

- 修正后的 gui2/report.json：**6 个测试局／6 个步骤全部通过**，复用 1 个自有进程，PID 83617 已退出；覆盖原生 35 项遗物检查、渲染与模型状态独立、未知着色／无 shader、不可悬停、预设对照、原下标、提示和 note 裁剪、错误后直接结束回合、地图／牌组／牌堆读取、商店／火堆、自然蜡质熔化和测试入口门控。
- 单独文件与 stdio 旧验证器在战斗、火堆均通过；有效路径仍保留英语、状态不变、解释去重和原生关联校验。
- 最终 26 项定向回归通过，见 final-pure-unsandboxed.log；同步提示词后另有 77 项目录／stdio／遗物检查通过，见 catalog-final.log；普通沙箱中的同组回归因已知 socket 限制超时，未用它宣称通过。compileall、空白及文档链接检查通过。
- 构建、准备运行时及 GUI 的 Mod DLL SHA-256 一致：`4a735cf4bfb7a943ee6d9aeb5a9188344ad91dcb5ea6b8c973aa1a30e6804210`。
- [13 份完整实测 JSON](2026-11-04-relic-inspection-implementation-examples/README.md)与实际调用参数逐项匹配，保留来源与内容哈希；未将夹具注入的边界标为自然游玩事件。

独立只读审阅未发现生产正确性或信息边界问题，确认上述测试编排问题。该问题以首次 GUI 失败为 RED，拆局后的完整 gui2 为 GREEN；没有第二次派生审阅。未留下已确认而未修复的问题。未裁定的第三方 shader／祖先着色组合纳入下述验证边界，不作支持保证。

## 验证边界

人为注入的置灰／pulse、未知着色、无 shader、隐藏栏及关闭悬停入口，只证明对应显示边界；不表示自然游玩出现这些异常组合。自然蜡质熔化使用原生出牌流程验证。全部遗物、第三方任意 shader、多人及任意祖先着色组合未穷举。正式 Mod 未安装，也未操作正式存档。
