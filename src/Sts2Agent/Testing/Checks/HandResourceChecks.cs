using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class HandResourceChecks
{
    public static async Task<object> Run(GameAdapter adapter, Player player)
    {
        var room = NCombatRoom.Instance!;
        var energy = VisibleUi.Descendants<NEnergyCounter>(room.Ui.EnergyCounterContainer).Single().GetNode<Label>("Label");
        var star = VisibleUi.Descendants<NStarCounter>(room.Ui).Single().GetNode<CanvasItem>("%CountLabel");
        List<object> checks = [];
        void Check(string name, bool passed) => checks.Add(new { name, passed });
        async Task<JsonElement> Read()
        {
            using var document = JsonDocument.Parse(await adapter.Execute(new Request(Guid.NewGuid().ToString("N"), "inspect_hand", null)));
            if (!document.RootElement.GetProperty("ok").GetBoolean()) throw new InvalidOperationException("Hand resource check could not inspect hand.");
            return document.RootElement.GetProperty("state").Clone();
        }
        var before = await Read();
        var body = room.GetCreatureNode(player.Creature)!.Body;
        bool bodyShown = body.Visible;
        try
        {
            body.Visible = false;
            var hidden = await Read();
            Check("HUD independent of hidden player body", new[] { "energy", "max_energy", "stars" }
                .All(key => hidden.GetProperty(key).GetRawText() == before.GetProperty(key).GetRawText()));
        }
        finally { body.Visible = bodyShown; }
        string original = energy.Text;
        bool energyShown = energy.Visible;
        try
        {
            energy.Text = "2/9";
            var altered = await Read();
            Check("energy pair comes from label", altered.GetProperty("energy").GetInt32() == 2 && altered.GetProperty("max_energy").GetInt32() == 9);
            energy.Visible = false;
            var hidden = await Read();
            Check("hidden energy never uses model", hidden.GetProperty("energy").ValueKind == JsonValueKind.Null
                && hidden.GetProperty("max_energy").ValueKind == JsonValueKind.Null);
        }
        finally { energy.Text = original; energy.Visible = energyShown; }
        bool starShown = star.Visible;
        try
        {
            star.Visible = false;
            Check("hidden stars never use model", (await Read()).GetProperty("stars").ValueKind == JsonValueKind.Null);
        }
        finally { star.Visible = starShown; }
        var after = await Read();
        Check("checks restore hand and HUD", before.GetRawText() == after.GetRawText());
        return new { checks, passed = checks.All(check => JsonSerializer.SerializeToElement(check).GetProperty("passed").GetBoolean()) };
    }
}
