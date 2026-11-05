using Godot;
using MegaCrit.Sts2.Core.Nodes.Screens.TreasureRoomRelic;

namespace Sts2Agent;

internal static class TreasureDisplayFixture
{
    private static NTreasureRoomRelicHolder? holder;
    private static Control? parent;
    private static Vector2 position, parentSize;
    private static Control.MouseFilterEnum mouse;
    private static Control.FocusModeEnum focus;
    private static bool enabled, visible, clipped;
    private static Color modulate;

    public static void Reset()
    {
        if (holder != null && GodotObject.IsInstanceValid(holder))
        {
            if (enabled) holder.Enable(); else holder.Disable();
            holder.Position = position;
            holder.MouseFilter = mouse;
            holder.FocusMode = focus;
            holder.Relic.Icon.Visible = visible;
            holder.Relic.Icon.Modulate = modulate;
        }
        if (parent != null && GodotObject.IsInstanceValid(parent))
        {
            parent.ClipContents = clipped;
            parent.Size = parentSize;
        }
        holder = null;
        parent = null;
    }

    public static object Set(string mode)
    {
        Reset();
        if (mode == "normal") return new { mode };
        var room = TreasureInspection.Current;
        if (room == null || !TreasureInspection.Ready(room) || TreasureInspection.Relic(room) is not { } current)
            throw new InvalidOperationException("A displayed and ready treasure relic is required.");
        holder = current;
        parent = holder.GetParent<Control>();
        position = holder.Position;
        parentSize = parent.Size;
        mouse = holder.MouseFilter;
        focus = holder.FocusMode;
        enabled = holder.IsEnabled;
        visible = holder.Relic.Icon.Visible;
        modulate = holder.Relic.Icon.Modulate;
        clipped = parent.ClipContents;
        switch (mode)
        {
            case "no_hover": holder.MouseFilter = Control.MouseFilterEnum.Ignore; holder.FocusMode = Control.FocusModeEnum.None; break;
            case "disabled": holder.Disable(); break;
            case "offscreen": holder.Position = new Vector2(-10000, -10000); break;
            case "hidden": holder.Relic.Icon.Visible = false; break;
            case "transparent": holder.Relic.Icon.Modulate = new Color(modulate, 0); break;
            case "clipped": parent.ClipContents = true; parent.Size = Vector2.One; holder.Position = new Vector2(100, 100); break;
            default: throw new ArgumentException("Unknown treasure display mode.");
        }
        return new { mode };
    }
}
