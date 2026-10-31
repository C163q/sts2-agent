using System.Reflection;
using System.Runtime.CompilerServices;
using System.Text.RegularExpressions;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;

namespace Sts2Agent;

internal static class EnglishEventText
{
    private sealed record Source(LocString Text, bool Raw = false, string Suffix = "");
    private sealed record Rendered(string Value, Source Source);
    private sealed record TipSources(Source? Title, Source? Description);
    private static readonly ConditionalWeakTable<StringVar, Source> VariablesByReference = new();
    private static readonly ConditionalWeakTable<LocString, Dictionary<string, Source>> LiteralVariables = new();
    // Native struct copies retain this ID object; keep provenance as long as the tip survives.
    private static readonly ConditionalWeakTable<string, TipSources> Tips = new();
    private static readonly MethodInfo Clone = typeof(object).GetMethod("MemberwiseClone", BindingFlags.Instance | BindingFlags.NonPublic)!;
    [ThreadStatic] private static Rendered? last;
    [ThreadStatic] private static bool active;
    [ThreadStatic] private static bool snapshotting;
    [ThreadStatic] private static HashSet<Source>? translating;

    private static bool Capturing => !EnglishCardText.Active && !snapshotting && NGame.IsMainThread();

    public static void Initialize()
    {
        var harmony = new Harmony("sts2_agent.event_english");
        void Patch(MethodBase method, string postfix, string? prefix = null) => harmony.Patch(method,
            prefix: prefix == null ? null : new HarmonyMethod(typeof(EnglishEventText), prefix),
            postfix: new HarmonyMethod(typeof(EnglishEventText), postfix));
        Patch(AccessTools.Method(typeof(LocString), nameof(LocString.GetFormattedText)), nameof(Formatted));
        Patch(AccessTools.Method(typeof(LocString), nameof(LocString.GetRawText)), nameof(Raw));
        Patch(AccessTools.Method(typeof(LocString), nameof(LocString.AddObj)), nameof(Added));
        Patch(AccessTools.Method(typeof(LocString), nameof(LocString.AddVariablesFrom)), nameof(CopiedLiterals));
        Patch(AccessTools.PropertySetter(typeof(StringVar), nameof(StringVar.StringValue)), nameof(Assigned));
        Patch(AccessTools.PropertyGetter(typeof(StringVar), nameof(StringVar.StringValue)), nameof(ReadVariable));
        Patch(AccessTools.Method(typeof(DynamicVar), nameof(DynamicVar.Clone)), nameof(ClonedVariable));
        Patch(AccessTools.PropertyGetter(typeof(CardModel), nameof(CardModel.Title)), nameof(CardTitle));
        foreach (var signature in new[] {
            new[] { typeof(LocString), typeof(Texture2D) },
            new[] { typeof(LocString), typeof(LocString), typeof(Texture2D) },
            new[] { typeof(LocString), typeof(string), typeof(Texture2D) },
            new[] { typeof(AfflictionModel), typeof(LocString) },
            new[] { typeof(OrbModel), typeof(LocString) },
            new[] { typeof(PowerModel), typeof(string), typeof(bool) } })
            Patch(AccessTools.Constructor(typeof(HoverTip), signature), nameof(TipConstructed), nameof(BeforeTip));
    }

    private static Source Snapshot(LocString text, bool raw = false, string suffix = "")
    {
        bool previous = snapshotting;
        try
        {
            snapshotting = true;
            var detached = new LocString(text.LocTable, text.LocEntryKey);
            foreach (var (key, value) in text.Variables)
            {
                object copy = value is DynamicVar variable ? Clone.Invoke(variable, null)! : value;
                if (value is StringVar original && copy is StringVar cloned) CopyVariable(original, cloned);
                detached.AddObj(key, copy);
            }
            if (LiteralVariables.TryGetValue(text, out var literals))
                LiteralVariables.Add(detached, new(literals));
            return new(detached, raw, suffix);
        }
        finally { snapshotting = previous; }
    }

    // Attach provenance at assignment, before another text with the same translation can replace it.
    private static Source? ImmediateSource(string value) => last is { } rendered && rendered.Value == value ? rendered.Source : null;
    private static void Formatted(LocString __instance, string __result)
    {
        if (Capturing) last = new(__result, Snapshot(__instance));
    }
    private static void Raw(LocString __instance, string __result)
    {
        if (Capturing) last = new(__result, Snapshot(__instance, raw: true));
    }

    private static void Assigned(StringVar __instance, string __0)
    {
        if (!Capturing) return;
        VariablesByReference.Remove(__instance);
        if (ImmediateSource(__0) is { } source) VariablesByReference.Add(__instance, source);
    }

    private static void ReadVariable(StringVar __instance, string __result)
    {
        if (Capturing) last = VariablesByReference.TryGetValue(__instance, out var source) ? new(__result, source) : null;
    }

    private static void CopyVariable(StringVar original, StringVar copy)
    {
        if (VariablesByReference.TryGetValue(original, out var source))
        {
            VariablesByReference.Remove(copy);
            VariablesByReference.Add(copy, source);
        }
    }

    private static void ClonedVariable(DynamicVar __instance, DynamicVar __result)
    {
        if (Capturing && __instance is StringVar original && __result is StringVar copy) CopyVariable(original, copy);
    }

    private static void Added(LocString __instance, string __0, object __1)
    {
        if (!Capturing) return;
        var values = LiteralVariables.GetValue(__instance, _ => []);
        string key = __0.Replace(' ', '-');
        values.Remove(key);
        if (__1 is string literal && ImmediateSource(literal) is { } source) values[key] = source;
    }

    private static void CopiedLiterals(LocString __instance, LocString __0)
    {
        if (Capturing && LiteralVariables.TryGetValue(__0, out var original))
        {
            var target = LiteralVariables.GetValue(__instance, _ => []);
            foreach (var (key, source) in original) target[key] = source;
        }
    }

    private static void CardTitle(CardModel __instance, string __result)
    {
        if (Capturing) last = new(__result, Snapshot(__instance.TitleLocString,
            suffix: Regex.Match(__result, @"\+\d*$").Value));
    }

    private static void BeforeTip(out Rendered? __state) => __state = Capturing ? last : null;

    private static void TipConstructed(ref HoverTip __instance, object[] __args, Rendered? __state)
    {
        if (!Capturing) return;
        Source? title = __instance.Title == null ? null : __args[0] switch {
            LocString titleText => Snapshot(titleText), AfflictionModel affliction => Snapshot(affliction.Title),
            OrbModel orb => Snapshot(orb.Title), PowerModel power => Snapshot(power.Title), _ => null };
        Source? description = __args[0] is LocString first && __args.Length == 2 ? Snapshot(first)
            : __args[1] is LocString text ? Snapshot(text)
            : __state?.Value == __instance.Description ? __state.Source : null;
        Tips.Remove(__instance.Id);
        Tips.Add(__instance.Id, new(title, description));
    }

    public static T Read<T>(Func<T> read)
    {
        bool previous = active;
        try { active = true; return EnglishCardText.Read(read); }
        finally { active = previous; }
    }

    public static IReadOnlyDictionary<string, object> Variables(LocString text, IReadOnlyDictionary<string, object> original)
    {
        if (!active) return original;
        var result = new Dictionary<string, object>(original);
        LiteralVariables.TryGetValue(text, out var literals);
        foreach (var (key, value) in original)
            if (value is StringVar variable && VariablesByReference.TryGetValue(variable, out var source))
                result[key] = new StringVar(variable.Name, Render(source));
            else if (value is string && literals?.GetValueOrDefault(key) is { } literalSource)
                result[key] = Render(literalSource);
        return result;
    }

    private static string Render(Source source)
    {
        translating ??= [];
        if (!translating.Add(source)) throw new InvalidOperationException("Cyclic localized event variable.");
        try { return (source.Raw ? source.Text.GetRawText() : source.Text.GetFormattedText()) + source.Suffix; }
        finally { translating.Remove(source); }
    }

    public static HoverTipText Tip(IHoverTip tip)
    {
        if (tip is not HoverTip text) return HoverTipText.From(tip);
        Tips.TryGetValue(text.Id, out var sources);
        return new(text.Title == null ? null : EnglishCardText.Plain(sources?.Title is { } title ? Render(title) : text.Title),
            EnglishCardText.Plain(sources?.Description is { } description ? Render(description) : text.Description));
    }
}
