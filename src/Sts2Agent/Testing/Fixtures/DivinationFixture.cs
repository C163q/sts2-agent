using Godot;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Events.Custom.CrystalSphereEvent;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Events.Custom.CrystalSphere;

namespace Sts2Agent;

internal static class DivinationFixture
{
    public static object Read(Player player)
    {
        var screen = DivinationInspection.Current!;
        var model = (CrystalSphereMinigame)PrivateFields.Read(screen, "_entity")!;
        var capture = ViewportCapture.Read(DivinationInspection.Bounds(screen))!.Value;
        using Image image = new();
        image.LoadPngFromBuffer(capture.png);
        bool WhiteNear(int x, int y) => Enumerable.Range(x - 3, 7).Any(px => Enumerable.Range(y - 3, 7).Any(py => {
            var color = image.GetPixel(px, py); return color.R > .9f && color.G > .9f && color.B > .9f; }));
        bool centerBorder = WhiteNear(5 * capture.width / 11, capture.height / 2)
            && WhiteNear(6 * capture.width / 11, capture.height / 2)
            && WhiteNear(capture.width / 2, 5 * capture.height / 11)
            && WhiteNear(capture.width / 2, 6 * capture.height / 11);
        return new { center_border = centerBorder,
            ui_items = VisibleUi.Descendants<NCrystalSphereItem>(screen).Select(item => new {
                position = item.Position.ToString(), size = item.Size.ToString(), scale = item.Scale.ToString(),
                relative = (DivinationInspection.Cells(screen).Single(c => c.Entity.X == 0 && c.Entity.Y == 0)
                    .GetGlobalTransformWithCanvas().AffineInverse() * item.GetGlobalTransformWithCanvas()).ToString(),
                cell_size = DivinationInspection.Cells(screen)[0].Size.ToString(),
                texture = item.GetNode<TextureRect>("Icon").Texture?.ResourcePath,
                banner = item.GetNode<TextureRect>("%CardBanner").Material?.ResourcePath }).ToArray(),
            rng = model.Rng.Counter, gold = player.Gold,
            deck = player.Deck.Cards.Select(c => c.Id.Entry).ToArray(),
            items = model.Items.Select(i => new { kind = i.GetType().Name, x = i.Position.X, y = i.Position.Y, width = i.Size.X, height = i.Size.Y }).ToArray(),
            pending = DivinationTasks.Pending(screen), event_pending = EventTaskTracker.Pending,
            viewport = new { texture_width = NGame.Instance!.GetViewport().GetTexture().GetWidth(),
                logical_size = NGame.Instance.GetViewport().GetVisibleRect().Size.ToString(),
                stretch = NGame.Instance.GetViewport().GetStretchTransform().ToString() } };
    }
}
