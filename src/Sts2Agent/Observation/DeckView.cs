using System.Reflection;
using Godot;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Nodes.Screens.Capstones;
using MegaCrit.Sts2.Core.Nodes.Screens.CardLibrary;

namespace Sts2Agent;

internal static class DeckView
{
    private const BindingFlags PrivateInstance = BindingFlags.Instance | BindingFlags.NonPublic;
    private static readonly FieldInfo SortingPriority = typeof(NDeckViewScreen).GetField("_sortingPriority", PrivateInstance)!;
    internal sealed record Sort(string by, bool descending);

    public static NDeckViewScreen? Current => NCapstoneContainer.Instance?.CurrentCapstoneScreen is NDeckViewScreen screen
        && ReferenceEquals(CardView.Current, screen)
        ? screen : null;

    public static NCardGrid Grid(NDeckViewScreen screen) => CardView.Grid(screen);
    public static CardModel[] Cards(NDeckViewScreen screen) => CardView.Cards(screen);

    public static Sort Sorting(NDeckViewScreen screen) =>
        ((List<SortingOrders>)SortingPriority.GetValue(screen)!)[0] switch
        {
            SortingOrders.Ascending => new("obtained", false), SortingOrders.Descending => new("obtained", true),
            SortingOrders.TypeAscending => new("type", false), SortingOrders.TypeDescending => new("type", true),
            SortingOrders.CostAscending => new("cost", false), SortingOrders.CostDescending => new("cost", true),
            SortingOrders.AlphabetAscending => new("name", false), SortingOrders.AlphabetDescending => new("name", true),
            _ => throw new InvalidOperationException("Unknown deck sorting.")
        };

    public static bool Ready(NDeckViewScreen screen) => ReferenceEquals(Current, screen)
        && !Grid(screen).IsAnimatingOut && (Cards(screen).Length == 0 || Grid(screen).CurrentlyDisplayedCardHolders.Any());

    public static void Apply(NDeckViewScreen screen, DeckOptions options)
    {
        if (!ReferenceEquals(Current, screen)) throw new InvalidOperationException("The deck screen changed.");
        var tickbox = screen.GetNode<NTickbox>("%Upgrades");
        if (options.ViewUpgrades.HasValue && (!VisibleUi.OnScreen(tickbox) || !tickbox.IsEnabled))
            throw new InvalidOperationException("The upgrade control is unavailable.");
        NCardViewSortButton? sorter = options.SortBy == null ? null : screen.GetNode<NCardViewSortButton>(options.SortBy switch
        {
            "obtained" => "%ObtainedSorter", "type" => "%CardTypeSorter", "cost" => "%CostSorter", _ => "%AlphabeticalSorter"
        });
        if (sorter != null && (!VisibleUi.OnScreen(sorter) || !sorter.IsEnabled))
            throw new InvalidOperationException("The sorting control is unavailable.");
        if (sorter != null)
        {
            sorter.IsDescending = !(options.Descending ?? false);
            sorter.ForceClick();
        }
        if (options.ViewUpgrades.HasValue && tickbox.IsTicked != options.ViewUpgrades.Value)
            tickbox.ForceClick();
    }

    public static bool CanClose(NDeckViewScreen screen) => ReferenceEquals(Current, screen)
        && VisibleUi.OnScreen(screen.GetNode<Control>("BackButton"))
        && screen.GetNode<MegaCrit.Sts2.Core.Nodes.GodotExtensions.NButton>("BackButton").IsEnabled;

    public static void Close(NDeckViewScreen screen) =>
        screen.GetNode<MegaCrit.Sts2.Core.Nodes.GodotExtensions.NButton>("BackButton").ForceClick();
}
