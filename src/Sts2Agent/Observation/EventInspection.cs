using Godot;
using MegaCrit.Sts2.Core.Events;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Events;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Events;
using MegaCrit.Sts2.Core.Nodes.Events.Custom.CrystalSphere;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed class EventInspection
{
    internal sealed record Context(EventModel Model, NEventLayout Layout);
    private readonly Dictionary<EventOption, int> ids = [];
    private EventModel? model;
    private int nextId;
    public int Generation { get; private set; }

    public static Context? Current => RunUi.LocalEvent is { } current && current is not (AncientEventModel or TheArchitect)
        && current.GetType().Assembly == typeof(EventModel).Assembly
        && current.LayoutType is EventLayoutType.Default or EventLayoutType.Combat
        && NEventRoom.Instance?.Layout is { } layout && ReferenceEquals(current.Node, layout)
        && GodotObject.IsInstanceValid(layout) && layout.IsNodeReady() && !layout.IsQueuedForDeletion()
        ? new(current, layout) : null;

    public static string? ManualView => Current == null ? null
        : NModalContainer.Instance?.OpenModal is NAbandonRunConfirmPopup popup && VisibleUi.Shown(popup) ? "confirmation"
        : null;

    public static bool Exposed(Context context) => ReferenceEquals(Current?.Layout, context.Layout)
        && RunUi.NonCombatVisible() && NRun.Instance?.GlobalUi.Overlays.ScreenCount == 0
        && !VisibleUi.Shown(NRun.Instance?.GlobalUi.MapScreen) && VisibleUi.Shown(context.Layout);

    public static string? InspectionUnavailableReason(Context? context) => PageUnavailableReason(context, false);

    private static string? PageUnavailableReason(Context? context, bool choosing)
    {
        if (!RunManager.Instance.IsInProgress) return choosing
            ? "No local run is available for choosing an event option." : "No local run is available for event inspection.";
        if (context == null) return "No supported event is available on the current screen.";
        if (!RunContext.Singleplayer) return choosing
            ? "Choosing an event option requires a local single-player run." : "Event inspection requires a local single-player run.";
        if (Exposed(context)) return null;
        string purpose = choosing ? "choosing an event option" : "inspecting the event";
        if (VisibleUi.Shown(NRun.Instance?.GlobalUi.MapScreen)) return NRun.Instance!.GlobalUi.MapScreen.IsOpen
            ? $"Close the map with close_map before {purpose}." : $"Wait for the map to finish closing before {purpose}.";
        if (CardView.Current != null) return $"Close the card browsing page with close_card_view before {purpose}.";
        if (CardSelection.Current != null) return "Resolve the current card selection; inspect_selection shows its choices.";
        if (RewardInspection.Current != null) return "Resolve the current reward page; inspect_rewards shows its rows.";
        if (DivinationInspection.Current != null) return choosing
            ? "Use the current divination tools; inspect_event shows the board." : "Wait for the divination board to finish opening.";
        if (EventConfirmation.Current != null) return $"Resolve the confirmation with respond_to_confirmation before {purpose}.";
        return "The event is covered by a dialog or a screen transition.";
    }

    public static string? ActionUnavailableReason(Context? context) => PageUnavailableReason(context, true)
        ?? (context!.Model.IsFinished ? "This event is finished. Use proceed to continue."
            : !Ready(context) ? "Wait for the event text, options, and current effects to finish before choosing another option." : null);

    private static bool TextComplete(Context context) => context.Layout.GetNodeOrNull<RichTextLabel>("%EventDescription")
        is { VisibleRatio: >= 0.999f } description && VisibleUi.OnScreen(description)
        && !RewardInspection.Animating(context.Layout, "_descriptionTween");

    public static bool Ready(Context context) => RunContext.Singleplayer && Exposed(context)
        && !EventTaskTracker.Pending && !RelicObtainTracker.Pending && TextComplete(context)
        && !RunUi.CardPreviewsPending() && !RunUi.ResourceMotionPending()
        && !NTargetManager.Instance.IsInSelection && RunManager.Instance.ActionQueueSet.IsEmpty
        && context.Layout.OptionButtons.Any(Shown)
        && context.Layout.OptionButtons.Where(Shown).All(b => !RewardInspection.Animating(b, "_animInTween"));

    public static bool Shown(NEventOptionButton button) => VisibleUi.Displayed(button.GetNodeOrNull<Control>("%Text"));

    public static bool CanHover(NEventOptionButton button) => Shown(button) && !button.Option.IsLocked
        && button.IsEnabled && (button.GetMouseFilterWithOverride() != Control.MouseFilterEnum.Ignore
            || button.GetFocusModeWithOverride() == Control.FocusModeEnum.All);

    public static string? OptionUnavailableReason(NEventOptionButton button)
    {
        if (button.Option.IsLocked) return "This event option is locked. Use inspect_event to read its requirements.";
        if (button.Option.WasChosen && PrivateFields.Read(button.Option, "<DisableOnChosen>k__BackingField") is not false)
            return "This event option has already been used. Use inspect_event to read the remaining options.";
        if (!button.IsEnabled || RewardInspection.Animating(button, "_animInTween"))
            return "Wait for this event option to become enabled after the current activity.";
        if (!Shown(button) || !VisibleUi.OnScreen(button) || button.MouseFilter == Control.MouseFilterEnum.Ignore)
            return "This event option is not currently visible and interactive. Use inspect_event after its button finishes appearing.";
        return null;
    }

    public static bool Clickable(NEventOptionButton button) => OptionUnavailableReason(button) == null;

    private static bool IsProceed(Context context, NEventOptionButton button) => context.Model.IsFinished
        && button.Option is { IsProceed: true, TextKey: "PROCEED" } && !context.Model.CurrentOptions.Contains(button.Option);

    public static NEventOptionButton? Proceed(Context context) => context.Layout.OptionButtons.FirstOrDefault(b => IsProceed(context, b) && Shown(b));

    public void Synchronize()
    {
        var current = Current;
        if (current == null) return;
        if (!ReferenceEquals(model, current.Model))
        {
            model = current.Model; ids.Clear(); Generation++;
        }
        if (!Exposed(current)) return;
        foreach (var button in current.Layout.OptionButtons.Where(Shown))
            if (!ids.ContainsKey(button.Option)) ids[button.Option] = nextId++;
    }

    public NEventOptionButton? Find(Context context, int id) => context.Layout.OptionButtons.FirstOrDefault(b =>
        !IsProceed(context, b) && Shown(b) && ids.TryGetValue(b.Option, out var known) && known == id);

    public object? Read(bool full = false)
    {
        if (Current is not { } current) return null;
        if (!Exposed(current)) return new { status = "covered", name = (string?)null, description = (string?)null,
            options = (object?)null, proceed = (object?)null };
        bool ready = Ready(current);
        bool canChoose = ActionUnavailableReason(current) == null;
        return EnglishEventText.Read(() =>
        {
            var options = current.Layout.OptionButtons.Where(b => !IsProceed(current, b) && Shown(b)).Select(b =>
            {
                var result = new Dictionary<string, object?> { ["id"] = ids[b.Option],
                    ["title"] = EnglishCardText.Plain(b.Option.Title.GetFormattedText()),
                    ["description"] = EnglishCardText.Plain(b.Option.Description.GetFormattedText()),
                    ["enabled"] = canChoose && Clickable(b),
                    ["lethal_warning"] = VisibleUi.Shown(b.GetNodeOrNull<CanvasItem>("RedFlash")) };
                if (full) result["hover_tips"] = CanHover(b) ? b.Option.HoverTips.Select(EnglishEventText.Tip).ToArray() : Array.Empty<HoverTipText>();
                return result;
            }).ToArray();
            var proceed = Proceed(current);
            return (object)new { status = "visible",
                name = VisibleUi.Text(current.Layout, "%Title") == null ? null : EnglishCardText.Plain(current.Model.Title.GetFormattedText()),
                description = TextComplete(current) && current.Model.Description is { } text ? EnglishCardText.Plain(text.GetFormattedText()) : null,
                options,
                proceed = proceed == null ? null : new { text = EnglishCardText.Plain(proceed.Option.Title.GetFormattedText()), enabled = ready && Clickable(proceed) } };
        });
    }
}
