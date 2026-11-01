using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Orbs;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal sealed class OrbJournal : IDisposable
{
    internal sealed record Slot(NOrb Node, OrbModel? Model, string? Name);
    internal sealed record Change(OrbJournal Journal, Slot[] Slots);
    private sealed record PendingChange(TurnEventBuffer.Reservation Reservation, int Capacity,
        NOrb[] Entering, Dictionary<string, object?> Fields, NOrb? Channel = null)
    {
        // A newly created node can precede the first application of its From(Zero) tween.
        public ulong CreatedFrame { get; } = OrbCapture.FrameNumber;
    }
    public static OrbJournal? Current { get; private set; }
    private readonly CombatState combat;
    private readonly Player player;
    private readonly TurnEventBuffer buffer;
    private readonly EnglishText english = new();
    private readonly List<PendingChange> pending = [];

    public OrbJournal(CombatState combat, Player player, TurnEventBuffer buffer)
    {
        if (Current != null) throw new InvalidOperationException("Orbs are already being recorded.");
        this.combat = combat;
        this.player = player;
        this.buffer = buffer;
        Current = this;
    }

    private NCreature? Creature => ReferenceEquals(combat, CombatManager.Instance.DebugOnlyGetState())
        ? NCombatRoom.Instance?.GetCreatureNode(player.Creature) : null;
    private NOrb[]? Displayed => Creature is { } creature ? OrbInspection.DisplayedNodes(creature) : null;
    private object Target() => new { id = (int)(player.Creature.CombatId ?? 0), kind = "player",
        name = english.Name(player.Character.Title) };
    private bool Entering(NOrb slot) => pending.Any(change => ReferenceEquals(change.Channel, slot));
    private bool Readable(NOrb[] slots) => slots.All(slot => OrbInspection.SlotVisible(slot, Entering(slot)));
    public bool Pending => pending.Count > 0 || Creature is { } creature && Displayed is { } slots
        && (RewardInspection.Animating(creature.OrbManager!, "_curTween")
            || slots.Any(slot => RewardInspection.Animating(slot, "_curTween")));

    public Change? Before(NOrbManager manager)
    {
        SampleVisibility();
        if (Creature is not { } creature || !ReferenceEquals(creature.OrbManager, manager)
            || OrbInspection.DisplayedNodes(creature) is not { } slots || !Readable(slots)) return null;
        return new(this, slots.Select(slot => new Slot(slot, slot.Model,
            slot.Model == null || Entering(slot) ? null : english.Name(slot.Model.Title))).ToArray());
    }

    public void Channeled(Change change)
    {
        if (!ReferenceEquals(change.Journal, Current) || Displayed is not { } slots) return;
        foreach (var slot in slots.Where(slot => slot.Model != null && !change.Slots.Any(old => ReferenceEquals(old.Node, slot))))
        {
            string? name = english.Name(slot.Model!.Title);
            if (name == null || buffer.Reserve("orb_channeled") is not { } reservation) continue;
            pending.Add(new(reservation, slots.Length, [slot], Fields(name, Array.IndexOf(slots, slot)), slot));
        }
        SampleVisibility();
    }

    public void Removed(Change change)
    {
        if (!ReferenceEquals(change.Journal, Current) || Displayed is not { } slots) return;
        // Native slot removal starts at the back; an evoke removes its single bound UI node.
        for (int i = change.Slots.Length - 1; i >= 0; i--)
        {
            var old = change.Slots[i];
            if (old.Model != null && old.Name != null && !slots.Contains(old.Node))
                buffer.Add("orb_removed", Fields(old.Name, i));
        }
    }

    public void SlotsChanged(Change change)
    {
        if (!ReferenceEquals(change.Journal, Current) || Displayed is not { } slots) return;
        Removed(change);
        if (change.Slots.Length == slots.Length) return;
        var prior = pending.FirstOrDefault(change => change.Channel == null);
        if (prior != null)
        {
            prior.Fields["after"] = slots.Length;
            pending[pending.IndexOf(prior)] = prior with { Capacity = slots.Length };
        }
        else if (buffer.Reserve("orb_slots_changed") is { } reservation)
            pending.Add(new(reservation, slots.Length, [], new() { ["target"] = Target(),
                ["before"] = change.Slots.Length, ["after"] = slots.Length }));
        SampleVisibility();
    }

    public void Evoking(Player owner, OrbModel orb)
    {
        if (!ReferenceEquals(player, owner) || CombatManager.Instance.IsOverOrEnding
            || !owner.PlayerCombatState!.OrbQueue.Orbs.Contains(orb)) return;
        SampleVisibility();
        if (Creature is not { } creature || OrbInspection.DisplayedNodes(creature) is not { } slots || !Readable(slots)) return;
        int index = Array.FindIndex(slots, slot => ReferenceEquals(slot.Model, orb));
        if (index >= 0 && !Entering(slots[index]) && english.Name(orb.Title) is { } name)
            buffer.Add("orb_evoked", Fields(name, index));
    }

    private Dictionary<string, object?> Fields(string name, int index) => new() {
        ["target"] = Target(), ["orb"] = new { name }, ["slot_index"] = index };

    public void SampleVisibility()
    {
        if (pending.Count == 0) return;
        var slots = Displayed;
        var entering = pending.SelectMany(change => change.Entering).ToHashSet();
        if (slots == null || slots.Any(slot => !OrbInspection.SlotVisible(slot, entering.Contains(slot))))
        {
            pending.Clear();
            return;
        }
        bool visible = slots.All(slot => OrbInspection.SlotVisible(slot));
        foreach (var change in pending.ToArray())
        {
            if (change.Channel == null ? change.Capacity != slots.Length : !slots.Contains(change.Channel))
            {
                pending.Remove(change);
                continue;
            }
            if (!visible || OrbCapture.FrameNumber <= change.CreatedFrame) continue;
            if (change.Channel == null && Equals(change.Fields["before"], change.Fields["after"]))
            {
                pending.Remove(change);
                continue;
            }
            if (change.Channel != null) change.Fields["slot_index"] = Array.IndexOf(slots, change.Channel);
            change.Reservation.Publish(change.Fields);
            pending.Remove(change);
        }
    }

    public void Dispose()
    {
        pending.Clear();
        if (ReferenceEquals(Current, this)) Current = null;
    }
}
