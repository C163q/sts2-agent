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

internal sealed class GameObservation
{
    private readonly string session = Guid.NewGuid().ToString("N");
    private int combatGeneration;
    private int uiGeneration;
    private CombatState? lastCombat;
    private readonly CombatObservation observation = new();
    private object? lastSelection;
    private int selectionGeneration;
    private PotionModel?[] lastPotions = [];
    private int potionGeneration;
    private object? lastRestSite;
    private int restSiteGeneration;
    private object? lastTreasure;
    private int treasureGeneration;

    private object? lastMap;
    private object? lastRun;
    private int mapGeneration;
    private object? lastConfirmation;
    private int confirmationGeneration;
    private readonly EventInspection eventInspection = new();
    private readonly AncientInspection ancientInspection = new();
    private readonly ShopInspection shopInspection = new();
    private readonly RunResultInspection runResultInspection = new();
    private readonly RewardInspection rewardInspection = new();

    public CombatObservation Combat => observation;
    public RewardInspection Rewards => rewardInspection;
    public ShopInspection Shop => shopInspection;
    public AncientInspection Ancient => ancientInspection;
    public EventInspection Event => eventInspection;
    public RunResultInspection RunResult => runResultInspection;
    public string Session => session;
    public void UiChanged() => uiGeneration++;

    public ObservationSnapshot Capture(Func<string, object?, EpilogueInspection.Context?,
        RunResultInspection.Context?, CardSelection?, List<string>> availableTools)
    {
        if (!NGame.IsMainThread())
            throw new InvalidOperationException("Game access requires the main thread.");
        CombatJournalScope.Current?.SampleVisibility();
        RunResourceJournal.Current?.SampleVisibility();
        RunInventoryJournal.Current?.SampleVisibility();
        PotionJournal.Current?.SampleVisibility();
        CombatResourceJournal.Current?.SampleVisibility();
        OrbJournal.Current?.SampleVisibility();
        TurnCapture.Journal?.SampleVisibility();
        CombatState? combat = CombatManager.Instance.DebugOnlyGetState();
        if (!ReferenceEquals(combat, lastCombat))
        {
            lastCombat = combat;
            combatGeneration++;
        }
        Player? player = RunContext.LocalPlayer;
        var potions = player?.PotionSlots.ToArray() ?? [];
        if (!potions.SequenceEqual(lastPotions, ReferenceEqualityComparer.Instance))
        {
            lastPotions = potions;
            potionGeneration++;
        }
        observation.Synchronize(combat, player);
        rewardInspection.Synchronize();
        shopInspection.Synchronize();
        ancientInspection.Synchronize();
        eventInspection.Synchronize();
        var confirmation = MegaCrit.Sts2.Core.Nodes.CommonUi.NModalContainer.Instance?.OpenModal;
        if (!ReferenceEquals(confirmation, lastConfirmation))
        {
            lastConfirmation = confirmation;
            confirmationGeneration++;
        }
        if (!ReferenceEquals(RestSiteInspection.Current, lastRestSite))
        {
            lastRestSite = RestSiteInspection.Current;
            restSiteGeneration++;
        }
        if (!ReferenceEquals(TreasureInspection.Current, lastTreasure))
        {
            lastTreasure = TreasureInspection.Current;
            treasureGeneration++;
        }
        var run = RunManager.Instance.DebugOnlyGetState();
        if (!ReferenceEquals(run, lastRun) || !ReferenceEquals(run?.Map, lastMap))
        {
            lastRun = run; lastMap = run?.Map; mapGeneration++;
        }
        runResultInspection.Synchronize();
        var ending = runResultInspection.Current;
        var epilogue = EpilogueInspection.Current;
        var map = ending == null ? MapInspection.Summary(run) : null;
        var selection = CardSelection.Current;
        if (!ReferenceEquals(selection?.Key, lastSelection))
        {
            lastSelection = selection?.Key;
            selectionGeneration++;
        }
        string scene = ObservationContext.Scene(ending, epilogue);
        var actions = availableTools(scene, map, epilogue, ending, selection);
        string visibility = ObservationContext.Visibility(scene, map, epilogue, ending);
        if (ending != null) selection = null;
        var screen = ObservationContext.Screen(scene, visibility, map != null);
        var combatants = scene == "combat" && CombatObservation.Status() == "visible"
            ? observation.Combatants(player) : null;
        string body = JsonSerializer.Serialize(new
        {
            schema_version = 34, language = "en", session, combat_generation = combatGeneration, ui_generation = uiGeneration, potion_generation = potionGeneration,
            rest_site_generation = restSiteGeneration, treasure_generation = treasureGeneration,
            reward_generation = rewardInspection.Generation, shop_generation = shopInspection.Generation, ancient_generation = ancientInspection.Generation,
            event_generation = eventInspection.Generation,
            confirmation_generation = confirmationGeneration,
            run_result_generation = runResultInspection.Generation, selection_generation = selectionGeneration, map_generation = mapGeneration, scene, map,
            screen,
            turn = scene == "combat" ? observation.Turn() : null,
            player = scene == "combat" ? observation.Player(player, combatants) : null,
            enemies = scene == "combat" ? observation.Enemies(combatants) : null,
            allies = scene == "combat" ? observation.Allies(combatants) : null,
            top_bar = observation.TopBar(),
            buttons = scene == "combat" ? observation.Buttons() : null,
            selection = new SelectionInspection(observation).Read(selection),
            rewards = ending == null ? rewardInspection.Read() : null,
            rest_site = ending == null ? RestSiteInspection.Read() : null,
            treasure = ending == null ? TreasureInspection.Read() : null,
            shop = ending == null ? shopInspection.Read() : null,
            ancient = ending == null ? ancientInspection.Read() : null,
            @event = ending == null ? eventInspection.Read() : null,
            divination = ending == null ? DivinationInspection.Read() : null,
            confirmation = ending == null ? EventConfirmation.Read() : null,
            epilogue = ending == null ? EpilogueInspection.Read() : null,
            run_result = runResultInspection.Read(),
            available_actions = actions
        });
        return ObservationSnapshot.Create(body, DivinationInspection.Current != null, combat, player, selection?.Key);
    }

}
