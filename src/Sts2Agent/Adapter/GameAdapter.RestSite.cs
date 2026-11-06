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
            return FileMailbox.RejectedBeforeSubmission(request.Id, "invalid_request", "One observed option_id is required.");
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
        if (RestSiteInspection.ActionUnavailableReason(room) is { } unavailableAction)
            return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action", unavailableAction);
        var button = RestSiteInspection.Buttons(room!).FirstOrDefault(b => b.Option.OptionId == optionId);
        if (button == null)
            return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action",
                "No current rest option matches option_id. It may have been used or replaced; inspect_rest_site shows the remaining IDs.");
        if (RestSiteInspection.OptionUnavailableReason(button) is { } unavailableOption)
            return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action", unavailableOption);
        var run = RunManager.Instance.DebugOnlyGetState();
        UiChanged();
        button.ForceClick();
        var (after, reason) = await ActionObservation(() => ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
            ? NonCombatBoundary() : "interrupted");
        return TransitionSuccess(request, after, reason);
    }
}
