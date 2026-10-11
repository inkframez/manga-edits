"""Kagurabachi v2 score: 160 BPM, D minor / miyako-bushi (D Eb G A Bb), 33.5 s, stereo 48 kHz -> score_v2.wav.

Everything is synthesized here (no samples): a ticking clock that becomes the hi-hat, Karplus-Strong shamisen
plucks, a detuned reese bass, a saw pad, taiko, a d&b break, and the sword / lightning / impact sound design.
The arrangement follows timeline_v2.ACTS, and the cut swishes and hits follow CUTS / HITS, so the render and the
score share one map.
Usage:  python music_v2.py
"""
from pathlib import Path
import wave
import numpy as np
from timeline_v2 import BEAT, DUR, NB, CUTS, HITS, GLITCH, SURGES, b

SR = 48000
N = round(SR * DUR)
RNG = np.random.default_rng(1717)
HERE = Path(__file__).resolve().parent
music = np.zeros((N, 2))
drums = np.zeros((N, 2))
fx = np.zeros((N, 2))


def tt(d): return np.arange(round(d * SR)) / SR
def hz(m): return 440 * 2 ** ((m - 69) / 12)


def place(bus, s, at, gain=1.0, pan=0.0):
    i = round(at * SR)
    if s.ndim == 1: s = np.stack([s * np.sqrt((1 - pan) / 2), s * np.sqrt((1 + pan) / 2)], 1)
    if i < 0: s, i = s[-i:], 0
    n = min(len(s), N - i)
    if n > 0: bus[i:i + n] += s[:n] * gain


def band(x, lo, hi):
    """Zero-phase FFT band-pass with soft (4th-order-ish) edges."""
    n = len(x); f = np.fft.rfftfreq(n, 1 / SR)
    h = (1 - np.exp(-(f / max(lo, 1)) ** 4)) * np.exp(-(f / hi) ** 4)
    return np.fft.irfft(np.fft.rfft(x, axis=0) * (h[:, None] if x.ndim == 2 else h), n, axis=0)


def noise(d, lo=20, hi=20000):
    s = band(RNG.normal(size=round(d * SR)), lo, hi)
    return s / max(1e-6, np.std(s)) * .3


# ---------------------------------------------------------------- instruments
def kick(p=1.0):
    t = tt(.45); f = 46 + 150 * np.exp(-t * 42)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    return np.tanh(s * 2.2 * p) * .85 + noise(.45, 2500, 9000) * np.exp(-t * 220) * .25


def snare():
    t = tt(.3)
    return (noise(.3, 1100, 12000) * np.exp(-t * 20) +
            (np.sin(2 * np.pi * 185 * t) + .5 * np.sin(2 * np.pi * 330 * t)) * np.exp(-t * 34) * .45)


def hat(open_=False):
    d = .32 if open_ else .07; t = tt(d)
    return noise(d, 7000, 18000) * np.exp(-t * (14 if open_ else 70)) * .45


def tick(hi=True):
    """Clock escapement: a woodblock-ish click; 'tock' is lower. Becomes the hat in the duel."""
    t = tt(.09); f = 2650 if hi else 1780
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 90) * .8 + noise(.09, 3000, 14000) * np.exp(-t * 260) * .6)


def taiko(f=72, d=.9):
    t = tt(d); ph = 2 * np.pi * f * t + 5 * (1 - np.exp(-t * 26))
    return ((np.sin(ph) + .35 * np.sin(1.6 * ph)) * np.exp(-t * 6) +
            noise(d, 120, 1500) * np.exp(-t * 32) * .35)


def pluck(m, d=.9, bright=.5):
    """Karplus-Strong (vectorised per period) -> a dry shamisen-like pluck with a hard 'bachi' attack."""
    n = round(d * SR); p = max(2, round(SR / hz(m)))
    y = np.zeros(n + p)
    y[:p] = RNG.uniform(-1, 1, p) * np.linspace(1, .2, p)
    k = .496 + .003 * bright
    for i in range(p, n + p, p):
        j = min(i + p, n + p)
        prev = y[i - p:j - p]; prev1 = y[i - p - 1:j - p - 1] if i - p - 1 >= 0 else np.r_[0, prev[:-1]]
        y[i:j] = k * (prev + prev1[:len(prev)])
    s = y[p:]; t = tt(d)
    s = s / max(1e-6, np.max(np.abs(s)))
    return np.tanh(s * 1.6) * np.exp(-t * 2.2) + noise(d, 2500, 9000) * np.exp(-t * 300) * .4


def reese(m, d, cut=900):
    t = tt(d); f = hz(m)
    s = sum(np.sin(2 * np.pi * f * k * t * (1 + det) + RNG.uniform(0, 6)) / k
            for k in range(1, 9) for det in (-.006, .006))
    s = band(np.tanh(s * .9), 25, cut) + np.sin(2 * np.pi * f * t) * .7
    env = np.minimum(t / .01, 1) * np.minimum((d - t) / .05, 1).clip(0, 1)
    return s * env * .5


def pad(ms, d, cut=2400):
    t = tt(d)
    s = sum(np.sin(2 * np.pi * hz(m) * k * t * (1 + det) + RNG.uniform(0, 6)) / k
            for m in ms for k in range(1, 7) for det in (-.004, 0, .004))
    s = band(s, 80, cut) / (len(ms) * 3)
    env = np.minimum(t / .35, 1) * np.minimum((d - t) / .4, 1).clip(0, 1)
    return s * env


def bell(m, d=1.2):
    t = tt(d); p = 2 * np.pi * hz(m) * t
    return (np.sin(p + 1.3 * np.sin(p * 3.5) * np.exp(-t * 6)) * np.exp(-t * 3.5) * np.minimum(t / .002, 1))


def metal(f=1200, d=.6):
    t = tt(d)
    s = sum(np.sin(2 * np.pi * f * r * t + RNG.uniform(0, 6)) * np.exp(-t * (5 + 3 * k)) / (k + 1)
            for k, r in enumerate([1, 1.483, 2.174, 2.91, 4.03, 5.2]))
    return s * .6 + noise(d, 2000, 15000) * np.exp(-t * 90) * .7


def whoosh(d=.22, up=True):
    t = tt(d); env = np.sin(np.pi * t / d) ** 2
    s = band(RNG.normal(size=len(t)), 500, 9000) * .3 * env
    return s if up else s[::-1]


def electric(d=.5):
    t = tt(d)
    gate = (np.sin(2 * np.pi * 47 * t + 1.2 * np.sin(2 * np.pi * 13 * t)) > .7).astype(float)
    return noise(d, 1800, 13000) * gate * np.exp(-t * 3.5) + np.sin(2 * np.pi * 98 * t) * np.exp(-t * 8) * .2


def riser(d):
    t = tt(d); u = t / d
    s = np.zeros(len(t))
    for i in range(8):     # band sweeps upward in eight overlapping slices
        a, z = int(i * len(t) / 8), int(min(len(t), (i + 1.6) * len(t) / 8))
        lo = 400 * 2 ** (i * .55)
        s[a:z] += band(RNG.normal(size=z - a), lo, lo * 3) * np.hanning(z - a)
    return s / max(1e-6, np.std(s)) * .25 * u ** 2


def reverse_cymbal(d):
    t = tt(d); return (noise(d, 3500, 16000) * np.exp(-t * 4))[::-1]


def boom(d=3.0):
    t = tt(d)
    sub = np.sin(2 * np.pi * (34 * t + 9 * (1 - np.exp(-t * 14)))) * np.exp(-t * 1.7)
    return np.tanh(sub * 1.6) + noise(d, 120, 12000) * np.exp(-t * 6) * .9


K, S, HH, OH = kick(), snare(), hat(), hat(True)
D2, F2, G2, A2, Bb2 = 38, 41, 43, 45, 46
# miyako-bushi on D: D Eb G A Bb (+ C for the cadence)
SCALE = [62, 63, 67, 69, 70, 74, 75, 79]

# ---------------------------------------------------------------- 0-8: the clock
for k in range(8):
    place(fx, tick(k % 2 == 0), b(k), .5 if k < 4 else .4, -.3 if k % 2 else .3)
for k in range(8, 16):
    place(fx, tick(True), b(k / 2), .22, .5)            # 8ths creep in under the castle band
place(music, np.sin(2 * np.pi * 36.7 * tt(3)) * np.minimum(tt(3) / 2.5, 1) * .35, 0)
place(fx, reverse_cymbal(1.2), b(4) - 1.2, .55)
for at, g in [(4, .9), (6, .6), (7, .55), (7.5, .5)]:
    place(drums, taiko(70), b(at), g)
place(music, pad([62, 65, 69], b(4) + .3), b(4), .55)
for i, (st, n) in enumerate([(4, 62), (5, 63), (5.5, 62), (6.5, 69), (7, 70)]):
    place(music, pluck(n), b(st), .5, -.25 + .12 * i)
place(fx, riser(b(2)), b(6), .7)

# ---------------------------------------------------------------- break patterns
def bar_dnb(at, g=1.0, fill=False):
    place(drums, K, at, .9 * g); place(drums, S, at + b(1), .7 * g)
    place(drums, K, at + b(2.5), .75 * g); place(drums, S, at + b(3), .7 * g)
    place(drums, S, at + b(3.75), .18 * g, .3)
    for e in range(8):
        place(drums, HH, at + b(e / 2), (.42 if e % 2 == 0 else .26) * g, -.25 if e % 2 else .25)
    if fill:
        for k in range(4): place(drums, S, at + b(3 + k / 4), (.2 + k * .1) * g, -.3 + .2 * k)


def bar_half(at, g=1.0):
    place(drums, K, at, .9 * g); place(drums, S, at + b(2), .75 * g)
    place(drums, tick(True), at + b(1), .3, .4); place(drums, tick(False), at + b(3), .3, -.4)
    place(drums, OH, at + b(3.5), .25 * g)


PROG = [(D2, [62, 65, 69]), (Bb2 - 12, [62, 65, 70]), (G2 - 12, [62, 67, 70]), (A2 - 12, [61, 64, 69])]
MOTIF = [0, 1, 0, 3, 2, 3, 4, 3]          # indices into SCALE
for bar, at_b in enumerate(range(8, 32, 4)):
    at = b(at_b)
    bar_dnb(at, 1.0, fill=(at_b + 4) % 8 == 0)
    root, chord = PROG[bar % 4]
    place(music, reese(root, b(3.7)), at, .7)
    place(music, pad(chord, b(4) + .2), at, .32)
    for e, idx in enumerate(MOTIF):
        if e in (2, 6) and bar % 2: continue
        place(music, pluck(SCALE[idx] + (12 if bar >= 4 and e % 4 == 0 else 0), .6), at + b(e / 2), .32,
              -.4 if e % 2 else .4)

# ---------------------------------------------------------------- 32-40: all in (half time, tension)
for at_b in (32, 36):
    bar_half(b(at_b))
    place(music, reese(D2 - 12 if at_b == 32 else 39 - 12, b(4)), b(at_b), .8)     # D -> Eb: the 2x surge
    place(music, pad([62, 65, 69] if at_b == 32 else [63, 67, 70], b(4) + .2, 1600), b(at_b), .45)
for at_b in (32, 34, 36, 38): place(drums, taiko(64), b(at_b), .55)
place(fx, riser(b(4)), b(36), .9)
for k in range(6): place(fx, electric(.4), b(36 + k * .66), .35, (-1) ** k * .5)
for k in range(4): place(music, pluck(SCALE[[5, 4, 3, 1][k]], 1.2), b(32 + k), .35, (-1) ** k * .3)

# ---------------------------------------------------------------- 40-56: Nishiki (double-time energy)
for bar, at_b in enumerate(range(40, 56, 4)):
    at = b(at_b)
    bar_dnb(at, 1.1, fill=at_b in (44, 52))
    for e in range(16): place(drums, HH, at + b(e / 4), .14, .4 if e % 2 else -.4)
    root, chord = PROG[bar % 4]
    place(music, reese(root, b(3.7), 1300), at, .75)
    place(music, pad([c + 12 for c in chord], b(4) + .2, 3500), at, .3)
    for e in range(8):
        idx = MOTIF[(e + bar * 3) % 8] + (2 if e % 4 == 3 else 0)
        place(music, pluck(SCALE[min(idx, 7)] + 12, .5, .9), at + b(e / 2), .26, -.45 if e % 2 else .45)
for at_b in (40, 48): place(music, bell(74, 2.0), b(at_b), .25)
place(fx, electric(.9), b(40), .6, -.3); place(fx, electric(.9), b(40) + .05, .5, .4)

# ---------------------------------------------------------------- 56-62: drain (Nishiki released, Kuro)
place(fx, whoosh(.7, up=False), b(56) - .1, .7, -.3)
place(fx, metal(2400, 1.4), b(56), .3, .3)
for k in range(3): place(drums, kick(.6), b(56 + 2 * k), .6 - .15 * k)               # heartbeat
for k in range(3): place(drums, kick(.4), b(56.4 + 2 * k), .35 - .1 * k)
place(music, reese(D2, b(6), 400), b(56), .55)
place(music, pad([62, 65, 69], b(6), 900), b(56), .4)
place(music, pluck(62, 2.0), b(58), .45)                                              # 'Kuro.'
place(fx, riser(b(3)), b(59), .3)

# ---------------------------------------------------------------- 62-64: vacuum
t = tt(b(2))
place(fx, np.sin(2 * np.pi * 6200 * t) * np.minimum(t / .1, 1) * .05, b(62))         # tinnitus
place(drums, kick(.5), b(62.6), .35)
place(fx, noise(b(1), 600, 5000) * np.linspace(0, 1, round(b(1) * SR)) ** 3, b(63), .5)   # inhale
place(fx, whoosh(.16), b(64) - .16, .9, -.5)

# ---------------------------------------------------------------- 64-72: impact
place(fx, boom(3.2), b(64), 1.0)
place(fx, metal(760, 2.4), b(64), .55, -.1)
for k in range(8): place(fx, metal(1900 + k * 330, .5), b(64) + .1 + k * .07, .08, (-1) ** k * .7)
for at_b in range(64, 72, 2):
    for o, g in [(0, .95), (.75, .5), (1.5, .65)]: place(drums, taiko(66), b(at_b + o), g, (-1) ** int(o * 4) * .2)
    place(drums, S, b(at_b + 1), .55)
    for e in range(4): place(drums, HH, b(at_b + e / 2), .25, .3)
place(music, reese(D2 - 12, b(8), 500), b(64), .8)
place(music, pad([50, 57, 62, 65, 69], b(8), 2800), b(64), .6)
for k, n in enumerate([74, 75, 79, 74, 70, 69]):
    place(music, pluck(n, 1.0), b(64 + k * 1.33), .38, (-1) ** k * .3)
# blade break: a shatter of short pings over a high ring
place(fx, metal(1750, 2.0), b(70), .45, .35)
for k in range(14): place(fx, metal(2600 + RNG.uniform(-800, 1600), .3), b(70) + k * .035, .07, RNG.uniform(-.8, .8))
place(fx, noise(.6, 4000, 16000) * np.exp(-tt(.6) * 7), b(70), .35)

# ---------------------------------------------------------------- 72-89: aftermath + end card
for at_b in (72, 76): place(drums, taiko(62, 1.4), b(at_b), .6)
place(music, pad([62, 65, 70], b(9), 1600), b(72), .45)
place(music, reese(Bb2 - 12, b(9), 500), b(72), .45)
for k, n in enumerate([70, 69, 67, 63, 62]):
    place(music, pluck(n, 1.4), b(72 + k * 1.5), .34, (-1) ** k * .35)
place(fx, whoosh(.2), b(75) - .2, .4, .4)
place(fx, whoosh(.2), b(78) - .2, .4, -.4)
# final: taiko + sub + bell chord, then ring out
place(drums, taiko(56, 2.0), b(81), .95)
place(fx, boom(2.6) * .6, b(81), .7)
for m in [50, 62, 69, 74, 77]: place(music, bell(m, 3.2), b(81), .17, (m - 66) / 18)
place(music, pad([50, 57, 62, 65], DUR - b(81), 1200), b(81), .45)

# ---------------------------------------------------------------- cut swishes + hits
for j, c in enumerate(CUTS):
    if c in (62, 64, 81): continue
    place(fx, whoosh(.2), b(c) - .19, .42, (-1) ** j * .6)
    place(fx, metal(1000 + (j % 5) * 230, .35), b(c), .12, (-1) ** (j + 1) * .4)
for h in HITS:
    if h in (64, 70): continue
    place(drums, taiko(60, 1.0), b(h), .6)
    place(fx, np.sin(2 * np.pi * 42 * tt(.5)) * np.exp(-tt(.5) * 7), b(h), .5)
place(fx, electric(.7), b(SURGES['sojo_2x']), .45, .4)

# ---------------------------------------------------------------- mix
mix = music * .9 + drums * .85 + fx
# glitch: the clock snaps 06:00 -> 03:00 - stutter a 1/16 slice four times
g0 = round(b(GLITCH) * SR); sl = round(b(.25) * SR)
seg = mix[g0 - sl:g0].copy()
for k in range(4): mix[g0 - sl + k * sl // 2: g0 - sl + k * sl // 2 + sl] = seg * (1 - .15 * k)
# ducking envelope: drain / vacuum / tail
tm = np.arange(N) / SR
duck = np.interp(tm, [0, b(56), b(56) + .3, b(62) - .05, b(62), b(64) - .02, b(64), DUR - .6, DUR],
                 [1, 1, .75, .65, .12, .12, 1, 1, 0])
mix *= duck[:, None]
# short stereo room
for delay, gain in [(.031, .10), (.077, .07), (.143, .05)]:
    n = round(delay * SR); mix[n:] += mix[:-n, ::-1] * gain
mix = np.tanh(mix * 1.1)
mix *= .93 / max(.93, np.max(np.abs(mix)))
with wave.open(str(HERE / 'score_v2.wav'), 'wb') as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR)
    f.writeframes((mix * 32767).astype('<i2').tobytes())
print(f'score_v2.wav: {DUR:.2f}s, {NB} beats @ {60 / BEAT:.0f} BPM, peak {20 * np.log10(np.max(np.abs(mix))):.2f} dBFS')
