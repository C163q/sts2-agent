using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class RunUi
{
    public static bool Transitioning()
    {
        var game = NGame.Instance;
        return game == null || game.Transition.InTransition
            || VisibleUi.Shown(game.Transition) && game.Transition.Material is ShaderMaterial material
                && material.GetShaderParameter("threshold").AsSingle() > 0.000001f
            || VisibleUi.Descendants<CanvasItem>(game.Transition).Any(VisibleUi.Shown);
    }

    public static bool NonCombatVisible()
    {
        var run = NRun.Instance;
        var global = run?.GlobalUi;
        var game = NGame.Instance;
        return !CombatManager.Instance.IsInProgress && RunManager.Instance.IsInProgress
            && game != null && game.MainMenu == null && VisibleUi.Shown(run) && global?.IsNodeReady() == true
            && !global.CapstoneContainer.InUse && (global.Overlays.ScreenCount == 0
                || global.Overlays.ScreenCount == 1 && global.Overlays.Peek() is NRewardsScreen rewards && VisibleUi.Shown(rewards))
            && !global.MapScreen.IsTraveling && NModalContainer.Instance?.OpenModal == null
            && !VisibleUi.Shown(game.InspectCardScreen) && !VisibleUi.Shown(game.InspectRelicScreen)
            && !Transitioning();
    }

    public static bool TopBarReadable() => VisibleUi.OnScreen(NRun.Instance?.GlobalUi.TopBar)
        && (CombatObservation.Status() == "visible" || CardSelection.Current is { Status: "visible" } || NonCombatVisible());
}
