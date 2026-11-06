using System.Reflection;
using Godot;
using MegaCrit.Sts2.Core.Events.Custom.CrystalSphereEvent;
using MegaCrit.Sts2.Core.Nodes.Events.Custom.CrystalSphere;

namespace Sts2Agent;

internal static class DivinationDisplayFixture
{
    private static Action? restore;
    public static object Set(string mode, int index, int dx, int dy)
    {
        restore?.Invoke(); restore = null;
        if (mode == "normal") return new { mode };
        if (mode is not ("partial" or "whole" or "all_clear" or "swapped_banner"))
            throw new ArgumentException("Unknown divination display mode.");
        var screen = DivinationInspection.Current ?? throw new InvalidOperationException("A test divination board is required.");
        var cells = DivinationInspection.Cells(screen);
        var nodes = VisibleUi.Descendants<NCrystalSphereItem>(screen).ToArray();
        if (index < 0 || index >= nodes.Length) throw new ArgumentException("Unknown test icon index.");
        var selected = nodes[index];
        var entity = (CrystalSphereItem)typeof(NCrystalSphereItem).GetField("_item", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(selected)!;
        if (dx < 0 || dy < 0 || dx >= entity.Size.X || dy >= entity.Size.Y) throw new ArgumentException("Unknown test icon part.");
        var mask = screen.GetNode<NCrystalSphereMask>("%ScryMask");
        var values = (Godot.Collections.Array<Vector3>)PrivateFields.Read(mask, "_values")!;
        var oldValues = values.ToArray();
        var flags = cells.Select(c => c.Entity.IsHidden).ToArray();
        var shown = nodes.Select(n => n.Visible).ToArray();
        var material = (ShaderMaterial)mask.Material;
        var clock = typeof(NCrystalSphereMask).GetField("_time", BindingFlags.Instance | BindingFlags.NonPublic)!;
        float oldTime = (float)clock.GetValue(mask)!;
        var banner = selected.GetNode<TextureRect>("%CardBanner");
        var oldMaterial = banner.Material;
        restore = () => {
            if (!GodotObject.IsInstanceValid(screen)) return;
            for (int i = 0; i < nodes.Length; i++) nodes[i].Visible = shown[i];
            for (int i = 0; i < cells.Length; i++) cells[i].Entity.IsHidden = flags[i];
            for (int i = 0; i < values.Count; i++) values[i] = oldValues[i];
            clock.SetValue(mask, oldTime); material.SetShaderParameter("time", oldTime);
            material.SetShaderParameter("gridFadeParams", values); banner.Material = oldMaterial;
        };
        for (int i = 0; i < nodes.Length; i++) nodes[i].Visible = i == index;
        foreach (var cell in cells)
        {
            bool reveal = mode is "whole" or "all_clear" ? mode == "all_clear"
                || cell.Entity.X >= entity.Position.X && cell.Entity.X < entity.Position.X + entity.Size.X
                    && cell.Entity.Y >= entity.Position.Y && cell.Entity.Y < entity.Position.Y + entity.Size.Y
                : cell.Entity.X == entity.Position.X + dx && cell.Entity.Y == entity.Position.Y + dy;
            cell.Entity.IsHidden = !reveal;
        }
        // This fixture changes only display flags; it never calls RevealItem or generates rewards.
        clock.SetValue(mask, 10f); material.SetShaderParameter("time", 10f);
        foreach (var cell in cells)
        {
            float alpha = cell.Entity.IsHidden ? 1 : 0;
            values[cell.Entity.Y * 11 + cell.Entity.X] = new Vector3(alpha, alpha, 1);
        }
        material.SetShaderParameter("gridFadeParams", values);
        if (mode == "swapped_banner")
            banner.Material = ResourceLoader.Load<Material>("res://materials/cards/banners/card_banner_rare_mat.tres");
        return new { mode, x = entity.Position.X, y = entity.Position.Y,
            width = entity.Size.X, height = entity.Size.Y, kind = entity.GetType().Name };
    }
}
