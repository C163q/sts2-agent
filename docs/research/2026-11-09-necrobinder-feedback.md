# 死灵契约师游玩反馈核验

> 当前状态：已完成。共 3 项，已完成 3 项；证据核对、两处输出改进、note 精简、文档与验证均已完成，无遗留事项。

## 基线与证据

核对日期为 2026-11-09；游戏为 Linux release v0.107.1、build 59260271，RitsuLib 0.6.10。反馈对应 Mod 0.84.0、MCP 0.87.0。

交付版本为 Mod 0.85.0、MCP 0.88.0，底层 schema 保持 49；出牌来源原本为可选字段，奖励原因同样按可选字段兼容旧响应。

游戏目录示例为 `~/.local/share/Steam/steamapps/common/Slay the Spire 2`，程序集证据为其 `data_sts2_linuxbsd_x86_64/sts2.dll`。本次核对 `CreatureCmd.Damage`、`Creature.LoseHpInternal`、`DieForYouPower`、`Nibbit`、`PenNib`、`Reave`、`Fetch`、`CardCmd.PreviewInternal`、`PotionReward.OnSelect`、`Reward.SelectUnsynchronized` 和 `NRewardButton.GetReward`，反编译文件放在忽略目录 `.tmp/2026-11-09-necrobinder-feedback/source/`。

原始回执位于 `.tmp/live/ipc/responses/`；这局从 03:30 左右开始，截图包含 `.sts2-agent/screenshots/14-combat-osty.png` 等。与之前对局的文件通过时间和状态中的角色区分。本次测试证据位于 `.tmp/2026-11-09-necrobinder-feedback/`，均不纳入 Git。

## 逐项判断

### 1—3. 格挡、Osty 与攻击意图

反馈把不同回合的意图与已结算的事件配在一起，未发现所述账目错误。

`c2679971e48d43db84d639e94d26a5ed.json` 是攻击前的完整状态：玩家 50 HP、5 格挡，Osty 1 HP，唯一敌人 Nibbit 已有 2 Strength，当前攻击意图为 **14**。`79ee81d11e944b6b8367b176b721ce2e.json` 结束回合后记录：

- Osty 失去 1 HP，随后死亡；
- 玩家事件包含 `blocked:5, hp_loss:8`，玩家生命变为 42；
- 新玩家回合开始后，Osty 复活为 1 HP；
- Nibbit 已切换下一次攻击与防御意图，显示 **8**。

本次伤害为 `14 = 5 格挡 + 1 Osty 生命 + 8 玩家生命`。截图 `14-combat-osty.png` 展示的是结算后玩家 42 HP、Osty 已复活、下一次意图 8 的画面。

另一组 `bb1724697c014871a290fc2f8fb4ee4c.json → 9b00099a42244d9fa0c36f4467a5eba8.json` 中，攻击前意图为 **6**，Osty 从 7 HP 降为 1 HP，玩家未失血，随后意图转为 buff。更早的 `992f8793fa424f7fb107589d1e697be5.json` 才是 **12** 点攻击，被 12 格挡完全抵消。两只 Nibbit 的另一回合则记录 `14 = 7 Osty 生命 + 7 玩家生命`，见 `6e2bccae34d84885a5573620a3629601.json`。

原生先处理主人格挡，再由 Die for You 将适用的剩余攻击交给 Osty，超过 Osty 生命的部分回到主人；接口按实际承受者记录。保留这些事件，避免把两个生物的生命变化合并成单一目标。伤害事件保留实际生命损失；过量伤害、减伤和转移使通用的 `incoming = blocked + hp_loss` 并不适合作为每条目标事件的不变量。

观察提示仅简述意图已含当前预览修正，格挡和伤害转移会影响生命损失。前后回合的对照说明保留在开发指南与本核验记录中。

### 4. Pen Nib 计数

`ace1ba5e85f54447bacf6ee62f644402.json` 的 Unleash+ 回执确实包含 `9→0→10→0`。原生在第十张攻击开始时先把计数取模归零，再进入激活动画并显示 10，约一秒后恢复真实计数。在此期间，原生用当前攻击实例决定翻倍；显示 10 的时段可能覆盖批次中的后续牌。

现有 `relic_counter_changed` 定义为标签变化，保留每次原生标签刷新，包括同帧刷新；它不是伤害乘数或独立触发事件。保留该语义，并在维护指南说明这些数值与攻击的关系。独立实例分别使用 Anger 和不生成卡牌预览的 Strike 验证：均正确翻倍，回执后采样 1.6 秒期间令牌稳定，直接续接出牌成功，未复现显示等待遗漏。

### 5. Soul 的初次去向

找到 4 条 `pile:null` 的 Soul/Soul+；例如 `21f3ef01bb6e412caac826a62c0a6de8.json` 中 Reave 生成 Soul 后，Fetch 紧接着抽到了同一 ID 的牌，结束时该牌在手中。

Reave 原生先入抽牌堆，再启动异步预览。`CardCmd.PreviewInternal` 在预览结束时重新读取卡牌所在牌堆，决定飞牌目标；Fetch 可以在预览完成前抽走它。因此画面可能只公开 Soul 的身份和后来的手牌，未显示最初进入抽牌堆。`pile:null` 保留这段未知，后续 `card_drawn` 和当前手牌分别表达已确认的移动与位置。

独立实例对照：单独 Reave 返回 `pile:"draw"`；Reave→Fetch 批次返回 `pile:null`，同时存在同一 ID 的 `card_drawn` 与手牌。保留当前信息边界。

### 6. card_played.source

这局 192 次出牌都是手动出牌，均未记录触发来源。default 按现行规则保留事件内的 null，所以该预设同样会输出 `source:null`。自动出牌可带已核实的卡牌、power、遗物等来源，因此字段整体仍有用途。

普通手动出牌改为省略 `source`，full/default 一致；自动出牌继续保留已核实来源，无法确认时保留 null。其他事件的 null 规则保持现行契约。

### 7. 药水满槽领取

`3a84d9ef874e4d1dac7361a4aa47dd47.json` 中药水栏已有 Swift Potion、Vulnerable Potion 和 Bottled Potential；领取 Colorless Potion 返回 `not_claimed`，奖励行保留。

`not_claimed` 对应原生奖励流程返回未领取的通用分支，继续保留；`CardReward.OnSelect` 也根据选择是否完成返回布尔值。目标版本 `PotionReward.OnSelect` 只有在 `PotionProcureFailureReason.TooFull` 时返回 false；该已确认分支附加 `reason:"potion_belt_full"`。原因来自本次原生领取结果，其他结果不按事后槽位猜测。

## 实施与验证

意图、手牌数值、页面更新三条 note 均保留简短的必要说明。维护文档描述规则与核验依据，工具输出不针对本次误读增加长篇提示。

| 检查 | 结果与证据 |
| --- | --- |
| 修改前原生与手动来源 | `red-native/report.json` 前 3 局通过：Pen Nib Anger、Soul、Osty；第 4 局按预期失败，普通手动出牌含 source:null |
| Pen Nib 无生成牌预览 | `strike-pen/report.json` 通过：Strike 正确造成 12 点伤害，记录 9→0→10→0，回执后令牌稳定且可直接续接 |
| 修改前满槽领取 | `red-reward/report.json` 按预期失败：有 not_claimed，缺少具体原因 |
| 奖励原因投影与非法组合 | 新增两项 Python 测试先失败后通过，覆盖原因保留、未知原因、错误类型和状态矛盾 |
| 最终真实 MCP | `green/report.json` 的 5 局通过：Pen Nib、Soul、手动／自动来源、药水满槽与恢复领取、Osty 拆分；full/default 满槽原因一致，腾出槽位后正常 claimed |
| Python 全量 | 862 项通过，包含最终 note 与固定输出基线 |
| C# 纯检查 | 155 个 PASS |
| Mod 构建 | 0 警告、0 错误；最终游戏验证 DLL 与构建产物哈希一致 |
| 文档与格式 | 271 个本地链接目标存在，改动 Python／JSON 可解析，`git diff --check` 通过 |

本次使用隔离游戏存档、IPC 与自有进程，结束后已清理。本次未安装正式游戏目录的 Mod，也未操作正式对局。
