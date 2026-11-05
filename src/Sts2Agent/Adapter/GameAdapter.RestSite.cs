using System.Text.Json;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private async Task<string> RestSiteRequest(Request request, JsonElement before)
    {
        string? optionId = null;
        if (request.Operation == "choose_rest_option" && (request.Arguments is not { } args
            || args.EnumerateObject().Count() != 1 || !args.TryGetProperty("option_id", out var id)
            || id.ValueKind != JsonValueKind.String || string.IsNullOrWhiteSpace(optionId = id.GetString()) || optionId.Length > 128))
            return FileMailbox.Error(request.Id, "invalid_request", "One observed option_id is required.");
        bool inspect = request.Operation == "inspect_rest_site";
        if (!inspect && request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read the current rest site before acting.");
        var room = RestSiteInspection.Current;
        if (inspect)
        {
            if (RestSiteInspection.InspectionUnavailableReason(room) is { } unavailable)
                return FileMailbox.Error(request.Id, "illegal_action", unavailable, publicMessage: true);
            return InspectionSuccess(request, before, RestSiteInspection.Inspect());
        }
        if (room == null || !RestSiteInspection.Ready(room) || !RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
            return FileMailbox.Error(request.Id, "illegal_action", "Return to an available local rest site.");
        var option = RestSiteInspection.Buttons(room).FirstOrDefault(b => b.Option.OptionId == optionId);
        NButton? button = option;
        if (button?.IsEnabled != true || request.Operation == "choose_rest_option"
            && (option == null || !RestSiteInspection.Clickable(option)))
            return FileMailbox.Error(request.Id, "illegal_action", "This rest site option is unavailable.");
        var run = RunManager.Instance.DebugOnlyGetState();
        UiChanged();
        button.ForceClick();
        var (after, reason) = await ActionObservation(() => ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
            ? NonCombatBoundary() : "interrupted");
        return TransitionSuccess(request, after, reason);
    }
}
