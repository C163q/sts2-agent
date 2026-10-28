# 战斗观察 JSON

适用于 Linux 游戏 `v0.107.1` 与 `spikes/roundtrip/` 原型。`get_state` 返回版本为 `2` 的观察结构，名称与已识别按钮文字使用英语，游戏本身可以继续使用中文。信息范围遵循 [可见信息边界](../observation.md)，安装与请求方式见 [正常游戏加载与读取](live-game.md)。

## 读取和保存

重新构建、复制 Mod 并重启游戏后，在战斗中执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc get_state > .tmp/live/observation.json
```

该文件是一次请求的完整 JSON 响应。成功时读取 `state`；失败时读取 `error.code` 与 `error.message`。只调用 `get_state` 不会出牌、结束回合、悬停卡牌或打开牌堆。

## 字段

| 字段 | 内容 |
| --- | --- |
| `schema_version`、`language` | 当前为 `2`、`en` |
| `screen.status` | `visible`、`covered`、`hidden`、`not_ready` 或非战斗时的 `not_applicable` |
| `turn` | 从当前结束回合按钮文字读取的回合号；按钮未显示数字时为空 |
| `player` | 可见角色身份、生命与上限、格挡、能量与上限、星星、状态图标、手牌及可见牌堆计数 |
| `enemies` | 按画面横向位置排列的敌人身份、生命与上限、格挡、状态图标和当前意图；保留仍可见的移除中节点 |
| `player.hand[]` | 手牌位置、可识别身份、可见名称和类型、能量及星星费用、费用文字颜色、不可打出标记、外框颜色；不含卡牌正文 |
| `powers[]` | 实际显示状态图标的英语名称和可见计数；不枚举全部模型状态 |
| `intents[]` | 当前渲染意图的 `category` 与 `value`；不读取敌人的下一招模型或悬停说明 |
| `top_bar` | 金币、总楼层、可见进阶等级、主牌组数量、房间与首领图标、药水槽和遗物、地图等入口的可见性 |
| `buttons.end_turn` | 当前结束回合按钮的英语文字及启用状态 |
| `overlay` | 实际显示的版本、种子和 Mod 提示文字；不从随机状态补种子 |
| `snapshot_id`、`session`、`combat_generation`、对象定位标识 | 通信及控制元数据；不代表额外可见玩法信息 |
| `available_actions` | 已实现动作的可用性，仍只逐步维护现有结束回合及测试入口 |

数字来自可见标签，金币动画期间也按标签返回。费用颜色以实际标签的 `#RRGGBB` 返回；`energy_unplayable_marker`、`star_unplayable_marker` 只表示对应标记可见，不据此判定资源不足。`energy_cost`、`star_cost` 与意图 `value` 是字符串，保留 `X`、`?`、攻击次数等显示形式。`position` 从 0 开始。

`hp_text` 保留数字生命文字或识别后的英语死亡文字；`hp_infinite` 表示当前是否显示无数字无限生命图标，不根据隐藏的生命模型推断。没有格挡图标时，只有生命条正常显示才归一化为 `block: 0`。

`null` 表示未显示、节点尚未准备或暂不能可靠识别；不能当作 0。已显示容器中没有对象时使用 `[]`，例如没有可见状态图标；空药水槽使用 `empty: true`。未知或锁定卡牌不返回真实模型标识。英语资源缺失或名称模板不能安全解析时名称为空，不回退输出其他语言或完整描述。

`intents.category` 根据当前图标纹理识别，包含 `attack`、`buff`、`debuff`、`defend`、`status` 等；相同图像不额外区分模型中的强弱。无法识别的图标使用 `unrecognized`，不补招式细节。

与早期原型相比，手牌由字符串数组改为对象数组，移除了内部 `phase`、`side`、`round`。客户端应按 `schema_version` 处理结构变化。

## 显示条件与采样

观察在游戏主线程执行，图形模式使用 `RenderingServer.FramePostDraw`，无头验证回退到 `SceneTree.ProcessFrame`；无头数据不能证明像素可见。动作完成后最多等待 2 秒，尝试取得连续 250 毫秒未变的观察；仍在变化时返回当时结果，不保证所有动画均已结束。读取不调用 UI 刷新，也不切换全局语言。英语名称独立读取游戏的 `res://localization/eng/` 表。

显示检查覆盖节点有效性、显示开关、父级透明度、视口及祖先裁剪区域。生物根节点和卡牌布局容器可能没有尺寸，分别检查实际身体、卡面等显示节点。描边还核对 Shader 宽度。打开菜单、覆盖层、教学、卡牌或遗物详情及画面过渡时，当前实现保守返回 `covered`，暂不导出战斗内容，也不提供战斗动作。

状态令牌包含当前导出的 UI 内容，动画或焦点变化也可能令旧令牌失效。动作仍核对当前令牌与合法性；收到 `stale_state` 时重新观察，不能绕过校验。

当前实现不是完整的像素遮挡分析器：旋转区域按包围矩形近似，尚未逐像素判定卡牌之间或任意 Mod 图层之间的遮挡。详情正文、完整关键词、未打开的牌堆内容、后续招式、内部阶段和随机状态不在观察中。悬停正文仍留给后续专门查看调用。

## 独立验证

按 [往返指南](roundtrip.md) 构建后，可将独立测试实例设为中文，再验证英语 JSON：

```sh
python3 scripts/prepare_roundtrip.py --game-dir "$HOME/.local/share/Steam/steamapps/common/Slay the Spire 2" --language zhs
```

```sh
python3 scripts/run_roundtrip.py --windowed --capture --check-observation
```

另一个终端执行：

```sh
python3 scripts/verify_observation.py --ipc-dir .tmp/roundtrip/ipc --output .tmp/observation-v2.json
```

测试入口仅在独立测试模式中创建临时铁甲战士战斗，并关闭该测试存档的教学。`--capture` 在读取时保存 `.tmp/roundtrip/observation.png` 和仅用于开发诊断的节点布局 `.layout.json`；它们不属于面向 LLM 的观察响应。`--check-observation` 临时改变 UI 的显示条件、立即还原并输出 `.tmp/roundtrip/observation-checks.json`，覆盖隐藏、移出屏幕、透明父节点、隐藏费用、费用文字颜色、描边、生命、意图、金币和过渡遮挡。

正常游戏只设置 `STS2_AGENT_IPC_DIR`，不要启用上述测试模式、测试截图或过滤检查环境变量。实测范围与未覆盖情形见 [本次验证记录](../research/2026-10-29-visible-combat-validation.md)。
