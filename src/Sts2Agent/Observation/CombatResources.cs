using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal sealed record CombatResources(int? Energy, int? Maximum, int? Stars,
    int? DrawCount, int? DiscardCount, int? ExhaustCount)
{
    public static CombatResources Read()
    {
        if (CombatObservation.Status() != "visible") return new(null, null, null, null, null, null);
        var ui = NCombatRoom.Instance!.Ui;
        var pair = CombatObservation.Pair(VisibleUi.Descendants<NEnergyCounter>(ui.EnergyCounterContainer)
            .Select(counter => VisibleUi.Text(counter, "Label")).FirstOrDefault(text => text != null));
        return new(pair.current, pair.maximum, VisibleUi.Descendants<NStarCounter>(ui).Where(VisibleUi.OnScreen)
            .Select(counter => VisibleUi.Number(counter, "%CountLabel")).FirstOrDefault(),
            VisibleUi.Number(ui.DrawPile, "CountContainer/Count"),
            VisibleUi.Number(ui.DiscardPile, "CountContainer/Count"),
            VisibleUi.Number(ui.ExhaustPile, "CountContainer/Count"));
    }
}
