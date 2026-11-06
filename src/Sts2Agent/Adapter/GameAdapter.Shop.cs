using System.Text.Json;
using HarmonyLib;
using MegaCrit.Sts2.Core.Entities.Merchant;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Screens.Shops;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{

    private async Task<string> ShopRequest(Request request, JsonElement before)
    {
        int itemId = -1;
        if (request.Operation == "buy_item" && (request.Arguments is not { } args || args.EnumerateObject().Count() != 1
            || !args.TryGetProperty("item_id", out var id) || id.ValueKind != JsonValueKind.Number || !id.TryGetInt32(out itemId) || itemId < 0))
            return FileMailbox.Error(request.Id, "invalid_request", "A nonnegative item_id is required.");
        bool inspect = request.Operation == "inspect_shop";
        if (!inspect && request.ExpectedState != before.GetProperty("snapshot_id").GetString())
            return FileMailbox.Error(request.Id, "stale_state", "Read the current shop before acting.");
        var context = ShopInspection.Current;
        if (inspect)
        {
            if (ShopInspection.InspectionUnavailableReason(context) is { } unavailable)
                return FileMailbox.Error(request.Id, "illegal_action", unavailable, publicMessage: true);
            var details = shopInspection.Inspect();
            return InspectionSuccess(request, before, new { details.shop, details.unavailable_hover_sources,
                top_bar = before.GetProperty("top_bar") });
        }
        if (request.Operation is "open_shop" or "close_shop") return await ShopViewRequest(request, context);
        if (context == null || !ShopInspection.Exposed(context) || !RunContext.Singleplayer
            || !ShopInspection.Ready(context))
            return FileMailbox.Error(request.Id, "illegal_action", "Return to an available single-player shop.");
        var run = RunManager.Instance.DebugOnlyGetState();
        Task? submitted = null;
        string? outcome = null;
        void Purchased(PurchaseStatus _, MerchantEntry __) => outcome = "success";
        void Failed(PurchaseStatus status) => outcome = status switch
        {
            PurchaseStatus.FailureSpace => "failure_space", PurchaseStatus.FailureForbidden => "failure_forbidden",
            PurchaseStatus.FailureGold => "failure_gold", PurchaseStatus.FailureOutOfStock => "failure_out_of_stock", _ => null
        };
        NMerchantSlot? slot = request.Operation == "buy_item" ? shopInspection.Find(context, itemId) : null;
        if (request.Operation == "buy_item" && (!context.Inventory.IsOpen || slot == null || !ShopInspection.Purchasable(slot)))
            return FileMailbox.Error(request.Id, "illegal_action", "The observed shop item is unavailable.");
        if (slot != null) { slot.Entry.PurchaseCompleted += Purchased; slot.Entry.PurchaseFailed += Failed; }
        try
        {
            UiChanged();
            if (slot != null)
                submitted = (Task)AccessTools.Method(typeof(NMerchantSlot), "OnSelected").Invoke(slot, null)!;
            var (after, reason) = await ActionObservation(() =>
            {
                if (!ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())) return "interrupted";
                if (submitted?.IsFaulted == true) throw submitted.Exception!.GetBaseException();
                string? boundary = NonCombatBoundary();
                return boundary == "action_completed" && RewardInspection.Current == null && submitted is { IsCompleted: false } ? null : boundary;
            });
            if (submitted is { IsCompletedSuccessfully: true } && outcome == null) outcome = "canceled";
            return TransitionSuccess(request, after, reason, purchaseResult:
                slot != null && outcome != null ? new { item_id = itemId, status = outcome } : null);
        }
        finally
        {
            if (slot != null) { slot.Entry.PurchaseCompleted -= Purchased; slot.Entry.PurchaseFailed -= Failed; }
        }
    }

    private async Task<string> ShopViewRequest(Request request, ShopInspection.Context? context)
    {
        bool opening = request.Operation == "open_shop";
        if ((opening ? ShopInspection.OpenUnavailableReason(context) : ShopInspection.CloseUnavailableReason(context)) is { } unavailable)
            return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action", unavailable);
        var run = RunManager.Instance.DebugOnlyGetState();
        UiChanged();
        if (opening) context!.Merchant.ForceClick();
        else ShopInspection.Back(context!).ForceClick();
        var (after, reason) = await ActionObservation(() => ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
            && ReferenceEquals(context!.Owner, ShopInspection.Current?.Owner) ? NonCombatBoundary() : "interrupted");
        return TransitionSuccess(request, after, reason);
    }
}
