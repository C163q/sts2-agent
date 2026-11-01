using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Orbs;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Orbs;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class OrbEventChecks
{
    public static async Task<object> Run(Player player, Func<Task> frame, Func<CardModel, int> cardId)
    {
        var node = NCombatRoom.Instance!.GetCreatureNode(player.Creature)!;
        var manager = node.OrbManager!;
        var choice = new ThrowingPlayerChoiceContext();
        var checks = new List<object>();
        var samples = new List<object>();
        bool passed = true;
        void Check(string name, bool ok) { checks.Add(new { name, passed = ok }); passed &= ok; }
        async Task Settle()
        {
            var deadline = DateTime.UtcNow.AddSeconds(8);
            do { await frame(); }
            while ((OrbInspection.VisibleNodes(node) == null || RewardInspection.Animating(manager, "_curTween")
                || OrbInspection.DisplayedNodes(node)!.Any(slot => RewardInspection.Animating(slot, "_curTween")))
                && DateTime.UtcNow < deadline);
            if (DateTime.UtcNow >= deadline) throw new TimeoutException("Orb UI did not settle.");
        }
        async Task Reset(int capacity = 3)
        {
            OrbCmd.RemoveSlots(player, player.PlayerCombatState!.OrbQueue.Capacity);
            await OrbCmd.AddSlots(player, capacity);
            if (capacity > 0) await OrbCmd.Channel<FrostOrb>(choice, player);
            await Settle();
        }
        async Task<Dictionary<string, object?>[]> Capture(string name, Func<ActionEventScope, Task> action, int limit = 512)
        {
            using var scope = new ActionEventScope(limit);
            using var journal = new TurnJournal(CombatManager.Instance.DebugOnlyGetState()!, player, cardId);
            await action(scope);
            await frame();
            var events = scope.Buffer.Events.Where(e => ((string)e["type"]!).StartsWith("orb_")).ToArray();
            samples.Add(new { name, events, truncated = scope.Buffer.Truncated });
            Check(name + ": dense shared sequence", scope.Buffer.Events.Select(e => (int)e["sequence"]!)
                .SequenceEqual(Enumerable.Range(1, scope.Buffer.Events.Count)));
            return events;
        }
        static string Kind(Dictionary<string, object?> e) => (string)e["type"]!;
        static string Name(Dictionary<string, object?> e) => JsonSerializer.SerializeToElement(e["orb"]).GetProperty("name").GetString()!;
        await Reset();
        var events = await Capture("channel", async _ => { await OrbCmd.Channel<FrostOrb>(choice, player); await Settle(); });
        Check("same-name orbs retain their actual positions", events is [var channel] && Kind(channel) == "orb_channeled"
            && Name(channel) == "Frost" && (int)channel["slot_index"]! == 1);
        Check("identity events have no hidden values", events is [var identity] && identity.Keys.Order()
            .SequenceEqual(new[] { "orb", "sequence", "slot_index", "target", "type" }));
        events = await Capture("repeat_evoke", async _ =>
        {
            await OrbCmd.EvokeNext(choice, player, false);
            await OrbCmd.EvokeNext(choice, player, false);
            await Settle();
        });
        Check("non-removing evocations remain separate", events.Length == 2 && events.All(e => Kind(e) == "orb_evoked"
            && Name(e) == "Frost" && (int)e["slot_index"]! == 0));
        events = await Capture("remove_evoke", async _ => { await OrbCmd.EvokeLast(choice, player); await Settle(); });
        Check("evocation and departure remain distinct", events.Select(Kind).SequenceEqual(new[] { "orb_evoked", "orb_removed" })
            && events.All(e => Name(e) == "Frost" && (int)e["slot_index"]! == 1));
        await Reset(1);
        events = await Capture("full_queue", async _ => { await OrbCmd.Channel<PlasmaOrb>(choice, player); await Settle(); });
        Check("full queue evokes before channeling", events.Select(Kind).SequenceEqual(new[] {
            "orb_evoked", "orb_removed", "orb_channeled" }) && Name(events[0]) == "Frost"
            && Name(events[2]) == "Plasma" && events.All(e => (int)e["slot_index"]! == 0));
        await Reset();
        await OrbCmd.Channel<PlasmaOrb>(choice, player); await Settle();
        events = await Capture("shrink", async _ => { OrbCmd.RemoveSlots(player, 2); await Settle(); });
        Check("shrinking discards the tail without evoking", events.Select(Kind).SequenceEqual(new[] {
            "orb_removed", "orb_slots_changed" }) && Name(events[0]) == "Plasma"
            && (int)events[0]["slot_index"]! == 1 && (int)events[1]["before"]! == 3 && (int)events[1]["after"]! == 1);
        events = await Capture("zero", async _ =>
        {
            OrbCmd.RemoveSlots(player, 0); await OrbCmd.AddSlots(player, 0);
            manager.UpdateVisuals(MegaCrit.Sts2.Core.Entities.Cards.OrbEvokeType.None);
            await Settle();
        });
        Check("zero changes and visual refresh are omitted", events.Length == 0);
        events = await Capture("capacity_cap", async _ => { await OrbCmd.AddSlots(player, 99); await Settle(); });
        Check("capacity uses the displayed native cap", events is [var cap] && Kind(cap) == "orb_slots_changed"
            && (int)cap["before"]! == 1 && (int)cap["after"]! == 10);
        events = await Capture("already_capped", async _ => { await OrbCmd.AddSlots(player, 1); await Settle(); });
        Check("already capped capacity is not duplicated", events.Length == 0);
        await Reset();
        events = await Capture("hidden", async _ =>
        {
            manager.Hide(); await frame();
            await OrbCmd.AddSlots(player, 1); await OrbCmd.Channel<PlasmaOrb>(choice, player);
            await OrbCmd.EvokeNext(choice, player); await frame();
            manager.Show(); await Settle();
        });
        Check("hidden changes are omitted and never replayed", events.Length == 0);
        events = await Capture("restored", async _ => { await OrbCmd.AddSlots(player, 1); await Settle(); });
        Check("restored capacity uses the current public count", events is [var restored]
            && Kind(restored) == "orb_slots_changed" && (int)restored["before"]! == 4 && (int)restored["after"]! == 5);
        await Reset();
        events = await Capture("pending_hidden", async _ =>
        {
            await OrbCmd.Channel<PlasmaOrb>(choice, player);
            manager.Hide(); await frame();
            manager.Show(); await Settle();
        });
        Check("hiding during native entry cancels unpublished identity", events.Length == 0);
        await Reset();
        events = await Capture("entry_chain", async _ =>
        {
            await OrbCmd.Channel<PlasmaOrb>(choice, player);
            await OrbCmd.AddSlots(player, 2);
            await Settle();
        });
        Check("entry survives an immediate capacity change", events.Select(Kind).SequenceEqual(new[] {
            "orb_channeled", "orb_slots_changed" }) && Name(events[0]) == "Plasma"
            && (int)events[0]["slot_index"]! == 1 && (int)events[1]["before"]! == 3 && (int)events[1]["after"]! == 5);
        await Reset();
        events = await Capture("unseen_departure", async _ =>
        {
            await OrbCmd.Channel<PlasmaOrb>(choice, player);
            await OrbCmd.EvokeLast(choice, player);
            await Settle();
        });
        Check("immediate departure never publishes an unshown orb identity", events.Length == 0);
        await Reset();
        events = await Capture("visible_entry_evoke", async _ =>
        {
            await OrbCmd.Channel<PlasmaOrb>(choice, player);
            ulong createdFrame = OrbCapture.FrameNumber;
            var deadline = DateTime.UtcNow.AddSeconds(3);
            do { await frame(); }
            while (OrbInspection.VisibleNodes(node) == null && DateTime.UtcNow < deadline);
            var slot = OrbInspection.VisibleNodes(node)!.Single(s => s.Model is PlasmaOrb);
            Check("visible entry has crossed an actual drawing boundary", OrbCapture.FrameNumber > createdFrame);
            Check("partly entered orb is already public before tween completion", RewardInspection.Animating(slot, "_curTween"));
            await OrbCmd.EvokeLast(choice, player);
            await Settle();
        });
        Check("visible entry retains channel evocation and departure", events.Select(Kind).SequenceEqual(new[] {
            "orb_channeled", "orb_evoked", "orb_removed" }) && events.All(e => Name(e) == "Plasma"
                && (int)e["slot_index"]! == 1));
        await Reset();
        events = await Capture("entry_offscreen", async _ =>
        {
            await OrbCmd.Channel<PlasmaOrb>(choice, player);
            var slot = OrbInspection.DisplayedNodes(node)!.Last(s => s.Model != null);
            var sprite = (Node2D)CardSelection.Field(slot, "_sprite")!;
            var position = sprite.Position;
            try { sprite.Position = new(-10000, -10000); await frame(); }
            finally { sprite.Position = position; }
            await Settle();
        });
        Check("offscreen entry cancels pending identity without replay", events.Length == 0);
        events = await Capture("capacity_coalesces", async _ =>
        {
            await OrbCmd.AddSlots(player, 2);
            OrbCmd.RemoveSlots(player, 2);
            await Settle();
        });
        Check("unpublished capacity round trips are omitted", events.Length == 0);
        await Reset();
        events = await Capture("clipped", async _ =>
        {
            var bounds = OrbInspection.VisibleNodes(node)![0].GetNode<Control>("Bounds");
            var position = bounds.Position;
            try
            {
                bounds.Position = new(-10000, -10000); await frame();
                await OrbCmd.AddSlots(player, 1); await OrbCmd.Channel<PlasmaOrb>(choice, player);
            }
            finally { bounds.Position = position; }
            await Settle();
        });
        Check("offscreen existing orb blocks disclosure", events.Length == 0);
        await Reset();
        events = await Capture("covered", async _ =>
        {
            NRun.Instance!.GlobalUi.MapScreen.Open(); await frame();
            await OrbCmd.AddSlots(player, 1); await OrbCmd.Channel<PlasmaOrb>(choice, player);
            NRun.Instance.GlobalUi.MapScreen.Close(); await Settle();
        });
        Check("covered battlefield omits orb events", events.Length == 0);
        await Reset();
        events = await Capture("invalid_ui", async _ =>
        {
            bool threw = false;
            try { manager.RemoveSlotAnim(99); } catch (InvalidOperationException) { threw = true; }
            Check("invalid native UI call fails before mutation", threw);
            await OrbCmd.AddSlots(player, 1); await Settle();
        });
        Check("failed UI call leaves no stale capture", events is [var afterFailure] && Kind(afterFailure) == "orb_slots_changed"
            && (int)afterFailure["before"]! == 3 && (int)afterFailure["after"]! == 4);
        await Reset();
        events = await Capture("bounded", async scope =>
        {
            await OrbCmd.AddSlots(player, 1); await Settle();
            await OrbCmd.AddSlots(player, 1); await Settle();
            Check("orb events respect the shared buffer limit", scope.Buffer.Truncated && scope.Buffer.Events.Count == 1);
        }, 1);
        await Reset(0);
        events = await Capture("empty", async _ =>
        {
            await OrbCmd.EvokeNext(choice, player); await OrbCmd.Channel<PlasmaOrb>(choice, player); await frame();
        });
        Check("empty queue and zero-capacity failed channel are omitted", events.Length == 0);
        await Reset();
        Check("journal is released after every scope", OrbJournal.Current == null && TurnCapture.Journal == null);
        await OrbCmd.Channel<PlasmaOrb>(choice, player); await Settle();
        events = await Capture("fresh", async _ => { await frame(); });
        Check("outside-action changes never replay into the next action", events.Length == 0);
        return new { passed, checks, samples };
    }
}
