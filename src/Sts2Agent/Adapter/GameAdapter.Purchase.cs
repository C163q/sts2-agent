using HarmonyLib;
using MegaCrit.Sts2.Core.Entities.Merchant;
using MegaCrit.Sts2.Core.Nodes.Screens.Shops;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private async Task<string> PurchaseShopItem(Request request, NMerchantSlot slot, int itemId)
    {
        var run = RunManager.Instance.DebugOnlyGetState();
        var entry = slot.Entry;
        string? reported = null;
        void Purchased(PurchaseStatus _, MerchantEntry __) => reported = "success";
        void Failed(PurchaseStatus status) => reported = status switch
        {
            PurchaseStatus.FailureSpace => "failure_space", PurchaseStatus.FailureForbidden => "failure_forbidden",
            PurchaseStatus.FailureGold => "failure_gold", PurchaseStatus.FailureOutOfStock => "failure_out_of_stock", _ => null
        };
        entry.PurchaseCompleted += Purchased;
        entry.PurchaseFailed += Failed;
        try
        {
            UiChanged();
            var submitted = (Task)AccessTools.Method(typeof(NMerchantSlot), "OnSelected").Invoke(slot, null)!;
            var (after, reason) = await ActionObservation(() =>
            {
                if (!ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState()) || submitted.IsCanceled) return "interrupted";
                if (submitted.IsFaulted) throw submitted.Exception!.GetBaseException();
                string? boundary = NonCombatBoundary();
                return boundary == "action_completed" && RewardInspection.Current == null && !submitted.IsCompleted ? null : boundary;
            });
            bool awaitingInput = reason == "choice_required" && CardSelection.Current is { Supported: true, Status: "visible" }
                    && CardSelection.AwaitingInput
                || reason == "action_completed" && RewardInspection.Current is { } rewards && RewardInspection.Ready(rewards);
            string? outcome = PurchaseOutcome.AtBoundary(reported, submitted, awaitingInput);
            return TransitionSuccess(request, after, reason, purchaseResult: outcome == null ? null : new { item_id = itemId, status = outcome });
        }
        finally
        {
            entry.PurchaseCompleted -= Purchased;
            entry.PurchaseFailed -= Failed;
        }
    }
}
