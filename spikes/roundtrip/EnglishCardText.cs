using System.Globalization;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using HarmonyLib;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using SmartFormat;

namespace Sts2Agent;

internal static class EnglishCardText
{
    private static readonly EnglishText English = new();
    [ThreadStatic] private static bool active;
    [ThreadStatic] private static PowerModel? activePower;

    static EnglishCardText()
    {
        // MonoMod's Linux helper imports unwind symbols without declaring a libgcc dependency.
        if (OperatingSystem.IsLinux() && LoadGlobalLibrary("libgcc_s.so.1", LoadNow | LoadGlobal) == IntPtr.Zero)
            throw new DllNotFoundException("The system exception runtime could not be loaded for card rendering.");
        var harmony = new Harmony("sts2_agent.hand_english");
        harmony.Patch(AccessTools.Method(typeof(LocString), nameof(LocString.GetFormattedText)),
            prefix: new HarmonyMethod(typeof(EnglishCardText), nameof(FormattedText)));
        harmony.Patch(AccessTools.Method(typeof(LocTable), nameof(LocTable.GetRawText)),
            prefix: new HarmonyMethod(typeof(EnglishCardText), nameof(RawText)));
        harmony.Patch(AccessTools.Method(typeof(HoverTipFactory), nameof(HoverTipFactory.FromKeyword)),
            prefix: new HarmonyMethod(typeof(EnglishCardText), nameof(KeywordTip)));
        harmony.Patch(AccessTools.Method(typeof(HoverTipFactory), nameof(HoverTipFactory.FromPotion), [typeof(PotionModel)]),
            prefix: new HarmonyMethod(typeof(EnglishCardText), nameof(PotionTip)));
        harmony.Patch(AccessTools.PropertyGetter(typeof(CardModel), nameof(CardModel.Pile)),
            prefix: new HarmonyMethod(typeof(BrowsedCard), nameof(BrowsedCard.PreviewPile)));
    }

    private const int LoadNow = 2;
    private const int LoadGlobal = 0x100;

    [DllImport("libdl.so.2", EntryPoint = "dlopen")]
    private static extern IntPtr LoadGlobalLibrary(string name, int flags);

    public static void Initialize() { }

    public static T Read<T>(Func<T> read)
    {
        if (!NGame.IsMainThread())
            throw new InvalidOperationException("English card rendering requires the game thread.");
        bool previous = active;
        try
        {
            active = true;
            return read();
        }
        finally { active = previous; }
    }

    public static T ReadPower<T>(PowerModel power, Func<T> read) => Read(() =>
    {
        var previous = activePower;
        try { activePower = power; return read(); }
        finally { activePower = previous; }
    });

    private static string Template(LocString text) => English.Entry(text.LocTable, text.LocEntryKey)
        ?? throw new InvalidOperationException("English localization is unavailable for this card detail.");

    private static bool FormattedText(LocString __instance, ref string __result)
    {
        if (!active)
            return true;
        var variables = __instance.Variables;
        if (activePower?.Applier?.Monster is { } applier && __instance.LocTable == "powers"
            && __instance.LocEntryKey.StartsWith(activePower.Id.Entry + ".", StringComparison.Ordinal)
            && variables.GetValueOrDefault("ApplierName") is StringVar)
        {
            // Some powers cache the applier's localized name when applied; format a detached value.
            variables = new Dictionary<string, object>(variables)
            {
                ["ApplierName"] = new StringVar("ApplierName", applier.Title.GetFormattedText())
            };
        }
        if (EnglishRelicText.Overrides is { Count: > 0 } values)
        {
            var detached = new Dictionary<string, object>(variables);
            foreach (var (key, value) in values)
                if (detached.ContainsKey(key)) detached[key] = new StringVar(key, value);
            variables = detached;
        }
        __result = Smart.Default.Format(CultureInfo.GetCultureInfo("en"), Template(__instance), variables);
        return false;
    }

    private static bool RawText(string key, string ____name, ref string __result)
    {
        if (!active)
            return true;
        __result = English.Entry(____name, key)
            ?? throw new InvalidOperationException("English localization is unavailable for this card detail.");
        return false;
    }

    private static bool KeywordTip(CardKeyword keyword, ref IHoverTip __result)
    {
        if (!active)
            return true;
        // Bypass language-dependent caches without reading or modifying their entries.
        string key = StringHelper.Slugify(keyword.ToString());
        __result = new HoverTip(new LocString("card_keywords", key + ".title"),
            new LocString("card_keywords", key + ".description"));
        return false;
    }

    private static bool PotionTip(PotionModel model, ref IHoverTip __result)
    {
        if (!active)
            return true;
        __result = HoverTipText.WithPotionValues(model, () => model.HoverTip);
        return false;
    }

    public static string Plain(string text)
    {
        string withIcons = Regex.Replace(text, @"\[img[^\]]*\](.*?)\[/img\]", match =>
        {
            string path = match.Groups[1].Value;
            return path.Contains("_energy_icon") ? " <Energy>" : path.Contains("star_icon") ? " <Star>"
                : " <Icon:" + Path.GetFileNameWithoutExtension(path) + ">";
        }, RegexOptions.Singleline);
        return Regex.Replace(EnglishText.Plain(withIcons.Replace("[br]", "\n")), @"[^\S\r\n]+", " ").Trim();
    }
}
