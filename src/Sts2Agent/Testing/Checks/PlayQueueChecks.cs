using System.Text.Json;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Actions;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class PlayQueueChecks
{
    public static readonly string[] Modes = ["ordered", "energy", "stars", "target", "random_exhaust",
        "hand_exhaust", "automatic_hand", "choose_one", "combat_pile", "victory", "death", "immediate_death",
        "bullet_time", "survivor_manual", "survivor_auto", "dagger_manual", "dagger_auto"];

    public static async Task<object> Run(string mode, Player player, CombatObservation observation,
        Func<Task> frame, Func<string> observe)
    {
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        await CardPileCmd.RemoveFromCombat(player.PlayerCombatState!.AllCards.ToArray());
        await PlayerCmd.SetEnergy(mode is "energy" or "bullet_time" ? 3 : 20, player);
        await PlayerCmd.SetStars(3, player);
        var cards = new List<CardModel>();
        CardModel Add<T>() where T : CardModel { var card = combat.CreateCard<T>(player); cards.Add(card); return card; }
        switch (mode)
        {
            case "bullet_time": Add<BulletTime>(); Add<StrikeIronclad>(); Add<StrikeIronclad>();
                Add<StrikeIronclad>(); Add<DefendIronclad>(); break;
            case "survivor_manual": Add<Survivor>(); Add<DefendIronclad>(); Add<PiercingWail>(); break;
            case "survivor_auto": Add<Survivor>(); Add<PiercingWail>(); break;
            case "dagger_manual": case "dagger_auto":
                Add<DaggerThrow>();
                if (mode == "dagger_manual") Add<DefendIronclad>();
                await CardPileCmd.AddGeneratedCardToCombat(combat.CreateCard<PiercingWail>(player), PileType.Draw, player);
                break;
            case "energy": Add<StrikeIronclad>(); Add<Bash>(); Add<StrikeIronclad>(); Add<DefendIronclad>().SetToFreeThisTurn(); break;
            case "stars": Add<StrikeIronclad>(); Add<DefendIronclad>().SetStarCostThisCombat(2);
                Add<DefendIronclad>().SetStarCostThisCombat(2); Add<DefendIronclad>(); break;
            case "random_exhaust": Add<TrueGrit>(); Add<DefendIronclad>(); Add<DefendIronclad>(); break;
            case "hand_exhaust": case "automatic_hand":
                var grit = Add<TrueGrit>(); grit.UpgradeInternal(); grit.FinalizeUpgradeInternal();
                Add<DefendIronclad>(); if (mode == "hand_exhaust") Add<DefendIronclad>(); break;
            case "choose_one": Add<StrikeIronclad>(); Add<Discovery>(); Add<DefendIronclad>(); Add<DefendIronclad>(); break;
            case "combat_pile":
                Add<Headbutt>(); Add<DefendIronclad>(); Add<DefendIronclad>();
                await CardPileCmd.AddGeneratedCardsToCombat(new CardModel[] { combat.CreateCard<StrikeIronclad>(player),
                    combat.CreateCard<DefendIronclad>(player) }, PileType.Discard, player); break;
            case "death": Add<StrikeIronclad>(); Add<Offering>(); Add<DefendIronclad>(); Add<DefendIronclad>();
                await CreatureCmd.SetCurrentHp(player.Creature, 1); break;
            case "immediate_death": Add<Offering>(); Add<DefendIronclad>(); Add<DefendIronclad>();
                await CreatureCmd.SetCurrentHp(player.Creature, 1); break;
            case "victory": Add<Thunderclap>(); Add<DefendIronclad>(); Add<DefendIronclad>();
                foreach (var enemy in combat.Enemies) await CreatureCmd.SetCurrentHp(enemy, 1); break;
            case "target": Add<StrikeIronclad>(); Add<StrikeIronclad>(); Add<DefendIronclad>();
                await CreatureCmd.SetCurrentHp(combat.Enemies.First(), 1); break;
            default: Add<StrikeIronclad>(); Add<DefendIronclad>(); Add<DefendIronclad>(); break;
        }
        await CardPileCmd.AddGeneratedCardsToCombat(cards, PileType.Hand, player);
        async Task Wait(Func<bool> done)
        {
            var deadline = DateTime.UtcNow.AddSeconds(18);
            do { await frame(); } while (!done() && DateTime.UtcNow < deadline);
            if (!done()) throw new TimeoutException("The native play queue probe did not reach its boundary.");
        }
        await Wait(() => NCombatRoom.Instance!.Ui.Hand.ActiveHolders.Count() == cards.Count);
        for (int i = 0; i < 25; i++) await frame();
        var before = JsonSerializer.Deserialize<JsonElement>(observe());
        var ids = cards.Select(observation.CardId).ToArray();
        var actions = new List<PlayCardAction>();
        var lifecycle = new List<object>();
        void Enqueued(GameAction action)
        {
            if (action is not PlayCardAction play || play.Player != player) return;
            actions.Add(play);
            int index = cards.IndexOf(play.NetCombatCard.ToCardModelOrNull()!);
            play.BeforeExecuted += _ => lifecycle.Add(new { index, stage = "executing" });
            play.BeforeCancelled += _ => lifecycle.Add(new { index, stage = "canceled" });
            play.AfterFinished += _ => lifecycle.Add(new { index, stage = "finished" });
        }
        using var scope = new ActionEventScope();
        using var journal = new TurnJournal(combat, player, observation.CardId,
            observation.KnownCardName, observation.RememberCardName);
        var queue = RunManager.Instance.ActionQueueSet;
        queue.ActionEnqueued += Enqueued;
        var submissions = new List<object>();
        JsonElement? choosing = null;
        object? paused = null;
        try
        {
            Creature target = combat.Enemies.First();
            for (int i = 0; i < cards.Count; i++)
            {
                string? previousState = actions.FirstOrDefault()?.State.ToString();
                bool accepted = cards[i].TryManualPlay(TargetInspection.RequiresTarget(cards[i]) ? target : null);
                submissions.Add(new { index = i, card_id = ids[i], accepted, previous_first_state = previousState });
            }
            bool choiceMode = mode is "hand_exhaust" or "choose_one" or "combat_pile" or "survivor_manual" or "dagger_manual";
            if (choiceMode)
            {
                await Wait(() => CardSelection.AwaitingInput);
                choosing = JsonSerializer.Deserialize<JsonElement>(observe());
                paused = actions.Select(a => new { card_id = observation.CardId(a.NetCombatCard.ToCardModel()),
                    state = a.State.ToString() }).ToArray();
                var selection = CardSelection.Current!;
                var candidate = mode == "hand_exhaust" ? cards[1] : selection.Cards.First();
                await SelectionActions.Click(selection, candidate, frame);
                await frame();
                if (CardSelection.Current is { } pending && SelectionActions.Same(selection))
                    foreach (var option in pending.Options().Where(o => o.id == "confirm" && o.button.IsEnabled))
                        option.button.ForceClick();
            }
            await Wait(() => queue.IsEmpty);
            for (int i = 0; i < 75; i++) await frame();
            var events = scope.Buffer.Events.ToArray();
            bool Played(int index) => events.Any(e => (string)e["type"]! == "card_played"
                && JsonSerializer.SerializeToElement(e["card"]).GetProperty("id").GetInt32() == ids[index]);
            bool WasCanceled(int index) => lifecycle.Any(e =>
                JsonSerializer.SerializeToElement(e).GetProperty("index").GetInt32() == index
                && JsonSerializer.SerializeToElement(e).GetProperty("stage").GetString() == "canceled");
            bool acceptedAll = submissions.All(s => JsonSerializer.SerializeToElement(s).GetProperty("accepted").GetBoolean());
            bool queuedBeforeChoiceOrCompletion = mode == "immediate_death" || submissions.Skip(1).All(s =>
                JsonSerializer.SerializeToElement(s).GetProperty("previous_first_state").GetString() == "Executing");
            bool outcome = mode switch
            {
                "bullet_time" => Played(0) && !Enumerable.Range(1, 4).Any(Played)
                    && submissions.Skip(1).All(s => !JsonSerializer.SerializeToElement(s).GetProperty("accepted").GetBoolean()),
                "survivor_manual" => Played(0) && !Played(1) && !Played(2) && WasCanceled(1) && WasCanceled(2),
                "dagger_manual" => Played(0) && !Played(1) && WasCanceled(1),
                "survivor_auto" => Played(0) && !Played(1) && WasCanceled(1)
                    && player.PlayerCombatState!.DiscardPile.Cards.Any(c => c is PiercingWail),
                "dagger_auto" => Played(0) && player.PlayerCombatState!.DiscardPile.Cards.Any(c => c is PiercingWail),
                "energy" or "stars" => Played(0) && Played(1) && !Played(2) && WasCanceled(2) && Played(3),
                "target" => Played(0) && !Played(1) && WasCanceled(1) && Played(2),
                "hand_exhaust" => Played(0) && !Played(1) && !Played(2) && WasCanceled(1) && WasCanceled(2),
                "automatic_hand" => Played(0) && !Played(1) && WasCanceled(1),
                "random_exhaust" => Played(0) && (Played(1) != Played(2)) && !WasCanceled(1) && !WasCanceled(2),
                "victory" => Played(0) && !Played(1) && !Played(2) && WasCanceled(1) && WasCanceled(2),
                "death" => Played(0) && Played(1) && !Played(2) && !Played(3) && !player.Creature.IsAlive,
                "immediate_death" => Played(0) && !Played(1) && !Played(2) && !player.Creature.IsAlive,
                _ => Enumerable.Range(0, cards.Count).All(Played)
            };
            bool admission = mode == "bullet_time"
                ? JsonSerializer.SerializeToElement(submissions[0]).GetProperty("accepted").GetBoolean() : acceptedAll;
            return new { passed = admission && outcome && queuedBeforeChoiceOrCompletion, mode, before, submissions, choosing, paused, lifecycle,
                actions = actions.Select((a, i) => new { index = i, state = a.State.ToString(),
                    played = i < cards.Count && Played(i), canceled = i < cards.Count && WasCanceled(i) }).ToArray(),
                events, after = JsonSerializer.Deserialize<JsonElement>(observe()) };
        }
        finally { queue.ActionEnqueued -= Enqueued; }
    }
}
