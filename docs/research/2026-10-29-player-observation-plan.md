# 面向 LLM 的观察格式调整

当前状态：已完成。客户端投影、Mod 字段、文档和验证均已完成，已安装 Mod `0.3.0`；手牌批量详情调用仅记录要求，留待后续实现。无阻塞。

## 已确认要求

- 基础观察使用英语。保留 `screen.status`，不自动展开手牌正文。
- 手牌 ID 按同一卡牌实例保持整场战斗稳定，重复抽到复用；数组顺序表示当前手牌位置，不以 ID 表示位置。普通抽牌按抽牌发生先后编号，生成等非抽牌来源在首次可见时编号。
- 已识别卡牌可直接提供固有 `type`、`rarity` 和 `visual_card_pool`；外观卡池使用游戏的 `VisualCardPool`。不因此附加效果、关键词和目标规则。
- 描边为 `none/cyan/gold/red/other`。能量和星星费用文字颜色统一转为 `red/green/blue/other`，默认颜色不输出颜色字段。费用图标配色不单独输出。
- 两个不可打出标记合并为 `unplayable_markers` 数组，值为 `energy`、`star`；不等价于动作合法性。
- 生命用数字与 `hp_display` 表达，保留数字、死亡、无限和隐藏显示的区别，删除重复 `hp_text` 与旧 `hp_infinite`。
- 首领使用 `bosses` 名称数组；空药水槽使用槽内 `null`，槽位未知使用整个字段 `null`。遗物依数组保留位置。
- 给 LLM 的成功结果不包含 `ok`、请求/会话/状态令牌、版本及 Mod 调试覆盖层。失败结果包含英语 `error.code/message/recovery`；超时必须说明执行结果未知，不自动重试。
- 后续手牌详情调用一次返回全部当前手牌，沿用稳定卡牌 ID。本次仅记录该要求，不增加详情工具或其他动作。

## 实现选择

直接删除底层控制字段会破坏动作校验；另建完整协议则超出本次范围。沿用现有文件协议，Mod 升级为观察结构 `3` 并精简玩法字段，Python 客户端默认输出面向 LLM 的投影，`--raw` 输出保留控制信息的原始响应。客户端未来接入工具时复用同一投影；本次不实现 LLM 集成。

卡牌身份私有映射依据对象引用，抽牌先后来自已核对的 `CombatManager.History` 与 `CardDrawnEntry.Card`。映射只输出当前可见卡牌 ID，不返回隐藏牌内容或位置。中途启用时可用现有抽牌历史恢复编号；ID 属于控制元数据。

基线为本地 Linux 游戏 `v0.107.1`、提交 `59260271`。接口依据为 `data_sts2_linuxbsd_x86_64/sts2.dll`：`NCard` 费用显示、`NHandCardHolder` 描边、`NHealthBar.RefreshText`、`CardModel.Rarity/Type/VisualCardPool`、`CombatHistory.Entries` 与 `CardDrawnEntry.Card`；反编译证据仅保存在 `.tmp/decompiled/`。

## 实施与验证

1. 在 `scripts/roundtrip_client.py` 增加成功/错误投影与 `--raw`，先写测试验证控制字段剥离、玩法字段保留、错误分类和超时不重试。
2. 修改 `CombatObservation`、`GameAdapter`，新增私有卡牌身份映射；调整独立游戏检查，覆盖 ID 唯一、复用与重置、默认/特殊双费用颜色、无标签实际牌型、生命显示与隐藏过滤。
3. 更新现行接口及边界文档。构建后在独立中文图形实例验证英语 JSON、可见性过滤、结束回合及旧状态/非法/重复请求回归。安装只复制已验证的 Mod 文件，不驱动正式存档战斗。完成后提交本次变更。

## 验证结果与边界

- 最终构建成功，0 个警告、0 个错误；Python 7 项检查通过，包含原安装路径隔离检查及成功/错误投影、未知字段不转发。
- 独立中文图形实例 27 项检查通过，覆盖引用身份与重置、隐藏再显示 ID、实际牌型、双费用特殊/默认颜色、生命文字/无限图标、透明/离屏/过渡遮挡，以及隐藏药水槽不压缩位置。临时 UI 扰动均立即还原，不改动正常游戏状态。
- 完整往返通过：回合 `1 → 2`、生命 `80 → 73`，读回一致，旧状态、非法动作和重复请求均通过。继续推进到第 3 回合后，原手牌 ID `1` 经洗牌重新抽到仍复用；未枚举隐藏牌堆来证明这一点。
- 默认 CLI 的旧状态错误输出为英语结构化 `error`，退出码为 1；`--raw` 与默认投影的玩法内容一致。
- 同次观察示例及截图：`.tmp/player-observation-v3.json`、`.tmp/player-observation-v3.png`；原始响应 `.tmp/player-observation-v3-raw.json`；过滤检查与往返、重抽证据位于 `.tmp/roundtrip/observation-checks.json`、`player-format-roundtrip.json`、`card-id-redraw.json`。原始游戏资源与产物不纳入 Git。
- Mod DLL 和清单已更新到本机 Steam 安装的 `mods/Sts2Agent/`，安装文件与构建产物的 SHA-256 一致。正式存档未用于动作验证；用户需重启正常游戏后重新读取。

代码审阅发现原槽位过滤会压缩位置，已改为未知时整体为空并补充回归；临时问题记录在 `.tmp/2026-10-29-potion-observation-report.md`。真实星星角色的完整战斗、任意 Mod 显示改写、多人及逐像素遮挡仍未覆盖；本次双费用颜色检查针对实际标签显示规则，不能替代完整角色流程验证。
