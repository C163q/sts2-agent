using Godot;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Relics;

namespace Sts2Agent;

internal static class RelicInspection
{
    private static readonly EnglishText Names = new();
    internal sealed record RelicText(string? name, int? counter, string description, HoverTipText[] hover_tips, bool? melted);

    internal static bool? Melted(NRelic relic)
    {
        var icon = relic.Icon;
        if (!VisibleUi.OnScreen(icon) || icon.Texture == null || icon.Material is not ShaderMaterial shader) return null;
        return shader.GetShaderParameter("is_wax").AsSingle() > 0
            && icon.SelfModulate.IsEqualApprox(Colors.DarkRed);
    }

    public static NRelicInventoryHolder[]? VisibleHolders()
    {
        if (!RunUi.TopBarReadable())
            return null;
        var inventory = NRun.Instance!.GlobalUi.RelicInventory;
        if (!VisibleUi.Shown(inventory))
            return null;
        return inventory.RelicNodes.Where(holder => VisibleUi.OnScreen(holder) && holder.IsEnabled
            && holder.MouseFilter != Control.MouseFilterEnum.Ignore
            && VisibleUi.OnScreen(holder.Relic) && VisibleUi.OnScreen(holder.Relic.Icon)
            && holder.Relic.Icon.Texture != null).ToArray();
    }

    public static RelicText[] Read(NRelicInventoryHolder[] holders) => EnglishCardText.Read(() =>
        holders.Select(holder => Details(holder.Relic.Model, VisibleUi.Number(holder, "%AmountLabel"), Melted(holder.Relic))).ToArray());

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
