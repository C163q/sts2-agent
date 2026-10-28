using Godot;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.addons.mega_text;

namespace Sts2Agent;

internal static class VisibleUi
{
    public static bool Shown(CanvasItem? item)
    {
        if (item == null || !GodotObject.IsInstanceValid(item) || !item.IsInsideTree()
            || item.IsQueuedForDeletion() || !item.IsVisibleInTree() || item.SelfModulate.A <= 0.01f)
            return false;
        float alpha = 1;
        for (Node? current = item; current != null; current = current.GetParent())
        {
            if (current is CanvasItem canvas)
                alpha *= canvas.Modulate.A;
            if (alpha <= 0.01f)
                return false;
        }
        return true;
    }

    public static bool OnScreen(CanvasItem? item)
    {
        if (!Shown(item))
            return false;
        if (item is not Control control)
            return item!.GetViewport().GetVisibleRect().HasPoint(item.GetGlobalTransformWithCanvas().Origin);
        Rect2 bounds = Bounds(control);
        bounds = bounds.Intersection(control.GetViewport().GetVisibleRect());
        if (!bounds.HasArea())
            return false;
        for (Node? ancestor = control.GetParent(); ancestor != null; ancestor = ancestor.GetParent())
            if (ancestor is Control { ClipContents: true } clip)
            {
                bounds = bounds.Intersection(Bounds(clip));
                if (!bounds.HasArea())
                    return false;
            }
        return true;
    }

    private static Rect2 Bounds(Control control)
    {
        Transform2D transform = control.GetGlobalTransformWithCanvas();
        Rect2 bounds = new(transform.Origin, Vector2.Zero);
        bounds = bounds.Expand(transform * new Vector2(control.Size.X, 0));
        bounds = bounds.Expand(transform * control.Size);
        return bounds.Expand(transform * new Vector2(0, control.Size.Y));
    }

    public static string? Text(Node? owner, string path)
    {
        var node = owner?.GetNodeOrNull<CanvasItem>(path);
        if (!OnScreen(node))
            return null;
        return node switch
        {
            RichTextLabel rich => rich.GetParsedText().Trim(),
            Label label => label.Text.Trim(),
            _ => null
        };
    }

    public static int? Number(Node? owner, string path) =>
        int.TryParse(Text(owner, path), out int value) ? value : null;

    public static string? SpecialCostColor(Node? owner, string path)
    {
        var label = owner?.GetNodeOrNull<Label>(path);
        if (!OnScreen(label))
            return null;
        Color color = label!.GetThemeColor(ThemeConstants.Label.FontColor);
        return color.IsEqualApprox(StsColors.cream) ? null
            : color.IsEqualApprox(StsColors.red) ? "red"
            : color.IsEqualApprox(StsColors.green) ? "green"
            : color.IsEqualApprox(StsColors.energyBlue) ? "blue" : "other";
    }

    public static IEnumerable<T> Descendants<T>(Node root) where T : Node
    {
        foreach (Node child in root.GetChildren())
        {
            if (child is T match)
                yield return match;
            foreach (T descendant in Descendants<T>(child))
                yield return descendant;
        }
    }
}
