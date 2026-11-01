using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Models.Enchantments;

namespace Sts2Agent;

internal static class EnglishRelicText
{
    [ThreadStatic] public static IReadOnlyDictionary<string, string>? Overrides;

    public static T Read<T>(RelicModel? relic, Func<T> read) => EnglishCardText.Read(() =>
    {
        var previous = Overrides;
        try
        {
            Overrides = null;
            Overrides = relic == null ? null : Variables(relic);
            return read();
        }
        finally { Overrides = previous; }
    });

    public static Dictionary<string, string> Variables(RelicModel relic)
    {
        var result = new Dictionary<string, string>();
        if (relic is TouchOfOrobas touch)
        {
            if (touch.StarterRelic != null) result["StarterRelic"] = ModelDb.GetById<RelicModel>(touch.StarterRelic).Title.GetFormattedText();
            if (touch.UpgradedRelic != null) result["UpgradedRelic"] = ModelDb.GetById<RelicModel>(touch.UpgradedRelic).Title.GetFormattedText();
        }
        if (relic is ArchaicTooth tooth)
        {
            if (tooth.StarterCard != null) result["StarterCard"] = CardModel.FromSerializable(tooth.StarterCard).Title;
            if (tooth.AncientCard != null) result["AncientCard"] = CardModel.FromSerializable(tooth.AncientCard).Title;
        }
        if (relic is PaelsTooth pael)
            result["CardTitles"] = string.Join('\n', pael.SerializableCards.Select(c => "- " + ModelDb.GetById<CardModel>(c.Id!).Title));
        if (relic is SeaGlass { CharacterId: not null } glass)
            result["Character"] = ModelDb.GetById<CharacterModel>(glass.CharacterId).Title.GetFormattedText();
        if (relic is DustyTome { AncientCard: not null } tome)
            result["AncientCard"] = ModelDb.GetById<CardModel>(tome.AncientCard).Title;
        if (relic is PaelsClaw) result["EnchantmentName"] = ModelDb.Enchantment<Goopy>().Title.GetFormattedText();
        if (relic is PaelsGrowth) result["EnchantmentName"] = ModelDb.Enchantment<Clone>().Title.GetFormattedText();
        return result;
    }

    public static IEnumerable<IHoverTip> ExtraTips(RelicModel relic)
    {
        // Rebuild only the already-disclosed references; their cached tips use the game's locale.
        if (relic is TouchOfOrobas touch)
            return new[] { touch.StarterRelic, touch.UpgradedRelic }.Where(id => id != null)
                .SelectMany(id => ModelDb.GetById<RelicModel>(id!).HoverTips);
        if (relic is ArchaicTooth tooth)
            return new[] { tooth.StarterCard, tooth.AncientCard }.Where(card => card != null).SelectMany(card =>
            {
                var model = CardModel.FromSerializable(card!);
                return model.HoverTips.Concat([HoverTipFactory.FromCard(model)]);
            });
        if (relic is DustyTome { AncientCard: not null } tome)
        {
            var model = ModelDb.GetById<CardModel>(tome.AncientCard);
            return model.HoverTips.Concat([HoverTipFactory.FromCard(model, upgrade: true)]);
        }
        return relic.HoverTipsExcludingRelic;
    }
}
