using System.Text.Json;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Vfx;

namespace Sts2Agent;

internal static class SovereignBladeChecks
{
    public static async Task<object> Run(Player player, Func<Task> frame, Func<CardModel, int> cardId, Func<string> observe)
    {
        var owner = NCombatRoom.Instance!.GetCreatureNode(player.Creature)!;
        var blade = SovereignBladeInspection.VisibleNodes(owner, cardId).Single();
        var sprite = blade.GetNode<Node2D>("SpineSword");
        var hitbox = blade.GetNode<Control>("%Hitbox");
        var checks = new List<object>();
        var samples = new List<object>();
        bool passed = true;
        void Check(string name, bool ok) { checks.Add(new { name, passed = ok }); passed &= ok; }
        bool HasTip() => CombatantInspection.Read(player, cardId).hover_tips.Any(t => t.sources.Contains("player.sovereign_blades.0"));
        int Count() => SovereignBladeInspection.Read(owner, cardId).Length;
        async Task Settle()
        {
            var deadline = DateTime.UtcNow.AddSeconds(6);
            do { await frame(); }
            while ((SovereignBladeInspection.Pending(owner)
                || VisibleUi.Number(NCombatRoom.Instance!.Ui.DiscardPile, "CountContainer/Count") != PileType.Discard.GetPile(player).Cards.Count)
                && DateTime.UtcNow < deadline);
            if (DateTime.UtcNow >= deadline) throw new TimeoutException("Blade visuals did not settle.");
            await frame();
        }
        await Settle();
        blade.Hide();
        try { Check("hidden sword has no identity or help", Count() == 0 && !HasTip()); }
        finally { blade.Show(); }
        var scale = sprite.Scale;
        sprite.Scale = Vector2.Zero;
        try { Check("zero-scale sword is not a public object", Count() == 0 && !HasTip()); }
        finally { sprite.Scale = scale; }
        var position = blade.Position;
        blade.Position = new Vector2(-10000, -10000);
        try { Check("offscreen sword retains identity and help", Count() == 1 && HasTip()); }
        finally { blade.Position = position; }
        hitbox.Hide();
        try { Check("hidden hitbox preserves the sword but omits help", Count() == 1 && !HasTip()); }
        finally { hitbox.Show(); }
        var filter = hitbox.MouseFilter;
        hitbox.MouseFilter = Control.MouseFilterEnum.Ignore;
        try { Check("non-hoverable sword has no help", Count() == 1 && !HasTip()); }
        finally { hitbox.MouseFilter = filter; }
        string language = LocManager.Instance.Language;
        try
        {
            foreach (string locale in new[] { "zhs", "eng" })
            {
                LocManager.Instance.SetLanguage(locale);
                AccessTools.Method(typeof(NSovereignBladeVfx), "OnFocused").Invoke(blade, null);
                await frame(); await frame();
                var hover = (Node)PrivateFields.Read(blade, "_hoverTip")!;
                var preview = VisibleUi.Descendants<NCard>(hover).Single();
                string? body = VisibleUi.Text(preview, "%DescriptionLabel");
                string path = Path.Combine(Path.GetDirectoryName(System.Environment.GetEnvironmentVariable("STS2_AGENT_IPC_DIR"))!,
                    "sovereign-blade-" + locale + ".png");
                TestCapture.Save(path);
                var details = CombatantInspection.Read(player, cardId);
                var tip = details.hover_tips.Single(t => t.sources.Contains("player.sovereign_blades.0"));
                if (locale == "eng") Check("tool description matches the rendered native card preview", body == tip.description);
                samples.Add(new { locale, native_description = body, tool_tip = tip, screenshot = path });
                AccessTools.Method(typeof(NSovereignBladeVfx), "OnUnfocused").Invoke(blade, null);
            }
        }
        finally
        {
            AccessTools.Method(typeof(NSovereignBladeVfx), "OnUnfocused").Invoke(blade, null);
            LocManager.Instance.SetLanguage(language);
        }
        var original = blade.Card;
        await CardPileCmd.Add(original, PileType.Discard);
        await Settle();
        Check("a sword remains inspectable outside the hand", Count() == 1 && HasTip());
        await PowerCmd.Apply<ParryPower>(new ThrowingPlayerChoiceContext(), player.Creature, 5, player.Creature, null);
        await Settle();
        decimal cachedBlock = original.DynamicVars.CalculatedBlock.PreviewValue;
        var beforeHover = CombatantInspection.Read(player, cardId).hover_tips
            .Single(t => t.sources.Contains("player.sovereign_blades.0"));
        Check("reading a fresh preview does not rewrite the owned card cache", original.DynamicVars.CalculatedBlock.PreviewValue == cachedBlock);
        try
        {
            LocManager.Instance.SetLanguage("eng");
            AccessTools.Method(typeof(NSovereignBladeVfx), "OnFocused").Invoke(blade, null);
            await frame(); await frame();
            var preview = VisibleUi.Descendants<NCard>((Node)PrivateFields.Read(blade, "_hoverTip")!).Single();
            string? body = VisibleUi.Text(preview, "%DescriptionLabel");
            Check("out-of-hand preview reflects current powers before native hovering", body == beforeHover.description);
            samples.Add(new { scenario = "out-of-hand Parry", native_description = body, tool_tip = beforeHover });
        }
        finally
        {
            AccessTools.Method(typeof(NSovereignBladeVfx), "OnUnfocused").Invoke(blade, null);
            LocManager.Instance.SetLanguage(language);
        }
        var added = CombatManager.Instance.DebugOnlyGetState()!.CreateCard<SovereignBlade>(player);
        await CardPileCmd.AddGeneratedCardToCombat(added, PileType.Hand, player);
        await Settle();
        added.UpgradeInternal();
        added.FinalizeUpgradeInternal();
        await Settle();
        Check("a floating sword identity does not reveal an unseen upgrade suffix", SovereignBladeInspection.Read(owner, cardId)
            .Single(item => item.id == cardId(added)).name == "Sovereign Blade");
        Check("an explicit card preview retains its displayed upgrade title", CombatantInspection.Read(player, cardId)
            .hover_tips.Any(t => t.title == "Sovereign Blade+" && t.sources.Any(s => s.StartsWith("player.sovereign_blades."))));
        var identities = SovereignBladeInspection.Read(owner, cardId);
        Check("multiple swords have distinct stable card identities", identities.Length == 2
            && identities.Select(item => item.id).Distinct().Count() == 2
            && identities.Any(item => item.id == cardId(original)) && identities.Any(item => item.id == cardId(added)));
        string state = observe();
        for (int i = 0; i < 45; i++) await frame();
        string afterOrbit = observe();
        samples.Add(new { scenario = "orbit stability", before = JsonSerializer.Deserialize<JsonElement>(state),
            after = JsonSerializer.Deserialize<JsonElement>(afterOrbit) });
        Check("orbiting and sibling reordering do not change the state token", JsonSerializer.Deserialize<JsonElement>(state).GetProperty("snapshot_id").GetString()
            == JsonSerializer.Deserialize<JsonElement>(afterOrbit).GetProperty("snapshot_id").GetString());
        await CardPileCmd.Add(original, PileType.Exhaust);
        await Settle();
        Check("exhaust removes only the corresponding visible sword", SovereignBladeInspection.Read(owner, cardId) is [var remaining]
            && remaining.id == cardId(added));
        return new { passed, checks, samples };
    }
}
