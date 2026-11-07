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
        if (resultMenuStack != null && PrivateFields.Read(resultMenuStack, "_submenus") is Stack<NSubmenu> pages
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
                return new(over, PrivateFields.Read(over, "_isAnimatingSummary") is true || VisibleUi.Descendants<NScoreLine>(over).Any() ? "summary" : "outcome");
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
    public static bool DisplayComplete(Context context) => TextReady(context.Root)
        && (context.Root is not NGameOverScreen over || PrivateFields.Read(over, "_isAnimatingSummary") is not true
            && !PresentationMotion.Pending(over))
        && !new[] { "_tween", "_textTween", "_buttonTween", "_unlockTween", "_cardTween", "_relicTween", "_potionTween", "_screenTween", "_backstopTween", "_lineGrowTween" }
            .Any(field => RewardInspection.Animating(context.Root, field));

    public bool Ready(Context context) => ActionUnavailableReason(context) == null;

    public string? ActionUnavailableReason(Context? context)
    {
        if (InspectionUnavailableReason(context) is { } unavailable) return unavailable;
        if (!DisplayComplete(context!)) return "The run result page is still displaying text or animation. Wait before choosing an option.";
        if (context!.Root is NTimelineScreen timeline && timeline.GetNodeOrNull<Control>("%InputBlocker") is { Visible: true })
            return "The timeline is still updating. Wait for the current unlock animation to finish.";
        return Options(context).Any(o => Clickable(o.button)) ? null
            : "No result option is enabled yet. Wait, then use get_observation or inspect_run_result to read the current options.";
    }

    public string? OptionUnavailableReason(Context? context, string id, out NClickableControl? button)
    {
        button = null;
        if (ActionUnavailableReason(context) is { } unavailable) return unavailable;
        button = Options(context!).FirstOrDefault(o => o.id == id).button;
        if (button == null) return $"The result option '{id}' is not offered on this page. Use an enabled ID from get_observation or inspect_run_result.";
        return Clickable(button) ? null
            : $"The result option '{id}' is disabled or still animating. Choose an enabled option or wait for the animation to finish.";
    }

    // Use the same result as the native banner; victory also kills the player during the epilogue.
    public static string? Outcome(Context context) => context.Root is NGameOverScreen over
        && PrivateFields.Read(over, "_history") is RunHistory history
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
        name = PrivateFields.Read(badge, "_title") is LocString title ? EnglishCardText.Plain(title.GetFormattedText()) : "",
        rarity = Path.GetFileNameWithoutExtension(badge.GetNode<TextureRect>("%BadgeHolder").Texture.ResourcePath).Replace("badge_", "") });
    private static object[] Cards(Node root, bool hover, List<string> unavailable) => VisibleUi.Descendants<NCard>(root)
        .Where(c => CombatObservation.CardVisible(c, VisibleUi.Browsable) && c.Visibility == ModelVisibility.Visible && c.Model != null).Select((card, index) =>
        EnglishEventText.Read(() => {
            var result = BrowsedCard.Read(card.Model!, $"card:{index}", PileType.None, upgrades: false, full: true, appearance: true);
            var description = card.GetNodeOrNull<CanvasItem>("%DescriptionLabel");
            if (!VisibleUi.Browsable(description) || description is RichTextLabel { VisibleRatio: < .999f })
                result["description"] = null;
            if (!hover)
            {
                result["hover_tips"] = Array.Empty<HoverTipText>();
                unavailable.Add("run_result.cards.card:" + index);
            }
            return (object)result;
        })).ToArray();

    public string? InspectionUnavailableReason(Context? context)
    {
        if (context == null) return NGame.Instance?.MainMenu != null
            ? "No run result is associated with this menu. Use get_observation to read the current screen."
            : "No run result page is available. Use get_observation to continue the current run.";
        if (!singleplayer) return "Run result access requires a local single-player result.";
        if (NModalContainer.Instance?.OpenModal != null) return "Resolve the covering dialog before using the run result.";
        if (VisibleUi.Shown(NGame.Instance?.InspectCardScreen) || VisibleUi.Shown(NGame.Instance?.InspectRelicScreen))
            return "Close the native card or relic details panel before using the run result.";
        if (RunUi.Transitioning()) return "Wait for the screen transition before using the run result.";
        return Exposed(context) ? null : "The run result page is currently covered or hidden.";
    }

    public object? Read(bool full = false)
    {
        if (Current is not { } context) return null;
        bool exposed = Exposed(context), ready = Ready(context), complete = DisplayComplete(context);
        var root = context.Root;
        bool hover = exposed && complete && (root is not NTimelineScreen timeline
            || timeline.GetNodeOrNull<Control>("%InputBlocker") is not { Visible: true });
        var badges = exposed ? VisibleUi.Descendants<NBadge>(root).Where(VisibleUi.Browsable).ToArray() : [];
        List<string> unavailable = [];
        var result = new Dictionary<string, object?> {
            ["status"] = PresentationState.Status(exposed, complete), ["phase"] = context.Phase,
            ["title"] = exposed && root is NGameOverScreen ? Text(root.GetNode<NCommonBanner>("%Banner").label) : null,
            ["texts"] = exposed ? VisibleUi.Descendants<CanvasItem>(root).Where(node => !InsideCard(node)).Select(Text)
                .Where(text => !string.IsNullOrWhiteSpace(text)).Distinct().ToArray() : [],
            ["score_lines"] = exposed && context.Phase == "summary" ? VisibleUi.Descendants<NScoreLine>(root)
                .Where(VisibleUi.Browsable).Select(line => new { label = Text(line.GetNode<CanvasItem>("%Label")) ?? "",
                    value = Text(line.GetNode<CanvasItem>("%Score")) ?? "" }).ToArray() : Array.Empty<object>(),
            ["badges"] = badges.Select(Badge).ToArray(),
            ["discoveries"] = exposed ? VisibleUi.Descendants<NDiscoveredItem>(root)
                .Where(VisibleUi.Browsable).Select(item => new { kind = DiscoveryKind(item),
                    count = int.TryParse(Text(item.GetNode<CanvasItem>("%Label")), out int count) ? count : 0 }).ToArray() : Array.Empty<object>(),
            ["options"] = exposed ? Options(context).Select(option => new { id = option.id,
                text = ButtonText(option.button), enabled = ready && Clickable(option.button) }).ToArray() : Array.Empty<object>() };
        result["cards"] = exposed ? Cards(root, hover, unavailable) : Array.Empty<object>();
        result["relics"] = exposed ? VisibleUi.Descendants<NRelicBasicHolder>(root)
            .Where(holder => VisibleUi.Browsable(holder) && VisibleUi.Browsable(holder.Relic.Icon)).Select((holder, index) => {
                if (!full) return EnglishEventText.Read(() => (object)new { name = EnglishCardText.Plain(holder.Relic.Model.Title.GetFormattedText()) });
                if (hover && HoverAccess.CanFocus(holder)) return (object)RelicInspection.Details(holder.Relic.Model, null);
                unavailable.Add("run_result.relics." + index);
                return EnglishEventText.Read(() => (object)new { name = EnglishCardText.Plain(holder.Relic.Model.Title.GetFormattedText()),
                    description = (string?)null, hover_tips = Array.Empty<HoverTipText>() });
            }).ToArray() : Array.Empty<object>();
        result["potions"] = exposed ? VisibleUi.Descendants<NPotionHolder>(root)
            .Where(holder => VisibleUi.Browsable(holder) && holder.HasPotion && VisibleUi.Browsable(holder.Potion)).Select((holder, index) => {
                if (!full) return EnglishEventText.Read(() => (object)new { name = EnglishCardText.Plain(holder.Potion!.Model.Title.GetFormattedText()) });
                if (hover && HoverAccess.CanFocus(holder)) return (object)PotionInspection.Details(holder.Potion!.Model);
                unavailable.Add("run_result.potions." + index);
                return EnglishEventText.Read(() => (object)new { name = EnglishCardText.Plain(holder.Potion!.Model.Title.GetFormattedText()),
                    description = (string?)null, hover_tips = Array.Empty<HoverTipText>() });
            }).ToArray() : Array.Empty<object>();

        List<object> tips = [];
        List<string> sources = [];
        HashSet<string> identities = [];
        void AddTip(string source, NClickableControl control, Func<HoverTipText> read)
        {
            string candidate = source;
            for (int suffix = 1; !identities.Add(candidate); suffix++) candidate = source + ":" + suffix;
            source = candidate;
            sources.Add(source);
            if (!hover || !HoverAccess.CanFocus(control)) { unavailable.Add("run_result.hover_tips." + source); return; }
            var tip = read();
            tips.Add(full ? new { source, tip.title, tip.description } : (object)new { source, tip.title });
        }
        if (exposed)
        {
            foreach (var control in VisibleUi.Descendants<NClickableControl>(root).Where(control => control is not NEpochSlot && VisibleUi.Browsable(control)))
            {
                // Navigation controls in this heterogeneous tree have no hover text.
                if (PrivateFields.Optional(control, "_hoverTip") is not IHoverTip tip) continue;
                string source = control is NBadge badge ? "badge:" + Array.IndexOf(badges, badge)
                    : control is NDiscoveredItem discovery ? "discovery:" + DiscoveryKind(discovery) : control.Name.ToString();
                AddTip(source, control, () => EnglishEventText.Read(() => EnglishEventText.Tip(tip)));
            }
            if (root is NTimelineScreen)
                foreach (var slot in VisibleUi.Descendants<NEpochSlot>(root).Where(slot => VisibleUi.Shown(slot) && epochIds.ContainsKey(slot)))
                    AddTip("epoch:" + epochIds[slot], slot, () => EnglishEventText.Read(() => {
                        var info = slot.model.UnlockInfo;
                        info.Add("IsRevealed", slot.State == EpochSlotState.Complete);
                        return HoverTipText.From(new HoverTip(slot.model.Title, info));
                    }));
        }
        result["hover_tips"] = tips.ToArray();
        // Kept in native snapshots to validate associations; public projections omit these lists.
        result["hover_sources"] = sources.ToArray();
        result["unavailable_hover_sources"] = unavailable.Distinct().ToArray();
        return result;
    }
}
