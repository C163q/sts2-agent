using Godot;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.RestSite;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class RestSiteInspection
{
    public static NRestSiteRoom? Current => RunManager.Instance.DebugOnlyGetState()?.CurrentRoom is RestSiteRoom
        && NRestSiteRoom.Instance is { } room && GodotObject.IsInstanceValid(room)
        && !room.IsQueuedForDeletion() && room.IsNodeReady() ? room : null;

    public static bool Exposed(NRestSiteRoom room) => ReferenceEquals(Current, room) && RunUi.NonCombatVisible()
        && NRun.Instance?.GlobalUi.Overlays.ScreenCount == 0 && !RunUi.CardPreviewsPending()
        && !VisibleUi.Shown(NRun.Instance?.GlobalUi.MapScreen) && VisibleUi.Shown(room);

    public static string? InspectionUnavailableReason(NRestSiteRoom? room)
    {
        if (room != null && GodotObject.IsInstanceValid(room) && Exposed(room)
            && RunManager.Instance.IsSingleplayerOrFakeMultiplayer) return null;
        if (!RunManager.Instance.IsInProgress) return "No local run is available for rest site inspection.";
        if (room == null || !GodotObject.IsInstanceValid(room)) return "No rest site is available on the current screen.";
        if (!RunManager.Instance.IsSingleplayerOrFakeMultiplayer) return "Rest site inspection requires a local single-player run.";
        var map = NRun.Instance?.GlobalUi.MapScreen;
        if (VisibleUi.Shown(map)) return map!.IsOpen
            ? "Close the map with close_map before inspecting rest options."
            : "Wait for the map to finish closing before inspecting rest options.";
        if (CardView.Current != null) return "Close the card browsing page with close_card_view before inspecting rest options.";
        if (CardSelection.Current != null) return "Resolve the current card selection before inspecting rest options; inspect_selection shows its choices.";
        if (RewardInspection.Current != null) return "Resolve the current reward page before inspecting rest options; inspect_rewards shows its rows.";
        if (RunUi.CardPreviewsPending()) return "Wait for card previews to finish before inspecting rest options.";
        if (RunUi.Transitioning()) return "Wait for the screen transition before inspecting rest options.";
        return "The rest site is covered by a dialog or another screen.";
    }

    public static NRestSiteButton[] Buttons(NRestSiteRoom room) => room.GetNode<Control>("%ChoicesContainer")
        .GetChildren().OfType<NRestSiteButton>().Where(b => !b.IsQueuedForDeletion() && b.IsNodeReady()).ToArray();

    public static bool Supported(NRestSiteButton button) => button.Option.OptionId is
        "HEAL" or "SMITH" or "DIG" or "LIFT" or "KINDLE" or "COOK" or "CLONE" or "HATCH";

    public static bool Clickable(NRestSiteButton button) => Supported(button) && button.IsEnabled && button.Option.IsEnabled
        && PrivateFields.Read(button, "_isUnclickable") is false && VisibleUi.OnScreen(button)
        && button.Modulate.A >= 0.99f && HoverAccess.CanFocus(button);

    public static bool Ready(NRestSiteRoom room)
    {
        if (!Exposed(room) || !RunManager.Instance.ActionQueueSet.IsEmpty
            || RewardInspection.Animating(room, "_choicesTween")
            || RewardInspection.Animating(room, "_descriptionTween")) return false;
        var buttons = Buttons(room);
        if (buttons.Any(b => PrivateFields.Read(b, "_executingOption") is true)) return false;
        if (room.Options.Count == 0) return Proceed(room)?.IsEnabled == true;
        return buttons.Length == room.Options.Count && buttons.All(b => room.Options.Contains(b.Option)
            && b.IsEnabled && b.Modulate.A >= 0.99f);
    }

    // The native Proceed button hides by sliding outside the viewport, without clearing Visible.
    public static NProceedButton? Proceed(NRestSiteRoom room) => VisibleUi.OnScreen(room.ProceedButton)
        && VisibleUi.Text(room.ProceedButton, "%Label") is { Length: > 0 } ? room.ProceedButton : null;

    public static object Inspect()
    {
        var restSite = Read(full: true, out var unavailable);
        return new { rest_site = restSite, unavailable_hover_sources = unavailable };
    }

    public static object? Read(bool full = false) => Read(full, out _);

    private static object? Read(bool full, out string[] unavailable)
    {
        unavailable = [];
        if (Current is not { } room) return null;
        if (!Exposed(room)) return new { status = "covered", prompt = (string?)null, description = (string?)null,
            options = (object?)null, proceed = (object?)null };
        bool ready = Ready(room);
        var visible = Buttons(room).Where(b => VisibleUi.Displayed(b)
            && VisibleUi.DisplayedText(b, "%Label") is { Length: > 0 }).ToArray();
        List<string> missing = [];
        string? shown = VisibleUi.DisplayedText(room, "%Description");
        string? description = shown == null ? null : Buttons(room).Select(b => b.Option.Description)
            .FirstOrDefault(loc => EnglishCardText.Plain(loc.GetFormattedText()) == shown) is { } loc
            ? EnglishCardText.Read(() => EnglishCardText.Plain(loc.GetFormattedText())) : null;
        var options = visible.Select(b =>
        {
            var option = new Dictionary<string, object?>
            {
                ["id"] = b.Option.OptionId, ["text"] = EnglishCardText.Read(() => EnglishCardText.Plain(b.Option.Title.GetFormattedText())),
                ["enabled"] = ready && Clickable(b)
            };
            if (full)
            {
                bool hoverable = HoverAccess.CanFocus(b);
                option["description"] = hoverable ? EnglishCardText.Read(() => EnglishCardText.Plain(b.Option.Description.GetFormattedText())) : null;
                if (!hoverable) missing.Add("rest_site.options." + b.Option.OptionId);
            }
            return option;
        }).ToArray();
        unavailable = missing.ToArray();
        var button = Proceed(room);
        object? proceed = button == null ? null : new { text = EnglishCardText.Read(() =>
            EnglishCardText.Plain(NProceedButton.ProceedLoc.GetFormattedText())), enabled = ready && button.IsEnabled };
        return new { status = "visible", prompt = VisibleUi.DisplayedText(room, "%Header") == null ? null :
            EnglishCardText.Read(() => EnglishCardText.Plain(new LocString("rest_site_ui", "PROMPT").GetFormattedText())),
            description, options, proceed };
    }
}
