import argparse
import json
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="准备独立的 Linux 游戏验证目录。")
    parser.add_argument("--game-dir", required=True, type=Path)
    parser.add_argument("--language", choices=("eng", "zhs"), default="eng")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    game = args.game_dir.expanduser().resolve()
    runtime = root / ".tmp" / "roundtrip" / "runtime"
    build = root / "spikes" / "roundtrip" / "bin" / "Debug" / "net9.0"
    if not (game / "SlayTheSpire2").is_file():
        parser.error("游戏目录中缺少 SlayTheSpire2。")
    if not (build / "Sts2Agent.dll").is_file():
        parser.error("请先构建 spikes/roundtrip/Sts2Agent.csproj。")
    installation = runtime.parent / "installation.json"
    if installation.exists():
        previous = json.loads(installation.read_text())
        if previous.get("game_dir") != str(game):
            parser.error("运行目录已绑定其他游戏安装位置；请先保留验证证据并重建 .tmp/roundtrip，避免混用资源。")
    elif runtime.exists() and any(runtime.iterdir()):
        parser.error("运行目录已有文件但缺少安装记录；请先保留证据并重建 .tmp/roundtrip。")
    runtime.mkdir(parents=True, exist_ok=True)
    for source in game.iterdir():
        if source.name == "SlayTheSpire2":
            shutil.copy2(source, runtime / source.name)
        elif source.name not in ("mods", "override.cfg", "probe.gd") and not (runtime / source.name).exists():
            (runtime / source.name).symlink_to(source, target_is_directory=source.is_dir())
    destination = runtime / "mods" / "Sts2Agent"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("Sts2Agent.dll", "Sts2Agent.json"):
        shutil.copy2(build / name, destination / name)
    (runtime / "override.cfg").write_text(
        '[application]\nconfig/use_custom_user_dir=true\n'
        'config/custom_user_dir_name="sts2_agent-roundtrip"\n'
    )
    settings = runtime.parent / "userdata" / "sts2_agent-roundtrip" / "default" / "1" / "settings.save"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps({
        "schema_version": 5, "language": args.language, "fullscreen": False,
        "skip_intro_logo": True, "seen_ea_disclaimer": True,
        "mod_settings": {"mods_enabled": True, "mod_list": []},
    }, indent=2) + "\n")
    installation.write_text(json.dumps({
        "game_dir": str(game), "runtime": str(runtime),
        "release": json.loads((game / "release_info.json").read_text()),
    }, indent=2) + "\n")
    print(runtime)


if __name__ == "__main__":
    main()
