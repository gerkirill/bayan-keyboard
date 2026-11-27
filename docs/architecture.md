# Architecture and decisions

## Preserve the simplest working signal path

```text
focused QWERTY keys
  → VMPK keyboard map
  → ALSA sequencer, channel 0
  → FluidSynth's native MIDI router
  → synth voices loaded from FluidR3_GM.sf2
  → native PipeWire driver
```

There is no custom MIDI-event daemon, MIDI loopback, global key listener,
privileged input access, JACK server, or TCP control server.

VMPK/Drumstick maps one Qt key to one relative note (`QHash<int, int>`).
It cannot express multiple-note chords in XML. Its integrated FluidSynth
backend calls the synth directly; it does not expose the shell MIDI router.
That is why the chord version uses an external FluidSynth process.

## Pitch and channel invariants

VMPK computes:

```text
MIDI note = BaseOctave × 12 + map offset + Transpose
```

- BaseOctave = 4, Transpose = 0, GUI Channel = 1 (MIDI channel 0).
- Melody offsets 0–33 produce notes 48–81, with the mapping's intentional gap.
- Number-row offsets 36–47 produce trigger notes 84–95.
- F-key offsets 48–59 produce trigger notes 96–107.
- The router passes through melody notes only. It consumes each trigger,
  emitting a major or minor triad instead of sounding the trigger itself.
- Root order: C, G, D, A, E, B, F#, C#, Ab, Eb, Bb, F.
- Chord roots are MIDI `48 + pitch class`; thirds are +4/+3 and fifths +7.
  These are one octave above the first experimental voicing.

Treble uses channel 0. Each of the 24 chord triggers gets a separate channel
from 1–31, excluding 9 and 25 (percussion positions). The synth has 32 channels.
This isolation prevents a note-off in one chord from releasing an identical
pitch still held in another chord or in the melody.

All 25 used channels initially select SoundFont ID 1, bank 0, program 21
(Accordion). Program, bank/controller, and pitch-bend events fan out to every
used channel. Both note-on and note-off traverse the same note-routing rules.

An actual FluidSynth `channels` query on the original working session confirmed
the accordion preset on every used channel. Its FluidR3 label is spelled
`Accordian`; unused channels may still show piano or drums and are not played.

## Startup and shutdown

The Python standard-library wrapper:

1. Takes an exclusive per-user session lock.
2. Checks that the saved octave/transpose/channel are fixed.
3. Generates a temporary FluidSynth command file, including router rules and
   initial programs.
4. Starts FluidSynth with 32 MIDI channels, native PipeWire, 48 kHz, 128-frame
   periods × 2, and ALSA ID `Bayan`.
5. Waits, with a deadline, for its ALSA client.
6. Starts VMPK and supervises both children.
7. Reaps both when the GUI exits or the launcher receives a termination signal.

**Do not add `-i` casually:** FluidSynth 2.6.2 exits if it has no interactive
shell, player, or server to keep it alive. Holding its local shell stdin pipe
open keeps it alive without exposing a network server.

At 32 channels, FluidSynth creates two ALSA input ports. VMPK's destination
**`FLUID Synth (Bayan) (1)` means port 0**, not port 1. Drumstick numbers display
names starting at 1. VMPK must connect to port 0 so its incoming channel 0
matches the router rules.

## Persistence and safety

VMPK saves QSettings on normal exit. Editing its profile while it runs can lose
changes. The installer detects matching VMPK command lines and takes the same
session lock as the wrapper before updating files.

The repo contains a minimal profile template instead of generated palettes,
window geometry, or controller/UI history. Installations render the user's
absolute data paths. Updates refuse differing files unless `--force` is given;
forced updates back up all replaced originals before writing any replacements.

The scripts use the established `~/.config/vmpk-bayan.conf` and
`~/.local/share/vmpk` locations; full XDG config/data relocation is not implemented.

## Verification boundaries

- Unit tests inspect mappings/rules and exercise installation under temporary
  homes, including spaces, repeat installs, refusal, backups, and active writers.
- Native integration tests feed events through the actual FluidSynth router
  and inspect actual held synth voices. No audio/MIDI driver is opened.
- Environment checks inspect installed capabilities and the current audio
  server. They do not prove audibility or keyboard latency.
- Playing tests are manual: focus, Fn-lock, desktop shortcuts, physical rollover,
  timbre, and perceived latency.
- 256/48000 is a buffer request. `pw-top` verifies negotiated graph timing;
  neither is a complete key-to-speaker latency measurement.

## Upstream references

- [VMPK 0.9.2 keyboard-map parser](https://github.com/pedrolcl/VMPK/blob/v0.9.2/src/keyboardmap.cpp)
- [VMPK MIDI initialization and program state](https://github.com/pedrolcl/VMPK/blob/v0.9.2/src/vpiano.cpp)
- [Drumstick 2.11.1 keyboard events and pitch calculation](https://github.com/pedrolcl/drumstick/blob/RELEASE_2_11_1/library/widgets/pianoscene.cpp)
- [Drumstick ALSA output connection names](https://github.com/pedrolcl/drumstick/blob/RELEASE_2_11_1/library/rt-backends/alsa-out/alsamidioutput.cpp)
- [FluidSynth MIDI-router API](https://www.fluidsynth.org/api/group__midi__router.html)
- [FluidSynth 2.6.2 router implementation](https://github.com/FluidSynth/fluidsynth/blob/v2.6.2/src/midi/fluid_midi_router.c)
- [FluidSynth 2.6.2 ALSA input ports](https://github.com/FluidSynth/fluidsynth/blob/v2.6.2/src/drivers/fluid_alsa.c)
- [B-system button diagram](https://commons.wikimedia.org/wiki/File:B-Griff.svg)
