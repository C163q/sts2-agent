using System.Text.Json;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Actions;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private static bool CanPlayCards() => CanEndTurn() && CombatObservation.Status() == "visible"
        && RunManager.Instance.ActionQueueSet.IsEmpty && !NTargetManager.Instance.IsInSelection;

    private async Task<string> CardPlayRequest(Request request, JsonElement before)
    {
        var arguments = request.Arguments;
        bool playing = request.Operation == "play_card";
        string Reject(string code, string message) => playing
            ? FileMailbox.RejectedBeforeSubmission(request.Id, code, message)
            : FileMailbox.Error(request.Id, code, message, publicMessage: true);
        uint targetId = 0;
        if (arguments == null || !arguments.Value.TryGetProperty("card_id", out var id)
            || id.ValueKind != JsonValueKind.Number || !id.TryGetInt32(out int cardId) || cardId < 0
            || arguments.Value.EnumerateObject().Any(property => property.Name != "card_id" && (!playing || property.Name != "target_id"))
            || arguments.Value.EnumerateObject().Select(property => property.Name).Distinct().Count() != arguments.Value.EnumerateObject().Count())
            return Reject("invalid_request", "Invalid card play arguments.");
        bool suppliedTarget = arguments.Value.TryGetProperty("target_id", out var supplied);
        if (suppliedTarget && (supplied.ValueKind != JsonValueKind.Number || !supplied.TryGetUInt32(out targetId)))
            return Reject("invalid_request", "Invalid target ID.");
        if (playing && request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read current state before playing a card.");
        if (!CanPlayCards())
            return Reject("illegal_action", "Normal card play is unavailable.");
        if (playing && !STS2RitsuLib.RitsuLibFramework.IsActive)
            return Reject("illegal_action", "RitsuLib is unavailable; no card was submitted.");
        var reader = new TargetInspection(observation);
        var card = reader.FindCard(cardId);
        var player = LocalPlayer!;
        if (card == null || card.Owner != player || card.Pile?.Type != PileType.Hand || TargetInspection.Type(card) == null)
            return Reject("illegal_action", "No supported visible hand card has that ID.");
        if (!playing) return Success(request.Id, JsonSerializer.Serialize(reader.Read(card, before.GetProperty("snapshot_id").GetString()!)));

        var targets = TargetInspection.Targets(card);
        var target = suppliedTarget ? targets.FirstOrDefault(creature => creature.CombatId == targetId) : null;
        if (TargetInspection.Reason(card, targets) is { } unavailable)
            return Reject("illegal_action", unavailable);
        if (TargetInspection.RequiresTarget(card) && !suppliedTarget)
            return Reject("illegal_action", "This card requires target_id from inspect_targets.targets.");
        if (!TargetInspection.RequiresTarget(card) && suppliedTarget)
            return Reject("illegal_action", "This card does not accept target_id; omit it.");
        if (suppliedTarget && target == null)
            return Reject("illegal_action", "The specified target is not currently available for this card.");
        if (!card.CanPlayTargeting(target))
            return Reject("illegal_action", "The card cannot be played with the specified target.");

        var journal = CombatJournalScope.Current!;
        PlayCardAction? submitted = null;
        bool canceled = false;
        void Canceled(GameAction action) => canceled = true;
        void Enqueued(GameAction action)
        {
            if (submitted == null && action is PlayCardAction play && play.Player == player
                && ReferenceEquals(play.NetCombatCard.ToCardModelOrNull(), card))
            {
                submitted = play;
                play.BeforeCancelled += Canceled;
            }
        }
        RunManager.Instance.ActionQueueSet.ActionEnqueued += Enqueued;
        try
        {
            uiGeneration++;
            if (!card.TryManualPlay(target))
                return FileMailbox.Error(request.Id, "illegal_action", "The native card play was rejected before submission.");
            if (target != null) NCombatRoom.Instance!.LastTargetedCreature = target;
            else if (card.TargetType is TargetType.AllEnemies or TargetType.AllAllies) NCombatRoom.Instance!.LastTargetedCreature = null;
            var (after, reason) = await ActionObservation(() =>
            {
                bool ready = submitted?.State is GameActionState.Finished or GameActionState.Canceled && CanPlayCards();
                string? boundary = journal.StopReason(ready);
                return boundary == "player_ready" && canceled ? "action_canceled" : boundary;
            });
            return Success(request.Id, after[..^1] + ",\"transition\":" + JsonSerializer.Serialize(journal.Result(reason)) + "}");
        }
        finally
        {
            RunManager.Instance.ActionQueueSet.ActionEnqueued -= Enqueued;
            if (submitted != null) submitted.BeforeCancelled -= Canceled;
        }
    }
}
