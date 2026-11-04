using Godot;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Relics;

namespace Sts2Agent;

internal static class RelicDisplayFixture
{
    private static NRelicInventoryHolder? holder;
    private static Material? material;
    private static Color color;
    private static CanvasItem? hidden;
    private static bool previousVisible;

    public static object Set(string mode, int index = 0)
    {
        if (GodotObject.IsInstanceValid(holder))
        {
            holder!.Relic.Icon.Material = material;
            holder.Relic.Icon.Modulate = color;
        }
        if (GodotObject.IsInstanceValid(hidden)) hidden!.Visible = previousVisible;
        holder = null;
        hidden = null;
        if (mode == "normal") return new { mode, source = (string?)null };
        if (mode is "hidden_inventory" or "hidden_top_bar")
        {
            hidden = mode == "hidden_inventory" ? NRun.Instance!.GlobalUi.RelicInventory : NRun.Instance!.GlobalUi.TopBar;
            previousVisible = hidden.Visible;
            hidden.Visible = false;
            return new { mode, source = (string?)null };
        }
        var holders = RelicInspection.DisplayedHolders() ?? throw new InvalidOperationException("No displayed relic inventory.");
        if (index < 0 || index >= holders.Length) throw new ArgumentOutOfRangeException(nameof(index));
        holder = holders[index];
        var icon = holder.Relic.Icon;
        material = icon.Material;
        color = icon.Modulate;
        icon.Modulate = mode is "grayed" or "both" ? new Color("#808080") : Colors.White;
        if (mode == "unknown_tint") icon.Modulate = new Color("#ff0000");
        if (mode == "no_shader") icon.Material = null;
        else
        {
            var copy = (ShaderMaterial)material!.Duplicate();
            copy.SetShaderParameter("pulse", mode is "pulsing" or "both" ? 1 : 0);
            icon.Material = copy;
        }
        return new { mode, source = $"relics.{index}" };
    }
}
