# 截图保存错误与许可恢复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

> 当前状态：实施中，共2项，已完成1项；正在迁移隔离实测，剩余文档、样例和一次独立审阅。暂无阻塞。

**Goal:** 修复本地截图保存失败后的许可保留和具体原因，恢复可维护的隔离验证入口。

**Architecture:** ScreenshotStore提供受控错误原因；GameSession保留已验证的原生取图证据，仅同令牌且明确未交互时沿用已有许可。MCP目录层区分配置关闭。取图和文件发布机制保持，验证器复用GameSession与verification_runtime。

**Tech Stack:** Python／anyio／stdio MCP；原生Mod0.80.0、schema47保持，MCP更新0.83.0。

**Spec:** [输出定稿](../../research/2026-11-08-capture-screenshot-review.md#输出定稿)，[开发核验](../../research/2026-11-08-capture-screenshot-development-notes.md)。

## Global Constraints

- 基线3620942；当前工作区临时分支fix/screenshot-recovery，用户已授权连续实施、验证、自行合main，无须重复确认。
- 无新参数／preset／图片响应；成功只有path/width/height。保持不覆盖、符号链接保护和临时文件发布，文件路径不传入游戏。
- 恢复要求有效原生图像、完整无交互执行证据、同旧令牌、已识别的本地保存拒绝；冷调用、不同令牌、坏响应、取消、原生失败和未知文件结果不获得恢复。
- 不公开任意OS异常；未知原因保留通用提示。清理失败不伪装为目标未写入。
- 不更改C#／Mod／schema，不重建DLL；运行产物2a87d3a18c4c34dca800132ed4cdb489f4ac8e20dc1e9ec3bfb6be84cfb4a1b5。
- 不新增用户TODO、不安装、不推送；中文文档、英文注释和英文Conventional Commits。
- 异步／IPC测试沙箱外且有限超时，保留失败证据、清理自有进程；当前文档只描述最终支持行为。

## Review Focus

1. 原生缺失或相互矛盾执行证据、非法PNG仍可能触发本地错误：不得恢复许可或写坏文件。
2. 原生采样成功但旧许可不同／为空／被取消：本地错误不得建立或恢复旧许可。
3. 目标发布成功后清理失败及未知I/O结果：提示结果可能已存在，不错误恢复；不覆盖已有文件。
4. 配置关闭和任意未知工具：只明确截图开关错误，其他工具的行为和许可不变。
5. 套件复用与独立主菜单／headless：只访问传入IPC，工具数不手工维护，操作遵循实际available_actions。

### Task 1: 本地错误原因及证据驱动恢复

**Files:** screenshot_tool.py、game_session.py、mcp_server.py、tool_registry.py；新增tests/python/test_screenshot_recovery.py，补充test_screenshots.py。

**Interfaces:** ScreenshotError提供受控公开错误及是否明确保存拒绝；GameResponse使用独立CAPTURED_READ_ONLY证据携带采样token，错误恢复仅file effect且同token。其他动作策略不变。

- [x] 先写测试：同名、目录是文件、长Unicode名后直接动作；缺失／矛盾证据、冷调用、变更令牌、坏PNG、未知I/O、原生错误和保存期间取消均不恢复；OS原因、清理失败和禁用配置提示。
- [x] RED运行新模块（90秒上限）；Expected：旧行为确实在恢复与提示上失败，保留输出。
- [x] 实现受控错误映射和局部捕获；正面执行证据在文件保存前检查，保存拒绝后保留合法token；配置关闭提供配置恢复提示，元数据精简。
- [x] GREEN：截图相关模块及全量Python通过；Expected：不影响其他工具许可，所有新负例通过。仅升级MCP0.83.0并同步现行许可说明。
- [x] 提交独立变更，记录测试结果。

### Task 2: 隔离实测、文档、样例与最终审阅

**Files:** verify_screenshots.py、tests/game/suite.py、gui_suite_screenshots.json、截图指南与工具清单、带日期实施记录及样例；只更新README中的MCP基线。

**Interfaces:** 使用Task1的具体错误及保留许可行为；verification_runtime.ipc_directory/ensure_run支持复用对局，独立模式保持主菜单及headless验证。

- [x] 迁移验证器及套件；比较tool_definitions提供的实际集合，报告与配置使用新路径；只有实际可用操作才调用。Expected：不连接旧共享IPC。
- [x] GUI测试战斗／选牌／战场／地图／牌组、同名／目录错误／长名字后直接动作；独立主菜单冷调用、关闭配置与headless。Expected：PNG与原生字节一致、无新增许可、不同状态及原生失败保守。
- [x] 更新现行指南、导出原样JSON和来源；运行样例／PNG重放、版本、链接、进程退出核验；全量Python按实际新增变更运行，不重建C#或重复无关GUI。
- [ ] 全分支仅一次新上下文独立审阅。Critical/Important单轮TDD修复与受影响验收，Minor和搁置范围完整记录，不二次派审。
- [ ] 完成核销44/44、自行合main、归档校验后删除本计划工作区、清理分支；Expected：工作区干净、未安装／推送，未隐藏遗留。
