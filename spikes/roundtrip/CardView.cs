using Godot;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Nodes.Screens.Capstones;

namespace Sts2Agent;

internal static class CardView
{
    public static Control? Current
    {
        get
        {
            var screen = NCapstoneContainer.Instance?.CurrentCapstoneScreen as Control;
            bool supported = screen is NDeckViewScreen || screen is NCardPileScreen pile
                && pile.Pile?.Type is PileType.Draw or PileType.Discard or PileType.Exhaust;
            return supported && VisibleUi.Shown(screen) && screen!.IsNodeReady()
                && CombatObservation.Status(allowCardView: true, allowMap: true) == "visible" ? screen : null;
        }
    }

    public static bool CanClose(Control screen) => ReferenceEquals(Current, screen)
        && VisibleUi.OnScreen(screen.GetNodeOrNull<NButton>("BackButton"))
        && screen.GetNode<NButton>("BackButton").IsEnabled;

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
            && CombatObservation.Status(allowMap: true) == "visible")
            view = "map";
        if (view != null) result["view"] = view;
        return result;
    }
}
