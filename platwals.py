"""Hoogovens platwalserij sound for the model railroad.

Background hall noise loops continuously. A trigger (GPIO button, or space/Enter
in the terminal while testing) plays one rolling pass:

    0 s   slow  - plate travels on the roller table to the stand
    14 s  fast  - main drive spools up
    22 s        - drive fades out, the roll clip fades in under it
    24 s  roll  - plate is rolled

Slow and fast are one continuous clip (motor.wav), so the drive glides up
instead of jumping; see make_clips.py. Timings live in timeline.py.

Presses during a pass are ignored. Press q (or Ctrl-C) to quit.
"""
import argparse
import os
import sys
import threading
import time
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

from timeline import FAST_AT, FAST_END, ROLL_AT, ROLL_LEAD, SLOW_AT  # noqa: E402,F401

SOUNDS = Path(__file__).parent / "sounds"

VOLUME = {"hall": 0.6, "water": 0.4, "motor": 1.0, "roll": 1.0}


class Mill:
    def __init__(self, roll_clip, water):
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(8)
        self.snd = {n: pygame.mixer.Sound(str(SOUNDS / f"{n}.wav")) for n in ("hall", "water", "motor")}
        self.snd["roll"] = pygame.mixer.Sound(str(SOUNDS / f"{roll_clip}.wav"))
        self.ch = {n: pygame.mixer.Channel(i) for i, n in enumerate(("hall", "water", "motor", "roll"))}
        self.busy = threading.Lock()
        self.t0 = None  # start of the running pass, for progress display
        self.status = "ready"

        self._play("hall", VOLUME["hall"], loops=-1, fade_ms=2000)
        self.set_water(water)

    def set_water(self, on):
        self.water = on
        if on:
            self._play("water", VOLUME["water"], loops=-1, fade_ms=2000)
        else:
            self.ch["water"].fadeout(2000)

    def set_roll(self, clip):
        self.snd["roll"] = pygame.mixer.Sound(str(SOUNDS / f"{clip}.wav"))

    def _play(self, name, volume, loops=0, fade_ms=0):
        self.ch[name].set_volume(volume)
        self.ch[name].play(self.snd[name], loops=loops, fade_ms=fade_ms)

    def trigger(self):
        if not self.busy.acquire(blocking=False):
            print("  (pass already running, ignored)")
            return
        threading.Thread(target=self._pass, daemon=True).start()

    def _pass(self):
        try:
            t0 = self.t0 = time.monotonic()

            def at(t, label):
                time.sleep(max(0.0, t0 + t - time.monotonic()))
                self.status = label
                print(f"  {t:4.0f}s  {label}")

            # Fades and crossfades are baked into the clips.
            at(SLOW_AT, "slow: plate to the stand")
            self._play("motor", VOLUME["motor"])
            at(FAST_AT, "fast: drive spools up")
            at(ROLL_AT - ROLL_LEAD, "drive fades out")
            self._play("roll", VOLUME["roll"])
            at(ROLL_AT, "roll")
            while self.ch["roll"].get_busy():
                time.sleep(0.1)
            print("  ready")
        finally:
            self.t0 = None
            self.status = "ready"
            self.busy.release()


def watch_gpio(pin, mill):
    try:
        from gpiozero import Button

        button = Button(pin, pull_up=True, bounce_time=0.05)
    except Exception as e:  # not on a Pi, or gpiozero missing
        print(f"GPIO off ({type(e).__name__}: {e})")
        return None
    button.when_pressed = mill.trigger
    print(f"GPIO{pin} armed (button to GND)")
    return button  # keep a reference, or gpiozero closes the pin


def watch_keyboard(mill, quit_event):
    print("Keyboard armed: space/Enter = trigger, q = quit")
    while not quit_event.is_set():
        key = sys.stdin.read(1)
        if key in (" ", "\n"):
            mill.trigger()
        elif key in ("q", "Q", ""):
            quit_event.set()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pin", type=int, default=17, help="BCM pin of the button (default 17)")
    ap.add_argument("--roll", choices=("roll", "roll_alt"), default="roll", help="which rolling recording")
    ap.add_argument("--water", action="store_true", help="add the water spray loop to the background")
    args = ap.parse_args()

    mill = Mill(args.roll, args.water)
    quit_event = threading.Event()
    button = watch_gpio(args.pin, mill)  # noqa: F841
    tty_state = None
    if sys.stdin.isatty():
        import termios
        import tty

        tty_state = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin)  # single keypresses, Ctrl-C still works
        threading.Thread(target=watch_keyboard, args=(mill, quit_event), daemon=True).start()
    try:
        quit_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if tty_state:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, tty_state)
    pygame.mixer.fadeout(1000)
    time.sleep(1)


if __name__ == "__main__":
    main()
