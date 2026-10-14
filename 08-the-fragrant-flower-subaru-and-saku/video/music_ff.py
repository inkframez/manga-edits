"""Fragrant Flower Short score: an emotional piano / lofi ballad, 80 BPM, D major, 47 s -> score_ff.wav.

Romance edits live on a felt piano, a soft lofi beat and a string swell, so that is what this builds, from
scratch (no samples, no third-party music):
  piano    modelled: stretched (inharmonic) partials, three detuned strings per note, a felt-hammer spectrum,
           two-stage decay, hammer thump, sustain-pedal release; played as arpeggios, chords and the melody
  strings  a detuned ensemble with slow attacks and vibrato for the realisation and the confession
  celesta  snow chimes once the snow starts
  drums    lofi: round kick, finger snap, swung shaker; out for the hush before "I..."
  air      vinyl crackle, and winter wind under the snow scenes
The harmony is the J-pop "royal road" (IV-V-iii-vi) in D, and the tonic chord is held back until the title.
Sections, chords and the drum map come from timeline_ff.py, the same file the renderer reads.
Usage:  python music_ff.py
"""
from pathlib import Path
from functools import lru_cache
import wave
import numpy as np
from timeline_ff import BEAT, DUR, NB, CHORDS, SECTIONS, BIG, drum_hits, b

SR = 48000
N = round(SR * DUR)
RNG = np.random.default_rng(204)
HERE = Path(__file__).resolve().parent
BUS = {k: np.zeros((N, 2)) for k in ('piano', 'strings', 'cel', 'drums', 'bass', 'air', 'verb')}


def tt(d): return np.arange(max(1, round(d * SR))) / SR
def hz(m): return 440 * 2 ** ((m - 69) / 12)


def place(bus, s, at, gain=1.0, pan=0.0, send=0.0):
    i = round(at * SR); pan = max(-1.0, min(1.0, pan))
    if s.ndim == 1: s = np.stack([s * np.sqrt((1 - pan) / 2), s * np.sqrt((1 + pan) / 2)], 1)
    if i < 0: s, i = s[-i:], 0
    n = min(len(s), N - i)
    if n <= 0: return
    BUS[bus][i:i + n] += s[:n] * gain
    if send: BUS['verb'][i:i + n] += s[:n] * gain * send


def filt(x, lo, hi):
    n = len(x); f = np.fft.rfftfreq(n, 1 / SR)
    h = (1 - np.exp(-(f / max(lo, 1)) ** 2)) * np.exp(-(f / hi) ** 2)
    return np.fft.irfft(np.fft.rfft(x, axis=0) * (h[:, None] if x.ndim == 2 else h), n, axis=0)


def noise(d, lo=20, hi=20000):
    s = filt(RNG.normal(size=max(16, round(d * SR))), lo, hi); return s / max(1e-6, np.std(s)) * .3


# ---------------------------------------------------------------- instruments
@lru_cache(maxsize=None)
def piano(m, dur, vel=.6):
    """One piano note, dur seconds before the damper falls (pedal = long dur)."""
    f0 = hz(m); rel = .35; t = tt(dur + rel)
    Bc = 6e-5 * 2 ** ((m - 48) / 12)                       # inharmonicity grows up the keyboard
    strings = (-.55, 0, .65) if m >= 40 else (-.4, .4)      # cents
    d1 = .32 + .004 * f0                                    # slow decay rate grows with pitch
    out = np.zeros(len(t)); total = 0.0
    k = 1
    while k <= 26:
        fk = k * f0 * np.sqrt(1 + Bc * k * k)
        if fk > 9500: break
        amp = k ** -1.15 * np.exp(-(k - 1) / (1.2 + 6 * vel)) * (abs(np.sin(np.pi * k / 7.3)) + .08)
        dk = d1 * (1 + .14 * (k - 1))
        env = .62 * np.exp(-t * dk * 3.5) + .38 * np.exp(-t * dk * .55)
        for c in strings:
            out += amp * env * np.sin(2 * np.pi * fk * 2 ** (c / 1200) * t + RNG.uniform(0, 6.283))
        total += amp * len(strings)
        k += 1
    out /= total
    out *= np.minimum(t / .003, 1)
    out += filt(RNG.normal(size=len(t)), 60, 900 + 1200 * vel) * np.exp(-t * 55) * .06 * vel      # hammer thump
    out *= np.where(t > dur, np.exp(-(t - dur) / .16), 1.0)
    out = filt(out, 25, 3800 + 8000 * vel)                                                          # felt
    return out * (.35 + .9 * vel)


@lru_cache(maxsize=None)
def strings_note(m, dur, att=.7):
    t = tt(dur + .9); f0 = hz(m); out = np.zeros(len(t))
    for v in range(6):
        det = RNG.uniform(-.006, .006); vib = 1 + .0035 * np.sin(2 * np.pi * (4.6 + .5 * v) * t + v)
        ph = 2 * np.pi * np.cumsum(np.full(len(t), f0 * (1 + det)) * vib) / SR + RNG.uniform(0, 6)
        out += sum(np.sin(ph * k) / k for k in range(1, 12) if f0 * k < 6000)
    out = filt(out / 6, 120, 2200)
    env = np.minimum(t / att, 1) ** 2 * np.clip((dur + .9 - t) / .9, 0, 1)
    return out * env * .35


@lru_cache(maxsize=None)
def celesta(m, d=1.6):
    t = tt(d); f = hz(m)
    s = np.sin(2 * np.pi * f * t) + .3 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 6) + .12 * np.sin(2 * np.pi * f * 9.8 * t) * np.exp(-t * 14)
    return s * np.exp(-t * 2.6) * np.minimum(t / .002, 1) * .5


def kick(deep=1.0):
    t = tt(.5); f = 48 + 75 * np.exp(-t * 30)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (7 / deep))
    return filt(np.tanh(s * 1.5), 20, 1400) * .9


def snap():
    t = tt(.25); s = np.zeros(len(t))
    for off, g in ((0, .5), (.006, .7), (.013, 1.0)):
        i = int(off * SR); seg = noise(.25 - off, 1100, 6500) * np.exp(-tt(.25 - off) * 42)
        s[i:i + len(seg)] += seg * g
    return s * .8


def shaker(acc=1.0):
    t = tt(.12); env = np.minimum(t / .012, 1) * np.exp(-t * 34)
    return noise(.12, 5500, 13000) * env * .45 * acc


def bass(m, d):
    t = tt(d); f = hz(m)
    s = np.sin(2 * np.pi * f * t) + .25 * np.sin(4 * np.pi * f * t) + .08 * np.sin(6 * np.pi * f * t)
    env = np.minimum(t / .01, 1) * np.exp(-t * 1.1) * np.clip((d - t) / .08, 0, 1)
    return np.tanh(s * env * 1.4) * .6


def reverse_swell(ms, d):
    s = sum(piano(m, d, .55) for m in ms)[:round(d * SR)][::-1]
    return s * np.linspace(0, 1, len(s)) ** 2


def cymbal_swell(d):
    t = tt(d); return (noise(d, 4000, 15000) * np.exp(-(d - t) * 2.5))[::1] * (t / d) ** 3


# ---------------------------------------------------------------- harmony
VOICE = {   # (bass root, right-hand voicing)
    'Gmaj7': (43, [59, 62, 66, 69]), 'A': (45, [57, 61, 64, 69]), 'F#m7': (42, [57, 61, 64, 66]),
    'Bm7': (47, [57, 62, 66, 69]), 'Em7': (40, [55, 59, 62, 66]), 'Asus4': (45, [57, 62, 64, 69]),
    'Dadd9': (38, [57, 62, 64, 66, 69]),
}
MELODY = {  # bar -> [(beat in bar, midi, beats)]
    2: [(0, 73, 1.5), (1.5, 71, .5), (2, 69, 1), (3, 71, 1)],
    3: [(0, 74, 1.5), (1.5, 73, .5), (2, 69, 2)],
    4: [(0, 71, 1), (1, 74, 1), (2, 78, 1.5), (3.5, 76, .5)],
    5: [(0, 76, 1.5), (1.5, 73, .5), (2, 69, 2)],
    6: [(0, 73, 1), (1, 76, 1), (2, 81, 1.5), (3.5, 78, .5)],
    7: [(0, 78, 2), (2, 74, 1), (3, 76, 1)],
    8: [(0, 79, 2), (2, 78, 2)],
    9: [(0, 76, 1.5), (1.5, 73, .5), (2, 69, 2)],
    10: [(0, 83, 1), (1, 81, .5), (1.5, 78, .5), (2, 81, 1.5), (3.5, 83, .5)],
    11: [(0, 86, 2)],
    12: [(0, 78, 1), (1, 79, 1), (2, 81, 2)],
    13: [(0, 85, 1.5), (1.5, 83, .5), (2, 81, 2)],
    14: [(0, 78, 4)],
}


def bar_of(beat): return int(beat // 4)
def kind_at(beat): return next(k for s0, s1, k in SECTIONS if s0 <= beat < s1)


# ---------------------------------------------------------------- piano part
for bar, name in enumerate(CHORDS):
    root, rh = VOICE[name]; at = bar * 4; kind = kind_at(at)
    if kind == 'intro':                                  # broken chord, pedal down, 8ths rising and falling
        seq = [root - 12, root, rh[0], rh[1], rh[2], rh[3], rh[2], rh[1]]
        for e, m in enumerate(seq):
            place('piano', piano(m, b(4 - e / 2) + .4, .42 + .06 * (e == 0)), b(at + e / 2), .5, (m - 60) / 50, .45)
    elif kind in ('cafe', 'snow'):
        place('piano', piano(root - 12, b(3.8), .5), b(at), .55, -.25, .3)
        for e in range(8):                                # soft arpeggio under the melody
            m = rh[(0, 2, 1, 3, 2, 1, 3, 2)[e]]
            place('piano', piano(m, b(1.2), .32 + .05 * (e % 4 == 0)), b(at + e / 2), .38, (m - 60) / 40, .4)
    elif kind == 'full':
        place('piano', piano(root - 12, b(3.8), .62), b(at), .6, -.25, .3)
        place('piano', piano(root, b(3.8), .5), b(at), .4, -.15, .3)
        for e in range(8):
            m = rh[(0, 1, 2, 3, 2, 3, 1, 2)[e]] + (12 if e in (3, 5) else 0)
            place('piano', piano(m, b(1.3), .36 + .06 * (e % 2 == 0)), b(at + e / 2), .38, (m - 60) / 40, .4)
    elif kind == 'held':                                  # the Asus4 rolled and left hanging
        for j, m in enumerate([root - 12, root] + rh + [rh[-1] + 12]):
            place('piano', piano(m, b(2.2), .45), b(at) + j * .045, .5, (m - 60) / 40, .55)
    elif kind == 'swell':
        for j, m in enumerate([root - 24, root - 12, root] + rh + [rh[1] + 12]):
            place('piano', piano(m, b(4), .7), b(at) + j * .03, .55, (m - 60) / 40, .5)
        for e in (2, 2.5, 3, 3.5):
            m = rh[int(e * 2) % 4] + 12
            place('piano', piano(m, b(.8), .4), b(at + e), .3, .3, .5)
    elif kind == 'end':
        for j, m in enumerate([root - 12, root] + rh + [rh[2] + 12, rh[4] + 12]):
            place('piano', piano(m, 5.0, .5), b(at) + j * .07, .55, (m - 60) / 40, .6)

# the single note on "I..." (the hush)
place('piano', piano(69, 2.2, .38), b(46), .5, 0, .8)

# melody (octave doubled in the swell)
for bar, notes in MELODY.items():
    for st, m, ln in notes:
        at = bar * 4 + st; kind = kind_at(at)
        v = {'cafe': .55, 'snow': .5, 'full': .66, 'held': .55, 'swell': .8, 'end': .55}.get(kind, .55)
        place('piano', piano(m, b(ln) + .3, v), b(at), .62, .1, .45)
        if kind == 'swell': place('piano', piano(m - 12, b(ln) + .3, v - .15), b(at), .4, -.05, .45)

# ---------------------------------------------------------------- strings
for bar, name in enumerate(CHORDS):
    at = bar * 4; kind = kind_at(at)
    root, rh = VOICE[name]
    if at < 20 or kind in ('hush',): continue
    g = {'cafe': .35, 'snow': .45, 'full': .6, 'held': .75, 'swell': 1.0, 'end': .6}[kind]
    d = b(2) if kind == 'held' else b(4) + .2
    for m in [root - 12] + [x + 12 for x in rh[:3]]:
        place('strings', strings_note(m, round(d, 3), .9 if kind != 'swell' else .35), b(at), g * .5, (m - 62) / 40, .5)

# ---------------------------------------------------------------- celesta (snow)
for beat8 in range(28 * 2, 56 * 2):
    at = beat8 / 2; kind = kind_at(at)
    if kind in ('held', 'hush'): continue
    if RNG.random() < (.45 if kind in ('snow', 'swell') else .25):
        _, rh = VOICE[CHORDS[bar_of(at)]]
        m = int(RNG.choice(rh)) + 24
        place('cel', celesta(m), b(at), .22, RNG.uniform(-.6, .6), .7)
for j, m in enumerate([86, 88, 90, 93, 98]):                     # the title sparkle
    place('cel', celesta(m, 2.5), b(56) + .25 + j * .14, .3, -.5 + j * .25, .8)

# ---------------------------------------------------------------- drums and bass
KICKS, SNAPS = drum_hits()
for kb in KICKS:
    place('drums', kick(1.6 if kind_at(kb) == 'swell' else 1.0), b(kb), .85 if kind_at(kb) != 'swell' else 1.0)
for sb in SNAPS:
    place('drums', snap(), b(sb), .5, .05, .35)
for s0, s1, kind in SECTIONS:
    if kind in ('cafe', 'full', 'swell', 'snow'):
        x = s0
        while x < s1:
            off = .08 if (x * 2) % 2 else 0                       # swing the offbeats
            place('drums', shaker(1.0 if x % 1 == 0 else .7), b(x + off), .9 if kind != 'snow' else .6, .35)
            x += .5
    if kind in ('cafe', 'full', 'swell'):
        for bar in range(s0 // 4, s1 // 4):
            root = VOICE[CHORDS[bar]][0] - 12
            place('bass', bass(root, b(2.4)), b(bar * 4), .7)
            place('bass', bass(root + (7 if kind == 'full' else 0), b(1.3)), b(bar * 4 + 2.5), .45)

# ---------------------------------------------------------------- swells into the big cuts, air
for c in BIG:
    if c == 8: place('air', cymbal_swell(1.6), b(c) - 1.6, .35, 0, .4)
place('piano', reverse_swell([62, 66, 69, 74], 1.8), b(32) - 1.8, .5, 0, .5)
place('piano', reverse_swell([59, 62, 66, 69, 74], 2.6), b(48) - 2.6, .55, 0, .6)
place('air', cymbal_swell(2.4), b(48) - 2.4, .45, 0, .5)
place('air', noise(4.0, 5000, 15000) * np.exp(-tt(4.0) * 1.2), b(48), .35, 0, .6)    # soft crash

crackle = np.zeros(N)
idx = RNG.choice(N, size=int(DUR * 14), replace=False); crackle[idx] = RNG.normal(0, 1, len(idx)) ** 3
crackle = filt(crackle, 900, 6000) * .5 + filt(RNG.normal(size=N), 3000, 11000) * .004
place('air', crackle, 0, .25)
tm = np.arange(N) / SR
wind = filt(RNG.normal(size=N), 180, 1300) * (.5 + .5 * np.sin(2 * np.pi * .13 * tm)) * .12
wind *= np.interp(tm, [0, b(27), b(30), b(44), b(46), b(48), b(49), DUR], [0, 0, 1, .7, .25, .25, .8, .6])
place('air', np.stack([wind, np.roll(wind, 2400)], 1), 0, .5)

# ---------------------------------------------------------------- mix
def reverb_ir(rt=3.0):
    t = tt(rt); ir = RNG.normal(size=(len(t), 2)) * np.exp(-t * 6.9 / rt)[:, None]
    ir = filt(ir, 250, 6500)
    for d, g in ((.011, .5), (.019, .4), (.027, .32), (.041, .25)):       # early reflections
        i = int(d * SR); ir[i] += (g, g * .9)
    ir[:int(.008 * SR)] *= 0
    return ir / np.sqrt((ir ** 2).sum() / 2)


ir = reverb_ir()
nfft = 1 << (N + len(ir) - 1).bit_length()
wet = np.stack([np.fft.irfft(np.fft.rfft(BUS['verb'][:, c], nfft) * np.fft.rfft(ir[:, c], nfft), nfft)[:N]
                for c in range(2)], 1)

kenv = np.zeros(N)
for kb in KICKS:
    i = round(b(kb) * SR); seg = np.exp(-tt(.3) * 10); kenv[i:i + len(seg)] = np.maximum(kenv[i:i + len(seg)], seg[:N - i])
duck = (1 - .22 * kenv)[:, None]

mix = (BUS['piano'] * 1.0 + BUS['strings'] * duck * .8 + BUS['cel'] * .9 + BUS['drums'] * .55
       + BUS['bass'].mean(1, keepdims=True).repeat(2, 1) * duck * .38 + BUS['air'] * .8 + wet * .3)
hush = np.interp(tm, [0, b(46) - .05, b(46), b(48) - .02, b(48), DUR], [1, 1, .6, .6, 1, 1])
mix *= hush[:, None]
mix = filt(mix, 28, 15000)
mix -= filt(mix, 20, 140) * .3          # tilt: a little less low end so the piano sits forward
mix *= np.clip((DUR - tm) / 1.2, 0, 1)[:, None]
mix = np.tanh(mix * 1.6) / np.tanh(1.6)
mix *= .92 / max(.92, np.max(np.abs(mix)))
with wave.open(str(HERE / 'score_ff.wav'), 'wb') as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR)
    f.writeframes((mix * 32767).astype('<i2').tobytes())
print(f'score_ff.wav: {DUR:.1f}s, {NB} beats @ {60 / BEAT:.0f} BPM, peak {20 * np.log10(np.max(np.abs(mix))):.2f} dBFS')
