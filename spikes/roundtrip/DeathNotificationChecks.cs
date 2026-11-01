using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Powers;

namespace Sts2Agent;

internal static class DeathNotificationChecks
{
    public static async Task<object> Run(Player player, Func<CardModel, int> cardId)
    {
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        var target = combat.Enemies.First();
        var checks = new List<object>();
        var samples = new List<object>();
        bool passed = true;
        void Check(string name, bool ok) { checks.Add(new { name, passed = ok }); passed &= ok; }
        using (var action = new ActionEventScope())
        using (var journal = new TurnJournal(combat, player, cardId))
        {
            await CreatureCmd.Kill(target);
            target.InvokeDiedEvent();
            Check("repeated native death notification records one death", action.Buffer.Events.Count(e => (string)e["type"]! == "died") == 1);
            await target.GetPower<ReattachPower>()!.DoReattach();
            Check("native reattachment restores a living target", target.IsAlive);
            await CreatureCmd.Kill(target);
            target.InvokeDiedEvent();
            var life = action.Buffer.Events.Select(e => (string)e["type"]!).Where(type => type is "died" or "revived").ToArray();
            Check("revival allows a second death in the same journal", life.SequenceEqual(new[] { "died", "revived", "died" }));
            samples.Add(action.Buffer.Events);
        }
        using (var action = new ActionEventScope())
        using (var journal = new TurnJournal(combat, player, cardId))
        {
            target.InvokeDiedEvent();
            Check("a fresh journal does not kill an existing corpse again", !action.Buffer.Events.Any(e => (string)e["type"]! == "died"));
            samples.Add(action.Buffer.Events);
        }
        Check("journals release their capture subscription", TurnCapture.Journal == null);
        return new { passed, checks, samples };
    }
}
