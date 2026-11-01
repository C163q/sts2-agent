using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.Entities.Enchantments;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Enchantments;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.Models.Powers.Mocks;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class PlayFixture
{
    public static async Task Configure(string scenario, Player player)
    {
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        var state = player.PlayerCombatState!;
        await CardPileCmd.RemoveFromCombat(state.AllCards.ToArray());
        state.Energy = scenario == "energy" ? 0 : scenario == "x_cost" ? 2 : scenario == "energy_chain" ? 3 : 20;
        var cards = new List<CardModel>();
        void Add<T>() where T : CardModel => cards.Add(combat.CreateCard<T>(player));
        if (scenario == "anger") Add<Anger>();
        else if (scenario == "turbo") Add<Turbo>();
        else if (scenario == "blade_dance") Add<BladeDance>();
        else if (scenario == "pommel_strike") Add<PommelStrike>();
        else if (scenario == "bloodletting") Add<Bloodletting>();
        else if (scenario == "gather_light") Add<GatherLight>();
        else if (scenario.StartsWith("charge", StringComparison.Ordinal)) Add<Charge>();
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
        if (scenario == "choice_chain")
        {
            cards.Clear();
            for (int i = 0; i < 5; i++) Add<Discovery>();
            Add<DefendIronclad>(); Add<StrikeIronclad>();
        }
        if (scenario == "energy_chain")
        {
            cards.Clear();
            Add<Bash>(); Add<Dominate>(); Add<StrikeIronclad>(); Add<StrikeIronclad>(); Add<DefendIronclad>();
        }
        if (scenario == "card_names")
        {
            cards.Clear();
            Add<TrueGrit>(); Add<StrikeIronclad>(); Add<DefendIronclad>();
            foreach (var card in cards) { card.UpgradeInternal(); card.FinalizeUpgradeInternal(); }
            Add<StrikeIronclad>(); Add<DefendIronclad>();
        }
        if (scenario == "enchantments")
        {
            cards.Clear();
            Add<StrikeIronclad>(); Add<DefendIronclad>(); Add<StrikeIronclad>(); Add<StrikeIronclad>();
            CardCmd.Enchant<Sharp>(cards[0], 3);
            CardCmd.Enchant<Swift>(cards[1], 2)!.Status = EnchantmentStatus.Disabled;
            CardCmd.Enchant<Clone>(cards[2], 7);
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
        if (scenario is "stars" or "star_spend") cards[0].SetStarCostThisCombat(2);
        if (scenario == "star_spend") await PlayerCmd.SetStars(5, player);
        await CardPileCmd.AddGeneratedCardsToCombat(cards, PileType.Hand, player);
        int drawCount = scenario.StartsWith("charge", StringComparison.Ordinal) ? int.Parse(scenario[^1..])
            : scenario is "glimmer" or "card_logic" or "pommel_strike" ? 3 : 0;
        for (int i = 0; i < drawCount; i++)
        {
            var added = await CardPileCmd.AddGeneratedCardToCombat(combat.CreateCard<DefendIronclad>(player), PileType.Draw, player);
            if (scenario == "pommel_strike") CardCmd.PreviewCardPileAdd(added, 0.1f);
        }
        if (scenario == "pommel_strike")
        {
            // Prepare a visible starting count through native flights, not a label/model rewrite.
            var timer = System.Diagnostics.Stopwatch.StartNew();
            while (VisibleUi.Number(NCombatRoom.Instance!.Ui.DrawPile, "CountContainer/Count") != drawCount
                && timer.Elapsed < TimeSpan.FromSeconds(10)) await Cmd.Wait(0.1f);
            if (VisibleUi.Number(NCombatRoom.Instance!.Ui.DrawPile, "CountContainer/Count") != drawCount)
                throw new InvalidOperationException("The fixture draw pile did not finish its native preview.");
        }
        if (scenario is "preview_draw" or "preview_messy")
        {
            int count = scenario == "preview_messy" ? 7 : 1;
            var generated = await CardPileCmd.AddGeneratedCardsToCombat(
                Enumerable.Range(0, count).Select(_ => combat.CreateCard<Dazed>(player)), PileType.Draw, player);
            void PreviewOnBlock(int _, int __)
            {
                player.Creature.BlockChanged -= PreviewOnBlock;
                // Exercise both native combat preview layouts before their delayed pile flights.
                CardCmd.PreviewCardPileAdd(generated, 2.2f,
                    count > 5 ? CardPreviewStyle.MessyLayout : CardPreviewStyle.HorizontalLayout);
            }
            player.Creature.BlockChanged += PreviewOnBlock;
        }
        if (scenario is "victory" or "test_subject")
            foreach (var enemy in combat.Enemies) await CreatureCmd.SetCurrentHp(enemy, 1);
        if (scenario == "kill_chain") await CreatureCmd.SetCurrentHp(combat.Enemies.First(), 1);
        if (scenario == "delayed_ui")
        {
            void BlockChanged(int _, int __)
            {
                player.Creature.BlockChanged -= BlockChanged;
                // Exercise the native delayed health UI on an otherwise ordinary card action.
                NCombatRoom.Instance!.GetCreatureNode(player.Creature)!
                    .GetNode<NCreatureStateDisplay>("%HealthBar").AnimateIn(HealthBarAnimMode.SpawnedAtCombatStart);
            }
            player.Creature.BlockChanged += BlockChanged;
        }
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
