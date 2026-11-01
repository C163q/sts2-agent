using System.Text.Json;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Encounters;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.ValueProps;

namespace Sts2Agent;

internal static class CombatHandoffChecks
{
    public static async Task<object> Run(Player player, CombatObservation observation, Func<Task> frame, Func<string> observe)
    {
        var checks = new List<object>();
        var samples = new List<object>();
        bool passed = true;
        void Check(string name, bool ok) { checks.Add(new { name, passed = ok }); passed &= ok; }
        async Task Ready(bool covered = false, int? afterTurn = null)
        {
            var deadline = DateTime.UtcNow.AddSeconds(15);
            do { await frame(); }
            while ((!CombatManager.Instance.IsInProgress || CombatManager.Instance.IsStarting
                || !covered && (player.PlayerCombatState?.Phase != PlayerTurnPhase.Play
                    || !RunManager.Instance.ActionQueueSet.IsEmpty || CardSelection.Current != null
                    || CombatObservation.Status() != "visible")
                || afterTurn.HasValue && (player.PlayerCombatState?.TurnNumber ?? 0) <= afterTurn.Value)
                && DateTime.UtcNow < deadline);
            if (DateTime.UtcNow >= deadline) throw new TimeoutException("The replacement combat did not become ready.");
            await frame();
        }
        async Task Replace(bool covered = false)
        {
            void SetUp(CombatState state) => NRun.Instance!.GlobalUi.MapScreen.Open();
            if (covered) CombatManager.Instance.CombatSetUp += SetUp;
            try
            {
                await RunManager.Instance.EnterRoomDebug(RoomType.Monster,
                    model: ModelDb.Encounter<SlimesWeak>().ToMutable(), showTransition: true);
                await Ready(covered);
            }
            finally { if (covered) CombatManager.Instance.CombatSetUp -= SetUp; }
        }
        using (var action = new ActionEventScope())
        using (var scope = CombatJournalScope.Begin(player, observation))
        {
            var original = TurnCapture.Journal;
            var oldState = player.PlayerCombatState!;
            Check("initial battle is borrowed once without a marker", original != null && action.Buffer.Events.Count == 0);
            bool rejected = false;
            try { using var nested = CombatJournalScope.Begin(player, observation); }
            catch (InvalidOperationException) { rejected = true; }
            Check("nested ownership is rejected without disturbing the active journal", rejected
                && ReferenceEquals(scope, CombatJournalScope.Current) && ReferenceEquals(original, TurnCapture.Journal));
            await CreatureCmd.GainBlock(player.Creature, 2, ValueProp.Unpowered, null);
            await frame();
            await Replace();
            var first = action.Buffer.Events.ToArray();
            int boundary = Array.FindIndex(first, e => (string)e["type"]! == "combat_started");
            Check("old effect precedes the replacement boundary", boundary > 0 && first.Take(boundary)
                .Any(e => (string)e["type"]! == "block_changed" && (int)e["after"]! == 2));
            Check("native reset cleanup never invents block loss", !first.Any(e => (string)e["type"]! == "block_changed"
                && (int)e["after"]! == 0));
            Check("first replacement has one marker and five draws", first.Count(e => (string)e["type"]! == "combat_started") == 1
                && first.Skip(boundary + 1).Count(e => (string)e["type"]! == "card_drawn") == 5);
            Check("marker has no hidden encounter payload", boundary >= 0 && first[boundary].Keys.Order()
                .SequenceEqual(new[] { "sequence", "type" }));
            using (var state = JsonDocument.Parse(observe()))
            {
                var handIds = state.RootElement.GetProperty("player").GetProperty("hand").EnumerateArray()
                    .Select(card => card.GetProperty("id").GetInt32()).Order().ToArray();
                var drawnIds = first.Skip(boundary + 1).Where(e => (string)e["type"]! == "card_drawn")
                    .Select(e => JsonSerializer.SerializeToElement(e["card"]).GetProperty("id").GetInt32()).Order();
                Check("new draw IDs match the actual new hand", drawnIds.SequenceEqual(handIds));
            }
            var replacement = TurnCapture.Journal;
            original!.Dispose();
            Check("disposing an old journal cannot release the new journal", replacement != null
                && !ReferenceEquals(original, replacement) && ReferenceEquals(replacement, TurnCapture.Journal));
            int energyCount = action.Buffer.Events.Count(e => (string)e["type"]! == "energy_changed");
            oldState.Energy = 99;
            await frame();
            Check("obsolete energy state cannot append events", action.Buffer.Events.Count(e => (string)e["type"]! == "energy_changed") == energyCount);
            int blockCount = action.Buffer.Events.Count(e => (string)e["type"]! == "block_changed");
            await CreatureCmd.GainBlock(player.Creature, 3, ValueProp.Unpowered, null);
            await frame();
            Check("current creature has one effective subscription", action.Buffer.Events.Count(e => (string)e["type"]! == "block_changed") == blockCount + 1);
            await Replace();
            var second = action.Buffer.Events;
            Check("two replacements retain both opening histories", second.Count(e => (string)e["type"]! == "combat_started") == 2
                && second.Count(e => (string)e["type"]! == "card_drawn") == 10);
            Check("replacement boundaries do not leave sequence gaps", second.Select(e => (int)e["sequence"]!)
                .SequenceEqual(Enumerable.Range(1, second.Count)));
            Check("the latest battle controls readiness", scope.StopReason(true) == "player_ready" && !scope.Pending);
            samples.Add(new { name = "two_replacements", events = second.ToArray() });
        }
        Check("all action-owned journals are released", CombatJournalScope.Current == null && TurnCapture.Journal == null
            && CombatResourceJournal.Current == null && OrbJournal.Current == null && PotionJournal.Current == null);
        using (var action = new ActionEventScope())
        using (var scope = CombatJournalScope.Begin(player, observation))
        {
            var current = TurnCapture.Journal;
            int turn = player.PlayerCombatState!.TurnNumber;
            RunManager.Instance.ActionQueueSynchronizer.RequestEnqueue(new EndPlayerTurnAction(player, turn));
            await Ready(afterTurn: turn);
            Check("another turn in the same battle keeps its journal", ReferenceEquals(current, TurnCapture.Journal)
                && !action.Buffer.Events.Any(e => (string)e["type"]! == "combat_started"));
        }
        using (var action = new ActionEventScope(1))
        using (var scope = CombatJournalScope.Begin(player, observation))
        {
            action.Buffer.Add("fixture", new());
            await Replace();
            Check("handoffs retain the shared buffer bound", action.Buffer.Truncated && action.Buffer.Events.Count == 1
                && !JsonSerializer.SerializeToElement(scope.Result("player_ready")).GetProperty("complete").GetBoolean());
        }
        using (var action = new ActionEventScope())
        using (var scope = CombatJournalScope.Begin(player, observation))
        {
            await Replace(covered: true);
            Check("covered replacement never publishes a context marker", CombatObservation.Status() == "covered"
                && !action.Buffer.Events.Any(e => (string)e["type"]! == "combat_started"));
        }
        NRun.Instance!.GlobalUi.MapScreen.Close();
        await Ready();
        try
        {
            using var action = new ActionEventScope();
            using var scope = CombatJournalScope.Begin(player, observation);
            Check("the next action does not replay hidden markers or old history", action.Buffer.Events.Count == 0);
            throw new InvalidOperationException("fixture scope exit");
        }
        catch (InvalidOperationException error) when (error.Message == "fixture scope exit") { }
        Check("exception exit releases every active journal", CombatJournalScope.Current == null && TurnCapture.Journal == null
            && CombatResourceJournal.Current == null && OrbJournal.Current == null && ActionEventScope.Current == null);
        return new { passed, checks, samples };
    }
}
