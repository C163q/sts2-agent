using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Relics;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class CapacityChecks
{
    public static async Task<object> Run(Player player, Func<Task> frame, Func<CardModel, int> cardId, Func<string> observe)
    {
        var added = new List<RelicModel>();
        async Task<PhilosophersStone> Stone(bool wax = false)
        {
            var relic = ModelDb.Relic<PhilosophersStone>().ToMutable();
            relic.IsWax = wax;
            added.Add(relic);
            await RelicCmd.Obtain(relic, player);
            return (PhilosophersStone)relic;
        }
        var counter = VisibleUi.Descendants<NEnergyCounter>(NCombatRoom.Instance!.Ui.EnergyCounterContainer).Single();
        var label = counter.GetNode<CanvasItem>("Label");
        var inventory = NRun.Instance!.GlobalUi.RelicInventory;
        void Refresh() => HarmonyLib.AccessTools.Method(typeof(CombatStateTracker), "NotifyCombatStateChanged")
            .Invoke(CombatManager.Instance.StateTracker, ["capacity checks"]);
        async Task Settle()
        {
            Refresh();
            var deadline = DateTime.UtcNow.AddSeconds(8);
            do { await frame(); }
            while ((CombatObservation.Status() != "visible"
                || CombatObservation.Pair(VisibleUi.Text(counter, "Label")).maximum != player.PlayerCombatState!.MaxEnergy)
                && DateTime.UtcNow < deadline);
            if (DateTime.UtcNow >= deadline) throw new TimeoutException("Capacity label did not settle.");
            await frame();
        }
        var wax = await Stone(true);
        await Settle();
        string uiTitle = wax.Title.GetFormattedText();
        string uiLanguage = MegaCrit.Sts2.Core.Localization.LocManager.Instance.Language;
        using var scope = new ActionEventScope();
        using var resources = new RunResourceJournal(player, scope.Buffer);
        using var items = new RunInventoryJournal(player, scope.Buffer, cardId);
        using var journal = new TurnJournal(CombatManager.Instance.DebugOnlyGetState()!, player, cardId);
        var checks = new List<object>();
        bool passed = true;
        void Check(string name, bool ok) { checks.Add(new { name, passed = ok }); passed &= ok; }
        var countedHolder = inventory.RelicNodes.Single(holder => ReferenceEquals(holder.Relic.Model, wax));
        int heldRelics = inventory.RelicNodes.Count;
        bool CountMatches()
        {
            using var state = JsonDocument.Parse(observe());
            return state.RootElement.GetProperty("top_bar").TryGetProperty("relic_count", out var count)
                && count.ValueKind == JsonValueKind.Number && count.GetInt32() == heldRelics;
        }
        Check("relic count comes from the complete inventory", CountMatches());
        var originalPosition = countedHolder.Position;
        try
        {
            countedHolder.Position = new Vector2(-10000, -10000);
            Check("offscreen relic remains in the basic list", JsonSerializer.SerializeToElement(
                new CombatObservation().TopBar()).GetProperty("relics").EnumerateArray()
                .Any(relic => relic.GetProperty("name").GetString() == "Wax Philosopher's Stone"));
            Check("offscreen relic remains inspectable", RelicInspection.VisibleHolders()!.Contains(countedHolder));
            Check("offscreen relic still counts", CountMatches());
            Check("offscreen wax retains displayed unmelted state", RelicInspection.Melted(countedHolder.Relic) == false);
        }
        finally { countedHolder.Position = originalPosition; }
        bool holderEnabled = countedHolder.IsEnabled;
        try
        {
            countedHolder.Disable();
            Check("non-hoverable relic still counts", CountMatches());
            Check("non-hoverable relic retains static inspection", RelicInspection.VisibleHolders()!.Contains(countedHolder));
        }
        finally { if (holderEnabled) countedHolder.Enable(); }
        bool inventoryVisible = inventory.Visible;
        try
        {
            inventory.Visible = false;
            Check("hidden inventory count remains unknown", RelicInspection.HeldCount() == null);
            Check("hidden inventory cannot be inspected", RelicInspection.VisibleHolders() == null);
        }
        finally { inventory.Visible = inventoryVisible; }
        Dictionary<string, object?>[] Events(string type) => scope.Buffer.Events.Where(e => (string)e["type"]! == type).ToArray();
        try
        {
            var regular = await Stone();
            await Settle();
            Check("visible maximum energy gain", Events("max_energy_changed") is [var gain]
                && (int)gain["before"]! == 4 && (int)gain["after"]! == 5);
            await RelicCmd.Remove(regular);
            await Settle();
            Check("visible maximum energy loss", Events("max_energy_changed") is [_, var loss]
                && (int)loss["before"]! == 5 && (int)loss["after"]! == 4);
            label.Hide();
            await frame();
            var hiddenCapacity = await Stone();
            Refresh();
            await frame();
            Check("hidden capacity is omitted", Events("max_energy_changed").Length == 2);
            label.Show();
            await Settle();
            Check("restoring capacity does not replay", Events("max_energy_changed").Length == 2);
            await RelicCmd.Remove(hiddenCapacity);
            await Settle();
            Check("restored capacity uses public baseline", Events("max_energy_changed") is [_, _, var restored]
                && (int)restored["before"]! == 5 && (int)restored["after"]! == 4);
            await RelicCmd.Melt(wax);
            await Settle();
            Check("wax melting is recorded once", Events("relic_melted").Length == 1);
            Check("melting retains inventory membership", player.Relics.Contains(wax) && Events("relic_removed").Length == 2);
            Check("melting reduces visible capacity", Events("max_energy_changed") is [_, _, _, var melted]
                && (int)melted["before"]! == 4 && (int)melted["after"]! == 3);
            using var state = JsonDocument.Parse(observe());
            Check("observation shows melted icon", state.RootElement.GetProperty("top_bar").GetProperty("relics")
                .EnumerateArray().Any(r => r.GetProperty("name").GetString() == "Wax Philosopher's Stone"
                    && r.TryGetProperty("melted", out var value) && value.ValueKind == JsonValueKind.True));
            var lantern = ModelDb.Relic<Lantern>().ToMutable();
            added.Add(lantern);
            await RelicCmd.Obtain(lantern, player);
            await Settle();
            var ordinaryHolder = inventory.RelicNodes.Single(h => ReferenceEquals(h.Relic.Model, lantern));
            Check("ordinary relic melting is not applicable", RelicInspection.Melted(ordinaryHolder.Relic) == null);
            lantern.Status = RelicStatus.Disabled;
            await frame();
            Check("ordinary disabled relic melting stays not applicable", Events("relic_melted").Length == 1
                && RelicInspection.Melted(ordinaryHolder.Relic) == null);
            inventory.Hide();
            await frame();
            var hiddenWax = ModelDb.Relic<Lantern>().ToMutable();
            hiddenWax.IsWax = true;
            added.Add(hiddenWax);
            await RelicCmd.Obtain(hiddenWax, player);
            await RelicCmd.Melt(hiddenWax);
            await frame();
            Check("hidden melting is omitted", Events("relic_melted").Length == 1);
            inventory.Show();
            await Settle();
            Check("restoring relics does not replay melting", Events("relic_melted").Length == 1);
            var disabledWax = ModelDb.Relic<Lantern>().ToMutable();
            disabledWax.IsWax = true;
            added.Add(disabledWax);
            await RelicCmd.Obtain(disabledWax, player);
            disabledWax.Status = RelicStatus.Disabled;
            await Settle();
            var disabledHolder = inventory.RelicNodes.Single(h => ReferenceEquals(h.Relic.Model, disabledWax));
            await RelicCmd.Melt(disabledWax);
            await frame();
            Check("unrefreshed disabled wax never leaks model melting", Events("relic_melted").Length == 1
                && RelicInspection.Melted(disabledHolder.Relic) == false);
            HarmonyLib.AccessTools.Method(disabledHolder.GetType(), "RefreshStatus").Invoke(disabledHolder, null);
            await frame();
            Check("actual redraw without status notification publishes melting", Events("relic_melted").Length == 2
                && RelicInspection.Melted(disabledHolder.Relic) == true);
            var waxPosition = disabledHolder.Position;
            try
            {
                disabledHolder.Position = new Vector2(-10000, -10000);
                Check("offscreen wax retains actual melted display", RelicInspection.Melted(disabledHolder.Relic) == true);
            }
            finally { disabledHolder.Position = waxPosition; }
            await frame();
            Check("repeated visible redraw is not duplicated", Events("relic_melted").Length == 2);
            Check("wax event names are entirely English", Events("relic_melted").All(e =>
                !JsonSerializer.Serialize(e["relic"], new JsonSerializerOptions { Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping })
                    .Any(c => c >= '\u4e00' && c <= '\u9fff')));
            Check("name reads preserve native title and locale", wax.Title.GetFormattedText() == uiTitle
                && MegaCrit.Sts2.Core.Localization.LocManager.Instance.Language == uiLanguage);
            Check("shared sequences remain dense", scope.Buffer.Events.Select(e => (int)e["sequence"]!)
                .SequenceEqual(Enumerable.Range(1, scope.Buffer.Events.Count)));
            return new { passed, checks, events = scope.Buffer.Events.ToArray() };
        }
        finally
        {
            label.Show(); inventory.Show();
            foreach (var relic in added.Where(player.Relics.Contains)) await RelicCmd.Remove(relic);
        }
    }
}
