using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.Models.Powers.Mocks;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class PlayFixture
{
    public static async Task Configure(string scenario, Player player)
    {
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        var state = player.PlayerCombatState!;
        await CardPileCmd.RemoveFromCombat(state.AllCards.ToArray());
        state.Energy = scenario == "energy" ? 0 : scenario == "x_cost" ? 2 : 20;
        var cards = new List<CardModel>();
        void Add<T>() where T : CardModel => cards.Add(combat.CreateCard<T>(player));
        if (scenario.StartsWith("charge", StringComparison.Ordinal)) Add<Charge>();
        else if (scenario == "discovery") Add<Discovery>();
        else if (scenario == "glimmer") Add<Glimmer>();
        else if (scenario is "random" or "random_empty") Add<SwordBoomerang>();
        else if (scenario is "aoe" or "victory") Add<Thunderclap>();
        else if (scenario == "death") Add<Offering>();
        else if (scenario.StartsWith("armaments", StringComparison.Ordinal)) Add<Armaments>();
        else if (scenario == "x_cost") Add<Whirlwind>();
        else if (scenario == "card_logic") Add<GrandFinale>();
        else if (scenario == "unplayable") Add<Dazed>();
        else if (scenario == "ally") Add<Mimic>();
        else if (scenario == "multi_hit") Add<TwinStrike>();
        else Add<StrikeIronclad>();
        Add<DefendIronclad>();
        Add<StrikeIronclad>();
        if (scenario == "card_names")
        {
            cards.Clear();
            Add<TrueGrit>(); Add<StrikeIronclad>(); Add<DefendIronclad>();
            foreach (var card in cards) { card.UpgradeInternal(); card.FinalizeUpgradeInternal(); }
            Add<StrikeIronclad>(); Add<DefendIronclad>();
        }
        if (scenario == "armaments_free") cards[0].SetToFreeThisTurn();
        if (scenario == "armaments_filtered")
        {
            Add<DefendIronclad>();
            cards[^1].UpgradeInternal(); cards[^1].FinalizeUpgradeInternal();
        }
        if (scenario == "armaments_upgraded") { cards[0].UpgradeInternal(); cards[0].FinalizeUpgradeInternal(); }
        if (scenario is "armaments_one" or "armaments_none")
            foreach (var card in cards.Skip(scenario == "armaments_one" ? 2 : 1))
            { card.UpgradeInternal(); card.FinalizeUpgradeInternal(); }
        if (scenario is "test_subject" or "unhittable") { Add<SwordBoomerang>(); Add<Thunderclap>(); }
        if (scenario == "hook")
        {
            cards.Clear();
            for (int i = 0; i < 4; i++) Add<DefendIronclad>();
            Add<Normality>();
        }
        if (scenario == "stars") cards[0].SetStarCostThisCombat(2);
        await CardPileCmd.AddGeneratedCardsToCombat(cards, PileType.Hand, player);
        int drawCount = scenario.StartsWith("charge", StringComparison.Ordinal) ? int.Parse(scenario[^1..])
            : scenario is "glimmer" or "card_logic" ? 3 : 0;
        for (int i = 0; i < drawCount; i++)
            await CardPileCmd.AddGeneratedCardToCombat(combat.CreateCard<DefendIronclad>(player), PileType.Draw, player);
        if (scenario is "victory" or "test_subject")
            foreach (var enemy in combat.Enemies) await CreatureCmd.SetCurrentHp(enemy, 1);
        if (scenario is "death" or "thorns_death") await CreatureCmd.SetCurrentHp(player.Creature, 1);
        if (scenario == "thorns_death")
            await PowerCmd.Apply<ThornsPower>(new ThrowingPlayerChoiceContext(), combat.Enemies.First(), 3, player.Creature, null);
        if (scenario == "unhittable")
            await PowerCmd.Apply<MockUnhittablePower>(new ThrowingPlayerChoiceContext(), combat.Enemies.First(), 1, player.Creature, null);
        if (scenario is "no_target" or "random_empty")
            foreach (var enemy in combat.Enemies) await CreatureCmd.Kill(enemy);
        if (scenario == "cancel")
        {
            void Changed(GameAction action)
            {
                if (action is not PlayCardAction) return;
                RunManager.Instance.ActionQueueSet.ActionEnqueued -= Changed;
                cards[0].SetStarCostThisCombat(999);
            }
            RunManager.Instance.ActionQueueSet.ActionEnqueued += Changed;
        }
    }

    public static object Read(Player player) => new
    {
        rng_counter = player.RunState.Rng.CombatTargets.Counter,
        energy = player.PlayerCombatState!.Energy,
        in_card_play = NPlayerHand.Instance!.InCardPlay,
        targeting = NTargetManager.Instance.IsInSelection,
        queue_empty = RunManager.Instance.ActionQueueSet.IsEmpty
    };
}
