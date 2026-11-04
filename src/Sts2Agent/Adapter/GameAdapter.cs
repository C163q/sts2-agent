using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Characters;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Encounters;
using MegaCrit.Sts2.Core.Models.Potions;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Nodes.Screens.Capstones;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Saves;

namespace Sts2Agent;

internal sealed partial class GameAdapter(bool testMode)
{
    private readonly GameObservation capture = new();
    private DeckInspection deckInspection => capture.Deck;
    private PileInspection pileInspection => capture.Piles;
    private CombatObservation observation => capture.Combat;
    private RewardInspection rewardInspection => capture.Rewards;
    private ShopInspection shopInspection => capture.Shop;
    private AncientInspection ancientInspection => capture.Ancient;
    private EventInspection eventInspection => capture.Event;
    private RunResultInspection runResultInspection => capture.RunResult;

    private static Player? LocalPlayer => RunContext.LocalPlayer;

    private static bool CanEndTurn(bool allowMapPause = false)
    {
        CombatManager combat = CombatManager.Instance;
        Player? player = LocalPlayer;
        NCombatRoom? room = NCombatRoom.Instance;
        return RunManager.Instance.IsInProgress
            && RunManager.Instance.IsSingleplayerOrFakeMultiplayer
            && combat.IsInProgress && (!combat.IsPaused || allowMapPause) && !combat.IsOverOrEnding
            && !combat.PlayerActionsDisabled
            && player?.PlayerCombatState?.Phase == PlayerTurnPhase.Play
            && player.Creature.IsAlive && !combat.IsPlayerReadyToEndTurn(player)
            && (combat.PlayersTakingExtraTurn.Count == 0 || combat.PlayersTakingExtraTurn.Contains(player))
            && room?.Ui?.Hand != null && !room.Ui.Hand.InCardPlay
            && room.Ui.Hand.CurrentMode == NPlayerHand.Mode.Play && CardSelection.Current == null;
    }

    private static bool CanInspectViews(bool allowPause = false) => CanEndTurn(allowPause)
        || CardSelection.Current is { Peeking: true, Supported: true } && LocalPlayer?.Creature.IsAlive == true;

    private ObservationSnapshot Capture() => execution is { } request
        ? request.RecordCapture(() => capture.Capture(AvailableTools)) : capture.Capture(AvailableTools);
    public string Observe() => Capture().Json;

}
