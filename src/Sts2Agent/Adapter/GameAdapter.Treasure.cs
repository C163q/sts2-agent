using System.Diagnostics;
using System.Text.Json;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private async Task<string> TreasureRequest(Request request, JsonElement before)
    {
        bool openOnly = false;
        bool loot = request.Operation == "loot_treasure";
        if (loot && request.Arguments is { } args)
        {
            if (args.EnumerateObject().Any(p => p.Name != "open_only") || args.EnumerateObject().Count() > 1
                || args.TryGetProperty("open_only", out var value) && value.ValueKind is not (JsonValueKind.True or JsonValueKind.False))
                return FileMailbox.RejectedBeforeSubmission(request.Id, "invalid_request", "Only boolean open_only is accepted.");
            openOnly = args.TryGetProperty("open_only", out value) && value.GetBoolean();
        }
        bool inspect = request.Operation == "inspect_treasure";
        if (!inspect && request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read the current treasure room before acting.");
        var room = TreasureInspection.Current;
        if (inspect)
        {
            if (TreasureInspection.InspectionUnavailableReason(room) is { } unavailable)
                return ResponseBuilder.Error(request.Id, "illegal_action", unavailable, publicMessage: true);
            return InspectionSuccess(request, before, TreasureInspection.Inspect());
        }
        if (TreasureInspection.LootUnavailableReason(room, openOnly, out var button) is { } rejection)
            return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action", rejection);
        bool closed = !TreasureInspection.Opened(room!);
        var run = RunManager.Instance.DebugOnlyGetState();
        string? Boundary() => ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
            && ReferenceEquals(room, TreasureInspection.Current) ? NonCombatBoundary() : "interrupted";
        var timer = Stopwatch.StartNew();
        UiChanged();
        button!.ForceClick();
        var (after, reason) = await ActionObservation(Boundary, TimeSpan.FromSeconds(25) - timer.Elapsed);
        if (loot && closed && !openOnly && reason == "action_completed"
            && ReferenceEquals(room, TreasureInspection.Current) && TreasureInspection.Opened(room!)
            && TreasureInspection.LootUnavailableReason(room, false, out var relic) == null)
        {
            var remaining = TimeSpan.FromSeconds(25) - timer.Elapsed;
            if (remaining <= TimeSpan.Zero) reason = "timeout";
            else
            {
                UiChanged();
                relic!.ForceClick();
                (after, reason) = await ActionObservation(Boundary, TimeSpan.FromSeconds(25) - timer.Elapsed);
            }
        }
        return TransitionSuccess(request, after, reason);
    }
}
