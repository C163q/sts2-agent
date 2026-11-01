using System.Reflection;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models.Monsters;
using MegaCrit.Sts2.Core.MonsterMoves.Intents;
using MegaCrit.Sts2.Core.Nodes.Combat;

namespace Sts2Agent;

internal static class IntentTextChecks
{
    public static async Task<object> CaptureGasBomb(Func<Task> frame)
    {
        const BindingFlags hidden = BindingFlags.Instance | BindingFlags.NonPublic;
        var node = CombatObservation.EnemyNodes().Single(node => node.Entity.Monster is GasBomb);
        var intent = node.IntentContainer.GetChildren().OfType<NIntent>().Single();
        var model = (AbstractIntent)typeof(NIntent).GetField("_intent", hidden)!.GetValue(intent)!;
        var targets = (IEnumerable<Creature>)typeof(NIntent).GetField("_targets", hidden)!.GetValue(intent)!;
        string language = LocManager.Instance.Language;
        var directory = Directory.GetParent(Environment.GetEnvironmentVariable("STS2_AGENT_IPC_DIR")!)!.FullName;
        List<object> results = [];
        try
        {
            foreach (string locale in new[] { "zhs", "eng" })
            {
                LocManager.Instance.SetLanguage(locale);
                typeof(NIntent).GetMethod("OnHovered", hidden)!.Invoke(intent, null);
                try
                {
                    for (int i = 0; i < 15; i++) await frame();
                    string path = Path.Combine(directory, $"native-gas-bomb-{locale}.png");
                    TestCapture.Save(path);
                    results.Add(new { locale, path, intent = CombatObservation.Intent(intent),
                        tip = HoverTipText.From(model.GetHoverTip(targets, node.Entity)) });
                }
                finally { typeof(NIntent).GetMethod("OnUnhovered", hidden)!.Invoke(intent, null); }
            }
        }
        finally { LocManager.Instance.SetLanguage(language); }
        return new { results };
    }
}
