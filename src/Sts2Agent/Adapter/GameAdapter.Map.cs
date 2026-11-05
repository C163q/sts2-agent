using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private async Task<string> InspectMap(Request request)
    {
        string Reject(string message, bool unchanged = false) => ResponseBuilder.Error(request.Id, "illegal_action",
            message, publicMessage: true, uiUnchanged: unchanged);
        if (MapUnavailableReason() is { } reason) return Reject(reason, unchanged: true);
        var run = RunManager.Instance.DebugOnlyGetState();
        var map = NRun.Instance?.GlobalUi.MapScreen;
        if (run == null || map == null) return Reject("No local run is available for map viewing.", unchanged: true);
        var graph = run.Map;
        int act = run.CurrentActIndex;
        bool cardOpen = MapView.CardPage != null;
        if (!map.IsOpen || cardOpen)
        {
            var button = NRun.Instance!.GlobalUi.TopBar.Map;
            if (MapUnavailableReason() is { } unavailable) return Reject(unavailable, unchanged: true);
            UiChanged();
            button.ForceClick();
        }
        bool closed = false;
        void Closed() => closed = true;
        bool SamePage() => !closed && ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
            && ReferenceEquals(graph, run.Map) && act == run.CurrentActIndex && MapView.Current(map);
        map.Closed += Closed;
        try
        {
            await ObservationFrame();
            await WaitUntil(() => !SamePage() || MapView.Ready(map));
            if (!SamePage() || !MapView.Ready(map))
                return Reject("The map changed while reading. Read the current screen before continuing.");
            using var snapshot = JsonDocument.Parse(Observe());
            return InspectionSuccess(request, snapshot.RootElement, snapshot.RootElement.GetProperty("map"));
        }
        finally
        {
            if (GodotObject.IsInstanceValid(map)) map.Closed -= Closed;
        }
    }

    private async Task<string> CloseMap(Request request)
    {
        string Reject(string message, bool unchanged = false) => ResponseBuilder.Error(request.Id,
            "illegal_action", message, publicMessage: true, uiUnchanged: unchanged);
        var candidate = NRun.Instance?.GlobalUi.MapScreen;
        if (MapView.CloseUnavailableReason(candidate) is { } reason) return Reject(reason, unchanged: true);
        var map = candidate!;
        var run = RunManager.Instance.DebugOnlyGetState();
        var graph = run?.Map;
        int? act = run?.CurrentActIndex;
        var underlyingOverlay = NRun.Instance!.GlobalUi.Overlays.Peek();
        bool reopened = false;
        void Opened() => reopened = true;
        UiChanged();
        bool SameMap() => ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
            && ReferenceEquals(graph, run?.Map) && act == run?.CurrentActIndex && GodotObject.IsInstanceValid(map)
            && ReferenceEquals(underlyingOverlay, NRun.Instance?.GlobalUi.Overlays.Peek())
            && ReferenceEquals(NRun.Instance?.GlobalUi.MapScreen, map);
        map.Opened += Opened;
        try
        {
            MapView.Back(map)!.ForceClick();
            await ObservationFrame();
            await WaitUntil(() => !SameMap() || reopened || map.IsOpen || !MapView.Clear() || !VisibleUi.Shown(map));
            if (!SameMap() || reopened || map.IsOpen || !MapView.Clear())
                return Reject("The map changed while closing. Read the current screen before continuing.");
            string after = await SettledObservation();
            if (!SameMap() || reopened || map.IsOpen || !MapView.Clear())
                return Reject("The map changed while closing. Read the current screen before continuing.");
            return Success(request, after);
        }
        finally
        {
            if (GodotObject.IsInstanceValid(map)) map.Opened -= Opened;
        }
    }
}
