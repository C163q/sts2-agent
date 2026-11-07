using Godot;
using MegaCrit.Sts2.Core.Entities.Ancients;
using MegaCrit.Sts2.Core.Events;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Events;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed class AncientInspection
{
    internal sealed record Context(AncientEventModel Model, NAncientEventLayout Layout);
    private readonly Dictionary<EventOption, int> ids = [];
    private AncientEventModel? model;
    private int nextId;
    public int Generation { get; private set; }

    public static Context? Current => RunUi.LocalEvent is AncientEventModel ancient && NEventRoom.Instance?.Layout is NAncientEventLayout layout
        && ReferenceEquals(ancient.Node, layout) && GodotObject.IsInstanceValid(layout) && layout.IsNodeReady() && !layout.IsQueuedForDeletion()
        ? new(ancient, layout) : null;

    public static bool Exposed(Context context) => ReferenceEquals(Current?.Layout, context.Layout)
        && RunUi.NonCombatVisible() && NRun.Instance?.GlobalUi.Overlays.ScreenCount == 0
        && !VisibleUi.Shown(NRun.Instance?.GlobalUi.MapScreen) && VisibleUi.Shown(context.Layout);

    public static string? InspectionUnavailableReason(Context? context)
    {
        if (!RunManager.Instance.IsInProgress) return "No local run is available for ancient inspection.";
        if (context == null) return "No supported ancient is available on the current screen.";
        if (!RunContext.Singleplayer) return "Ancient inspection requires a local single-player run.";
        if (Exposed(context)) return null;
        if (VisibleUi.Shown(NRun.Instance?.GlobalUi.MapScreen)) return NRun.Instance!.GlobalUi.MapScreen.IsOpen
            ? "Close the map with close_map before inspecting the ancient." : "Wait for the map to finish closing before inspecting the ancient.";
        if (CardView.Current != null) return "Close the card browsing page with close_card_view before inspecting the ancient.";
        if (CardSelection.Current != null) return "Resolve the current card selection; inspect_selection shows its choices.";
        if (RewardInspection.Current != null) return "Resolve the current reward page; inspect_rewards shows its rows.";
        return "The ancient is covered by a dialog or a screen transition.";
    }

    public static bool Busy => Current is { } current
        && PrivateFields.Read(RunManager.Instance.EventSynchronizer, "_pendingOptionTasks") is IEnumerable<Task> tasks
        && tasks.Any(t => !t.IsCompleted) || RelicObtainTracker.Pending;

    public static bool Ready(Context context) => RunContext.Singleplayer && Exposed(context)
        && !Busy && !RunUi.CardPreviewsPending() && !RunUi.ResourceMotionPending()
        && !NTargetManager.Instance.IsInSelection && RunManager.Instance.ActionQueueSet.IsEmpty
        && !MotionPending(context)
        && (Continue(context) != null || context.Layout.OptionButtons.Any(Shown));

    private static bool MotionPending(Context context) => RewardInspection.Animating(context.Layout, "_contentTween")
        || RewardInspection.Animating(context.Layout, "_descriptionTween")
        || RewardInspection.Animating(context.Layout, "_bannerTween")
        // The name banner can reveal its epithet after the options have become clickable.
        || PrivateFields.Read(context.Layout, "_ancientNameBanner") is Control banner && GodotObject.IsInstanceValid(banner)
            && (RewardInspection.Animating(banner, "_tween") || RewardInspection.Animating(banner, "_moveTween"));

    private static NAncientDialogueHitbox? DisplayedContinue(Context context) => context.Layout.GetNodeOrNull<NAncientDialogueHitbox>("%DialogueHitbox")
        is { IsEnabled: true } button && VisibleUi.Displayed(button) ? button : null;

    public static NAncientDialogueHitbox? Continue(Context context) => DisplayedContinue(context) is { } button
        && VisibleUi.OnScreen(button) ? button : null;

    public static bool Shown(NEventOptionButton button) => VisibleUi.Displayed(button.GetNodeOrNull<Control>("%Text"));
    public static bool CanHover(NEventOptionButton button) => Shown(button) && !button.Option.IsLocked && button.IsEnabled
        && (button.GetMouseFilterWithOverride() != Control.MouseFilterEnum.Ignore
            || button.GetFocusModeWithOverride() == Control.FocusModeEnum.All);
    public static bool Clickable(NEventOptionButton button) => Shown(button) && VisibleUi.OnScreen(button)
        && button.IsEnabled && !button.Option.IsLocked
        && button.MouseFilter != Control.MouseFilterEnum.Ignore && (!button.Option.WasChosen || button.Option.IsProceed)
        && !RewardInspection.Animating(button, "_animInTween");

    public static NEventOptionButton? Proceed(Context context) => context.Layout.OptionButtons
        .FirstOrDefault(b => b.Option.IsProceed && Shown(b));

    public void Synchronize()
    {
        var current = Current;
        if (!ReferenceEquals(model, current?.Model))
        {
            model = current?.Model; ids.Clear(); nextId = 0; Generation++;
        }
        if (current == null || !Exposed(current)) return;
        foreach (var button in current.Layout.OptionButtons.Where(Shown))
            if (!ids.ContainsKey(button.Option)) ids[button.Option] = nextId++;
    }

    public NEventOptionButton? Find(Context context, int id) => context.Layout.OptionButtons.FirstOrDefault(b =>
        !b.Option.IsProceed && Shown(b) && ids.TryGetValue(b.Option, out var known) && known == id);

    public object Inspect()
    {
        var current = Current!;
        return new { ancient = Read(full: true), unavailable_hover_sources = current.Layout.OptionButtons
            .Where(button => !button.Option.IsProceed && Shown(button) && !CanHover(button))
            .Select(button => "ancient.options." + ids[button.Option]).ToArray() };
    }

    public object? Read(bool full = false)
    {
        if (Current is not { } current) return null;
        if (!Exposed(current)) return new { status = "covered", name = (string?)null, epithet = (string?)null, description = (string?)null,
            dialogue = (object?)null, options = (object?)null, @continue = (object?)null, proceed = (object?)null };
        bool ready = Ready(current);
        return EnglishCardText.Read(() =>
        {
            var lines = VisibleUi.Descendants<NAncientDialogueLine>(current.Layout).Where(line =>
                VisibleUi.DisplayedText(line, "%Text") != null).Select(line =>
            {
                var data = (AncientDialogueLine)PrivateFields.Read(line, "_line")!;
                return new { speaker = EnglishCardText.Plain((data.Speaker == AncientDialogueSpeaker.Ancient
                    ? current.Model.Title : current.Model.Owner!.Character.Title).GetFormattedText()),
                    text = EnglishCardText.Plain(data.LineText!.GetFormattedText()) };
            }).ToArray();
            var options = current.Layout.OptionButtons.Where(b => !b.Option.IsProceed && Shown(b)).Select(b => EnglishRelicText.Read(b.Option.Relic, () =>
            {
                var result = new Dictionary<string, object?> { ["id"] = ids[b.Option],
                    ["title"] = EnglishCardText.Plain(b.Option.Title.GetFormattedText()),
                    ["description"] = EnglishCardText.Plain(b.Option.Description.GetFormattedText()),
                    ["enabled"] = ready && DisplayedContinue(current) == null && Clickable(b),
                    ["lethal_warning"] = b.Option.WillKillPlayer?.Invoke(current.Model.Owner!) ?? false };
                if (full) result["hover_tips"] = CanHover(b)
                    ? (b.Option.Relic is { } relic ? EnglishRelicText.ExtraTips(relic) : b.Option.HoverTips).Select(HoverTipText.From).ToArray()
                    : Array.Empty<HoverTipText>();
                return result;
            })).ToArray();
            var proceed = Proceed(current);
            var next = DisplayedContinue(current);
            var label = PrivateFields.Read(current.Layout, "_fakeNextButtonLabel") as Control;
            return (object)new { status = "visible", name = EnglishCardText.Plain(current.Model.Title.GetFormattedText()),
                epithet = VisibleUi.DisplayedText(PrivateFields.Read(current.Layout, "_ancientNameBanner") as Control, "%Epithet") == null
                    ? null : EnglishCardText.Plain(current.Model.Epithet.GetFormattedText()),
                description = VisibleUi.DisplayedText(current.Layout, "%EventDescription") == null ? null
                    : EnglishCardText.Plain(current.Model.Description!.GetFormattedText()), dialogue = lines, options,
                @continue = next == null ? null : new { text = VisibleUi.DisplayedText(label, ".") == null ? null :
                    (PrivateFields.Read(current.Layout, "_dialogue") as IReadOnlyList<AncientDialogueLine>)?
                        .ElementAtOrDefault((int)PrivateFields.Read(current.Layout, "_currentDialogueLine")!)?.NextButtonText is { } nextText
                        ? EnglishCardText.Plain(nextText.GetFormattedText()) : null, enabled = ready && Continue(current) != null },
                proceed = proceed == null ? null : new { text = EnglishCardText.Plain(proceed.Option.Title.GetFormattedText()),
                    enabled = ready && Clickable(proceed) } };
        });
    }
}
