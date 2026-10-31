import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="启动使用独立数据目录的游戏测试实例。")
    parser.add_argument("--windowed", action="store_true", help="使用图形窗口，验证实际显示与帧后采样")
    parser.add_argument("--capture", action="store_true", help="每次读取时保存测试窗口截图至测试工作目录的 observation.png")
    parser.add_argument("--check-observation", action="store_true", help="对独立测试战斗执行可见性过滤检查")
    parser.add_argument("--check-hand", action="store_true", help="在读取手牌时检查英语正文、提示缓存与动态数值")
    parser.add_argument("--check-ui", action="store_true", help="在读取界面说明时检查英语文本、可见性和读取前后一致性")
    parser.add_argument("--check-potions", action="store_true", help="为独立测试战斗准备药水并检查只读详情")
    parser.add_argument("--check-combatants", action="store_true", help="为独立战斗准备双方 powers 并检查意图与能力详情")
    parser.add_argument("--check-relics", action="store_true", help="为独立战斗准备遗物并检查只读正文、计数和可见性")
    parser.add_argument("--check-deck", action="store_true", help="检查原生牌组页的完整列表、升级预览和模型不变性")
    parser.add_argument("--check-piles", action="store_true", help="允许独立测试三类牌堆、空堆反馈、替换及生命周期")
    parser.add_argument("--check-map", action="store_true", help="允许独立测试整图、选路候选、飞鞋及双 Boss")
    catalog = json.loads(Path(__file__).with_name('test_scenarios.json').read_text())
    for name, choices in catalog.items():
        parser.add_argument('--' + name + '-scenario', choices=choices)
    parser.add_argument('--suite', action='store_true', help='启用仅测试的动态场景与对局清理接口')
    parser.add_argument('--work-dir', type=Path, help='新建的独立日志、IPC 与存档目录；运行时仍使用已准备目录')
    args = parser.parse_args()
    if args.capture and not args.windowed:
        parser.error("--capture 需要 --windowed。")
    root = Path(__file__).resolve().parents[1]
    work = root / ".tmp" / "roundtrip"
    prepared = work
    runtime = prepared / "runtime"
    if args.work_dir:
        work = args.work_dir.resolve()
        work.mkdir(parents=True, exist_ok=True)
        if any(work.iterdir()):
            parser.error('--work-dir 必须为空，避免混用旧 IPC、日志和存档。')
        settings_path = Path('sts2_agent-roundtrip/default/1/settings.save')
        target = work / 'userdata' / settings_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prepared / 'userdata' / settings_path, target)
    if args.suite and not args.work_dir:
        parser.error('--suite 需要显式 --work-dir。')
    if args.suite and any(value for key, value in vars(args).items() if key.startswith('check_')):
        parser.error('--suite 暂未接入 --check-* 内嵌检查，请单独启动。')
    if args.suite and any(getattr(args, name + '_scenario') for name in catalog):
        parser.error('--suite 场景由每局配置，不接受启动场景。')
    executable = runtime / "SlayTheSpire2"
    if not executable.is_file():
        raise SystemExit("请先运行 scripts/prepare_roundtrip.py。")
    environment = os.environ.copy()
    environment.update({
        "XDG_DATA_HOME": str(work / "userdata"),
        "STS2_AGENT_IPC_DIR": str(work / "ipc"),
        "STS2_AGENT_TEST_MODE": "1",
    })
    for variable in list(environment):
        if variable.startswith('STS2_AGENT_TEST_'):
            del environment[variable]
    environment['STS2_AGENT_TEST_MODE'] = '1'
    if args.suite:
        environment['STS2_AGENT_TEST_SUITE'] = '1'
    if args.ending_scenario:
        isolated = Path(tempfile.mkdtemp(prefix='ending-userdata-', dir=work))
        settings_path = Path('sts2_agent-roundtrip/default/1/settings.save')
        target = isolated / settings_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(work / 'userdata' / settings_path, target)
        environment['XDG_DATA_HOME'] = str(isolated)
        environment['STS2_AGENT_TEST_ENDING_SCENARIO'] = args.ending_scenario
    for name in catalog:
        value = getattr(args, name + '_scenario')
        if value:
            environment['STS2_AGENT_TEST_' + name.upper() + '_SCENARIO'] = value
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
    if args.check_map:
        environment["STS2_AGENT_TEST_MAP_CHECKS"] = str(work / "map-checks.json")
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
