using HarmonyLib;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Rewards;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class TreasureFixture
{
    private static Func<Task>? nextFrame;
    private static bool delayedDone;

    public static async Task Configure(string scenario, Player player, Func<Task> frame)
    {
        RunManager.Instance.DebugOnlyGetState()!.ActFloor = 1;
        nextFrame = frame;
        if (scenario == "map_pending") new Harmony("sts2_agent.test_treasure_map_pending").Patch(
            AccessTools.Method(typeof(RelicModel), nameof(RelicModel.AfterObtained)),
            postfix: new HarmonyMethod(typeof(TreasureFixture), nameof(DelayObtain)));
        if (scenario == "extra") new Harmony("sts2_agent.test_treasure_extra").Patch(
            AccessTools.Method(typeof(RewardsSet), nameof(RewardsSet.WithRewardsFromRoom)),
            postfix: new HarmonyMethod(typeof(TreasureFixture), nameof(AddExtraReward)));
        if (scenario == "empty") await RelicCmd.Obtain<SilverCrucible>(player);
        await RunManager.Instance.EnterRoomDebug(RoomType.Treasure, showTransition: false);
        // Fix only the isolated fixture's generated offer, never the production observation path.
        if (scenario != "empty")
        {
            var offers = (List<RelicModel>)RunManager.Instance.TreasureRoomRelicSynchronizer.CurrentRelics!;
            offers.Clear();
            offers.Add(scenario switch
            {
                "nested" => ModelDb.Relic<CallingBell>(),
                "choice" => ModelDb.Relic<Astrolabe>(),
                _ => ModelDb.Relic<Anchor>()
            });
        }
        for (int i = 0; i < 600 && (TreasureInspection.Current == null || !TreasureInspection.Ready(TreasureInspection.Current)); i++)
            await frame();
        if (TreasureInspection.Current == null || !TreasureInspection.Ready(TreasureInspection.Current))
            throw new InvalidOperationException("Treasure fixture did not become ready.");
    }

    private static void DelayObtain(RelicModel __instance, ref Task __result)
    {
        if (__instance is Anchor) __result = Delayed(__result, __instance.Owner);
    }

    private static async Task Delayed(Task original, Player player)
    {
        await original;
        for (int i = 0; i < 600; i++)
        {
            await nextFrame!();
            if (TreasureInspection.Current is { } room && TreasureInspection.Opened(room)
                && room.ProceedButton.IsEnabled && !VisibleUi.Shown(TreasureInspection.Collection(room))) break;
        }
        NRun.Instance!.GlobalUi.MapScreen.Open();
        for (int i = 0; i < 600 && !MapView.Ready(NRun.Instance.GlobalUi.MapScreen); i++) await nextFrame!();
        await Cmd.Wait(2f);
        await PlayerCmd.GainGold(7, player);
        delayedDone = true;
    }

    private static void AddExtraReward(RewardsSet __instance, AbstractRoom __0)
    {
        if (__0 is TreasureRoom) __instance.WithCustomRewards([new GoldReward(7, 7, __instance.Player)]);
    }

    public static object Read(Player player) => new
    {
        gold = player.Gold, delayed_done = delayedDone, relics = player.Relics.Select(r => r.Id.Entry).ToArray(),
        opened = TreasureInspection.Current is { } room && TreasureInspection.Opened(room),
        obtaining = RelicObtainTracker.Pending, preview_cards = RunUi.CardPreviewsPending(),
        crucible_rooms = player.GetRelic<SilverCrucible>()?.TreasureRoomsEntered
    };
}
