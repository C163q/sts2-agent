import argparse
import json
import os
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="准备独立的 Linux 游戏验证目录。")
    parser.add_argument("--game-dir", required=True, type=Path)
    parser.add_argument("--ritsu-lib-dir", type=Path, default=os.environ.get("RitsuLibDir"))
    parser.add_argument("--language", choices=("eng", "zhs"), default="eng")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    game = args.game_dir.expanduser().resolve()
    runtime = root / ".tmp" / "roundtrip" / "runtime"
    build = root / "src" / "Sts2Agent" / "bin" / "Debug" / "net9.0"
    if not (game / "SlayTheSpire2").is_file():
        parser.error("游戏目录中缺少 SlayTheSpire2。")
    release = json.loads((game / "release_info.json").read_text())
    if release.get("version") != "v0.111.0":
        parser.error("当前构建目标为 v0.111.0，请使用该版本的完整游戏目录。")
    if not (build / "Sts2Agent.dll").is_file():
        parser.error("请先构建 src/Sts2Agent/Sts2Agent.csproj。")
    if not args.ritsu_lib_dir:
        parser.error("请配置 RitsuLibDir 或 --ritsu-lib-dir，指向完整的 RitsuLib 0.6.10 运行时。")
    library = args.ritsu_lib_dir.expanduser().resolve()
    required = ("mod_manifest.json", "RitsuLib.References.props", "assets.zip", "STS2-RitsuLib.dll",
                "ritsulib-variants.manifest", "compat/0.111.0/STS2-RitsuLib.dll",
                "compat/0.111.0/STS2-RitsuLib.Runtime.dll", "shared/STS2-RitsuLib.Shared.dll",
                "shared/STS2-RitsuLib.Ui.dll", "shared/STS2-RitsuLib.Settings.dll")
    if any(not (library / name).is_file() for name in required):
        parser.error("RitsuLib 目录不完整或缺少 0.111.0 兼容目标。")
    manifest = json.loads((library / "mod_manifest.json").read_text())
    if manifest.get("id") != "STS2-RitsuLib" or manifest.get("version") != "0.6.10":
        parser.error("本原型要求 RitsuLib 0.6.10。")
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
    shutil.copytree(library, runtime / "mods" / "STS2-RitsuLib", dirs_exist_ok=True)
    (runtime / "override.cfg").write_text(
        '[application]\nconfig/use_custom_user_dir=true\n'
        'config/custom_user_dir_name="sts2_agent-roundtrip"\n'
    )
    settings = runtime.parent / "userdata" / "sts2_agent-roundtrip" / "default" / "1" / "settings.save"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps({
        "schema_version": 8, "language": args.language, "fullscreen": False,
        "skip_intro_logo": True, "seen_ea_disclaimer": True,
        "mod_settings": {"mods_enabled": True, "mod_list": []},
    }, indent=2) + "\n")
    installation.write_text(json.dumps({
        "game_dir": str(game), "runtime": str(runtime),
        "release": release,
        "ritsulib": {"version": "0.6.10", "api": "0.111.0", "source": str(library)},
    }, indent=2) + "\n")
    print(runtime)


if __name__ == "__main__":
    main()
