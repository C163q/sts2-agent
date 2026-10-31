using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Models.Powers;

namespace Sts2Agent;

internal static class EventTextChecks
{
    public static object Run(bool stress = false)
    {
        LocString Wrapper(object value)
        {
            var text = new LocString("events", "TEA_MASTER.pages.INITIAL.options.TEA_OF_DISCOURTESY.description");
            text.AddObj("TeaOfDiscourtesyDescription", value);
            return text;
        }
        var card = new StringVar("TeaOfDiscourtesyDescription", new LocString("cards", "LANTERN_KEY.title").GetFormattedText());
        var original = Wrapper(card);
        var literal = new LocString("cards", "LANTERN_KEY.title").GetFormattedText();
        var literalWrapper = Wrapper(literal);
        var other = Wrapper(new StringVar("TeaOfDiscourtesyDescription", new LocString("events", "THE_LANTERN_KEY.title").GetFormattedText()));
        var cloned = Wrapper(card.Clone());
        string before = original.GetFormattedText();
        var strike = ModelDb.Card<StrikeIronclad>().ToMutable();
        strike.UpgradeInternal(); strike.FinalizeUpgradeInternal();
        var upgraded = Wrapper(new StringVar("TeaOfDiscourtesyDescription", strike.Title));
        var results = EnglishEventText.Read(() => new[] { original, other, cloned, literalWrapper, upgraded }
            .Select(t => t.GetFormattedText()).ToArray());
        if (!results.SequenceEqual(new[] { "Lantern Key", "The Lantern Key", "Lantern Key", "Lantern Key", "Strike+" }))
            throw new InvalidOperationException("Localized event provenance mismatch: " + string.Join(" | ", results));
        if (original.GetFormattedText() != before || card.StringValue != before)
            throw new InvalidOperationException("Event translation mutated a native localized variable.");
        if (stress)
        {
            var power = ModelDb.Power<StrengthPower>();
            var firstTip = new HoverTip(power, new LocString("cards", "LANTERN_KEY.title").GetFormattedText(), false);
            var secondTip = new HoverTip(power, new LocString("events", "THE_LANTERN_KEY.title").GetFormattedText(), false);
            var tipTexts = EnglishEventText.Read(() => new[] { EnglishEventText.Tip(firstTip).description, EnglishEventText.Tip(secondTip).description });
            if (!tipTexts.SequenceEqual(new[] { "Lantern Key", "The Lantern Key" }))
                throw new InvalidOperationException("Identical native hover text confused distinct sources: " + string.Join(" | ", tipTexts));
            var cached = HoverTipFactory.FromKeyword(CardKeyword.Ethereal);
            for (int index = 0; index < 4200; index++)
                _ = new HoverTip(new LocString("cards", "LANTERN_KEY.title"), index.ToString());
            var recovered = EnglishEventText.Read(() => EnglishEventText.Tip(cached));
            if (recovered.title != "Ethereal" || recovered.description != "If this card is in your Hand at the end of this turn, it is Exhausted.")
                throw new InvalidOperationException("A retained native hover tip lost its English source: " + recovered.title);
        }
        return new { collision = results[..2], cloned = results[2], literal = results[3], upgraded = results[4], unchanged = true, stress };
    }
}
