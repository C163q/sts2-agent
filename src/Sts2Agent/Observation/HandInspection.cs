using MegaCrit.Sts2.Core.Nodes.Cards;

namespace Sts2Agent;

internal sealed class HandInspection(CombatObservation observation)
{
    public Dictionary<string, object?> Card(NCard card) => CardPresentation.Read(card, observation, full: true);
}
