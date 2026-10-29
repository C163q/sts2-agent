using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;

namespace Sts2Agent;

internal sealed record HoverTipText(string? title, string description)
{
    public static HoverTipText From(IHoverTip tip) => tip switch
    {
        HoverTip text => new(text.Title == null ? null : EnglishCardText.Plain(text.Title),
            EnglishCardText.Plain(text.Description)),
        CardHoverTip preview => new(EnglishCardText.Plain(preview.Card.Title), DescribeCard(preview.Card, PileType.None)),
        _ => throw new InvalidOperationException("Unsupported hover tip.")
    };

    public static string DescribeCard(CardModel card, PileType pile, Creature? target = null)
    {
        var prefixes = card.DynamicVars.Values.OfType<EnergyVar>().Select(value => (value, value.ColorPrefix)).ToArray();
        try { return EnglishCardText.Plain(card.GetDescriptionForPile(pile, target)); }
        finally
        {
            foreach (var (value, prefix) in prefixes)
                value.ColorPrefix = prefix;
        }
    }

    public static T WithPotionValues<T>(PotionModel potion, Func<T> read)
    {
        var prefixes = potion.DynamicVars.Values.OfType<EnergyVar>().Select(value => (value, value.ColorPrefix)).ToArray();
        try { return read(); }
        finally
        {
            foreach (var (value, prefix) in prefixes)
                value.ColorPrefix = prefix;
        }
    }
}
