using System.Text.Json;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class TestDispatchChecks
{
    private static readonly string[] Operations = [
        "configure_test_run", "reset_test_run", "get_test_session", "set_test_combatant_hover",
        "set_test_relic_hover", "check_test_display_readers", "set_test_capture_failure", "check_test_dispatch", "check_test_run_result_text", "check_test_card_additions", "check_test_permanent_cards",
        "check_test_combat_handoff", "check_test_death_notifications", "check_test_orb_events", "check_test_companions",
        "check_test_blades", "check_test_orb_visibility", "check_test_capacity", "check_test_combat_resources",
        "check_test_star_reveal", "check_test_inventory", "check_test_resources", "check_test_resource_masks",
        "external_back_test_result", "reopen_test_timeline", "close_test_timeline", "inspect_test_browsing_containers",
        "prepare_test_browsable_result", "prepare_test_browsable_history", "check_test_browsable_content", "check_test_top_bar",
        "check_test_selection_observation", "check_test_afflictions", "check_test_hand_resources", "check_test_enchantments",
        "capture_test_power_tips", "capture_test_gas_bomb_intent", "check_test_confirmation", "open_test_unowned_confirmation",
        "cancel_test_confirmation", "reopen_test_confirmation", "check_test_divination", "check_test_event",
        "check_test_event_english", "prepare_test_event_victory", "check_test_ancient", "start_test_ancient_combat",
        "check_test_navigation", "finish_test_navigation_boss", "set_test_navigation_drawing", "clear_test_navigation_drawing",
        "scroll_test_navigation", "cancel_test_shop_targeting", "check_test_shop", "check_test_treasure",
        "check_test_rest_site", "check_test_rewards", "check_test_potion_state", "replace_test_potion", "check_test_play_state",
        "check_test_selection_race", "check_test_deck_lifecycle", "check_test_card_views", "check_test_piles", "check_test_map",
        "start_test_combat"
    ];

    public static async Task<object> Run()
    {
        var run = RunManager.Instance.DebugOnlyGetState();
        async Task<int> Rejected(GameAdapter adapter)
        {
            foreach (string operation in Operations)
            {
                using var before = JsonDocument.Parse(adapter.Observe());
                string token = before.RootElement.GetProperty("snapshot_id").GetString()!;
                using var response = JsonDocument.Parse(await adapter.Execute(new Request("test-dispatch", operation, token)));
                if (response.RootElement.GetProperty("ok").GetBoolean()
                    || response.RootElement.GetProperty("error").GetProperty("code").GetString() != "illegal_action"
                    || !ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState()))
                    throw new InvalidOperationException("A disabled test operation was dispatched: " + operation);
            }
            return Operations.Length;
        }
        int disabled = await Rejected(new GameAdapter(false));
        string? suite = Environment.GetEnvironmentVariable("STS2_AGENT_TEST_SUITE");
        int withoutSuite;
        try
        {
            Environment.SetEnvironmentVariable("STS2_AGENT_TEST_SUITE", null);
            withoutSuite = await Rejected(new GameAdapter(true));
        }
        finally { Environment.SetEnvironmentVariable("STS2_AGENT_TEST_SUITE", suite); }
        return new { test_mode_off = disabled, suite_and_scenarios_off = withoutSuite };
    }
}
