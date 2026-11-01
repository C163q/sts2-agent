using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using Godot;

namespace Sts2Agent;

internal sealed class CombatResourceJournal : IDisposable
{
    public static CombatResourceJournal? Current { get; private set; }
    private readonly CombatState combat;
    private readonly Player player;
    private readonly PlayerCombatState state;
    private readonly VisibleResourceChange energy, stars;
    private bool starLabelHasLayout;
    public bool Pending => energy.Pending || stars.Pending;

    public CombatResourceJournal(CombatState combat, Player player, TurnEventBuffer buffer)
    {
        if (Current != null) throw new InvalidOperationException("Combat resources are already being recorded.");
        this.combat = combat;
        this.player = player;
        state = player.PlayerCombatState!;
        var english = new EnglishText();
        object Target() => new { id = (int)(player.Creature.CombatId ?? 0), kind = "player", name = english.Name(player.Character.Title) };
        energy = new("energy_changed", buffer, Target);
        stars = new("stars_changed", buffer, Target);
        SampleVisibility();
        state.EnergyChanged += Energy;
        state.StarsChanged += Stars;
        Current = this;
    }

    private bool Visible => ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState())
        && ReferenceEquals(state, player.PlayerCombatState) && CombatObservation.Status() == "visible";

    private int? EnergyDisplay => !Visible ? null : CombatObservation.Pair(
        VisibleUi.Descendants<NEnergyCounter>(NCombatRoom.Instance!.Ui.EnergyCounterContainer)
            .Where(counter => ReferenceEquals(CardSelection.Field(counter, "_player"), player))
            .Select(counter => VisibleUi.Text(counter, "Label")).FirstOrDefault(text => text != null)).current;

    private int? StarsDisplay => !Visible ? null : VisibleUi.Descendants<NStarCounter>(NCombatRoom.Instance!.Ui)
        .Where(counter => VisibleUi.OnScreen(counter) && ReferenceEquals(CardSelection.Field(counter, "_player"), player))
        .Select(counter => VisibleUi.Number(counter, "%CountLabel")).FirstOrDefault();

    private bool StarAreaVisible
    {
        get
        {
            if (NCombatRoom.Instance is not { } room) return false;
            var counter = VisibleUi.Descendants<NStarCounter>(room.Ui)
                .FirstOrDefault(node => ReferenceEquals(CardSelection.Field(node, "_player"), player));
            var label = counter?.GetNodeOrNull<Control>("%CountLabel");
            starLabelHasLayout |= label != null && label.Size.X > 0 && label.Size.Y > 0;
            return Visible && VisibleUi.OnScreen(counter) && VisibleUi.Shown(label)
                && (VisibleUi.OnScreen(label) || !starLabelHasLayout);
        }
    }

    public void SampleVisibility()
    {
        energy.Sample(EnergyDisplay);
        int? displayed = StarsDisplay;
        bool area = StarAreaVisible;
        // A newly revealed star counter can precede the label's first layout and number.
        if (displayed != null || !stars.PendingReveal || !area) stars.Sample(displayed);
    }

    private void Energy(int before, int after) => energy.Changed(after, EnergyDisplay);
    private void Stars(int before, int after)
    {
        int? displayed = StarsDisplay;
        if (!stars.HasBaseline && StarAreaVisible) stars.Revealed(after, displayed);
        else stars.Changed(after, displayed);
    }

    public void Dispose()
    {
        state.EnergyChanged -= Energy;
        state.StarsChanged -= Stars;
        if (ReferenceEquals(Current, this)) Current = null;
    }
}
