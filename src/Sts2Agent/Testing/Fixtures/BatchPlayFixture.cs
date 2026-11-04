using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;

namespace Sts2Agent;

internal static class BatchPlayFixture
{
    public static async Task Configure(string mode, Player player)
    {
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        var cards = new List<CardModel>();
        CardModel Add<T>() where T : CardModel { var card = combat.CreateCard<T>(player); cards.Add(card); return card; }
        await PlayerCmd.SetEnergy(mode == "energy" ? 3 : mode == "partial" ? 1 : mode == "zero" ? 0 : 20, player);
        await PlayerCmd.SetStars(mode == "stars" ? 3 : 0, player);
        switch (mode)
        {
            case "energy": Add<StrikeIronclad>(); Add<Bash>(); Add<StrikeIronclad>(); Add<DefendIronclad>().SetToFreeThisTurn(); break;
            case "partial": Add<StrikeIronclad>(); Add<Bash>(); Add<DefendIronclad>().SetToFreeThisTurn(); break;
            case "zero": Add<StrikeIronclad>(); Add<DefendIronclad>(); break;
            case "stars": Add<StrikeIronclad>(); Add<DefendIronclad>().SetStarCostThisCombat(2);
                Add<DefendIronclad>().SetStarCostThisCombat(2); Add<DefendIronclad>(); break;
            case "target": Add<StrikeIronclad>(); Add<StrikeIronclad>(); Add<DefendIronclad>();
                await CreatureCmd.SetCurrentHp(combat.Enemies.First(), 1); break;
            case "random_exhaust": Add<TrueGrit>(); Add<DefendIronclad>(); Add<DefendIronclad>(); break;
            case "hand_exhaust": case "automatic_hand":
                var grit = Add<TrueGrit>(); grit.UpgradeInternal(); grit.FinalizeUpgradeInternal();
                Add<DefendIronclad>(); if (mode == "hand_exhaust") Add<DefendIronclad>(); break;
            case "choose_one": Add<StrikeIronclad>(); Add<Discovery>(); Add<DefendIronclad>(); Add<DefendIronclad>(); break;
            case "immediate_choice": Add<Discovery>(); Add<DefendIronclad>(); Add<DefendIronclad>(); break;
            case "combat_pile":
                Add<StrikeIronclad>(); Add<Headbutt>(); Add<DefendIronclad>(); Add<DefendIronclad>();
                await CardPileCmd.AddGeneratedCardsToCombat(new CardModel[] {
                    combat.CreateCard<StrikeIronclad>(player), combat.CreateCard<DefendIronclad>(player) }, PileType.Discard, player);
                break;
            case "victory": Add<Thunderclap>(); Add<DefendIronclad>(); Add<DefendIronclad>();
                foreach (var enemy in combat.Enemies) await CreatureCmd.SetCurrentHp(enemy, 1); break;
            case "death": Add<StrikeIronclad>(); Add<Offering>(); Add<DefendIronclad>(); Add<DefendIronclad>();
                await CreatureCmd.SetCurrentHp(player.Creature, 1); break;
            case "immediate_death": Add<Offering>(); Add<DefendIronclad>(); Add<DefendIronclad>();
                await CreatureCmd.SetCurrentHp(player.Creature, 1); break;
            default: throw new ArgumentException("Unknown batch fixture.");
        }
        await CardPileCmd.AddGeneratedCardsToCombat(cards, PileType.Hand, player);
    }
}
