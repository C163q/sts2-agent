using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private static bool CanPlayCards() => CardPlayUnavailableReason() == null;

    private static string? CardPlayUnavailableReason(bool allowQueued = false)
    {
        if (LocalPlayer == null || !RunManager.Instance.IsInProgress)
            return "No local run is available for playing cards.";
        if (!RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
            return "Playing cards requires a local single-player run.";
        if (!CombatManager.Instance.IsInProgress)
            return "Cards can be played only during combat.";
        if (CombatManager.Instance.IsOverOrEnding || !LocalPlayer.Creature.IsAlive)
            return "Combat is ending; inspect the current screen before continuing.";
        if (CardSelection.Current != null)
            return "Resolve the current card selection before playing cards.";
        if (CardView.Current != null)
            return "Close the card browsing page before playing cards.";
        if (NRun.Instance?.GlobalUi.MapScreen.IsOpen == true)
            return "Close the map before playing cards.";
        if (RunUi.Transitioning())
            return "Wait for the screen transition before playing cards.";
        if (CombatObservation.Status() != "visible")
            return "Return to the combat screen before playing cards.";
        if (NCombatRoom.Instance?.Ui.Hand.InCardPlay == true || NTargetManager.Instance.IsInSelection)
            return "Finish or cancel the current card play or target selection before playing another card.";
        if (!CanEndTurn() || !allowQueued && !RunManager.Instance.ActionQueueSet.IsEmpty)
            return "The player turn is not ready for card input; wait for the current action to finish.";
        return null;
    }

    private static string? CardReferenceReason(CardModel card, CardPlayInput input)
    {
        if (TargetInspection.Type(card) == null) return "This card's target type is not supported.";
        if (TargetInspection.RequiresTarget(card) && input.TargetId == null)
            return "This card requires target_id for a current target; inspect_targets can clarify its target range.";
        if (!TargetInspection.RequiresTarget(card) && input.TargetId != null)
            return "This card does not accept target_id; omit it.";
        return null;
    }

    private static string? CardSubmissionReason(CardModel card, CardPlayInput input, Creature? initialTarget)
    {
        if (card.Owner != LocalPlayer || card.Pile?.Type != PileType.Hand)
            return "This card is no longer in the local player's hand.";
        var targets = TargetInspection.Targets(card);
        if (TargetInspection.Reason(card, targets) is { } reason) return reason;
        if (CardReferenceReason(card, input) is { } reference) return reference;
        if (input.TargetId.HasValue && (initialTarget == null || !targets.Contains(initialTarget)))
            return "The specified target is not currently available for this card.";
        return card.CanPlayTargeting(initialTarget) ? null : "The card cannot be played with the specified target.";
    }
}
