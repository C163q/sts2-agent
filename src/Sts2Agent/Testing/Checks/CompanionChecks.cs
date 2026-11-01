using System.Text.Json;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.ValueProps;

namespace Sts2Agent;

internal static class CompanionChecks
{
    public static async Task<object> Run(Player player, Func<Task> frame, Func<CardModel, int> cardId, Func<string> observe)
    {
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        var choice = new ThrowingPlayerChoiceContext();
        var osty = player.Osty!;
        var node = NCombatRoom.Instance!.GetCreatureNode(osty)!;
        var checks = new List<object>();
        var samples = new List<object>();
        bool passed = true;
        void Check(string name, bool ok) { checks.Add(new { name, passed = ok }); passed &= ok; }
        JsonElement Read() => JsonSerializer.Deserialize<JsonElement>(observe());
        async Task Settle()
        {
            AccessTools.Method(typeof(CombatStateTracker), "NotifyCombatStateChanged")
                .Invoke(CombatManager.Instance.StateTracker, ["companion checks"]);
            var deadline = DateTime.UtcNow.AddSeconds(6);
            do { await frame(); }
            while ((CombatMotion.Pending() || osty.IsAlive && CombatObservation.Health(node).maximum != osty.MaxHp)
                && DateTime.UtcNow < deadline);
            if (DateTime.UtcNow >= deadline) throw new TimeoutException("Companion UI did not settle.");
            await frame();
        }
        var label = node.GetNode<NCreatureStateDisplay>("%HealthBar").GetNode<NHealthBar>("%HealthBar")
            .GetNode<CanvasItem>("%HpLabel");
        var initial = Read();
        Check("Osty is an ally rather than an enemy", initial.GetProperty("allies").GetArrayLength() == 1
            && !initial.GetProperty("enemies").EnumerateArray().Any(e => e.GetProperty("name").GetString() == "Osty"));
        Check("shared block is explicitly identified", initial.GetProperty("allies")[0].GetProperty("block_shared_with").GetString() == "player");
        node.Hide();
        try { Check("a hidden ally is omitted", Read().GetProperty("allies").GetArrayLength() == 0); }
        finally { node.Show(); }
        label.Hide();
        try { Check("hidden health is not read from the model", Read().GetProperty("allies")[0].GetProperty("hp").ValueKind == JsonValueKind.Null); }
        finally { label.Show(); }
        await Settle();
        using (var action = new ActionEventScope())
        using (var journal = new TurnJournal(combat, player, cardId))
        {
            int before = osty.MaxHp;
            await OstyCmd.Summon(choice, player, 5, null);
            await Settle();
            var growth = action.Buffer.Events.Where(e => (string)e["type"]! == "max_hp_changed").ToArray();
            Check("summon growth records the visible maximum HP endpoints", growth is [var change]
                && (int)change["before"]! == before && (int)change["after"]! == before + 5);
            samples.Add(new { scenario = "growth", events = action.Buffer.Events });
            int count = action.Buffer.Events.Count;
            label.Hide(); await frame();
            await OstyCmd.Summon(choice, player, 2, null);
            await frame();
            Check("hidden summon health is not published", action.Buffer.Events.Count == count);
            label.Show(); await Settle();
            Check("restoring health does not replay hidden growth", action.Buffer.Events.Count == count);
            await OstyCmd.Summon(choice, player, 3, null);
            await Settle();
            growth = action.Buffer.Events.Where(e => (string)e["type"]! == "max_hp_changed").ToArray();
            Check("later growth uses the restored public baseline", growth.Length == 2
                && (int)growth[1]["before"]! == before + 7 && (int)growth[1]["after"]! == before + 10);
        }
        foreach (var scenario in new[] { (name: "partial block", hp: 20, block: 3, loss: 0),
            (name: "overflow", hp: 2, block: 3, loss: 5), (name: "full block", hp: 20, block: 12, loss: 0) })
        {
            if (player.IsOstyMissing) await OstyCmd.Summon(choice, player, scenario.hp, null);
            else { await CreatureCmd.SetMaxHp(osty, scenario.hp); await CreatureCmd.Heal(osty, scenario.hp); }
            await CreatureCmd.LoseBlock(player.Creature, player.Creature.Block);
            await CreatureCmd.GainBlock(player.Creature, scenario.block, ValueProp.Unpowered, null);
            await Settle();
            using var action = new ActionEventScope();
            using var journal = new TurnJournal(combat, player, cardId);
            int playerHp = player.Creature.CurrentHp;
            await CreatureCmd.Damage(choice, player.Creature, 10, ValueProp.Move, combat.Enemies.First());
            await Settle();
            journal.Flush();
            var damage = action.Buffer.Events.Where(e => (string)e["type"]! == "damage").ToArray();
            Check(scenario.name + " retains actual blocked damage once", damage.Sum(e => (int)e["blocked"]!) == Math.Min(10, scenario.block));
            Check(scenario.name + " follows the native HP split", playerHp - player.Creature.CurrentHp == scenario.loss);
            samples.Add(new { scenario = scenario.name, events = action.Buffer.Events });
        }
        Check("capture subscriptions are released", TurnCapture.Journal == null);
        await CreatureCmd.LoseBlock(player.Creature, player.Creature.Block);
        await CreatureCmd.GainBlock(player.Creature, 12, ValueProp.Unpowered, null);
        await Settle();
        var playerBlock = NCombatRoom.Instance!.GetCreatureNode(player.Creature)!.GetNode<NCreatureStateDisplay>("%HealthBar")
            .GetNode<NHealthBar>("%HealthBar").GetNode<CanvasItem>("%BlockLabel");
        playerBlock.Hide();
        try
        {
            await frame();
            using var action = new ActionEventScope();
            using var journal = new TurnJournal(combat, player, cardId);
            await CreatureCmd.Damage(choice, player.Creature, 10, ValueProp.Move, combat.Enemies.First());
            await Settle();
            journal.Flush();
            Check("block-only fallback does not reveal a hidden block label", !action.Buffer.Events.Any(e =>
                (string)e["type"]! == "damage" && (int)e["blocked"]! > 0));
            samples.Add(new { scenario = "hidden block", events = action.Buffer.Events });
        }
        finally { playerBlock.Show(); }
        return new { passed, checks, samples };
    }
}
