using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class RunContext
{
    public static Player? LocalPlayer => LocalContext.GetMe(CombatManager.Instance.DebugOnlyGetState())
        ?? LocalContext.GetMe(RunManager.Instance.DebugOnlyGetState());
    public static bool Singleplayer => RunManager.Instance.IsSingleplayerOrFakeMultiplayer
        && RunManager.Instance.DebugOnlyGetState()?.Players.Count == 1;
}
