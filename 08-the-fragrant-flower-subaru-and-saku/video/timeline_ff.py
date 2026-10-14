"""Shared timing for the Fragrant Flower Short, cut to BEAUZ & JVNA - Crazy [NCS Release] (136 BPM).

The edit uses song time SONG_START .. SONG_START + DUR. Beat 0 of the edit is a downbeat; the song's drop
(1:06.04) is edit beat 72. Picture cuts sit on these beats; lyric fragments are timed to the vocal (found by
transcribing short windows of the song) and snapped to the eighth-note grid. The drum pulses come from the
real hits in beatmap_ff.json (analyze_song.py).
"""
BPM = 136
BEAT = 60 / BPM
FPS = 30
SONG_START = 66.04 - 72 * BEAT       # 34.275 s: a downbeat, 18 bars before the drop
DROP = 72                            # edit beat of the drop
NB = 119
DUR = 52.7                           # ends in the piano break after the drop


def b(n):
    return n * BEAT


SECTIONS = [(0, 24, 'verse'), (24, 56, 'chorus'), (56, 72, 'build'), (72, 108, 'drop'), (108, NB + 1, 'end')]

# Short lyric fragments only (not the full lyric):
# (start beat, [(word, beat)...], end beat, accent word, baseline y). y keeps clear of balloons and of the
# Shorts caption overlay at the bottom of the screen.
LYRICS = [
    (27.2, [('so', 27.4), ('crazy', 28.4)], 30.0, 'crazy', 330),
    (30.2, [('still', 30.4), ('in', 31.4), ('love', 31.9), ('with', 32.7), ('you', 33.2)], 36.0, 'love', 1420),
    (41.0, [('when', 41.2), ("I'm", 41.9), ('next', 42.6), ('to', 43.4), ('you', 43.8)], 46.0, 'next', 1300),
]


def section_at(beat):
    for s0, s1, kind in SECTIONS:
        if s0 <= beat < s1: return s0, s1, kind
    return SECTIONS[-1]
