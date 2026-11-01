using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class ObservationChecks
{
    private static bool completed;
    private sealed record IdentityToken(string Value);

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
            var tokens = new CardIdentityMap<IdentityToken>();
            var firstToken = new IdentityToken("identical");
            var secondToken = new IdentityToken("identical");
            Check("identity_uses_references", _ => tokens.Get(firstToken) == 0 && tokens.Get(secondToken) == 1);
            Check("identity_reuses_same_instance", _ => tokens.Get(secondToken) == 1 && tokens.Get(firstToken) == 0);
            tokens.Clear();
            Check("identity_resets_for_combat", _ => tokens.Get(secondToken) == 0);
            var baseline = Read();
            int[] initialIds = baseline.GetProperty("player").GetProperty("hand").EnumerateArray()
                .Select(c => c.GetProperty("id").GetInt32()).ToArray();
            Check("visible_ids_unique", _ => initialIds.Distinct().Count() == initialIds.Length);
            Hide(card.GetNode<Label>("%TypeLabel"), () => Check("identified_card_type_without_label", state =>
                state.GetProperty("player").GetProperty("hand")[0].GetProperty("type").GetString() != null));
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
                cost.AddThemeColorOverride("font_color", StsColors.red);
                Check("displayed_cost_color_preserved", state => state.GetProperty("player").GetProperty("hand")[0]
                    .GetProperty("energy_cost_color").GetString() == "red");
            }
            finally
            {
                if (hadColorOverride)
                    cost.AddThemeColorOverride("font_color", costColor);
                else
                    cost.RemoveThemeColorOverride("font_color");
            }
            var starIcon = card.GetNode<Control>("%StarIcon");
            var starLabel = card.GetNode<Label>("%StarLabel");
            bool starVisible = starIcon.Visible;
            bool starLabelVisible = starLabel.Visible;
            Color starColor = starLabel.GetThemeColor("font_color");
            bool hadStarOverride = starLabel.HasThemeColorOverride("font_color");
            try
            {
                starIcon.Visible = true;
                starLabel.Visible = true;
                foreach (var (colorName, actualColor) in new[] { ("red", StsColors.red), ("green", StsColors.green), ("blue", StsColors.energyBlue) })
                {
                    cost.AddThemeColorOverride("font_color", actualColor);
                    starLabel.AddThemeColorOverride("font_color", actualColor);
                    Check("both_cost_colors_" + colorName, state => state.GetProperty("player").GetProperty("hand")[0]
                        .GetProperty("energy_cost_color").GetString() == colorName
                        && state.GetProperty("player").GetProperty("hand")[0].GetProperty("star_cost_color").GetString() == colorName);
                }
                cost.AddThemeColorOverride("font_color", StsColors.cream);
                starLabel.AddThemeColorOverride("font_color", StsColors.cream);
                Check("default_cost_colors_omitted", state => !state.GetProperty("player").GetProperty("hand")[0].TryGetProperty("energy_cost_color", out _)
                    && !state.GetProperty("player").GetProperty("hand")[0].TryGetProperty("star_cost_color", out _));
            }
            finally
            {
                if (hadColorOverride) cost.AddThemeColorOverride("font_color", costColor);
                else cost.RemoveThemeColorOverride("font_color");
                if (hadStarOverride) starLabel.AddThemeColorOverride("font_color", starColor);
                else starLabel.RemoveThemeColorOverride("font_color");
                starIcon.Visible = starVisible;
                starLabel.Visible = starLabelVisible;
            }
            var material = (ShaderMaterial)card.CardHighlight.Material;
            Variant width = material.GetShaderParameter("width");
            try
            {
                material.SetShaderParameter("width", 0);
                Check("zero_width_outline_excluded", state => state.GetProperty("player").GetProperty("hand")[0]
                    .GetProperty("outline").GetString() == "none");
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
            var potions = NRun.Instance.GlobalUi.TopBar.PotionContainer;
            Hide(potions, () => Check("hidden_potion_slots_unknown", state =>
                state.GetProperty("top_bar").GetProperty("potion_slots").ValueKind == JsonValueKind.Null));
            var firstPotion = potions.GetNode<Control>("MarginContainer/PotionHolders").GetChildren().OfType<Control>().First();
            Hide(firstPotion, () => Check("hidden_potion_slot_does_not_shift_indices", state =>
                state.GetProperty("top_bar").GetProperty("potion_slots").ValueKind == JsonValueKind.Null));
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
            Check("visible_ids_reused_after_hidden", state => state.GetProperty("player").GetProperty("hand").EnumerateArray()
                .Select(c => c.GetProperty("id").GetInt32()).SequenceEqual(initialIds));
            string oldHp = hpLabel.Text;
            var infinity = hpLabel.GetParent().GetNode<TextureRect>("InfinityTex");
            bool oldInfinity = infinity.Visible;
            bool oldHpVisibility = hpLabel.Visible;
            try
            {
                hpLabel.Visible = true;
                hpLabel.Text = new LocString("gameplay_ui", "HEALTH_BAR.DEAD").GetFormattedText();
                Check("dead_health_display", state => state.GetProperty("enemies").EnumerateArray()
                    .First(e => e.GetProperty("id").GetUInt32() == enemy.Entity.CombatId).GetProperty("hp_display").GetString() == "dead");
                hpLabel.Visible = false;
                infinity.Visible = true;
                Check("infinite_health_display", state => state.GetProperty("enemies").EnumerateArray()
                    .First(e => e.GetProperty("id").GetUInt32() == enemy.Entity.CombatId).GetProperty("hp_display").GetString() == "infinite");
            }
            finally { hpLabel.Text = oldHp; hpLabel.Visible = oldHpVisibility; infinity.Visible = oldInfinity; }
            completed = true;
        }
        finally
        {
            File.WriteAllText(reportPath, JsonSerializer.Serialize(new { completed, results }, new JsonSerializerOptions { WriteIndented = true }));
        }
    }
}
