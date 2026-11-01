using System.Text.Json;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private async Task<string> DivinationRequest(Request request, JsonElement before)
    {
        bool inspect = request.Operation == "inspect_event";
        string? tool = null;
        int x = -1, y = -1;
        if (request.Operation == "set_divination_tool" && (request.Arguments is not { } toolArgs
            || toolArgs.EnumerateObject().Count() != 1 || !toolArgs.TryGetProperty("tool", out var value)
            || value.ValueKind != JsonValueKind.String || (tool = value.GetString()) is not ("big" or "small")))
            return FileMailbox.Error(request.Id, "invalid_request", "Expected big or small tool.");
        if (request.Operation == "divine" && (request.Arguments is not { } args || args.EnumerateObject().Count() != 2
            || !args.TryGetProperty("x", out var xv) || !args.TryGetProperty("y", out var yv)
            || xv.ValueKind != JsonValueKind.Number || yv.ValueKind != JsonValueKind.Number
            || !xv.TryGetInt32(out x) || !yv.TryGetInt32(out y) || x is < 0 or > 10 || y is < 0 or > 10))
            return FileMailbox.Error(request.Id, "invalid_request", "Expected integer coordinates from 0 to 10.");
        if (!inspect && request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read the current board before acting.");
        var screen = DivinationInspection.Current;
        if (screen == null || !DivinationInspection.Ready(screen))
            return FileMailbox.Error(request.Id, "illegal_action", "Return to an available divination board.");
        if (inspect) return Success(request.Id, JsonSerializer.Serialize(new {
            snapshot_id = before.GetProperty("snapshot_id").GetString(), scene = "event", divination = DivinationInspection.Read() }));
        NClickableControl? button = request.Operation == "proceed" ? DivinationInspection.Proceed(screen)
            : !DivinationInspection.Playing(screen) ? null
            : tool != null ? DivinationInspection.Tool(screen, tool)
            : DivinationInspection.Cells(screen).SingleOrDefault(c => c.Entity.X == x && c.Entity.Y == y && DivinationInspection.Clickable(c));
        if (button?.IsEnabled != true)
            return FileMailbox.Error(request.Id, "illegal_action", "The requested divination action is unavailable.");
        var run = RunManager.Instance.DebugOnlyGetState();
        uiGeneration++;
        button.ForceClick();
        var (after, reason) = await ActionObservation(() => !ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
            ? "interrupted" : NonCombatBoundary());
        return Success(request.Id, after[..^1] + ",\"transition\":" + JsonSerializer.Serialize(new {
            stop_reason = reason, complete = reason is not ("timeout" or "interrupted"), events = Array.Empty<object>() }) + "}");
    }
}
