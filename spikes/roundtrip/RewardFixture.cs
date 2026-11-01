using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Rewards;
using MegaCrit.Sts2.Core.Entities.Gold;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Potions;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Rewards;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class RewardFixture
{
    public static Task? Pending { get; private set; }
    public static void Reset() => Pending = null;

    public static async Task Configure(string scenario, Player player, Func<Task> frame)
    {
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        var room = player.RunState.CurrentRoom as CombatRoom ?? throw new InvalidOperationException("Expected combat room.");
        RunManager.Instance.DebugOnlyGetState()!.ActFloor = 1;
        foreach (var potion in player.Potions.ToArray()) await PotionCmd.Discard(potion);
        if (scenario == "paels_wing") await RelicCmd.Obtain<PaelsWing>(player);
        if (scenario == "driftwood") await RelicCmd.Obtain<Driftwood>(player);
        if (scenario == "full")
            for (int i = 0; i < player.PotionSlots.Count; i++) await PotionCmd.TryToProcure<BlockPotion>(player);
        // An isolated fixture may replace the deck to make the pickup order observable without RNG assumptions.
        if (scenario is "card_first" or "relic_first")
        {
            await CardPileCmd.RemoveFromDeck(player.Deck.Cards.ToArray());
            await CardPileCmd.Add(player.RunState.CreateCard<DefendIronclad>(player), PileType.Deck);
        }
        if (scenario is "returned" or "escaped")
        {
            var enemy = combat.Enemies.First();
            var swipe = (SwipePower)ModelDb.Power<SwipePower>().ToMutable();
            await PowerCmd.Apply(new ThrowingPlayerChoiceContext(), swipe, enemy, 1, enemy, null);
            await swipe.Steal(player.PlayerCombatState!.AllCards.First(c => c.DeckVersion != null));
            var heist = (HeistPower)ModelDb.Power<HeistPower>().ToMutable();
            heist.Target = player.Creature;
            await PowerCmd.Apply(new ThrowingPlayerChoiceContext(), heist, enemy, 23, enemy, null);
            await PlayerCmd.LoseGold(23, player, GoldLossType.Stolen);
        }
        foreach (var enemy in combat.Enemies.ToArray())
            if (scenario == "escaped") await CreatureCmd.Escape(enemy);
            else await CreatureCmd.Kill(enemy);
        await CombatManager.Instance.CheckWinCondition();
        for (int i = 0; i < 600 && RewardInspection.Current == null; i++) await frame();
        if (RewardInspection.Current is not { } old) throw new InvalidOperationException("Fixture combat has no reward screen.");
        if (scenario is "returned" or "escaped")
        {
            for (int i = 0; i < 600 && !RewardInspection.Ready(old); i++) await frame();
            return;
        }
        RunManager.Instance.RewardsSetSynchronizer.SkipLocalRewardsSet();
        NRun.Instance!.GlobalUi.Overlays.Remove(old);
        var list = new List<Reward>();
        CardModel NewCard<T>() where T : CardModel => player.RunState.CreateCard<T>(player);
        CardReward Cards() => new(new CardModel[] { NewCard<Anger>(), NewCard<Inflame>(), NewCard<ShrugItOff>() },
            CardCreationSource.Encounter, player, CardCreationOptions.ForRoom(player, RoomType.Monster));
        if (scenario is "basic" or "full")
        {
            list.Add(new GoldReward(17, player));
            list.Add(new PotionReward(ModelDb.Potion<BlockPotion>().ToMutable(), player));
            list.Add(new RelicReward(ModelDb.Relic<Whetstone>().ToMutable(), player));
            var stolen = NewCard<StrikeIronclad>();
            stolen.UpgradeInternal(); stolen.FinalizeUpgradeInternal();
            var special = new SpecialCardReward(stolen, player);
            list.Add(special);
            list.Add(new GoldReward(23, player, wasGoldStolenBack: true));
            list.Add(Cards());
        }
        else if (scenario is "card_first" or "relic_first")
        {
            list.Add(new RelicReward(ModelDb.Relic<Whetstone>().ToMutable(), player));
            list.Add(Cards());
        }
        else if (scenario == "linked") list.Add(new LinkedRewardSet([
            new GoldReward(17, player), new PotionReward(ModelDb.Potion<BlockPotion>().ToMutable(), player)], player));
        else if (scenario == "nested") list.Add(new RelicReward(ModelDb.Relic<CallingBell>().ToMutable(), player));
        else if (scenario == "unsupported") list.Add(new RelicReward(ModelDb.Relic<Astrolabe>().ToMutable(), player));
        else if (scenario == "skip") { list.Add(new GoldReward(17, player)); list.Add(Cards()); }
        else if (scenario is "paels_wing" or "driftwood") { list.Add(Cards()); list.Add(Cards()); }
        else if (scenario != "empty") throw new InvalidOperationException("Unknown reward fixture.");
        var set = new RewardsSet(player).EmptyForRoom(room).WithCustomRewards(list);
        Pending = set.Offer();
        for (int i = 0; i < 600 && (RewardInspection.Current == null || !RewardInspection.Ready(RewardInspection.Current)); i++)
        {
            if (Pending.IsFaulted) await Pending;
            await frame();
        }
        if (Pending.IsFaulted) await Pending;
    }

    public static object Read(Player player) => new
    {
        gold = player.Gold,
        gold_proportion = (player.RunState.CurrentRoom as CombatRoom)?.GoldProportion,
        escaped_count = CombatManager.Instance.DebugOnlyGetState()?.EscapedCreatures.Count,
        deck = player.Deck.Cards.Select(c => new { name = EnglishCardText.Read(() => EnglishCardText.Plain(c.Title)),
            upgrades = c.CurrentUpgradeLevel }).ToArray(),
        relics = player.Relics.Select(r => r.Id.Entry).ToArray(),
        sacrifices = player.GetRelic<PaelsWing>()?.RewardsSacrificed,
        potions = player.PotionSlots.Select(p => p?.Id.Entry).ToArray(),
        preview_cards = NRun.Instance is { } run ? new Godot.Node[] { run.GlobalUi.CardPreviewContainer,
            run.GlobalUi.MessyCardPreviewContainer, run.GlobalUi.EventCardPreviewContainer, run.GlobalUi.GridCardPreviewContainer }
            .Sum(container => VisibleUi.Descendants<NCard>(container).Count(VisibleUi.Shown)) : 0,
        pending_fault = Pending?.IsFaulted
    };
}
