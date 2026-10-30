using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Combat.History.Entries;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.UI;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Rooms;
using STS2RitsuLib;

namespace Sts2Agent;

internal sealed class TurnJournal : IDisposable, ILifecycleObserver
{
    private readonly CombatState combat;
    private readonly Player player;
    private readonly Func<CardModel, int> cardId;
    private readonly EnglishText english = new();
    private readonly TurnEventBuffer buffer = new();
    private readonly List<Action> cleanup = [];
    private readonly HashSet<Creature> subscribed = [];
    private readonly Dictionary<Creature, object> identities = [];
    private readonly Dictionary<PowerModel, int?> powerAmounts = [];
    private readonly HashSet<PowerModel> watchedPowers = [];
    private readonly Dictionary<CardModel, object?> autoSources = [];
    private readonly List<(DamageResult result, Dictionary<string, object?> entry)> damageResults = [];
    private readonly HashSet<CardModel> generated = [];
    private readonly HashSet<CardModel> handCards = [];
    private readonly Dictionary<CardModel, string?> knownCards = [];
    private readonly IDisposable? lifecycle;
    private bool ended, won, disposed;
    private int historyCursor;
    public bool SawTurnStart { get; private set; }
    public int LifecycleEvents { get; private set; }

    public TurnJournal(CombatState combat, Player player, Func<CardModel, int> cardId)
    {
        this.combat = combat;
        this.player = player;
        this.cardId = cardId;
        if (TurnCapture.Journal != null) throw new InvalidOperationException("A turn is already being recorded.");
        try
        {
            TurnCapture.Journal = this;
            CombatManager.Instance.CombatWon += Won;
            CombatManager.Instance.CombatEnded += Ended;
            CombatManager.Instance.TurnStarted += Started;
            combat.CreaturesChanged += CreaturesChanged;
            lifecycle = RitsuLibFramework.SubscribeLifecycle(this, replayCurrentState: false);
            historyCursor = CombatManager.Instance.History.Entries.Count();
            CombatManager.Instance.History.Changed += HistoryChanged;
            SubscribeCreatures();
            // Selected cards leave the hand holders but remain visible when confirmation starts a new journal.
            foreach (var node in VisibleUi.Descendants<NCard>(NCombatRoom.Instance!.Ui))
                if (node.Model is { } card && node.Visibility == ModelVisibility.Visible
                    && CombatObservation.CardVisible(node) && english.CardName(node) is { } name)
                    knownCards[card] = name;
            SubscribePiles();
            var potions = new PotionJournal(player, (type, potion) => buffer.Add(type, new() { ["potion"] = potion }));
            cleanup.Add(potions.Dispose);
        }
        catch
        {
            Dispose();
            throw;
        }
    }

    public string? StopReason(bool sameCombat, bool playerReady, bool requireTurnStarted = true)
    {
        foreach (var creature in combat.Creatures) RememberVisible(creature);
        CapturePublicCards();
        bool choiceReady = CardSelection.AwaitingInput;
        return TurnBoundary.Decide(sameCombat, ended, choiceReady, playerReady && (!requireTurnStarted || SawTurnStart), won);
    }

    public object Result(string reason)
    {
        foreach (var (result, entry) in damageResults) entry["blocked"] = result.BlockedDamage;
        return new { stop_reason = reason, complete = !buffer.Truncated && reason is not ("timeout" or "interrupted"),
            events = buffer.Events };
    }

    private void Won(CombatRoom room) { if (ReferenceEquals(room.CombatState, combat)) won = true; }
    private void Ended(CombatRoom room) { if (ReferenceEquals(room.CombatState, combat)) ended = true; }
    private void Started(CombatState state)
    {
        if (ReferenceEquals(state, combat) && state.CurrentSide == CombatSide.Player) SawTurnStart = true;
    }
    private void CreaturesChanged(ICombatState state) => SubscribeCreatures();

    private void RememberVisible(Creature creature)
    {
        if (identities.ContainsKey(creature)) return;
        var node = NCombatRoom.Instance?.GetCreatureNode(creature);
        if (!VisibleUi.Shown(node) || !VisibleUi.OnScreen(node!.Body)) return;
        identities[creature] = new { id = (int)(creature.CombatId ?? 0),
            kind = creature.IsPlayer ? "player" : creature.IsEnemy ? "enemy" : "ally",
            name = creature.IsPlayer ? english.Name(creature.Player!.Character.Title) : english.Name(creature.Monster!.Title) };
    }

    private object? Entity(Creature? creature)
    {
        if (creature == null) return null;
        RememberVisible(creature);
        return identities.GetValueOrDefault(creature);
    }

    private object? Source(AbstractModel? model) => model switch
    {
        CardModel card => new { kind = "card", name = CardName(card) },
        PowerModel power when power.IsVisible => new { kind = "power", name = english.Name(power.Title) },
        RelicModel relic => new { kind = "relic", name = english.Name(relic.Title) },
        PotionModel potion => new { kind = "potion", name = english.Name(potion.Title) },
        _ => null
    };

    private Dictionary<string, object?>? Add(string type, Creature target, Dictionary<string, object?>? fields = null)
    {
        if (Entity(target) is not { } identity) return null;
        fields ??= [];
        fields["target"] = identity;
        return buffer.Add(type, fields);
    }

    private void SubscribeCreatures()
    {
        foreach (var creature in combat.Creatures.ToArray())
        {
            if (!subscribed.Add(creature)) continue;
            RememberVisible(creature);
            foreach (var power in creature.Powers)
            {
                powerAmounts[power] = DisplayAmount(power);
                WatchPower(power);
            }
            void Hp(int before, int after)
            {
                if (!TurnCapture.CapturingDamageHp && CombatObservation.HealthNumbersVisible(creature))
                    Add("hp_changed", creature, new() { ["before"] = before, ["after"] = after,
                        ["source"] = Source(TurnCapture.Current?.Model) });
            }
            void Block(int before, int after)
            {
                if (before != after && !(TurnCapture.Current?.IsDamage == true && after < before))
                    Add("block_changed", creature, new() { ["before"] = before, ["after"] = after });
            }
            void Power(PowerModel power)
            {
                bool existed = powerAmounts.TryGetValue(power, out int? before);
                bool present = creature.Powers.Contains(power);
                int? after = present ? DisplayAmount(power) : null;
                if (present) powerAmounts[power] = after;
                else powerAmounts.Remove(power);
                if (power.IsVisible && (before != after || existed != present))
                    Add("power_changed", creature, new() { ["name"] = english.Name(power.Title),
                        ["change"] = !present ? "removed" : existed ? "modified" : "applied",
                        ["before"] = before, ["after"] = after });
            }
            void WatchPower(PowerModel power)
            {
                if (!watchedPowers.Add(power)) return;
                void Changed() => Power(power);
                power.DisplayAmountChanged += Changed;
                cleanup.Add(() => power.DisplayAmountChanged -= Changed);
            }
            void Applied(PowerModel power) { Power(power); WatchPower(power); }
            void Increased(PowerModel power, int _, bool silent) => Power(power);
            void Decreased(PowerModel power, bool silent) => Power(power);
            void Died(Creature target) => Add("died", target, new() { ["source"] = Source(TurnCapture.Current?.Model) });
            void Revived(Creature target) => Add("revived", target);
            creature.CurrentHpChanged += Hp;
            creature.BlockChanged += Block;
            creature.PowerApplied += Applied;
            creature.PowerIncreased += Increased;
            creature.PowerDecreased += Decreased;
            creature.PowerRemoved += Power;
            creature.Died += Died;
            creature.Revived += Revived;
            cleanup.Add(() =>
            {
                creature.CurrentHpChanged -= Hp;
                creature.BlockChanged -= Block;
                creature.PowerApplied -= Applied;
                creature.PowerIncreased -= Increased;
                creature.PowerDecreased -= Decreased;
                creature.PowerRemoved -= Power;
                creature.Died -= Died;
                creature.Revived -= Revived;
            });
        }
    }

    public void AutoPlaySource(CardModel card, AbstractModel? source) => autoSources[card] = Source(source);
    private static int? DisplayAmount(PowerModel power) => power.StackType == PowerStackType.Counter ? power.DisplayAmount : null;

    private string? CardName(CardModel card)
    {
        var node = NCard.FindOnTable(card);
        if (CombatObservation.CardVisible(node) && node!.Visibility == ModelVisibility.Visible
            && english.CardName(node) is { } name)
            knownCards[card] = name;
        return knownCards.GetValueOrDefault(card);
    }

    private void CapturePublicCards()
    {
        var ui = NCombatRoom.Instance?.Ui;
        if (ui == null) return;
        foreach (var node in VisibleUi.Descendants<NCard>(ui))
        {
            if (node.Model is not { } card || !generated.Contains(card)
                || node.Visibility != ModelVisibility.Visible || !CombatObservation.CardVisible(node)
                || english.CardName(node) is not { } name) continue;
            knownCards[card] = name;
            Card("card_added", card);
            generated.Remove(card);
        }
    }

    public void Damage(DamageResult result, TurnCapture.Origin origin)
    {
        var fields = new Dictionary<string, object?> { ["hp_loss"] = CombatObservation.HealthNumbersVisible(result.Receiver)
                ? result.UnblockedDamage : (int?)null,
            ["blocked"] = result.BlockedDamage, ["source"] = Source(origin.Model) };
        if (Entity(origin.Dealer) is { } actor) fields["actor"] = actor;
        var entry = Add("damage", result.Receiver, fields);
        if (entry != null) damageResults.Add((result, entry));
    }

    private void HistoryChanged()
    {
        var entries = CombatManager.Instance.History.Entries.ToArray();
        if (historyCursor > entries.Length) historyCursor = 0;
        while (historyCursor < entries.Length)
        {
            var entry = entries[historyCursor++];
            if (entry is CardDrawnEntry draw) Card("card_drawn", draw.Card);
        }
    }

    private void SubscribePiles()
    {
        foreach (var card in player.PlayerCombatState!.Hand.Cards) handCards.Add(card);
        foreach (var type in new[] { PileType.Hand, PileType.Play, PileType.Draw, PileType.Discard, PileType.Exhaust })
        {
            var pile = type.GetPile(player);
            void Added(CardModel card)
            {
                bool wasHand = handCards.Remove(card);
                if (type == PileType.Hand) handCards.Add(card);
                else if (type == PileType.Exhaust) Card("card_exhausted", card);
                else if (type == PileType.Discard && wasHand) Card("card_discarded", card);
            }
            pile.CardAdded += Added;
            cleanup.Add(() => pile.CardAdded -= Added);
        }
    }

    private void Card(string type, CardModel card, bool? autoplay = null, Creature? target = null)
    {
        if (!ReferenceEquals(card.Owner, player)) return;
        var fields = new Dictionary<string, object?> { ["card"] = new { id = cardId(card), name = CardName(card) } };
        if (autoplay.HasValue)
        {
            fields["autoplay"] = autoplay.Value;
            fields["source"] = autoSources.GetValueOrDefault(card);
        }
        if (Entity(target) is { } identity) fields["target"] = identity;
        buffer.Add(type, fields);
    }

    public void OnEvent(IFrameworkLifecycleEvent evt)
    {
        if (disposed) return;
        switch (evt)
        {
            case CardPlayingEvent e when ReferenceEquals(e.CombatState, combat):
                LifecycleEvents++;
                Card("card_played", e.CardPlay.Card, e.CardPlay.IsAutoPlay, e.CardPlay.Target);
                break;
            case CardDrawnEvent e when ReferenceEquals(e.CombatState, combat):
                LifecycleEvents++;
                break;
            case CardDiscardedEvent e when ReferenceEquals(e.CombatState, combat):
                LifecycleEvents++;
                break;
            case CardExhaustedEvent e when ReferenceEquals(e.CombatState, combat):
                LifecycleEvents++;
                break;
            case CardsFlushedEvent e when ReferenceEquals(e.CombatState, combat):
                LifecycleEvents++;
                break;
            case CardGeneratedForCombatEvent e when ReferenceEquals(e.CombatState, combat):
                generated.Add(e.Card);
                break;
            case CreatureAddedToCombatEvent e when ReferenceEquals(e.CombatState, combat):
                SubscribeCreatures();
                Add("creature_added", e.Creature);
                break;
        }
    }

    public void Dispose()
    {
        if (disposed) return;
        disposed = true;
        TurnCapture.Journal = null;
        lifecycle?.Dispose();
        CombatManager.Instance.CombatWon -= Won;
        CombatManager.Instance.CombatEnded -= Ended;
        CombatManager.Instance.TurnStarted -= Started;
        CombatManager.Instance.History.Changed -= HistoryChanged;
        combat.CreaturesChanged -= CreaturesChanged;
        foreach (var unsubscribe in cleanup) unsubscribe();
    }
}
