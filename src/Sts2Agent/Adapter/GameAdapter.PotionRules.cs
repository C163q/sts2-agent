using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private static bool CanHandlePotions() => PotionStageUnavailableReason() == null;
    private static bool CanDiscardPotions() => DiscardPotionStageUnavailableReason() == null;

    private static string? PotionStageUnavailableReason() => PotionStageUnavailableReason(allowDiscardAtChoice: false);
    private static string? DiscardPotionStageUnavailableReason() => PotionStageUnavailableReason(allowDiscardAtChoice: true);

    private static string? PotionStageUnavailableReason(bool allowDiscardAtChoice)
    {
        if (LocalPlayer == null || !RunManager.Instance.IsInProgress)
            return "No local run is available for potion actions.";
        if (!RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
            return "Potion actions require a local single-player run.";
        if (!LocalPlayer.Creature.IsAlive || LocalPlayer.RunState.IsGameOver)
            return "The run or combat is over; potion actions are unavailable.";
        if (CardView.Current != null)
            return "Close the card browsing page before using or discarding a potion.";
        if (CombatManager.Instance.IsInProgress && NRun.Instance?.GlobalUi.MapScreen.IsOpen == true)
            return "Close the map before using or discarding a potion in combat.";
        if (RunUi.Transitioning())
            return "Wait for the screen transition before using or discarding a potion.";
        if (NTargetManager.Instance.IsInSelection)
            return "Finish or cancel target selection before using or discarding another potion.";
        if (CardSelection.Current is { } selection)
        {
            if (!allowDiscardAtChoice)
                return "Resolve the current card selection before using a potion.";
            if (!selection.Supported || selection.Kind == "view_cards" || selection.Status != "visible"
                || selection.InPreview || !CardSelection.AwaitingInput)
                return "Return to a ready card selection before discarding a potion.";
            if (CombatManager.Instance.IsInProgress && (CombatManager.Instance.IsOverOrEnding
                || LocalPlayer.PlayerCombatState?.Phase != PlayerTurnPhase.Play))
                return "The player turn is not ready for a potion discard.";
            // The native queue waits behind the choice. Do not require that queue to be empty.
            return null;
        }
        if (!RunManager.Instance.ActionQueueSet.IsEmpty)
            return "Wait for the current action to finish before using or discarding a potion.";
        bool childRewardsReady = RewardInspection.Current is { } rewards && RewardInspection.Ready(rewards);
        if (AncientInspection.Busy && !childRewardsReady)
            return "Wait for the ancient's current interaction to finish before using a potion.";
        if (!CombatManager.Instance.IsInProgress && EventTaskTracker.Pending && !childRewardsReady)
            return "Wait for the event's current interaction to finish before using a potion.";
        if (ShopTransactions.Pending && !childRewardsReady)
            return "Wait for the current purchase to finish before using a potion.";
        if (ShopInspection.Current is { } shop && ShopInspection.Exposed(shop) && !ShopInspection.Ready(shop))
            return "Wait for the shop screen to finish appearing before using a potion.";
        if (CombatManager.Instance.IsInProgress)
            return CanPlayCards() ? null : "The player turn is not ready for potion input; wait for the current action to finish.";
        return RunUi.NonCombatVisible() ? null
            : "The current screen does not allow potion actions; close the covering dialog or view first.";
    }
}
