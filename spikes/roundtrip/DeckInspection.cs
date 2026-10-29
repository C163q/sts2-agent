using System.Globalization;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Screens;

namespace Sts2Agent;

internal sealed class DeckInspection
{
    private readonly CardIdentityMap<CardModel> ids = new();
    private object? run;

    public object Read(NDeckViewScreen screen, Player player, string detailLevel, string snapshotId)
    {
        if (!ReferenceEquals(run, player.RunState))
        {
            run = player.RunState;
            ids.Clear();
        }
        bool upgrades = DeckView.Grid(screen).IsShowingUpgrades;
        return EnglishCardText.Read(() => new
        {
            snapshot_id = snapshotId, scene = "deck", detail_level = detailLevel,
            view_upgrades = upgrades, sort = DeckView.Sorting(screen),
            deck = DeckView.Cards(screen).Select(card => Card(card, upgrades, detailLevel == "full")).ToArray()
        });
    }

    private Dictionary<string, object?> Card(CardModel original, bool upgrades, bool full)
    {
        // Native grid previews also upgrade a clone; never upgrade or recalculate the owned card.
        var model = (CardModel)original.MutableClone();
        bool preview = upgrades && model.IsUpgradable;
        if (preview) model.UpgradeInternal();
        model.DynamicVars.ClearPreview();
        model.UpdateDynamicVarPreview(preview ? CardPreviewMode.Upgrade : CardPreviewMode.Normal, null, model.DynamicVars);
        if (model.Enchantment != null)
        {
            model.Enchantment.DynamicVars.ClearPreview();
            model.UpdateDynamicVarPreview(preview ? CardPreviewMode.Upgrade : CardPreviewMode.Normal, null, model.Enchantment.DynamicVars);
        }
        int energy = model.EnergyCost.GetWithModifiers(CostModifiers.All);
        int stars = model.GetStarCostWithModifiers();
        var result = new Dictionary<string, object?>
        {
            ["id"] = "deck:" + ids.Get(original), ["name"] = EnglishCardText.Plain(model.Title),
            ["type"] = EnglishCardText.Plain(model.Type.ToLocString().GetFormattedText()),
            ["rarity"] = model.Rarity.ToString().ToLowerInvariant(), ["visual_card_pool"] = model.VisualCardPool.Title,
            ["energy_cost"] = model.EnergyCost.CostsX ? "X" : energy < 0 ? null : energy.ToString(CultureInfo.InvariantCulture),
            ["star_cost"] = model.HasStarCostX ? "X" : stars < 0 ? null : stars.ToString(CultureInfo.InvariantCulture)
        };
        if (full)
        {
            result["description"] = EnglishCardText.Plain(preview
                ? model.GetDescriptionForUpgradePreview() : model.GetDescriptionForPile(PileType.Deck));
            result["hover_tips"] = IHoverTip.RemoveDupes(model.HoverTips).Select(HoverTipText.From).ToArray();
        }
        return result;
    }
}
