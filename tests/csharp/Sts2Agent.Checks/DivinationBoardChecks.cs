using Sts2Agent;

internal static class DivinationBoardChecks
{
    public static void Run(Action<bool, string> check)
    {
        var hidden = new bool[11, 11];
        for (int y = 0; y < 11; y++) for (int x = 0; x < 11; x++) hidden[x, y] = true;
        hidden[5, 5] = false;
        var blank = DivinationBoard.Build(hidden, []);
        check(blank.cell_rows[5] == "#####.#####" && blank.visible_fragments.Length == 0,
            "revealed transparent space has no fragment or hidden identity");
        var partial = DivinationBoard.Build(hidden, [new(5, 5, "potion.base", false), new(6, 5, "gold.coin", true)]);
        check(partial.cell_rows[5] == "#####s#####" && partial.visible_fragments.Single().appearance == "potion.base",
            "only revealed patches enter the text board");
        var whole = DivinationBoard.Build(hidden, [new(5, 5, "potion.base", true)]);
        check(whole.cell_rows[5] == "#####S#####", "complete visible icons use S without filling transparent cells");
        var conflict = DivinationBoard.Build(hidden, [new(5, 5, "potion.base", true), new(5, 5, "gold.coin", true)]);
        check(conflict.cell_rows[5] == "#####s#####" && conflict.visible_fragments.Single().appearance == "unrecognized",
            "overlapping incompatible drawings remain unknown");
        var unknown = DivinationBoard.Build(hidden, [new(5, 5, "unrecognized", false)]);
        check(unknown.cell_rows[5] == "#####s#####", "unrecognized ink is not reported as empty");
        hidden[8, 0] = false;
        var outside = DivinationBoard.Build(hidden, [new(8, 0, "unrecognized", false)]);
        check(outside.cell_rows[0][8] == '.' && outside.visible_fragments.Length == 0,
            "native sphere clipping excludes icon bleed behind the outer frame");
    }
}
