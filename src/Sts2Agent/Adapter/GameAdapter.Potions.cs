using System.Text.Json;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Actions;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Potions;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private async Task<string> PotionRequest(Request request, JsonElement before)
    {
        bool query = request.Operation == "inspect_targets", use = request.Operation == "use_potion";
        string Reject(string code, string message) => query
            ? FileMailbox.Error(request.Id, code, message, publicMessage: true)
            : FileMailbox.RejectedBeforeSubmission(request.Id, code, message);
        var arguments = request.Arguments;
        if (arguments == null || arguments.Value.ValueKind != JsonValueKind.Object || !arguments.Value.TryGetProperty("potion_slot", out var suppliedSlot)
            || suppliedSlot.ValueKind != JsonValueKind.Number || !suppliedSlot.TryGetInt32(out int slot) || slot < 0
            || arguments.Value.EnumerateObject().Any(p => p.Name != "potion_slot" && (!use || p.Name != "target_id"))
            || arguments.Value.EnumerateObject().Select(p => p.Name).Distinct().Count() != arguments.Value.EnumerateObject().Count())
            return Reject("invalid_request", "Pass potion_slot as a nonnegative integer; only use_potion accepts optional target_id.");
        bool suppliedTarget = arguments.Value.TryGetProperty("target_id", out var targetId);
        uint creatureId = 0;
        bool merchant = suppliedTarget && targetId.ValueKind == JsonValueKind.String && targetId.GetString() == "merchant";
        if (suppliedTarget && !merchant && (targetId.ValueKind != JsonValueKind.Number || !targetId.TryGetUInt32(out creatureId)))
            return Reject("invalid_request", "target_id must be an integer from 0 to 4294967295 or merchant; omit it when no target is required.");
        if (!query && request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read current state before using or discarding a potion.");
        string? useStage = PotionStageUnavailableReason(), discardStage = DiscardPotionStageUnavailableReason();
        string? stage = query ? useStage == null || discardStage == null ? null : useStage
            : use ? useStage : discardStage;
        if (stage != null) return Reject("illegal_action", stage);
        var holders = PotionInspection.ExposedHolders();
        if (holders == null) return Reject("illegal_action", "The potion bar is hidden or not ready in the current screen.");
        if (slot >= holders.Length) return Reject("illegal_action", $"potion_slot {slot} is out of range; the belt has {holders.Length} slots.");
        if (!PotionInspection.Displayed(holders[slot])) return Reject("illegal_action", "The specified potion slot is hidden or not ready.");
        if (!holders[slot].HasPotion) return Reject("illegal_action", "The specified potion slot is empty.");
        NPotionHolder? holder = PotionActions.Find(slot);
        var potion = holder?.Potion?.Model;
        var player = LocalPlayer!;
        if (potion == null || potion.Owner != player || player.GetPotionSlotIndex(potion) != slot
            || PotionActions.Type(potion) == null)
            return Reject("illegal_action", "The potion in that slot is no longer owned by the local player or has an unsupported target type.");
        if (query) return InspectionSuccess(request, before, PotionActions.Read(potion, slot,
            before.GetProperty("snapshot_id").GetString()!, useStage));
        if ((use ? PotionActions.Reason(potion) : PotionActions.RemovalReason(potion)) is { } unavailable)
            return Reject("illegal_action", unavailable);
        MegaCrit.Sts2.Core.Entities.Creatures.Creature? target = null;
        if (use && PotionActions.TargetReason(potion, suppliedTarget, merchant, creatureId, out target) is { } targetReason)
            return Reject("illegal_action", targetReason);
        bool inCombat = CombatManager.Instance.IsInProgress;
        if (inCombat && !STS2RitsuLib.RitsuLibFramework.IsActive)
            return Reject("illegal_action", "RitsuLib is unavailable; no potion action was submitted.");
        var run = player.RunState;
        var journal = CombatJournalScope.Current!;
        GameAction? submitted = null;
        var discardAction = use ? null : new DiscardPotionGameAction(player, (uint)slot, inCombat);
        var progress = use ? null : new PotionDiscardProgress();
        var discardResult = use ? null : JsonSerializer.SerializeToNode(PotionActions.Reference(potion, slot))!.AsObject();
        var potionJournal = PotionJournal.Current!;
        bool discardExecuting = false;
        void DiscardObserved(PotionModel removed)
        {
            if (discardExecuting && submitted?.State == GameActionState.Executing
                && ReferenceEquals(removed, potion)) progress?.ObserveDiscard();
        }
        bool canceled = false;
        void Canceled(GameAction _) => canceled = true;
        void Executed(GameAction _) => discardExecuting = true;
        var actionExecution = execution;
        void Enqueued(GameAction action)
        {
            if (submitted != null) return;
            if (use ? action is not UsePotionAction played || played.Player != player || played.PotionIndex != slot
                : !ReferenceEquals(action, discardAction)) return;
            submitted = action;
            progress?.Submit();
            actionExecution?.ActionSubmitted();
            action.BeforeCancelled += Canceled;
            if (progress != null) action.BeforeExecuted += Executed;
        }
        RunManager.Instance.ActionQueueSet.ActionEnqueued += Enqueued;
        if (progress != null) potionJournal.DiscardObserved += DiscardObserved;
        try
        {
            UiChanged();
            holder!.DisableUntilPotionRemoved();
            if (use) potion.EnqueueManualUse(potion.TargetType == TargetType.Self ? player.Creature : target);
            else RunManager.Instance.ActionQueueSynchronizer.RequestEnqueue(discardAction!);
            var (after, reason) = await ActionObservation(() =>
            {
                if (!use && submitted?.Exception != null) return "interrupted";
                bool finished = submitted?.State is GameActionState.Finished or GameActionState.Canceled;
                bool ready = finished && (use ? CanHandlePotions() : CanDiscardPotions());
                string? boundary = journal.StopReason(ready);
                if (!inCombat)
                    boundary = !ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState()) ? "interrupted"
                        : RunUi.Transitioning() ? null
                        : CardSelection.AwaitingInput ? NonCombatBoundary()
                        : ready ? ShopInspection.Current == null ? "action_completed" : NonCombatBoundary() : null;
                return boundary is "player_ready" or "action_completed" && canceled ? "action_canceled" : boundary;
            });
            object transition = journal.Result(reason);
            if (progress != null)
            {
                bool sameRun = ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState());
                bool stillVisible = sameRun && ReferenceEquals(PotionInspection.DisplayedAt(slot)?.Potion?.Model, potion);
                if (canceled && stillVisible) progress.Cancel();
                if (submitted?.State is GameActionState.Finished or GameActionState.Canceled)
                    progress.Finish(submitted.Exception != null);
                if (!sameRun || reason is "timeout" or "interrupted" || ActionEventScope.Current?.Buffer.Truncated == true
                    || progress.Status == "queued" && (reason != "choice_required" || !stillVisible
                        || submitted?.State != GameActionState.WaitingForExecution)) progress.Abandon();
                discardResult!["status"] = progress.Status;
            }
            return Success(request, ResponseBuilder.WithTransition(after, transition, potionDiscard: discardResult));
        }
        finally
        {
            RunManager.Instance.ActionQueueSet.ActionEnqueued -= Enqueued;
            if (progress != null) potionJournal.DiscardObserved -= DiscardObserved;
            if (submitted != null) submitted.BeforeCancelled -= Canceled;
            if (progress != null && submitted != null) submitted.BeforeExecuted -= Executed;
        }
    }
}
