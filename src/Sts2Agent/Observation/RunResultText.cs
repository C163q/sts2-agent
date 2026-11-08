using Godot;

namespace Sts2Agent;

internal static class RunResultText
{
    public static string[] Read(Node root, IEnumerable<Node> represented)
    {
        var sources = represented.ToHashSet();
        bool Included(CanvasItem item)
        {
            for (Node? node = item; node != null; node = node.GetParent())
            {
                if (sources.Contains(node)) return false;
                if (ReferenceEquals(node, root)) break;
            }
            return true;
        }
        // Source ownership matters: an independent paragraph can match a button or score verbatim.
        return VisibleUi.Descendants<CanvasItem>(root).Where(Included).Select(RunResultInspection.Text)
            .Where(text => !string.IsNullOrWhiteSpace(text)).Cast<string>().Distinct().ToArray();
    }
}
