using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Enchantments;

namespace Sts2Agent;

internal static class PermanentCardFixture
{
    public static async Task Configure(string scenario, Player player)
    {
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        var genetic = player.RunState.CreateCard<GeneticAlgorithm>(player);
        var attack = player.RunState.CreateCard<StrikeIronclad>(player);
        var defend = player.RunState.CreateCard<DefendIronclad>(player);
        var bash = player.RunState.CreateCard<Bash>(player);
        CardModel[] originals = [genetic, attack, defend, bash];
        foreach (var card in originals) await CardPileCmd.Add(card, PileType.Deck);
        if (scenario == "permanent_enchant") CardCmd.Enchant<Sharp>(attack, 3);
        // Use the native deck population to establish real combat-copy/DeckVersion bindings.
        player.PopulateCombatState(player.RunState.Rng.Shuffle, combat);
        var copies = player.PlayerCombatState!.AllCards.Where(c => c.DeckVersion != null && originals.Contains(c.DeckVersion)).ToArray();
        await CardPileCmd.RemoveFromCombat(player.PlayerCombatState.AllCards.Except(copies).ToArray());
        foreach (var card in copies) await CardPileCmd.Add(card, PileType.Hand);
        if (scenario is "permanent_cost" or "permanent_enchant")
        {
            var attackCopy = copies.Single(c => ReferenceEquals(c.DeckVersion, attack));
            void Change(int _, int __)
            {
                player.Creature.BlockChanged -= Change;
                if (scenario == "permanent_cost")
                {
                    attack.EnergyCost.SetCustomBaseCost(0);
                    attackCopy.EnergyCost.SetCustomBaseCost(0);
                }
                else
                {
                    attack.Enchantment!.Amount = 5;
                    attackCopy.Enchantment!.Amount = 5;
                }
            }
            player.Creature.BlockChanged += Change;
        }
    }
}
