using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Rewards;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Rewards;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed class RewardInspection
{
    private readonly CardIdentityMap<Reward> ids = new();
    private NRewardsScreen? lastScreen;
    public int Generation { get; private set; }
    public static NRewardsScreen? Current => NRun.Instance?.GlobalUi.Overlays is { } overlays
        ? VisibleUi.Descendants<NRewardsScreen>(overlays).LastOrDefault(s => GodotObject.IsInstanceValid(s)
            && !s.IsQueuedForDeletion() && s.IsNodeReady()) : null;

    public void Synchronize()
    {
        if (ReferenceEquals(Current, lastScreen)) return;
        lastScreen = Current;
        Generation++;
    }

    public static bool Exposed(NRewardsScreen screen) => ReferenceEquals(Current, screen)
        && ReferenceEquals(NRun.Instance?.GlobalUi.Overlays.Peek(), screen)
        && RunUi.NonCombatVisible() && !VisibleUi.Shown(NRun.Instance?.GlobalUi.MapScreen)
        && !RunUi.CardPreviewsPending()
        && VisibleUi.Shown(screen);

    public static NRewardButton[] Buttons(NRewardsScreen screen) => VisibleUi.Descendants<NRewardButton>(screen)
        .Where(b => GodotObject.IsInstanceValid(b) && !b.IsQueuedForDeletion() && b.Reward != null
            && VisibleUi.Shown(b) && VisibleUi.Shown(b.GetNode<Control>("%Label"))).ToArray();

    public static bool Animating(object owner, string field) => PrivateFields.Optional(owner, field) is Tween tween
        && GodotObject.IsInstanceValid(tween) && tween.IsRunning();

    public static bool DisplayComplete(NRewardsScreen screen) => !Animating(screen, "_fadeTween");

    public static bool Ready(NRewardsScreen screen) => Exposed(screen) && DisplayComplete(screen)
        && !Buttons(screen).Any(b => !b.IsEnabled) && RunManager.Instance.ActionQueueSet.IsEmpty
        && !CombatManager.Instance.IsInProgress;

    public static string? InspectionUnavailableReason(NRewardsScreen? screen) => UnavailableReason(screen, claiming: false);

    public static bool Claimable(NRewardButton button) => button.IsEnabled && Type(button.Reward!) != "unsupported";

    public string? ClaimUnavailableReason(NRewardsScreen? screen, int id, out NRewardButton? button)
    {
        button = null;
        if (UnavailableReason(screen, claiming: true) is { } reason) return reason;
        button = Find(screen!, id);
        if (button == null) return "That reward is no longer available. Choose a current ID from inspect_rewards or get_observation.";
        if (Type(button.Reward!) == "unsupported") return "That reward type is not supported by claim_reward.";
        return Claimable(button) ? null : "That reward is disabled. Wait for the current reward interaction to finish.";
    }

    private static string? UnavailableReason(NRewardsScreen? screen, bool claiming)
    {
        if (screen != null && GodotObject.IsInstanceValid(screen) && screen.IsNodeReady()
            && RunManager.Instance.IsSingleplayerOrFakeMultiplayer && (claiming ? Ready(screen) : Exposed(screen))) return null;
        if (!RunManager.Instance.IsInProgress)
            return claiming ? "No local run is available for claiming rewards." : "No local run is available for reward inspection.";
        if (!RunManager.Instance.IsSingleplayerOrFakeMultiplayer)
            return claiming ? "Claiming rewards requires a local single-player run." : "Reward inspection requires a local single-player run.";
        if (screen == null || !GodotObject.IsInstanceValid(screen) || !screen.IsNodeReady())
            return "No reward list is available on the current screen.";
        var map = NRun.Instance?.GlobalUi.MapScreen;
        if (VisibleUi.Shown(map))
            return map!.IsOpen ? "Close the map with close_map before interacting with rewards."
                : "Wait for the map to finish closing before interacting with rewards.";
        if (CardView.Current != null)
            return "Close the card browsing page with close_card_view before interacting with rewards.";
        if (CardSelection.Current != null)
            return "Resolve the current card selection before interacting with rewards; inspect_selection shows its choices.";
        if (RunUi.CardPreviewsPending()) return "Wait for the card previews to finish before interacting with rewards.";
        if (RunUi.Transitioning()) return "Wait for the screen transition before interacting with rewards.";
        if (!Exposed(screen)) return "The reward list is covered by a dialog or another screen.";
        if (!RunManager.Instance.ActionQueueSet.IsEmpty)
            return "Wait for the current action to finish before interacting with rewards.";
        return "The reward list is still preparing. Wait before interacting with it.";
    }

    public static NProceedButton? Proceed(NRewardsScreen screen) => screen.GetNodeOrNull<NProceedButton>("ProceedButton") is { } button
        && VisibleUi.OnScreen(button) && VisibleUi.Text(button, "%Label") is { Length: > 0 } ? button : null;

    public static string Type(Reward reward) => reward switch
    {
        GoldReward => "gold", PotionReward => "potion", RelicReward => "relic", CardReward => "card",
        SpecialCardReward => "special_card", CardRemovalReward => "card_removal", _ => "unsupported"
    };

    public int Id(Reward reward) => ids.Get(reward);
    public NRewardButton? Find(NRewardsScreen screen, int id) => Buttons(screen).FirstOrDefault(b => Id(b.Reward!) == id);

    public object? Read(bool full = false)
    {
        if (Current is not { } screen) return null;
        if (!Exposed(screen)) return new { status = "covered", title = (string?)null, items = (object?)null, proceed = (object?)null };
        bool ready = Ready(screen);
        // The current list can be scrolled; only explicit hiding excludes a reward row.
        var rows = Buttons(screen).Select(b =>
        {
            var reward = b.Reward!;
            var item = new Dictionary<string, object?>
            {
                ["id"] = Id(reward), ["type"] = Type(reward),
                ["text"] = EnglishCardText.Read(() => EnglishCardText.Plain(reward.Description.GetFormattedText())),
                ["enabled"] = ready && Claimable(b),
                ["linked_group"] = reward.ParentRewardSet is { } group ? Id(group) : null
            };
            if (full) item["hover_tips"] = EnglishCardText.Read(() => reward.HoverTips.Select(HoverTipText.From).Distinct().ToArray());
            return item;
        }).ToArray();
        var button = Proceed(screen);
        object? proceed = button == null ? null : new
        {
            text = EnglishCardText.Read(() => EnglishCardText.Plain((button.IsSkip ? NProceedButton.SkipLoc : NProceedButton.ProceedLoc).GetFormattedText())),
            enabled = ready && button.IsEnabled, skips_remaining = button.IsSkip
        };
        string? title = null;
        string? displayed = VisibleUi.Text(screen, "%HeaderLabel");
        foreach (string key in new[] { "COMBAT_REWARD_HEADER_LOOT", "COMBAT_REWARD_HEADER_MUGGED" })
        {
            var loc = new LocString("gameplay_ui", key);
            if (displayed != null && EnglishCardText.Plain(loc.GetFormattedText()) == displayed)
                title = EnglishCardText.Read(() => EnglishCardText.Plain(loc.GetFormattedText()));
        }
        return new { status = PresentationState.Status(true, DisplayComplete(screen)), title, items = rows, proceed };
    }

    public static async Task Reveal(NRewardsScreen screen, NRewardButton button, Func<Task> frame, Func<bool> unchanged,
        Action beginInteraction)
    {
        if (VisibleUi.OnScreen(button.GetNode<Control>("%Label"))) return;
        // Follow the native reward list's wheel target; never click a clipped row through its mask.
        var container = screen.GetNode<Control>("%RewardsContainer");
        float bottom = 35f - container.Size.Y + 400f;
        float target = Mathf.Clamp(35f - button.Position.Y, Mathf.Min(35f, bottom), 35f);
        beginInteraction();
        HarmonyLib.AccessTools.Field(typeof(NRewardsScreen), "_targetDragPos").SetValue(screen, new Vector2(container.Position.X, target));
        for (int i = 0; i < 30; i++)
        {
            await frame();
            if (!unchanged()) throw new InvalidOperationException("The rewards changed while scrolling.");
            if (VisibleUi.OnScreen(button.GetNode<Control>("%Label"))) return;
        }
        throw new InvalidOperationException("The reward row is not visible.");
    }
}
