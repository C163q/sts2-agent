using System.Text.Json;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{

    private async Task<string> AncientRequest(Request request, JsonElement before)
    {
        bool inspect = request.Operation == "inspect_ancient";
        bool choose = request.Operation == "choose_ancient_option";
        int optionId = -1;
        if (choose && (request.Arguments is not { } args
            || args.EnumerateObject().Count() != 1 || !args.TryGetProperty("option_id", out var id)
            || id.ValueKind != JsonValueKind.Number || !id.TryGetInt32(out optionId) || optionId < 0))
            return FileMailbox.RejectedBeforeSubmission(request.Id, "invalid_request", "A nonnegative Int32 option_id is required.");
        if (!inspect && request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read the current ancient before acting.");
        var context = AncientInspection.Current;
        if (inspect)
        {
            if (AncientInspection.InspectionUnavailableReason(context) is { } rejection)
                return ResponseBuilder.Error(request.Id, "illegal_action", rejection, publicMessage: true, uiUnchanged: true);
            return InspectionSuccess(request, before, ancientInspection.Inspect());
        }
        NClickableControl? button;
        if (choose)
        {
            if (AncientInspection.ChoiceUnavailableReason(context) is { } unavailable)
                return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action", unavailable);
            var option = ancientInspection.Find(context!, optionId);
            if (option == null)
                return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action",
                    "No current ancient gift matches option_id. It may have been used or replaced; inspect_ancient shows the current IDs.");
            if (AncientInspection.OptionUnavailableReason(option) is { } optionUnavailable)
                return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action", optionUnavailable);
            button = option;
        }
        else
        {
            if (AncientInspection.DialogueUnavailableReason(context) is { } unavailable)
                return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action", unavailable);
            button = AncientInspection.Continue(context!)!;
        }
        var run = RunManager.Instance.DebugOnlyGetState();
        UiChanged();
        // Match the native mouse/controller release; EventSynchronizer owns the option task.
        button.ForceClick();
        var (after, reason) = await ActionObservation(() => ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
            && ReferenceEquals(context!.Model, AncientInspection.Current?.Model) ? NonCombatBoundary() : "interrupted");
        return TransitionSuccess(request, after, reason);
    }
}
