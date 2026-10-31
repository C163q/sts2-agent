using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Saves;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Timeline;
using MegaCrit.Sts2.Core.Timeline.Epochs;

namespace Sts2Agent;

internal static class EndingFixture
{
    public static async Task Configure(string scenario, Player player, Func<Task> frame)
    {
        SaveManager.Instance.Progress.GetOrCreateCharacterStats(player.Character.Id);
        if (scenario == "victory_unlock")
        {
            SaveManager.Instance.Progress.CurrentScore = 190;
            string neow = EpochModel.GetId<NeowEpoch>();
            SaveManager.Instance.Progress.ObtainEpochOverride(neow, EpochState.ObtainedNoSlot);
            player.DiscoveredEpochs.Add(neow);
            foreach (string id in new[] { EpochModel.GetId<Ironclad2Epoch>(), EpochModel.GetId<Ironclad3Epoch>() })
            {
                SaveManager.Instance.Progress.ObtainEpochOverride(id, EpochState.ObtainedNoSlot);
                player.DiscoveredEpochs.Add(id);
            }
        }
        else
        {
            SaveManager.Instance.Progress.CurrentScore = 0;
            foreach (var epoch in SaveManager.Instance.Progress.Epochs.ToArray())
                SaveManager.Instance.Progress.ObtainEpochOverride(epoch.Id, EpochState.Revealed);
        }
        if (scenario.StartsWith("victory"))
        {
            var cards = ModelDb.AllCards.Take(12).ToArray();
            player.DiscoveredCards.Clear();
            player.DiscoveredCards.AddRange(cards.Select(c => c.Id));
            await NavigationFixture.Configure("boss3", player, frame);
        }
        else if (scenario == "event_death") await EventFixture.Configure("death", player, frame);
        else
        {
            await CreatureCmd.Kill(player.Creature, force: true);
            var result = new RunResultInspection();
            for (int i = 0; i < 900 && !(result.Current is { } current && result.Ready(current)); i++) await frame();
        }
    }
}
