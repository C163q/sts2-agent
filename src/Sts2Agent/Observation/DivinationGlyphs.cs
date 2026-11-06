using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Nodes.Events.Custom.CrystalSphere;

namespace Sts2Agent;

internal static class DivinationGlyphs
{
    private sealed record Pixels(int Width, int Height, byte[] Rgba);
    private sealed record Pattern(string? Texture, string? Banner, string[][] Parts);
    private static readonly Dictionary<ulong, Pixels?> pixelCache = [];
    private static readonly Pattern[] patterns = LoadPatterns();

    private static Pattern[] LoadPatterns()
    {
        using var stream = typeof(DivinationGlyphs).Assembly.GetManifestResourceStream("Sts2Agent.DivinationPatterns")!;
        using var document = JsonDocument.Parse(stream);
        return document.RootElement.GetProperty("patterns").EnumerateArray().Select(p => new Pattern(
            p.TryGetProperty("texture", out var texture) ? texture.GetString() : null,
            p.TryGetProperty("banner", out var banner) ? banner.GetString() : null,
            p.GetProperty("parts").EnumerateArray().Select(row => row.EnumerateArray().Select(v => v.GetString()!).ToArray()).ToArray())).ToArray();
    }

    public static DivinationPatch[] Read(NCrystalSphereScreen screen, NCrystalSphereCell[] cells, bool[,] hidden)
    {
        var origin = cells.Single(c => c.Entity.X == 0 && c.Entity.Y == 0);
        var fromCanvas = origin.GetGlobalTransformWithCanvas().AffineInverse();
        var patches = new List<DivinationPatch>();
        foreach (var item in VisibleUi.Descendants<NCrystalSphereItem>(screen).Where(VisibleUi.Displayed))
        {
            var transform = fromCanvas * item.GetGlobalTransformWithCanvas();
            // Native Items and Cells have different parent offsets (2 px vertically).
            // Their child positions share the same 57 px placement grid.
            var start = (item.Position - origin.Position) / origin.Size;
            var extent = item.Size / origin.Size;
            bool aligned = NearInteger(start.X) && NearInteger(start.Y) && NearInteger(extent.X) && NearInteger(extent.Y)
                && transform.X.IsEqualApprox(Vector2.Right) && transform.Y.IsEqualApprox(Vector2.Down)
                && extent.X > 0 && extent.Y > 0;
            var layers = VisibleUi.Descendants<TextureRect>(item).Where(t => VisibleUi.Displayed(t) && t.Texture != null).ToArray();
            var pattern = Identify(item);
            bool known = aligned && pattern != null && pattern.Parts.Length == Mathf.RoundToInt(extent.Y)
                && pattern.Parts.All(row => row.Length == Mathf.RoundToInt(extent.X));
            int left = aligned ? Mathf.RoundToInt(start.X) : Mathf.FloorToInt(start.X);
            int top = aligned ? Mathf.RoundToInt(start.Y) : Mathf.FloorToInt(start.Y);
            int right = aligned ? Mathf.RoundToInt(start.X + extent.X) : Mathf.CeilToInt(start.X + extent.X);
            int bottom = aligned ? Mathf.RoundToInt(start.Y + extent.Y) : Mathf.CeilToInt(start.Y + extent.Y);
            bool complete = known && left >= 0 && top >= 0 && right <= 11 && bottom <= 11
                && Enumerable.Range(left, right - left).All(x => Enumerable.Range(top, bottom - top).All(y => !hidden[x, y]));
            foreach (var cell in cells.Where(c => !hidden[c.Entity.X, c.Entity.Y]))
            {
                int x = cell.Entity.X, y = cell.Entity.Y;
                // The scry border covers the native two-pixel bleed outside placement cells.
                if (aligned && (x < left || x >= right || y < top || y >= bottom)) continue;
                var drawing = new Rect2(transform.Origin, transform * item.Size - transform.Origin);
                if (!drawing.Intersects(new Rect2(new Vector2(x, y) * origin.Size, origin.Size))) continue;
                if (!layers.Any(layer => HasInk(layer, cell))) continue;
                bool partKnown = known && x >= left && x < right && y >= top && y < bottom;
                string appearance = partKnown ? pattern!.Parts[y - top][x - left] : "unrecognized";
                if (appearance.StartsWith("card.") && y == top && item.GetNode<Control>("%Card").Visible
                    && (!VisibleUi.Displayed(item.GetNode<TextureRect>("%CardBanner"))
                        || !HasInk(item.GetNode<TextureRect>("%CardBanner"), cell)))
                    appearance = x == left ? "card.upper_left" : "card.upper_right";
                patches.Add(new(x, y, appearance, complete));
            }
        }
        return patches.ToArray();
    }

    private static bool NearInteger(float value) => Math.Abs(value - Mathf.Round(value)) < 0.01f;

    private static Pattern? Identify(NCrystalSphereItem item)
    {
        var card = item.GetNode<Control>("%Card");
        if (VisibleUi.Displayed(card))
        {
            string? banner = item.GetNode<TextureRect>("%CardBanner").Material?.ResourcePath.GetFile().GetBaseName();
            return patterns.SingleOrDefault(p => p.Banner != null && p.Banner == banner);
        }
        var icon = item.GetNode<TextureRect>("Icon");
        string? texture = VisibleUi.Displayed(icon) ? icon.Texture?.ResourcePath.GetFile().GetBaseName() : null;
        return patterns.SingleOrDefault(p => p.Texture != null && p.Texture == texture);
    }

    private static bool HasInk(TextureRect layer, NCrystalSphereCell cell)
    {
        if (layer.Texture == null || layer.Size.X <= 0 || layer.Size.Y <= 0) return false;
        var pixels = ReadPixels(layer.Texture);
        if (pixels == null) return false;
        var transform = layer.GetGlobalTransformWithCanvas().AffineInverse() * cell.GetGlobalTransformWithCanvas();
        int columns = Math.Max(1, Mathf.CeilToInt(cell.Size.X)), rows = Math.Max(1, Mathf.CeilToInt(cell.Size.Y));
        for (int y = 0; y < rows; y++) for (int x = 0; x < columns; x++)
        {
            var local = transform * new Vector2((x + .5f) * cell.Size.X / columns, (y + .5f) * cell.Size.Y / rows);
            if (local.X < 0 || local.Y < 0 || local.X >= layer.Size.X || local.Y >= layer.Size.Y) continue;
            int sx = Math.Clamp((int)(local.X / layer.Size.X * pixels.Width), 0, pixels.Width - 1);
            int sy = Math.Clamp((int)(local.Y / layer.Size.Y * pixels.Height), 0, pixels.Height - 1);
            // Ignore fully transparent padding; a control's occupied rectangle is not visible ink.
            if (pixels.Rgba[(sy * pixels.Width + sx) * 4 + 3] > 25) return true;
        }
        return false;
    }

    private static Pixels? ReadPixels(Texture2D texture)
    {
        ulong id = texture.GetInstanceId();
        if (pixelCache.TryGetValue(id, out var cached)) return cached;
        using Image image = texture.GetImage();
        if (image == null || image.IsEmpty() || image.IsCompressed() && image.Decompress() != Error.Ok)
            return pixelCache[id] = null;
        image.Convert(Image.Format.Rgba8);
        return pixelCache[id] = new(image.GetWidth(), image.GetHeight(), image.GetData());
    }
}
