using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Events;
using MegaCrit.Sts2.Core.Models.Potions;
using MegaCrit.Sts2.Core.Models.Powers.Mocks;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Rewards;
using MegaCrit.Sts2.Core.Rewards;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class PotionFixture
{
    public static async Task Configure(string scenario, Player player)
    {
        foreach (var potion in player.Potions.ToArray()) await PotionCmd.Discard(potion);
        if (scenario.StartsWith("noncombat", StringComparison.Ordinal) || scenario.StartsWith("merchant", StringComparison.Ordinal))
        {
            if (scenario == "noncombat_shop" || scenario.StartsWith("merchant", StringComparison.Ordinal))
                await RunManager.Instance.EnterRoomDebug(RoomType.Shop, showTransition: false);
            else if (scenario is "noncombat_rest" or "noncombat_map") await RunManager.Instance.EnterRoomDebug(RoomType.RestSite, showTransition: false);
            else await RunManager.Instance.EnterRoomDebug(RoomType.Event, model: ModelDb.Event<BrainLeech>(), showTransition: false);
            if (scenario == "noncombat_map") NRun.Instance!.GlobalUi.MapScreen.Open();
            if (scenario == "merchant_map") NRun.Instance!.GlobalUi.MapScreen.Open();
            if (scenario == "merchant_inventory") NMerchantRoom.Instance!.OpenInventory();
        }
        if (scenario.StartsWith("noncombat", StringComparison.Ordinal) || scenario == "fruit_combat")
        {
            await CreatureCmd.SetCurrentHp(player.Creature, 40);
            await PotionCmd.TryToProcure<FruitJuice>(player);
            await PotionCmd.TryToProcure<BloodPotion>(player);
            await PotionCmd.TryToProcure<BlockPotion>(player);
        }
        else
        {
            PotionModel primary = scenario switch
            {
                "skill" or "inspection" => ModelDb.Potion<SkillPotion>(), "attack" => ModelDb.Potion<AttackPotion>(),
                "power" => ModelDb.Potion<PowerPotion>(), "colorless" => ModelDb.Potion<ColorlessPotion>(),
                "memories" => ModelDb.Potion<LiquidMemories>(), "gamblers" => ModelDb.Potion<GamblersBrew>(),
                "merchant" or "merchant_map" or "merchant_inventory" or "death" or "fairy_rescue" => ModelDb.Potion<FoulPotion>(), "entropic" => ModelDb.Potion<EntropicBrew>(),
                "aoe" or "victory" => ModelDb.Potion<ExplosiveAmpoule>(), _ => ModelDb.Potion<FirePotion>()
            };
            await PotionCmd.TryToProcure(primary.ToMutable(), player);
            if (scenario != "entropic")
            {
                await PotionCmd.TryToProcure<BlockPotion>(player);
                if (scenario == "inspection") await PotionCmd.TryToProcure<BlockPotion>(player);
                else await PotionCmd.TryToProcure<FairyInABottle>(player);
            }
        }
        if (scenario == "memories")
            for (int i = 0; i < 3; i++)
                await CardPileCmd.AddGeneratedCardToCombat(player.Creature.CombatState!.CreateCard<DefendIronclad>(player), PileType.Discard, player);
        if (scenario == "victory")
            foreach (var enemy in player.Creature.CombatState!.Enemies) await CreatureCmd.SetCurrentHp(enemy, 1);
        if (scenario == "death")
        {
            await PotionCmd.Discard(player.PotionSlots[2]!);
            await CreatureCmd.SetCurrentHp(player.Creature, 1);
        }
        if (scenario == "fairy_rescue") await CreatureCmd.SetCurrentHp(player.Creature, 1);
        if (scenario == "noncombat_reward")
            SelectionFixture.Pending = new RewardsSet(player).WithCustomRewards([
                new PotionReward(ModelDb.Potion<BlockPotion>().ToMutable(), player)]).Offer();
        if (scenario == "blocked") player.CanRemovePotions = false;
        if (scenario == "unhittable")
            await PowerCmd.Apply<MockUnhittablePower>(new ThrowingPlayerChoiceContext(), player.Creature.CombatState!.Enemies.First(), 1, player.Creature, null);
        if (scenario == "cancel")
        {
            void Enqueued(GameAction action)
            {
                if (action is not UsePotionAction) return;
                RunManager.Instance.ActionQueueSet.ActionEnqueued -= Enqueued;
                player.PotionSlots[0]!.Discard();
            }
            RunManager.Instance.ActionQueueSet.ActionEnqueued += Enqueued;
        }
    }

    public static async Task Replace(Player player)
    {
        var potion = player.PotionSlots[0]!.CanonicalInstance.ToMutable();
        await PotionCmd.Discard(player.PotionSlots[0]!);
        await PotionCmd.TryToProcure(potion, player, 0);
    }

    public static object Read(Player player)
    {
        var merchant = player.Potions.OfType<FoulPotion>().FirstOrDefault()?.Owner.RunState.CurrentRoom is { } room
            ? FoulPotion.GetFoulPotionMerchantTarget(room).button : null;
        return new
        {
            rng_counter = player.RunState.Rng.CombatTargets.Counter,
            targeting = NTargetManager.Instance.IsInSelection,
            queue_empty = RunManager.Instance.ActionQueueSet.IsEmpty,
            slots = player.PotionSlots.Select(p => p?.Id.Entry).ToArray(),
            reward_visible = NRun.Instance?.GlobalUi.Overlays.Peek() is NRewardsScreen rewards
                && VisibleUi.Shown(rewards) && VisibleUi.Descendants<NRewardButton>(rewards).Any(VisibleUi.OnScreen),
            merchant = merchant == null ? null : new { shown = VisibleUi.Shown(merchant), on_screen = VisibleUi.OnScreen(merchant),
                visible = merchant.IsVisibleInTree(), alpha = merchant.Modulate.A, self_alpha = merchant.SelfModulate.A,
                bounds = merchant.GetGlobalRect().ToString(), size = merchant.Size.ToString() }
        };
    }
}
