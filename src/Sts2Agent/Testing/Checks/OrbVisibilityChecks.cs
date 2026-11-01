using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models.Orbs;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class OrbVisibilityChecks
{
    public static async Task<object> Run(Player player, Func<Task> frame, Func<string> observe)
    {
        var cardIds = new CardIdentityMap<MegaCrit.Sts2.Core.Models.CardModel>();
        var node = NCombatRoom.Instance!.GetCreatureNode(player.Creature)!;
        var manager = node.OrbManager!;
        var slots = OrbInspection.VisibleNodes(node) ?? throw new InvalidOperationException("Fixture slots are not visible.");
        var checks = new List<object>();
        bool passed = true;
        void Check(string name, bool ok) { checks.Add(new { name, passed = ok }); passed &= ok; }
        JsonElement ReadPlayer()
        {
            using var state = JsonDocument.Parse(observe());
            return state.RootElement.GetProperty("player").Clone();
        }
        bool Unknown() => ReadPlayer().GetProperty("orb_slots").ValueKind == JsonValueKind.Null;
        bool NoTips() => !CombatantInspection.Read(player, cardIds.Get).hover_tips.Any(t => t.sources.Any(s => s.StartsWith("player.orb_slots.")))
            && !UiInspection.Read().Any(t => t.sources.Any(s => s.StartsWith("player.orb_slots.")));
        Check("native five slots are exposed", ReadPlayer().GetProperty("orb_slots").GetArrayLength() == 5);
        foreach (var (item, name) in new (CanvasItem, string)[] {
            (manager, "manager"), (slots[4].GetNode<Control>("%Outline"), "empty outline"),
            ((CanvasItem)CardSelection.Field(slots[0], "_sprite")!, "orb sprite"), (slots[0], "orb node") })
        {
            bool visible = item.Visible;
            try { item.Hide(); await frame(); Check("hidden " + name + " is unknown without hover help", Unknown() && NoTips()); }
            finally { item.Visible = visible; }
            await frame();
        }
        var label = slots[0].GetNode<CanvasItem>("%PassiveAmount");
        try
        {
            label.Hide(); await frame();
            var lightning = ReadPlayer().GetProperty("orb_slots")[0];
            Check("hidden label never uses model amount", lightning.GetProperty("name").GetString() == "Lightning"
                && lightning.GetProperty("passive").ValueKind == JsonValueKind.Null);
        }
        finally { label.Show(); }
        var sprite = (Node2D)CardSelection.Field(slots[0], "_sprite")!;
        var spriteScale = sprite.Scale;
        var spritePosition = sprite.Position;
        try
        {
            sprite.Scale = Vector2.Zero;
            Check("zero-scale sprite is unknown", Unknown() && NoTips());
            sprite.Scale = spriteScale;
            sprite.Position = new(-10000, -10000);
            Check("offscreen sprite is unknown", Unknown() && NoTips());
        }
        finally { sprite.Scale = spriteScale; sprite.Position = spritePosition; }
        var visual = sprite.GetParent<Control>();
        var visualClip = visual.ClipContents;
        var visualSize = visual.Size;
        try
        {
            visual.ClipContents = true; visual.Size = Vector2.One;
            sprite.Position = new(100, 100);
            Check("sprite-only clipping is unknown", Unknown() && NoTips());
        }
        finally { visual.ClipContents = visualClip; visual.Size = visualSize; sprite.Position = spritePosition; }
        var bounds = slots[0].GetNode<Control>("Bounds");
        var position = bounds.Position;
        try { bounds.Position = new(-10000, -10000); await frame(); Check("offscreen bounds are unknown", Unknown() && NoTips()); }
        finally { bounds.Position = position; }
        var container = slots[0].GetParent<Control>();
        var clip = container.ClipContents;
        var size = container.Size;
        try
        {
            container.ClipContents = true; container.Size = Vector2.One;
            await frame(); Check("clipped slots are unknown", Unknown() && NoTips());
        }
        finally { container.ClipContents = clip; container.Size = size; }
        foreach (int i in new[] { 0, 4 })
        {
            var filter = slots[i].MouseFilter;
            try
            {
                slots[i].MouseFilter = Control.MouseFilterEnum.Ignore; await frame();
                string source = $"player.orb_slots.{i}";
                Check("non-hoverable slot has no help: " + i, !CombatantInspection.Read(player, cardIds.Get).hover_tips.Any(t => t.sources.Contains(source))
                    && !UiInspection.Read().Any(t => t.sources.Contains(source)));
            }
            finally { slots[i].MouseFilter = filter; }
        }
        try
        {
            NRun.Instance!.GlobalUi.MapScreen.Open(); await frame();
            Check("map covers the entire player observation", ReadPlayer().ValueKind == JsonValueKind.Null);
        }
        finally { NRun.Instance!.GlobalUi.MapScreen.Close(); }
        var deadline = DateTime.UtcNow.AddSeconds(8);
        while (CombatObservation.Status() != "visible" && DateTime.UtcNow < deadline) await frame();
        OrbCmd.RemoveSlots(player, 5);
        await frame();
        Check("no slots is an empty array", ReadPlayer().GetProperty("orb_slots").GetArrayLength() == 0 && NoTips());
        await OrbCmd.AddSlots(player, 3);
        // Slot movement is a native finite tween; wait for its actual visible geometry.
        deadline = DateTime.UtcNow.AddSeconds(8);
        while (OrbInspection.VisibleNodes(node)?.Length != 3 && DateTime.UtcNow < deadline) await frame();
        Check("all-empty slots retain positions", ReadPlayer().GetProperty("orb_slots").EnumerateArray()
            .Count(s => s.ValueKind == JsonValueKind.Null) == 3);
        Check("empty-slot help shares all visible sources", UiInspection.Read().Any(t =>
            t.sources.Count(s => s.StartsWith("player.orb_slots.")) == 3));
        await OrbCmd.Channel<GlassOrb>(new ThrowingPlayerChoiceContext(), player);
        deadline = DateTime.UtcNow.AddSeconds(8);
        do { await frame(); }
        while (OrbInspection.Read(node) is not [{ name: "Glass" }, null, null] && DateTime.UtcNow < deadline);
        Check("glass orb is identified without inventing evoke number", OrbInspection.Read(node) is
            [{ name: "Glass", passive: not null, evoke: null }, null, null]);
        return new { passed, checks };
    }
}
