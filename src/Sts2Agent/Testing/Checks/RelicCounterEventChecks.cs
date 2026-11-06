using System.Reflection;
using Godot;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Nodes;

namespace Sts2Agent;

internal static class RelicCounterEventChecks
{
    public static async Task<object> Run(Player player, Func<Task> frame)
    {
        var girya = player.GetRelic<Girya>()!;
        var holder = NRun.Instance!.GlobalUi.RelicInventory.RelicNodes.Single(h => ReferenceEquals(h.Relic.Model, girya));
        var inventory = NRun.Instance.GlobalUi.RelicInventory;
        var bar = NRun.Instance.GlobalUi.TopBar;
        var label = holder.GetNode<Control>("%AmountLabel");
        int original = girya.TimesLifted;
        var position = holder.Position;
        var color = holder.Modulate;
        bool enabled = holder.IsEnabled;
        bool labelVisible = label.Visible;
        var checks = new List<object>();
        bool passed = true;
        void Check(string name, bool ok) { checks.Add(new { name, passed = ok }); passed &= ok; }
        using var scope = new ActionEventScope();
        var journal = new RelicCounterJournal(player, scope.Buffer);
        int Count() => scope.Buffer.Events.Count;
        void Advance() => girya.TimesLifted++;
        try
        {
            Check("initial display only establishes baseline", Count() == 0);
            Advance();
            Check("native label refresh captures immediately", Count() == 1
                && (int)scope.Buffer.Events[0]["before"]! == original && (int)scope.Buffer.Events[0]["after"]! == original + 1);
            girya.TimesLifted = girya.TimesLifted;
            journal.SampleVisibility();
            Check("duplicate notifications and observation do not repeat", Count() == 1);
            Advance(); Advance();
            Check("same-frame native refreshes retain both steps", Count() == 3
                && (int)scope.Buffer.Events[1]["after"]! == original + 2 && (int)scope.Buffer.Events[2]["after"]! == original + 3);
            foreach (var hidden in new CanvasItem[] { inventory, bar, holder.Relic.Icon })
            {
                int count = Count();
                try
                {
                    hidden.Hide(); journal.SampleVisibility(); Advance();
                    Check("hidden counter mutation omitted: " + hidden.Name, Count() == count);
                }
                finally { hidden.Show(); }
                journal.SampleVisibility();
                Check("restoring display never replays hidden mutation: " + hidden.Name, Count() == count);
                Advance();
                Check("restored display establishes a new baseline: " + hidden.Name, Count() == count + 1);
            }
            int before = Count();
            holder.Modulate = new Color(color, 0); journal.SampleVisibility(); Advance();
            holder.Modulate = color; journal.SampleVisibility();
            Check("transparent holder never replays", Count() == before);
            holder.Position = new Vector2(-10000, -10000); Advance();
            Check("offscreen held relic retains counter changes", Count() == before + 1);
            holder.Position = position;
            holder.Disable(); Advance();
            Check("non-hoverable held relic retains counter changes", Count() == before + 2);
            if (enabled) holder.Enable();
            before = Count();
            label.Hide(); journal.SampleVisibility();
            Check("visible icon with absent counter keeps null after", Count() == before + 1
                && scope.Buffer.Events[^1]["after"] == null);
            label.Show(); journal.SampleVisibility();
            Check("counter appearance keeps null before", Count() == before + 2
                && scope.Buffer.Events[^1]["before"] == null);
            before = Count();
            var stored = typeof(Girya).GetField("_timesLifted", BindingFlags.Instance | BindingFlags.NonPublic)!;
            stored.SetValue(girya, girya.TimesLifted + 1);
            journal.SampleVisibility();
            Check("unrendered model values are never substituted", Count() == before);
            HarmonyLib.AccessTools.Method(holder.GetType(), "RefreshAmount").Invoke(holder, null);
            Check("actual label refresh exposes the changed value", Count() == before + 1);
            before = Count();
            journal.Dispose(); Advance(); journal.SampleVisibility();
            Check("disposed capture never receives further redraws", Count() == before && RelicCounterJournal.Current == null);
            using (var next = new RelicCounterJournal(player, scope.Buffer))
            {
                Check("new action baseline does not replay earlier changes", Count() == before);
                Advance();
                Check("next capture records only its own change", Count() == before + 1);
            }
            Check("counter event names are English", scope.Buffer.Events.All(e =>
                System.Text.Json.JsonSerializer.Serialize(e["relic"]).Contains("Girya")));
            Check("shared event sequences are dense", scope.Buffer.Events.Select(e => (int)e["sequence"]!)
                .SequenceEqual(Enumerable.Range(1, Count())));
            return new { passed, checks, events = scope.Buffer.Events.ToArray() };
        }
        finally
        {
            journal.Dispose();
            inventory.Show(); bar.Show(); holder.Relic.Icon.Show(); holder.Modulate = color; holder.Position = position;
            if (enabled) holder.Enable();
            girya.TimesLifted = original; label.Visible = labelVisible;
            await frame();
        }
    }
}
