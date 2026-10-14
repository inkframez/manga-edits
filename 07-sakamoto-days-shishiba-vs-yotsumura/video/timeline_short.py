"""Shared timing for the full Sakamoto Days Short: music_short.py and render_short.py both import this.

170 BPM, one beat = 0.353 s. Everything is placed in beats; b(n) converts to seconds. Change timing here first,
then re-run music_short.py and render_short.py so the swishes, hits and hit-stops stay locked to the picture.
"""
BPM = 170
BEAT = 60 / BPM
FPS = 30
NB = 90                    # musical beats
DUR = 32.4                 # 90 beats = 31.76 s, plus a short ring-out


def b(n):
    return n * BEAT


# Story acts (beats). The score changes texture at each one.
ACTS = {
    'versus': (0, 4),        # name card: both fighters slide in on a split field
    'rooftop': (4, 16),      # BABAM clash, VWAM over the roofs, SHWOO, crash down the shaft, BAM BAM
    'city': (16, 20),        # "Killing is like housecleaning to me."
    'passage': (20, 28),     # the dark Channel of Rebirth: half-time, then SHING
    'clash': (28, 36),       # the spread: three clashes, eyes lock
    'noh': (36, 40),         # the audience at the Noh stage, then KRASH
    'stage': (40, 56),       # leap, attack, the disguise, the reveal, "choosing my family"
    'mirror': (56, 64),      # the hammer as a mirror; the hammer flies
    'breath': (64, 66),      # 0.7 s of near-silence
    'impact': (66, 74),      # the finishing blow
    'after': (74, 90),       # "...I get tired of trying to find a reason to kill you", title
}

# Picture cuts. The score puts a swish into each one.
CUTS = [2, 4, 6, 8, 10, 14, 16, 18, 20, 24, 28, 33, 36, 38, 40, 44, 48, 52, 54, 56, 60, 64, 66, 74, 80]
# Contact hits: (beat, strength 1-3). Picture: hit-stop + flash + shake. Score: metal clang + brass stab + sub.
HITS = [(5, 2), (8, 1), (14, 1), (14.5, 1), (15, 1), (15.5, 2), (24, 2), (29, 3), (31, 2), (32, 2), (32.5, 3),
        (38, 2), (41, 2), (45, 2), (52, 3), (60, 1), (66, 3)]
# Hit-stop length per strength (s): the animation freezes while the camera keeps shaking.
HITSTOP = {1: 0.05, 2: 0.10, 3: 0.17}

# Song form. The drum pattern (and the picture's beat pulses) come from the section kind:
#   drop  = half-time phonk: 808 kicks on 0, 0.75, 2.5 of each 4-beat bar, clap on 2
#   drop2 = double-time: kicks on 0, 1.5, 2.5, claps on 1 and 3 (the clash and the final blow)
#   intro / break / noh / build / silence / soft / end = no kick pattern
SECTIONS = [(0, 4, 'intro'), (4, 20, 'drop'), (20, 24, 'break'), (24, 28, 'drop'), (28, 36, 'drop2'),
            (36, 38, 'noh'), (38, 56, 'drop'), (56, 64, 'build'), (64, 66, 'silence'), (66, 74, 'drop2'),
            (74, 80, 'soft'), (80, 88, 'drop'), (88, NB, 'end')]
PATTERNS = {'drop': ([0, .75, 2.5], [2]), 'drop2': ([0, 1.5, 2.5], [1, 3])}


def section_at(beat):
    for s0, s1, kind in SECTIONS:
        if s0 <= beat < s1: return s0, s1, kind
    return SECTIONS[-1]


def drum_hits():
    """(kicks, claps) as beat lists, generated from SECTIONS / PATTERNS."""
    kicks, claps = [], []
    for s0, s1, kind in SECTIONS:
        if kind not in PATTERNS: continue
        kp, cp = PATTERNS[kind]
        for bar in range(s0, s1, 4):
            kicks += [bar + k for k in kp if bar + k < s1]
            claps += [bar + c for c in cp if bar + c < s1]
    return kicks, claps
