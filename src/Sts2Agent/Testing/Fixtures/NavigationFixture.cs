using MegaCrit.Sts2.Core.Assets;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Map;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Screens.Map;
using MegaCrit.Sts2.Core.Random;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Unlocks;

namespace Sts2Agent;

internal static class NavigationFixture
{
    public static async Task Configure(string scenario, Player player, Func<Task> frame)
    {
        var manager = RunManager.Instance;
        var run = manager.DebugOnlyGetState()!;
        foreach (var act in run.Acts) act.GenerateRooms(new Rng(9751, "navigation_fixture"), UnlockState.all);
        if (scenario is "boss2" or "boss3") await manager.EnterAct(scenario == "boss2" ? 1 : 2);
        if (scenario == "double")
        {
            run.Act.SetSecondBossEncounter(run.Act.AllBossEncounters.First(e => e.Id != run.Act.BossEncounter.Id));
            await PreloadManager.LoadActAssets(run.Act);
        }
        var map = new StandardActMap(new Rng(1234, "navigation_map_fixture"), run.Act, false, false, hasSecondBoss: scenario == "double");
        run.Map = map;
        run.ClearVisitedMapCoordsDebug();
        var screen = NMapScreen.Instance!;
        if (scenario is "boss1" or "boss2" or "boss3" or "double")
        {
            run.AddVisitedMapCoord(map.BossMapPoint.coord);
            screen.SetMap(map, run.Rng.Seed, clearDrawings: true);
            manager.MapSelectionSynchronizer.OnLocationChanged(run.MapLocation);
            await manager.EnterRoomDebug(RoomType.Boss, model: run.Act.BossEncounter.ToMutable(), showTransition: false);
            await FinishBoss(frame);
            return;
        }
        var source = map.GetAllMapPoints().First(p => p.coord.row == 1 && p.Children.Count > 0
            && map.GetPointsInRow(2).Any(q => !p.Children.Contains(q)));
        foreach (var point in map.GetPointsInRow(2))
            point.PointType = scenario switch { "combat" or "choice" or "antler" or "resource_combat" => MapPointType.Monster,
                "shop" => MapPointType.Shop, "treasure" => MapPointType.Treasure, "unknown" or "resource_unknown" => MapPointType.Unknown,
                _ => MapPointType.RestSite };
        run.AddVisitedMapCoord(source.coord);
        run.ActFloor = 2;
        screen.SetMap(map, run.Rng.Seed, clearDrawings: true);
        screen.InitMarker(source.coord);
        manager.MapSelectionSynchronizer.OnLocationChanged(run.MapLocation);
        if (scenario is "basic" or "flight")
        {
            var boots = await RelicCmd.Obtain<WingedBoots>(player);
            if (scenario == "flight") boots.TimesUsed = 2;
        }
        if (scenario == "choice") await RelicCmd.Obtain<ChoicesParadox>(player);
        if (scenario == "antler") await RelicCmd.Obtain<BlessedAntler>(player);
        await RewardFixture.Configure("basic", player, frame);
        if (scenario.StartsWith("resource_", StringComparison.Ordinal))
        {
            await RelicCmd.Obtain<MawBank>(player);
            await RelicCmd.Obtain<Planisphere>(player);
            await CreatureCmd.SetCurrentHp(player.Creature, 60);
            await PlayerCmd.SetGold(100, player);
        }
        screen.SetTravelEnabled(true);
    }

    public static async Task FinishBoss(Func<Task> frame)
    {
        for (int i = 0; i < 900 && !CombatManager.Instance.IsInProgress; i++) await frame();
        foreach (var enemy in CombatManager.Instance.DebugOnlyGetState()!.Enemies.ToArray())
            await CreatureCmd.Kill(enemy, force: true);
        await CombatManager.Instance.CheckWinCondition();
        for (int i = 0; i < 900 && (RewardInspection.Current == null || !RewardInspection.Ready(RewardInspection.Current)); i++) await frame();
        if (RewardInspection.Current == null || !RewardInspection.Ready(RewardInspection.Current))
            throw new InvalidOperationException("Native Boss rewards did not become ready.");
    }

    public static object Read(Player player)
    {
        var run = RunManager.Instance.DebugOnlyGetState()!;
        return new { gold = player.Gold, hp = player.Creature.CurrentHp, boots_used = player.Relics.OfType<WingedBoots>().SingleOrDefault()?.TimesUsed,
            current_node = run.CurrentMapCoord is { } coord ? MapInspection.Id(run, coord) : null,
            act = run.CurrentActIndex + 1, rewards = RewardInspection.Current != null,
            @event = (run.CurrentRoom as EventRoom)?.LocalMutableEvent.Id.Entry,
            traveling = NMapScreen.Instance?.IsTraveling, changing_act = NavigationTasks.ChangingAct };
    }
}
