using Godot;
using MegaCrit.Sts2.Core.Entities.Merchant;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Screens.Shops;

namespace Sts2Agent;

internal static class ShopDisplayFixture
{
    private static ShopInspection.Context? context;
    private static NMerchantSlot? slot;
    private static CanvasItem? visual;
    private static Control? parent, price, gold;
    private static Vector2 position, pricePosition, visualPosition;
    private static Color modulate;
    private static bool visible, visualVisible, clipped, parentClipped, priceVisible, goldVisible, barVisible, hitboxEnabled, inputBlocked;
    private static Control.FocusModeEnum focus;
    private static Control.FocusBehaviorRecursiveEnum focusBehavior;
    private static Control.MouseFilterEnum mouse;

    private static Vector2 Position(CanvasItem item) => item is Control control ? control.Position : ((Node2D)item).Position;
    private static void Move(CanvasItem item, Vector2 value)
    {
        if (item is Control control) control.Position = value;
        else ((Node2D)item).Position = value;
    }

    public static void Reset()
    {
        if (slot != null && GodotObject.IsInstanceValid(slot))
        {
            if (hitboxEnabled) slot.Hitbox.Enable(); else slot.Hitbox.Disable();
            slot.Position = position; slot.Modulate = modulate; slot.Visible = visible;
            slot.ClipContents = clipped; slot.FocusMode = focus; slot.FocusBehaviorRecursive = focusBehavior; slot.Hitbox.MouseFilter = mouse;
        }
        if (visual != null && GodotObject.IsInstanceValid(visual)) { Move(visual, visualPosition); visual.Visible = visualVisible; }
        if (price != null && GodotObject.IsInstanceValid(price)) { price.Position = pricePosition; price.Visible = priceVisible; }
        if (parent != null && GodotObject.IsInstanceValid(parent)) parent.ClipContents = parentClipped;
        if (gold != null && GodotObject.IsInstanceValid(gold)) gold.Visible = goldVisible;
        if (context != null && GodotObject.IsInstanceValid(context.Inventory))
        {
            if (inputBlocked) context.Inventory.BlockInput(); else context.Inventory.UnblockInput();
            if (NRun.Instance is { } run) run.GlobalUi.TopBar.Visible = barVisible;
        }
        slot = null; visual = null; price = null; parent = null; gold = null; context = null;
    }

    public static object Set(string mode, string kind)
    {
        Reset();
        if (mode == "normal") return new { mode, kind };
        context = ShopInspection.Current;
        if (context == null || !context.Inventory.IsOpen || !ShopInspection.Ready(context))
            throw new InvalidOperationException("An open ready test shop is required.");
        slot = context.Inventory.GetAllSlots().First(candidate => candidate.Entry.IsStocked && (kind switch
        {
            "card" => candidate.Entry is MerchantCardEntry, "relic" => candidate.Entry is MerchantRelicEntry,
            "potion" => candidate.Entry is MerchantPotionEntry, "card_removal" => candidate.Entry is MerchantCardRemovalEntry,
            _ => throw new ArgumentException("Unknown shop display kind.")
        }));
        visual = ShopInspection.Visual(slot); parent = slot.GetParent<Control>();
        price = slot.GetNode<Control>("%CostLabel");
        gold = NRun.Instance!.GlobalUi.TopBar.Gold.GetNode<Control>("%GoldLabel");
        position = slot.Position; modulate = slot.Modulate; visible = slot.Visible; clipped = slot.ClipContents;
        focus = slot.FocusMode; focusBehavior = slot.FocusBehaviorRecursive; mouse = slot.Hitbox.MouseFilter; hitboxEnabled = slot.Hitbox.IsEnabled;
        parentClipped = parent.ClipContents; pricePosition = price.Position; priceVisible = price.Visible;
        visualPosition = Position(visual); visualVisible = visual.Visible; goldVisible = gold.Visible;
        barVisible = NRun.Instance.GlobalUi.TopBar.Visible;
        inputBlocked = PrivateFields.Read(context.Inventory, "_isInputBlocked") is true;
        switch (mode)
        {
            case "offscreen": parent.ClipContents = false; slot.Position = new(-10000, -10000); break;
            case "price_offscreen": parent.ClipContents = false; slot.ClipContents = false; price.Position = new(-10000, -10000); break;
            case "hidden": slot.Hide(); break;
            case "transparent": slot.Modulate = new Color(modulate, 0); break;
            case "visual_hidden": visual.Hide(); break;
            case "clipped": slot.ClipContents = true; Move(visual, new(10000, 10000)); break;
            case "controller_only": slot.FocusMode = Control.FocusModeEnum.All; slot.FocusBehaviorRecursive = Control.FocusBehaviorRecursiveEnum.Enabled;
                slot.Hitbox.MouseFilter = Control.MouseFilterEnum.Ignore; break;
            case "mouse_only": slot.FocusMode = Control.FocusModeEnum.None; slot.Hitbox.MouseFilter = Control.MouseFilterEnum.Stop; break;
            case "click_disabled": slot.FocusMode = Control.FocusModeEnum.None; slot.Hitbox.Disable(); slot.Hitbox.MouseFilter = Control.MouseFilterEnum.Stop; break;
            case "no_hover": slot.FocusMode = Control.FocusModeEnum.None; slot.Hitbox.MouseFilter = Control.MouseFilterEnum.Ignore; break;
            case "blocked": context.Inventory.BlockInput(); break;
            case "gold_hidden": gold.Hide(); break;
            case "top_bar_hidden": NRun.Instance.GlobalUi.TopBar.Hide(); break;
            default: throw new ArgumentException("Unknown shop display mode.");
        }
        return new { mode, kind, effective_focus = slot.GetFocusModeWithOverride().ToString() };
    }
}
