using Godot;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Relics;

namespace Sts2Agent;

internal static class RelicInspection
{
    internal sealed record RelicText(string? name, int? counter, string description, HoverTipText[] hover_tips);

    public static NRelicInventoryHolder[]? VisibleHolders()
    {
        if (CombatObservation.Status() != "visible"
            && !(AncientInspection.Current is { } ancient && AncientInspection.Exposed(ancient))
            && !(ShopInspection.Current is { } shop && ShopInspection.Exposed(shop)))
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
        holders.Select(holder => Details(holder.Relic.Model, VisibleUi.Number(holder, "%AmountLabel"))).ToArray());

    internal static RelicText Details(RelicModel model, int? counter) => EnglishRelicText.Read(model, () =>
    {
        var prefixes = model.DynamicVars.Values.OfType<EnergyVar>().Select(value => (value, value.ColorPrefix)).ToArray();
        try
        {
            var entries = model.HoverTips.Take(1).Concat(EnglishRelicText.ExtraTips(model)).Select(HoverTipText.From).ToArray();
            if (entries.Length == 0)
                throw new InvalidOperationException("Displayed relic has no main hover tip.");
            var main = entries[0];
            return new RelicText(main.title, counter, main.description,
                entries.Skip(1).Where(tip => tip != main).Distinct().ToArray());
        }
        finally
        {
            foreach (var (value, prefix) in prefixes)
                value.ColorPrefix = prefix;
        }
    });
}
