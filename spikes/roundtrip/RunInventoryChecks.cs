using Godot;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Enchantments;
using MegaCrit.Sts2.Core.Models.Potions;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Nodes;

namespace Sts2Agent;

internal static class RunInventoryChecks
{
    public static async Task<object> Run(Player player, Func<Task> frame, Func<CardModel, int> cardId)
    {
        var checks = new List<object>();
        bool passed = true;
        void Check(string name, bool ok) { checks.Add(new { name, passed = ok }); passed &= ok; }
        var global = NRun.Instance!.GlobalUi;
        RelicModel relic = await RelicCmd.Obtain<Anchor>(player);
        async Task Settle()
        {
            var deadline = DateTime.UtcNow.AddSeconds(10);
            do
            {
                await frame();
                RunResourceJournal.Current?.SampleVisibility();
                RunInventoryJournal.Current?.SampleVisibility();
                PotionJournal.Current?.SampleVisibility();
            } while ((RunUi.ResourceMotionPending() || RunUi.CardPreviewsPending()) && DateTime.UtcNow < deadline);
            if (DateTime.UtcNow >= deadline) throw new TimeoutException("Inventory test animation did not finish.");
        }
        await Settle();
        using var events = new ActionEventScope();
        using var resources = new RunResourceJournal(player, events.Buffer);
        using var inventory = new RunInventoryJournal(player, events.Buffer, cardId);
        using var potions = new PotionJournal(player);
        try
        {
            int count = events.Buffer.Events.Count;
            global.RelicInventory.Hide();
            inventory.SampleVisibility();
            await RelicCmd.Remove(relic);
            Check("hidden inventory removal is omitted", events.Buffer.Events.Count == count);
            global.RelicInventory.Show();
            inventory.SampleVisibility();
            await Settle();
            Check("restoring inventory never replays a hidden removal", events.Buffer.Events.Count == count);

            relic = await RelicCmd.Obtain<Anchor>(player);
            await Settle();
            Check("visible relic acquisition is captured once", events.Buffer.Events.Count(e => (string)e["type"]! == "relic_obtained") == 1);
            await RelicCmd.Remove(relic);
            Check("visible relic removal is captured once", events.Buffer.Events.Count(e => (string)e["type"]! == "relic_removed") == 1);

            var card = player.Deck.Cards.First(c => c.IsUpgradable && c.Enchantment == null);
            CardCmd.Preview(card);
            for (int i = 0; i < 12; i++) await frame();
            inventory.SampleVisibility();
            count = events.Buffer.Events.Count;
            CardCmd.Enchant<Sharp>(card, 1);
            CardCmd.ClearEnchantment(card);
            CardCmd.Enchant<Sharp>(card, 2);
            Check("attach, clear and replacement enchantments are each captured once", events.Buffer.Events.Skip(count)
                .Count(e => (string)e["type"]! == "card_enchantment_changed") == 3);
            CardCmd.ClearEnchantment(card);
            CardCmd.Upgrade(card, MegaCrit.Sts2.Core.Nodes.CommonUi.CardPreviewStyle.None);
            CardCmd.Downgrade(card);
            Check("visible permanent upgrade and downgrade have distinct events", events.Buffer.Events.Skip(count)
                .Count(e => (string)e["type"]! is "card_upgraded" or "card_downgraded") == 2);
            await Settle();

            count = events.Buffer.Events.Count;
            global.TopBar.Hide();
            resources.SampleVisibility();
            inventory.SampleVisibility();
            potions.SampleVisibility();
            relic = await RelicCmd.Obtain<Lantern>(player);
            await RelicCmd.Remove(relic);
            await PotionCmd.TryToProcure<BlockPotion>(player);
            var potion = player.Potions.OfType<BlockPotion>().Last();
            await PotionCmd.Discard(potion);
            var hidden = player.RunState.CreateCard<MegaCrit.Sts2.Core.Models.Cards.Anger>(player);
            await CardPileCmd.Add(hidden, PileType.Deck, skipVisuals: true);
            CardCmd.Upgrade(hidden, MegaCrit.Sts2.Core.Nodes.CommonUi.CardPreviewStyle.None);
            await CardPileCmd.RemoveFromDeck(hidden, showPreview: false);
            Check("hidden item and permanent card changes expose no identity", events.Buffer.Events.Count == count);
            global.TopBar.Show();
            resources.SampleVisibility();
            inventory.SampleVisibility();
            potions.SampleVisibility();
            await Settle();
            Check("restoring UI never replays hidden changes", events.Buffer.Events.Count == count);

            await PotionCmd.TryToProcure<BlockPotion>(player);
            await Settle();
            potion = player.Potions.OfType<BlockPotion>().Last();
            count = events.Buffer.Events.Count;
            global.TopBar.PotionContainer.Hide();
            potions.SampleVisibility();
            await PotionCmd.Discard(potion);
            Check("hidden potion container removal is omitted", events.Buffer.Events.Count == count);
            global.TopBar.PotionContainer.Show();
            potions.SampleVisibility();
            await Settle();
            Check("restoring potion container never replays a hidden discard", events.Buffer.Events.Count == count);

            foreach (bool hideBefore in new[] { true, false })
            {
                count = events.Buffer.Events.Count;
                if (hideBefore) global.RelicInventory.Hide();
                relic = await RelicCmd.Obtain<Anchor>(player);
                if (!hideBefore) global.RelicInventory.Hide();
                inventory.SampleVisibility();
                await Settle();
                Check("hidden or interrupted relic acquisition stays unpublished", events.Buffer.Events.Count == count);
                global.RelicInventory.Show();
                await Settle();
                Check("restoring relic inventory never publishes a hidden acquisition", events.Buffer.Events.Count == count);
                await RelicCmd.Remove(relic);

                count = events.Buffer.Events.Count;
                global.TopBar.PotionContainer.Hide();
                await PotionCmd.TryToProcure<BlockPotion>(player);
                potion = player.Potions.OfType<BlockPotion>().Last();
                inventory.SampleVisibility();
                await Settle();
                Check("hidden potion acquisition stays unpublished", events.Buffer.Events.Count == count);
                global.TopBar.PotionContainer.Show();
                await Settle();
                Check("restoring potion inventory never publishes a hidden acquisition", events.Buffer.Events.Count == count);
                await PotionCmd.Discard(potion);
            }
            count = events.Buffer.Events.Count;
            inventory.Dispose();
            potions.Dispose();
            await PotionCmd.TryToProcure<BlockPotion>(player);
            potion = player.Potions.OfType<BlockPotion>().Last();
            await PotionCmd.Discard(potion);
            Check("disposed journals do not record future changes", events.Buffer.Events.Count == count);
            return new { passed, checks, events = events.Buffer.Events };
        }
        finally { global.TopBar.Show(); global.RelicInventory.Show(); global.TopBar.PotionContainer.Show(); }
    }
}
