using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Events;
using MegaCrit.Sts2.Core.Models.Relics;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Encounters;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class AncientFixture
{
    public static async Task Configure(string scenario, Player player, Func<Task> frame)
    {
        RunManager.Instance.DebugOnlyGetState()!.ActFloor = 1;
        (AncientEventModel model, string option) = scenario switch {
            "touch" => ((AncientEventModel)ModelDb.Event<Orobas>(), "TOUCH_OF_OROBAS"),
            "tooth" => ((AncientEventModel)ModelDb.Event<Pael>(), "PAELS_TOOTH"),
            "eye" => ((AncientEventModel)ModelDb.Event<Pael>(), "PAELS_EYE"),
            "earring" => ((AncientEventModel)ModelDb.Event<Vakuu>(), "WHISPERING_EARRING"),
            "shrymp" => ((AncientEventModel)ModelDb.Event<Orobas>(), "ELECTRIC_SHRYMP"),
            "multi" => ((AncientEventModel)ModelDb.Event<Tanx>(), "TRI_BOOMERANG"),
            "transform" => ((AncientEventModel)ModelDb.Event<Neow>(), "NEW_LEAF"),
            "bundle" => ((AncientEventModel)ModelDb.Event<Neow>(), "SCROLL_BOXES"),
            "nested" => ((AncientEventModel)ModelDb.Event<Neow>(), "LOST_COFFER"),
            "pandora" => ((AncientEventModel)ModelDb.Event<Darv>(), "PANDORAS_BOX"),
            _ => ((AncientEventModel)ModelDb.Event<Neow>(), "NUTRITIOUS_OYSTER") };
        await RunManager.Instance.EnterRoom(new EventRoom(model) { OnStart = e => ((AncientEventModel)e).DebugOption = option });
        for (int i = 0; i < 600 && (AncientInspection.Current == null || !AncientInspection.Ready(AncientInspection.Current)); i++) await frame();
        if (AncientInspection.Current == null || !AncientInspection.Ready(AncientInspection.Current))
            throw new InvalidOperationException("Ancient fixture did not become ready.");
        if (scenario == "dialogue")
        {
            var context = AncientInspection.Current!;
            var dialogue = context.Model.DialogueSet.GetValidDialogues(player.Character.Id, 4, 10, true)
                .OrderByDescending(d => d.Lines.Count).First();
            context.Layout.ClearDialogue();
            context.Layout.SetDialogue(dialogue.Lines);
            context.Layout.OnSetupComplete();
            for (int i = 0; i < 600 && !AncientInspection.Ready(context); i++) await frame();
        }
        NRun.Instance!.GlobalUi.MapScreen.SetTravelEnabled(false);
    }

    public static async Task EnterCombat(string scenario, Player player, Func<Task> frame)
    {
        await RunManager.Instance.EnterRoomDebug(RoomType.Monster, model: ModelDb.Encounter<SlimesWeak>().ToMutable(), showTransition: false);
        for (int i = 0; i < 600 && (!CombatManager.Instance.IsInProgress || player.PlayerCombatState?.Phase != PlayerTurnPhase.Play
            || !RunManager.Instance.ActionQueueSet.IsEmpty); i++) await frame();
        if (scenario == "tooth")
        {
            foreach (var enemy in CombatManager.Instance.DebugOnlyGetState()!.Enemies) await CreatureCmd.SetCurrentHp(enemy, 1);
            await CardPileCmd.AddGeneratedCardToCombat(CombatManager.Instance.DebugOnlyGetState()!.CreateCard<Thunderclap>(player), PileType.Hand, player);
        }
    }

    public static object Read(Player player) => new {
        hp = player.Creature.CurrentHp, max_hp = player.Creature.MaxHp,
        deck = player.Deck.Cards.Select(c => new { name = EnglishCardText.Read(() => EnglishCardText.Plain(c.Title)),
            upgrades = c.CurrentUpgradeLevel, enchantment = c.Enchantment?.Id.Entry }).ToArray(),
        relics = player.Relics.Select(r => r.Id.Entry).ToArray(), tooth_count = player.GetRelic<PaelsTooth>()?.DisplayAmount,
        energy = player.PlayerCombatState?.Energy, turn = player.PlayerCombatState?.TurnNumber,
        history_plays = CombatManager.Instance.History.CardPlaysFinished.Count(),
        pending = AncientInspection.Busy, previews = RunUi.CardPreviewsPending(),
        option_keys = AncientInspection.Current?.Layout.OptionButtons.Select(b => b.Option.TextKey).ToArray()
    };
}
