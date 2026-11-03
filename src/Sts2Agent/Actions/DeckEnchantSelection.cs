using Godot;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Cards;

namespace Sts2Agent;

internal static class DeckEnchantSelection
{
    public static Control? Preview(CardSelection selection) => selection.Kind == "deck_enchant"
        ? new[] { "%EnchantSinglePreviewContainer", "%EnchantMultiPreviewContainer" }
            .Select(path => selection.Owner.GetNodeOrNull<Control>(path)).FirstOrDefault(VisibleUi.Shown) : null;

    public static object? Description(CardSelection selection)
    {
        if (VisibleUi.Text(selection.Owner, "%EnchantmentTitle") == null
            || VisibleUi.Text(selection.Owner, "%EnchantmentDescription") == null) return null;
        return EnglishCardText.Read(() =>
        {
            var model = ((EnchantmentModel)PrivateFields.Read(selection.Owner, "_enchantment")!).ToMutable();
            model.Amount = (int)PrivateFields.Read(selection.Owner, "_enchantmentAmount")!;
            model.RecalculateValues();
            return (object)new { title = EnglishCardText.Plain(model.Title.GetFormattedText()),
                description = EnglishCardText.Plain(model.DynamicDescription.GetFormattedText()) };
        });
    }

    public static IEnumerable<(CardModel original, NCard? before, NCard after)> Previews(CardSelection selection)
    {
        var container = Preview(selection);
        if (container == null) yield break;
        if (container.GetNodeOrNull<NEnchantPreview>("EnchantPreview") is { } single)
        {
            var before = VisibleUi.Descendants<NCard>(single.GetNode<Control>("%Before")).FirstOrDefault(CombatObservation.CardVisible);
            var after = VisibleUi.Descendants<NCard>(single.GetNode<Control>("%After")).FirstOrDefault(CombatObservation.CardVisible);
            if (after != null && selection.Selected.FirstOrDefault() is { } original) yield return (original, before, after);
            yield break;
        }
        // The native multi-preview displays the selected originals, without simulated enchantments.
        var shown = VisibleUi.Descendants<NCard>(container.GetNode<Control>("Cards")).Where(CombatObservation.CardVisible).ToArray();
        foreach (var after in shown)
            if (selection.Selected.FirstOrDefault(c => ReferenceEquals(c, after.Model)) is { } original)
            {
                var holder = selection.Grid?.GetCardHolder(original);
                var before = holder != null && VisibleUi.OnScreen(holder) && CombatObservation.CardVisible(holder.CardNode) ? holder.CardNode : null;
                yield return (original, before, after);
            }
    }
}
