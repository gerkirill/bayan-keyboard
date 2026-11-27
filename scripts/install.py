#!/usr/bin/env python3
"""Install user-owned files only; never install packages or change audio services."""

import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


REPO = Path(__file__).resolve().parents[1]


def desktop_command(executable):
    # Desktop-entry string decoding happens before Exec argument decoding.
    text = str(executable)
    for old, new in (
        ("\\", "\\\\\\\\"), ('"', '\\\\"'), ("`", "\\\\`"),
        ("$", "\\\\$"), ("%", "%%"),
    ):
        text = text.replace(old, new)
    return f'"{text}"'


def install_files(home, soundfont, instruments):
    data = home / ".local/share/vmpk"
    template = (REPO / "config/vmpk-bayan.conf.in").read_text()
    for token, value in (
        ("@MAP_FILE@", data / "bayan-b.xml"),
        ("@SOUNDFONT@", soundfont),
        ("@INSTRUMENTS@", instruments),
    ):
        template = template.replace(token, json.dumps(str(value), ensure_ascii=False))
    desktop = "\n".join((
        "[Desktop Entry]",
        "Type=Application",
        "Name=Bayan — B-system Accordion",
        "GenericName=Virtual Accordion",
        "Comment=B-system accordion with one-key major/minor chords",
        f"Exec={desktop_command(home / '.local/bin/bayan')}",
        "TryExec=vmpk",
        "Icon=vmpk",
        "Terminal=false",
        "Categories=AudioVideo;Audio;Midi;Music;",
        "Keywords=Bayan;Accordion;B-system;VMPK;",
        "",
    ))
    return {
        home / ".local/bin/bayan": ((REPO / "bin/bayan").read_bytes(), 0o755),
        data / "bayan-b.xml": ((REPO / "config/bayan-b.xml").read_bytes(), 0o644),
        data / "README-bayan.md": ((REPO / "docs/playing.md").read_bytes(), 0o644),
        home / ".config/vmpk-bayan.conf": (template.encode(), 0o644),
        home / ".local/share/applications/bayan.desktop": (desktop.encode(), 0o644),
    }


def profile_writers(profile):
    writers = []
    for filename in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            args = filename.read_bytes().split(b"\0")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if args and Path(os.fsdecode(args[0])).name == "vmpk":
            if os.fsencode(profile) in args:
                writers.append(filename.parent.name)
    return writers


def atomic_write(target, content, mode):
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, filename = tempfile.mkstemp(prefix=f".{target.name}-", dir=target.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
            os.fchmod(output.fileno(), mode)
        os.replace(filename, target)
    finally:
        if os.path.exists(filename):
            os.unlink(filename)


def install(args):
    home = args.home.expanduser().resolve()
    files = install_files(home, args.soundfont.expanduser().resolve(),
                          args.instruments.expanduser().resolve())
    changed = {}
    for target, (content, mode) in files.items():
        if target.is_symlink():
            raise RuntimeError(f"Refusing to replace a symlink: {target}")
        if target.exists() and not target.is_file():
            raise RuntimeError(f"Not a regular file: {target}")
        if (not target.exists() or target.read_bytes() != content
                or target.stat().st_mode & 0o777 != mode):
            changed[target] = (content, mode)
    if args.dry_run:
        for target in files:
            action = "install/update" if target in changed else "unchanged"
            print(f"{action}: {target}")
        print("Dry run: no files changed. Dependencies are checked separately.")
        return
    if not changed:
        print("Already installed; no files changed.")
        return
    writers = profile_writers(home / ".config/vmpk-bayan.conf")
    if writers:
        raise RuntimeError(f"Close VMPK normally first (PID(s): {', '.join(writers)}).")
    existing = [target for target in changed if target.exists()]
    if existing and not args.force:
        listing = "\n".join(str(target) for target in existing)
        raise RuntimeError(f"Existing files differ; nothing changed:\n{listing}\n"
                           "Close Bayan and use --force to back them up and replace them.")

    lockfile = home / ".cache/vmpk-bayan/session.lock"
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    with lockfile.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Close Bayan before installing; its session is still running.")
        if existing:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
            backup = home / ".local/share/vmpk/backups" / stamp
            for target in existing:
                destination = backup / target.relative_to(home)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, destination)
            print(f"Backup: {backup}")
        for target, (content, mode) in changed.items():
            atomic_write(target, content, mode)
            print(f"Installed: {target}")
    if shutil.which("update-desktop-database"):
        subprocess.run(
            ["update-desktop-database", str(home / ".local/share/applications")],
            check=False,
        )
    print("Launch 'Bayan — B-system Accordion' from the menu, or ~/.local/bin/bayan.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home(),
                        help="target home directory (also useful for staging/tests)")
    parser.add_argument("--soundfont", type=Path,
                        default=Path("/usr/share/soundfonts/FluidR3_GM.sf2"))
    parser.add_argument("--instruments", type=Path,
                        default=Path("/usr/share/vmpk/gmgsxg.ins"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="back up differing existing files before replacing them")
    args = parser.parse_args()
    try:
        install(args)
    except (OSError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
