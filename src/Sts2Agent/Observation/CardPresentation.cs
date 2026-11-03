using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Nodes.Cards;

namespace Sts2Agent;

internal static class CardPresentation
{
    public static Dictionary<string, object?> Unknown() => new()
    {
        ["name"] = null, ["description"] = null, ["hover_tips"] = null,
        ["enchantment"] = null, ["affliction"] = null
    };

    public static Dictionary<string, object?> Read(NCard card, CombatObservation observation, bool full)
    {
        var result = observation.Card(card);
        if (!full) return result;
        bool identified = card.Visibility == ModelVisibility.Visible;
        result["description"] = identified ? EnglishCardText.Read(() => HoverTipText.DescribeCard(card.Model!, card.DisplayingPile,
            PrivateFields.Read(card, "_previewTarget") as Creature ?? card.Model!.CurrentTarget)) : null;
        result["hover_tips"] = identified ? EnglishCardText.Read(() => IHoverTip.RemoveDupes(card.Model!.HoverTips)
            .Select(HoverTipText.From).ToArray()) : null;
        return result;
    }
}
