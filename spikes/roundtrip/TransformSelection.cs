using Godot;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Cards;

namespace Sts2Agent;

internal static class TransformSelection
{
    public static Control? Preview(CardSelection selection) => selection.Kind == "deck_transform"
        && selection.Owner.GetNodeOrNull<Control>("%PreviewContainer") is { } container && VisibleUi.Shown(container) ? container : null;

    public static IEnumerable<(CardModel original, NCard before, NCard? after)> Previews(CardSelection selection)
    {
        var preview = Preview(selection)?.GetNode<NTransformPreview>("TransformPreview");
        if (preview == null) yield break;
        var before = VisibleUi.Descendants<NCard>(preview.GetNode<Control>("%Before")).Where(CombatObservation.CardVisible).ToArray();
        var after = VisibleUi.Descendants<NCard>(preview.GetNode<Control>("%After")).Where(CombatObservation.CardVisible).ToArray();
        for (int i = 0; i < before.Length && i < after.Length; i++)
        {
            if (before[i].Model is not { } original) continue;
            // Disabled preview hitboxes identify cycling illustrations, not resolved replacements.
            var holder = after[i].GetParent() as MegaCrit.Sts2.Core.Nodes.Cards.Holders.NPreviewCardHolder;
            yield return (original, before[i], holder?.Hitbox.MouseFilter == Control.MouseFilterEnum.Ignore ? null : after[i]);
        }
    }
}
