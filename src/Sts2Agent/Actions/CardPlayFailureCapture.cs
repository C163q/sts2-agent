using System.Reflection;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using HarmonyLib;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Agent;

internal static class CardPlayFailureCapture
{
    private static readonly MethodInfo NativeCheck = AccessTools.Method(typeof(CardModel), nameof(CardModel.CanPlay),
        [typeof(UnplayableReason).MakeByRefType(), typeof(AbstractModel).MakeByRefType()]);
    public static event Action<PlayCardAction, string>? Rejected;

    public static void Initialize()
    {
        var execute = AccessTools.Method(typeof(PlayCardAction), "ExecuteAction");
        var state = execute.GetCustomAttribute<AsyncStateMachineAttribute>()!.StateMachineType;
        new Harmony("sts2_agent.card_play_failure").Patch(AccessTools.Method(state, "MoveNext"),
            transpiler: new HarmonyMethod(typeof(CardPlayFailureCapture), nameof(CaptureCheck)));
    }

    private static IEnumerable<CodeInstruction> CaptureCheck(IEnumerable<CodeInstruction> instructions)
    {
        var body = instructions.ToArray();
        var checks = body.Where(instruction => instruction.Calls(NativeCheck)).ToArray();
        if (checks.Length != 1) throw new InvalidOperationException("Native card execution check changed.");
        checks[0].opcode = OpCodes.Call;
        checks[0].operand = AccessTools.Method(typeof(CardPlayFailureCapture), nameof(Check));
        return body;
    }

    private static bool Check(CardModel card, out UnplayableReason reason, out AbstractModel? preventer)
    {
        bool playable = card.CanPlay(out reason, out preventer);
        if (!playable && RunManager.Instance.ActionExecutor.CurrentlyRunningAction is PlayCardAction action
            && ReferenceEquals(action.NetCombatCard.ToCardModelOrNull(), card))
            Rejected?.Invoke(action, CardPlayFailureText.Read(reason, preventer));
        return playable;
    }
}
