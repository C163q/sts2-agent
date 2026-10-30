using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Nodes.Cards;

namespace Sts2Agent;

internal sealed class SelectionInspection(CombatObservation observation)
{
    public object? Read(CardSelection? selection, bool full = false)
    {
        if (selection == null) return null;
        string status = selection.Status;
        bool visible = status == "visible";
        var limits = visible ? selection.Limits : ((int minimum, int maximum)?)null;
        object? cards = null;
        if (visible)
        {
            if (full && selection.Grid != null && !selection.InPreview)
                cards = EnglishCardText.Read(() => selection.Cards.Select(model =>
                {
                    // Display context can differ from the owning pile; keep both for native previews.
                    var card = BrowsedCard.Read(model, "selection", selection.DisplayingPile, false, true, preservePile: true);
                    card["id"] = observation.CardId(model);
                    return card;
                }).ToArray());
            else
                cards = selection.Holders.Where(holder => CombatObservation.CardVisible(holder.CardNode))
                    .Select(holder => Card(holder.CardNode!, full, selection.Kind is not ("hand" or "hand_upgrade"))).ToArray();
        }
        var result = new Dictionary<string, object?>
        {
            ["type"] = selection.Kind, ["status"] = status, ["prompt"] = visible ? selection.Prompt : null,
            ["min_select"] = limits?.minimum, ["max_select"] = limits?.maximum,
            ["selected_ids"] = visible ? selection.Selected.Select(observation.CardId).ToArray() : null,
            ["cards"] = cards, ["options"] = selection.Options().Select(option => new
                { option.id, option.text, enabled = option.button.IsEnabled }).ToArray(),
            ["can_view_battlefield"] = selection.CanPeek
        };
        if (selection.Kind == "hand_upgrade")
        {
            object? preview = null;
            if (visible && selection.UpgradePreview?.Card is { } original
                && selection.UpgradeCard("%Before") is { } before && selection.UpgradeCard("%After") is { } after)
            {
                var beforeCard = Card(before, full, expanded: true);
                var afterCard = Card(after, full, expanded: true);
                // Both visible sides describe the selected hand card, not an actionable clone.
                beforeCard["id"] = afterCard["id"] = observation.CardId(original);
                if (after.Visibility == ModelVisibility.Visible && VisibleUi.Text(after, "%DescriptionLabel") != null)
                    afterCard["description"] = EnglishCardText.Read(() => EnglishCardText.Plain(after.Model!.GetDescriptionForUpgradePreview()));
                preview = new { before = beforeCard, after = afterCard };
            }
            result["upgrade_preview"] = preview;
        }
        return result;
    }

    private Dictionary<string, object?> Card(NCard node, bool full, bool expanded)
    {
        var card = observation.Card(node);
        bool identified = node.Visibility == ModelVisibility.Visible;
        if (full || expanded && VisibleUi.Text(node, "%DescriptionLabel") != null)
            card["description"] = identified ? EnglishCardText.Read(() => HoverTipText.DescribeCard(node.Model!, node.DisplayingPile,
                CardSelection.Field(node, "_previewTarget") as MegaCrit.Sts2.Core.Entities.Creatures.Creature ?? node.Model!.CurrentTarget)) : null;
        if (full)
            card["hover_tips"] = identified ? EnglishCardText.Read(() => IHoverTip.RemoveDupes(node.Model!.HoverTips).Select(HoverTipText.From).ToArray()) : null;
        return card;
    }
}
