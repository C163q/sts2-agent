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
            games = []
            for label in ("A", "B"):
                game = root / label
                game.mkdir()
                (game / "SlayTheSpire2").write_text(label)
                (game / "resource.dat").write_text(label)
                (game / "release_info.json").write_text(json.dumps({"version": label}))
                games.append(game)
            first = subprocess.run([sys.executable, str(script), "--game-dir", str(games[0])],
                                   capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            work = root / ".tmp" / "roundtrip"
            record = (work / "installation.json").read_text()
            second = subprocess.run([sys.executable, str(script), "--game-dir", str(games[1])],
                                    capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0, second.stdout)
            self.assertEqual((work / "runtime" / "SlayTheSpire2").read_text(), "A")
            self.assertEqual((work / "runtime" / "resource.dat").resolve(), games[0] / "resource.dat")
            self.assertEqual((work / "installation.json").read_text(), record)


if __name__ == "__main__":
    unittest.main()
