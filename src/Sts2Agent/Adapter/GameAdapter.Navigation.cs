using System.Globalization;
using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Screens.Map;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{

    private static bool NodeId(string? id)
    {
        var parts = id?.Split(':');
        return parts is { Length: 4 } && parts[0] == "map"
            && parts.Skip(1).All(p => int.TryParse(p, NumberStyles.None, CultureInfo.InvariantCulture, out int n)
                && n >= 0 && p == n.ToString(CultureInfo.InvariantCulture)) && parts[1] != "0";
    }

    private async Task<string> TravelRequest(Request request, JsonElement before)
    {
        string Reject(string message) => ResponseBuilder.Error(request.Id, "illegal_action", message, publicMessage: true);
        if (request.Arguments is not { } args || args.ValueKind != JsonValueKind.Object || args.EnumerateObject().Count() != 1
            || !args.TryGetProperty("node_id", out var node) || node.ValueKind != JsonValueKind.String || !NodeId(node.GetString()))
            return FileMailbox.RejectedBeforeSubmission(request.Id, "invalid_request",
                "Specify one canonical node_id from the current map's selectable_nodes, such as map:1:2:3.");
        if (request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Observe the current map before traveling.");
        var run = RunManager.Instance.DebugOnlyGetState();
        var map = NMapScreen.Instance;
        if (MapView.TravelUnavailableReason(map) is { } unavailable)
            return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action", unavailable);
        if (run == null || map == null || LocalPlayer == null)
            return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action", "No local player is available for map travel.");
        var point = MapInspection.Choices(map).SingleOrDefault(p => MapInspection.Id(run, p.Point.coord) == node.GetString());
        if (point == null) return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action",
            "The requested node is not selectable on the current map. Choose an ID from selectable_nodes.");
        var graph = run.Map;
        int act = run.CurrentActIndex;
        bool interacted = false;
        void BeginInteraction()
        {
            if (!interacted) UiChanged();
            interacted = true;
        }
        bool SamePage() => ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState()) && ReferenceEquals(graph, run.Map)
            && act == run.CurrentActIndex && MapInspection.Choices(map).Contains(point);
        // Scroll through the native map input so off-screen candidates are visibly clicked.
        for (int i = 0; i < 24; i++)
        {
            if (!SamePage()) return Reject("The map changed while preparing travel. Read the current map before continuing.");
            if (map.IsNodeOnScreen(point)) break;
            float distance = Math.Clamp(map.Size.Y * 0.5f - point.GlobalPosition.Y, -500f, 500f);
            using var scroll = new InputEventPanGesture { Delta = new Vector2(0, -distance / 50f) };
            BeginInteraction();
            map.Call("ProcessScrollEvent", scroll);
            for (int frame = 0; frame < 6; frame++) await ObservationFrame();
        }
        if (!SamePage() || !map.IsNodeOnScreen(point))
            return Reject("The requested map node cannot be clicked after preparing travel. Read the current map before continuing.");
        var enteringCombat = CombatJournalScope.Current!;
        BeginInteraction();
        point.ForceClick();
        var destination = point.Point.coord;
        var (after, reason) = await ActionObservation(() =>
        {
            if (!ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState()) || !ReferenceEquals(graph, run.Map)
                || run.CurrentActIndex != act) return "interrupted";
            if (run.CurrentMapCoord != destination) return null;
            return enteringCombat.StopReason(CanPlayCards()) ?? NonCombatBoundary();
        });
        return Success(request, ResponseBuilder.WithTransition(after, enteringCombat.Result(reason)));
    }
}
