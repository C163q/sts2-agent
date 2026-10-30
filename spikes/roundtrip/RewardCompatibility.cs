using Godot;
using MegaCrit.Sts2.Core.Nodes.Rewards;

namespace Sts2Agent;

internal static class RewardCompatibility
{
    public static void AdaptLinkedClaim(NRewardButton button)
    {
        if (button.Reward?.ParentRewardSet == null) return;
        foreach (var connection in button.GetSignalConnectionList(NRewardButton.SignalName.RewardClaimed))
        {
            var callback = connection["callable"].AsCallable();
            if (callback.Delegate is not Action native || native.Target is not NLinkedRewardSet parent
                || !ReferenceEquals(parent.LinkedRewardSet, button.Reward.ParentRewardSet)
                || native.Method.Name != "GetReward") continue;
            // v0.107.1 connects a zero-argument delegate to RewardClaimed(NRewardButton).
            // Preserve the native collector and drop only its unused signal argument.
            button.Disconnect(NRewardButton.SignalName.RewardClaimed, callback);
            button.Connect(NRewardButton.SignalName.RewardClaimed, Callable.From<NRewardButton>(_ => native()),
                connection["flags"].AsUInt32());
        }
    }
}
