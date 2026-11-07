using System.Text.Json;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{

    private async Task<string> ConfirmationRequest(Request request, JsonElement before)
    {
        if (request.Arguments is not { } args || args.EnumerateObject().Count() != 1
            || !args.TryGetProperty("option", out var value) || value.ValueKind != JsonValueKind.String
            || value.GetString() is not ("confirm" or "cancel"))
            return FileMailbox.RejectedBeforeSubmission(request.Id, "invalid_request", "Expected confirm or cancel.");
        if (request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read the current confirmation before acting.");
        var popup = EventConfirmation.Current;
        if (EventConfirmation.ActionUnavailableReason(popup) is { } unavailable)
            return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action", unavailable);
        bool confirming = value.GetString() == "confirm";
        var contents = EventConfirmation.Contents(popup!);
        var button = confirming ? contents.YesButton : contents.NoButton;
        if (EventConfirmation.ButtonUnavailableReason(popup!, button) is { } unavailableButton)
            return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action", unavailableButton);
        var run = RunManager.Instance.DebugOnlyGetState();
        UiChanged();
        button.ForceClick();
        var (after, reason) = await ActionObservation(() => {
            if (!ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())) return "interrupted";
            if (EventConfirmation.AbandonPending || EventConfirmation.BackdropAnimating) return null;
            if (confirming && !EventTaskTracker.RunLost) return null;
            return NonCombatBoundary();
        });
        return TransitionSuccess(request, after, reason);
    }
}
