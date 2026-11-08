using System.Globalization;
using System.Reflection.Emit;
using HarmonyLib;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Nodes.Screens.GameOverScreen;
using MegaCrit.Sts2.Core.Nodes.Screens.RunHistoryScreen;
using MegaCrit.Sts2.Core.Nodes.Screens.Timeline;
using MegaCrit.Sts2.Core.Nodes.Screens.Timeline.UnlockScreens;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Timeline.Epochs;
using MegaCrit.Sts2.addons.mega_text;

namespace Sts2Agent;

internal static class EnglishRunResultText
{
    private static readonly EnglishText English = new();

    public static void Initialize()
    {
        var harmony = new Harmony("sts2_agent.result_english");
        var capture = new HarmonyMethod(typeof(EnglishRunResultText), nameof(CaptureSources));
        harmony.Patch(AccessTools.Method(typeof(NRunHistory), nameof(NRunHistory.GetDeathQuote)),
            transpiler: capture, postfix: new HarmonyMethod(typeof(EnglishRunResultText), nameof(RetainQuote)));
        harmony.Patch(AccessTools.Method(typeof(NRunHistory), "LoadDeathQuote"), transpiler: capture);
        harmony.Patch(AccessTools.Method(typeof(NGameOverScreen), "InitializeBannerAndQuote"), transpiler: capture);
        harmony.Patch(AccessTools.Method(typeof(NRunHistory), "LoadTimeDetails"),
            postfix: new HarmonyMethod(typeof(EnglishRunResultText), nameof(BindDate)));
        harmony.Patch(AccessTools.Method(typeof(NUnlockMiscScreen), nameof(NUnlockMiscScreen._Ready)),
            postfix: new HarmonyMethod(typeof(EnglishRunResultText), nameof(MiscReady)));
        harmony.Patch(AccessTools.Method(typeof(NUnlockMiscScreen), nameof(NUnlockMiscScreen.SetUnlocks)),
            prefix: new HarmonyMethod(typeof(EnglishRunResultText), nameof(BindMisc)));
        harmony.Patch(AccessTools.Method(typeof(NTimelineScreen), nameof(NTimelineScreen.QueueMiscUnlock)),
            prefix: new HarmonyMethod(typeof(EnglishRunResultText), nameof(QueuedMisc)));
        harmony.Patch(AccessTools.Method(typeof(NeowEpoch), nameof(NeowEpoch.QueueUnlocks)), transpiler: capture);
    }

    private static IEnumerable<CodeInstruction> CaptureSources(IEnumerable<CodeInstruction> instructions)
    {
        var formatted = AccessTools.Method(typeof(LocString), nameof(LocString.GetFormattedText));
        var raw = AccessTools.Method(typeof(LocString), nameof(LocString.GetRawText));
        foreach (var instruction in instructions)
        {
            // Native precompiled calls can bypass the general localization hooks.
            if (instruction.Calls(formatted) || instruction.Calls(raw))
            {
                string replacement = instruction.Calls(formatted) ? nameof(EnglishEventText.CaptureFormatted) : nameof(EnglishEventText.CaptureRaw);
                instruction.opcode = OpCodes.Call;
                instruction.operand = AccessTools.Method(typeof(EnglishEventText), replacement);
            }
            yield return instruction;
        }
    }

    private static void RetainQuote(string __result) => EnglishEventText.RetainComposite(__result);

    private static void QueuedMisc(string __0) => EnglishEventText.RetainComposite(__0);
    private static void BindMisc(NUnlockMiscScreen __instance, string __0) => EnglishEventText.BindSource(__instance, __0);
    private static void MiscReady(NUnlockMiscScreen __instance)
    {
        var label = __instance.GetNode<MegaRichTextLabel>("%Label");
        // Queueing and scene instantiation can outlive the short recent-text cache.
        EnglishEventText.CopySource(__instance, label, label.Text);
    }

    private static void BindDate(NRunHistory __instance, RunHistory history)
    {
        var label = __instance.GetNode<MegaRichTextLabel>("%DateLabel");
        string displayed = label.Text;
        // Capture the same displayed time at assignment; observation never reloads history.
        DateTime local = TimeZoneInfo.ConvertTimeFromUtc(DateTimeOffset.FromUnixTimeSeconds(history.StartTime).UtcDateTime, TimeZoneInfo.Local);
        var culture = CultureInfo.GetCultureInfo("en");
        string dateFormat = English.Entry("run_history", "INFO.DATE_FORMAT")
            ?? throw new InvalidOperationException("English run history date format is unavailable.");
        string timeFormat = English.Entry("run_history", "INFO.TIME_FORMAT")
            ?? throw new InvalidOperationException("English run history time format is unavailable.");
        string translated = EnglishEventText.Read(() =>
        {
            var text = new LocString("run_history", "INFO.DATE_TIME");
            text.Add("Date", local.ToString(dateFormat, culture));
            text.Add("Time", local.ToString(timeFormat, culture));
            return text.GetFormattedText();
        });
        EnglishEventText.BindTranslation(label, displayed, translated);
    }
}
