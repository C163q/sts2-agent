using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Screens;

namespace Sts2Agent;

internal sealed class DeckInspection
{
    internal sealed record View(string? snapshot_id, bool view_upgrades, DeckView.Sort sort,
        Dictionary<string, object?>[] deck);
    private readonly CardIdentityMap<CardModel> ids = new();
    private object? run;

    public View Read(NDeckViewScreen screen, Player player, string? snapshotId = null, bool full = true)
    {
        if (!ReferenceEquals(run, player.RunState))
        {
            run = player.RunState;
            ids.Clear();
        }
        bool upgrades = DeckView.Grid(screen).IsShowingUpgrades;
        return EnglishCardText.Read(() => new View(snapshotId, upgrades, DeckView.Sorting(screen),
            DeckView.Cards(screen).Select(card => BrowsedCard.Read(card, "deck:" + ids.Get(card),
                PileType.Deck, upgrades, full, appearance: true)).ToArray()));
    }
}
