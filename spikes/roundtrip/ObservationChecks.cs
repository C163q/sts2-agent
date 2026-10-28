using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class ObservationChecks
{
    private static bool completed;

    public static void Run(string reportPath)
    {
        var room = NCombatRoom.Instance;
        if (completed || room?.Ui.Hand.ActiveHolders.Count != 5 || CombatObservation.Status() != "visible")
            return;
        var results = new List<object>();
        var reader = new GameAdapter(false);
        var card = room.Ui.Hand.ActiveHolders[0].CardNode!;
        var enemy = room.CreatureNodes.First(node => node.Entity.IsMonster);
        var hpLabel = enemy.GetNode<NCreatureStateDisplay>("%HealthBar")
            .GetNode<NHealthBar>("%HealthBar").GetNode<Label>("%HpLabel");

        JsonElement Read() => JsonSerializer.Deserialize<JsonElement>(reader.Observe());
        void Check(string name, Func<JsonElement, bool> condition)
        {
            bool passed = condition(Read());
            results.Add(new { name, passed });
            if (!passed)
                throw new InvalidOperationException("Observation filter check failed: " + name);
        }
        void Hide(CanvasItem item, Action check)
        {
            bool visible = item.Visible;
            try { item.Visible = false; check(); }
            finally { item.Visible = visible; }
        }
        try
        {
            Check("visible_card_baseline", state => state.GetProperty("player").GetProperty("hand").GetArrayLength() == 5);
            Hide(card, () => Check("hidden_card_excluded", state =>
                state.GetProperty("player").GetProperty("hand").GetArrayLength() == 4));
            Vector2 position = room.Ui.Hand.Position;
            try
            {
                room.Ui.Hand.Position += new Vector2(0, 10000);
                Check("offscreen_cards_excluded", state => state.GetProperty("player").GetProperty("hand").GetArrayLength() == 0);
            }
            finally { room.Ui.Hand.Position = position; }
            Color color = room.Ui.Hand.Modulate;
            try
            {
                room.Ui.Hand.Modulate = new Color(color, 0);
                Check("transparent_parent_excluded", state => state.GetProperty("player").GetProperty("hand").ValueKind == JsonValueKind.Null);
            }
            finally { room.Ui.Hand.Modulate = color; }
            var cost = card.GetNode<Label>("%EnergyLabel");
            string costText = cost.Text;
            try
            {
                cost.Text = "-1";
                Hide(card.GetNode<Control>("%EnergyIcon"), () => Check("hidden_negative_cost_excluded", state =>
                    state.GetProperty("player").GetProperty("hand")[0].GetProperty("energy_cost").ValueKind == JsonValueKind.Null));
            }
            finally { cost.Text = costText; }
            Color costColor = cost.GetThemeColor("font_color");
            bool hadColorOverride = cost.HasThemeColorOverride("font_color");
            try
            {
                cost.AddThemeColorOverride("font_color", Colors.Red);
                Check("displayed_cost_color_preserved", state => state.GetProperty("player").GetProperty("hand")[0]
                    .GetProperty("energy_cost_color").GetString() == "#ff0000");
            }
            finally
            {
                if (hadColorOverride)
                    cost.AddThemeColorOverride("font_color", costColor);
                else
                    cost.RemoveThemeColorOverride("font_color");
            }
            var material = (ShaderMaterial)card.CardHighlight.Material;
            Variant width = material.GetShaderParameter("width");
            try
            {
                material.SetShaderParameter("width", 0);
                Check("zero_width_outline_excluded", state => state.GetProperty("player").GetProperty("hand")[0]
                    .GetProperty("outline").ValueKind == JsonValueKind.Null);
            }
            finally { material.SetShaderParameter("width", width); }
            Hide(hpLabel, () => Check("hidden_hp_numbers_excluded", state =>
            {
                var observed = state.GetProperty("enemies").EnumerateArray().First(e => e.GetProperty("id").GetUInt32() == enemy.Entity.CombatId);
                return observed.GetProperty("hp").ValueKind == JsonValueKind.Null
                    && observed.GetProperty("max_hp").ValueKind == JsonValueKind.Null;
            }));
            Hide(enemy.IntentContainer, () => Check("hidden_intent_excluded", state => state.GetProperty("enemies")
                .EnumerateArray().First(e => e.GetProperty("id").GetUInt32() == enemy.Entity.CombatId)
                .GetProperty("intents").ValueKind == JsonValueKind.Null));
            Hide(NRun.Instance!.GlobalUi.TopBar.Gold.GetNode<Label>("%GoldLabel"), () =>
                Check("hidden_gold_excluded", state => state.GetProperty("top_bar").GetProperty("gold").ValueKind == JsonValueKind.Null));
            var transition = NGame.Instance!.Transition.GetNode<Control>("SimpleTransition");
            bool transitionVisible = transition.Visible;
            Color transitionColor = transition.Modulate;
            try
            {
                transition.Visible = true;
                transition.Modulate = Colors.White;
                Check("covered_combat_excluded", state => state.GetProperty("screen").GetProperty("status").GetString() == "covered"
                    && state.GetProperty("player").ValueKind == JsonValueKind.Null
                    && state.GetProperty("enemies").ValueKind == JsonValueKind.Null
                    && state.GetProperty("available_actions").GetArrayLength() == 0);
            }
            finally { transition.Visible = transitionVisible; transition.Modulate = transitionColor; }
            var rootTransition = NGame.Instance.Transition;
            var transitionMaterial = (ShaderMaterial)rootTransition.Material;
            Variant threshold = transitionMaterial.GetShaderParameter("threshold");
            bool rootVisible = rootTransition.Visible;
            try
            {
                rootTransition.Visible = true;
                transitionMaterial.SetShaderParameter("threshold", 0.1f);
                Check("root_transition_shader_excluded", state => state.GetProperty("screen").GetProperty("status").GetString() == "covered"
                    && state.GetProperty("player").ValueKind == JsonValueKind.Null);
            }
            finally { rootTransition.Visible = rootVisible; transitionMaterial.SetShaderParameter("threshold", threshold); }
            Check("visible_card_restored", state => state.GetProperty("player").GetProperty("hand").GetArrayLength() == 5);
            completed = true;
        }
        finally
        {
            File.WriteAllText(reportPath, JsonSerializer.Serialize(new { completed, results }, new JsonSerializerOptions { WriteIndented = true }));
        }
    }
}
