using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using Godot;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Potions;

namespace Sts2Agent;

internal sealed class PotionJournal : IDisposable
{
    public static PotionJournal? Current { get; private set; }
    private readonly bool subscribed;
    private readonly Player player;
    private readonly Action<string, object> record;
    private readonly Dictionary<PotionModel, int> slots = [];
    private readonly TurnEventBuffer buffer = ActionEventScope.Current?.Buffer ?? new();

    public PotionJournal(Player player, Action<string, object>? record = null)
    {
        this.player = player;
        this.record = record ?? ((type, potion) => buffer.Add(type, new() { ["potion"] = potion }));
        if (Current != null) return;
        Current = this;
        subscribed = true;
        foreach (var potion in player.Potions) Remember(potion);
        player.PotionProcured += Remember;
        player.UsedPotionRemoved += Used;
        player.PotionDiscarded += Discarded;
    }

    private void Remember(PotionModel potion)
    {
        int slot = player.GetPotionSlotIndex(potion);
        if (ReferenceEquals(PotionInspection.DisplayedAt(slot)?.Potion?.Model, potion))
            slots[potion] = slot;
    }
    private void Used(PotionModel potion) => Record("potion_used", potion);
    private void Discarded(PotionModel potion) => Record("potion_discarded", potion);
    private void Record(string type, PotionModel potion)
    {
        if (RunResourceJournal.Current is { TopBarVisible: false }) return;
        if (slots.Remove(potion, out int slot) && SlotVisible(slot)) record(type, PotionActions.Reference(potion, slot));
    }

    // Native removal can clear the image before notifying this journal. The known identity
    // comes from an earlier displayed icon; the holder must still be exposed.
    private static bool SlotVisible(int slot) => PotionInspection.ExposedAt(slot) != null;

    public void SampleVisibility()
    {
        if (RunResourceJournal.Current is { TopBarVisible: false }) slots.Clear();
        else
        {
            foreach (var potion in slots.Keys.ToArray())
                if (!ReferenceEquals(PotionInspection.DisplayedAt(slots[potion])?.Potion?.Model, potion)) slots.Remove(potion);
            foreach (var potion in player.Potions) Remember(potion);
        }
    }

    public object Result(string reason) => TransitionResult.Create(reason, buffer);

    public void Dispose()
    {
        if (!subscribed) return;
        player.PotionProcured -= Remember;
        player.UsedPotionRemoved -= Used;
        player.PotionDiscarded -= Discarded;
        if (ReferenceEquals(Current, this)) Current = null;
    }
}
