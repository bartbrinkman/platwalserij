"""Cut the playback clips out of the original phone recordings.

Run on the Mac (needs ffmpeg + numpy); copy the resulting sounds/ folder to the Pi.
Cut points come from analysing the recordings (see README.md); tweak them here.
"""
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

from timeline import FAST_AT, FAST_END, ROLL_LEAD

SR = 44100
SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "~/Downloads/drive-download-20261024T111144Z-1-001").expanduser()
OUT = Path(__file__).parent / "sounds"

SPOOL = "spool up event 2.m4a"
STEADY_END = 17.0  # motor steady at 262 Hz until here...
RAMP_END = 59.0    # ...then spools up to ~370 Hz by here
TAIL = 4.0         # seconds of top speed after the ramp, faded out under the roll

# Roll clips: (source file, moment the plate bites, end s). The clip starts
# ROLL_LEAD before the bite so the hall noise in it fades in first.
ROLLS = {
    "roll": ("event 2.m4a", 9.5, 30.7),      # +8 dB, the biggest event
    "roll_alt": ("event 1.m4a", 4.0, 27.3),  # +6 dB, motor drops under load
}
# Seamless background loops: (source file, start s, end s, crossfade s)
LOOPS = {
    "hall": ("Audio from Bart(1) copy.m4a", 0.0, 30.9, 2.0),
    "water": ("continous - water.m4a", 0.0, 72.8, 3.0),
}


def ffmpeg(args, stdin=None):
    return np.frombuffer(subprocess.run(
        ["ffmpeg", "-v", "error", *args, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        input=stdin, check=True, capture_output=True,
    ).stdout, dtype=np.float32)


def load(name):
    return ffmpeg(["-i", str(SRC / name)])


def stretch(x, factor):
    # Speed up without changing pitch; atempo takes at most 2x per stage.
    stages = []
    while factor > 2:
        stages.append("atempo=2")
        factor /= 2
    stages.append(f"atempo={factor:.4f}")
    return ffmpeg(["-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", ",".join(stages)], x.tobytes())


def save(name, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"{name}.wav  {len(x) / SR:5.1f}s")


def cut(x, start, end):
    return x[int(start * SR):int(end * SR)]


def fade(x, fade_in, fade_out):
    x = x.copy()
    n_in, n_out = int(fade_in * SR), int(fade_out * SR)
    if n_in:
        x[:n_in] *= np.sin(np.linspace(0, np.pi / 2, n_in)) ** 2
    if n_out:
        x[-n_out:] *= np.cos(np.linspace(0, np.pi / 2, n_out)) ** 2
    return x


def join(a, b, xfade):
    # Equal-power crossfade: the last xfade s of a overlap the first of b.
    n = int(xfade * SR)
    t = np.linspace(0, np.pi / 2, n)
    return np.concatenate([a[:-n], a[-n:] * np.cos(t) + b[:n] * np.sin(t), b[n:]])


def seamless(x, xfade):
    # Blend the tail into the head so the loop point is inaudible.
    n = int(xfade * SR)
    t = np.linspace(0, np.pi / 2, n)
    head, body, tail = x[:n], x[n:-n], x[-n:]
    return np.concatenate([body, tail * np.cos(t) + head * np.sin(t)])


def motor(x):
    """Slow + fast as one clip: steady hum, then the real spool-up compressed
    to the fast phase (pitch kept), then top speed fading out under the roll."""
    xf = 2.0
    slow = cut(x, 0, FAST_AT + xf)  # ends at 262 Hz, same as where the ramp begins
    ramp_len = FAST_END - FAST_AT + xf
    ramp = stretch(cut(x, STEADY_END, RAMP_END), (RAMP_END - STEADY_END) / ramp_len)
    tail = cut(x, RAMP_END, RAMP_END + TAIL + 1)
    m = join(join(slow, ramp, xf), tail, 1.0)
    m = m[:int((FAST_END + TAIL) * SR)]
    return fade(m, 2.5, TAIL)


def main():
    OUT.mkdir(exist_ok=True)
    for stale in ("slow", "fast"):  # replaced by motor.wav
        (OUT / f"{stale}.wav").unlink(missing_ok=True)
    save("motor", motor(load(SPOOL)))
    for name, (src, bite, end) in ROLLS.items():
        save(name, fade(cut(load(src), bite - ROLL_LEAD, end), ROLL_LEAD, 3.0))
    for name, (src, start, end, xf) in LOOPS.items():
        save(name, seamless(cut(load(src), start, end), xf))


if __name__ == "__main__":
    main()
