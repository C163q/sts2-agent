using System.Text.Json;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private readonly AncientInspection ancientInspection = new();

    private async Task<string> AncientRequest(Request request, JsonElement before)
    {
        bool inspect = request.Operation == "inspect_ancient";
        int optionId = -1;
        if (request.Operation == "choose_ancient_option" && (request.Arguments is not { } args
            || args.EnumerateObject().Count() != 1 || !args.TryGetProperty("option_id", out var id)
            || id.ValueKind != JsonValueKind.Number || !id.TryGetInt32(out optionId) || optionId < 0))
            return FileMailbox.Error(request.Id, "invalid_request", "A nonnegative option_id is required.");
        if (!inspect && request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read the current ancient before acting.");
        var context = AncientInspection.Current;
        if (context == null || !AncientInspection.Exposed(context) || !TreasureInspection.Singleplayer
            || !inspect && !AncientInspection.Ready(context))
            return FileMailbox.Error(request.Id, "illegal_action", "Return to an available single-player ancient.");
        if (inspect) return Success(request.Id, JsonSerializer.Serialize(new {
            snapshot_id = before.GetProperty("snapshot_id").GetString(), scene = "ancient", ancient = ancientInspection.Read(full: true) }));
        NClickableControl? button = request.Operation == "advance_dialogue" ? AncientInspection.Continue(context)
            : request.Operation == "proceed" ? AncientInspection.Proceed(context) : ancientInspection.Find(context, optionId);
        if (button?.IsEnabled != true || button is MegaCrit.Sts2.Core.Nodes.Events.NEventOptionButton option
            && (!AncientInspection.Clickable(option) || AncientInspection.Continue(context) != null))
            return FileMailbox.Error(request.Id, "illegal_action", "The requested dialogue or option is unavailable.");
        var run = RunManager.Instance.DebugOnlyGetState();
        uiGeneration++;
        // Match the native mouse/controller release; EventSynchronizer owns the option task.
        button.ForceClick();
        var (after, reason) = await ActionObservation(() => ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
            && ReferenceEquals(context.Model, AncientInspection.Current?.Model) ? NonCombatBoundary() : "interrupted");
        return Success(request.Id, after[..^1] + ",\"transition\":" + JsonSerializer.Serialize(new {
            stop_reason = reason, complete = reason is not ("timeout" or "interrupted"), events = Array.Empty<object>() }) + "}");
    }
}
