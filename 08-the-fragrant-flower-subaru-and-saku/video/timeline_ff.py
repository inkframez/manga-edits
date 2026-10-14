"""Shared timing for the Fragrant Flower Short: music_ff.py and render_ff.py both import this.

80 BPM, one beat = 0.75 s, 60 beats + a ring-out. One chord per 4-beat bar. Change timing here first, then
re-run music_ff.py and render_ff.py so picture and score stay locked.
"""
BPM = 80
BEAT = 60 / BPM
FPS = 30
NB = 60
DUR = NB * BEAT + 2.0          # 47.0 s: the last chord rings out under the title


def b(n):
    return n * BEAT


# The "royal road" progression (IV - V - iii - vi) in D major. The tonic (D) is withheld until the title.
#            bar: 0        1      2       3      4        5    6       7      8      9       10       11       12       13   14
CHORDS = ['Gmaj7', 'A', 'F#m7', 'Bm7', 'Gmaj7', 'A', 'F#m7', 'Bm7', 'Em7', 'F#m7', 'Gmaj7', 'Asus4', 'Gmaj7', 'A', 'Dadd9']

# Song sections (beats). The drum map and the picture's beat pulse come from these.
#   intro  piano alone          cafe  lofi beat enters        snow  beat thins to shaker + chimes
#   full   full beat + strings  held  drums out, riser        hush  near silence ("I...")
#   swell  confession: strings, piano octaves, deep kick      end   tonic resolves, rings out
SECTIONS = [(0, 8, 'intro'), (8, 28, 'cafe'), (28, 32, 'snow'), (32, 44, 'full'), (44, 46, 'held'),
            (46, 48, 'hush'), (48, 56, 'swell'), (56, NB, 'end')]
PATTERNS = {'cafe': ([0, 2.5], [1, 3]), 'full': ([0, 1.75, 2.5], [1, 3]), 'swell': ([0, 2], [1, 3])}

# Picture cuts (beats). The score puts a soft cymbal swell or reverse piano into the big ones.
CUTS = [4, 8, 12, 16, 20, 23, 26, 28, 30, 32, 34, 38, 40, 42, 44, 46, 48, 50, 56]
BIG = [8, 32, 48, 56]          # the beat entering, the snow scene opening up, "...like you", the title


def section_at(beat):
    for s0, s1, kind in SECTIONS:
        if s0 <= beat < s1: return s0, s1, kind
    return SECTIONS[-1]


def drum_hits():
    """(kicks, snaps) as beat lists from SECTIONS / PATTERNS."""
    kicks, snaps = [], []
    for s0, s1, kind in SECTIONS:
        if kind not in PATTERNS: continue
        kp, sp = PATTERNS[kind]
        for bar in range(s0, s1, 4):
            kicks += [bar + k for k in kp if bar + k < s1]
            snaps += [bar + c for c in sp if bar + c < s1]
    return kicks, snaps
