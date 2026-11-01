using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models.Orbs;

namespace Sts2Agent;

internal static class OrbFixture
{
    public static async Task Configure(Player player)
    {
        var choice = new ThrowingPlayerChoiceContext();
        while (player.PlayerCombatState!.OrbQueue.Orbs.Count > 0)
            await OrbCmd.EvokeNext(choice, player);
        OrbCmd.RemoveSlots(player, player.PlayerCombatState.OrbQueue.Capacity);
        await OrbCmd.AddSlots(player, 5);
        await OrbCmd.Channel<LightningOrb>(choice, player);
        await OrbCmd.Channel<FrostOrb>(choice, player);
        await OrbCmd.Channel<DarkOrb>(choice, player);
        await OrbCmd.Channel<PlasmaOrb>(choice, player);
    }
}
