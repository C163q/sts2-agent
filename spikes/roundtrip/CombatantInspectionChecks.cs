using System.Reflection;
using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.MonsterMoves.Intents;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class CombatantInspectionChecks
{
    public static void Run(string reportPath, Player player)
    {
        List<object> results = [];
        void Check(string name, bool passed) => results.Add(new { name, passed });
        var room = NCombatRoom.Instance!;
        var enemies = CombatObservation.EnemyNodes().ToArray();
        var playerNode = room.GetCreatureNode(player.Creature)!;
        var playerPowers = CombatantInspection.PowerContainer(playerNode)!;
        var enemy = enemies.First();
        var enemyPowers = CombatantInspection.PowerContainer(enemy)!;
        var power = playerPowers.GetChildren().OfType<NPower>().First();
        var intent = enemies.SelectMany(node => node.IntentContainer.GetChildren().OfType<NIntent>()).First();
        string language = LocManager.Instance.Language;
        var localized = new LocString("powers", "VULNERABLE_POWER.title");
        string original = localized.GetFormattedText();
        var cachedKeyword = HoverTipFactory.FromKeyword(MegaCrit.Sts2.Core.Entities.Cards.CardKeyword.Exhaust);
        var shrink = player.Creature.GetPower<ShrinkPower>()!;
        var cachedApplier = (StringVar)shrink.DynamicVars["ApplierName"];
        string cachedApplierName = cachedApplier.StringValue;
        string chineseShrinkTip = JsonSerializer.Serialize(shrink.HoverTips.Select(HoverTipText.From));
        var before = CombatantInspection.Read(player);
        var escape = enemy.Entity.GetPower<EscapeArtistPower>()!;
        var nativeEscape = escape.HoverTips.Select(HoverTipText.From).ToArray();
        var escapeText = new LocString("powers", "ESCAPE_ARTIST_POWER.smartDescription");
        escapeText.Add("Amount", 5);
        string formattedEscape = EnglishCardText.Read(() => escapeText.GetFormattedText());
        Check("escape_countdown_uses_english_plural", before.hover_tips.Any(tip => tip.title == "Escape Artist"
            && tip.description == "Tries to escape the combat after 5 turns."));
        Check("player_power_amounts", before.player?.powers?.Any(item => item.name == "Strength" && item.amount == 2) == true);
        Check("enemy_power_amounts", before.enemies.All(item => item.powers?.Any(power => power.name == "Vulnerable" && power.amount == 2) == true));
        Check("english_dynamic_vulnerable", before.hover_tips.Any(tip => tip.title == "Vulnerable"
            && tip.description.Contains("2") && tip.description.Contains("50%")));
        Check("enemy_ids_match_observation", before.enemies.Select(item => item.id).SequenceEqual(enemies.Select(node => node.Entity.CombatId)));
        Check("shared_tips_are_unique", before.hover_tips.Select(tip => (tip.title, tip.description)).Distinct().Count() == before.hover_tips.Length);
        Check("sources_are_unique", before.hover_tips.All(tip => tip.sources.Length > 0 && tip.sources.Distinct().Count() == tip.sources.Length));
        Check("shared_enemy_power_tips", before.hover_tips.Any(tip => tip.title == "Vulnerable"
            && tip.sources.Count(source => source.StartsWith("enemies.") && source.Contains(".powers.")) == enemies.Length));
        string attackTitle = EnglishCardText.Read(() => new LocString("intents", "ATTACK.title").GetFormattedText());
        Check("native_attack_tips", before.hover_tips.Any(tip => tip.title == attackTitle && tip.sources.Any(source => source.Contains(".intents."))));
        Check("no_unexpanded_card_or_other_sources", before.hover_tips.SelectMany(tip => tip.sources).All(source =>
            source.StartsWith("player.powers.") || (source.StartsWith("enemies.") && (source.Contains(".powers.") || source.Contains(".intents.")))));
        Check("english_text", before.hover_tips.All(tip => !tip.description.Any(character => character >= '\u4e00' && character <= '\u9fff')));
        string englishApplier = EnglishCardText.Read(() => shrink.Applier!.Monster!.Title.GetFormattedText());
        Check("cached_applier_name_is_english_in_output", before.hover_tips.Any(tip =>
            tip.description.Contains(englishApplier) && tip.sources.Any(source => source.StartsWith("player.powers."))));
        Check("cached_applier_name_is_unchanged", cachedApplier.StringValue == cachedApplierName);
        Check("original_power_tip_unchanged", chineseShrinkTip == JsonSerializer.Serialize(shrink.HoverTips.Select(HoverTipText.From)));
        try { EnglishCardText.ReadPower<string>(shrink, () => throw new InvalidOperationException("Expected scope check.")); }
        catch (InvalidOperationException) { }
        Check("power_scope_restores_after_exception", EnglishCardText.Read(() => shrink.HoverTips.OfType<HoverTip>()
            .Any(tip => tip.Description.Contains(cachedApplierName))));

        void Hidden(CanvasItem item, string name, Func<CombatantInspection.Result, bool> verify)
        {
            bool visible = item.Visible;
            try { item.Visible = false; Check(name, verify(CombatantInspection.Read(player))); }
            finally { item.Visible = visible; }
        }
        Hidden(playerPowers, "hidden_player_powers_are_unknown", state => state.player?.powers == null
            && !state.hover_tips.Any(tip => tip.sources.Any(source => source.StartsWith("player.powers."))));
        Hidden(enemyPowers, "hidden_enemy_powers_are_unknown", state => state.enemies[0].powers == null);
        Hidden(enemy.IntentContainer, "hidden_intents_are_unknown", state => state.enemies[0].intents == null
            && !state.hover_tips.Any(tip => tip.sources.Any(source => source.StartsWith("enemies.0.intents."))));
        int count = before.player!.powers!.Length;
        Hidden(power, "hidden_power_is_excluded", state => state.player!.powers!.Length == count - 1);
        Hidden(power.GetNode<TextureRect>("%Icon"), "hidden_power_icon_is_excluded", state => state.player!.powers!.Length == count - 1);
        var mouseFilter = power.MouseFilter;
        Vector2 position = power.Position;
        try
        {
            power.MouseFilter = Control.MouseFilterEnum.Ignore;
            Check("non_hoverable_power_is_excluded", CombatantInspection.Read(player).player!.powers!.Length == count - 1);
            power.MouseFilter = mouseFilter;
            power.Position = new Vector2(-10000, -10000);
            Check("offscreen_power_is_excluded", CombatantInspection.Read(player).player!.powers!.Length == count - 1);
        }
        finally { power.MouseFilter = mouseFilter; power.Position = position; }
        var intentNode = enemies.First(node => node.IntentContainer.GetChildren().Contains(intent));
        int intentIndex = Array.IndexOf(enemies, intentNode);
        int intentCount = before.enemies[intentIndex].intents!.Length;
        Hidden(intent.GetNode<Control>("%IntentHolder"), "hidden_intent_holder_is_excluded",
            state => state.enemies[intentIndex].intents!.Length == intentCount - 1);
        Hidden(intent.GetNode<Sprite2D>("%Intent"), "hidden_intent_sprite_is_excluded",
            state => state.enemies[intentIndex].intents!.Length == intentCount - 1);
        var intentMouseFilter = intent.MouseFilter;
        var field = typeof(NIntent).GetField("_intent", BindingFlags.Instance | BindingFlags.NonPublic)!;
        var model = field.GetValue(intent);
        try
        {
            intent.MouseFilter = Control.MouseFilterEnum.Ignore;
            Check("non_hoverable_intent_is_excluded", CombatantInspection.Read(player).enemies[intentIndex].intents!.Length == intentCount - 1);
            intent.MouseFilter = intentMouseFilter;
            field.SetValue(intent, new HiddenIntent());
            Check("hidden_intent_has_no_explanation", !CombatantInspection.Read(player).hover_tips.Any(tip =>
                tip.sources.Contains($"enemies.{intentIndex}.intents.0")));
            field.SetValue(intent, new BuffIntent());
            string buffTitle = EnglishCardText.Read(() => new LocString("intents", "BUFF.title").GetFormattedText());
            Check("uses_displayed_intent_binding", CombatantInspection.Read(player).hover_tips.Any(tip =>
                tip.title == buffTitle && tip.sources.Contains($"enemies.{intentIndex}.intents.0")));
            field.SetValue(intent, new MultiAttackIntent(13, 2));
            Check("native_multiattack_uses_player_vulnerable", CombatantInspection.Read(player).hover_tips.Any(tip =>
                tip.sources.Contains($"enemies.{intentIndex}.intents.0") && tip.description.Contains("19") && tip.description.Contains("2")));
        }
        finally { field.SetValue(intent, model); intent.MouseFilter = intentMouseFilter; }
        var cardPlayField = typeof(NPlayerHand).GetField("_currentCardPlay", BindingFlags.Instance | BindingFlags.NonPublic)!;
        var previousPlay = cardPlayField.GetValue(room.Ui.Hand);
        var dummyPlay = new NMouseCardPlay();
        try
        {
            cardPlayField.SetValue(room.Ui.Hand, dummyPlay);
            bool rejected = false;
            try { CombatantInspection.Read(player); }
            catch (InvalidOperationException) { rejected = true; }
            Check("card_aiming_is_unavailable", rejected);
        }
        finally { cardPlayField.SetValue(room.Ui.Hand, previousPlay); dummyPlay.Free(); }
        Check("locale_unchanged", language == LocManager.Instance.Language && localized.GetFormattedText() == original);
        Check("keyword_cache_unchanged", HoverTipFactory.FromKeyword(MegaCrit.Sts2.Core.Entities.Cards.CardKeyword.Exhaust).Equals(cachedKeyword));
        Check("read_is_repeatable", JsonSerializer.Serialize(before) == JsonSerializer.Serialize(CombatantInspection.Read(player)));
        var audit = PowerTextChecks.Run();
        Check("native_english_power_parity", JsonSerializer.SerializeToElement(audit).GetProperty("passed").GetBoolean());
        File.WriteAllText(reportPath, JsonSerializer.Serialize(new { language, nativeEscape, formattedEscape, inspection = before, results, audit }, new JsonSerializerOptions { WriteIndented = true }));
        if (results.Any(result => !JsonSerializer.SerializeToElement(result).GetProperty("passed").GetBoolean()))
            throw new InvalidOperationException("Combatant inspection checks failed; see the local report.");
    }
}
