#!/usr/bin/env python3
"""Read-only prerequisite checks: no installs, audio playback, or service changes."""

import argparse
import configparser
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def command(args, **kwargs):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=15, **kwargs)
    except (OSError, subprocess.TimeoutExpired) as error:
        return subprocess.CompletedProcess(args, 1, "", str(error))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--soundfont", type=Path,
                        default=Path("/usr/share/soundfonts/FluidR3_GM.sf2"))
    parser.add_argument("--instruments", type=Path,
                        default=Path("/usr/share/vmpk/gmgsxg.ins"))
    parser.add_argument("--installed", action="store_true",
                        help="also check installed user files and the saved profile")
    args = parser.parse_args()
    failures = []

    def check(label, ok, detail=""):
        print(f"{'OK' if ok else 'FAIL'}: {label}" + (f" — {detail}" if detail else ""))
        if not ok:
            failures.append(label)

    check("Python 3.10+", sys.version_info >= (3, 10), sys.version.split()[0])
    available = {}
    for tool in ("vmpk", "fluidsynth", "aconnect", "pw-dump"):
        available[tool] = bool(shutil.which(tool))
        check(tool, available[tool])
    check("General MIDI SoundFont", args.soundfont.expanduser().is_file(),
          str(args.soundfont))
    check("VMPK instrument definitions", args.instruments.expanduser().is_file(),
          str(args.instruments))
    if available["vmpk"]:
        result = command(["vmpk", "--version"], env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
        check("VMPK starts", result.returncode == 0, result.stdout.strip())
    if available["fluidsynth"]:
        result = command(["fluidsynth", "-o", "help"])
        lines = result.stdout + result.stderr
        drivers = next((line for line in lines.splitlines()
                        if line.startswith("audio.driver ")), "")
        midi = next((line for line in lines.splitlines()
                     if line.startswith("midi.driver ")), "")
        check("FluidSynth native PipeWire driver", "'pipewire'" in drivers)
        check("FluidSynth ALSA sequencer driver", "'alsa_seq'" in midi)
    if available["aconnect"]:
        result = command(["aconnect", "-l"])
        check("ALSA sequencer access", result.returncode == 0)
        if "'FLUID Synth (Bayan)'" in result.stdout:
            print("INFO: a Bayan synth is currently running; close it before installing.")
    if available["pw-dump"]:
        result = command(["pw-dump"])
        try:
            data = json.loads(result.stdout) if result.returncode == 0 else []
            sinks = [node for node in data
                     if node.get("info", {}).get("props", {}).get("media.class") == "Audio/Sink"]
            check("PipeWire connection and audio sink", bool(sinks),
                  f"{len(sinks)} sink(s)" if result.returncode == 0 else result.stderr.strip())
        except (ValueError, TypeError):
            check("PipeWire status JSON", False)
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print("WARN: no graphical display in this shell; VMPK needs a desktop session.")
    for tool in ("notify-send", "desktop-file-validate"):
        if not shutil.which(tool):
            print(f"WARN: optional {tool} is missing.")

    if args.installed:
        home = args.home.expanduser().resolve()
        for name in (".local/bin/bayan", ".local/share/vmpk/bayan-b.xml",
                     ".local/share/vmpk/README-bayan.md",
                     ".local/share/applications/bayan.desktop", ".config/vmpk-bayan.conf"):
            check(f"installed {name}", (home / name).is_file())
        check("executable launcher", os.access(home / ".local/bin/bayan", os.X_OK))
        settings = configparser.ConfigParser(interpolation=None)
        try:
            settings.read(home / ".config/vmpk-bayan.conf")
            fixed = all(settings.getint("Preferences", key) == value
                        for key, value in (("BaseOctave", 4), ("Transpose", 0), ("Channel", 0)))
            check("fixed octave/transpose/channel", fixed)
            check("ALSA MIDI output", settings.get("Connections", "OutputDriver") == "ALSA")
            check("FluidSynth port 0 selected",
                  settings.get("Connections", "OutPort") == "FLUID Synth (Bayan) (1)")
        except (ValueError, configparser.Error):
            check("readable installed profile", False)
    print(f"\n{'Ready' if not failures else 'Not ready'}: {len(failures)} required check(s) failed.")
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
