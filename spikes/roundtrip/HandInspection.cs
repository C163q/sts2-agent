using System.Reflection;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Cards;

namespace Sts2Agent;

internal sealed class HandInspection(CombatObservation observation)
{
    private sealed record TipText(string? title, string description);
    private static readonly FieldInfo PreviewTarget = typeof(NCard).GetField("_previewTarget", BindingFlags.Instance | BindingFlags.NonPublic)!;
    public Dictionary<string, object?> Card(NCard card)
    {
        var result = observation.Card(card);
        bool identified = card.Visibility == ModelVisibility.Visible;
        result["description"] = identified ? EnglishCardText.Read(() => Description(card.Model!, PileType.Hand,
            PreviewTarget.GetValue(card) as Creature ?? card.Model!.CurrentTarget)) : null;
        result["hover_tips"] = identified ? EnglishCardText.Read(() => IHoverTip.RemoveDupes(card.Model!.HoverTips)
            .Select(Tip).ToArray()) : null;
        return result;
    }

    private static string Description(CardModel card, PileType pile, Creature? target = null)
    {
        var prefixes = card.DynamicVars.Values.OfType<EnergyVar>().Select(value => (value, value.ColorPrefix)).ToArray();
        try { return EnglishCardText.Plain(card.GetDescriptionForPile(pile, target)); }
        finally
        {
            foreach (var (value, prefix) in prefixes)
                value.ColorPrefix = prefix;
        }
    }

    private static object Tip(IHoverTip tip) => tip switch
    {
        HoverTip text => new TipText(text.Title == null ? null : EnglishCardText.Plain(text.Title),
            EnglishCardText.Plain(text.Description)),
        CardHoverTip preview => new TipText(EnglishCardText.Plain(preview.Card.Title),
            Description(preview.Card, PileType.None)),
        _ => throw new InvalidOperationException("Unsupported card hover tip.")
    };
}
