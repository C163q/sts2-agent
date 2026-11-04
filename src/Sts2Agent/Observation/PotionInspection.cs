using System.Text.Json.Serialization;
using Godot;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Potions;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Potions;

namespace Sts2Agent;

internal static class PotionInspection
{
    private static readonly EnglishText Names = new();
    internal record StaticText(string? name)
    {
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public bool? usable_here { get; init; }
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public bool? bouncing { get; init; }
    }
    internal sealed record PotionText(string? name, string? description, HoverTipText[] hover_tips) : StaticText(name);
    internal sealed record Result(HoverTipText? slot_tip, PotionText?[] potion_slots, string[] unavailable_hover_sources);

    internal static NPotionHolder[]? ExposedHolders() => RunUi.TopBarReadable()
        ? ExposedHolders(NRun.Instance!.GlobalUi.TopBar.PotionContainer) : null;

    private static NPotionHolder[]? ExposedHolders(NPotionContainer container)
    {
        var layout = container.GetNodeOrNull<Control>("MarginContainer/PotionHolders");
        return VisibleUi.Displayed(container) && VisibleUi.Displayed(layout)
            ? layout!.GetChildren().OfType<NPotionHolder>().ToArray() : null;
    }

    public static NPotionHolder[]? VisibleHolders()
    {
        var holders = ExposedHolders();
        return holders != null && holders.All(Displayed) ? holders : null;
    }

    internal static NPotionHolder? ExposedAt(int slot)
    {
        var holders = ExposedHolders();
        return holders != null && slot >= 0 && slot < holders.Length && VisibleUi.Displayed(holders[slot])
            ? holders[slot] : null;
    }

    internal static NPotionHolder? DisplayedAt(int slot)
    {
        var holder = ExposedAt(slot);
        return holder != null && Displayed(holder) ? holder : null;
    }

    internal static bool Hoverable(NPotionHolder holder) => HoverAccess.CanFocus(holder);
    internal static bool Interactive(NPotionHolder holder) => Displayed(holder) && holder.IsEnabled && Hoverable(holder);

    private static TextureRect? Icon(NPotionHolder holder) => holder.HasPotion
        ? holder.Potion!.GetNodeOrNull<TextureRect>("%Image") : holder.GetNodeOrNull<TextureRect>("%EmptyIcon");

    internal static bool Displayed(NPotionHolder holder) => VisibleUi.Displayed(holder)
        && Icon(holder) is { } icon && VisibleUi.Displayed(icon) && icon.Texture != null
        && Mathf.Abs(icon.GetGlobalTransformWithCanvas().Determinant()) > 0.000001f;

    internal static NPotionHolder[]? DisplayedHolders(NPotionContainer container)
    {
        var holders = ExposedHolders(container);
        return holders != null && holders.All(Displayed) ? holders : null;
    }

    internal static string? UnavailableReason()
    {
        if (!RunUi.TopBarReadable()) return "The potion bar is not exposed in the current screen. Close the covering dialog or view first.";
        var container = NRun.Instance!.GlobalUi.TopBar.PotionContainer;
        if (!VisibleUi.Displayed(container) || !VisibleUi.Displayed(container.GetNodeOrNull<Control>("MarginContainer/PotionHolders")))
            return "The potion bar is hidden or not ready. Wait for the current screen to finish appearing.";
        return DisplayedHolders(container) == null
            ? "At least one potion slot or icon is hidden, clipped, or not ready. Its contents cannot be identified; no slot positions were changed." : null;
    }

    internal static StaticText? Static(NPotionHolder holder)
    {
        if (!holder.HasPotion) return null;
        var potion = holder.Potion!;
        return new StaticText(Names.Name(potion.Model.Title))
        {
            usable_here = potion.Model is FoulPotion && ShopInspection.Current is { } shop && ShopInspection.Exposed(shop)
                ? PotionActions.MerchantVisible(potion.Model) && PotionActions.Reason(potion.Model) == null : null,
            bouncing = RewardInspection.Animating(potion, "_bounceTween") ? true : null
        };
    }

    public static Result Read(NPotionHolder[] holders, bool full = true) => EnglishCardText.Read(() => new Result(
        full ? HoverTipText.From(new HoverTip(new LocString("static_hover_tips", "POTION_SLOT.title"),
            new LocString("static_hover_tips", "POTION_SLOT.description"))) : null,
        holders.Select(holder =>
        {
            var value = Static(holder);
            if (value == null) return null;
            var detail = full && Hoverable(holder) ? Details(holder.Potion!.Model) : new PotionText(value.name, null, []);
            return detail with { name = value.name, usable_here = value.usable_here, bouncing = value.bouncing };
        }).ToArray(),
        full ? holders.Select((holder, index) => (holder, index)).Where(item => item.holder.HasPotion && !Hoverable(item.holder))
            .Select(item => $"potion_slots.{item.index}").ToArray() : []));

    internal static PotionText Details(PotionModel potion) => EnglishCardText.Read(() =>
        HoverTipText.WithPotionValues(potion, () =>
        {
            var main = HoverTipText.From(potion.HoverTip);
            var extras = IHoverTip.RemoveDupes(potion.ExtraHoverTips).Select(HoverTipText.From)
                .Where(tip => tip != main).ToArray();
            return new PotionText(main.title, main.description, extras);
        }));
}
