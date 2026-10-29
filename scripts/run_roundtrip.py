import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="启动使用独立数据目录的游戏测试实例。")
    parser.add_argument("--windowed", action="store_true", help="使用图形窗口，验证实际显示与帧后采样")
    parser.add_argument("--capture", action="store_true", help="每次读取时保存测试窗口截图至 .tmp/roundtrip/observation.png")
    parser.add_argument("--check-observation", action="store_true", help="对独立测试战斗执行可见性过滤检查")
    parser.add_argument("--check-hand", action="store_true", help="在读取手牌时检查英语正文、提示缓存与动态数值")
    parser.add_argument("--check-ui", action="store_true", help="在读取界面说明时检查英语文本、可见性和读取前后一致性")
    parser.add_argument("--check-potions", action="store_true", help="为独立测试战斗准备药水并检查只读详情")
    parser.add_argument("--check-combatants", action="store_true", help="为独立战斗准备双方 powers 并检查意图与能力详情")
    parser.add_argument("--check-relics", action="store_true", help="为独立战斗准备遗物并检查只读正文、计数和可见性")
    parser.add_argument("--check-deck", action="store_true", help="检查原生牌组页的完整列表、升级预览和模型不变性")
    parser.add_argument("--check-piles", action="store_true", help="允许独立测试三类牌堆、空堆反馈、替换及生命周期")
    args = parser.parse_args()
    if args.capture and not args.windowed:
        parser.error("--capture 需要 --windowed。")
    root = Path(__file__).resolve().parents[1]
    work = root / ".tmp" / "roundtrip"
    runtime = work / "runtime"
    executable = runtime / "SlayTheSpire2"
    if not executable.is_file():
        raise SystemExit("请先运行 scripts/prepare_roundtrip.py。")
    environment = os.environ.copy()
    environment.update({
        "XDG_DATA_HOME": str(work / "userdata"),
        "STS2_AGENT_IPC_DIR": str(work / "ipc"),
        "STS2_AGENT_TEST_MODE": "1",
    })
    if args.capture:
        environment["STS2_AGENT_TEST_CAPTURE"] = str(work / "observation.png")
    if args.check_observation:
        environment["STS2_AGENT_TEST_CHECKS"] = str(work / "observation-checks.json")
    if args.check_hand:
        environment["STS2_AGENT_TEST_HAND_CHECKS"] = str(work / "hand-checks.json")
    if args.check_ui:
        environment["STS2_AGENT_TEST_UI_CHECKS"] = str(work / "ui-checks.json")
    if args.check_potions:
        environment["STS2_AGENT_TEST_POTION_CHECKS"] = str(work / "potion-checks.json")
    if args.check_combatants:
        environment["STS2_AGENT_TEST_COMBATANT_CHECKS"] = str(work / "combatant-checks.json")
    if args.check_relics:
        environment["STS2_AGENT_TEST_RELIC_CHECKS"] = str(work / "relic-checks.json")
    if args.check_deck:
        environment["STS2_AGENT_TEST_DECK_CHECKS"] = str(work / "deck-checks.json")
    if args.check_piles:
        environment["STS2_AGENT_TEST_PILE_CHECKS"] = str(work / "pile-checks.json")
    print(f"启动独立测试实例，日志位于 {work / 'stdout.log'}，按 Ctrl+C 停止。", flush=True)
    arguments = [str(executable), "--path", str(runtime),
                 "--force-steam", "off", "--log-file", str(work / "game.log"), "--max-fps", "30"]
    arguments += ["--windowed", "--resolution", "1280x720"] if args.windowed else ["--headless"]
    with (work / "stdout.log").open("w") as output:
        os.dup2(output.fileno(), 1)
        os.dup2(output.fileno(), 2)
    os.chdir(runtime)
    os.execve(executable, arguments, environment)


if __name__ == "__main__":
    main()
