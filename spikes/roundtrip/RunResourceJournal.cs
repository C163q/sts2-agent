using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Screens.CardSelection;
using MegaCrit.sts2.Core.Nodes.TopBar;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal sealed class RunResourceJournal : IDisposable
{
    public static RunResourceJournal? Current { get; private set; }
    private readonly Player player;
    private readonly TurnEventBuffer buffer;
    private readonly EnglishText english = new();
    private bool healthKnown;
    private int? knownGold;

    public RunResourceJournal(Player player, TurnEventBuffer buffer)
    {
        if (Current != null) throw new InvalidOperationException("Player resources are already being recorded.");
        this.player = player;
        this.buffer = buffer;
        SampleVisibility();
        player.Creature.CurrentHpChanged += Hp;
        player.Creature.MaxHpChanged += MaxHp;
        player.GoldChanged += Gold;
        Current = this;
    }

    private bool TopBarVisible
    {
        get
        {
            if (!ReferenceEquals(player, LocalContext.GetMe(RunManager.Instance.DebugOnlyGetState()))) return false;
            if (RunUi.TopBarReadable()) return true;
            if (CardSelection.Current != null) return false;
            var global = NRun.Instance?.GlobalUi;
            var game = NGame.Instance;
            // Native choices complete before removing their overlay; the top bar stays drawn in this handoff.
            return global != null && game != null && VisibleUi.OnScreen(global.TopBar) && !RunUi.Transitioning()
                && !global.CapstoneContainer.InUse && !VisibleUi.Shown(global.MapScreen)
                && !VisibleUi.Shown(game.InspectCardScreen) && !VisibleUi.Shown(game.InspectRelicScreen)
                && NModalContainer.Instance?.OpenModal == null
                && global.Overlays.Peek() is NCardGridSelectionScreen or NChooseACardSelectionScreen
                    or NCardRewardSelectionScreen or NChooseABundleSelectionScreen;
        }
    }

    private (int? current, int? maximum) Health => !TopBarVisible ? (null, null)
        : CombatObservation.Pair(VisibleUi.Descendants<NTopBarHp>(NRun.Instance!.GlobalUi.TopBar)
            .Select(node => VisibleUi.Text(node, "%HpLabel")).FirstOrDefault(text => text != null));

    private int? GoldDisplay => TopBarVisible ? VisibleUi.Number(NRun.Instance!.GlobalUi.TopBar.Gold, "%GoldLabel") : null;

    public void SampleVisibility()
    {
        var hp = Health;
        healthKnown = hp.current == player.Creature.CurrentHp && hp.maximum == player.Creature.MaxHp;
        int? gold = GoldDisplay;
        if (gold == null) knownGold = null;
        else if (knownGold == null && gold == player.Gold) knownGold = gold;
    }

    private void Add(string type, int before, int after)
    {
        if (before == after) return;
        buffer.Add(type, new()
        {
            ["target"] = new { id = (int)(player.Creature.CombatId ?? 0), kind = "player", name = english.Name(player.Character.Title) },
            ["before"] = before, ["after"] = after
        });
    }

    private void Hp(int before, int after)
    {
        bool visible = Health.current.HasValue;
        // The combat journal owns damage and HP so a single hit is never counted twice.
        if (healthKnown && visible && TurnCapture.Journal == null) Add("hp_changed", before, after);
        healthKnown = visible;
    }

    private void MaxHp(int before, int after)
    {
        bool visible = Health.maximum.HasValue;
        if (healthKnown && visible) Add("max_hp_changed", before, after);
        healthKnown = visible;
    }

    private void Gold()
    {
        bool visible = GoldDisplay.HasValue;
        if (knownGold is int before && visible) Add("gold_changed", before, player.Gold);
        knownGold = visible ? player.Gold : null;
    }

    public void Dispose()
    {
        player.Creature.CurrentHpChanged -= Hp;
        player.Creature.MaxHpChanged -= MaxHp;
        player.GoldChanged -= Gold;
        if (ReferenceEquals(Current, this)) Current = null;
    }
}
