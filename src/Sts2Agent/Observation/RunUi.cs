using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Relics;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Rooms;

namespace Sts2Agent;

internal static class RunUi
{
    public static EventModel? LocalEvent
    {
        get
        {
            var run = RunManager.Instance.DebugOnlyGetState();
            if (run?.CurrentRoom is not EventRoom || LocalContext.GetMe(run) is not { } player) return null;
            var events = RunManager.Instance.EventSynchronizer.Events;
            int slot = run.GetPlayerSlotIndex(player);
            // Room identity changes before asynchronous event setup fills the synchronizer.
            return slot >= 0 && slot < events.Count ? events[slot] : null;
        }
    }

    public static bool ResourceMotionPending() => NRun.Instance is { } run
        && (CardSelection.Field(run.GlobalUi.TopBar.Gold, "_alreadyRunning") is true
            || VisibleUi.Descendants<MegaCrit.Sts2.Core.Nodes.Potions.NPotion>(run.GlobalUi.TopBar.PotionContainer)
                .Any(potion => RewardInspection.Animating(potion, "_obtainedTween"))
            || VisibleUi.Descendants<NRelicInventoryHolder>(run.GlobalUi.RelicInventory)
                .Any(holder => holder.IsNodeReady() && !holder.IsQueuedForDeletion()
                    && (RewardInspection.Animating(holder, "_obtainedTween")
                        // Pael's Wing resets its counter after an independent activation task.
                        || holder.Relic.Model is PaelsWing wing && CardSelection.Field(wing, "_isActivating") is true)));

    public static bool CardPreviewsPending()
    {
        var global = NRun.Instance?.GlobalUi;
        var combat = NCombatRoom.Instance?.Ui;
        Node?[] containers = [global?.CardPreviewContainer, global?.MessyCardPreviewContainer,
            global?.EventCardPreviewContainer, global?.GridCardPreviewContainer,
            combat?.CardPreviewContainer, combat?.MessyCardPreviewContainer];
        // Previews spawn future pile flights, including while covered or entering the screen.
        return containers.Any(container => container != null && GodotObject.IsInstanceValid(container)
            && VisibleUi.Descendants<NCard>(container).Any(card => card.IsInsideTree() && !card.IsQueuedForDeletion()));
    }

    public static bool OnlyRewardOverlays()
    {
        var overlays = NRun.Instance?.GlobalUi.Overlays;
        return overlays?.ScreenCount > 0 && overlays.Peek() is NRewardsScreen
            && VisibleUi.Descendants<NRewardsScreen>(overlays).Count(s => !s.IsQueuedForDeletion())
                + (DivinationInspection.Current == null ? 0 : 1) == overlays.ScreenCount;
    }

    public static bool Transitioning()
    {
        var game = NGame.Instance;
        return game == null || game.Transition.InTransition
            || VisibleUi.Shown(game.Transition) && game.Transition.Material is ShaderMaterial material
                && material.GetShaderParameter("threshold").AsSingle() > 0.000001f
            || VisibleUi.Descendants<CanvasItem>(game.Transition).Any(VisibleUi.Shown);
    }

    public static bool NonCombatVisible(bool allowCardView = false)
    {
        var run = NRun.Instance;
        var global = run?.GlobalUi;
        var game = NGame.Instance;
        return !CombatManager.Instance.IsInProgress && RunManager.Instance.IsInProgress
            && game != null && game.MainMenu == null && VisibleUi.Shown(run) && global?.IsNodeReady() == true
            && (!global.CapstoneContainer.InUse || allowCardView
                && global.CapstoneContainer.CurrentCapstoneScreen is NDeckViewScreen)
            && (global.Overlays.ScreenCount == 0
                || OnlyRewardOverlays() && global.Overlays.Peek() is NRewardsScreen rewards && VisibleUi.Shown(rewards)
                || DivinationInspection.OnlyOverlay)
            && !global.MapScreen.IsTraveling && NModalContainer.Instance?.OpenModal == null
            && !VisibleUi.Shown(game.InspectCardScreen) && !VisibleUi.Shown(game.InspectRelicScreen)
            && !Transitioning();
    }

    private static bool ResultTopBarVisible() => NRun.Instance?.GlobalUi.Overlays.Peek()
        is MegaCrit.Sts2.Core.Nodes.Screens.GameOverScreen.NGameOverScreen screen
        && RunResultInspection.Exposed(new(screen, "outcome"));

    public static bool TopBarReadable() => VisibleUi.OnScreen(NRun.Instance?.GlobalUi.TopBar)
        && (CombatObservation.Status() == "visible" || CardSelection.Current is { Status: "visible" }
            // Browsers cover the room while leaving the top bar exposed.
            || CardView.Current != null
            || NRun.Instance?.GlobalUi.MapScreen is { } map && MapView.Current(map)
            || NonCombatVisible() || ResultTopBarVisible());
}
