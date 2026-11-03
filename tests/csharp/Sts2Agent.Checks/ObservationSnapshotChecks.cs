using System.Text.Json;
using Sts2Agent;

internal static class ObservationSnapshotChecks
{
    public static void Run(Action<bool, string> check)
    {
        const string body = "{\"schema_version\":34,\"scene\":\"combat\",\"divination\":{\"status\":\"visible\",\"dialogue\":\"hello\",\"remaining\":3},\"player\":null}";
        var identity = new object();
        var snapshot = ObservationSnapshot.Create(body, false, identity, null, null);
        check(snapshot.Token == "616E7E9BF6B5AFB36BBABCC5741FE174E1405BBF199E022565706DAF1CBC47B8", "snapshot hash preserves the original serialized observation");
        check(snapshot.State.GetProperty("player").ValueKind == JsonValueKind.Null
            && snapshot.State.GetProperty("snapshot_id").GetString() == snapshot.Token
            && ReferenceEquals(snapshot.CombatIdentity, identity), "snapshot binds state token and native identity");
        var masked = ObservationSnapshot.Create(body, true, null, null, null);
        check(masked.Token == "AAD735A5F3939F49A825C1FA7040FDBB5C60FF567AF085E10C336A62FA0B532F", "divination dialogue keeps the original hash exception");
        check(masked.Token == ObservationSnapshot.Create(body.Replace("hello", "changed"), true, null, null, null).Token
            && masked.Token != ObservationSnapshot.Create(body.Replace(":3", ":2"), true, null, null, null).Token,
            "dialogue animation does not stale permissions but reveals do");
        check(masked.State.GetProperty("divination").GetProperty("dialogue").GetString() == "hello",
            "token normalization never rewrites the visible observation");
    }
}
