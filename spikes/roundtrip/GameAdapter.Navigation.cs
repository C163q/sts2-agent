using System.Globalization;
using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Screens.Map;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private object? lastMap;
    private object? lastRun;
    private int mapGeneration;

    private static bool NodeId(string? id)
    {
        var parts = id?.Split(':');
        return parts is { Length: 4 } && parts[0] == "map"
            && parts.Skip(1).All(p => int.TryParse(p, NumberStyles.None, CultureInfo.InvariantCulture, out int n)
                && n >= 0 && p == n.ToString(CultureInfo.InvariantCulture)) && parts[1] != "0";
    }

    private async Task<string> TravelRequest(Request request, JsonElement before)
    {
        if (request.Arguments is not { } args || args.ValueKind != JsonValueKind.Object || args.EnumerateObject().Count() != 1
            || !args.TryGetProperty("node_id", out var node) || node.ValueKind != JsonValueKind.String || !NodeId(node.GetString()))
            return FileMailbox.Error(request.Id, "invalid_request", "A canonical map node_id is required.");
        if (request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Observe the current map before traveling.");
        var run = RunManager.Instance.DebugOnlyGetState();
        var map = NMapScreen.Instance;
        if (run == null || map == null || !MapView.Ready(map) || LocalPlayer == null)
            return FileMailbox.Error(request.Id, "illegal_action", "Return to the available single-player map.");
        var point = MapInspection.Choices(map).SingleOrDefault(p => MapInspection.Id(run, p.Point.coord) == node.GetString());
        if (point == null) return FileMailbox.Error(request.Id, "illegal_action", "This map node is not selectable.");
        var graph = run.Map;
        int act = run.CurrentActIndex;
        bool SamePage() => ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState()) && ReferenceEquals(graph, run.Map)
            && act == run.CurrentActIndex && MapInspection.Choices(map).Contains(point);
        // Scroll through the native map input so off-screen candidates are visibly clicked.
        for (int i = 0; i < 24; i++)
        {
            if (!SamePage()) return FileMailbox.Error(request.Id, "illegal_action", "The map changed before traveling.");
            if (map.IsNodeOnScreen(point)) break;
            float distance = Math.Clamp(map.Size.Y * 0.5f - point.GlobalPosition.Y, -500f, 500f);
            using var scroll = new InputEventPanGesture { Delta = new Vector2(0, -distance / 50f) };
            map.Call("ProcessScrollEvent", scroll);
            for (int frame = 0; frame < 6; frame++) await ObservationFrame();
        }
        if (!SamePage() || !map.IsNodeOnScreen(point))
            return FileMailbox.Error(request.Id, "illegal_action", "The requested map node cannot be clicked now.");
        using var enteringCombat = CombatEntryCapture.Begin(LocalPlayer, observation.CardId);
        uiGeneration++;
        point.ForceClick();
        var destination = point.Point.coord;
        var (after, reason) = await ActionObservation(() =>
        {
            if (!ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState()) || !ReferenceEquals(graph, run.Map)
                || run.CurrentActIndex != act) return "interrupted";
            if (run.CurrentMapCoord != destination) return null;
            return enteringCombat.StopReason(CanPlayCards()) ?? NonCombatBoundary();
        });
        return Success(request.Id, after[..^1] + ",\"transition\":" + JsonSerializer.Serialize(enteringCombat.Result(reason)) + "}");
    }
}
