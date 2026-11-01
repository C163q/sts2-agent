using MegaCrit.Sts2.Core.Combat;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private static readonly HashSet<string> RecordedActions = [
        "play_card", "end_turn", "use_potion", "discard_potion", "select_card", "selection_option",
        "claim_reward", "proceed", "choose_rest_option", "loot_treasure", "open_shop", "close_shop", "buy_item",
        "choose_ancient_option", "advance_dialogue", "choose_event_option", "set_divination_tool", "divine",
        "respond_to_confirmation", "travel_to_node", "run_result_option"
    ];

    public async Task<string> Execute(Request request)
    {
        if (!RecordedActions.Contains(request.Operation)) return await ExecuteCore(request);
        using var events = new ActionEventScope();
        using var resources = LocalPlayer is { } player ? new RunResourceJournal(player, events.Buffer) : null;
        using var inventory = LocalPlayer is { } owner ? new RunInventoryJournal(owner, events.Buffer, observation.CardId) : null;
        using var potions = LocalPlayer is { } potionOwner ? new PotionJournal(potionOwner) : null;
        using var enteringCombat = LocalPlayer is { } combatPlayer && !CombatManager.Instance.IsInProgress
            ? CombatEntryCapture.Begin(combatPlayer, observation.CardId) : null;
        string response = await ExecuteCore(request);
        enteringCombat?.Flush();
        return events.Apply(response);
    }
}
