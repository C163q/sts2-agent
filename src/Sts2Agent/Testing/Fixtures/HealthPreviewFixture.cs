using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace Sts2Agent;

internal static class HealthPreviewFixture
{
    private static Action? restore;

    public static async Task<object> Set(string mode, Player player, Func<Task> frame)
    {
        string[] modes = ["normal", "poison", "poison_lethal", "doom", "doom_lethal", "combined", "accelerated",
            "hidden_poison", "hidden_doom", "hidden_bar", "hidden_label", "player"];
        if (!modes.Contains(mode)) throw new ArgumentException("Unknown health preview fixture mode.");
        restore?.Invoke(); restore = null;
        var combat = CombatManager.Instance.DebugOnlyGetState()!;
        var enemy = combat.Enemies.First();
        foreach (var creature in new[] { player.Creature, enemy })
        {
            await PowerCmd.Remove<PoisonPower>(creature);
            await PowerCmd.Remove<DoomPower>(creature);
            await PowerCmd.Remove<AccelerantPower>(creature);
        }
        await CreatureCmd.SetMaxHp(enemy, 60);
        await CreatureCmd.SetCurrentHp(enemy, 20);
        await CreatureCmd.SetCurrentHp(player.Creature, player.Creature.MaxHp);
        var target = mode == "player" ? player.Creature : enemy;
        int poison = mode is "normal" or "doom" or "doom_lethal" ? 0 : mode == "poison_lethal" ? 30 : 7;
        int doom = mode is "combined" or "hidden_poison" or "hidden_doom" or "hidden_bar" or "hidden_label" ? 15
            : mode == "doom" ? 10 : mode == "doom_lethal" ? 20 : 0;
        var choices = new ThrowingPlayerChoiceContext();
        if (mode == "accelerated") await PowerCmd.Apply<AccelerantPower>(choices, player.Creature, 2, player.Creature, null);
        if (poison > 0) await PowerCmd.Apply<PoisonPower>(choices, target, poison, player.Creature, null);
        if (doom > 0) await PowerCmd.Apply<DoomPower>(choices, target, doom, player.Creature, null);
        for (int i = 0; i < 4; i++) await frame();
        if (mode.StartsWith("hidden_"))
        {
            var node = NCombatRoom.Instance!.GetCreatureNode(enemy)!;
            var bar = node.GetNode<NCreatureStateDisplay>("%HealthBar").GetNode<NHealthBar>("%HealthBar");
            Control hidden = mode switch {
                "hidden_poison" => bar.GetNode<Control>("%PoisonForeground"),
                "hidden_doom" => bar.GetNode<Control>("%DoomForeground"),
                "hidden_label" => bar.GetNode<Control>("%HpLabel"),
                _ => bar };
            bool visible = hidden.Visible;
            restore = () => { if (GodotObject.IsInstanceValid(hidden)) hidden.Visible = visible; };
            hidden.Visible = false;
            await frame();
        }
        return new { mode, target_id = target.CombatId };
    }
}
