"""Timing of one rolling pass, shared by make_clips.py and platwals.py (seconds)."""
SLOW_AT = 0.0    # plate starts moving on the roller table
FAST_AT = 13.0  # main drive spools up
FAST_END = 22.0  # drive at speed, starts fading out
ROLL_AT = 24.0   # plate enters the rolls
ROLL_LEAD = 2.0  # roll clips start this early, so they fade in under the drive
