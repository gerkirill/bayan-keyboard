import configparser
import fcntl
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET


REPO = Path(__file__).resolve().parents[1]
LAUNCHER = runpy.run_path(str(REPO / "bin/bayan"))
INSTALLER = REPO / "scripts/install.py"


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.lines = LAUNCHER["router_config"](0, 21).splitlines()
        self.rules = []
        rule = None
        for line in self.lines:
            parts = line.split()
            if parts[0] == "router_begin":
                rule = {"kind": parts[1]}
            elif parts[0] == "router_chan":
                rule["channel"] = tuple(map(int, parts[1:]))
            elif parts[0] == "router_par1":
                rule["key"] = tuple(map(int, parts[1:]))
            elif parts[0] == "router_end":
                self.rules.append(rule)
                rule = None

    def test_melody_and_all_chords(self):
        notes = [r for r in self.rules if r["kind"] == "note"]
        self.assertEqual(notes[0], {
            "kind": "note", "channel": (0, 0, 0, 0), "key": (48, 81, 1, 0),
        })
        expected_roots = (48, 55, 50, 57, 52, 59, 54, 49, 56, 51, 58, 53)
        self.assertEqual(len(notes), 73)
        channels = set()
        for index in range(24):
            chord = [r for r in notes if r["key"][:2] == (84 + index,) * 2]
            root = expected_roots[index % 12]
            third = 4 if index < 12 else 3
            self.assertEqual(sorted(r["key"][3] for r in chord),
                             [root, root + third, root + 7])
            self.assertTrue(all(r["key"][2] == 0 for r in chord))
            chord_channels = {r["channel"] for r in chord}
            self.assertEqual(len(chord_channels), 1)
            channel = next(iter(chord_channels))
            self.assertEqual(channel[:3], (0, 0, 0))
            self.assertNotIn(channel[3], (0, 9, 25))
            self.assertNotIn(channel[3], channels)
            channels.add(channel[3])

    def test_controllers_programs_and_preset(self):
        expected_channels = set(LAUNCHER["CHANNELS"])
        self.assertEqual(len(expected_channels), 25)
        for kind in ("cc", "prog", "pbend"):
            self.assertEqual(
                {r["channel"][3] for r in self.rules if r["kind"] == kind},
                expected_channels,
            )
        self.assertEqual(
            {line for line in self.lines if line.startswith("select ")},
            {f"select {c} 1 0 21" for c in expected_channels},
        )

    def test_key_map(self):
        entries = ET.parse(REPO / "config/bayan-b.xml").getroot()
        keys = {e.attrib["key"]: int(e.attrib["note"]) for e in entries}
        self.assertEqual(len(keys), 57)
        self.assertEqual(len(keys), len(entries))
        self.assertEqual([48 + keys[k] for k in "QZSXDRVT"],
                         [48, 50, 52, 53, 55, 57, 59, 60])
        self.assertEqual([48 + keys[k] for k in "1234567890-="], list(range(84, 96)))
        self.assertEqual([48 + keys[f"F{i}"] for i in range(1, 13)], list(range(96, 108)))
        self.assertTrue(all(0 <= offset < 61 for offset in keys.values()))


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="bayan-test-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "musician home"

    def install(self, *args):
        return subprocess.run(
            [sys.executable, str(INSTALLER), "--home", str(self.home), *args],
            capture_output=True, text=True,
        )

    def snapshot(self):
        return {str(p.relative_to(self.home)): p.read_bytes()
                for p in self.home.rglob("*") if p.is_file()}

    def test_dry_run_has_no_side_effects(self):
        result = self.install("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.home.exists())
        self.assertIn("Dry run", result.stdout)

    def test_install_rendering_and_repeat(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        before = self.snapshot()
        self.assertTrue(os.access(self.home / ".local/bin/bayan", os.X_OK))
        settings = configparser.ConfigParser(interpolation=None)
        settings.read(self.home / ".config/vmpk-bayan.conf")
        self.assertEqual(json.loads(settings.get("Keyboard", "MapFile")),
                         str(self.home / ".local/share/vmpk/bayan-b.xml"))
        self.assertEqual(settings.getint("Preferences", "BaseOctave"), 4)
        self.assertEqual(settings.getint("Preferences", "StartingKey"), 0)
        self.assertEqual(settings.getint("Preferences", "NumKeys"), 61)
        self.assertEqual(settings.getint("Instrument0", "Program"), 21)
        self.assertEqual(settings.get("Shortcuts", "actionContents"), "Ctrl+F1")
        self.assertEqual(settings.get("Shortcuts", "actionOctaveUp"), "")
        desktop = (self.home / ".local/share/applications/bayan.desktop").read_text()
        self.assertIn(f'Exec="{self.home}/.local/bin/bayan"', desktop)
        self.assertNotIn("@MAP_FILE@", settings.get("Keyboard", "MapFile"))
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Already installed", result.stdout)
        self.assertEqual(before, self.snapshot())

    def test_refuse_changed_files_and_backup_forced_update(self):
        self.assertEqual(self.install().returncode, 0)
        profile = self.home / ".config/vmpk-bayan.conf"
        profile.write_text(profile.read_text() + "\n# personal adjustment\n")
        before = self.snapshot()
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--force", result.stderr)
        self.assertEqual(before, self.snapshot())
        result = self.install("--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        backups = list((self.home / ".local/share/vmpk/backups").glob("*/.config/vmpk-bayan.conf"))
        self.assertEqual(len(backups), 1)
        self.assertIn("# personal adjustment", backups[0].read_text())
        self.assertNotIn("# personal adjustment", profile.read_text())

    def test_active_session_lock_blocks_update(self):
        self.assertEqual(self.install().returncode, 0)
        profile = self.home / ".config/vmpk-bayan.conf"
        profile.write_text(profile.read_text() + "\n# changed\n")
        lockfile = self.home / ".cache/vmpk-bayan/session.lock"
        lockfile.parent.mkdir(parents=True, exist_ok=True)
        with lockfile.open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            before = self.snapshot()
            result = self.install("--force")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("session is still running", result.stderr)
            self.assertEqual(before, self.snapshot())

    def test_running_vmpk_blocks_update(self):
        self.assertEqual(self.install().returncode, 0)
        profile = self.home / ".config/vmpk-bayan.conf"
        profile.write_text(profile.read_text() + "\n# changed\n")
        before = self.snapshot()
        process = subprocess.Popen(
            ["vmpk", "-c", "import time; time.sleep(30)", "--file", str(profile)],
            executable=sys.executable,
        )
        try:
            result = self.install("--force")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Close VMPK", result.stderr)
            self.assertEqual(before, self.snapshot())
        finally:
            process.terminate()
            process.wait(timeout=5)

    def test_symlink_is_not_replaced(self):
        self.home.mkdir()
        profile = self.home / ".config/vmpk-bayan.conf"
        profile.parent.mkdir()
        original = self.home / "personal.conf"
        original.write_text("keep me")
        profile.symlink_to(original)
        result = self.install("--force")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(profile.is_symlink())
        self.assertEqual(original.read_text(), "keep me")

    def test_staged_launcher_owns_and_cleans_up_children(self):
        self.home.mkdir()
        font = self.home / "test font.sf2"
        font.write_bytes(b"stub font, never passed to the real FluidSynth")
        result = self.install("--soundfont", str(font))
        self.assertEqual(result.returncode, 0, result.stderr)
        fakebin = self.home / "fakebin"
        fakebin.mkdir()
        stubs = {
            "fluidsynth": (
                "import json,os,pathlib,sys\n"
                "h=pathlib.Path(os.environ['HOME'])\n"
                "(h/'synth-args.json').write_text(json.dumps(sys.argv[1:]))\n"
                "(h/'synth.pid').write_text(str(os.getpid()))\n"
                "for line in sys.stdin: pass\n"
            ),
            "aconnect": """print("client 128: 'FLUID Synth (Bayan)'")\n""",
            "vmpk": (
                "import os,pathlib,sys,time\n"
                "h=pathlib.Path(os.environ['HOME'])\n"
                "(h/'piano-profile').write_text(sys.argv[2])\n"
                "time.sleep(.2)\n"
            ),
        }
        for name, source in stubs.items():
            filename = fakebin / name
            filename.write_text(f"#!{sys.executable}\n{source}")
            filename.chmod(0o755)
        result = subprocess.run(
            [sys.executable, str(self.home / ".local/bin/bayan")],
            env={**os.environ, "HOME": str(self.home), "PATH": str(fakebin),
                 "XDG_RUNTIME_DIR": str(self.home)},
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = json.loads((self.home / "synth-args.json").read_text())
        self.assertEqual(argv[-1], str(font))
        self.assertEqual(argv[argv.index("-K") + 1], "32")
        self.assertEqual(argv[argv.index("-r") + 1], "48000")
        self.assertNotIn("-i", argv)
        self.assertFalse(Path(argv[argv.index("-f") + 1]).exists())
        self.assertEqual((self.home / "piano-profile").read_text(),
                         str(self.home / ".config/vmpk-bayan.conf"))
        pid = int((self.home / "synth.pid").read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_checker_reports_missing_tools_without_installing_anything(self):
        result = subprocess.run(
            [sys.executable, str(REPO / "scripts/check-env.py")],
            env={**os.environ, "PATH": ""},
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL: vmpk", result.stdout)
        self.assertIn("Not ready", result.stdout)
        self.assertFalse(self.home.exists())


if __name__ == "__main__":
    unittest.main()
