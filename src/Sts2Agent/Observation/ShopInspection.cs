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

namespace Sts2Agent;

internal sealed class ShopInspection
{
    internal sealed record Context(Control Owner, NMerchantInventory Inventory, NMerchantButton Merchant, NProceedButton Proceed);
    private readonly Dictionary<NMerchantSlot, (object payload, int id)> ids = [];
    private Control? owner;
    private int nextId;
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
    public static bool Ready(Context context) => RunContext.Singleplayer && Exposed(context) && !Animating(context)
        && !MegaCrit.Sts2.Core.Nodes.Combat.NTargetManager.Instance.IsInSelection
        && !Busy && !RunUi.CardPreviewsPending() && !RunUi.ResourceMotionPending() && RunManager.Instance.ActionQueueSet.IsEmpty
        && CardSelection.Field(context.Inventory, "_isInputBlocked") is false
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

    private static bool VisibleSlot(NMerchantSlot slot) => VisibleUi.OnScreen(slot)
        && (slot.Entry.IsStocked || slot.Entry is MerchantCardRemovalEntry);

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
        foreach (var slot in context.Inventory.GetAllSlots().Where(VisibleSlot))
        {
            var payload = Payload(slot);
            if (!ids.TryGetValue(slot, out var known) || !ReferenceEquals(payload, known.payload))
                ids[slot] = (payload, nextId++);
        }
    }

    public NMerchantSlot? Find(Context context, int id) => context.Inventory.GetAllSlots().FirstOrDefault(slot =>
        VisibleSlot(slot) && ids.TryGetValue(slot, out var value) && value.id == id && ReferenceEquals(value.payload, Payload(slot)));

    public object? Read(bool full = false)
    {
        var context = Current;
        if (context == null) return null;
        if (!Exposed(context)) return new { status = "covered", view = (string?)null, items = (object?)null,
            open = (object?)null, back = (object?)null, proceed = (object?)null };
        bool animating = Animating(context), opened = context.Inventory.IsOpen;
        string view = animating ? opened ? "opening" : "closing" : opened ? "inventory" : "merchant";
        bool ready = Ready(context);
        return EnglishCardText.Read(() => new
        {
            status = "visible", view,
            items = opened && !animating ? context.Inventory.GetAllSlots().Where(VisibleSlot).Select(slot => ReadItem(slot, ready, full)).ToArray() : null,
            open = !opened && !animating && MerchantShown(context) ? new { enabled = ready && context.Merchant.IsEnabled } : null,
            back = opened && !animating && VisibleUi.OnScreen(Back(context)) ? new { enabled = ready && Back(context).IsEnabled } : null,
            proceed = !opened && !animating && VisibleUi.OnScreen(context.Proceed) ? new
            {
                text = EnglishCardText.Plain(NProceedButton.ProceedLoc.GetFormattedText()), enabled = ready && context.Proceed.IsEnabled
            } : null
        });
    }

    private Dictionary<string, object?> ReadItem(NMerchantSlot slot, bool ready, bool full)
    {
        string kind = slot.Entry switch
        {
            MerchantCardEntry => "card", MerchantRelicEntry => "relic", MerchantPotionEntry => "potion", MerchantCardRemovalEntry => "card_removal",
            _ => throw new InvalidOperationException("Unsupported merchant slot.")
        };
        bool used = slot.Entry is MerchantCardRemovalEntry { Used: true };
        int? price = used ? null : VisibleUi.Number(slot, "%CostLabel");
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
            result["on_sale"] = VisibleUi.Shown(slot.GetNode<Node2D>("%SaleVisual"));
        }
        else if (slot.Entry is MerchantRelicEntry relic)
        {
            result["name"] = EnglishCardText.Plain(relic.Model!.Title.GetFormattedText());
            if (full)
            {
                var details = RelicInspection.Details(relic.Model, null);
                result["description"] = details.description; result["hover_tips"] = details.hover_tips;
            }
        }
        else if (slot.Entry is MerchantPotionEntry potion)
        {
            var details = full ? PotionInspection.Details(potion.Model!) : null;
            result["name"] = EnglishCardText.Plain(potion.Model!.Title.GetFormattedText());
            if (details != null) { result["description"] = details.description; result["hover_tips"] = details.hover_tips; }
        }
        else
        {
            result["name"] = EnglishCardText.Plain(new LocString("merchant_room", "MERCHANT.cardRemovalService.title").GetFormattedText());
            result["used"] = used;
            if (full && !used)
            {
                var description = new LocString("merchant_room", "MERCHANT.cardRemovalService.description");
                description.Add("Amount", MerchantCardRemovalEntry.PriceIncrease);
                result["description"] = EnglishCardText.Plain(description.GetFormattedText());
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
