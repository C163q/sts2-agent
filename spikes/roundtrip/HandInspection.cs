using System.Reflection;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Nodes.Cards;

namespace Sts2Agent;

internal sealed class HandInspection(CombatObservation observation)
{
    private static readonly FieldInfo PreviewTarget = typeof(NCard).GetField("_previewTarget", BindingFlags.Instance | BindingFlags.NonPublic)!;
    public Dictionary<string, object?> Card(NCard card)
    {
        var result = observation.Card(card);
        bool identified = card.Visibility == ModelVisibility.Visible;
        result["description"] = identified ? EnglishCardText.Read(() => HoverTipText.DescribeCard(card.Model!, PileType.Hand,
            PreviewTarget.GetValue(card) as Creature ?? card.Model!.CurrentTarget)) : null;
        result["hover_tips"] = identified ? EnglishCardText.Read(() => IHoverTip.RemoveDupes(card.Model!.HoverTips)
            .Select(HoverTipText.From).ToArray()) : null;
        return result;
    }

}
