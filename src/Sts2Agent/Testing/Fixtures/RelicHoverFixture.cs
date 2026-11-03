using Godot;
using MegaCrit.Sts2.Core.Nodes.Relics;

namespace Sts2Agent;

internal static class RelicHoverFixture
{
    private static NRelicInventoryHolder? holder;
    private static Control.MouseFilterEnum previousMouse;
    private static Control.FocusModeEnum previousFocus;

    public static object SetEnabled(bool enabled)
    {
        if (GodotObject.IsInstanceValid(holder))
        {
            holder!.MouseFilter = previousMouse;
            holder.FocusMode = previousFocus;
        }
        holder = null;
        if (enabled) return new { enabled, source = (string?)null };
        var holders = RelicInspection.DisplayedHolders() ?? throw new InvalidOperationException("No displayed relics.");
        int index = holders.Length - 1;
        holder = holders[index];
        previousMouse = holder.MouseFilter;
        previousFocus = holder.FocusMode;
        holder.MouseFilter = Control.MouseFilterEnum.Ignore;
        holder.FocusMode = Control.FocusModeEnum.None;
        return new { enabled, source = $"relics.{index}" };
    }
}
