using Godot;
using MegaCrit.Sts2.Core.Nodes;

namespace Sts2Agent;

internal static class ViewportCapture
{
    public static (int width, int height, byte[] png)? Read(Rect2I? region = null)
    {
        if (!NGame.IsMainThread())
            throw new InvalidOperationException("Viewport capture requires the main thread.");
        if (DisplayServer.GetName() == "headless" || NGame.Instance is not { } game)
            return null;
        // The bridge invokes this after drawing; no UI changes or additional frames are requested.
        using ViewportTexture texture = game.GetViewport().GetTexture();
        using Image image = texture.GetImage();
        if (image == null || image.IsEmpty())
            return null;
        int width = image.GetWidth(), height = image.GetHeight();
        if (width <= 0 || height <= 0 || (long)width * height > 16_777_216)
            return null;
        if (region is { } bounds)
        {
            if (bounds.Position.X < 0 || bounds.Position.Y < 0 || bounds.Size.X <= 0 || bounds.Size.Y <= 0
                || bounds.End.X > width || bounds.End.Y > height) return null;
            using Image cropped = image.GetRegion(bounds);
            byte[] data = cropped.SavePngToBuffer();
            return data.Length is > 0 and <= 32 * 1024 * 1024 ? (bounds.Size.X, bounds.Size.Y, data) : null;
        }
        byte[] png = image.SavePngToBuffer();
        return png.Length is > 0 and <= 32 * 1024 * 1024 ? (width, height, png) : null;
    }
}
