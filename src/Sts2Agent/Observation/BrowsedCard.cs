using System.Globalization;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Enchantments;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Models;

namespace Sts2Agent;

internal static class BrowsedCard
{
    [ThreadStatic] private static CardModel? contextualClone;
    [ThreadStatic] private static CardPile? contextualPile;

    internal static bool PreviewPile(CardModel __instance, ref CardPile? __result)
    {
        if (!ReferenceEquals(__instance, contextualClone)) return true;
        __result = contextualPile;
        return false;
    }

    public static Dictionary<string, object?> Read(CardModel original, string id, PileType pile, bool upgrades, bool full,
        bool preservePile = false, bool appearance = false)
    {
        // Native grid previews also upgrade a clone; never recalculate or upgrade the owned card.
        var model = (CardModel)original.MutableClone();
        var previousClone = contextualClone;
        var previousPile = contextualPile;
        try
        {
            // Combat formatting and costs consult CardModel.Pile; the detached clone must retain that context.
            contextualClone = pile.IsCombatPile() || preservePile ? model : null;
            contextualPile = contextualClone == null ? null : original.Pile;
            return ReadClone(model, id, pile, upgrades, full, contextualClone != null ? original.CurrentTarget : null, appearance);
        }
        finally { contextualClone = previousClone; contextualPile = previousPile; }
    }

    private static Dictionary<string, object?> ReadClone(CardModel model, string id, PileType pile, bool upgrades, bool full,
        MegaCrit.Sts2.Core.Entities.Creatures.Creature? target, bool appearance)
    {
        bool preview = upgrades && model.IsUpgradable;
        if (preview) model.UpgradeInternal();
        model.DynamicVars.ClearPreview();
        model.UpdateDynamicVarPreview(preview ? CardPreviewMode.Upgrade : CardPreviewMode.Normal, target, model.DynamicVars);
        if (model.Enchantment != null)
        {
            model.Enchantment.DynamicVars.ClearPreview();
            model.UpdateDynamicVarPreview(preview ? CardPreviewMode.Upgrade : CardPreviewMode.Normal, target, model.Enchantment.DynamicVars);
        }
        int energy = model.EnergyCost.GetWithModifiers(CostModifiers.All);
        int stars = model.GetStarCostWithModifiers();
        var result = new Dictionary<string, object?>
        {
            ["id"] = id, ["name"] = EnglishCardText.Plain(model.Title),
            ["type"] = EnglishCardText.Plain(model.Type.ToLocString().GetFormattedText()),
            ["rarity"] = model.Rarity.ToString().ToLowerInvariant(), ["visual_card_pool"] = model.VisualCardPool.Title,
            ["energy_cost"] = model.EnergyCost.CostsX ? "X" : energy < 0 ? null : energy.ToString(CultureInfo.InvariantCulture),
            ["star_cost"] = model.HasStarCostX ? "X" : stars < 0 ? null : stars.ToString(CultureInfo.InvariantCulture)
        };
        if (appearance)
        {
            // Match NCard's normal grid rendering; these are display properties, not internal stacks.
            if (model.Enchantment is { } enchantment && enchantment.Icon != null)
            {
                var visible = new Dictionary<string, object?>
                {
                    ["name"] = EnglishCardText.Plain(enchantment.Title.GetFormattedText()),
                    ["dimmed"] = enchantment.Status == EnchantmentStatus.Disabled
                };
                if (enchantment.ShowAmount) visible["amount"] = enchantment.DisplayAmount;
                result["enchantment"] = visible;
            }
            if (energy >= 0 && !model.EnergyCost.CostsX && model.EnergyCost.WasJustUpgraded)
                result["energy_cost_color"] = "green";
            if (stars >= 0 && !model.HasStarCostX && model.WasStarCostJustUpgraded)
                result["star_cost_color"] = "green";
        }
        if (full)
        {
            result["description"] = EnglishCardText.Plain(preview
                ? model.GetDescriptionForUpgradePreview() : model.GetDescriptionForPile(pile, target));
            result["hover_tips"] = IHoverTip.RemoveDupes(model.HoverTips).Select(HoverTipText.From).ToArray();
        }
        return result;
    }
}
