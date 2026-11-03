using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Screens;

namespace Sts2Agent;

internal sealed class DeckInspection
{
    private readonly CardIdentityMap<CardModel> ids = new();
    private object? run;

    public object Read(NDeckViewScreen screen, Player player, string snapshotId)
    {
        if (!ReferenceEquals(run, player.RunState))
        {
            run = player.RunState;
            ids.Clear();
        }
        bool upgrades = DeckView.Grid(screen).IsShowingUpgrades;
        return EnglishCardText.Read(() => new
        {
            snapshot_id = snapshotId,
            view_upgrades = upgrades, sort = DeckView.Sorting(screen),
            deck = DeckView.Cards(screen).Select(card => BrowsedCard.Read(card, "deck:" + ids.Get(card),
                PileType.Deck, upgrades, full: true, appearance: true)).ToArray()
        });
    }
}
