using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;

namespace Sts2Agent;

internal sealed class PotionJournal : IDisposable
{
    private readonly Player player;
    private readonly Action<string, object> record;
    private readonly Dictionary<PotionModel, int> slots = [];
    private readonly TurnEventBuffer buffer = new();

    public PotionJournal(Player player, Action<string, object>? record = null)
    {
        this.player = player;
        this.record = record ?? ((type, potion) => buffer.Add(type, new() { ["potion"] = potion }));
        foreach (var potion in player.Potions) Remember(potion);
        player.PotionProcured += Remember;
        player.UsedPotionRemoved += Used;
        player.PotionDiscarded += Discarded;
    }

    private void Remember(PotionModel potion)
    {
        if (PotionInspection.VisibleHolders()?.Any(holder => ReferenceEquals(holder.Potion?.Model, potion)) == true)
            slots[potion] = player.GetPotionSlotIndex(potion);
    }
    private void Used(PotionModel potion) => Record("potion_used", potion);
    private void Discarded(PotionModel potion) => Record("potion_discarded", potion);
    private void Record(string type, PotionModel potion)
    {
        if (slots.TryGetValue(potion, out int slot) && slot >= 0) record(type, PotionActions.Reference(potion, slot));
    }

    public object Result(string reason) => new { stop_reason = reason,
        complete = !buffer.Truncated && reason is not ("timeout" or "interrupted"), events = buffer.Events };

    public void Dispose()
    {
        player.PotionProcured -= Remember;
        player.UsedPotionRemoved -= Used;
        player.PotionDiscarded -= Discarded;
    }
}
