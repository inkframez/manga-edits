"""v2 timing shared by music_v2.py and render_v2.py. 160 BPM, one beat = 0.375 s, 89 beats + a short tail.

Everything is placed in beats; b(n) converts to seconds. Change timing here first, then re-run music_v2.py and
render_v2.py so picture and score stay locked.
"""
BPM = 160
BEAT = 60 / BPM
FPS = 30
NB = 89                      # musical beats; the last 0.125 s is a fade tail
DUR = 33.5


def b(n):
    return n * BEAT


# Acts (beats). The score changes texture at each one.
ACTS = {
    'tick': (0, 8),          # black + clock assembling, castle band
    'duel': (8, 32),         # first contact -> arm sacrifice -> 07:68
    'all_in': (32, 40),      # no more tricks, Sojo 2x (half-time, tension)
    'nishiki': (40, 56),     # Chihiro 3x, from above, Sojo still reacts
    'drain': (56, 62),       # Nishiki released, Kuro, timing skewed
    'vacuum': (62, 64),      # 0.75 s of near silence, clock runs out
    'impact': (64, 72),      # strike, Cloud Gouger breaks
    'after': (72, 89),       # hilt, the price, end card
}

# Hard picture cuts (beats). The score puts a sword swish ahead of each one and a metal contact on it.
CUTS = [4, 8, 12, 16, 18, 20, 21, 24, 27, 32, 36, 40, 42, 48, 52, 56, 60, 62, 64, 68, 72, 75, 78, 81]
# Heavy hits: flash / shake in picture, taiko + sub in the score.
HITS = [8, 16, 24, 29, 40, 44, 48, 64, 70]
# Clock-snap glitch (06:00 -> 03:00) and the two energy surges.
GLITCH = 38
SURGES = {'sojo_2x': 36, 'chihiro_3x': 40}

# Story clock: (beat, seconds remaining). Linear between anchors; the 06:00 -> 03:00 jump is a snap.
# Anchors are the clocks printed on the pages: 12:00, 11:52, 09:04, 07:68, 06:00 / 03:00, 01:47, 00:89.
CLOCK = [(0, 12.0), (8, 12.0), (12, 11.52), (24, 9.04), (29, 7.68), (36, 6.0), (38, 6.0), (38.15, 3.0),
         (40, 1.47), (48, 0.89), (56, 0.60), (62, 0.18), (64, 0.0), (NB, 0.0)]


def clock_at(beat):
    for (b0, v0), (b1, v1) in zip(CLOCK, CLOCK[1:]):
        if beat <= b1:
            u = 0 if b1 == b0 else max(0.0, min(1.0, (beat - b0) / (b1 - b0)))
            return v0 + (v1 - v0) * u
    return CLOCK[-1][1]
