using System.Text.Json;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Actions;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Potions;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private static bool CanHandlePotions() => RunManager.Instance.IsInProgress
        && RunManager.Instance.IsSingleplayerOrFakeMultiplayer && LocalPlayer?.Creature.IsAlive == true
        && !LocalPlayer.RunState.IsGameOver
        && (!AncientInspection.Busy || RewardInspection.Current is { } ancientRewards && RewardInspection.Ready(ancientRewards))
        && (CombatManager.Instance.IsInProgress || !EventTaskTracker.Pending || RewardInspection.Current is { } eventRewards && RewardInspection.Ready(eventRewards))
        && (!ShopTransactions.Pending || RewardInspection.Current is { } rewards && RewardInspection.Ready(rewards))
        && (ShopInspection.Current is not { } shop || !ShopInspection.Exposed(shop) || ShopInspection.Ready(shop)) && CardSelection.Current == null
        && RunManager.Instance.ActionQueueSet.IsEmpty && !NTargetManager.Instance.IsInSelection
        && (CombatManager.Instance.IsInProgress ? CanPlayCards() : RunUi.NonCombatVisible());

    private async Task<string> PotionRequest(Request request, JsonElement before)
    {
        bool query = request.Operation == "inspect_targets", use = request.Operation == "use_potion";
        var arguments = request.Arguments;
        if (arguments == null || !arguments.Value.TryGetProperty("potion_slot", out var suppliedSlot)
            || suppliedSlot.ValueKind != JsonValueKind.Number || !suppliedSlot.TryGetInt32(out int slot) || slot < 0
            || arguments.Value.EnumerateObject().Any(p => p.Name != "potion_slot" && (!use || p.Name != "target_id"))
            || arguments.Value.EnumerateObject().Select(p => p.Name).Distinct().Count() != arguments.Value.EnumerateObject().Count())
            return FileMailbox.Error(request.Id, "invalid_request", "Invalid potion arguments.", publicMessage: query);
        bool suppliedTarget = arguments.Value.TryGetProperty("target_id", out var targetId);
        uint creatureId = 0;
        bool merchant = suppliedTarget && targetId.ValueKind == JsonValueKind.String && targetId.GetString() == "merchant";
        if (suppliedTarget && !merchant && (targetId.ValueKind != JsonValueKind.Number || !targetId.TryGetUInt32(out creatureId)))
            return FileMailbox.Error(request.Id, "invalid_request", "Invalid potion target.");
        if (!query && request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read current state before using or discarding a potion.");
        if (!CanHandlePotions()) return FileMailbox.Error(request.Id, "illegal_action", "Potion actions are unavailable in this screen.", publicMessage: query);
        NPotionHolder? holder = PotionActions.Find(slot);
        var potion = holder?.Potion?.Model;
        var player = LocalPlayer!;
        if (potion == null || potion.Owner != player || player.GetPotionSlotIndex(potion) != slot
            || PotionActions.Type(potion) == null)
            return FileMailbox.Error(request.Id, "illegal_action", "No supported visible potion occupies that slot.", publicMessage: query);
        if (query) return Success(request.Id, JsonSerializer.Serialize(PotionActions.Read(potion, slot, before.GetProperty("snapshot_id").GetString()!)));
        var target = suppliedTarget && !merchant ? PotionActions.Targets(potion).FirstOrDefault(c => c.CombatId == creatureId) : null;
        if (!PotionActions.Discardable(potion) || use && (PotionActions.Reason(potion) != null
            || suppliedTarget != PotionActions.RequiresTarget(potion)
            || suppliedTarget && (merchant ? !PotionActions.MerchantVisible(potion) : target == null)
            || merchant != (potion.TargetType == TargetType.TargetedNoCreature)
            || suppliedTarget && !potion.IsValidTarget(target)))
            return FileMailbox.Error(request.Id, "illegal_action", "The potion or specified target cannot be used or discarded now.");
        bool inCombat = CombatManager.Instance.IsInProgress;
        if (inCombat && !STS2RitsuLib.RitsuLibFramework.IsActive)
            return FileMailbox.Error(request.Id, "illegal_action", "RitsuLib is unavailable; no potion action was submitted.");
        var run = player.RunState;
        var journal = CombatJournalScope.Current!;
        GameAction? submitted = null;
        bool canceled = false;
        void Canceled(GameAction _) => canceled = true;
        void Enqueued(GameAction action)
        {
            if (submitted != null) return;
            if (use ? action is not UsePotionAction played || played.Player != player || played.PotionIndex != slot
                : action is not DiscardPotionGameAction || action.OwnerId != player.NetId) return;
            submitted = action;
            action.BeforeCancelled += Canceled;
        }
        RunManager.Instance.ActionQueueSet.ActionEnqueued += Enqueued;
        try
        {
            uiGeneration++;
            holder!.DisableUntilPotionRemoved();
            if (use) potion.EnqueueManualUse(potion.TargetType == TargetType.Self ? player.Creature : target);
            else RunManager.Instance.ActionQueueSynchronizer.RequestEnqueue(new DiscardPotionGameAction(player, (uint)slot, inCombat));
            var (after, reason) = await ActionObservation(() =>
            {
                bool finished = submitted?.State is GameActionState.Finished or GameActionState.Canceled;
                bool ready = finished && CanHandlePotions();
                string? boundary = journal.StopReason(ready);
                if (!inCombat)
                    boundary = !ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState()) ? "interrupted"
                        : RunUi.Transitioning() ? null
                        : CardSelection.AwaitingInput ? NonCombatBoundary()
                        : ready ? ShopInspection.Current == null ? "action_completed" : NonCombatBoundary() : null;
                return boundary is "player_ready" or "action_completed" && canceled ? "action_canceled" : boundary;
            });
            object transition = journal.Result(reason);
            return Success(request.Id, after[..^1] + ",\"transition\":" + JsonSerializer.Serialize(transition) + "}");
        }
        finally
        {
            RunManager.Instance.ActionQueueSet.ActionEnqueued -= Enqueued;
            if (submitted != null) submitted.BeforeCancelled -= Canceled;
        }
    }
}
