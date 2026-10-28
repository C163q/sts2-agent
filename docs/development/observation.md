# 战斗观察 JSON

适用于 Linux 游戏 `v0.107.1` 与 Mod `0.3.0`。底层观察结构版本为 `3`，输出语言为英语，游戏本身可以继续使用中文。信息范围遵循 [可见信息边界](../observation.md)，安装见 [正常游戏加载与读取](live-game.md)。

## 读取和控制信息

重新构建、安装 Mod 并重启游戏后执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc get_state > .tmp/live/observation.json
```

默认输出面向 LLM 的玩法内容，成功结果直接包含 `scene`、`screen`、`player` 等字段，没有 `ok`、外层 `state`、请求 ID、状态令牌、会话、结构版本或语言字段。版本、种子、Mod 调试覆盖层也不再作为玩法内容返回。

需要控制信息或排查问题时执行：

```sh
python3 scripts/roundtrip_client.py --ipc-dir .tmp/live/ipc get_state --raw
```

`--raw` 保留原始文件协议：成功为 `id/ok/state`，`state` 内保留 `snapshot_id/schema_version/language/session/combat_generation`；失败为 `id/ok/error`。Python 的 `Client.call()` 同样返回原始响应，`player_result(response)` 产生面向 LLM 的结果，不改写原响应。外部客户端必须自行保存最近的原始令牌，动作仍带 `expected_state` 校验；省略 LLM 可见令牌不等于绕过校验。当前尚未接入正式 LLM 工具框架。

## 玩法字段

| 字段 | 内容 |
| --- | --- |
| `scene`、`screen.status` | 当前场景，以及 `visible/covered/hidden/not_ready/not_applicable` |
| `turn` | 当前结束回合按钮显示的回合号；未显示数字时为空 |
| `player.character` | 当前可见角色身份，例如 `IRONCLAD` |
| `hp`、`max_hp`、`hp_display` | 实际显示的生命数字，以及 `numeric/dead/infinite/hidden/unknown` 显示状态；用于角色和敌人 |
| `block`、`energy`、`max_energy`、`stars` | 当前可见资源与计数 |
| `player.hand[]` | 从左到右排列的当前可见手牌，包含稳定 ID、名称、固有属性、显示费用与标记，不含卡牌正文 |
| `powers[]` | 实际显示状态图标的英语名称和可见计数，不枚举全部模型状态 |
| `enemies[]` | 从左到右排列的可见敌人身份、定位 ID、生命、格挡、状态图标和当前意图 |
| `intents[]` | 当前渲染意图的 `category/value`，不读取下一招模型或悬停说明 |
| `draw_count/discard_count/exhaust_count` | 当前可见牌堆计数，不返回内容或顺序 |
| `top_bar` | 金币、总楼层、可见进阶等级、主牌组数量、房间图标、首领、药水槽、遗物及入口可见性 |
| `top_bar.bosses` | 实际显示的首领名称数组，例如 `["Ceremonial Beast"]`；未识别的可见图标以槽内 `null` 保留 |
| `top_bar.potion_slots` | 按位置排列；槽内 `null` 是已确认空槽，非空为含 `name` 的对象，整个字段为 `null` 是未能观察槽位 |
| `buttons.end_turn` | 当前按钮的英语文字与启用状态 |
| `available_actions` | 当前已实现动作的可用性；不是完整工具目录 |

数字来自可见标签，金币动画期间也按标签返回。`null` 不等于 0，表示未显示、尚未准备或不能可靠识别；可见空容器使用 `[]`。正常生命条没有格挡图标时才归一化为 `block: 0`。死亡文字与无限图标分别映射为 `dead`、`infinite`，不从隐藏生命模型补数字。

## 手牌与身份

单张已识别卡牌的示例：

```json
{
  "id": 0,
  "name": "Defend",
  "type": "Skill",
  "rarity": "basic",
  "visual_card_pool": "ironclad",
  "energy_cost": "1",
  "star_cost": null,
  "unplayable_markers": [],
  "outline": "cyan"
}
```

- `id` 对应卡牌实例，在同一战斗和 Mod 会话中稳定。同名副本使用不同 ID；重新抽到同一实例复用 ID，ID 不因位置改变而重排。普通抽牌按实际发生顺序分配，生成等其他来源在首次可见时分配。身份映射仅使用过去的本地抽牌记录与当前可见卡牌，不输出隐藏牌内容或位置；重启进程不保证相同编号。
- `type` 为攻击、技能等固有牌型，已识别卡牌直接给出实际值，不要求小标签在画面中展开。`rarity` 为固有稀有度；普通横幅颜色不能单独区分 `basic/common`，这里明确允许按已识别身份补充。`visual_card_pool` 使用实际外观卡池，与真实卡池不同的特殊牌不暴露真实卡池。
- 未知或锁定牌不输出真实名称、牌型、稀有度或卡池，仍可通过不含内容语义的 ID 定位。
- `energy_cost/star_cost` 是显示字符串，保留 `X`、`?` 等形式。`energy_cost_color/star_cost_color` 仅在文字出现特殊颜色时输出 `red/green/blue/other`，默认颜色省略字段；不输出 RGB 或费用图标配色。
- `unplayable_markers` 合并标记位置：`[]`、`["energy"]`、`["star"]` 或二者都有。没有标记不等于可以打出。
- `outline` 为 `none/cyan/gold/red/other`，只表达当前描边，不据此声明动作合法。
- 后续手牌详情调用一次返回全部当前手牌及其效果，沿用这些 ID。本次没有实现该调用，基础观察仍不输出完整效果、关键词或目标规则。

## 失败结果

默认失败结果为 `{"error":{"code":"stale_state","message":"...","recovery":"get_state"}}`，没有 `ok`。`message` 使用英语，提供可指导下一步的提示，内部异常路径和堆栈留在原始诊断响应或游戏日志中。

| 错误 | 建议处理 |
| --- | --- |
| `stale_state`、`illegal_action`、`expired_request` | `recovery: get_state`，重新观察后再选择动作 |
| `invalid_request` | `recovery: correct_request`，修正参数 |
| `timeout`、`game_error` | 标记 `outcome: unknown`，重新观察，不自动重试动作 |
| `transport_error` | 标记结果未知，`recovery: check_connection`，先检查连接 |

成功请求不自动重试动作。客户端等待超时也输出结构化错误；默认输出不会把原始异常信息直接交给 LLM。失败时命令仍以非零退出码结束。

## 采样与验证

读取在主线程执行，图形模式使用 `RenderingServer.FramePostDraw`，无头验证回退到 `SceneTree.ProcessFrame`。动作完成后最多等待 2 秒，尝试取得连续 250 毫秒未变的观察；仍变化时返回当前结果。读取不刷新 UI、不切换全局语言，英语名称独立读取游戏资源表。

显示检查覆盖有效性、显示开关、父级透明度、视口、祖先裁剪和描边 Shader 宽度。打开菜单、教学、详情或过渡期间保守返回 `covered`。当前仍用矩形近似，不承诺逐像素判断卡牌之间或任意 Mod 图层的遮挡。

按 [往返指南](roundtrip.md) 构建后，在独立实例验证：

```sh
python3 scripts/prepare_roundtrip.py --game-dir "$HOME/.local/share/Steam/steamapps/common/Slay the Spire 2" --language zhs
```

```sh
python3 scripts/run_roundtrip.py --windowed --capture --check-observation
```

```sh
python3 scripts/verify_roundtrip.py --ipc-dir .tmp/roundtrip/ipc --report .tmp/roundtrip/player-format-roundtrip.json --observation-output .tmp/player-observation-v3.json
```

独立测试入口创建铁甲战士临时战斗并关闭该测试存档的教学。截图和布局、临时 UI 扰动检查仅由测试标志启用；正常游戏不启用测试环境变量。当前调整及验证记录见 [实施说明](../research/2026-10-29-player-observation-plan.md)，上一版图形验证见 [历史记录](../research/2026-10-29-visible-combat-validation.md)。
