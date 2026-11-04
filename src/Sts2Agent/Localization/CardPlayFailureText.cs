using HarmonyLib;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;

namespace Sts2Agent;

internal static class CardPlayFailureText
{
    private static readonly Func<UnplayableReason, AbstractModel?, LocString?> NativeLine =
        AccessTools.Method(typeof(CardModel).Assembly.GetType("MegaCrit.Sts2.Core.Entities.Cards.UnplayableReasonExtensions"),
            "GetPlayerDialogueLine").CreateDelegate<Func<UnplayableReason, AbstractModel?, LocString?>>();

    public static string Read(UnplayableReason reason, AbstractModel? preventer)
    {
        // Use the same public thought bubble as native mouse/controller rejection.
        try
        {
            string? text = EnglishCardText.Read(() => NativeLine(reason, preventer)?.GetFormattedText());
            if (!string.IsNullOrWhiteSpace(text)) return EnglishCardText.Plain(text);
        }
        catch (Exception) { }
        return "This card cannot be played now.";
    }
}
