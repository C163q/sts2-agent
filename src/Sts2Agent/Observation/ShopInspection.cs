using Godot;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Merchant;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Events.Custom;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Screens.Shops;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;
using System.Reflection;

namespace Sts2Agent;

internal sealed class ShopInspection
{
    internal sealed record Context(Control Owner, NMerchantInventory Inventory, NMerchantButton Merchant, NProceedButton Proceed);
    private readonly Dictionary<NMerchantSlot, (object payload, int id)> ids = [];
    private Control? owner;
    private int nextId;
    private static readonly PropertyInfo SlotVisual = typeof(NMerchantSlot).GetProperty("Visual", BindingFlags.Instance | BindingFlags.NonPublic)
        ?? throw new MissingMemberException(typeof(NMerchantSlot).FullName, "Visual");
    public int Generation { get; private set; }

    public static Context? Current
    {
        get
        {
            var room = RunManager.Instance.DebugOnlyGetState()?.CurrentRoom;
            Context? result = room is MerchantRoom && NMerchantRoom.Instance is { } merchant && ReferenceEquals(merchant.Room, room)
                ? new(merchant, merchant.Inventory, merchant.MerchantButton, merchant.ProceedButton)
                : room is EventRoom { CanonicalEvent: MegaCrit.Sts2.Core.Models.Events.FakeMerchant } events
                    && RunUi.LocalEvent?.Node is NFakeMerchant fake
                ? new(fake, fake.Inventory, fake.MerchantButton, fake.GetNode<NProceedButton>("%ProceedButton")) : null;
            return result != null && GodotObject.IsInstanceValid(result.Owner) && result.Owner.IsNodeReady()
                && !result.Owner.IsQueuedForDeletion() ? result : null;
        }
    }

    public static bool Exposed(Context context) => ReferenceEquals(Current?.Owner, context.Owner) && RunUi.NonCombatVisible()
        && NRun.Instance?.GlobalUi.Overlays.ScreenCount == 0 && !VisibleUi.Shown(NRun.Instance?.GlobalUi.MapScreen)
        && VisibleUi.Shown(context.Owner);
    public static NBackButton Back(Context context) => context.Inventory.GetNode<NBackButton>("%BackButton");
    public static bool Animating(Context context) => RewardInspection.Animating(context.Inventory, "_inventoryTween");
    public static bool Busy => ShopTransactions.Pending || RelicObtainTracker.Pending;
    private enum PagePurpose { Inspect, Open, Close }

    public static string? InspectionUnavailableReason(Context? context)
        => PageUnavailableReason(context, PagePurpose.Inspect)
            ?? (!context!.Inventory.IsOpen ? "Open the shop with open_shop before inspecting its goods." : null);

    private static string? PageUnavailableReason(Context? context, PagePurpose operation)
    {
        var (purpose, subject) = operation switch
        {
            PagePurpose.Inspect => ("inspecting shop goods", "Shop inspection"),
            PagePurpose.Open => ("opening the shop", "Opening the shop"),
            PagePurpose.Close => ("closing the shop", "Closing the shop"),
            _ => throw new ArgumentOutOfRangeException(nameof(operation))
        };
        if (!RunManager.Instance.IsInProgress) return operation == PagePurpose.Inspect
            ? "No local run is available for shop inspection." : $"No local run is available for {purpose}.";
        if (context == null) return "No shop is available on the current screen.";
        if (!RunContext.Singleplayer) return $"{subject} requires a local single-player run.";
        var map = NRun.Instance?.GlobalUi.MapScreen;
        if (VisibleUi.Shown(map)) return map!.IsOpen
            ? $"Close the map with close_map before {purpose}."
            : $"Wait for the map to finish closing before {purpose}.";
        if (CardView.Current != null) return $"Close the card browsing page with close_card_view before {purpose}.";
        if (CardSelection.Current != null) return $"Resolve the current card selection before {purpose}; inspect_selection shows its choices.";
        if (RewardInspection.Current != null) return $"Resolve the current reward page before {purpose}; inspect_rewards shows its rows.";
        if (RunUi.Transitioning()) return $"Wait for the screen transition before {purpose}.";
        if (!Exposed(context)) return "The shop is covered by a dialog or another screen.";
        if (Animating(context)) return "Wait for the shop inventory to finish opening or closing.";
        return null;
    }

    private static string? ActivityUnavailableReason(Context context, string purpose)
    {
        if (MegaCrit.Sts2.Core.Nodes.Combat.NTargetManager.Instance.IsInSelection)
            return $"Wait for the current targeting to finish before {purpose}.";
        if (Busy) return $"Wait for the current purchase or relic effect to finish before {purpose}.";
        if (RunUi.CardPreviewsPending()) return $"Wait for card previews to finish before {purpose}.";
        if (RunUi.ResourceMotionPending()) return $"Wait for resource animations to finish before {purpose}.";
        if (!RunManager.Instance.ActionQueueSet.IsEmpty) return $"Wait for queued game actions to finish before {purpose}.";
        return PrivateFields.Read(context.Inventory, "_isInputBlocked") is not false
            ? $"Wait for the shop to accept input before {purpose}." : null;
    }

    public static string? OpenUnavailableReason(Context? context)
    {
        if (PageUnavailableReason(context, PagePurpose.Open) is { } unavailable) return unavailable;
        if (context!.Inventory.IsOpen) return "The shop is already open. Use inspect_shop to read its goods or close_shop to return to the merchant.";
        if (ActivityUnavailableReason(context, "opening the shop") is { } pending) return pending;
        if (context.Merchant.IsLocalPlayerDead) return "The local player is dead; the merchant cannot open the shop.";
        if (!MerchantShown(context)) return "The merchant is not currently visible and interactive.";
        return !context.Merchant.IsEnabled ? "Wait for the merchant to become enabled before opening the shop." : null;
    }

    public static string? CloseUnavailableReason(Context? context)
    {
        if (PageUnavailableReason(context, PagePurpose.Close) is { } unavailable) return unavailable;
        if (!context!.Inventory.IsOpen) return "The shop is already closed. Use open_shop to view its goods.";
        if (ActivityUnavailableReason(context, "closing the shop") is { } pending) return pending;
        return !Back(context).IsEnabled ? "Wait for the shop back button to become enabled before closing the shop." : null;
    }

    public static bool Ready(Context context) => RunContext.Singleplayer && Exposed(context) && !Animating(context)
        && ActivityUnavailableReason(context, "using shop controls") == null
        && (context.Inventory.IsOpen ? Back(context).IsEnabled : context.Merchant.IsEnabled || context.Proceed.IsEnabled);

    public static bool MerchantShown(Context context) => context.Merchant.IsVisibleInTree()
        && VisibleUi.Descendants<CanvasItem>(context.Merchant).Any(VisibleUi.OnScreen);

    private static object Payload(NMerchantSlot slot) => slot.Entry switch
    {
        MerchantCardEntry card when card.CreationResult != null => card.CreationResult.Card,
        MerchantRelicEntry relic when relic.Model != null => relic.Model,
        MerchantPotionEntry potion when potion.Model != null => potion.Model,
        _ => slot.Entry
    };

    internal static CanvasItem Visual(NMerchantSlot slot) => (CanvasItem)SlotVisual.GetValue(slot)!;

    private static bool ContentDisplayed(CanvasItem visual) => VisibleUi.Shown(visual)
        && (visual is Control { Size: var size } && size == Vector2.Zero
            ? VisibleUi.Descendants<CanvasItem>(visual).Any(VisibleUi.Displayed) : VisibleUi.Displayed(visual));

    internal static bool DisplayedSlot(NMerchantSlot slot) => VisibleUi.Displayed(slot)
        && (slot.Entry.IsStocked || slot.Entry is MerchantCardRemovalEntry) && ContentDisplayed(Visual(slot));

    private static bool VisibleSlot(NMerchantSlot slot) => DisplayedSlot(slot) && VisibleUi.OnScreen(slot);

    internal static bool CanHover(Context context, NMerchantSlot slot)
    {
        if (!DisplayedSlot(slot) || slot.Entry is MerchantCardRemovalEntry { Used: true }
            || PrivateFields.Read(context.Inventory, "_isInputBlocked") is not false) return false;
        // Slots subscribe to MouseEntered directly; disabling clicks alone does not remove hover help.
        bool mouse = VisibleUi.Displayed(slot.Hitbox) && slot.Hitbox.GetMouseFilterWithOverride() != Control.MouseFilterEnum.Ignore;
        bool controller = slot.GetFocusModeWithOverride() == Control.FocusModeEnum.All;
        return mouse || controller;
    }

    public static bool Purchasable(NMerchantSlot slot) => VisibleSlot(slot) && slot.Entry.IsStocked
        && slot.Hitbox.IsEnabled && slot.Hitbox.IsVisibleInTree() && slot.Hitbox.MouseFilter != Control.MouseFilterEnum.Ignore
        && VisibleUi.Number(slot, "%CostLabel") is >= 0 && slot.Entry.EnoughGold;

    public void Synchronize()
    {
        var context = Current;
        if (!ReferenceEquals(owner, context?.Owner))
        {
            owner = context?.Owner;
            Generation++;
            ids.Clear(); nextId = 0;
        }
        if (context == null || !Exposed(context) || !context.Inventory.IsOpen || Animating(context)) return;
        foreach (var slot in context.Inventory.GetAllSlots().Where(DisplayedSlot))
        {
            var payload = Payload(slot);
            if (!ids.TryGetValue(slot, out var known) || !ReferenceEquals(payload, known.payload))
                ids[slot] = (payload, nextId++);
        }
    }

    public NMerchantSlot? Find(Context context, int id) => context.Inventory.GetAllSlots().FirstOrDefault(slot =>
        VisibleSlot(slot) && ids.TryGetValue(slot, out var value) && value.id == id && ReferenceEquals(value.payload, Payload(slot)));

    public object? Read(bool full = false)
        => Read(full, out _);

    internal sealed record Inspection(object? shop, string[] unavailable_hover_sources);
    public Inspection Inspect() => new(Read(true, out var unavailable), unavailable);

    private object? Read(bool full, out string[] unavailable)
    {
        unavailable = [];
        var context = Current;
        if (context == null) return null;
        if (!Exposed(context)) return new { status = "covered", view = (string?)null, items = (object?)null,
            open = (object?)null, back = (object?)null, proceed = (object?)null };
        bool animating = Animating(context), opened = context.Inventory.IsOpen;
        string view = animating ? opened ? "opening" : "closing" : opened ? "inventory" : "merchant";
        bool ready = Ready(context);
        var slots = opened && !animating ? context.Inventory.GetAllSlots().Where(DisplayedSlot).ToArray() : [];
        if (full) unavailable = slots.Where(slot => slot.Entry is not MerchantCardRemovalEntry { Used: true }
            && !CanHover(context, slot)).Select(slot => "shop.items." + ids[slot].id).ToArray();
        return EnglishCardText.Read(() => new
        {
            status = "visible", view,
            items = opened && !animating ? slots.Select(slot => ReadItem(slot, ready, full, CanHover(context, slot))).ToArray() : null,
            open = !opened && !animating && MerchantShown(context) ? new { enabled = OpenUnavailableReason(context) == null } : null,
            back = opened && !animating && VisibleUi.OnScreen(Back(context)) ? new { enabled = CloseUnavailableReason(context) == null } : null,
            proceed = !opened && !animating && VisibleUi.OnScreen(context.Proceed) ? new
            {
                text = EnglishCardText.Plain(NProceedButton.ProceedLoc.GetFormattedText()), enabled = ready && context.Proceed.IsEnabled
            } : null
        });
    }

    private Dictionary<string, object?> ReadItem(NMerchantSlot slot, bool ready, bool full, bool hoverable)
    {
        string kind = slot.Entry switch
        {
            MerchantCardEntry => "card", MerchantRelicEntry => "relic", MerchantPotionEntry => "potion", MerchantCardRemovalEntry => "card_removal",
            _ => throw new InvalidOperationException("Unsupported merchant slot.")
        };
        bool used = slot.Entry is MerchantCardRemovalEntry { Used: true };
        int? price = used ? null : VisibleUi.DisplayedNumber(slot, "%CostLabel");
        var result = new Dictionary<string, object?>
        {
            ["id"] = ids[slot].id, ["kind"] = kind, ["position"] = Position(slot), ["price"] = price,
            ["affordable"] = price.HasValue ? slot.Entry.EnoughGold : (bool?)null,
            ["enabled"] = ready && Purchasable(slot)
        };
        if (slot.Entry is MerchantCardEntry card)
        {
            var details = BrowsedCard.Read(card.CreationResult!.Card, "", PileType.None, false, full, appearance: true);
            details.Remove("id"); result["card"] = details;
            if (full && !hoverable) details["hover_tips"] = null;
            result["on_sale"] = VisibleUi.Shown(slot.GetNode<Node2D>("%SaleVisual"));
        }
        else if (slot.Entry is MerchantRelicEntry relic)
        {
            result["name"] = EnglishCardText.Plain(relic.Model!.Title.GetFormattedText());
            if (full)
            {
                var details = hoverable ? RelicInspection.Details(relic.Model, null) : null;
                result["description"] = details?.description; result["hover_tips"] = details?.hover_tips ?? [];
            }
        }
        else if (slot.Entry is MerchantPotionEntry potion)
        {
            var details = full && hoverable ? PotionInspection.Details(potion.Model!) : null;
            result["name"] = EnglishCardText.Plain(potion.Model!.Title.GetFormattedText());
            if (full) { result["description"] = details?.description; result["hover_tips"] = details?.hover_tips ?? []; }
        }
        else
        {
            result["name"] = EnglishCardText.Plain(new LocString("merchant_room", "MERCHANT.cardRemovalService.title").GetFormattedText());
            result["used"] = used;
            if (full && !used)
            {
                var description = new LocString("merchant_room", "MERCHANT.cardRemovalService.description");
                description.Add("Amount", MerchantCardRemovalEntry.PriceIncrease);
                result["description"] = hoverable ? EnglishCardText.Plain(description.GetFormattedText()) : null;
                result["hover_tips"] = Array.Empty<object>();
            }
        }
        return result;
    }

    private static string Position(NMerchantSlot slot)
    {
        string group = slot.GetParent().Name.ToString() switch
        {
            "CharacterCards" => "character_card", "ColorlessCards" => "colorless_card", "Relics" => "relic", "Potions" => "potion", _ => "card_removal"
        };
        return group + ":" + (slot is NMerchantCardRemoval ? 0 : slot.GetIndex());
    }
}
