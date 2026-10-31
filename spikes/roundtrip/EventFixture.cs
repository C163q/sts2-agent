using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Events;
using MegaCrit.Sts2.Core.Models.Potions;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class EventFixture
{
    public static async Task Configure(string scenario, Player player, Func<Task> frame)
    {
        RunManager.Instance.DebugOnlyGetState()!.ActFloor = 1;
        await PlayerCmd.GainGold(1000, player);
        await CreatureCmd.SetCurrentHp(player.Creature, scenario is "death" or "rescue" ? 1 : 40);
        if (scenario == "rescue") await PotionCmd.TryToProcure<FairyInABottle>(player);
        if (scenario == "dense_choice") await RelicCmd.Obtain<ChoicesParadox>(player);
        if (scenario == "repy")
        {
            await CardPileCmd.Add(player.RunState.CreateCard<LanternKey>(player), PileType.Deck, skipVisuals: true);
            PileType.Deck.GetPile(player).InvokeCardAddFinished();
        }
        if (scenario == "relic_trader")
        {
            await RelicCmd.Obtain<Anchor>(player); await RelicCmd.Obtain<Vajra>(player);
            await RelicCmd.Obtain<Nunchaku>(player); await RelicCmd.Obtain<PenNib>(player);
        }
        if (scenario is "future_potions" or "potions")
        {
            await PotionCmd.TryToProcure<FirePotion>(player);
            await PotionCmd.TryToProcure<BlockPotion>(player);
            await PotionCmd.TryToProcure<FruitJuice>(player);
        }
        if (scenario == "slippery")
            foreach (var card in player.Deck.Cards.Where(c => c.IsUpgradable)) { card.UpgradeInternal(); card.FinalizeUpgradeInternal(); }
        EventModel model = scenario switch {
            "upgrade" or "upgrade_cancel" or "transform" => ModelDb.Event<AromaOfChaos>(),
            "enchant" or "locked" => ModelDb.Event<SelfHelpBook>(),
            "remove" => ModelDb.Event<Wellspring>(),
            "grid" or "reward" => ModelDb.Event<BrainLeech>(),
            "cheese" => ModelDb.Event<RoomFullOfCheese>(),
            "potions" => ModelDb.Event<PotionCourier>(),
            "dense" or "dense_choice" => ModelDb.Event<DenseVegetation>(),
            "lantern" => ModelDb.Event<TheLanternKey>(),
            "repy" => ModelDb.Event<WarHistorianRepy>(),
            "dummy1" or "dummy2" or "dummy3" => ModelDb.Event<BattlewornDummy>(),
            "trial" or "trial_story" => ModelDb.Event<Trial>(),
            "crystal" => ModelDb.Event<CrystalSphere>(),
            "relic_trader" => ModelDb.Event<RelicTrader>(),
            "future_potions" => ModelDb.Event<TheFutureOfPotions>(),
            "tea" => ModelDb.Event<TeaMaster>(),
            "conveyor" => ModelDb.Event<EndlessConveyor>(),
            "slippery" => ModelDb.Event<SlipperyBridge>(),
            "reflections" => ModelDb.Event<Reflections>(),
            "doll" => ModelDb.Event<DollRoom>(),
            "wood" => ModelDb.Event<WoodCarvings>(),
            "sapphire" => ModelDb.Event<SapphireSeed>(),
            "symbiote" => ModelDb.Event<Symbiote>(),
            _ => ModelDb.Event<AbyssalBaths>() };
        await RunManager.Instance.EnterRoom(new EventRoom(model));
        for (int i = 0; i < 900 && !(EventInspection.Current is { } current && EventInspection.Ready(current)); i++) await frame();
        if (EventInspection.Current is not { } ready || !EventInspection.Ready(ready))
            throw new InvalidOperationException("Event fixture did not become ready.");
        NRun.Instance!.GlobalUi.MapScreen.SetTravelEnabled(false);
    }

    public static async Task PrepareVictory(Player player)
    {
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        foreach (var enemy in combat.Enemies) await CreatureCmd.SetCurrentHp(enemy, 1);
        await CardPileCmd.AddGeneratedCardToCombat(combat.CreateCard<Thunderclap>(player), PileType.Hand, player);
    }

    public static object Read(Player player) => new {
        hp = player.Creature.CurrentHp, gold = player.Gold, deck_count = player.Deck.Cards.Count,
        upgrades = player.Deck.Cards.Sum(c => c.CurrentUpgradeLevel),
        enchantments = player.Deck.Cards.Count(c => c.Enchantment != null),
        relics = player.Relics.Select(r => r.Id.Entry).ToArray(),
        potions = player.PotionSlots.Select(p => p?.Id.Entry).ToArray(),
        event_rng = EventInspection.Current?.Model.Rng.Counter,
        pending = EventTaskTracker.Pending, previews = RunUi.CardPreviewsPending(),
        option_keys = EventInspection.Current?.Layout.OptionButtons.Select(b => b.Option.TextKey).ToArray(),
        room_count = player.RunState.CurrentRoomCount
    };
}
