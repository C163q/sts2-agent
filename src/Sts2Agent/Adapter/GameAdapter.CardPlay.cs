using System.Text.Json;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Creatures;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private ManualPlayBatch? cardPlayBatch;

    private async Task<string> CardPlayRequest(Request request, JsonElement before)
    {
        bool playing = request.Operation != "inspect_targets", multiple = request.Operation == "play_cards";
        string Reject(string code, string message) => playing
            ? FileMailbox.RejectedBeforeSubmission(request.Id, code, message)
            : FileMailbox.Error(request.Id, code, message, publicMessage: true);
        CardPlayInput[] inputs;
        try
        {
            inputs = CardPlayOptions.Parse(request.Arguments, multiple);
            if (!playing && inputs[0].TargetId.HasValue)
                throw new JsonException("inspect_targets accepts only card_id; target_id is used when playing a card.");
        }
        catch (JsonException error) { return Reject("invalid_request", error.Message); }
        if (playing && request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read current state before playing cards.");
        if (CardPlayUnavailableReason() is { } unavailable) return Reject("illegal_action", unavailable);
        if (playing && !STS2RitsuLib.RitsuLibFramework.IsActive)
            return Reject("illegal_action", "RitsuLib is unavailable; no card was submitted.");

        var reader = new TargetInspection(observation);
        var items = new List<ManualPlayBatch.Item>();
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        for (int index = 0; index < inputs.Length; index++)
        {
            var input = inputs[index];
            string prefix = multiple ? $"cards[{index}]: " : "";
            var card = reader.FindCard(input.CardId);
            if (card == null || card.Owner != LocalPlayer)
                return Reject("illegal_action", prefix + "No supported visible hand card has that ID.");
            if (!playing)
                return TargetInspection.Type(card) == null
                    ? Reject("illegal_action", "This card's target type is not supported.")
                    : InspectionSuccess(request, before, reader.Read(card, before.GetProperty("snapshot_id").GetString()!));
            if (CardReferenceReason(card, input) is { } reference)
                return Reject("illegal_action", prefix + reference);
            Creature? target = input.TargetId.HasValue ? combat.Creatures.FirstOrDefault(c =>
                c.CombatId == input.TargetId && TargetInspection.Visible(c)) : null;
            if (input.TargetId.HasValue && target == null)
                return Reject("illegal_action", prefix + "target_id does not identify a current visible combat object.");
            items.Add(new(input, card, target));
        }
        var actionExecution = execution;
        var tracker = new ManualPlayBatch(LocalPlayer!, items.ToArray(), () => {
            UiChanged();
            actionExecution?.ActionSubmitted();
        });
        if (multiple)
        {
            cardPlayBatch?.Dispose();
            cardPlayBatch = tracker;
        }
        try
        {
            foreach (var item in tracker.Items)
            {
                string? boundary = !tracker.SameContext ? "The run, combat or turn changed before this card was submitted."
                    : CardPlayUnavailableReason(allowQueued: multiple);
                if (boundary != null) { tracker.StopRemaining(boundary); break; }
                string? failure = !ReferenceEquals(reader.FindCard(item.Input.CardId), item.Card)
                    ? "This card is no longer an available hand card."
                    : CardSubmissionReason(item.Card, item.Input, item.Target);
                if (failure != null)
                {
                    if (!multiple) return Reject("illegal_action", failure);
                    item.Rejection = failure;
                    continue;
                }
                if (!tracker.Submit(item))
                {
                    if (!multiple) return Reject("illegal_action", item.Rejection!);
                    continue;
                }
                if (tracker.SubmissionUncertain)
                {
                    UiChanged();
                    tracker.StopRemaining("Submission stopped because the native enqueue could not be confirmed.");
                    break;
                }
            }
            var journal = CombatJournalScope.Current!;
            var (after, reason) = await ActionObservation(() =>
            {
                if (tracker.SubmissionUncertain || tracker.Faulted || tracker.Uncertain) return "interrupted";
                string? boundary = journal.StopReason(!tracker.Pending && CanPlayCards());
                return !multiple && boundary == "player_ready" && tracker.Items[0].Progress.Canceled
                    ? "action_canceled" : boundary;
            });
            return Success(request, ResponseBuilder.WithTransition(after, journal.Result(reason)));
        }
        finally { if (!multiple) tracker.Dispose(); }
    }
}
