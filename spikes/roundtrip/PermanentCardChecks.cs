using Godot;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Enchantments;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.CommonUi;

namespace Sts2Agent;

internal static class PermanentCardChecks
{
    public static async Task<object> Run(Player player, Func<Task> frame, Func<CardModel, int> cardId)
    {
        var copies = NPlayerHand.Instance!.ActiveHolders.Select(h => h.CardNode!.Model!).ToArray();
        var attackCopy = copies.OfType<StrikeIronclad>().Single();
        var attack = attackCopy.DeckVersion!;
        var genetic = (GeneticAlgorithm)copies.OfType<GeneticAlgorithm>().Single().DeckVersion!;
        var geneticCopy = copies.OfType<GeneticAlgorithm>().Single();
        var bash = copies.OfType<Bash>().Single().DeckVersion!;
        var unseen = player.Deck.Cards.OfType<StrikeIronclad>().First(c => !ReferenceEquals(c, attack));
        var checks = new List<object>();
        var samples = new List<object>();
        bool passed = true;
        void Check(string name, bool ok) { checks.Add(new { name, passed = ok }); passed &= ok; }
        async Task<Dictionary<string, object?>[]> Capture(string name, Func<ActionEventScope, Task> action, int limit = 512)
        {
            using var scope = new ActionEventScope(limit);
            using var resources = new RunResourceJournal(player, scope.Buffer);
            using var journal = new RunInventoryJournal(player, scope.Buffer, cardId);
            await frame();
            await action(scope);
            await frame();
            var events = scope.Buffer.Events.ToArray();
            samples.Add(new { name, events, truncated = scope.Buffer.Truncated });
            return events;
        }
        static bool Kinds(Dictionary<string, object?>[] events, params string[] kinds) =>
            events.Select(e => (string)e["type"]!).SequenceEqual(kinds);
        async Task SettlePreview()
        {
            var deadline = DateTime.UtcNow.AddSeconds(8);
            do { await frame(); } while (RunUi.CardPreviewsPending() && DateTime.UtcNow < deadline);
            if (RunUi.CardPreviewsPending()) throw new TimeoutException("Permanent card preview did not settle.");
        }
        var events = await Capture("stats", async scope =>
        {
            genetic.CurrentBlock += 2;
            genetic.CurrentBlock += 1;
            genetic.CurrentBlock = genetic.CurrentBlock;
            await frame();
        }, 1);
        Check("direct native base changes coalesce without consuming extra buffer", Kinds(events, "card_stats_changed"));
        Check("stats receipt never contains private values", events is [var stats] && stats.Keys.Order()
            .SequenceEqual(new[] { "card", "pile", "sequence", "type" }));
        events = await Capture("cost", async scope =>
        {
            attack.EnergyCost.SetCustomBaseCost(2);
            attack.EnergyCost.SetCustomBaseCost(0);
            attack.EnergyCost.SetCustomBaseCost(0);
            await frame();
        }, 1);
        Check("permanent base cost coalesces once", Kinds(events, "card_energy_cost_changed"));
        events = await Capture("unchanged", async scope =>
        {
            genetic.CurrentBlock = genetic.CurrentBlock;
            attack.EnergyCost.SetCustomBaseCost(0);
            await frame();
        });
        Check("unchanged native base values are omitted", events.Length == 0);
        events = await Capture("temporary", async scope =>
        {
            attackCopy.DynamicVars.Damage.BaseValue += 1;
            attackCopy.EnergyCost.SetThisTurn(0);
            attackCopy.EnergyCost.SetCustomBaseCost(2);
            attack.DynamicVars.Damage.PreviewValue += 3;
            attack.DynamicVars.Damage.EnchantedValue += 3;
            await frame();
        });
        Check("combat copies temporary costs and preview values are excluded", events.Length == 0);
        CardCmd.Upgrade(geneticCopy, CardPreviewStyle.None);
        NCard.FindOnTable(geneticCopy)!.UpdateVisuals(PileType.Hand, CardPreviewMode.Normal);
        await frame();
        events = await Capture("copy_upgrade_name", async scope =>
        {
            genetic.CurrentBlock += 1;
            await frame();
        });
        Check("temporary upgraded copy never upgrades the permanent identity name", events is [var copyName]
            && System.Text.Json.JsonSerializer.SerializeToElement(copyName["card"]).GetProperty("name").GetString() == "Genetic Algorithm"
            && !genetic.IsUpgraded);
        CardCmd.Downgrade(geneticCopy);
        NCard.FindOnTable(geneticCopy)!.UpdateVisuals(PileType.Hand, CardPreviewMode.Normal);
        await frame();
        events = await Capture("previews", async scope =>
        {
            EnglishCardText.Read(() => BrowsedCard.Read(bash, "test", PileType.Deck, true, true));
            var detached = (CardModel)attack.MutableClone();
            detached.DynamicVars.Damage.BaseValue += 9;
            detached.EnergyCost.SetCustomBaseCost(0);
            await frame();
        });
        Check("upgrade previews and detached clones never modify permanent log", events.Length == 0);
        events = await Capture("upgrades", async scope =>
        {
            CardCmd.Upgrade(bash, CardPreviewStyle.None);
            CardCmd.Downgrade(bash);
            await frame();
        });
        Check("upgrade and downgrade do not duplicate numeric events", Kinds(events, "card_upgraded", "card_downgraded"));
        events = await Capture("another_card", async scope =>
        {
            void OtherCard() => genetic.CurrentBlock += 1;
            bash.Upgraded += OtherCard;
            try { CardCmd.Upgrade(bash, CardPreviewStyle.None); }
            finally { bash.Upgraded -= OtherCard; }
            await frame();
        });
        Check("suppressing one card preserves another card's actual mutation", Kinds(events,
            "card_upgraded", "card_stats_changed"));
        CardCmd.Downgrade(bash);
        events = await Capture("enchantment", async scope =>
        {
            CardCmd.Enchant<Sharp>(attack, 2);
            attack.Enchantment!.Amount = 4;
            attack.Enchantment.Amount = 5;
            await frame();
        });
        Check("enchantment attachment and direct amount changes are distinct", Kinds(events,
            "card_enchantment_changed", "card_enchantment_changed"));
        events = await Capture("enchantment_unchanged", async scope =>
        {
            attack.Enchantment!.Amount = 5;
            attack.Enchantment.ModifyCard();
            await frame();
        });
        Check("unchanged enchantment and recomputation do not duplicate", events.Length == 0);
        events = await Capture("enchantment_clear", async scope =>
        {
            CardCmd.ClearEnchantment(attack);
            await frame();
        });
        Check("enchantment removal has one existing event", Kinds(events, "card_enchantment_changed"));
        CardCmd.Enchant<Spiral>(attack, 1);
        events = await Capture("enchantment_variable", async scope =>
        {
            attack.Enchantment!.DynamicVars["Times"].BaseValue = 2;
            attack.Enchantment.DynamicVars["Times"].BaseValue = 3;
            await frame();
        });
        Check("enchantment-owned variables retain enchantment category", Kinds(events, "card_enchantment_changed"));
        CardCmd.ClearEnchantment(attack);
        events = await Capture("hidden_identity", async scope =>
        {
            unseen.DynamicVars.Damage.BaseValue += 1;
            await frame();
        });
        Check("same-name hidden permanent card cannot borrow visible identity", events.Length == 0);
        events = await Capture("late_identity", async scope =>
        {
            unseen.DynamicVars.Damage.BaseValue += 1;
            attack.EnergyCost.SetCustomBaseCost(1);
            Check("unknown identity remains pending", scope.Buffer.Events.Count == 1);
            CardCmd.Preview(unseen, 0.25f);
            await SettlePreview();
        });
        Check("later actual preview preserves first mutation position", Kinds(events, "card_stats_changed", "card_energy_cost_changed"));
        events = await Capture("hidden_ui", async scope =>
        {
            var top = NRun.Instance!.GlobalUi.TopBar;
            try
            {
                top.Hide(); await frame();
                genetic.CurrentBlock += 1;
                attack.EnergyCost.SetCustomBaseCost(2);
                await frame();
                Check("hidden permanent changes remain private", scope.Buffer.Events.Count == 0);
            }
            finally { top.Show(); }
            await frame();
        });
        Check("restoring UI does not replay hidden mutations", events.Length == 0);
        events = await Capture("canceled_identity", async scope =>
        {
            unseen.DynamicVars.Damage.BaseValue += 1;
            var top = NRun.Instance!.GlobalUi.TopBar;
            try { top.Hide(); await frame(); }
            finally { top.Show(); }
            await frame();
            CardCmd.Preview(unseen, 0.25f);
            await SettlePreview();
            Check("canceled unknown mutation never reappears", scope.Buffer.Events.Count == 0);
            unseen.DynamicVars.Damage.BaseValue += 1;
            await frame();
        });
        Check("restored public identity accepts a new mutation", Kinds(events, "card_stats_changed"));
        events = await Capture("exception", async scope =>
        {
            CardCmd.Upgrade(bash, CardPreviewStyle.None);
            try { bash.UpgradeInternal(); }
            catch (InvalidOperationException) { }
            bash.DynamicVars.Damage.BaseValue += 1;
            await frame();
        });
        Check("throwing nested upgrade releases mutation suppression", Kinds(events, "card_upgraded", "card_stats_changed"));
        events = await Capture("limit", async scope =>
        {
            genetic.CurrentBlock += 1;
            attack.EnergyCost.SetCustomBaseCost(0);
            await frame();
            Check("direct changes share the action buffer cap", scope.Buffer.Truncated && scope.Buffer.Events.Count == 1);
        }, 1);
        genetic.CurrentBlock += 1;
        events = await Capture("fresh", async scope => await frame());
        Check("disposed capture never replays outside-scope mutations", events.Length == 0 && RunInventoryJournal.Current == null);
        return new { passed, checks, samples };
    }
}
