from scripts._bootstrap import ROOT
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class PrepareRoundtripTests(unittest.TestCase):
    def test_changed_installation_is_rejected_before_mutating_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "scripts" / "prepare_roundtrip.py"
            script.parent.mkdir()
            shutil.copy2((ROOT / "scripts/prepare_roundtrip.py"), script)
            build = root / "src" / "Sts2Agent" / "bin" / "Debug" / "net9.0"
            build.mkdir(parents=True)
            for name in ("Sts2Agent.dll", "Sts2Agent.json"):
                (build / name).write_text("fixture")
            library = root / "library"
            for name in ("RitsuLib.References.props", "assets.zip", "STS2-RitsuLib.dll",
                         "compat/0.111.0/STS2-RitsuLib.dll", "compat/0.111.0/STS2-RitsuLib.Runtime.dll",
                         "shared/STS2-RitsuLib.Shared.dll", "shared/STS2-RitsuLib.Ui.dll",
                         "shared/STS2-RitsuLib.Settings.dll", "ritsulib-variants.manifest"):
                path = library / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture")
            (library / "mod_manifest.json").write_text(json.dumps({"id": "STS2-RitsuLib", "version": "0.6.15"}))
            windows = sys.platform == "win32"
            executable = "SlayTheSpire2.exe" if windows else "SlayTheSpire2"
            games = []
            for label in ("A", "B"):
                game = root / label
                game.mkdir()
                (game / executable).write_text(label)
                (game / "resource.dat").write_text(label)
                (game / "release_info.json").write_text(json.dumps({"version": "v0.111.1", "commit": label}))
                live_mods = game / ("Mods" if windows else "mods")
                live_mods.mkdir()
                (live_mods / "unrelated.json").write_text("{}")
                games.append(game)
            missing = subprocess.run([sys.executable, str(script), "--game-dir", str(games[0]),
                                      "--ritsu-lib-dir", str(root / "missing")], capture_output=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertFalse((root / ".tmp" / "roundtrip" / "runtime").exists())
            release_path = games[0] / "release_info.json"
            release_path.write_text(json.dumps({"version": "v0.111.0"}))
            incompatible = subprocess.run([sys.executable, str(script), "--game-dir", str(games[0]),
                                           "--ritsu-lib-dir", str(library)], capture_output=True)
            self.assertNotEqual(incompatible.returncode, 0, incompatible.stdout)
            self.assertFalse((root / ".tmp" / "roundtrip" / "runtime").exists())
            release_path.write_text(json.dumps({"version": "v0.111.1", "commit": "A"}))
            first = subprocess.run([sys.executable, str(script), "--game-dir", str(games[0]),
                                    "--ritsu-lib-dir", str(library)],
                                   capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            work = root / ".tmp" / "roundtrip"
            self.assertFalse((work / "runtime/mods/unrelated.json").exists())
            record = (work / "installation.json").read_text()
            self.assertTrue((work / "runtime/mods/STS2-RitsuLib/compat/0.111.0/STS2-RitsuLib.Runtime.dll").is_file())
            self.assertEqual(json.loads(record)["ritsulib"]["api"], "0.111.0")
            settings = json.loads((work / "userdata/sts2_agent-roundtrip/default/1/settings.save").read_text())
            self.assertEqual(settings["schema_version"], 8)
            second = subprocess.run([sys.executable, str(script), "--game-dir", str(games[1]),
                                     "--ritsu-lib-dir", str(library)],
                                    capture_output=True)
            self.assertNotEqual(second.returncode, 0, second.stdout)
            self.assertEqual((work / "runtime" / executable).read_text(), "A")
            resource = work / "runtime" / "resource.dat"
            if windows:
                self.assertEqual(resource.read_text(), "A")
                self.assertFalse(resource.is_symlink())
            else:
                self.assertEqual(resource.resolve(), games[0] / "resource.dat")
            self.assertEqual((work / "installation.json").read_text(), record)

            # A dependency upgrade must replace compatibility DLLs absent from the new package.
            installed_library = work / "runtime/mods/STS2-RitsuLib"
            obsolete = installed_library / "compat/0.110.0/STS2-RitsuLib.dll"
            obsolete.parent.mkdir()
            obsolete.write_text("previous runtime")
            updated = subprocess.run([sys.executable, str(script), "--game-dir", str(games[0]),
                                      "--ritsu-lib-dir", str(library)], capture_output=True)
            self.assertEqual(updated.returncode, 0, updated.stderr)
            self.assertFalse(obsolete.exists())
            self.assertTrue((installed_library / "compat/0.111.0/STS2-RitsuLib.dll").is_file())


if __name__ == "__main__":
    unittest.main()
