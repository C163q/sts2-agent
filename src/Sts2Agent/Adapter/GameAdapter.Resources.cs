using Godot;
using System.Text.Json.Nodes;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private static readonly HashSet<string> RecordedActions = [
        "play_card", "play_cards", "end_turn", "use_potion", "discard_potion", "select_card", "selection_option",
        "claim_reward", "proceed", "choose_rest_option", "loot_treasure", "open_shop", "close_shop", "buy_item",
        "choose_ancient_option", "advance_dialogue", "choose_event_option", "divine",
        "respond_to_confirmation", "travel_to_node", "run_result_option"
    ];

    private RequestExecution? execution;

    public async Task<string> Execute(Request request)
    {
        if (cardPlayBatch != null && !cardPlayBatch.SameContext)
        { cardPlayBatch.Dispose(); cardPlayBatch = null; }
        var previous = execution;
        var current = new RequestExecution();
        execution = current;
        try { return ResponseBuilder.WithExecution(await ExecuteRecorded(request), current); }
        catch (Exception error)
        {
            cardPlayBatch?.Dispose(); cardPlayBatch = null;
            GD.PushError("[Sts2Agent] Operation failed: " + error);
            return ResponseBuilder.WithExecution(ResponseBuilder.Failure(request.Id, error), current);
        }
        finally { execution = previous; }
    }

    private async Task<string> ExecuteRecorded(Request request)
    {
        if (!RecordedActions.Contains(request.Operation)) return await ExecuteCore(request);
        using var events = new ActionEventScope();
        using var resources = LocalPlayer is { } player ? new RunResourceJournal(player, events.Buffer) : null;
        using var inventory = LocalPlayer is { } owner ? new RunInventoryJournal(owner, events.Buffer, observation.CardId) : null;
        using var relicCounters = LocalPlayer is { } relicOwner ? new RelicCounterJournal(relicOwner, events.Buffer) : null;
        using var potions = LocalPlayer is { } potionOwner ? new PotionJournal(potionOwner) : null;
        using var enteringCombat = LocalPlayer is { } combatPlayer
            ? CombatJournalScope.Begin(combatPlayer, observation) : null;
        string response = await ExecuteCore(request);
        enteringCombat?.Flush();
        response = events.Apply(response);
        if (cardPlayBatch is { } batch)
        {
            var result = JsonNode.Parse(response)!.AsObject();
            if (result["ok"]?.GetValue<bool>() == true && result["state"]?["transition"] != null)
            {
                result["state"]!["card_plays"] = System.Text.Json.JsonSerializer.SerializeToNode(batch.Read());
                response = result.ToJsonString();
                if (!batch.Pending) { batch.Dispose(); cardPlayBatch = null; }
            }
        }
        return response;
    }
}
