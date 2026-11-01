using Godot;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.sts2.Core.Nodes.TopBar;

namespace Sts2Agent;

internal static class RunResourceChecks
{
    public static async Task<object> Covered(Player player, Func<Task> frame)
    {
        var choice = CardSelection.Current ?? throw new InvalidOperationException("Expected a pending native selection.");
        var game = NGame.Instance!;
        var map = NRun.Instance!.GlobalUi.MapScreen;
        int hp = player.Creature.CurrentHp, maximum = player.Creature.MaxHp, gold = player.Gold;
        using var events = new ActionEventScope();
        using var resources = new RunResourceJournal(player, events.Buffer);
        var checks = new List<object>();
        bool passed = true;
        try
        {
            foreach (string cover in new[] { "card_details", "map" })
            {
                if (cover == "card_details") game.GetInspectCardScreen().Open(choice.Cards.ToList(), 0);
                else map.Open();
                await frame();
                resources.SampleVisibility();
                int before = events.Buffer.Events.Count;
                await CreatureCmd.SetMaxHp(player.Creature, maximum + 1);
                await CreatureCmd.SetCurrentHp(player.Creature, hp - 1);
                await PlayerCmd.GainGold(1, player);
                await CreatureCmd.SetMaxHp(player.Creature, maximum);
                await CreatureCmd.SetCurrentHp(player.Creature, hp);
                await PlayerCmd.SetGold(gold, player);
                bool ok = choice.Status == "covered" && events.Buffer.Events.Count == before;
                checks.Add(new { name = cover + "_masks_native_selection_resources", passed = ok });
                passed &= ok;
                if (cover == "card_details") game.GetInspectCardScreen().Close();
                else map.Close();
                DateTime deadline = DateTime.UtcNow.AddSeconds(8);
                while (choice.Status != "visible" || RunUi.ResourceMotionPending())
                {
                    if (DateTime.UtcNow >= deadline) throw new TimeoutException("Resource mask check did not close.");
                    await frame();
                }
                resources.SampleVisibility();
            }
            return new { passed, checks, events = events.Buffer.Events };
        }
        finally
        {
            if (VisibleUi.Shown(game.InspectCardScreen)) game.GetInspectCardScreen().Close();
            if (VisibleUi.Shown(map)) map.Close();
            await CreatureCmd.SetMaxHp(player.Creature, maximum);
            await CreatureCmd.SetCurrentHp(player.Creature, hp);
            await PlayerCmd.SetGold(gold, player);
        }
    }

    public static async Task<object> Run(Player player, Func<Task> frame)
    {
        var checks = new List<object>();
        bool passed = true;
        void Check(string name, bool ok) { checks.Add(new { name, passed = ok }); passed &= ok; }
        int hp = player.Creature.CurrentHp, maximum = player.Creature.MaxHp, gold = player.Gold;
        var top = NRun.Instance!.GlobalUi.TopBar;
        var hpNode = VisibleUi.Descendants<NTopBarHp>(top).Single();
        var hpLabel = hpNode.GetNode<CanvasItem>("%HpLabel");
        var goldLabel = top.Gold.GetNode<CanvasItem>("%GoldLabel");
        bool topVisible = top.Visible, hpVisible = hpLabel.Visible, goldVisible = goldLabel.Visible;
        using var events = new ActionEventScope();
        using var resources = new RunResourceJournal(player, events.Buffer);
        async Task Quiet()
        {
            DateTime deadline = DateTime.UtcNow.AddSeconds(8);
            while (RunUi.ResourceMotionPending())
            {
                if (DateTime.UtcNow >= deadline) throw new TimeoutException("Resource check animation did not settle.");
                await frame();
            }
            resources.SampleVisibility();
        }
        try
        {
            await PlayerCmd.GainGold(7, player); await Quiet();
            await PlayerCmd.LoseGold(7, player); await Quiet();
            var gains = events.Buffer.Events.Where(e => (string)e["type"]! == "gold_changed").ToArray();
            Check("gold_preserves_gain_and_loss", gains.Length == 2 && (int)gains[0]["before"]! == gold
                && (int)gains[0]["after"]! == gold + 7 && (int)gains[1]["after"]! == gold);
            int start = events.Buffer.Events.Count;
            await CreatureCmd.SetCurrentHp(player.Creature, hp - 1);
            await CreatureCmd.SetCurrentHp(player.Creature, hp);
            Check("hp_preserves_intermediate_changes", events.Buffer.Events.Count == start + 2);
            start = events.Buffer.Events.Count;
            await CreatureCmd.GainMaxHp(player.Creature, 2);
            await CreatureCmd.SetMaxHp(player.Creature, maximum);
            var maximums = events.Buffer.Events.Skip(start).Where(e => (string)e["type"]! == "max_hp_changed").ToArray();
            Check("maximum_hp_gain_and_loss", maximums.Length == 2 && (int)maximums[0]["after"]! == maximum + 2
                && (int)maximums[1]["after"]! == maximum);
            await CreatureCmd.SetCurrentHp(player.Creature, hp);

            foreach (bool hideTop in new[] { true, false })
            {
                start = events.Buffer.Events.Count;
                if (hideTop) top.Visible = false;
                else { hpLabel.Visible = false; goldLabel.Visible = false; }
                resources.SampleVisibility();
                await CreatureCmd.SetCurrentHp(player.Creature, hp - 1);
                await CreatureCmd.SetMaxHp(player.Creature, maximum + 1);
                await PlayerCmd.GainGold(1, player);
                await CreatureCmd.SetMaxHp(player.Creature, maximum);
                await CreatureCmd.SetCurrentHp(player.Creature, hp);
                await PlayerCmd.LoseGold(1, player);
                Check(hideTop ? "hidden_top_bar_omits_changes" : "hidden_resource_labels_omit_changes",
                    events.Buffer.Events.Count == start);
                top.Visible = topVisible; hpLabel.Visible = hpVisible; goldLabel.Visible = goldVisible;
                await Quiet();
                Check("restoring_visibility_does_not_replay_hidden_changes", events.Buffer.Events.Count == start);
            }
            start = events.Buffer.Events.Count;
            hpLabel.Visible = false; goldLabel.Visible = false;
            resources.SampleVisibility();
            await CreatureCmd.SetMaxHp(player.Creature, maximum + 1);
            await CreatureCmd.SetCurrentHp(player.Creature, hp - 2);
            await PlayerCmd.GainGold(5, player);
            hpLabel.Visible = hpVisible; goldLabel.Visible = goldVisible;
            await Quiet();
            Check("lasting_hidden_changes_are_not_replayed", events.Buffer.Events.Count == start);
            await CreatureCmd.SetMaxHp(player.Creature, maximum + 2);
            await CreatureCmd.SetCurrentHp(player.Creature, hp - 1);
            await PlayerCmd.LoseGold(1, player); await Quiet();
            var resumed = events.Buffer.Events.Skip(start).ToArray();
            Check("visible_changes_use_the_restored_public_baseline", resumed.Length == 3
                && (string)resumed[0]["type"]! == "max_hp_changed" && (int)resumed[0]["before"]! == maximum + 1
                && (string)resumed[1]["type"]! == "hp_changed" && (int)resumed[1]["before"]! == hp - 2
                && (string)resumed[2]["type"]! == "gold_changed" && (int)resumed[2]["before"]! == gold + 5);
            await CreatureCmd.SetMaxHp(player.Creature, maximum);
            await CreatureCmd.SetCurrentHp(player.Creature, hp);
            await PlayerCmd.SetGold(gold, player); await Quiet();
            start = events.Buffer.Events.Count;
            await CreatureCmd.SetCurrentHp(player.Creature, hp);
            await CreatureCmd.SetMaxHp(player.Creature, maximum);
            await PlayerCmd.GainGold(0, player);
            Check("unchanged_values_do_not_create_events", events.Buffer.Events.Count == start);
            resources.Dispose();
            await PlayerCmd.GainGold(1, player);
            await PlayerCmd.LoseGold(1, player); await Quiet();
            Check("disposed_subscription_does_not_record", events.Buffer.Events.Count == start && RunResourceJournal.Current == null);
            Check("resources_restored", player.Creature.CurrentHp == hp && player.Creature.MaxHp == maximum && player.Gold == gold);
            return new { passed, checks, events = events.Buffer.Events };
        }
        finally
        {
            top.Visible = topVisible; hpLabel.Visible = hpVisible; goldLabel.Visible = goldVisible;
            await CreatureCmd.SetMaxHp(player.Creature, maximum);
            await CreatureCmd.SetCurrentHp(player.Creature, hp);
            await PlayerCmd.SetGold(gold, player);
        }
    }
}
