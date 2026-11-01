using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;

namespace Sts2Agent;

internal static class CompanionFixture
{
    public static async Task Configure(string scenario, Player player)
    {
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        await CardPileCmd.RemoveFromCombat(player.PlayerCombatState!.AllCards.ToArray());
        player.PlayerCombatState.Energy = 20;
        var cards = new List<CardModel>();
        void Add<T>() where T : CardModel => cards.Add(combat.CreateCard<T>(player));
        if (scenario == "companions_blade")
        {
            Add<WroughtInWar>(); Add<RefineBlade>(); Add<DefendRegent>();
            await ForgeCmd.Forge(5, player, null);
        }
        else
        {
            Add<Unleash>(); Add<Bodyguard>(); Add<Bodyguard>(); Add<DefendNecrobinder>();
        }
        foreach (var enemy in combat.Enemies)
        {
            await CreatureCmd.SetMaxHp(enemy, 300);
            await CreatureCmd.SetCurrentHp(enemy, 300);
        }
        await CardPileCmd.AddGeneratedCardsToCombat(cards, PileType.Hand, player);
    }
}
