using System.Text.Json;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed partial class GameAdapter
{

    private async Task<string> ShopRequest(Request request, JsonElement before)
    {
        int itemId = -1;
        if (request.Operation == "buy_item" && (request.Arguments is not { } args || args.EnumerateObject().Count() != 1
            || !args.TryGetProperty("item_id", out var id) || id.ValueKind != JsonValueKind.Number || !id.TryGetInt32(out itemId) || itemId < 0))
            return FileMailbox.RejectedBeforeSubmission(request.Id, "invalid_request", "A nonnegative item_id is required.");
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
        if (ShopInspection.PurchaseUnavailableReason(context) is { } unavailablePurchase)
            return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action", unavailablePurchase);
        var slot = shopInspection.Find(context!, itemId);
        if (slot == null) return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action",
            "No current item matches item_id; it may have been sold or restocked. inspect_shop shows the current IDs.");
        if (ShopInspection.ItemUnavailableReason(slot) is { } unavailableItem)
            return FileMailbox.RejectedBeforeSubmission(request.Id, "illegal_action", unavailableItem);
        return await PurchaseShopItem(request, slot, itemId);
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
