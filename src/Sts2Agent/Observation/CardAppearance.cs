using Godot;
using MegaCrit.Sts2.Core.Entities.Enchantments;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Cards;

namespace Sts2Agent;

internal static class CardAppearance
{
    private static Dictionary<string, object?> Enchantment(EnchantmentModel model, int? amount, bool dimmed)
    {
        var result = new Dictionary<string, object?>
        {
            ["name"] = EnglishCardText.Read(() => EnglishCardText.Plain(model.Title.GetFormattedText())),
            ["dimmed"] = dimmed
        };
        if (amount.HasValue) result["amount"] = amount.Value;
        return result;
    }

    private static object Affliction(AfflictionModel model) => new
    {
        name = EnglishCardText.Read(() => EnglishCardText.Plain(model.Title.GetFormattedText()))
    };

    public static void Read(NCard card, Dictionary<string, object?> result)
    {
        result["enchantment"] = null;
        result["affliction"] = null;
        if (card.Visibility != ModelVisibility.Visible) return;
        var icon = card.GetNodeOrNull<TextureRect>("%Enchantment/Icon");
        if (VisibleUi.OnScreen(card.EnchantmentTab) && VisibleUi.OnScreen(icon) && icon!.Texture != null
            && card.Model!.Enchantment is { } enchantment && icon.Texture == enchantment.Icon)
            result["enchantment"] = Enchantment(enchantment, VisibleUi.Number(card, "%Enchantment/Label"), icon.UseParentMaterial);
        // The model alone is insufficient: an overlay can be hidden, stale or replaced by a built-in effect.
        if (card.Model!.Affliction is { HasOverlay: true } affliction
            && PrivateFields.Read(card, "_cardOverlay") is Control overlay
            && overlay.SceneFilePath == affliction.OverlayPath && VisibleUi.Shown(overlay)
            && VisibleUi.Descendants<TextureRect>(overlay).Any(texture => texture.Texture != null && VisibleUi.OnScreen(texture)))
            result["affliction"] = Affliction(affliction);
    }

    public static void Preview(CardModel model, Dictionary<string, object?> result)
    {
        // A browsable grid formats a detached clone as the native NCard would render it.
        result["enchantment"] = model.Enchantment is { Icon: not null } enchantment
            ? Enchantment(enchantment, enchantment.ShowAmount ? enchantment.DisplayAmount : null,
                enchantment.Status == EnchantmentStatus.Disabled) : null;
        result["affliction"] = model.Affliction is { HasOverlay: true } affliction ? Affliction(affliction) : null;
    }
}
