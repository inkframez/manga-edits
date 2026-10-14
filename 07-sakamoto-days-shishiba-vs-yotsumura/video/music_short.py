"""Sakamoto Days Short score: 170 BPM jazz-funk two-step, E minor, 32.4 s, stereo 48 kHz -> score_short.wav.

Everything is synthesized here (no samples, no third-party music):
  drums      two-step break (kick 1 / snare 2 / kick 2-and-a-half / snare 4) with ghost notes, 16th hats, ride
  bass       slap-style riff that follows the chords (Em9 - A13 - Cmaj9 - B7#9), sidechained to the kick
  brass      detuned-saw stabs on every contact in timeline_short.HITS and on the name / title stamps
  rhodes     FM electric piano for the quiet beats (the quote, the passage, "choosing my family", the ending)
  noh        tsuzumi "pon" drum and a breathy flute line for the Noh stage
  fx         swishes into every cut, metal clangs, KRASH, the cloth, the hammer spin, sparks, the final impact
The arrangement follows timeline_short.ACTS; hits, cuts and the 0.7 s breath before the blow come from the same
file the renderer reads.
Usage:  python music_short.py
"""
from pathlib import Path
from functools import lru_cache
import wave
import numpy as np
from timeline_short import BEAT, DUR, NB, CUTS, HITS, b

SR = 48000
N = round(SR * DUR)
RNG = np.random.default_rng(100)
HERE = Path(__file__).resolve().parent
drums = np.zeros((N, 2)); bass_bus = np.zeros((N, 2)); music = np.zeros((N, 2)); fx = np.zeros((N, 2))
S16 = BEAT / 4


def tt(d): return np.arange(max(1, round(d * SR))) / SR
def hz(m): return 440 * 2 ** ((m - 69) / 12)


def place(bus, s, at, gain=1.0, pan=0.0):
    i = round(at * SR)
    if s.ndim == 1: s = np.stack([s * np.sqrt((1 - pan) / 2), s * np.sqrt((1 + pan) / 2)], 1)
    if i < 0: s, i = s[-i:], 0
    n = min(len(s), N - i)
    if n > 0: bus[i:i + n] += s[:n] * gain


def filt(x, lo, hi):
    n = len(x); f = np.fft.rfftfreq(n, 1 / SR)
    h = (1 - np.exp(-(f / max(lo, 1)) ** 4)) * np.exp(-(f / hi) ** 4)
    return np.fft.irfft(np.fft.rfft(x, axis=0) * (h[:, None] if x.ndim == 2 else h), n, axis=0)


def noise(d, lo=20, hi=20000):
    s = filt(RNG.normal(size=max(8, round(d * SR))), lo, hi); return s / max(1e-6, np.std(s)) * .3


def sweep(x, lo, hi, env):
    """Filter-envelope approximation: crossfade a dark and a bright low-passed copy by env (0..1)."""
    return filt(x, 20, lo) + (filt(x, 20, hi) - filt(x, 20, lo)) * env


# ---------------------------------------------------------------- instruments
def kick(p=1.0):
    t = tt(.42); f = 50 + 170 * np.exp(-t * 45)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8)
    return np.tanh(s * 2.4 * p) * .9 + noise(.42, 3000, 10000) * np.exp(-t * 260) * .3


def snare(p=1.0):
    t = tt(.26)
    body = (np.sin(2 * np.pi * 200 * t) + .5 * np.sin(2 * np.pi * 340 * t)) * np.exp(-t * 30)
    return (noise(.26, 1500, 13000) * np.exp(-t * 18) * 1.1 + body * .5) * p


def hat(o=False):
    d = .3 if o else .05; t = tt(d)
    return noise(d, 7500, 19000) * np.exp(-t * (13 if o else 90)) * .5


def ride():
    t = tt(.8)
    s = sum(np.sin(2 * np.pi * f * t + RNG.uniform(0, 6)) for f in (3240, 4410, 5120, 6780)) * .15
    return (s + noise(.8, 5000, 15000) * .5) * np.exp(-t * 5)


def crash(d=1.6):
    t = tt(d); return noise(d, 3000, 17000) * np.exp(-t * 2.6) * 1.2


@lru_cache(maxsize=None)
def slap(m, d=.3, pop=False):
    t = tt(d); f = hz(m)
    saw = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 12))
    s = sweep(saw, 220, 2800 if pop else 1700, np.exp(-t * 22)) * 1.6 + np.sin(2 * np.pi * f * t) * .8
    env = np.minimum(t / .003, 1) * np.exp(-t * (6 if d > .25 else 10)) * np.minimum((d - t) / .02, 1).clip(0, 1)
    click = noise(d, 2000, 8000) * np.exp(-t * 400) * (.8 if pop else .3)
    return np.tanh((s * env + click) * 1.3) * .6


def stab(ms, d=.22, bright=1.0):
    """Brass section stab: detuned saws per note with a fast filter swell."""
    t = tt(d)
    s = np.zeros(len(t))
    for m in ms:
        for det in (-.007, 0, .007):
            ph = 2 * np.pi * hz(m) * (1 + det) * t + RNG.uniform(0, 6)
            s += sum(np.sin(ph * k) / k for k in range(1, 10))
    s /= len(ms) * 3
    s = sweep(s, 450, 450 + 4200 * bright, np.minimum(t / .02, 1) * np.exp(-t * 9))
    env = np.minimum(t / .006, 1) * np.minimum((d - t) / .05, 1).clip(0, 1)
    return np.tanh(s * env * 2.2) * .7


def rhodes(ms, d=1.4):
    t = tt(d); out = np.zeros(len(t))
    for m in ms:
        f = hz(m); ix = 1.6 * np.exp(-t * 6)
        out += np.sin(2 * np.pi * f * t + ix * np.sin(2 * np.pi * f * t)) * np.exp(-t * 2.2)
        out += .25 * np.sin(2 * np.pi * f * 14 * t) * np.exp(-t * 30)       # tine
    trem = 1 + .15 * np.sin(2 * np.pi * 5 * t)
    return out / len(ms) * trem * np.minimum(t / .004, 1)


def tsuzumi(high=True):
    t = tt(.5); f0 = 420 if high else 210
    f = f0 * (1 + .5 * np.exp(-t * 40))
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) + noise(.5, 800, 5000) * np.exp(-t * 80) * .3)


def flute(m, d):
    t = tt(d); f = hz(m) * (1 + .006 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(t / .3, 1))
    tone_ = np.sin(2 * np.pi * np.cumsum(f) / SR) + .2 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    breath = filt(RNG.normal(size=len(t)), hz(m) * .8, hz(m) * 3) * .25
    env = np.minimum(t / .08, 1) * np.minimum((d - t) / .15, 1).clip(0, 1)
    return (tone_ * .6 + breath) * env


def clang(f=900, d=1.0):
    t = tt(d)
    s = sum(np.sin(2 * np.pi * f * r * t + RNG.uniform(0, 6)) * np.exp(-t * (4 + 2.5 * k)) / (k + 1)
            for k, r in enumerate([1, 1.41, 2.03, 2.76, 3.51, 4.62, 5.9]))
    return s * .55 + noise(d, 2500, 16000) * np.exp(-t * 70) * .9


def whoosh(d=.25, lo=600, hi=9000):
    t = tt(d); env = np.sin(np.pi * t / d) ** 2
    return filt(RNG.normal(size=len(t)), lo, hi) * .32 * env


def riser(d):
    t = tt(d); u = t / d; s = np.zeros(len(t))
    for i in range(8):
        a, z = int(i * len(t) / 8), int(min(len(t), (i + 1.6) * len(t) / 8)); lo = 500 * 2 ** (i * .5)
        s[a:z] += filt(RNG.normal(size=z - a), lo, lo * 3) * np.hanning(z - a)
    return s / max(1e-6, np.std(s)) * .22 * u ** 2


def boom(d=3.0):
    t = tt(d)
    sub = np.sin(2 * np.pi * (36 * t + 10 * (1 - np.exp(-t * 15)))) * np.exp(-t * 1.8)
    return np.tanh(sub * 1.8) + noise(d, 100, 12000) * np.exp(-t * 6) * .9


def glass(d=1.0):
    t = tt(d); s = noise(d, 2500, 16000) * np.exp(-t * 7)
    for k in range(18):
        at = RNG.uniform(0, .5); f = RNG.uniform(2500, 7000)
        i = int(at * SR); seg = tt(.12)
        s[i:i + len(seg)] += np.sin(2 * np.pi * f * seg) * np.exp(-seg * 40) * .4
    return s


def spin(d):
    """The thrown hammer: a rotating whoosh (AM at a rising rate) that pans across."""
    t = tt(d); rate = 6 + 14 * t / d
    am = (.5 + .5 * np.sin(2 * np.pi * np.cumsum(rate) / SR)) ** 2
    return filt(RNG.normal(size=len(t)), 400, 7000) * .35 * am * np.minimum(t / .1, 1) * (t / d + .3)


# ---------------------------------------------------------------- harmony
E2 = 40
CHORDS = [  # (bass root midi, voicing for stabs / rhodes)
    (40, [55, 59, 62, 66]),        # Em9   (G B D F#)
    (45, [55, 61, 66, 69]),        # A13   (G C# F# A)
    (36, [55, 59, 64, 67]),        # Cmaj9 (G B E G) over C
    (47, [57, 62, 63, 66]),        # B7#9  (A D D# F#)
]
RIFF = [(0, 0, 3, False), (3, 12, 1, True), (6, 10, 2, False), (8, 0, 2, False), (10, 3, 1, False),
        (11, 5, 1, False), (12, 7, 2, False), (14, 12, 1, True)]   # (16th step, interval, length, pop)


def chord_at(beat): return CHORDS[int(beat // 4) % 4]


def bar_drums(at_b, g=1.0, half=False, ride_on=False, fill=False):
    at = b(at_b)
    if half:
        place(drums, kick(), at, .9 * g); place(drums, snare(), at + b(2), .8 * g)
        for e in range(8): place(drums, hat(), at + b(e / 2), (.3 if e % 2 == 0 else .18) * g, .25)
        return
    place(drums, kick(), at, .95 * g); place(drums, snare(), at + b(1), .85 * g)
    place(drums, kick(.85), at + b(2.5), .8 * g); place(drums, snare(), at + b(3), .85 * g)
    for gs in (1.75, 3.5): place(drums, snare(.3), at + b(gs), .22 * g, -.3)
    for e in range(16):
        acc = .34 if e % 4 == 0 else (.24 if e % 2 == 0 else .14)
        place(drums, hat(), at + e * S16, acc * g, .3 if e % 2 else -.1)
    place(drums, hat(True), at + b(3.5), .25 * g, .35)
    if ride_on:
        for q in range(4): place(drums, ride(), at + b(q), .2 * g, -.4)
    if fill:
        for k in range(6): place(drums, snare(.5 + k * .1), at + b(2.5) + k * S16, .25 + .07 * k, -.4 + .15 * k)


def bar_bass(at_b, g=1.0, sparse=False):
    root, _ = chord_at(at_b)
    for st, iv, ln, pop in RIFF:
        if sparse and st not in (0, 8, 12): continue
        place(bass_bus, slap(root + iv, ln * S16 + .05, pop), b(at_b) + st * S16, .75 * g, -.05)


# ---------------------------------------------------------------- arrangement
# 0-4: versus card. Stab on each stamp, a snare roll that builds, riser into the drop.
for at_b, g in [(0, 1.0), (1.5, .8), (2.2, 1.0), (3, .9)]:
    place(music, stab([52] + CHORDS[0][1], .26), b(at_b), .55 * g)
place(drums, crash(), 0, .5); place(drums, kick(), 0, .9)
for k in range(16):
    place(drums, snare(.35 + .04 * k), b(2) + k * S16 / 2, .12 + .03 * k, (-1) ** k * .2)
bar_bass(0, .55)
place(fx, riser(b(1.5)), b(2.5), .8)
place(fx, whoosh(.35), b(4) - .33, .6)

# 4-20: groove A
for at_b in range(4, 20, 4):
    bar_drums(at_b, fill=(at_b in (12,)))
    bar_bass(at_b, 1.0)
    root, ch = chord_at(at_b)
    place(music, stab(ch, .14, .7), b(at_b + 3.5), .3, .3)
place(drums, crash(), b(4), .45)
# the shaft: bass slides down, falling whoosh
t = tt(b(4)); place(bass_bus, np.sin(2 * np.pi * np.cumsum(hz(52) * 2 ** (-2 * t / t[-1])) / SR) * .35 * np.exp(-t * .4), b(10), .6)
place(fx, whoosh(b(3.5), 200, 5000)[::-1], b(10), .4)
# 18-20: the quote - drums thin out, rhodes
for k in range(2): place(music, rhodes(CHORDS[k][1], b(2) + .3), b(16 + 2 * k), .2)

# 20-24: the passage - half time, filtered bass, rhodes
bar_drums(20, .75, half=True)
for at_b in (20, 22):
    root, ch = chord_at(at_b)
    place(bass_bus, slap(root, b(1.8), False), b(at_b), .7)
    place(music, rhodes([c - 12 for c in ch] + ch[:2], b(2) + .4), b(at_b), .32)
for k in range(8): place(drums, hat(), b(22 + k / 2), .16, .3)
place(fx, riser(b(2)), b(22), .6)

# 24-28: SHING, groove back
for at_b in (24,):
    bar_drums(at_b); bar_bass(at_b)
place(drums, crash(), b(24), .4)

# 28-36: the clash - harder groove with ride and extra kicks
for at_b in range(28, 36, 4):
    bar_drums(at_b, 1.1, ride_on=True, fill=at_b == 32); bar_bass(at_b, 1.1)
    place(drums, kick(.9), b(at_b + 1.5), .5)

# 36-38: the Noh stage - drums out, tsuzumi and flute
for at_b, hi in [(36, True), (36.75, False), (37.25, True), (37.75, True)]:
    place(music, tsuzumi(hi), b(at_b), .5, -.3 if hi else .2)
place(music, flute(76, b(1.0)), b(36.1), .22, .2); place(music, flute(74, b(.9)), b(37.1), .22, .2)
place(music, rhodes([52, 59, 62, 66], b(2)), b(36), .18)

# 38-56: KRASH, groove A' with tsuzumi accents; 54-56 drops for the dialogue
place(fx, glass(1.2), b(38), .8, .2); place(drums, crash(), b(38), .55)
for at_b in range(38, 54, 4):
    bar_drums(at_b, 1.0, fill=at_b == 50); bar_bass(at_b)
    place(music, tsuzumi(True), b(at_b + 1.5), .3, -.4); place(music, tsuzumi(False), b(at_b + 3.75), .3, .4)
place(fx, whoosh(.5, 300, 6000), b(48), .6, -.4)     # the cloth (SHFF)
for at_b in (54,):
    root, ch = chord_at(at_b)
    place(music, rhodes(ch, b(2) + .4), b(at_b), .32); place(bass_bus, slap(root, b(1.5)), b(at_b), .6)
    for k in range(8): place(drums, hat(), b(at_b + k / 4), .12, .3)

# 56-60: the mirror - groove under a low-pass, glint shimmer
_saved = drums.copy(); drums[:] = 0
bar_drums(56, .9)
seg = drums[round(b(56) * SR):round(b(60) * SR)].copy(); drums[:] = _saved
seg = filt(seg, 20, 900)
place(drums, seg, b(56), 1.0)
bar_bass(56, .8)
for k, m in enumerate([88, 91, 95, 98, 100, 103]):
    place(music, rhodes([m], .6), b(56.6) + k * .07, .12, -.6 + .24 * k)
place(music, stab(CHORDS[3][1], .2), b(58), .4)

# 60-64: the hammer flies - spin, snare roll crescendo, riser
place(fx, spin(b(4)), b(60), .9)
place(music, stab(CHORDS[0][1] + [64], .3), b(60), .5)
for k in range(16): place(drums, snare(.4 + .04 * k), b(62) + k * S16 / 2, .1 + .035 * k, (-1) ** k * .3)
place(fx, riser(b(4)), b(60), .8)
place(bass_bus, slap(40, b(2)), b(60), .7)

# 64-66: the breath - near silence, one heartbeat, an inhale
place(drums, kick(.5), b(64.6), .35)
place(fx, noise(.45, 700, 6000) * np.linspace(0, 1, round(.45 * SR)) ** 3, b(66) - .45, .5)

# 66-74: the blow - boom, full brass, heavy half-time
place(fx, boom(3.0), b(66), 1.0); place(drums, crash(2.4), b(66), .7)
place(fx, clang(700, 2.0), b(66), .6, -.1)
place(music, stab([40, 52] + CHORDS[0][1] + [71], .9, 1.2), b(66), .75)
for at_b in (68, 70, 72):
    bar_drums(at_b, 1.0, half=True)
for at_b, ch in [(68, CHORDS[2][1]), (70, CHORDS[3][1]), (72, CHORDS[0][1])]:
    place(music, stab(ch, .4, .9), b(at_b), .5)
    root = {68: 36, 70: 47, 72: 40}[at_b]; place(bass_bus, slap(root, b(1.9), True), b(at_b), .75)

# 74-80: "...a reason to kill you" - rhodes, soft bass, ride
for at_b in (74, 76, 78):
    root, ch = chord_at(at_b - 2)
    place(music, rhodes(ch, b(2) + .5), b(at_b), .34); place(bass_bus, slap(root, b(1.8)), b(at_b), .5)
    for q in range(4): place(drums, ride(), b(at_b + q / 2), .1, -.4)

# 80-90: title - stab sequence, last groove bar, final chord rings
for at_b, g in [(80, 1), (80.6, .8), (81, 1)]:
    place(music, stab(CHORDS[0][1] + [64], .26), b(at_b), .55 * g)
bar_drums(80, 1.0); bar_drums(84, .8, fill=True); bar_bass(80); bar_bass(84, .8)
place(drums, crash(2.4), b(88), .6); place(drums, kick(), b(88), .9)
place(music, stab([40, 52] + CHORDS[0][1] + [71], 1.6, .8), b(88), .6)
place(music, rhodes([64, 67, 71, 74, 78], 3.0), b(88), .3)

# ---------------------------------------------------------------- swishes into cuts, contacts
for j, c in enumerate(CUTS):
    if c in (64, 66, 36, 74): continue
    place(fx, whoosh(.22), b(c) - .2, .45, (-1) ** j * .6)
for hb, st in HITS:
    place(fx, clang(800 + 140 * (hb % 5), .6 + .3 * st), b(hb), .22 + .1 * st, (-1) ** int(hb * 2) * .3)
    if st >= 2: place(drums, kick(1.1), b(hb), .5 + .15 * st)
    if st >= 2 and hb not in (66,): place(music, stab(chord_at(hb)[1], .18), b(hb), .3 + .08 * st)
    place(fx, np.sin(2 * np.pi * 45 * tt(.4)) * np.exp(-tt(.4) * 8), b(hb), .25 * st)

# ---------------------------------------------------------------- mix
# sidechain: the kick pumps the bass and the music slightly
env = np.abs(drums[:, 0]) ; env = np.convolve(env, np.ones(480) / 480, 'same')
duck = 1 - .45 * np.clip(env / (env.max() + 1e-9) * 4, 0, 1)
mix = drums * .9 + bass_bus * duck[:, None] * .72 + music * (1 - (1 - duck[:, None]) * .5) * 1.3 + fx
tm = np.arange(N) / SR
gate = np.interp(tm, [0, b(64), b(64) + .05, b(66) - .5, b(66), DUR - .8, DUR], [1, 1, .06, .06, 1, 1, 0])
mix *= gate[:, None]
for delay, gain in [(.029, .09), (.071, .06), (.13, .04)]:
    n = round(delay * SR); mix[n:] += mix[:-n, ::-1] * gain
mix = np.tanh(mix * 1.05)
mix *= .93 / max(.93, np.max(np.abs(mix)))
with wave.open(str(HERE / 'score_short.wav'), 'wb') as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR)
    f.writeframes((mix * 32767).astype('<i2').tobytes())
print(f'score_short.wav: {DUR:.2f}s, {NB} beats @ {60 / BEAT:.0f} BPM, peak {20 * np.log10(np.max(np.abs(mix))):.2f} dBFS')
