# 先古馈赠选择恢复与反馈计划

> 当前状态：实施中，共1项，已完成0项；实现与18组验收已完成，剩余提交、独立审阅及合并清理。无阻塞。

## 范围与依据

用户已确认[三项整改](../../research/2026-11-07-choose-ancient-option-review.md#建议的处理范围)：修复明确拒绝后的许可恢复、具体诊断和卡牌包遗物事件遗漏。按用户要求在TODO新增升级至v0.111后的致死馈赠崩溃复测；该原版可复现问题不在本次修复或GUI运行范围。

参数维持option_id及default/full，成功保持精简回执和原生领取／选择／奖励流程。源码基线da5edf8，目标游戏v0.107.1、RitsuLib0.6.10、Godot4.5.1。Mod0.78.1、MCP0.80.1，schema46不变；版本统一维护README。

## 文件职责及边界

- AncientInspection集中页面、选择动作和选项不可用原因，执行入口、enabled及available_actions共用。适配器只对choose_ancient_option的明确点击前拒绝启用已有保证；advance_dialogue错误恢复留在后续审阅。
- RunResourceJournal的原生选牌入口／出口可见性：当前早退在CardSelection存在但未就绪时把仍画出的顶栏判为不可读，导致RunInventoryJournal清理挂起事件。仅核验并修正已识别原生选择页的过渡读取，不保留真实隐藏期间的事件、不从持有模型补造名称。
- tests/python/test_ancient_choice_recovery.py验证真实会话／注册策略；新GUI验证器覆盖原生拒绝与正常回执。现有RunInventoryChecks验证隐藏／中断获取仍不会回放。
- 复用现有测试夹具，无新增公开工具或私有测试入口。旧审阅样本保持原样，输出修复后实际样本。

## Task 1: 修复并交付先古选择契约

- [x] Python测试先行：明确保证保留旧许可、冷调用不授予许可、非法本地参数保留许可、stale／已交互／未知／矛盾结果撤销；运行RED。
- [x] GUI先在旧DLL验证卡牌包遗物获取断言失败，保留原始响应与日志。
- [x] 集中选择页面／动作／按钮拒绝并接入注册恢复策略；可见选项仍按原生鼠标点击规则执行，不拓展离屏点击。
- [x] 只移除原生已知选择过渡顶栏读取中的过早拒绝，验证卡牌包事件GREEN；若事实不支持该原因，记录调查后调整最小实现。
- [x] 运行专项及全套Python、C#检查，最终构建后准备隔离运行时；不得因提交重建DLL。
- [x] GUI覆盖无房间、有效／无效ID、本地与原生参数、对话、完成、地图／牌组、禁用／隐藏／离屏、选牌／卡牌包／奖励、stale，以及旧事件可见性和先古稳定性回归；不选择致死馈赠。
- [x] 同步接口、TODO与清单，保存实际返回和边界；交付检查后提交fix: preserve ancient choice permission and feedback。

### 验证命令与预期

- `timeout 60s .tmp/mcp-venv/bin/python -m unittest tests.python.test_ancient_choice_recovery`：RED缺少恢复策略，接入后GREEN。
- `timeout 180s .tmp/mcp-venv/bin/python -m unittest discover -s tests -t . -p 'test_*.py'`：完整通过，异步stdio在沙箱外运行。
- `dotnet build Sts2Agent.sln -m:1 --no-restore`：加载.env指定Sts2Dir及RitsuLibDir，90秒超时；零错误。C#检查用dotnet run --no-build --no-restore，45秒超时，全部通过。
- `scripts/gui_suite.py --suite tests/game/data/gui_suite_ancient_choice_recovery.json --output <新目录>`：新建隔离进程与证据，全部用例通过、进程退出、最终DLL哈希一致。
- 交付脚本核对测试日志、样本来源与重放、链接、版本、进程、TODO计数与DLL；最终task-done运行该交付脚本，不重复已有完整测试。

## 独立审阅与收尾

实现验收后一次独立整分支审阅；重要问题一次测试先行修复，轻微建议记录，不安排复审。归档并校验本计划技能目录后删除，合入main并删除临时分支，不推送或正式安装。

### Review Focus

明确拒绝只能恢复已有且有效的许可，stale／未知／已交互或坏响应必须撤销；选择动作与可用性判断应一致，推进对话恢复不能因共享分支被意外改变。顶栏过渡修复只允许仍真实显示的已知原生选择页，地图／牌组／模态／隐藏UI不能泄露信息；隐藏后恢复不得回放物品变化。卡牌包应记录已显示遗物一次，不提前记录未选定包内卡牌。保持原生动作、状态令牌、精简default/full及不确定结果语义。已知原版崩溃仅加入v0.111升级后复测，不修改游戏规则或在本轮重新触发。
