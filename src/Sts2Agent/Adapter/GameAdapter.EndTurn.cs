using System.Text.Json;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private static string? EndTurnUnavailableReason()
    {
        if (LocalPlayer == null || !RunManager.Instance.IsInProgress)
            return "No local run is available for ending a turn.";
        if (!RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
            return "Ending a turn requires a local single-player run.";
        if (!CombatManager.Instance.IsInProgress)
            return "Turns can be ended only during combat.";
        if (CombatManager.Instance.IsOverOrEnding)
            return "Combat is ending; inspect the current screen before continuing.";
        if (CardSelection.Current != null)
            return "Resolve the current card selection before ending the turn.";
        if (CardView.Current != null)
            return "Close the card browsing page before ending the turn.";
        if (NRun.Instance?.GlobalUi.MapScreen.IsOpen == true)
            return "Close the map before ending the turn.";
        if (RunUi.Transitioning())
            return "Wait for the screen transition before ending the turn.";
        if (CombatObservation.Status() != "visible")
            return "Return to the combat screen before ending the turn.";
        if (NCombatRoom.Instance?.Ui.Hand.InCardPlay == true || NTargetManager.Instance.IsInSelection)
            return "Finish or cancel the current card play or target selection before ending the turn.";
        if (!CanEndTurn() || !RunManager.Instance.ActionQueueSet.IsEmpty)
            return "The player turn is not ready to end; wait for the current action to finish.";
        var button = NCombatRoom.Instance?.Ui.EndTurnButton;
        if (!VisibleUi.OnScreen(button)) return "The end-turn button is not visible.";
        if (!button!.IsEnabled) return "The end-turn button is disabled.";
        if (!STS2RitsuLib.RitsuLibFramework.IsActive)
            return "RitsuLib is unavailable; no action was submitted.";
        return null;
    }

    private async Task<string> EndTurnRequest(Request request)
    {
        if (EndTurnUnavailableReason() is { } reason)
            return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action", reason);
        var player = LocalPlayer!;
        int turn = player.PlayerCombatState!.TurnNumber;
        var journal = CombatJournalScope.Current!;
        RunManager.Instance.ActionQueueSynchronizer.RequestEnqueue(new EndPlayerTurnAction(player, turn));
        execution?.ActionSubmitted();
        var (state, stop) = await ActionObservation(() => journal.StopReason(
            player.PlayerCombatState?.TurnNumber > turn && CanEndTurn()
            && RunManager.Instance.ActionQueueSet.IsEmpty, requireTurnStarted: true));
        return Success(request, ResponseBuilder.WithTransition(state, journal.Result(stop)));
    }
}
