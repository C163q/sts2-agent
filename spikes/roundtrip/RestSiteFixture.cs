using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.RestSite;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.TestSupport;

namespace Sts2Agent;

internal static class RestSiteFixture
{
    public static async Task Configure(string scenario, Player player, Func<Task> frame)
    {
        RunManager.Instance.DebugOnlyGetState()!.ActFloor = 1;
        await CreatureCmd.SetCurrentHp(player.Creature, 30);
        if (scenario is "cook" or "disabled") await RelicCmd.Obtain<MeatCleaver>(player);
        if (scenario == "tent")
        {
            await RelicCmd.Obtain<MiniatureTent>(player);
            await RelicCmd.Obtain<Girya>(player);
            await RelicCmd.Obtain<PumpkinCandle>(player);
            await RelicCmd.Obtain<MeatCleaver>(player);
        }
        if (scenario.StartsWith("dig", StringComparison.Ordinal)) await RelicCmd.Obtain<Shovel>(player);
        if (scenario == "heal_rewards") await RelicCmd.Obtain<DreamCatcher>(player);
        if (scenario == "disabled")
        {
            await CardPileCmd.RemoveFromDeck(player.Deck.Cards.Skip(1).ToArray());
            CardCmd.Upgrade(player.Deck.Cards.First(), CardPreviewStyle.None);
        }
        await RunManager.Instance.EnterRoomDebug(RoomType.RestSite, showTransition: false);
        if (scenario == "dig_nested") TestRngInjector.SetRelicOverride<CallingBell>();
        if (scenario == "dig_choice") TestRngInjector.SetRelicOverride<Astrolabe>();
        if (scenario == "multi")
            NRestSiteRoom.Instance!.Options.OfType<SmithRestSiteOption>().Single().SmithCount = 2;
        for (int i = 0; i < 600 && (RestSiteInspection.Current == null || !RestSiteInspection.Ready(RestSiteInspection.Current)); i++)
            await frame();
        if (RestSiteInspection.Current == null || !RestSiteInspection.Ready(RestSiteInspection.Current))
            throw new InvalidOperationException("Rest site fixture did not become ready.");
    }

    public static object Read(Player player) => new
    {
        hp = player.Creature.CurrentHp, max_hp = player.Creature.MaxHp,
        deck = player.Deck.Cards.Select(c => new { name = EnglishCardText.Read(() => EnglishCardText.Plain(c.Title)),
            upgrades = c.CurrentUpgradeLevel }).ToArray(),
        relics = player.Relics.Select(r => r.Id.Entry).ToArray(),
        lifts = player.GetRelic<Girya>()?.TimesLifted, kindle = player.GetRelic<PumpkinCandle>()?.KindleCount,
        native_options = NRestSiteRoom.Instance?.Options.Select(o => o.OptionId).ToArray(),
        preview_cards = RunUi.CardPreviewsPending()
    };
}
