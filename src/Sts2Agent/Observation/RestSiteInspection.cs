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

    public static NRestSiteButton[] Buttons(NRestSiteRoom room) => room.GetNode<Control>("%ChoicesContainer")
        .GetChildren().OfType<NRestSiteButton>().Where(b => !b.IsQueuedForDeletion() && b.IsNodeReady()).ToArray();

    public static bool Supported(NRestSiteButton button) => button.Option.OptionId is
        "HEAL" or "SMITH" or "DIG" or "LIFT" or "KINDLE" or "COOK" or "CLONE" or "HATCH";

    public static bool Clickable(NRestSiteButton button) => Supported(button) && button.IsEnabled && button.Option.IsEnabled
        && CardSelection.Field(button, "_isUnclickable") is false && VisibleUi.OnScreen(button)
        && button.Modulate.A >= 0.99f;

    public static bool Ready(NRestSiteRoom room)
    {
        if (!Exposed(room) || !RunManager.Instance.ActionQueueSet.IsEmpty
            || RewardInspection.Animating(room, "_choicesTween")
            || RewardInspection.Animating(room, "_descriptionTween")) return false;
        var buttons = Buttons(room);
        if (buttons.Any(b => CardSelection.Field(b, "_executingOption") is true)) return false;
        if (room.Options.Count == 0) return Proceed(room)?.IsEnabled == true;
        return buttons.Length == room.Options.Count && buttons.All(b => room.Options.Contains(b.Option)
            && b.IsEnabled && VisibleUi.OnScreen(b) && b.Modulate.A >= 0.99f);
    }

    public static NProceedButton? Proceed(NRestSiteRoom room) => VisibleUi.OnScreen(room.ProceedButton)
        && VisibleUi.Text(room.ProceedButton, "%Label") is { Length: > 0 } ? room.ProceedButton : null;

    public static object? Read(bool full = false)
    {
        if (Current is not { } room) return null;
        if (!Exposed(room)) return new { status = "covered", prompt = (string?)null, description = (string?)null,
            options = (object?)null, proceed = (object?)null };
        bool ready = Ready(room);
        var visible = Buttons(room).Where(b => VisibleUi.OnScreen(b.GetNode<Control>("%Label"))).ToArray();
        string? shown = VisibleUi.Text(room, "%Description");
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
            if (full) option["description"] = EnglishCardText.Read(() => EnglishCardText.Plain(b.Option.Description.GetFormattedText()));
            return option;
        }).ToArray();
        var button = Proceed(room);
        object? proceed = button == null ? null : new { text = EnglishCardText.Read(() =>
            EnglishCardText.Plain(NProceedButton.ProceedLoc.GetFormattedText())), enabled = ready && button.IsEnabled };
        return new { status = "visible", prompt = VisibleUi.Text(room, "%Header") == null ? null :
            EnglishCardText.Read(() => EnglishCardText.Plain(new LocString("rest_site_ui", "PROMPT").GetFormattedText())),
            description, options, proceed };
    }
}
