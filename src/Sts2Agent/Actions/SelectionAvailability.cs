using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;

namespace Sts2Agent;

internal static class SelectionAvailability
{
    private static string? ContextUnavailableReason(CardSelection? selection, string action)
    {
        if (selection == null) return "No card selection is open.";
        if (!RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
            return "Card selection is supported only in single-player.";
        if (!selection.Supported) return "This card selection is not supported; use manual input.";
        if (selection.Status == "battlefield")
            return $"The selection is hidden while viewing the battlefield. Return with set_selection_view(view=\"selection\") before {action}.";
        if (selection.Status != "visible")
            return $"The card selection is covered or hidden. Close the covering screen or wait for the transition before {action}.";
        return null;
    }

    public static string? UnavailableReason(CardSelection? candidate, int cardId, CombatObservation observation)
    {
        if (ContextUnavailableReason(candidate, "selecting a card") is { } reason) return reason;
        var selection = candidate!;
        if (selection.Kind == "bundle")
            return "Choose a whole card bundle with an enabled selection_option; individual cards cannot be selected here.";
        if (selection.Kind == "view_cards")
            return "These cards are results for viewing. Use the enabled confirmation option to close the page.";
        if (selection.InPreview)
            return "A confirmation preview is open. Use its enabled confirm or cancel_preview selection_option instead of selecting another card.";
        if (!selection.Cards.Any(card => observation.CardId(card) == cardId))
            return $"Card ID {cardId} is not a candidate in the current selection.";
        if (!selection.CanSelect)
            return "The card selection is not ready for clicks. Wait for the opening animation or transition before continuing.";
        return null;
    }

    public static string? OptionUnavailableReason(CardSelection? selection, string optionId, out NButton? button)
    {
        button = null;
        if (ContextUnavailableReason(selection, "clicking a selection option") is { } reason) return reason;
        button = selection!.Options().FirstOrDefault(option => option.id == optionId).button;
        if (button == null)
            return $"Selection option '{optionId}' is not offered on the current page. Use an enabled ID from selection.options.";
        if (!button.IsEnabled)
            return $"Selection option '{optionId}' is disabled. Follow the current selection prompt before continuing.";
        return null;
    }
}
