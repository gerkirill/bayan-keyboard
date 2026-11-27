# Playing the Bayan keyboard

Launch **Bayan — B-system Accordion**, or `~/.local/bin/bayan`.
Select English/QWERTY input and click the piano area. The GUI remains
piano-shaped; the typing-key layout is B-system chromatic accordion.

## Melody

The bottom letter row is the outer accordion row; the top is the inner row.
Moving right raises pitch by three semitones.

```text
Keys:  Q   W   E   R   T   Y   U   I   O   P   [   ]
Notes: C3  Eb3 F#3 A3  C4  Eb4 F#4 A4  C5  Eb5 F#5 A5

Keys:   A   S   D   F   G   H   J   K   L   ;   '
Notes:  Db3 E3  G3  Bb3 Db4 E4  G4  Bb4 Db5 E5  G5

Keys:    Z   X   C   V   B   N   M   ,   .   /
Notes:   D3  F3  Ab3 B3  D4  F4  Ab4 B4  D5  F5
```

C3 here means MIDI note 48; VMPK's octave labels may differ.

- Chromatic test: `Q A Z W S X E D C R` (C3 through A3).
- C-major scale: `Q Z S X D R V T`.
- Manual C-major chord: hold `Q S D`; one octave higher: `T H J`.

## One-key chords

```text
Major: 1   2   3   4   5   6   7   8   9   0   -   =
Minor: F1  F2  F3  F4  F5  F6  F7  F8  F9  F10 F11 F12
Root:  C   G   D   A   E   B   F#  C#  Ab  Eb  Bb  F
```

Hold to sustain; release to stop. Letter-key melody and multiple chords can be
played together. Each chord has its own synth channel, so releasing a shared
pitch does not cut off another held chord or melody.

Chord roots are C3–B3: C major is C3/E3/G3, C minor is C3/Eb3/G3.
This is the final, raised voicing—not the initial lower accompaniment.

Try `1 → = → 2 → 1` for C–F–G–C. `F4` is A minor.
Depending on your notebook's Fn-lock, use Fn with F1–F12. Desktop global
shortcuts and hardware key rollover can affect particular combinations.

## Controls and limits

- **Base Octave 4, Transpose 0, Channel 1:** leave these fixed. Their change
  shortcuts are disabled because they would shift the trigger notes.
- **Program:** changes the melody and all chord channels together. The default
  is Accordion (GM program 21 zero-based, conventionally number 22).
- **Velocity:** changes the strength of newly played notes.
- **Esc / Panic:** all-notes-off. Release the Sustain control as well if used.
- **Ctrl+F1:** help; F1 is reserved for C minor.
- Close the app normally to save changes and stop the managed synth.

The high piano keys shown for chord triggers do not represent the sounding
triad pitches. Use the typing-key labels above.

This is three-row bayan-style melody plus major/minor triads, not a full
Stradella bass system. There is no bellows expression or physical-key velocity,
and notebook key geometry is only an approximation of accordion buttons.

Use speakers or wired headphones. Startup diagnostics are in
`~/.cache/vmpk-bayan/session.log`.
