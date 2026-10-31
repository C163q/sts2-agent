# 观察预设与当前可用工具实施计划

当前状态：实施中，共 3 项，完成 0 项。已核对现状与用户偏好，正在补充回归；暂无阻塞。

> **For agentic workers:** 使用 superpowers:executing-plans 在当前会话依次实施，并进行最终独立审阅。

**目标：** 让观察准确列出当前可用工具，并支持保持令牌校验的精简输出。

**架构：** 游戏端生成当前可用工具，Python 只做公开名称过滤和输出投影；共享可用性条件用于原生动作入口与工具发现。

**技术：** C# / Godot 4.5.1 / Python stdio MCP。

**规格：** [观察预设与当前可用工具](../specs/2026-10-31-observation-presets-design.md)。

## 全局约束

- Linux 游戏 v0.107.1、RitsuLib 0.6.10；不添加第三方依赖。
- 默认 full，精简 actions_only；省略观察、截图和测试工具。
- 游戏线程读取真实状态，具体调用保持合法性与状态令牌检查。
- 文档中文、注释英文；不操作正式对局。

## 审阅重点

- 选牌被地图或牌堆覆盖后不能提供候选操作。
- 精简输出不得绕过完整响应校验或附带占卜图像。
- 地图、弹窗和结算新增详情不放行底层动作。
- 非法预设必须清除旧令牌；精简观察后的合法动作仍能正常提交。
- 列表扩展后，动作结果失败与选择边界的许可续接语义保持不变。

### 任务 1：预设与公开工具投影

**文件：** 新建 scripts/observation_presets.py、scripts/test_observation_presets.py；修改 game_tools.py、mcp_catalog.py、mcp_server.py、game_output.py、run_ending_details.py、transition_details.py。

**接口：** get_observation(arguments=None)；preset_arguments 校验 full/actions_only；observation_preset 在完整校验后投影。公共工具过滤在 observation_details 统一完成，测试入口不暴露。

- [ ] 编写并运行失败测试：默认兼容、手牌选择上下文、占卜无图、非法输入、完整校验与令牌衔接、真实 stdio。
- [ ] 实现预设与公共工具白名单；调整专属边界仅允许对应详情和真实页面工具。
- [ ] 运行新增测试与 Python 全套，确认失败恢复及动作边界兼容。

### 任务 2：游戏端可用性核查与修复

**文件：** 新建 spikes/roundtrip/GameAdapter.AvailableTools.cs、scripts/verify_available_tools.py；修改 GameAdapter.cs 及必要动作入口。

**接口：** 游戏端 AvailableTools 汇总当前工具；CanInspectMap/Deck/Piles 等共享条件由观察和执行复用。

- [ ] 隔离游戏复现现有详情/关闭/眼睛工具缺失，保存真实 MCP 失败报告。
- [ ] 补齐当前工具和共享条件，不通过隐藏参数/随机结果判断未来能力。
- [ ] 对战斗、选择、查看、房间、确认和结算执行真实 MCP 断言与截图，列表中的无参数工具可实际调用。

### 任务 3：验证与交付

**文件：** 更新 README、开发接口、版本及本次验证记录。

- [ ] 完成编译、Python 全套、C# 检查、文档链接与差异检查。
- [ ] 独立审阅，修复重要问题并验证；同步说明实际验证和未覆盖范围。
- [ ] 提交本次变更，按既有授权备份安装，并说明正式游戏须重启与 MCP 重连。
