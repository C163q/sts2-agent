using Godot;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.Potions;
using MegaCrit.Sts2.Core.Nodes.Relics;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Screens.GameOverScreen;
using MegaCrit.Sts2.Core.Nodes.Screens.MainMenu;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Screens.RunHistoryScreen;
using MegaCrit.Sts2.Core.Nodes.Screens.Timeline;
using MegaCrit.Sts2.Core.Nodes.Screens.Timeline.UnlockScreens;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed class RunResultInspection
{
    internal sealed record Context(Control Root, string Phase);
    private bool leavingResult;
    private NGameOverScreen? lastGameOver;
    private Control? lastRoot;
    private bool singleplayer;
    private NSubmenuStack? resultMenuStack;
    private NTimelineScreen? resultTimeline;
    private readonly Dictionary<NEpochSlot, int> epochIds = [];
    public int Generation { get; private set; }
    public bool ReturningToMenu => leavingResult;
    public void Leaving() => leavingResult = true;
    public void Finished()
    {
        leavingResult = false;
        if (GodotObject.IsInstanceValid(resultMenuStack)) resultMenuStack!.StackModified -= MenuStackChanged;
        resultMenuStack = null; resultTimeline = null;
    }

    private void MenuStackChanged()
    {
        if (resultMenuStack != null && CardSelection.Field(resultMenuStack, "_submenus") is Stack<NSubmenu> pages
            && resultTimeline != null && pages.Contains(resultTimeline)) return;
        Finished();
    }

    private void BindTimeline(NTimelineScreen timeline)
    {
        var stack = NGame.Instance!.MainMenu!.SubmenuStack;
        if (ReferenceEquals(resultMenuStack, stack) && ReferenceEquals(resultTimeline, timeline)) return;
        if (GodotObject.IsInstanceValid(resultMenuStack)) resultMenuStack!.StackModified -= MenuStackChanged;
        resultMenuStack = stack; resultTimeline = timeline;
        resultMenuStack.StackModified += MenuStackChanged;
    }

    public Context? Current
    {
        get
        {
            if (NRun.Instance?.GlobalUi.Overlays.Peek() is NGameOverScreen over && GodotObject.IsInstanceValid(over)
                && over.IsNodeReady() && !over.IsQueuedForDeletion())
            {
                if (!ReferenceEquals(lastGameOver, over)) { Finished(); lastGameOver = over; Generation++; epochIds.Clear(); singleplayer = RunContext.Singleplayer; }
                if (VisibleUi.Descendants<NRunHistory>(over).FirstOrDefault(VisibleUi.Shown) is { } history) return new(history, "history");
                if (VisibleUi.Shown(over.GetNodeOrNull<Control>("%DailyRunLeaderboard"))) return new(over, "leaderboard");
                return new(over, CardSelection.Field(over, "_isAnimatingSummary") is true || VisibleUi.Descendants<NScoreLine>(over).Any() ? "summary" : "outcome");
            }
            if (leavingResult && NGame.Instance?.MainMenu?.SubmenuStack.Peek() is NTimelineScreen timeline && VisibleUi.Shown(timeline))
            {
                BindTimeline(timeline);
                if (VisibleUi.Descendants<NTimelineTutorial>(timeline).FirstOrDefault(VisibleUi.Shown) is { } tutorial) return new(tutorial, "tutorial");
                if (VisibleUi.Descendants<NUnlockScreen>(timeline).LastOrDefault(VisibleUi.Shown) is { } unlock) return new(unlock, "unlock");
                if (VisibleUi.Descendants<NEpochInspectScreen>(timeline).FirstOrDefault(VisibleUi.Shown) is { } epoch) return new(epoch, "epoch");
                return new(timeline, "timeline");
            }
            return null;
        }
    }

    public void Synchronize()
    {
        if (leavingResult && NGame.Instance?.MainMenu is { } menu && !menu.SubmenuStack.SubmenusOpen
            && !RunUi.Transitioning()) Finished();
        var current = Current;
        if (!ReferenceEquals(lastRoot, current?.Root)) { lastRoot = current?.Root; Generation++; }
        if (current?.Root is NTimelineScreen timeline)
            foreach (var slot in VisibleUi.Descendants<NEpochSlot>(timeline).Where(VisibleUi.Shown))
                if (!epochIds.ContainsKey(slot)) epochIds[slot] = epochIds.Count;
    }

    public static bool Exposed(Context context) => VisibleUi.Shown(context.Root) && !RunUi.Transitioning()
        && NModalContainer.Instance?.OpenModal == null && !VisibleUi.Shown(NGame.Instance?.InspectCardScreen)
        && !VisibleUi.Shown(NGame.Instance?.InspectRelicScreen);

    private static bool TextReady(Node root) => VisibleUi.Descendants<RichTextLabel>(root).Where(VisibleUi.Browsable).All(l => l.VisibleRatio >= .999f);
    public bool Ready(Context context) => singleplayer && Exposed(context) && TextReady(context.Root)
        && (context.Root is not NGameOverScreen over || CardSelection.Field(over, "_isAnimatingSummary") is not true
            && !RunResultMotion.Pending(over))
        && !new[] { "_tween", "_textTween", "_buttonTween", "_unlockTween", "_cardTween", "_relicTween", "_potionTween", "_screenTween", "_backstopTween", "_lineGrowTween" }
            .Any(field => RewardInspection.Animating(context.Root, field))
        && (context.Root is not NTimelineScreen timeline || timeline.GetNodeOrNull<Control>("%InputBlocker") is not { Visible: true })
        && Options(context).Any(o => Clickable(o.button));

    // Use the same result as the native banner; victory also kills the player during the epilogue.
    public static string? Outcome(Context context) => context.Root is NGameOverScreen over
        && CardSelection.Field(over, "_history") is RunHistory history
            ? history.Win ? "run_won" : "run_lost" : null;

    public static bool Clickable(NClickableControl button) => (button is NEpochSlot ? VisibleUi.Shown(button) : VisibleUi.OnScreen(button)) && button.IsEnabled
        && !RewardInspection.Animating(button, "_tween") && !RewardInspection.Animating(button, "_buttonTween");

    public IEnumerable<(string id, NClickableControl button)> Options(Context context)
    {
        var root = context.Root;
        if (root is NGameOverScreen)
        {
            foreach (var (id, path) in new[] { ("continue", "%ContinueButton"), ("view_run", "%ViewRunButton"),
                ("main_menu", "%MainMenuButton"), ("leaderboard", "%LeaderboardButton") })
                if (root.GetNodeOrNull<NClickableControl>(path) is { } button && VisibleUi.OnScreen(button)) yield return (id, button);
        }
        else if (root is NTimelineScreen timeline)
        {
            foreach (var slot in VisibleUi.Descendants<NEpochSlot>(timeline).Where(s => s.State == EpochSlotState.Obtained && VisibleUi.Shown(s)))
                if (epochIds.TryGetValue(slot, out int id)) yield return ($"epoch:{id}", slot);
            if (root.GetNodeOrNull<NClickableControl>("BackButton") is { } back && VisibleUi.OnScreen(back)) yield return ("back", back);
        }
        else
        {
            foreach (var (id, path) in context.Phase switch {
                "epoch" => new[] { ("continue", "%CloseButton"), ("next_chapter", "%NextChapterButton"), ("previous_chapter", "%PrevChapterButton") },
                "tutorial" => new[] { ("continue", "%AcknowledgeButton") },
                "unlock" => new[] { ("confirm", "ConfirmButton") },
                _ => new[] { ("back", "BackButton") } })
                if (root.GetNodeOrNull<NClickableControl>(path) is { } button && VisibleUi.OnScreen(button)) yield return (id, button);
        }
    }

    public static string? Text(CanvasItem item)
    {
        if (!VisibleUi.Browsable(item)) return null;
        string? value = item switch { RichTextLabel rich when rich.VisibleRatio >= .999f => rich.Text,
            Label label => label.Text, _ => null };
        if (value != null && item.Name == "PlaceholderLabel")
            value = EnglishCardText.Read(() => new LocString("timeline", "PLACEHOLDER_PORTRAIT").GetRawText());
        return value == null ? null : item is Label && System.Text.RegularExpressions.Regex.IsMatch(value, @"\A\[\d+/\d+\]\z")
            ? value : EnglishEventText.Label(item, value);
    }
    private static string ButtonText(NClickableControl button) => button is NEpochSlot ? "Reveal"
        : string.Join(" ", VisibleUi.Descendants<CanvasItem>(button).Select(Text).Where(t => !string.IsNullOrWhiteSpace(t)).Distinct());

    private static string DiscoveryKind(NDiscoveredItem item) => item.Name.ToString().Replace("Discovered", "").ToLowerInvariant();
    private static bool InsideCard(Node node)
    {
        for (var parent = node.GetParent(); parent != null; parent = parent.GetParent()) if (parent is NCard) return true;
        return false;
    }
    private static object Badge(NBadge badge) => EnglishEventText.Read(() => new {
        name = CardSelection.Field(badge, "_title") is LocString title ? EnglishCardText.Plain(title.GetFormattedText()) : "",
        rarity = Path.GetFileNameWithoutExtension(badge.GetNode<TextureRect>("%BadgeHolder").Texture.ResourcePath).Replace("badge_", "") });
    private static object[] Cards(Node root) => VisibleUi.Descendants<NCard>(root)
        .Where(c => CombatObservation.CardVisible(c, VisibleUi.Browsable) && c.Visibility == ModelVisibility.Visible && c.Model != null).Select((card, index) =>
        EnglishEventText.Read(() => {
            var result = BrowsedCard.Read(card.Model!, $"card:{index}", PileType.None, upgrades: false, full: true, appearance: true);
            return (object)result;
        })).ToArray();

    public object? Read(bool full = false)
    {
        if (Current is not { } context) return null;
        bool exposed = Exposed(context), ready = Ready(context);
        var root = context.Root;
        var result = new Dictionary<string, object?> {
            ["status"] = !exposed ? "covered" : ready ? "visible" : "not_ready", ["phase"] = context.Phase,
            ["title"] = exposed && root is NGameOverScreen ? Text(root.GetNode<NCommonBanner>("%Banner").label) : null,
            ["texts"] = exposed ? VisibleUi.Descendants<CanvasItem>(root).Where(n => !InsideCard(n)).Select(Text).Where(t => !string.IsNullOrWhiteSpace(t)).Distinct().ToArray() : [],
            ["score_lines"] = exposed && context.Phase == "summary" ? VisibleUi.Descendants<NScoreLine>(root).Where(VisibleUi.Browsable).Select(line => new {
                label = Text(line.GetNode<CanvasItem>("%Label")) ?? "", value = Text(line.GetNode<CanvasItem>("%Score")) ?? "" }).ToArray() : Array.Empty<object>(),
            ["badges"] = exposed && context.Phase == "summary" ? VisibleUi.Descendants<NBadge>(root).Where(VisibleUi.Browsable).Select(Badge).ToArray() : Array.Empty<object>(),
            ["discoveries"] = exposed && context.Phase == "summary" ? VisibleUi.Descendants<NDiscoveredItem>(root).Where(VisibleUi.Browsable).Select(item => new {
                kind = DiscoveryKind(item), count = int.TryParse(Text(item.GetNode<CanvasItem>("%Label")), out int count) ? count : 0 }).ToArray() : Array.Empty<object>(),
            ["options"] = exposed ? Options(context).Select(o => new { id = o.id, text = ButtonText(o.button), enabled = ready && Clickable(o.button) }).ToArray() : Array.Empty<object>() };
        result["cards"] = exposed ? Cards(root) : Array.Empty<object>();
        result["relics"] = exposed ? VisibleUi.Descendants<NRelicBasicHolder>(root).Where(h => VisibleUi.Browsable(h) && VisibleUi.Browsable(h.Relic.Icon))
            .Select(h => full ? (object)RelicInspection.Details(h.Relic.Model, null) : EnglishEventText.Read(() => (object)new { name = EnglishCardText.Plain(h.Relic.Model.Title.GetFormattedText()) })).ToArray() : Array.Empty<object>();
        result["potions"] = exposed ? VisibleUi.Descendants<NPotionHolder>(root).Where(h => VisibleUi.Browsable(h) && h.HasPotion && VisibleUi.Browsable(h.Potion))
            .Select(h => full ? (object)PotionInspection.Details(h.Potion!.Model) : EnglishEventText.Read(() => (object)new { name = EnglishCardText.Plain(h.Potion!.Model.Title.GetFormattedText()) })).ToArray() : Array.Empty<object>();
        if (full) result["hover_tips"] = exposed ? VisibleUi.Descendants<NClickableControl>(root).Where(c => c is not NEpochSlot && VisibleUi.Browsable(c))
            .Select(control => (control, tip: CardSelection.Field(control, "_hoverTip") as IHoverTip))
            .Where(pair => pair.tip != null).Select(pair => EnglishEventText.Read(() => new {
                source = pair.control is NBadge ? "badge:" + VisibleUi.Descendants<NBadge>(root).ToList().IndexOf((NBadge)pair.control)
                    : pair.control is NDiscoveredItem discovery ? "discovery:" + DiscoveryKind(discovery) : pair.control.Name.ToString(), title = EnglishEventText.Tip(pair.tip!).title,
                description = EnglishEventText.Tip(pair.tip!).description })).Cast<object>().Concat(
                root is NTimelineScreen ? VisibleUi.Descendants<NEpochSlot>(root).Where(s => VisibleUi.Shown(s) && epochIds.ContainsKey(s)).Select(slot => EnglishEventText.Read(() => {
                    var info = slot.model.UnlockInfo;
                    info.Add("IsRevealed", slot.State == EpochSlotState.Complete);
                    var tip = HoverTipText.From(new HoverTip(slot.model.Title, info));
                    return (object)new { source = $"epoch:{epochIds[slot]}", title = tip.title, description = tip.description };
                })) : Array.Empty<object>()).ToArray() : Array.Empty<object>();
        return result;
    }
}
