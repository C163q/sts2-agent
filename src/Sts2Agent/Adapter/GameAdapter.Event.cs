using System.Text.Json;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{

    private async Task<string> EventRequest(Request request, JsonElement before)
    {
        bool inspect = request.Operation == "inspect_event";
        int optionId = -1;
        if (request.Operation == "choose_event_option" && (request.Arguments is not { } args
            || args.EnumerateObject().Count() != 1 || !args.TryGetProperty("option_id", out var id)
            || id.ValueKind != JsonValueKind.Number || !id.TryGetInt32(out optionId) || optionId < 0))
            return FileMailbox.Error(request.Id, "invalid_request", "A nonnegative option_id is required.");
        if (!inspect && request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read the current event before acting.");
        var context = EventInspection.Current;
        if (context == null || !EventInspection.Exposed(context) || !RunContext.Singleplayer
            || !inspect && !EventInspection.Ready(context))
            return FileMailbox.Error(request.Id, "illegal_action", "Return to an available single-player event.");
        if (inspect) return InspectionSuccess(request, before, new { @event = eventInspection.Read(full: true) });
        var button = eventInspection.Find(context, optionId);
        if (button == null || !EventInspection.Clickable(button))
            return FileMailbox.Error(request.Id, "illegal_action", "The requested event option is unavailable.");
        var run = RunManager.Instance.DebugOnlyGetState();
        var enteringCombat = CombatJournalScope.Current!;
        UiChanged();
        button.ForceClick();
        var (after, reason) = await ActionObservation(() => !ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
            ? "interrupted" : enteringCombat.StopReason(CanPlayCards()) ?? NonCombatBoundary());
        return Success(request, ResponseBuilder.WithTransition(after, enteringCombat.Result(reason)));
    }
}
