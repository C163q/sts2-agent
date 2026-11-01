using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class CombatResourceChecks
{
    public static async Task<object> Run(Player player, Func<Task> frame, Func<CardModel, int> cardId)
    {
        var state = player.PlayerCombatState!;
        int originalEnergy = state.Energy, originalStars = state.Stars;
        var ui = NCombatRoom.Instance!.Ui;
        var energyLabel = VisibleUi.Descendants<NEnergyCounter>(ui.EnergyCounterContainer).Single().GetNode<CanvasItem>("Label");
        var stars = VisibleUi.Descendants<NStarCounter>(ui).Single();
        var starLabel = stars.GetNode<CanvasItem>("%CountLabel");
        int? Energy() => CombatObservation.Pair(VisibleUi.Text(energyLabel.GetParent(), "Label")).current;
        int? Stars() => VisibleUi.Number(stars, "%CountLabel");
        async Task Settle()
        {
            var deadline = DateTime.UtcNow.AddSeconds(8);
            do { await frame(); }
            while ((CombatObservation.Status() != "visible" || Energy() != state.Energy || Stars() != state.Stars)
                && DateTime.UtcNow < deadline);
            if (DateTime.UtcNow >= deadline) throw new TimeoutException("Combat counter did not show its current value.");
            await frame();
        }
        await PlayerCmd.SetEnergy(5, player);
        await PlayerCmd.SetStars(3, player);
        await Settle();
        using var scope = new ActionEventScope();
        using var journal = new TurnJournal(CombatManager.Instance.DebugOnlyGetState()!, player, cardId);
        var checks = new List<object>();
        bool passed = true;
        void Check(string name, bool ok) { checks.Add(new { name, passed = ok }); passed &= ok; }
        try
        {
            await PlayerCmd.GainEnergy(1, player);
            await Settle();
            await PlayerCmd.LoseEnergy(1, player);
            await Settle();
            Check("separate visible energy changes retain both endpoints", scope.Buffer.Events.Count == 2
                && (int)scope.Buffer.Events[0]["before"]! == 5 && (int)scope.Buffer.Events[0]["after"]! == 6
                && (int)scope.Buffer.Events[1]["before"]! == 6 && (int)scope.Buffer.Events[1]["after"]! == 5);
            int count = scope.Buffer.Events.Count;
            await PlayerCmd.GainStars(2, player);
            Check("unrendered star target is withheld", scope.Buffer.Events.Count == count);
            await Settle();
            Check("star counter animation emits one final change", scope.Buffer.Events.Count == count + 1
                && (int)scope.Buffer.Events[^1]["before"]! == 3 && (int)scope.Buffer.Events[^1]["after"]! == 5);
            await PlayerCmd.LoseStars(1, player);
            await Settle();
            Check("synchronous star spending is recorded once", scope.Buffer.Events.Count == count + 2
                && (int)scope.Buffer.Events[^1]["before"]! == 5 && (int)scope.Buffer.Events[^1]["after"]! == 4);

            foreach (string cover in new[] { "energy_label", "star_label", "map", "combat_ui" })
            {
                count = scope.Buffer.Events.Count;
                if (cover == "energy_label") energyLabel.Hide();
                else if (cover == "star_label") starLabel.Hide();
                else if (cover == "combat_ui") ui.Hide();
                else NRun.Instance!.GlobalUi.MapScreen.Open();
                await frame();
                if (cover != "star_label") await PlayerCmd.GainEnergy(2, player);
                if (cover != "energy_label") await PlayerCmd.GainStars(2, player);
                await frame();
                Check("covered resource values are omitted: " + cover, scope.Buffer.Events.Count == count);
                if (cover == "energy_label") energyLabel.Show();
                else if (cover == "star_label") starLabel.Show();
                else if (cover == "combat_ui") ui.Show();
                else NRun.Instance!.GlobalUi.MapScreen.Close();
                await Settle();
                Check("uncovering never replays hidden changes: " + cover, scope.Buffer.Events.Count == count);
            }

            count = scope.Buffer.Events.Count;
            await PlayerCmd.GainStars(5, player);
            starLabel.Hide();
            await frame();
            starLabel.Show();
            await Settle();
            Check("covering a pending star animation cancels publication", scope.Buffer.Events.Count == count);
            int publicEnergy = Energy()!.Value;
            await PlayerCmd.GainEnergy(1, player);
            await Settle();
            Check("visible changes resume from the restored public baseline", scope.Buffer.Events.Count == count + 1
                && (int)scope.Buffer.Events[^1]["before"]! == publicEnergy);
            count = scope.Buffer.Events.Count;
            journal.Dispose();
            await PlayerCmd.GainEnergy(1, player);
            await PlayerCmd.GainStars(1, player);
            await Settle();
            Check("disposed combat subscriptions never record later changes", scope.Buffer.Events.Count == count);
            return new { passed, checks, events = scope.Buffer.Events };
        }
        finally
        {
            energyLabel.Show();
            starLabel.Show();
            ui.Show();
            if (NRun.Instance!.GlobalUi.MapScreen.IsOpen) NRun.Instance.GlobalUi.MapScreen.Close();
            journal.Dispose();
            await PlayerCmd.SetEnergy(originalEnergy, player);
            await PlayerCmd.SetStars(originalStars, player);
            await Settle();
        }
    }

    public static async Task<object> FirstReveal(Player player, Func<Task> frame, Func<CardModel, int> cardId)
    {
        var counter = VisibleUi.Descendants<NStarCounter>(NCombatRoom.Instance!.Ui).Single();
        var label = counter.GetNode<CanvasItem>("%CountLabel");
        if (player.PlayerCombatState!.Stars != 0 || VisibleUi.OnScreen(counter))
            throw new InvalidOperationException("Expected a never-revealed star counter.");
        using var scope = new ActionEventScope();
        using var journal = new TurnJournal(CombatManager.Instance.DebugOnlyGetState()!, player, cardId);
        var checks = new List<object>();
        bool passed = true;
        void Check(string name, bool ok) { checks.Add(new { name, passed = ok }); passed &= ok; }
        object? firstLayout = null;
        try
        {
            await PlayerCmd.GainStars(1, player);
            firstLayout = new { size = ((Control)label).Size.ToString(), bounds = ((Control)label).GetGlobalRect().ToString(),
                text = (label as RichTextLabel)?.GetParsedText(), onscreen = VisibleUi.OnScreen(label) };
            Check("first star waits for its label layout", scope.Buffer.Events.Count == 0 && CombatResourceJournal.Current!.Pending);
            label.Hide();
            await frame();
            label.Show();
            async Task Settle()
            {
                var deadline = DateTime.UtcNow.AddSeconds(8);
                do { await frame(); } while (VisibleUi.Number(counter, "%CountLabel") != player.PlayerCombatState.Stars && DateTime.UtcNow < deadline);
                if (DateTime.UtcNow >= deadline) throw new TimeoutException("Revealed star count did not settle.");
                await frame();
            }
            await Settle();
            Check("covering a first reveal never replays it on restoration", scope.Buffer.Events.Count == 0);
            await PlayerCmd.GainStars(1, player);
            await Settle();
            Check("subsequent stars use the now-public baseline", scope.Buffer.Events.Count == 1
                && (int)scope.Buffer.Events[0]["before"]! == 1 && (int)scope.Buffer.Events[0]["after"]! == 2);
            var control = (Control)label;
            Vector2 position = control.Position;
            bool clipping = counter.ClipContents;
            foreach (string mask in new[] { "offscreen", "clipped", "pending_offscreen" })
            {
                int count = scope.Buffer.Events.Count;
                control.Position = position + new Vector2(10000, 0);
                await frame();
                if (mask == "pending_offscreen") control.Position = position;
                else if (mask == "clipped")
                {
                    counter.ClipContents = true;
                    control.Position = position + new Vector2(counter.Size.X + control.Size.X + 2, 0);
                }
                await PlayerCmd.GainStars(1, player);
                if (mask == "pending_offscreen") control.Position = position + new Vector2(10000, 0);
                await frame();
                Check("offscreen or clipped star label is excluded: " + mask, !VisibleUi.OnScreen(label)
                    && VisibleUi.OnScreen(counter) && scope.Buffer.Events.Count == count);
                control.Position = position;
                counter.ClipContents = clipping;
                await Settle();
                Check("restoring star label never replays a hidden reveal: " + mask, scope.Buffer.Events.Count == count);
            }
            return new { passed, checks, first_layout = firstLayout, events = scope.Buffer.Events };
        }
        finally
        {
            label.Show();
            journal.Dispose();
            await PlayerCmd.SetStars(0, player);
            counter.Hide();
        }
    }
}
