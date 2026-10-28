import os
from pathlib import Path


def main():
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
    print(f"启动独立无头测试实例，日志位于 {work / 'stdout.log'}，按 Ctrl+C 停止。", flush=True)
    arguments = [str(executable), "--headless", "--path", str(runtime),
                 "--force-steam", "off", "--log-file", str(work / "game.log"), "--max-fps", "30"]
    with (work / "stdout.log").open("w") as output:
        os.dup2(output.fileno(), 1)
        os.dup2(output.fileno(), 2)
    os.chdir(runtime)
    os.execve(executable, arguments, environment)


if __name__ == "__main__":
    main()
