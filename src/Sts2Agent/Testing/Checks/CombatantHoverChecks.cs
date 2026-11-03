using Godot;
using MegaCrit.Sts2.Core.Nodes.Combat;

namespace Sts2Agent;

internal static class CombatantHoverChecks
{
    private static NIntent? intent;
    private static Control.MouseFilterEnum previous;

    public static object SetEnabled(bool enabled)
    {
        if (GodotObject.IsInstanceValid(intent)) intent!.MouseFilter = previous;
        intent = null;
        if (enabled) return new { enabled, source = (string?)null };
        var nodes = CombatObservation.EnemyNodes().ToArray();
        for (int i = 0; i < nodes.Length; i++)
        {
            var candidates = nodes[i].IntentContainer.GetChildren().OfType<NIntent>().Where(item =>
                VisibleUi.Displayed(item.GetNodeOrNull<Control>("%IntentHolder"))
                && VisibleUi.Displayed(item.GetNodeOrNull<Sprite2D>("%Intent"))).ToArray();
            if (candidates.Length == 0) continue;
            intent = candidates[0];
            previous = intent.MouseFilter;
            intent.MouseFilter = Control.MouseFilterEnum.Ignore;
            return new { enabled, source = $"enemies.{i}.intents.0" };
        }
        throw new InvalidOperationException("The test battlefield has no displayed intent.");
    }
}
