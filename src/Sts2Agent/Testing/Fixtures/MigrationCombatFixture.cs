using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Relics;

namespace Sts2Agent;

internal static class MigrationCombatFixture
{
    public static async Task Configure(string scenario, Player player)
    {
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        await CardPileCmd.RemoveFromCombat(player.PlayerCombatState!.AllCards.ToArray());
        await PlayerCmd.SetEnergy(20, player);
        foreach (var enemy in combat.Enemies)
        {
            await CreatureCmd.SetMaxHp(enemy, 100);
            await CreatureCmd.Heal(enemy, 100);
        }
        CardModel? subject = scenario switch
        {
            "outbreak" => combat.CreateCard<Outbreak>(player),
            "well_laid_plans" => combat.CreateCard<WellLaidPlans>(player),
            "expertise" => combat.CreateCard<Expertise>(player),
            "toasty_mittens" => null,
            _ => throw new ArgumentException("Unknown migration combat scenario.")
        };
        if (subject != null) await CardPileCmd.AddGeneratedCardToCombat(subject, PileType.Hand, player);
        await CardPileCmd.AddGeneratedCardsToCombat(new CardModel[] {
            combat.CreateCard<StrikeIronclad>(player), combat.CreateCard<DefendIronclad>(player) }, PileType.Hand, player);
        await CardPileCmd.AddGeneratedCardsToCombat(Enumerable.Range(0, 20)
            .Select(_ => combat.CreateCard<DefendIronclad>(player)), PileType.Draw, player);
        if (scenario == "toasty_mittens") await RelicCmd.Obtain<ToastyMittens>(player);
    }
}
