using Godot;
using MegaCrit.Sts2.Core.CardSelection;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Events;
using MegaCrit.Sts2.Core.Models.Enchantments;
using MegaCrit.Sts2.Core.Entities.Enchantments;
using MegaCrit.Sts2.Core.Models.Monsters;
using MegaCrit.Sts2.Core.Models.Potions;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.Models.Encounters;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Rewards;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class SelectionFixture
{
    public static Task? Pending { get; set; }

    public static async Task Configure(string scenario, Player player)
    {
        if (scenario == "paradox") return;
        if (scenario == "tyranny") { await TurnFixture.Configure("tyranny", player); return; }
        if (scenario is "optional_hand_zero" or "optional_hand_one") { await PlayFixture.Configure("purity", player); return; }
        if (scenario.StartsWith("potion", StringComparison.Ordinal))
        {
            await PotionCmd.TryToProcure<SkillPotion>(player);
            RunManager.Instance.ActionQueueSynchronizer.RequestEnqueue(new UsePotionAction(player.Potions.OfType<SkillPotion>().First(), null, true));
            return;
        }
        if (scenario == "grid_two")
        {
            var room = (EventRoom)await RunManager.Instance.EnterRoomDebug(RoomType.Event, model: ModelDb.Event<RoomFullOfCheese>(), showTransition: false);
            var model = room.LocalMutableEvent;
            Pending = (Task)HarmonyLib.AccessTools.Method(typeof(RoomFullOfCheese), "Gorge").Invoke(model, null)!;
        }
        else if (scenario == "grid_one" || scenario.StartsWith("reward", StringComparison.Ordinal))
        {
            var room = (EventRoom)await RunManager.Instance.EnterRoomDebug(RoomType.Event, model: ModelDb.Event<BrainLeech>(), showTransition: false);
            var model = room.LocalMutableEvent;
            Pending = scenario == "grid_one"
                ? (Task)HarmonyLib.AccessTools.Method(typeof(BrainLeech), "ShareKnowledge").Invoke(model, null)!
                : Reward(model);
        }
        else if (scenario == "combat_entry")
        {
            await RunManager.Instance.EnterRoomDebug(RoomType.Event, model: ModelDb.Event<BrainLeech>(), showTransition: false);
            Pending = ChooseThenFight(player);
        }
        else if (scenario == "upgrade_multi")
        {
            await RunManager.Instance.EnterRoomDebug(RoomType.Event, model: ModelDb.Event<BrainLeech>(), showTransition: false);
            Pending = UpgradeMultiple(player);
        }
        else if (scenario == "deck")
        {
            await RunManager.Instance.EnterRoomDebug(RoomType.Event, model: ModelDb.Event<BrainLeech>(), showTransition: false);
            Pending = CardSelectCmd.FromDeckForRemoval(player, new CardSelectorPrefs(CardSelectorPrefs.RemoveSelectionPrompt, 1) { Cancelable = true });
        }
        else if (scenario is "forced_two" or "chain" or "unsupported_next")
            Pending = Choose(player, scenario == "chain" ? 2 : 1, scenario == "unsupported_next");
        else if (scenario == "knowledge")
        {
            var monster = MegaCrit.Sts2.Core.Combat.CombatManager.Instance.DebugOnlyGetState()!.Enemies
                .Select(enemy => enemy.Monster).OfType<KnowledgeDemon>().Single();
            Pending = (Task)HarmonyLib.AccessTools.Method(typeof(KnowledgeDemon), "ChooseCurse").Invoke(monster, [player.Creature])!;
        }
        else if (scenario == "combat_pile")
        {
            await PowerCmd.Apply<CorruptionPower>(new ThrowingPlayerChoiceContext(), player.Creature, 1, player.Creature, null);
            Pending = CardSelectCmd.FromCombatPile(new BlockingPlayerChoiceContext(), PileType.Draw.GetPile(player), player,
                new CardSelectorPrefs(CardSelectorPrefs.ExhaustSelectionPrompt, 1), card => card.Type == CardType.Skill);
        }
        else if (scenario == "upgrade_enchantments")
        {
            await RunManager.Instance.EnterRoomDebug(RoomType.Event, model: ModelDb.Event<BrainLeech>(), showTransition: false);
            while (player.Deck.Cards.Count < 40)
                await CardPileCmd.Add(player.Deck.Cards.Count == 39 ? player.RunState.CreateCard<BodySlam>(player)
                    : player.Deck.Cards.Count % 2 == 0 ? (CardModel)player.RunState.CreateCard<StrikeIronclad>(player)
                    : player.RunState.CreateCard<DefendIronclad>(player), PileType.Deck, skipVisuals: true);
            player.Deck.InvokeCardAddFinished();
            var attacks = player.Deck.Cards.Where(card => card is StrikeIronclad).ToArray();
            var skills = player.Deck.Cards.Where(card => card is DefendIronclad).ToArray();
            foreach (int offset in new[] { 0, attacks.Length - 2 })
            {
                CardCmd.Enchant<Sharp>(attacks[offset], 3);
                CardCmd.Enchant<Clone>(attacks[offset + 1], 7);
            }
            foreach (int offset in new[] { 0, skills.Length - 2 })
            {
                CardCmd.Enchant<Swift>(skills[offset], 2)!.Status = EnchantmentStatus.Disabled;
                CardCmd.Enchant<Spiral>(skills[offset + 1], 1);
            }
            Pending = CardSelectCmd.FromDeckForUpgrade(player,
                new CardSelectorPrefs(CardSelectorPrefs.UpgradeSelectionPrompt, 1) { Cancelable = true });
        }
        else if (scenario == "grid_enchantments")
        {
            var cards = Enumerable.Range(0, 40).Select(i => i % 2 == 0
                ? (CardModel)player.RunState.CreateCard<StrikeIronclad>(player)
                : player.RunState.CreateCard<DefendIronclad>(player)).ToArray();
            foreach (int offset in new[] { 0, 36 })
            {
                CardCmd.Enchant<Sharp>(cards[offset], 3);
                CardCmd.Enchant<Swift>(cards[offset + 1], 2)!.Status = EnchantmentStatus.Disabled;
                CardCmd.Enchant<Clone>(cards[offset + 2], 7);
                CardCmd.Enchant<Spiral>(cards[offset + 3], 1);
            }
            Pending = CardSelectCmd.FromSimpleGrid(new BlockingPlayerChoiceContext(), cards, player,
                new CardSelectorPrefs(CardSelectorPrefs.ExhaustSelectionPrompt, 2));
        }
        else if (scenario is "grid_scroll" or "scroll_race" or "grid_manual")
        {
            var cards = Enumerable.Range(0, 40).Select(_ => (CardModel)player.RunState.CreateCard<DefendIronclad>(player)).ToArray();
            Pending = CardSelectCmd.FromSimpleGrid(new BlockingPlayerChoiceContext(), cards, player,
                new CardSelectorPrefs(CardSelectorPrefs.ExhaustSelectionPrompt, scenario is "scroll_race" or "grid_manual" ? 2 : 1)
                    { RequireManualConfirmation = scenario == "grid_manual" });
        }
        else throw new ArgumentException("Unknown card selection test scenario.");
    }

    private static async Task ChooseThenFight(Player player)
    {
        CardModel[] cards = [player.RunState.CreateCard<DefendIronclad>(player), player.RunState.CreateCard<StrikeIronclad>(player)];
        await CardSelectCmd.FromChooseACardScreen(new BlockingPlayerChoiceContext(), cards, player);
        await RunManager.Instance.EnterRoomDebug(RoomType.Monster, model: ModelDb.Encounter<SlimesWeak>().ToMutable(), showTransition: false);
    }

    private static async Task UpgradeMultiple(Player player)
    {
        var cards = await CardSelectCmd.FromDeckForUpgrade(player,
            new CardSelectorPrefs(CardSelectorPrefs.UpgradeSelectionPrompt, 2));
        foreach (var card in cards) CardCmd.Upgrade(card);
    }

    private static async Task Choose(Player player, int count, bool upgradeAfter = false)
    {
        CardModel[] cards = [player.RunState.CreateCard<DefendIronclad>(player), player.RunState.CreateCard<StrikeIronclad>(player)];
        for (int i = 0; i < count; i++)
            await CardSelectCmd.FromChooseACardScreen(new BlockingPlayerChoiceContext(), cards, player);
        if (upgradeAfter)
            await CardSelectCmd.FromDeckForUpgrade(player, new CardSelectorPrefs(CardSelectorPrefs.UpgradeSelectionPrompt, 1));
    }

    public static async Task<object> CheckScrollRace(Func<Task> frame)
    {
        var selection = CardSelection.Current!;
        DateTime deadline = DateTime.UtcNow.AddSeconds(5);
        while (!selection.CanSelect && DateTime.UtcNow < deadline) await frame();
        var first = selection.Cards.First();
        var target = selection.Cards.Last();
        bool changed = false, rejected = false;
        async Task Frame()
        {
            await frame();
            await frame();
            if (changed) return;
            changed = true;
            var holder = selection.Grid!.CurrentlyDisplayedCardHolders.First(holder => CardSelection.Clickable(holder)
                && !ReferenceEquals(holder.CardModel, target));
            first = holder.CardModel!;
            holder.EmitSignal(MegaCrit.Sts2.Core.Nodes.Cards.Holders.NCardHolder.SignalName.Pressed, holder);
        }
        try { await SelectionActions.Click(selection, target, Frame); }
        catch (InvalidOperationException) { rejected = true; }
        if (!changed || !rejected || CardSelection.Current == null || !selection.Selected.SequenceEqual([first]))
            throw new InvalidOperationException($"Concurrent input must be rejected: changed={changed}, rejected={rejected}, pending={CardSelection.Current != null}, selected={selection.Selected.Length}.");
        return new { passed = true };
    }

    private static async Task Reward(EventModel model)
    {
        Task task = (Task)HarmonyLib.AccessTools.Method(typeof(BrainLeech), "Rip").Invoke(model, null)!;
        DateTime deadline = DateTime.UtcNow.AddSeconds(15);
        NRewardButton? button;
        do
        {
            await NGame.Instance!.ToSignal(NGame.Instance.GetTree(), SceneTree.SignalName.ProcessFrame);
            button = VisibleUi.Descendants<NRewardButton>(NRun.Instance!).FirstOrDefault(button => VisibleUi.Shown(button) && button.IsEnabled);
        } while (button == null && DateTime.UtcNow < deadline);
        if (button == null) throw new TimeoutException("The event card reward did not appear.");
        button.ForceClick();
        await task;
    }
}
