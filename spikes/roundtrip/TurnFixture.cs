using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Powers;

namespace Sts2Agent;

internal static class TurnFixture
{
    public static async Task Configure(string scenario, Player player)
    {
        var choice = new ThrowingPlayerChoiceContext();
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        if (scenario == "normal") return;
        if (scenario is "wither" or "wither_death")
        {
            await CardPileCmd.AddGeneratedCardToCombat(combat.CreateCard<Wither>(player), PileType.Hand, player);
            if (scenario == "wither_death") await CreatureCmd.SetCurrentHp(player.Creature, 1);
        }
        else if (scenario == "enemy_death") await CreatureCmd.SetCurrentHp(player.Creature, 1);
        else if (scenario == "tyranny") await PowerCmd.Apply<TyrannyPower>(choice, player.Creature, 1, player.Creature, null);
        else if (scenario == "retain_choice") await PowerCmd.Apply<WellLaidPlansPower>(choice, player.Creature, 1, player.Creature, null);
        else if (scenario == "boulder") await PowerCmd.Apply<RollingBoulderPower>(choice, player.Creature, 999, player.Creature, null);
        else if (scenario == "doom")
        {
            foreach (var enemy in combat.Enemies.ToArray())
                await PowerCmd.Apply<DoomPower>(choice, enemy, 999, player.Creature, null);
        }
        else if (scenario == "stampede")
        {
            await CardPileCmd.RemoveFromCombat(player.PlayerCombatState!.Hand.Cards.ToArray());
            await CardPileCmd.AddGeneratedCardToCombat(combat.CreateCard<Thunderclap>(player), PileType.Hand, player);
            foreach (var enemy in combat.Enemies.ToArray()) await CreatureCmd.SetCurrentHp(enemy, 1);
            await PowerCmd.Apply<StampedePower>(choice, player.Creature, 1, player.Creature, null);
        }
        else if (scenario == "revive")
        {
            var enemy = combat.Enemies.First();
            await PowerCmd.Apply<DoomPower>(choice, enemy, 999, player.Creature, null);
        }
        else if (scenario == "blocked") await CreatureCmd.GainBlock(player.Creature, 50, MegaCrit.Sts2.Core.ValueProps.ValueProp.Unpowered, null);
        else if (scenario == "hellraiser")
        {
            await PowerCmd.Apply<HellraiserPower>(choice, player.Creature, 1, player.Creature, null);
            await PowerCmd.Apply<StrengthPower>(choice, player.Creature, -999, player.Creature, null);
            await CardPileCmd.RemoveFromCombat(player.PlayerCombatState!.DrawPile.Cards.ToArray());
            await CardPileCmd.AddGeneratedCardToCombat(combat.CreateCard<StrikeIronclad>(player), PileType.Draw, player);
        }
        else if (scenario == "exhaust_block")
        {
            await CardPileCmd.AddGeneratedCardToCombat(combat.CreateCard<Dazed>(player), PileType.Hand, player);
            await PowerCmd.Apply<FeelNoPainPower>(choice, player.Creature, 3, player.Creature, null);
        }
        else if (scenario == "hidden_hp")
        {
            var enemy = combat.Enemies.First();
            enemy.HpDisplay = HpDisplay.InfiniteWithoutNumbers;
            await CreatureCmd.SetCurrentHp(enemy, enemy.CurrentHp - 1);
            await PowerCmd.Apply<DoomPower>(choice, enemy, 999, player.Creature, null);
        }
        else throw new ArgumentException("Unknown end-turn test scenario.");
    }
}
