# 火堆详情修复后实际完整返回

全部来自隔离游戏及真实MCP structuredContent；版本、证据与限制见[实施记录](../2026-11-06-rest-site-inspection-presets-implementation.md)。

共30份：24份full、2份default、4份summary；所有正文均保留实际返回，无图像内容。offscreen/no_hover/hidden/transparent/clipped/fade是受保护测试夹具构造的显示状态，不能当作普通游玩自然出现的样本。

get_observation的火堆主体与inspect_rest_site.summary均省略description；其他空值遵循各自preset，所以full仍可含proceed:null。

| 文件 | 工具与参数 | 场景标记 |
| --- | --- | --- |
| [inspect.full.json](inspect.full.json) | `inspect_rest_site({"preset": "full"})` | basic_initial |
| [inspect.default.json](inspect.default.json) | `inspect_rest_site({"preset": "default"})` | basic_default |
| [inspect.summary.json](inspect.summary.json) | `inspect_rest_site({"preset": "summary"})` | basic_summary |
| [observation.full.json](observation.full.json) | `get_observation({"preset": "full"})` | basic_observation_full |
| [observation.default.json](observation.default.json) | `get_observation({"preset": "default"})` | basic_observation_default |
| [observation.summary.json](observation.summary.json) | `get_observation({"preset": "summary"})` | basic_observation_summary |
| [filtered.summary.json](filtered.summary.json) | `inspect_rest_site({"preset": "summary", "option_ids": ["SMITH", "HEAL", "SMITH", "UNKNOWN"]})` | basic_filtered |
| [empty-filter.full.json](empty-filter.full.json) | `inspect_rest_site({"preset": "full", "option_ids": []})` | basic_empty_filter |
| [disabled.full.json](disabled.full.json) | `inspect_rest_site({"preset": "full"})` | disabled_initial |
| [tent.full.json](tent.full.json) | `inspect_rest_site({"preset": "full"})` | tent_initial |
| [tent-after-lift.full.json](tent-after-lift.full.json) | `inspect_rest_site({"preset": "full"})` | tent_after_lift |
| [heal-with-reward.full.json](heal-with-reward.full.json) | `inspect_rest_site({"preset": "full"})` | heal_rewards_initial |
| [dig.full.json](dig.full.json) | `inspect_rest_site({"preset": "full"})` | dig_initial |
| [activity-complete.full.json](activity-complete.full.json) | `inspect_rest_site({"preset": "full"})` | activity_complete |
| [no-hover.full.json](no-hover.full.json) | `inspect_rest_site({"preset": "full"})` | no_hover_full |
| [no-hover.summary.json](no-hover.summary.json) | `inspect_rest_site({"preset": "summary"})` | no_hover_summary |
| [no-hover-filtered.full.json](no-hover-filtered.full.json) | `inspect_rest_site({"preset": "full", "option_ids": ["SMITH"]})` | no_hover_filtered |
| [offscreen.full.json](offscreen.full.json) | `inspect_rest_site({"preset": "full"})` | offscreen_full |
| [offscreen-observation.full.json](offscreen-observation.full.json) | `get_observation({"preset": "full"})` | offscreen_observation |
| [hidden.full.json](hidden.full.json) | `inspect_rest_site({"preset": "full"})` | hidden_full |
| [transparent.full.json](transparent.full.json) | `inspect_rest_site({"preset": "full"})` | transparent_full |
| [clipped.full.json](clipped.full.json) | `inspect_rest_site({"preset": "full"})` | clipped_full |
| [fade.full.json](fade.full.json) | `inspect_rest_site({"preset": "full"})` | fade_full |
| [fade-observation.full.json](fade-observation.full.json) | `get_observation({"preset": "full"})` | fade_observation |
| [map-covered.full.json](map-covered.full.json) | `inspect_rest_site({"preset": "full"})` | map_covered |
| [deck-covered.full.json](deck-covered.full.json) | `inspect_rest_site({"preset": "full"})` | deck_covered |
| [selection-covered.full.json](selection-covered.full.json) | `inspect_rest_site({"preset": "full"})` | selection_covered |
| [reward-covered.full.json](reward-covered.full.json) | `inspect_rest_site({"preset": "full"})` | reward_covered |
| [no-rest-first-read.full.json](no-rest-first-read.full.json) | `inspect_rest_site({"preset": "full"})` | no_rest_first_read |
| [no-rest-existing-permission.full.json](no-rest-existing-permission.full.json) | `inspect_rest_site({"preset": "full"})` | no_rest_existing_permission |

来源位置与SHA-256见[manifest](manifest.json)；[16份原审阅返回](../2026-11-06-inspect-rest-site-examples/README.md)保持旧基线。
