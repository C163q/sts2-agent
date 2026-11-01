using Godot;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Cards;

namespace Sts2Agent;

internal static class DeckUpgradeSelection
{
    public static Control? Preview(CardSelection selection) => selection.Kind == "deck_upgrade"
        ? new[] { "%UpgradeSinglePreviewContainer", "%UpgradeMultiPreviewContainer" }
            .Select(path => selection.Owner.GetNodeOrNull<Control>(path)).FirstOrDefault(VisibleUi.Shown) : null;

    public static IEnumerable<(CardModel original, NCard? before, NCard after)> Previews(CardSelection selection)
    {
        var container = Preview(selection);
        if (container == null) yield break;
        if (container.GetNodeOrNull<NUpgradePreview>("UpgradePreview") is { Card: not null } single)
        {
            var before = VisibleUi.Descendants<NCard>(single.GetNode<Control>("%Before")).FirstOrDefault(CombatObservation.CardVisible);
            var after = VisibleUi.Descendants<NCard>(single.GetNode<Control>("%After")).FirstOrDefault(CombatObservation.CardVisible);
            if (after != null) yield return (single.Card, before, after);
            yield break;
        }
        var upgraded = VisibleUi.Descendants<NCard>(container.GetNode<Control>("Cards"))
            .Where(CombatObservation.CardVisible).ToArray();
        var originals = selection.Selected;
        for (int i = 0; i < originals.Length && i < upgraded.Length; i++)
        {
            var holder = selection.Grid?.GetCardHolder(originals[i]);
            var before = holder != null && VisibleUi.OnScreen(holder) && CombatObservation.CardVisible(holder.CardNode) ? holder.CardNode : null;
            yield return (originals[i], before, upgraded[i]);
        }
    }
}
