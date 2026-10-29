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
            shutil.copy2(Path(__file__).with_name("prepare_roundtrip.py"), script)
            build = root / "spikes" / "roundtrip" / "bin" / "Debug" / "net9.0"
            build.mkdir(parents=True)
            for name in ("Sts2Agent.dll", "Sts2Agent.json"):
                (build / name).write_text("fixture")
            library = root / "library"
            for name in ("RitsuLib.References.props", "assets.zip", "STS2-RitsuLib.dll",
                         "compat/0.107.1/STS2-RitsuLib.dll", "compat/0.107.1/STS2-RitsuLib.Runtime.dll",
                         "shared/STS2-RitsuLib.Shared.dll", "shared/STS2-RitsuLib.Ui.dll",
                         "shared/STS2-RitsuLib.Settings.dll", "ritsulib-variants.manifest"):
                path = library / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture")
            (library / "mod_manifest.json").write_text(json.dumps({"id": "STS2-RitsuLib", "version": "0.6.10"}))
            games = []
            for label in ("A", "B"):
                game = root / label
                game.mkdir()
                (game / "SlayTheSpire2").write_text(label)
                (game / "resource.dat").write_text(label)
                (game / "release_info.json").write_text(json.dumps({"version": label}))
                games.append(game)
            missing = subprocess.run([sys.executable, str(script), "--game-dir", str(games[0]),
                                      "--ritsu-lib-dir", str(root / "missing")], capture_output=True, text=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertFalse((root / ".tmp" / "roundtrip" / "runtime").exists())
            first = subprocess.run([sys.executable, str(script), "--game-dir", str(games[0]),
                                    "--ritsu-lib-dir", str(library)],
                                   capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            work = root / ".tmp" / "roundtrip"
            record = (work / "installation.json").read_text()
            self.assertTrue((work / "runtime/mods/STS2-RitsuLib/compat/0.107.1/STS2-RitsuLib.Runtime.dll").is_file())
            second = subprocess.run([sys.executable, str(script), "--game-dir", str(games[1]),
                                     "--ritsu-lib-dir", str(library)],
                                    capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0, second.stdout)
            self.assertEqual((work / "runtime" / "SlayTheSpire2").read_text(), "A")
            self.assertEqual((work / "runtime" / "resource.dat").resolve(), games[0] / "resource.dat")
            self.assertEqual((work / "installation.json").read_text(), record)


if __name__ == "__main__":
    unittest.main()
