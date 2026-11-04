using Godot;
using MegaCrit.Sts2.Core.Nodes.Potions;

namespace Sts2Agent;

internal static class PotionDisplayFixture
{
    private static NPotionHolder? holder;
    private static TextureRect? icon;
    private static bool previousVisible, previousEnabled;
    private static Vector2 previousPosition;
    private static Control.MouseFilterEnum previousMouse;
    private static Control.FocusModeEnum previousFocus;

    public static object Set(string mode, int index = 0)
    {
        if (GodotObject.IsInstanceValid(holder))
        {
            if (previousEnabled) holder!.Enable(); else holder!.Disable();
            holder.Position = previousPosition;
            holder.MouseFilter = previousMouse;
            holder.FocusMode = previousFocus;
        }
        if (GodotObject.IsInstanceValid(icon)) icon!.Visible = previousVisible;
        holder = null;
        icon = null;
        if (mode == "normal") return new { mode, source = (string?)null };
        var holders = PotionInspection.VisibleHolders() ?? throw new InvalidOperationException("No displayed potion slots.");
        if (index < 0 || index >= holders.Length) throw new ArgumentOutOfRangeException(nameof(index));
        holder = holders[index];
        icon = holder.HasPotion ? holder.Potion!.GetNode<TextureRect>("%Image") : holder.GetNode<TextureRect>("%EmptyIcon");
        previousVisible = icon.Visible;
        previousEnabled = holder.IsEnabled;
        previousPosition = holder.Position;
        previousMouse = holder.MouseFilter;
        previousFocus = holder.FocusMode;
        switch (mode)
        {
            case "no_hover": holder.MouseFilter = Control.MouseFilterEnum.Ignore; holder.FocusMode = Control.FocusModeEnum.None; break;
            case "disabled": holder.Disable(); break;
            case "hidden": icon.Visible = false; break;
            case "offscreen": holder.Position = new Vector2(-10000, -10000); break;
            default: throw new ArgumentException("Unknown potion display fixture.");
        }
        return new { mode, source = $"potion_slots.{index}" };
    }
}
