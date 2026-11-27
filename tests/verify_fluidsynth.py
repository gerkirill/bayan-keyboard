import ctypes as C
from pathlib import Path
import runpy
import tempfile

launcher = runpy.run_path(str(Path(__file__).resolve().parents[1] / "bin/bayan"))
lib = C.CDLL("libfluidsynth.so.3")
P, I, S = C.c_void_p, C.c_int, C.c_char_p
CALLBACK = C.CFUNCTYPE(I, P, P)


def bind(name, result, *args):
    fn = getattr(lib, name)
    fn.restype, fn.argtypes = result, args
    return fn


new_settings = bind("new_fluid_settings", P)
setting = bind("fluid_settings_setint", I, P, S, I)
new_synth = bind("new_fluid_synth", P, P)
load = bind("fluid_synth_sfload", I, P, S, I)
new_router = bind("new_fluid_midi_router", P, P, CALLBACK, P)
new_handler = bind("new_fluid_cmd_handler", P, P, P)
source = bind("fluid_source", I, P, S)
new_event = bind("new_fluid_midi_event", P)
route = bind("fluid_midi_router_handle_midi_event", I, P, P)
handle = bind("fluid_synth_handle_midi_event", I, P, P)
getters = {
    name: bind("fluid_midi_event_get_" + name, I, P)
    for name in ("type", "channel", "key", "velocity", "control", "value")
}
setters = {
    name: bind("fluid_midi_event_set_" + name, I, P, I)
    for name in ("type", "channel", "key", "velocity", "control", "value", "program")
}
voice_list = bind("fluid_synth_get_voicelist", None, P, C.POINTER(P), I, I)
voice_on = bind("fluid_voice_is_on", I, P)
voice_channel = bind("fluid_voice_get_channel", I, P)
voice_key = bind("fluid_voice_get_key", I, P)
get_program = bind("fluid_synth_get_program", I, P, I, C.POINTER(I), C.POINTER(I), C.POINTER(I))

settings = new_settings()
assert setting(settings, b"synth.midi-channels", 32) == 0
synth = new_synth(settings)
assert synth
assert load(synth, str(launcher["SOUNDFONT"]).encode(), 1) == 1
seen = []


@CALLBACK
def receive(_data, event):
    seen.append({name: get(event) for name, get in getters.items()})
    return handle(synth, event)


router = new_router(settings, receive, None)
handler = new_handler(synth, router)
with tempfile.NamedTemporaryFile(mode="w", suffix=".fluid") as rules:
    rules.write(launcher["router_config"](0, 21))
    rules.flush()
    assert source(handler, rules.name.encode()) == 0

for channel in launcher["CHANNELS"]:
    soundfont, bank, program = I(), I(), I()
    assert get_program(synth, channel, C.byref(soundfont), C.byref(bank), C.byref(program)) == 0
    assert (soundfont.value, bank.value, program.value) == (1, 0, 21)
print("PASS: all 25 used channels select the same accordion preset")


def event(kind, key=0, velocity=0, control=0, value=0, program=0):
    seen.clear()
    ev = new_event()
    for name, val in (
        ("type", kind), ("channel", 0), ("key", key), ("velocity", velocity),
        ("control", control), ("value", value), ("program", program),
    ):
        setters[name](ev, val)
    # MIDI data fields share storage; set only fields relevant to the event last.
    if kind in (0x80, 0x90):
        setters["key"](ev, key)
        setters["velocity"](ev, velocity)
    elif kind == 0xB0:
        setters["control"](ev, control)
        setters["value"](ev, value)
    elif kind == 0xC0:
        setters["program"](ev, program)
    assert route(router, ev) == 0
    bind("delete_fluid_midi_event", None, P)(ev)
    return list(seen)


def held():
    voices = (P * 256)()
    voice_list(synth, voices, 256, -1)
    return {
        (voice_channel(v), voice_key(v)) for v in voices if v and voice_on(v)
    }


for index, channel in enumerate(launcher["CHORD_CHANNELS"]):
    root = 48 + launcher["ROOTS"][index % 12]
    third = 4 if index < 12 else 3
    expected = {(channel, n) for n in (root, root + third, root + 7)}
    on = event(0x90, 84 + index, 85)
    assert {(e["channel"], e["key"]) for e in on} == expected, (index, on)
    assert len(on) == 3 and all(e["velocity"] == 85 for e in on)
    assert expected <= held(), (index, expected, held())
    off = event(0x80, 84 + index, 0)
    assert {(e["channel"], e["key"]) for e in off} == expected
    assert not expected & held()
print("PASS: all 24 triggers start and release the correct three live synth voices")

for note in (48, 60, 81):
    assert [(e["channel"], e["key"]) for e in event(0x90, note, 85)] == [(0, note)]
    event(0x80, note)
for note in (47, 82, 83, 108):
    assert event(0x90, note, 85) == []
print("PASS: melody passthrough and trigger suppression")

event(0x90, 84, 85)
event(0x90, 85, 85)
event(0x90, 62, 85)
event(0x80, 84)
assert {(2, 55), (2, 59), (2, 62), (0, 62)} <= held(), held()
event(0x80, 85)
assert (0, 62) in held()
event(0x80, 62)
print("PASS: releasing shared chord tones cannot interrupt another chord or melody")

for control, value in ((64, 127), (64, 0), (123, 0), (120, 0)):
    output = event(0xB0, control=control, value=value)
    assert {e["channel"] for e in output} == set(launcher["CHANNELS"])
event(0x90, 84, 85)
event(0xB0, control=123, value=0)
assert not held()
assert {e["channel"] for e in event(0xC0, program=23)} == set(launcher["CHANNELS"])
print("PASS: sustain, panic, and instrument changes reach all 25 channels")

for name, ptr in (
    ("delete_fluid_cmd_handler", handler), ("delete_fluid_midi_router", router),
    ("delete_fluid_synth", synth), ("delete_fluid_settings", settings),
):
    bind(name, None, P)(ptr)
