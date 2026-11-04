using Godot;
using System.Reflection;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Nodes.Screens.Capstones;

namespace Sts2Agent;

internal static class CardView
{
    private static readonly FieldInfo SortedCards = typeof(NCardGrid).GetField("_cards", BindingFlags.Instance | BindingFlags.NonPublic)!;
    public static NCardGrid Grid(Control screen) => screen.GetNode<NCardGrid>("CardGrid");
    public static CardModel[] Cards(Control screen) => ((List<CardModel>)SortedCards.GetValue(Grid(screen))!).ToArray();
    public static bool Ready(Control screen) => ReferenceEquals(Current, screen) && !Grid(screen).IsAnimatingOut
        && (Cards(screen).Length == 0 || Grid(screen).CurrentlyDisplayedCardHolders.Any()) && CanClose(screen);

    public static Control? Current
    {
        get
        {
            var screen = NCapstoneContainer.Instance?.CurrentCapstoneScreen as Control;
            return Supported(screen) && VisibleUi.Shown(screen) && screen!.IsNodeReady()
                && (CombatObservation.Status(allowCardView: true, allowMap: true) == "visible"
                    || screen is NDeckViewScreen && RunUi.NonCombatVisible(allowCardView: true)) ? screen : null;
        }
    }

    private static bool Supported(Control? screen) => screen is NDeckViewScreen || screen is NCardPileScreen pile
        && pile.Pile?.Type is PileType.Draw or PileType.Discard or PileType.Exhaust;

    public static string? CloseUnavailableReason(Control? screen)
    {
        if (screen == null)
        {
            if (Supported(NCapstoneContainer.Instance?.CurrentCapstoneScreen as Control))
                return "The card browsing page is covered, hidden or not ready. Return to it before closing it.";
            if (CardSelection.Current is { Status: "visible" or "unsupported" })
                return "A card selection is active. close_card_view only closes deck and combat-pile browsing pages.";
            return "No supported card browsing page is open.";
        }
        if (!ReferenceEquals(Current, screen)) return "The card browsing page is no longer exposed.";
        var button = screen.GetNodeOrNull<NButton>("BackButton");
        if (button == null) return "The card browsing return button is not ready.";
        if (!VisibleUi.OnScreen(button)) return "The card browsing return button is not visible.";
        return button.IsEnabled ? null : "The card browsing return button is disabled.";
    }

    public static bool CanClose(Control screen) => CloseUnavailableReason(screen) == null;

    public static void Close(Control screen) => screen.GetNode<NButton>("BackButton").ForceClick();

    public static Dictionary<string, string> Screen(string status)
    {
        var result = new Dictionary<string, string> { ["status"] = status };
        string? view = Current switch
        {
            NDeckViewScreen => "deck",
            NCardPileScreen pile => pile.Pile.Type.ToString().ToLowerInvariant() + "_pile",
            _ => null
        };
        if (view == null && NRun.Instance?.GlobalUi.MapScreen.IsOpen == true
            && MapView.Clear())
            view = "map";
        if (view == null && DivinationInspection.Current is { } divination && DivinationInspection.Exposed(divination)) view = "divination";
        view ??= EventInspection.ManualView;
        if (view != null) result["view"] = view;
        return result;
    }
}
