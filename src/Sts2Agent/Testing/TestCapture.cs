using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Nodes;

namespace Sts2Agent;

internal static class TestCapture
{
    public static void Save(string path)
    {
        NGame game = NGame.Instance!;
        using Image image = game.GetViewport().GetTexture().GetImage();
        Error saved = image.SavePng(path);
        if (saved != Error.Ok)
            throw new IOException("Unable to save test capture: " + saved);
        var layout = VisibleUi.Descendants<CanvasItem>(game).Select(node => new
        {
            path = node.GetPath().ToString(), type = node.GetType().Name,
            shown = VisibleUi.Shown(node), on_screen = VisibleUi.OnScreen(node),
            size = node is Control control ? new[] { control.Size.X, control.Size.Y } : null,
            text = node.Name.ToString() is "ReleaseInfo" or "ModdedWarning" or "RoomIcon"
                && node is Label label ? label.Text : null
        }).ToArray();
        File.WriteAllText(Path.ChangeExtension(path, ".layout.json"), JsonSerializer.Serialize(layout));
    }
}
