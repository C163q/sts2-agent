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

    private static bool TextComplete(Context context) => context.Layout.GetNodeOrNull<RichTextLabel>("%EventDescription")
        is { VisibleRatio: >= 0.999f } description && VisibleUi.OnScreen(description)
        && !RewardInspection.Animating(context.Layout, "_descriptionTween");

    public static bool Ready(Context context) => TreasureInspection.Singleplayer && Exposed(context)
        && !EventTaskTracker.Pending && !RelicObtainTracker.Pending && TextComplete(context)
        && !RunUi.CardPreviewsPending() && !RunUi.ResourceMotionPending()
        && !NTargetManager.Instance.IsInSelection && RunManager.Instance.ActionQueueSet.IsEmpty
        && context.Layout.OptionButtons.Any(Shown)
        && context.Layout.OptionButtons.Where(Shown).All(b => !RewardInspection.Animating(b, "_animInTween"));

    public static bool Shown(NEventOptionButton button) => VisibleUi.OnScreen(button.GetNodeOrNull<Control>("%Text"));

    public static bool Clickable(NEventOptionButton button) => Shown(button) && button.IsEnabled && !button.Option.IsLocked
        && button.MouseFilter != Control.MouseFilterEnum.Ignore
        && (!button.Option.WasChosen || CardSelection.Field(button.Option, "<DisableOnChosen>k__BackingField") is false)
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
                if (full) result["hover_tips"] = Clickable(b) ? b.Option.HoverTips.Select(EnglishEventText.Tip).ToArray() : Array.Empty<HoverTipText>();
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
