using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Nodes.CommonUi;

namespace Sts2Agent;

internal static class SelectionText
{
    public static string? Prompt(CardSelection selection)
    {
        if (selection.Kind == "bundle")
        {
            var banner = selection.Owner.GetNodeOrNull<NCommonBanner>("Banner");
            if (banner == null || string.IsNullOrWhiteSpace(VisibleUi.Text(selection.Owner,
                    banner.label.GetPath().ToString()))) return null;
            return Format(new LocString("gameplay_ui", "CHOOSE_A_PACK"));
        }
        if (selection.Kind == "view_cards")
        {
            if (string.IsNullOrWhiteSpace(VisibleUi.Text(selection.Owner, "%BottomLabel"))) return null;
            // The native result screen formats this LocString into its visible bottom label.
            return PrivateFields.Read(selection.Owner, "_infoText") is LocString text ? Format(text) : null;
        }
        return selection.Kind is "choose_one" or "reward"
            ? Format(new LocString("gameplay_ui", "CHOOSE_CARD_HEADER"))
            : selection.Prefs.Prompt is { } prompt ? Format(prompt) : null;
    }

    private static string Format(LocString text) =>
        EnglishCardText.Read(() => EnglishCardText.Plain(text.GetFormattedText()));
}
