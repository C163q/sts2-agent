using HarmonyLib;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Merchant;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Events;
using MegaCrit.Sts2.Core.Models.Enchantments;
using MegaCrit.Sts2.Core.Models.Potions;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class ShopFixture
{
    private static string scenario = "";
    private static Task? targetingTask;
    public static Task? Pending => targetingTask;
    public static void Reset() { targetingTask = null; scenario = ""; }

    public static async Task Configure(string name, Player player, Func<Task> frame)
    {
        scenario = name;
        RunManager.Instance.DebugOnlyGetState()!.ActFloor = 1;
        await PlayerCmd.GainGold(2000, player);
        if (name is "enchanted_remove" or "parasol_enchanted")
        {
            var attacks = player.Deck.Cards.Where(card => card.Type == CardType.Attack).ToArray();
            foreach (var card in attacks.Take(3)) CardCmd.Enchant<Sharp>(card, 3);
            CardCmd.Enchant<Spiral>(attacks.First(card => card.Enchantment == null
                && ModelDb.Enchantment<Spiral>().CanEnchant(card)), 1);
        }
        if (name.Contains("sozu", StringComparison.Ordinal)) await RelicCmd.Obtain<Sozu>(player);
        if (name is "courier" or "parasol_courier" or "fake") await RelicCmd.Obtain<TheCourier>(player);
        if (name.StartsWith("parasol", StringComparison.Ordinal)) await RelicCmd.Obtain<LordsParasol>(player);
        if (name is "foul" or "fake" or "targeting") await PotionCmd.TryToProcure<FoulPotion>(player);
        if (name is "full" or "cauldron")
            for (int i = 0; i < player.MaxPotionCount; i++) await PotionCmd.TryToProcure<BlockPotion>(player);
        new Harmony("sts2_agent.test_shop_inventory").Patch(
            AccessTools.Method(typeof(MegaCrit.Sts2.Core.Entities.Merchant.MerchantInventory), nameof(MegaCrit.Sts2.Core.Entities.Merchant.MerchantInventory.CreateForNormalMerchant)),
            postfix: new HarmonyMethod(typeof(ShopFixture), nameof(InventoryCreated)));
        await RunManager.Instance.EnterRoomDebug(name == "fake" ? RoomType.Event : RoomType.Shop,
            model: name == "fake" ? ModelDb.Event<FakeMerchant>() : null, showTransition: false);
        for (int i = 0; i < 900; i++)
        {
            await frame();
            if (CardSelection.AwaitingInput || RewardInspection.Current is { } rewards && RewardInspection.Ready(rewards)
                || ShopInspection.Current is { } shop && ShopInspection.Ready(shop))
            {
                if (name == "targeting")
                {
                    targetingTask = PotionActions.Find(0)!.UsePotion();
                    for (int j = 0; j < 60 && !MegaCrit.Sts2.Core.Nodes.Combat.NTargetManager.Instance.IsInSelection; j++) await frame();
                    if (!MegaCrit.Sts2.Core.Nodes.Combat.NTargetManager.Instance.IsInSelection)
                        throw new InvalidOperationException("Native potion targeting did not start.");
                }
                if (name == "hidden_price")
                {
                    NMerchantRoom.Instance!.OpenInventory();
                    for (int j = 0; j < 600 && ShopInspection.Animating(ShopInspection.Current!); j++) await frame();
                    ShopInspection.Current!.Inventory.GetAllSlots().First().GetNode<Godot.CanvasItem>("%CostLabel").Hide();
                }
                return;
            }
        }
        throw new InvalidOperationException("Shop fixture did not reach an input boundary.");
    }

    private static void InventoryCreated(MegaCrit.Sts2.Core.Entities.Merchant.MerchantInventory __result)
    {
        var models = new RelicModel[] { scenario is "cauldron" or "cauldron_sozu" ? ModelDb.Relic<Cauldron>() : scenario == "nested" ? ModelDb.Relic<CallingBell>()
            : scenario == "choice" ? ModelDb.Relic<Astrolabe>() : ModelDb.Relic<Anchor>(), ModelDb.Relic<Lantern>(), ModelDb.Relic<PenNib>() };
        for (int i = 0; i < __result.RelicEntries.Count; i++)
        {
            AccessTools.Property(typeof(MerchantRelicEntry), nameof(MerchantRelicEntry.Model)).SetValue(__result.RelicEntries[i], models[i].ToMutable());
            __result.RelicEntries[i].CalcCost();
            // These isolated nested/unsupported UI probes use relics unavailable in ordinary shops.
            if (i == 0 && scenario is "nested" or "choice")
                AccessTools.Field(typeof(MerchantEntry), "_cost").SetValue(__result.RelicEntries[i], 100);
        }
    }

    public static async Task CancelTargeting()
    {
        MegaCrit.Sts2.Core.Nodes.Combat.NTargetManager.Instance.CancelTargeting();
        if (targetingTask != null) await targetingTask;
    }

    public static object Read(Player player) => new
    {
        targeting = MegaCrit.Sts2.Core.Nodes.Combat.NTargetManager.Instance.IsInSelection,
        targeting_pending = targetingTask is { IsCompleted: false },
        gold = player.Gold, deck_count = player.Deck.Cards.Count,
        deck = player.Deck.Cards.Select(c => c.Id.Entry).ToArray(),
        enchantments = player.Deck.Cards.Where(card => card.Enchantment != null).Select(card => new
        {
            card = card.Id.Entry, enchantment = card.Enchantment!.Id.Entry, amount = card.Enchantment.Amount
        }).ToArray(),
        relics = player.Relics.Select(r => r.Id.Entry).ToArray(),
        potions = player.PotionSlots.Select(p => p?.Id.Entry).ToArray(),
        pending = ShopTransactions.Pending, obtaining = RelicObtainTracker.Pending,
        previews = RunUi.CardPreviewsPending(), rng_counter = player.PlayerRng.Shops.ToSerializable().counter,
        removal_used = ShopInspection.Current?.Inventory.Inventory?.CardRemovalEntry?.Used,
        removals = player.ExtraFields.CardShopRemovalsUsed,
        base_prices = ShopInspection.Current?.Inventory.Inventory?.AllEntries.Select(e => (int)PrivateFields.Read(e, "_cost")!).ToArray(),
        inventory = ShopInspection.Current?.Inventory.Inventory?.AllEntries.Select(e => new
        {
            stocked = e.IsStocked, name = e switch
            {
                MerchantCardEntry c => c.CreationResult?.Card.Id.Entry,
                MerchantRelicEntry r => r.Model?.Id.Entry,
                MerchantPotionEntry p => p.Model?.Id.Entry, _ => "removal"
            }
        }).ToArray()
    };
}
