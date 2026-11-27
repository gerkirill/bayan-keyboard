# Bayan Keyboard 🪗

A notebook-keyboard accordion for Linux: **B-system melody buttons plus 24
one-key major/minor chords**, using VMPK, FluidSynth, and an existing PipeWire
desktop. No Python packages, JACK server, global keyboard hooks, or root access
are needed to run it.

```text
Notebook keys → VMPK → ALSA MIDI → FluidSynth chord router → PipeWire
```

This preserves a setup developed and played on Manjaro/KDE Wayland. The current
voicing uses accordion for both melody and accompaniment, with chord roots at
C3–B3. Audio requests a 256-frame buffer at 48 kHz; this is not a measurement of
end-to-end latency.

## Install

Run these commands from the repository directory.

1. Have a working PipeWire desktop. On Manjaro/Arch, install missing application
   dependencies with:

   ```sh
   sudo pacman -Syu --needed python vmpk fluidsynth soundfont-fluid alsa-utils libnotify
   ```

   Review the transaction: `-Syu` may also update your system. The scripts below
   never run sudo, install packages, or reconfigure your audio services.
   `libnotify` supplies optional error notifications.

2. Check the environment and preview the user-file installation:

   ```sh
   python3 scripts/check-env.py
   python3 scripts/install.py --dry-run
   ```

3. **Close any Bayan/VMPK windows using this profile**, then install:

   ```sh
   python3 scripts/install.py
   ```

   Existing differing files are not overwritten. To deliberately update or
   replace an existing setup, close it and run:

   ```sh
   python3 scripts/install.py --force
   ```

   This first backs up replaced files, preserving their relative paths, under
   `~/.local/share/vmpk/backups/<UTC timestamp>/`. Identical files are left alone.
   Running VMPK profile writers and active Bayan session locks block updates.

4. Launch **Bayan — B-system Accordion** from your application menu, or:

   ```sh
   ~/.local/bin/bayan
   ```

   Use English/QWERTY input and click the piano area for keyboard focus.

For another GM-compatible SoundFont or VMPK data location, pass
`--soundfont /path/to/font.sf2 --instruments /path/to/gmgsxg.ins` to the installer
and environment checker. Program 21 must be an accordion preset. The launcher
reads the font path from its installed profile.

The layout uses the usual `$HOME/.config` and `$HOME/.local` paths; it does not
currently relocate them using XDG directory overrides. Paths are rendered for
the installing user, not the original machine.

## Play

```text
Major: 1   2   3   4   5   6   7   8   9   0   -   =
Minor: F1  F2  F3  F4  F5  F6  F7  F8  F9  F10 F11 F12
Root:  C   G   D   A   E   B   F#  C#  Ab  Eb  Bb  F
```

Hold a key to sustain its note/chord; release it to stop. Letters play a
three-row B-system treble mapping. Try:

- Melody C-major scale: `Q Z S X D R V T`.
- Accompaniment C–F–G–C: `1`, `=`, `2`, `1`.
- A minor: `F4`.
- Change timbre with VMPK's **Program** control; it affects all used channels.
- **Esc / Panic** sends all-notes-off. **Ctrl+F1** opens help.

**Keep Base Octave = 4, Transpose = 0, and Channel = 1.** The trigger mapping
depends on those values. Their keyboard shortcuts are disabled. Function keys
may require Fn/Fn-lock, and hardware key rollover can limit held combinations.

See [the full playing guide](docs/playing.md) for the note map and controls.

## What is saved here?

| File | Purpose |
| --- | --- |
| `bin/bayan` | Owns the VMPK/FluidSynth session and generates native chord-router rules |
| `config/bayan-b.xml` | The tested 57-key melody/chord mapping |
| `config/vmpk-bayan.conf.in` | Reproducible settings, without machine-specific window/palette state |
| `scripts/install.py` | Safe user-level installation, preview, backups, staging |
| `scripts/check-env.py` | Read-only dependency, backend, MIDI, PipeWire and optional install checks |
| `tests/` | Portable unit tests and optional real-FluidSynth verification |
| `AGENTS.md` | Instructions and invariants for future AI-assisted work |

The installer copies five files: the session launcher, XML map, rendered VMPK
profile, desktop entry, and playing guide. It does not symlink your home to this
checkout. Source edits take effect after reinstalling.

The 142-MiB SoundFont is supplied by the distribution package, **not Git**.
Generated VMPK UI state, session logs, personal backups, and upstream application
binaries/sources are intentionally not included.

## Verification

No desktop or audio device is needed for the standard-library unit tests:

```sh
python3 -m unittest discover -s tests -v
```

The optional native integration test loads the installed FluidSynth library
and FluidR3 SoundFont, but opens **no audio driver or MIDI port**:

```sh
python3 tests/verify_fluidsynth.py
```

It checks actual synth voices: all 24 chords, their releases, overlapping
chords/melody, the accordion program on all used channels, sustain/controller
fan-out, panic, and program changes.

To exercise installation without touching your real home:

```sh
python3 scripts/install.py --home /tmp/bayan-demo
python3 scripts/check-env.py --home /tmp/bayan-demo --installed
```

`--home` stages rendered files; it does not change the desktop session or start
the app. Do not launch that staged entry unless you intentionally run it with a
matching `HOME`.

For a real install:

```sh
python3 scripts/check-env.py --installed
```

Final acceptance is still audible/manual: test major and minor keys, especially
F10/F12, held overlapping chords with a melody, release behavior, and listening
latency. Use `pw-top` to inspect the actual graph quantum/rate and error count.

## Troubleshooting and removal

- Logs: `~/.cache/vmpk-bayan/session.log`.
- Always use the **Bayan** launcher; opening VMPK directly will not start the
  external chord synth.
- The wrapper prevents duplicate sessions and stops its synth when VMPK closes.
- Use speakers/wired headphones rather than Bluetooth for live playing.
- For crackling, change `"-z", "128"` to `"-z", "256"` and
  `"PIPEWIRE_LATENCY": "256/48000"` to `"PIPEWIRE_LATENCY": "512/48000"` in
  `bin/bayan`, test, then reinstall. Do not force global PipeWire settings.
- On another distribution, package names and data paths may differ; native
  PipeWire and ALSA-sequencer support in FluidSynth are required.

To uninstall, close Bayan and remove only these custom files:

```text
~/.local/bin/bayan
~/.config/vmpk-bayan.conf
~/.local/share/vmpk/bayan-b.xml
~/.local/share/vmpk/README-bayan.md
~/.local/share/applications/bayan.desktop
```

To restore a pre-install setup, copy the corresponding files from the timestamped
backup to their original paths, while VMPK is closed. Keep backups until satisfied.
There is no need to change PipeWire or remove your distribution packages.

## Provenance

Originally verified on **2026-11-27** with Manjaro/KDE Wayland, VMPK 0.9.2,
Drumstick 2.11.1, FluidSynth 2.6.2, FluidR3 3.1, and PipeWire (1.6.9 running;
1.6.11 installed). The user confirmed playback, chords, and the raised voicing.
These are tested versions, not a claim that every older/newer version works.

See [architecture notes](docs/architecture.md) for why the setup is structured
this way and the upstream references.
