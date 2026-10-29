using Godot;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Potions;

namespace Sts2Agent;

internal static class PotionInspection
{
    internal sealed record PotionText(string? name, string description, HoverTipText[] hover_tips);
    internal sealed record Result(HoverTipText slot_tip, PotionText?[] potion_slots);

    public static NPotionHolder[]? VisibleHolders()
    {
        if (CombatObservation.Status() != "visible")
            return null;
        var container = NRun.Instance!.GlobalUi.TopBar.PotionContainer;
        var layout = container.GetNodeOrNull<Control>("MarginContainer/PotionHolders");
        if (!VisibleUi.Shown(container) || !VisibleUi.Shown(layout))
            return null;
        var holders = layout!.GetChildren().OfType<NPotionHolder>().ToArray();
        if (holders.Any(holder => !VisibleUi.OnScreen(holder) || !holder.IsEnabled
            || (holder.HasPotion ? !VisibleUi.OnScreen(holder.Potion!.GetNodeOrNull<TextureRect>("%Image"))
                : !VisibleUi.OnScreen(holder.GetNodeOrNull<TextureRect>("%EmptyIcon")))))
            return null;
        return holders;
    }

    public static Result Read(NPotionHolder[] holders) => EnglishCardText.Read(() => new Result(
        HoverTipText.From(new HoverTip(new LocString("static_hover_tips", "POTION_SLOT.title"),
            new LocString("static_hover_tips", "POTION_SLOT.description"))),
        holders.Select(holder => holder.HasPotion ? Details(holder.Potion!.Model) : null).ToArray()));

    internal static PotionText Details(PotionModel potion) => EnglishCardText.Read(() =>
        HoverTipText.WithPotionValues(potion, () =>
        {
            var main = HoverTipText.From(potion.HoverTip);
            var extras = IHoverTip.RemoveDupes(potion.ExtraHoverTips).Select(HoverTipText.From)
                .Where(tip => tip != main).ToArray();
            return new PotionText(main.title, main.description, extras);
        }));
}
