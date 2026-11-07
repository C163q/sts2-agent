using System.Text.Json;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private async Task<string> SetDivinationTool(Request request)
    {
        string? tool;
        if (request.Arguments is not { } arguments || arguments.EnumerateObject().Count() != 1
            || !arguments.TryGetProperty("tool", out var value) || value.ValueKind != JsonValueKind.String
            || (tool = value.GetString()) is not ("big" or "small"))
            return ResponseBuilder.Error(request.Id, "invalid_request", "Expected tool to be big or small.",
                publicMessage: true, uiUnchanged: true);
        var screen = DivinationInspection.Current;
        if (DivinationInspection.ToolSwitchUnavailableReason(screen) is { } reason)
            return ResponseBuilder.Error(request.Id, "illegal_action", reason, publicMessage: true, uiUnchanged: true);
        if (DivinationInspection.ToolUnavailableReason(screen!, tool) is { } unavailable)
            return ResponseBuilder.Error(request.Id, "illegal_action", unavailable, publicMessage: true, uiUnchanged: true);
        var run = RunManager.Instance.DebugOnlyGetState();
        if (DivinationInspection.SelectedTool(screen!) != tool)
        {
            UiChanged();
            DivinationInspection.Tool(screen!, tool).ForceClick();
        }
        string state = await SettledObservation();
        if (!ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
            || !ReferenceEquals(screen, DivinationInspection.Current)
            || DivinationInspection.ToolUnavailableReason(screen!, tool) != null
            || DivinationInspection.SelectedTool(screen!) != tool)
            return FileMailbox.Error(request.Id, "illegal_action",
                "The divination board changed while switching tools. Read the current screen before continuing.", publicMessage: true);
        return Success(request, state);
    }

    private async Task<string> DivinationRequest(Request request, JsonElement before)
    {
        if (request.Operation == "set_divination_tool") return await SetDivinationTool(request);
        bool inspect = request.Operation == "inspect_event";
        int x = -1, y = -1;
        if (request.Operation == "divine" && (request.Arguments is not { } args || args.EnumerateObject().Count() != 2
            || !args.TryGetProperty("x", out var xv) || !args.TryGetProperty("y", out var yv)
            || xv.ValueKind != JsonValueKind.Number || yv.ValueKind != JsonValueKind.Number
            || !xv.TryGetInt32(out x) || !yv.TryGetInt32(out y) || x is < 0 or > 10 || y is < 0 or > 10))
            return FileMailbox.Error(request.Id, "invalid_request", "Expected integer coordinates from 0 to 10.");
        if (!inspect && request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read the current board before acting.");
        var screen = DivinationInspection.Current;
        if (inspect)
        {
            if (DivinationInspection.InspectionUnavailableReason(screen) is { } rejection)
                return ResponseBuilder.Error(request.Id, "illegal_action", rejection, publicMessage: true, uiUnchanged: true);
            return InspectionSuccess(request, before, new { divination = DivinationInspection.Read() });
        }
        if (screen == null || !DivinationInspection.Ready(screen))
            return FileMailbox.Error(request.Id, "illegal_action", "Return to an available divination board.");
        NClickableControl? button = !DivinationInspection.Playing(screen) ? null
            : DivinationInspection.Cells(screen).SingleOrDefault(c => c.Entity.X == x && c.Entity.Y == y && DivinationInspection.Clickable(c));
        if (button?.IsEnabled != true)
            return FileMailbox.Error(request.Id, "illegal_action", "The requested divination action is unavailable.");
        var run = RunManager.Instance.DebugOnlyGetState();
        UiChanged();
        button.ForceClick();
        var (after, reason) = await ActionObservation(() => !ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
            ? "interrupted" : NonCombatBoundary());
        return TransitionSuccess(request, after, reason);
    }
}
