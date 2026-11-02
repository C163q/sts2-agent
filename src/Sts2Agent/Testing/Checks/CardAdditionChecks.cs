using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class CardAdditionChecks
{
    public static async Task<object> Run(Player player, Func<Task> frame, Func<CardModel, int> cardId)
    {
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        var room = NCombatRoom.Instance!;
        var checks = new List<object>();
        var samples = new List<object>();
        bool passed = true;
        void Check(string name, bool ok) { checks.Add(new { name, passed = ok }); passed &= ok; }
        async Task Settle()
        {
            var deadline = DateTime.UtcNow.AddSeconds(12);
            do { await frame(); }
            while ((RunUi.CardPreviewsPending() || VisibleUi.Descendants<MegaCrit.Sts2.Core.Nodes.Vfx.NCardFlyVfx>(NRun.Instance!).Any())
                && DateTime.UtcNow < deadline);
            if (DateTime.UtcNow >= deadline) throw new TimeoutException("Card addition UI did not settle.");
        }
        async Task<Dictionary<string, object?>[]> Capture(string name, Func<ActionEventScope, Task> action, int limit = 512)
        {
            using var scope = new ActionEventScope(limit);
            using var journal = new TurnJournal(combat, player, cardId);
            await action(scope);
            await frame();
            var events = scope.Buffer.Events.Where(e => (string)e["type"]! == "card_added").ToArray();
            samples.Add(new { name, events, truncated = scope.Buffer.Truncated });
            Check(name + ": dense sequence", scope.Buffer.Events.Select(e => (int)e["sequence"]!)
                .SequenceEqual(Enumerable.Range(1, scope.Buffer.Events.Count)));
            return events;
        }
        static string? Pile(Dictionary<string, object?> e) => e.TryGetValue("pile", out var pile) ? pile as string : "MISSING";
        static int Id(Dictionary<string, object?> e) => JsonSerializer.SerializeToElement(e["card"]).GetProperty("id").GetInt32();

        foreach (var (type, expected) in new[] { (PileType.Hand, "hand"), (PileType.Draw, "draw"),
            (PileType.Discard, "discard"), (PileType.Exhaust, "exhaust"), (PileType.Play, "play") })
        {
            var card = combat.CreateCard<DefendIronclad>(player);
            var events = await Capture(expected, async _ =>
            {
                var result = await CardPileCmd.AddGeneratedCardToCombat(card, type, null);
                CardCmd.PreviewCardPileAdd(result, .1f);
                await Settle();
            });
            Check(expected + ": actual visible destination captured once", events.Length == 1 && Pile(events[0]) == expected
                && Id(events[0]) == cardId(card));
            await CardPileCmd.RemoveFromCombat(card);
        }

        var unknown = combat.CreateCard<DefendIronclad>(player);
        var unknownEvents = await Capture("identity before direction", async scope =>
        {
            var result = await CardPileCmd.AddGeneratedCardToCombat(unknown, PileType.Draw, player);
            CardCmd.PreviewCardPileAdd(result, 1f);
            for (int i = 0; i < 20; i++) await frame();
            var visible = scope.Buffer.Events.Where(e => (string)e["type"]! == "card_added").ToArray();
            Check("preview identity does not reveal its hidden pile", visible.Length == 1 && Pile(visible[0]) == null);
            await Settle();
        });
        Check("same event gains its rendered flight destination", unknownEvents.Length == 1 && Pile(unknownEvents[0]) == "draw");
        await CardPileCmd.RemoveFromCombat(unknown);

        var moved = combat.CreateCard<DefendIronclad>(player);
        var movedEvents = await Capture("later pile differs", async _ =>
        {
            await CardPileCmd.AddGeneratedCardToCombat(moved, PileType.Hand, player);
            for (int i = 0; i < 20; i++) await frame();
            await CardPileCmd.Add(moved, PileType.Discard);
            await Settle();
        });
        Check("later discard cannot replace the initial hand target", movedEvents.Length == 1 && Pile(movedEvents[0]) == "hand");
        await CardPileCmd.RemoveFromCombat(moved);

        var returned = combat.CreateCard<DefendIronclad>(player);
        try
        {
            var returnedEvents = await Capture("later return to initial pile", async _ =>
            {
                room.Ui.Hand.Hide();
                await CardPileCmd.AddGeneratedCardToCombat(returned, PileType.Hand, player);
                await CardPileCmd.Add(returned, PileType.Discard);
                await Settle();
                room.Ui.Hand.Show();
                await CardPileCmd.Add(returned, PileType.Hand);
                await Settle();
            });
            Check("ordinary return cannot establish an unshown initial destination", returnedEvents.Length == 1
                && Pile(returnedEvents[0]) == null);
        }
        finally { room.Ui.Hand.Show(); }
        await CardPileCmd.RemoveFromCombat(returned);

        var hiddenTarget = combat.CreateCard<DefendIronclad>(player);
        try
        {
            var targetEvents = await Capture("hidden pile button", async _ =>
            {
                room.Ui.DrawPile.Hide();
                var result = await CardPileCmd.AddGeneratedCardToCombat(hiddenTarget, PileType.Draw, player);
                CardCmd.PreviewCardPileAdd(result, .1f);
                await Settle();
                room.Ui.DrawPile.Show();
                await Settle();
            });
            Check("a visible card flight with a hidden target keeps unknown direction", targetEvents.Length == 1
                && Pile(targetEvents[0]) == null);
        }
        finally { room.Ui.DrawPile.Show(); }
        await CardPileCmd.RemoveFromCombat(hiddenTarget);

        var ordinary = player.PlayerCombatState!.Hand.Cards.First();
        var ordinaryEvents = await Capture("ordinary movement", async _ =>
        {
            await CardPileCmd.Add(ordinary, PileType.Discard);
            await CardPileCmd.Add(ordinary, PileType.Hand);
            await Settle();
        });
        Check("moving an existing card is not card_added", ordinaryEvents.Length == 0);

        var original = combat.CreateCard<DefendIronclad>(player);
        await CardPileCmd.AddGeneratedCardToCombat(original, PileType.Hand, player);
        await Settle();
        CardModel? replacement = null;
        var transformedEvents = await Capture("native combat transform", async _ =>
        {
            replacement = (await CardCmd.TransformTo<Anger>(original))?.cardAdded;
            await Settle();
        });
        Check("transform add-before-generation order retains its visible replacement", transformedEvents.Length == 1
            && replacement != null && Id(transformedEvents[0]) == cardId(replacement)
            && Pile(transformedEvents[0]) == "hand");
        if (replacement != null) await CardPileCmd.RemoveFromCombat(replacement);

        var hidden = combat.CreateCard<DefendIronclad>(player);
        try
        {
            var hiddenEvents = await Capture("hidden generation", async _ =>
            {
                room.Hide();
                await frame();
                var result = await CardPileCmd.AddGeneratedCardToCombat(hidden, PileType.Draw, player);
                CardCmd.PreviewCardPileAdd(result, .1f);
                await Settle();
                room.Show();
                await Settle();
            });
            Check("hidden generation never replays after restoring UI", hiddenEvents.Length == 0);
        }
        finally { room.Show(); }
        await CardPileCmd.RemoveFromCombat(hidden);

        var interrupted = combat.CreateCard<DefendIronclad>(player);
        try
        {
            var interruptedEvents = await Capture("hidden direction", async scope =>
            {
                var result = await CardPileCmd.AddGeneratedCardToCombat(interrupted, PileType.Draw, player);
                CardCmd.PreviewCardPileAdd(result, 1f);
                for (int i = 0; i < 20; i++) await frame();
                room.Hide();
                await Settle();
                room.Show();
                await Settle();
            });
            Check("hiding a known identity never exposes an unseen destination", interruptedEvents.Length == 1
                && Pile(interruptedEvents[0]) == null);
        }
        finally { room.Show(); }
        await CardPileCmd.RemoveFromCombat(interrupted);

        var overLimit = await Capture("bounded hidden identities", async _ =>
        {
            for (int i = 0; i < 3; i++)
                await CardPileCmd.AddGeneratedCardToCombat(combat.CreateCard<Dazed>(player), PileType.Draw, player);
            await Settle();
        }, limit: 2);
        Check("unshown identities are not published", overLimit.Length == 0);
        var lastSample = JsonSerializer.SerializeToElement(samples[^1]);
        Check("pending generations count toward the shared limit", lastSample.GetProperty("truncated").GetBoolean());

        using (var scope = new ActionEventScope())
        {
            var journal = new TurnJournal(combat, player, cardId);
            journal.Dispose();
            var result = await CardPileCmd.AddGeneratedCardToCombat(combat.CreateCard<Dazed>(player), PileType.Draw, player);
            CardCmd.PreviewCardPileAdd(result, .1f);
            await Settle();
            Check("disposed journal cannot publish later UI", scope.Buffer.Events.Count == 0);
        }
        return new { passed, checks, samples };
    }
}
