# Agent instructions

Read `README.md`, `docs/architecture.md`, and the relevant source before editing.
Keep this a small, user-level Linux setup; reuse FluidSynth's native router
rather than introducing another MIDI service or UI framework.

## Working scope

- This checkout is the source of truth. Do not edit/install into the user's live
  home, restart their instrument, or change system audio without authorization.
- Do not install packages automatically. Show the environment checker output and
  let the user review any package transaction.
- Never commit SoundFonts, generated profiles, logs, personal backups, or
  machine-specific paths. Dependencies are distribution packages.
- The installer defaults to refusing different existing files. Keep `--force`
  explicit, with backups made before replacement. Preserve the active-writer
  and shared session-lock guards.
- Never modify settings while VMPK is running: its exit-time QSettings writer
  can overwrite the work. Reconcile every writer before final checks.

## Behavioral invariants

- B-system treble: Q row inner (C family), A row middle (C# family), Z row outer
  (D/B family); +3 semitones per column.
- BaseOctave 4, Transpose 0, MIDI input channel 0 (GUI 1). Do not silently
  re-enable octave, transpose, or channel shortcuts.
- Melody 48–81; major triggers 84–95; minor triggers 96–107. Triggers must not
  pass through as high notes.
- Roots follow C G D A E B F# C# Ab Eb Bb F. Chord roots start at MIDI 48,
  not 36: the user preferred all chords one octave higher.
- Each chord has an independent channel; exclude 9 and 25, and keep 32 synth
  channels. Shared-pitch releases must not stop other chords/melody.
- Accordion = bank 0/program 21, zero-based. Initialize all used channels and
  forward program/controllers/pitch bend, not only note events.
- Use native PipeWire at 48 kHz. Buffer size is a per-instrument request; never
  force global PipeWire clock/quantum or add a JACK server.
- `FLUID Synth (Bayan) (1)` is the display name of ALSA port **0**. Start the
  synth before VMPK. Avoid feedback loops and duplicate sessions.
- Keep the FluidSynth stdin pipe open. `-i` alone makes this tested CLI version
  exit; do not solve that by exposing a TCP server.

## Verification

Minimum checks for ordinary changes:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check-env.py
python3 scripts/install.py --dry-run
```

For router, channel, program, or release changes:

```sh
python3 tests/verify_fluidsynth.py
```

That test loads a local SoundFont and native library but opens no audio/MIDI
driver. The standard unit suite needs only Python's standard library.
Use `scripts/install.py --home <temporary-home>` for installation verification;
do not use the real home as a test fixture.

After deliberate live installation, verify ALSA subscriptions, the actual
PipeWire stream/quantum/rate and error counts, normal-close process cleanup,
and restart persistence. Ask the user to test sound, F10/F12, held overlaps,
release, Fn-lock, and physical key rollover. Do not claim these are proven by
offline tests or that buffering duration equals end-to-end latency.

When adding features, keep the XML, router, profile template, playing guide,
and tests consistent. Document restrictions instead of hiding regressions.
