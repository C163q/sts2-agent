using System.Reflection;

namespace Sts2Agent;

internal static class PrivateFields
{
    private static FieldInfo? Find(Type type, string name)
    {
        for (Type? current = type; current != null; current = current.BaseType)
            if (current.GetField(name, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly) is { } field)
                return field;
        return null;
    }

    public static object? Read(object instance, string name) =>
        (Find(instance.GetType(), name) ?? throw new MissingFieldException(instance.GetType().FullName, name)).GetValue(instance);

    // Only for polymorphic UI families where some supported types intentionally lack this field.
    public static object? Optional(object instance, string name) => Find(instance.GetType(), name)?.GetValue(instance);
}
