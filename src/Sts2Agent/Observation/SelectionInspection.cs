using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Nodes.Cards;

namespace Sts2Agent;

internal sealed class SelectionInspection(CombatObservation observation)
{
    private static readonly System.Reflection.MethodInfo CardVisibility = HarmonyLib.AccessTools.Method(
        typeof(NCardGrid), "GetCardVisibility");

    public object? Read(CardSelection? selection, bool full = false)
    {
        if (selection == null) return null;
        string status = selection.Status;
        bool visible = status == "visible";
        var limits = visible ? selection.Limits : ((int minimum, int maximum)?)null;
        object? cards = null;
        if (visible)
        {
            if (selection.Grid != null && !selection.InPreview)
                cards = EnglishCardText.Read(() => selection.Cards.Select(model =>
                {
                    var node = selection.Grid.GetCardHolder(model)?.CardNode;
                    Dictionary<string, object?> card;
                    bool identified = CardVisibility.Invoke(selection.Grid, [model]) is ModelVisibility.Visible
                        && (node == null || node.Visibility == ModelVisibility.Visible);
                    if (!identified)
                    {
                        if (node is { Visibility: not ModelVisibility.Visible } && CombatObservation.CardVisible(node))
                            card = Card(node, full, expanded: true);
                        else
                        {
                            card = new() { ["name"] = null, ["description"] = null };
                            if (full) card["hover_tips"] = null;
                        }
                    }
                    else
                    {
                        // Every browsable card uses the same panel data, including partly clipped rows.
                        card = BrowsedCard.Read(model, "selection", selection.DisplayingPile,
                            selection.ViewUpgrades == true, true, preservePile: true, appearance: true);
                        if (!full) card.Remove("hover_tips");
                        if (CombatObservation.CardVisible(node))
                        {
                            var displayed = observation.Card(node!);
                            card["outline"] = displayed["outline"];
                            card["unplayable_markers"] = displayed["unplayable_markers"];
                        }
                    }
                    card["id"] = observation.CardId(model);
                    return card;
                }).ToArray());
            else
                cards = selection.Holders.Where(holder => CombatObservation.CardVisible(holder.CardNode))
                    .Select(holder =>
                    {
                        var card = Card(holder.CardNode!, full, selection.Kind is not ("hand" or "hand_upgrade"));
                        if (selection.ViewUpgrades == true && holder.IsShowingUpgradedCard
                            && holder.CardNode!.Visibility == ModelVisibility.Visible
                            && VisibleUi.Text(holder.CardNode!, "%DescriptionLabel") != null)
                            card["description"] = EnglishCardText.Read(() => EnglishCardText.Plain(
                                holder.CardNode!.Model!.GetDescriptionForUpgradePreview()));
                        return card;
                    }).ToArray();
        }
        var result = new Dictionary<string, object?>
        {
            ["type"] = selection.Kind, ["status"] = status, ["prompt"] = visible ? selection.Prompt : null,
            ["min_select"] = limits?.minimum, ["max_select"] = limits?.maximum,
            ["selected_ids"] = visible ? selection.Selected.Select(observation.CardId).ToArray() : null,
            ["cards"] = cards, ["options"] = selection.Options().Select(option => new
                { option.id, option.text, enabled = option.button.IsEnabled }).ToArray(),
            ["can_view_battlefield"] = selection.CanPeek,
            ["can_view_upgrades"] = selection.CanViewUpgrades, ["view_upgrades"] = selection.ViewUpgrades
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
        if (selection.Kind == "bundle")
            result["bundles"] = visible && !selection.InPreview
                ? selection.Owner.GetNode<Godot.Control>("%BundleRow").GetChildren().OfType<NCardBundle>().Select((bundle, i) =>
                    (object)new { id = "bundle:" + i, cards = bundle.CardNodes.Where(CombatObservation.CardVisible)
                        .Select(node => Card(node, full, expanded: false)).ToArray() }).ToArray() : Array.Empty<object>();
        if (selection.Kind == "deck_transform")
            result["transform_previews"] = !visible ? Array.Empty<object>() : TransformSelection.Previews(selection).Select(pair =>
            {
                var before = Card(pair.before, full, expanded: true);
                var after = pair.after == null ? null : Card(pair.after, full, expanded: true);
                before["id"] = observation.CardId(pair.original);
                if (after != null) after["id"] = observation.CardId(pair.original);
                return (object)new { before, after, random = pair.after == null };
            }).ToArray();
        if (selection.Kind == "deck_enchant")
        {
            result["enchantment"] = visible ? DeckEnchantSelection.Description(selection) : null;
            result["enchant_previews"] = !visible ? Array.Empty<object>() : DeckEnchantSelection.Previews(selection).Select(pair =>
            {
                var before = pair.before == null ? new Dictionary<string, object?> { ["name"] = null, ["description"] = null }
                    : Card(pair.before, full, expanded: true);
                var after = Card(pair.after, full, expanded: true);
                before["id"] = after["id"] = observation.CardId(pair.original);
                return (object)new { before, after };
            }).ToArray();
        }
        if (selection.Kind == "deck_upgrade")
            result["upgrade_previews"] = !visible ? Array.Empty<object>() : DeckUpgradeSelection.Previews(selection).Select(pair =>
            {
                var before = pair.before == null ? new Dictionary<string, object?> { ["name"] = null, ["description"] = null }
                    : Card(pair.before, full, expanded: true);
                var after = Card(pair.after, full, expanded: true);
                before["id"] = after["id"] = observation.CardId(pair.original);
                if (pair.after.Visibility == ModelVisibility.Visible && VisibleUi.Text(pair.after, "%DescriptionLabel") != null)
                    after["description"] = EnglishCardText.Read(() => EnglishCardText.Plain(pair.after.Model!.GetDescriptionForUpgradePreview()));
                return (object)new { before, after };
            }).ToArray();
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
