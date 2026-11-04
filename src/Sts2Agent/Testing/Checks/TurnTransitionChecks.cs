using System.Text.Json;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Vfx;

namespace Sts2Agent;

internal static class TurnTransitionChecks
{
    public static object EndTurn(Func<string?> unavailable, Func<string> observe)
    {
        var checks = new List<object>();
        void Check(string name, bool passed) => checks.Add(new { name, passed });
        bool Advertised()
        {
            using var snapshot = JsonDocument.Parse(observe());
            return snapshot.RootElement.GetProperty("available_actions").EnumerateArray().Any(a => a.GetString() == "end_turn");
        }
        var button = NCombatRoom.Instance!.Ui.EndTurnButton;
        bool visible = button.Visible, enabled = button.IsEnabled;
        try
        {
            Check("normal turn is available", unavailable() == null && Advertised());
            button.Visible = false;
            Check("hidden button is refused and not advertised", unavailable()?.Contains("not visible") == true && !Advertised());
            button.Visible = visible;
            button.Disable();
            Check("disabled button is refused and not advertised", unavailable()?.Contains("disabled") == true && !Advertised());
        }
        finally
        {
            button.Visible = visible;
            if (enabled) button.Enable(); else button.Disable();
        }
        Check("button restoration restores availability", unavailable() == null && Advertised());
        return Result(checks);
    }

    public static async Task<object> Movements(Player player, CombatObservation observation, Func<Task> frame)
    {
        var checks = new List<object>();
        var samples = new List<object>();
        void Check(string name, bool passed) => checks.Add(new { name, passed });
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        async Task Settle()
        {
            var deadline = DateTime.UtcNow.AddSeconds(10);
            do { await frame(); }
            while ((RunUi.CardPreviewsPending() || VisibleUi.Descendants<Godot.Node>(NRun.Instance!)
                .Any(node => node is NCardFlyVfx or NCardFlyShuffleVfx)) && DateTime.UtcNow < deadline);
            if (DateTime.UtcNow >= deadline) throw new TimeoutException("Movement check animation did not settle.");
        }
        async Task<Dictionary<string, object?>[]> Capture(string name, Func<Task> move, Action<TurnEventBuffer>? facts = null)
        {
            using var scope = new ActionEventScope();
            using var journal = new TurnJournal(combat, player, observation.CardId,
                observation.KnownCardName, observation.RememberCardName);
            await move();
            await Settle();
            facts?.Invoke(scope.Buffer);
            var events = scope.Buffer.Events.Where(e => (string)e["type"]! == "card_moved").ToArray();
            samples.Add(new { name, events });
            return events;
        }

        var card = combat.CreateCard<DefendIronclad>(player);
        await CardPileCmd.AddGeneratedCardToCombat(card, PileType.Hand, player);
        await Settle();
        await CardPileCmd.Add(card, PileType.Discard);
        await Settle();
        var absent = await Capture("no visual", () => CardPileCmd.Add(card, PileType.Draw, skipVisuals: true));
        Check("no visual does not invent a movement", absent.Length == 0);
        var same = await Capture("same pile", () => CardPileCmd.Add(card, PileType.Draw, CardPilePosition.Top));
        Check("same pile position is not exported", same.Length == 0);
        await CardPileCmd.Add(card, PileType.Discard);
        await Settle();
        var count = NCombatRoom.Instance!.Ui.DiscardPile.GetNode<Godot.Control>("CountContainer/Count");
        bool countVisible = count.Visible;
        Dictionary<string, object?>[] unreadable;
        try
        {
            count.Visible = false;
            unreadable = await Capture("hidden source count", () => CardPileCmd.Add(card, PileType.Draw));
        }
        finally { count.Visible = countVisible; }
        Check("hidden count cannot prove an anonymous singleton", unreadable.Length == 0);
        await CardPileCmd.Add(card, PileType.Discard);
        await Settle();
        var moved = await Capture("visible singleton", () => CardPileCmd.Add(card, PileType.Draw));
        Check("visible singleton moves once without position", moved.Length == 1
            && (string)moved[0]["from_pile"]! == "discard" && (string)moved[0]["to_pile"]! == "draw"
            && moved[0].Keys.ToHashSet().SetEquals(["sequence", "type", "card", "from_pile", "to_pile"]));

        var room = NCombatRoom.Instance!;
        bool wasVisible = room.Visible;
        var hidden = await Capture("hidden and revealed", async () =>
        {
            try { room.Visible = false; await CardPileCmd.Add(card, PileType.Discard); await Settle(); }
            finally { room.Visible = wasVisible; }
            await Settle();
        });
        Check("hidden movement is not replayed after reveal", hidden.Length == 0);

        var unknown = combat.CreateCard<DefendIronclad>(player);
        await CardPileCmd.AddGeneratedCardToCombat(unknown, PileType.Discard, player);
        await Settle();
        var anonymous = await Capture("unidentified back among multiple cards", () => CardPileCmd.Add(unknown, PileType.Draw));
        Check("anonymous multi-card source does not disclose identity", anonymous.Length == 0);

        await CardPileCmd.Add(card, PileType.Hand);
        await Settle();
        var backs = new[] { combat.CreateCard<DefendIronclad>(player), combat.CreateCard<DefendIronclad>(player) };
        await CardPileCmd.AddGeneratedCardsToCombat(backs, PileType.Discard, player);
        await Settle();
        var batch = await Capture("anonymous batch", () => CardPileCmd.Add(backs, PileType.Draw));
        Check("last anonymous card does not become identifiable through removal order", batch.Length == 0);

        var next = combat.CreateCard<StrikeIronclad>(player);
        await CardPileCmd.AddGeneratedCardToCombat(next, PileType.Hand, player);
        await CardPileCmd.Add(card, PileType.Discard);
        await Settle();
        var chained = await Capture("silent move before a visible transfer", async () =>
        {
            await CardPileCmd.Add(card, PileType.Draw, skipVisuals: true);
            await CardPileCmd.Add(next, PileType.Discard);
            await Settle();
            CardMovementJournal.Choose(next);
            await CardPileCmd.Add(next, PileType.Draw);
        });
        Check("a later flight cannot publish an earlier silent card", chained.Length == 1
            && JsonSerializer.SerializeToElement(chained[0]["card"]).GetProperty("id").GetInt32() == observation.CardId(next));

        await CardPileCmd.Add(card, PileType.Discard);
        await Settle();
        var shuffled = await Capture("shuffle", () => CardPileCmd.Shuffle(new ThrowingPlayerChoiceContext(), player));
        Check("shuffle does not expose per-card order", shuffled.Length == 0);

        var returned = await Capture("direct draw-pile return", () => CardPileCmd.Add(card, PileType.Hand));
        Check("draw-pile return without a draw history is retained", returned.Length == 1
            && (string)returned[0]["from_pile"]! == "draw" && (string)returned[0]["to_pile"]! == "hand");
        await CardPileCmd.Add(card, PileType.Draw, CardPilePosition.Top);
        await Settle();
        var drawn = await Capture("real native draw", () => CardPileCmd.Draw(new ThrowingPlayerChoiceContext(), 1, player),
            buffer => Check("native draw retains its specialized event", buffer.Events.Any(e => (string)e["type"]! == "card_drawn"
                && JsonSerializer.SerializeToElement(e["card"]).GetProperty("id").GetInt32() == observation.CardId(card))));
        Check("real native draw has no duplicate movement", drawn.Length == 0);

        using (var scope = new ActionEventScope())
        {
            var journal = new TurnJournal(combat, player, observation.CardId);
            journal.Dispose();
            await CardPileCmd.Add(card, PileType.Discard);
            await Settle();
            Check("disposed journal has no further events", scope.Buffer.Events.Count == 0);
        }
        return Result(checks, samples);
    }

    private static object Result(List<object> checks, List<object>? samples = null) => new {
        passed = checks.All(check => JsonSerializer.SerializeToElement(check).GetProperty("passed").GetBoolean()), checks, samples };
}
