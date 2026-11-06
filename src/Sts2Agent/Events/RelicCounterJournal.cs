using HarmonyLib;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Relics;

namespace Sts2Agent;

internal sealed class RelicCounterJournal : IDisposable
{
    public static RelicCounterJournal? Current { get; private set; }
    private readonly Player player;
    private readonly RelicCounterChanges<(RelicModel, NRelicInventoryHolder)> changes;
    private bool disposed;

    public static void Initialize() => new Harmony("sts2_agent.relic_counters").Patch(
        AccessTools.Method(typeof(NRelicInventoryHolder), "RefreshAmount"),
        postfix: new HarmonyMethod(typeof(RelicCounterJournal), nameof(Refreshed)));

    private static void Refreshed(NRelicInventoryHolder __instance)
    {
        if (NGame.IsMainThread()) Current?.Sample(__instance);
    }

    public RelicCounterJournal(Player player, TurnEventBuffer buffer)
    {
        if (Current != null) throw new InvalidOperationException("Relic counters are already being recorded.");
        this.player = player;
        changes = new(buffer);
        SampleVisibility();
        Current = this;
    }

    private NRelicInventoryHolder[] Displayed()
    {
        var holders = ReferenceEquals(player, RunContext.LocalPlayer)
            ? RelicInspection.DisplayedHolders()?.Where(holder => player.Relics.Contains(holder.Relic.Model)).ToArray() : null;
        holders ??= [];
        changes.ForgetExcept(holders.Select(holder => (holder.Relic.Model, holder)));
        return holders;
    }

    private void Read(NRelicInventoryHolder holder)
    {
        var value = RelicInspection.Static(holder);
        if (value.name is { Length: > 0 } name) changes.Sample((holder.Relic.Model, holder), name, value.counter);
    }

    private void Sample(NRelicInventoryHolder holder)
    {
        if (!disposed && Displayed().Contains(holder)) Read(holder);
    }

    public void SampleVisibility()
    {
        if (disposed) return;
        foreach (var holder in Displayed()) Read(holder);
    }

    public void Dispose()
    {
        disposed = true;
        changes.Clear();
        if (ReferenceEquals(Current, this)) Current = null;
    }
}
