using System.Text.Json;
using HarmonyLib;
using MegaCrit.Sts2.Core.Entities.Merchant;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Screens.Shops;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{
    private readonly ShopInspection shopInspection = new();

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
        if (context == null || !ShopInspection.Exposed(context) || !TreasureInspection.Singleplayer
            || (!inspect && !ShopInspection.Ready(context)))
            return FileMailbox.Error(request.Id, "illegal_action", "Return to an available single-player shop.");
        if (inspect)
        {
            if (!context.Inventory.IsOpen || ShopInspection.Animating(context))
                return FileMailbox.Error(request.Id, "illegal_action", "Open the shop before inspecting its items.");
            return InspectionSuccess(request.Id, before, new { shop = shopInspection.Read(full: true)
            });
        }
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
        if (request.Operation == "open_shop" && (context.Inventory.IsOpen || !context.Merchant.IsEnabled || !ShopInspection.MerchantShown(context))
            || request.Operation == "close_shop" && (!context.Inventory.IsOpen || !ShopInspection.Back(context).IsEnabled)
            || request.Operation == "proceed" && (context.Inventory.IsOpen || !context.Proceed.IsEnabled || !VisibleUi.OnScreen(context.Proceed)))
            return FileMailbox.Error(request.Id, "illegal_action", "This shop button is unavailable.");
        if (slot != null) { slot.Entry.PurchaseCompleted += Purchased; slot.Entry.PurchaseFailed += Failed; }
        try
        {
            uiGeneration++;
            if (slot != null)
                submitted = (Task)AccessTools.Method(typeof(NMerchantSlot), "OnSelected").Invoke(slot, null)!;
            else if (request.Operation == "open_shop") context.Merchant.ForceClick();
            else if (request.Operation == "close_shop") ShopInspection.Back(context).ForceClick();
            else context.Proceed.ForceClick();
            var (after, reason) = await ActionObservation(() =>
            {
                if (!ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())) return "interrupted";
                if (submitted?.IsFaulted == true) throw submitted.Exception!.GetBaseException();
                string? boundary = NonCombatBoundary();
                return boundary == "action_completed" && RewardInspection.Current == null && submitted is { IsCompleted: false } ? null : boundary;
            });
            if (submitted is { IsCompletedSuccessfully: true } && outcome == null) outcome = "canceled";
            return Success(request.Id, after[..^1] + ",\"transition\":" + JsonSerializer.Serialize(new
            {
                stop_reason = reason, complete = reason is not ("timeout" or "interrupted"), events = Array.Empty<object>()
            }) + (slot != null && outcome != null ? ",\"purchase_result\":" + JsonSerializer.Serialize(new { item_id = itemId, status = outcome }) : "") + "}");
        }
        finally
        {
            if (slot != null) { slot.Entry.PurchaseCompleted -= Purchased; slot.Entry.PurchaseFailed -= Failed; }
        }
    }
}
