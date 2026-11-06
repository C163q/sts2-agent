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

    public static string? InspectionUnavailableReason(Context? context)
    {
        if (!RunManager.Instance.IsInProgress) return "No local run is available for event inspection.";
        if (context == null) return "No supported event is available on the current screen.";
        if (!RunContext.Singleplayer) return "Event inspection requires a local single-player run.";
        if (Exposed(context)) return null;
        if (VisibleUi.Shown(NRun.Instance?.GlobalUi.MapScreen)) return "Close the map with close_map before inspecting the event.";
        if (CardView.Current != null) return "Close the card browsing page with close_card_view before inspecting the event.";
        if (CardSelection.Current != null) return "Resolve the current card selection; inspect_selection shows its choices.";
        if (RewardInspection.Current != null) return "Resolve the current reward page; inspect_rewards shows its rows.";
        if (DivinationInspection.Current != null) return "Wait for the divination board to finish opening.";
        if (EventConfirmation.Current != null) return "Resolve the confirmation with respond_to_confirmation before inspecting the event.";
        return "The event is covered by a dialog or a screen transition.";
    }

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

    public static bool Clickable(NEventOptionButton button) => Shown(button) && VisibleUi.OnScreen(button) && button.IsEnabled && !button.Option.IsLocked
        && button.MouseFilter != Control.MouseFilterEnum.Ignore
        && (!button.Option.WasChosen || PrivateFields.Read(button.Option, "<DisableOnChosen>k__BackingField") is false)
        && !RewardInspection.Animating(button, "_animInTween");

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
        return EnglishEventText.Read(() =>
        {
            var options = current.Layout.OptionButtons.Where(b => !IsProceed(current, b) && Shown(b)).Select(b =>
            {
                var result = new Dictionary<string, object?> { ["id"] = ids[b.Option],
                    ["title"] = EnglishCardText.Plain(b.Option.Title.GetFormattedText()),
                    ["description"] = EnglishCardText.Plain(b.Option.Description.GetFormattedText()),
                    ["enabled"] = ready && Clickable(b),
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
