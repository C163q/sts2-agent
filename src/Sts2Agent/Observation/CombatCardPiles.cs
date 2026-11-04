using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class CombatCardPiles
{
    public static bool Visible(PileType pile)
    {
        var ui = NCombatRoom.Instance?.Ui;
        return pile switch
        {
            PileType.Hand => VisibleUi.Shown(ui?.Hand),
            PileType.Play => VisibleUi.Shown(ui?.PlayContainer),
            PileType.Draw => VisibleUi.OnScreen(ui?.DrawPile),
            PileType.Discard => VisibleUi.OnScreen(ui?.DiscardPile),
            PileType.Exhaust => VisibleUi.OnScreen(ui?.ExhaustPile),
            PileType.Deck => VisibleUi.OnScreen(NRun.Instance?.GlobalUi.TopBar),
            _ => false
        };
    }

    public static int? Count(PileType pile)
    {
        var ui = NCombatRoom.Instance?.Ui;
        var resources = CombatResources.Read();
        return pile switch
        {
            PileType.Draw => resources.DrawCount,
            PileType.Discard => resources.DiscardCount,
            PileType.Exhaust => resources.ExhaustCount,
            PileType.Hand when ui != null => CombatObservation.HandCards(ui.Hand).Count(),
            PileType.Play when ui != null => VisibleUi.Descendants<NCard>(ui.PlayContainer).Count(CombatObservation.CardVisible),
            _ => null
        };
    }
}
