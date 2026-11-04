using Godot;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Relics;

namespace Sts2Agent;

internal static class RelicInspection
{
    private static readonly EnglishText Names = new();
    internal record StaticText(string? name, int? counter, bool? melted)
    {
        public bool? grayed_out { get; init; }
        public bool? pulsing { get; init; }
    }
    internal sealed record RelicText(string? name, int? counter, string? description, HoverTipText[] hover_tips, bool? melted)
        : StaticText(name, counter, melted);

    internal static bool? Melted(NRelic relic)
    {
        var icon = relic.Icon;
        if (!VisibleUi.Displayed(icon) || icon.Texture == null || icon.Material is not ShaderMaterial shader
            || shader.GetShaderParameter("is_wax").AsSingle() <= 0) return null;
        return icon.SelfModulate.IsEqualApprox(Colors.DarkRed);
    }

    public static NRelicInventoryHolder[]? VisibleHolders()
    {
        return DisplayedHolders();
    }

    internal static int? HeldCount() => RunUi.TopBarReadable()
        && VisibleUi.Shown(NRun.Instance!.GlobalUi.RelicInventory)
        ? NRun.Instance!.GlobalUi.RelicInventory.RelicNodes.Count : null;

    internal static NRelicInventoryHolder[]? DisplayedHolders()
    {
        if (!RunUi.TopBarReadable())
            return null;
        var inventory = NRun.Instance!.GlobalUi.RelicInventory;
        if (!VisibleUi.Shown(inventory))
            return null;
        // Inventory membership is independent of flow-layout viewport positions.
        return inventory.RelicNodes.Where(holder => VisibleUi.Displayed(holder)
            && VisibleUi.Displayed(holder.Relic) && VisibleUi.Displayed(holder.Relic.Icon)
            && holder.Relic.Icon.Texture != null
            && Mathf.Abs(holder.Relic.Icon.GetGlobalTransformWithCanvas().Determinant()) > 0.000001f).ToArray();
    }

    internal sealed record Result(RelicText[] relics, string[] unavailable_hover_sources);

    internal static StaticText Static(NRelicInventoryHolder holder) => new(
        Names.RelicName(holder.Relic.Model), VisibleUi.DisplayedNumber(holder, "%AmountLabel"), Melted(holder.Relic))
    {
        grayed_out = GrayedOut(holder.Relic.Icon),
        pulsing = ShaderFlag(holder.Relic.Icon, "pulse")
    };

    private static bool? GrayedOut(TextureRect icon)
    {
        Color tint = new(icon.Modulate, 1);
        return tint.IsEqualApprox(new Color("#808080")) ? true : tint.IsEqualApprox(Colors.White) ? false : null;
    }

    private static bool? ShaderFlag(TextureRect icon, string field)
    {
        if (icon.Material is not ShaderMaterial { Shader: { } shader } material
            || !shader.GetShaderUniformList().Any(value => value.AsGodotDictionary()["name"].AsString() == field)) return null;
        var flag = material.GetShaderParameter(field);
        if (flag.VariantType is not (Variant.Type.Int or Variant.Type.Float)) return null;
        return flag.AsDouble() switch { 0 => false, 1 => true, _ => null };
    }

    internal static string? UnavailableReason()
    {
        if (!RunUi.TopBarReadable())
            return "The top bar is not exposed in the current screen, so owned relics cannot be inspected. Close the covering dialog or wait for the screen transition.";
        return !VisibleUi.Shown(NRun.Instance!.GlobalUi.RelicInventory)
            ? "The owned relic inventory is hidden or not ready. Wait until the relic bar is displayed." : null;
    }

    internal static bool Hoverable(NRelicInventoryHolder holder) => HoverAccess.CanFocus(holder);

    public static RelicText[] Read(NRelicInventoryHolder[] holders, bool full = true) => EnglishCardText.Read(() =>
        holders.Select(holder =>
        {
            var value = Static(holder);
            var detail = full && Hoverable(holder) ? Details(holder.Relic.Model, value.counter, value.melted)
                : new RelicText(value.name, value.counter, null, [], value.melted);
            return detail with { grayed_out = value.grayed_out, pulsing = value.pulsing };
        }).ToArray());

    internal static Result Inspect(NRelicInventoryHolder[] holders, bool full = true) => new(Read(holders, full),
        full ? holders.Select((holder, index) => (holder, index)).Where(item => !Hoverable(item.holder))
            .Select(item => $"relics.{item.index}").ToArray() : []);

    internal static RelicText Details(RelicModel model, int? counter, bool? melted = null) => EnglishRelicText.Read(model, () =>
    {
        var prefixes = model.DynamicVars.Values.OfType<EnergyVar>().Select(value => (value, value.ColorPrefix)).ToArray();
        try
        {
            var entries = model.HoverTips.Take(1).Concat(EnglishRelicText.ExtraTips(model)).Select(HoverTipText.From).ToArray();
            if (entries.Length == 0)
                throw new InvalidOperationException("Displayed relic has no main hover tip.");
            var main = entries[0];
            return new RelicText(Names.RelicName(model), counter, main.description,
                entries.Skip(1).Where(tip => tip != main).Distinct().ToArray(), melted);
        }
        finally
        {
            foreach (var (value, prefix) in prefixes)
                value.ColorPrefix = prefix;
        }
    });
}
