# Platwalserij sound

Raspberry Pi + speaker under the layout. The hall noise loops continuously; a
button press plays one rolling pass:

| t      | clip    | what                                                    |
|--------|---------|---------------------------------------------------------|
| 0 s    | `motor` | slow: steady drive hum, plate on the roller table       |
| 14 s   |         | fast: the real spool-up, compressed to 8 s (pitch kept) |
| 22 s   | `roll`  | drive fades out, roll clip fades in under it            |
| 24 s   |         | plate bites and is rolled (~20 s)                       |

Slow and fast are one continuous clip, so the drive glides up instead of jumping
between two recordings. Timings are in `timeline.py`, cut points in
`make_clips.py`; rerun `make_clips.py` after changing either.

## The recordings

All recorded 2025-10-11, mono AAC 44.1 kHz from an Android phone, 20-110 s each.

| file                   | content                                                                     | used as         |
|------------------------|-----------------------------------------------------------------------------|-----------------|
| Audio from Bart(1) copy| completely steady hall noise, no events                                     | `hall` loop     |
| Audio from Bart        | same hall, slightly louder; level drops ~2 dB after 12 s                    | -               |
| continous - water      | water spray bursts (13-20 s, 35-45 s with a 4 kHz hiss, 47-66 s)            | `water` loop    |
| event 1                | rolling 4.0-21.0 s (+6 dB in 600-3000 Hz, motor drops 300 -> 202 Hz)        | `roll_alt`      |
| event 2                | rolling 9.5-29.0 s (+8 dB in 600-3000 Hz), the biggest event                | `roll`          |
| spool up event 2       | motor steady at 262 Hz for 17 s, then spools up smoothly to ~390 Hz by 65 s | `motor`        |
| spool up event         | spool-up already in progress (329 -> 393 Hz), slows at ~30 s, spools again  | -               |

The two spool-ups look like the reversing drive: speeds up, slows, speeds up again.

## Testing (Mac or Pi)

    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    python3 make_clips.py                     # Mac only (ffmpeg + numpy): regenerates sounds/
    .venv/bin/python platwals.py              # space/Enter = pass, q = quit
    .venv/bin/python platwals.py --roll roll_alt --water

## On the Pi

    git clone git@github.com:bartbrinkman/platwalserij.git
    cd platwalserij && ./install.sh           # PIN=27 ./install.sh for another pin

That installs pygame + gpiozero from apt and starts `platwals.py` at boot as a
systemd user service. Useful commands:

    git pull && systemctl --user restart platwals    # update
    journalctl --user -u platwals -f                 # log (every pass is printed)
    systemctl --user stop platwals                   # stop, e.g. to test by hand:
    python3 platwals.py                              # space/Enter = pass, q = quit

## Wiring

Push button between **GPIO17 (physical pin 11)** and **GND (pin 9)**. No resistor
needed: the internal pull-up is enabled and presses are debounced (50 ms).

    pin 1  3V3   o o  5V    pin 2
               ...
    pin 9  GND   o o        pin 10
    pin 11 GPIO17 o o       pin 12

- Any free GPIO works with `--pin N` (BCM numbering). Avoid GPIO2/3 (fixed I2C
  pull-ups) and GPIO18-21 if an I2S audio board or amp is fitted.
- A reed switch, relay contact or occupancy contact from the layout works the same
  way, as long as it is a dry contact to GND.
- Never connect track or accessory voltage (DCC, 12-16 V) to a GPIO pin: the Pi
  takes 3.3 V max. Use an optocoupler or a relay in between.
- Long wires under the layout pick up noise: twisted pair or a 100 nF capacitor
  across the button helps against false triggers.
