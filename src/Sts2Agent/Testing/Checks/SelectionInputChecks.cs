using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.Nodes.Cards;

namespace Sts2Agent;

internal static class SelectionInputChecks
{
    public static async Task<object> Run(GameAdapter adapter, CombatObservation observation, Func<Task> frame, Func<string> observe)
    {
        var selection = CardSelection.Current!;
        var checks = new List<object>();
        void Check(string name, bool passed) => checks.Add(new { name, passed });
        var holder = selection.Holders.First(h => h.CardNode != null && CardSelection.Clickable(h));
        var node = holder.CardNode!;
        var model = holder.CardModel!;
        int id = observation.CardId(model);
        var visibility = HarmonyLib.AccessTools.Field(typeof(NCard), "_visibility");
        var original = node.Visibility;
        var title = node.GetNode<Control>("%TitleLabel");
        bool titleVisible = title.Visible;
        try
        {
            visibility.SetValue(node, ModelVisibility.NotSeen);
            // NotSeen alone still exposes the native generic "Unknown" title.
            title.Visible = false;
            foreach (string kind in new[] { "card_selected", "card_deselected" })
            {
                using var before = JsonDocument.Parse(observe());
                var request = new Request(Guid.NewGuid().ToString("N"), "select_card",
                    before.RootElement.GetProperty("snapshot_id").GetString(), JsonSerializer.SerializeToElement(new { card_id = id }));
                using var response = JsonDocument.Parse(await adapter.Execute(request));
                var events = response.RootElement.GetProperty("state").GetProperty("transition").GetProperty("events");
                Check($"{kind} keeps unknown identity", events.GetArrayLength() == 1
                    && events[0].GetProperty("type").GetString() == kind
                    && events[0].GetProperty("card").GetProperty("id").GetInt32() == id
                    && events[0].GetProperty("card").GetProperty("name").ValueKind == JsonValueKind.Null);
            }
        }
        finally { visibility.SetValue(node, original); title.Visible = titleVisible; }
        Check("unknown identity checks restore selection", selection.Selected.Length == 0);

        var cards = selection.Cards.Take(2).ToArray();
        using (var scope = new ActionEventScope(1))
        {
            foreach (var card in cards)
            {
                using var snapshot = JsonDocument.Parse(observe());
                await SelectionActions.Click(selection, card, frame,
                    input => SelectionInputJournal.Record(selection, card, snapshot.RootElement, observation.CardId, input));
            }
            Check("selection feedback shares the bounded buffer", scope.Buffer.Events.Count == 1
                && scope.Buffer.Truncated && !TransitionResult.Complete("choice_required", scope.Buffer));
        }
        foreach (var card in cards) await SelectionActions.Click(selection, card, frame);
        Check("input checks release scope and restore selection", ActionEventScope.Current == null && selection.Selected.Length == 0);
        using (var scope = new ActionEventScope())
            Check("new action does not replay selection feedback", scope.Buffer.Events.Count == 0);
        return new { checks, passed = checks.All(c => JsonSerializer.SerializeToElement(c).GetProperty("passed").GetBoolean()) };
    }
}
