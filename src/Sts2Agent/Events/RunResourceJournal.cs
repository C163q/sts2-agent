using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Screens.CardSelection;
using Godot;
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
    private int lastGold;
    private bool crossingRoom;
    private readonly IRunState run;
    private readonly RoomResourceChange roomHp, roomMaximum, roomGold;
    public bool Pending => roomHp.Pending || roomMaximum.Pending || roomGold.Pending;

    public RunResourceJournal(Player player, TurnEventBuffer buffer)
    {
        if (Current != null) throw new InvalidOperationException("Player resources are already being recorded.");
        this.player = player;
        this.buffer = buffer;
        run = player.RunState;
        lastGold = player.Gold;
        roomHp = new("hp_changed", buffer, Target);
        roomMaximum = new("max_hp_changed", buffer, Target);
        roomGold = new("gold_changed", buffer, Target);
        SampleVisibility();
        player.Creature.CurrentHpChanged += Hp;
        player.Creature.MaxHpChanged += MaxHp;
        player.GoldChanged += Gold;
        Current = this;
    }

    internal bool TopBarVisible
    {
        get
        {
            if (!ReferenceEquals(player, LocalContext.GetMe(RunManager.Instance.DebugOnlyGetState()))) return false;
            if (RunUi.TopBarReadable()) return true;
            var global = NRun.Instance?.GlobalUi;
            var game = NGame.Instance;
            // Known native choices can keep the top bar drawn while their input boundary opens or closes.
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

    private CanvasItem? HealthLabel => NRun.Instance?.GlobalUi.TopBar is { } top
        ? VisibleUi.Descendants<NTopBarHp>(top).FirstOrDefault()?.GetNodeOrNull<CanvasItem>("%HpLabel") : null;

    private bool PreservingRoom
    {
        get
        {
            bool entering = NRun.Instance?.GlobalUi.MapScreen.IsTraveling == true
                || NavigationTasks.ChangingAct || CombatJournalScope.Current?.Pending == true;
            crossingRoom |= entering;
            var global = NRun.Instance?.GlobalUi;
            var game = NGame.Instance;
            return crossingRoom && (entering || RunUi.Transitioning())
                && ReferenceEquals(run, RunManager.Instance.DebugOnlyGetState())
                && global != null && game != null && VisibleUi.OnScreen(global.TopBar)
                && !global.CapstoneContainer.InUse && NModalContainer.Instance?.OpenModal == null
                && !VisibleUi.Shown(game.InspectCardScreen) && !VisibleUi.Shown(game.InspectRelicScreen)
                && (global.Overlays.ScreenCount == 0 || RunUi.OnlyRewardOverlays());
        }
    }

    private object Target() => new { id = (int)(player.Creature.CombatId ?? 0), kind = "player", name = english.Name(player.Character.Title) };

    public void SampleVisibility()
    {
        var hp = Health;
        bool preserve = PreservingRoom;
        roomHp.Sample(hp.current, preserve && VisibleUi.Shown(HealthLabel));
        roomMaximum.Sample(hp.maximum, preserve && VisibleUi.Shown(HealthLabel));
        healthKnown = hp.current == player.Creature.CurrentHp && hp.maximum == player.Creature.MaxHp;
        int? gold = GoldDisplay;
        roomGold.Sample(gold, preserve && VisibleUi.Shown(NRun.Instance?.GlobalUi.TopBar.Gold.GetNodeOrNull<CanvasItem>("%GoldLabel")));
        if (!preserve) crossingRoom = false;
        if (gold == null) knownGold = null;
        else if (knownGold == null && gold == player.Gold) knownGold = gold;
    }

    private void Add(string type, int before, int after)
    {
        if (before == after) return;
        buffer.Add(type, new()
        {
            ["target"] = Target(),
            ["before"] = before, ["after"] = after
        });
    }

    private void Hp(int before, int after)
    {
        bool visible = Health.current.HasValue;
        // The combat journal owns damage and HP so a single hit is never counted twice.
        if (TurnCapture.Journal != null && (TurnCapture.CapturingDamageHp || CombatObservation.HealthNumbersVisible(player.Creature)))
            roomHp.Sample(null);
        else if (roomHp.Pending || !visible && PreservingRoom && VisibleUi.Shown(HealthLabel))
        {
            roomHp.Sample(Health.current, PreservingRoom);
            roomHp.Changed(before, after);
            roomHp.Sample(Health.current, PreservingRoom);
        }
        else if (healthKnown && visible && TurnCapture.Journal == null) Add("hp_changed", before, after);
        healthKnown = visible;
    }

    private void MaxHp(int before, int after)
    {
        bool visible = Health.maximum.HasValue;
        if (roomMaximum.Pending || !visible && PreservingRoom && VisibleUi.Shown(HealthLabel))
        {
            roomMaximum.Sample(Health.maximum, PreservingRoom);
            roomMaximum.Changed(before, after);
            roomMaximum.Sample(Health.maximum, PreservingRoom);
        }
        else if (healthKnown && visible) Add("max_hp_changed", before, after);
        healthKnown = visible;
    }

    private void Gold()
    {
        int before = lastGold;
        lastGold = player.Gold;
        bool visible = GoldDisplay.HasValue;
        if (roomGold.Pending || !visible && PreservingRoom
            && VisibleUi.Shown(NRun.Instance?.GlobalUi.TopBar.Gold.GetNodeOrNull<CanvasItem>("%GoldLabel")))
        {
            roomGold.Sample(GoldDisplay, PreservingRoom);
            roomGold.Changed(before, player.Gold);
            roomGold.Sample(GoldDisplay, PreservingRoom);
        }
        else if (knownGold is int known && visible) Add("gold_changed", known, player.Gold);
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
