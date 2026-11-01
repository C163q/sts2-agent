using System.Text.Json;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class HandInspectionChecks
{
    public static void Run(string reportPath)
    {
        var results = new List<object>();
        void Check(string name, bool passed)
        {
            results.Add(new { name, passed });
            if (!passed)
                throw new InvalidOperationException("Hand inspection check failed: " + name);
        }
        var keyword = new LocString("card_keywords", "ETHEREAL.title");
        string language = LocManager.Instance.Language;
        string titleBefore = keyword.GetFormattedText();
        IHoverTip cachedBefore = HoverTipFactory.FromKeyword(CardKeyword.Ethereal);
        var bane = ModelDb.Card<AscendersBane>();
        string body = EnglishCardText.Read(() => EnglishCardText.Plain(bane.GetDescriptionForPile(PileType.None)));
        var tips = EnglishCardText.Read(() => IHoverTip.RemoveDupes(bane.HoverTips).Cast<HoverTip>().ToArray());
        Check("keyword_only_card_description", body == "Unplayable.\nEthereal.\nEternal.");
        Check("ethereal_includes_exhaust_tip", tips.Length == 4
            && tips.Any(tip => tip.Title == "Ethereal") && tips.Any(tip => tip.Title == "Exhaust"));
        Check("keyword_tip_is_english", tips.Single(tip => tip.Title == "Exhaust").Description == "Removed until the end of combat.");
        Check("locale_unchanged", LocManager.Instance.Language == language && keyword.GetFormattedText() == titleBefore);
        Check("keyword_cache_unchanged", HoverTipFactory.FromKeyword(CardKeyword.Ethereal).Equals(cachedBefore));
        try { EnglishCardText.Read<string>(() => throw new InvalidOperationException("Expected scope check.")); }
        catch (InvalidOperationException) { }
        Check("exception_restores_locale_scope", keyword.GetFormattedText() == titleBefore);
        Check("resource_icons_retained", EnglishCardText.Plain("Gain [img]res://images/packed/sprite_fonts/ironclad_energy_icon.png[/img].")
            == "Gain <Energy>.");
        var attack = NCombatRoom.Instance!.Ui.Hand.ActiveHolders.Select(holder => holder.CardNode!.Model!)
            .First(card => card.DynamicVars.Values.OfType<DamageVar>().Any());
        DamageVar damage = attack.DynamicVars.Values.OfType<DamageVar>().First();
        decimal original = damage.PreviewValue;
        try
        {
            damage.PreviewValue = 4;
            Check("description_uses_current_preview", EnglishCardText.Read(() => EnglishCardText.Plain(
                attack.GetDescriptionForPile(PileType.Hand))).StartsWith("Deal 4 damage.", StringComparison.Ordinal));
        }
        finally { damage.PreviewValue = original; }
        File.WriteAllText(reportPath, JsonSerializer.Serialize(new { language, results }, new JsonSerializerOptions { WriteIndented = true }));
    }
}
