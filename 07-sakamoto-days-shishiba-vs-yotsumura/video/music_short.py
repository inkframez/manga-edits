"""Sakamoto Days Short score: phonk at 170 BPM in E phrygian, 32.4 s, stereo 48 kHz -> score_short.wav.

Phonk is the house sound of manga / anime edits: an 808 cowbell hook, a distorted 808 that glides between notes,
a clap backbeat, rolling hats, dark pads and a lot of reverb. Everything here is synthesized (no samples, no
third-party music):
  cowbell    two band-limited square oscillators a fifth-ish apart (the TR-808 recipe), pitched to the hook
  808        sine with a pitch punch, glides, hard saturation, a click on the attack
  drums      layered clap, 808-style metallic hats with trap rolls, snare rolls for the builds, crash
  pad        dark detuned-saw "choir" through vowel formants, for the breaks
  noh        tsuzumi "pon" and a breathy flute for the Noh stage
  fx         swishes into cuts, clangs on contacts, KRASH, the hammer spin, the final boom
The drum pattern comes from timeline_short.SECTIONS / PATTERNS (drum_hits), the same map the renderer uses for
its beat pulses, so every kick you hear is a zoom bump you see.
Usage:  python music_short.py
"""
from pathlib import Path
from functools import lru_cache
import wave
import numpy as np
from timeline_short import BEAT, DUR, NB, CUTS, HITS, SECTIONS, drum_hits, b

SR = 48000
N = round(SR * DUR)
RNG = np.random.default_rng(170)
HERE = Path(__file__).resolve().parent
BUS = {k: np.zeros((N, 2)) for k in ('drums', 'bass', 'bell', 'pad', 'fx', 'verb')}
S16 = BEAT / 4


def tt(d): return np.arange(max(1, round(d * SR))) / SR
def hz(m): return 440 * 2 ** ((m - 69) / 12)


def place(bus, s, at, gain=1.0, pan=0.0, send=0.0):
    i = round(at * SR)
    if s.ndim == 1: s = np.stack([s * np.sqrt((1 - pan) / 2), s * np.sqrt((1 + pan) / 2)], 1)
    if i < 0: s, i = s[-i:], 0
    n = min(len(s), N - i)
    if n <= 0: return
    BUS[bus][i:i + n] += s[:n] * gain
    if send: BUS['verb'][i:i + n] += s[:n] * gain * send


def filt(x, lo, hi):
    n = len(x); f = np.fft.rfftfreq(n, 1 / SR)
    h = (1 - np.exp(-(f / max(lo, 1)) ** 4)) * np.exp(-(f / hi) ** 4)
    return np.fft.irfft(np.fft.rfft(x, axis=0) * (h[:, None] if x.ndim == 2 else h), n, axis=0)


def noise(d, lo=20, hi=20000):
    s = filt(RNG.normal(size=max(16, round(d * SR))), lo, hi); return s / max(1e-6, np.std(s)) * .3


def square(f, t, kmax=11):
    """Band-limited square (odd harmonics below 18 kHz)."""
    out = np.zeros(len(t))
    for k in range(1, kmax + 1, 2):
        if f * k > 18000: break
        out += np.sin(2 * np.pi * f * k * t) / k
    return out


# ---------------------------------------------------------------- instruments
@lru_cache(maxsize=None)
def cowbell(m, d=.32, bright=1.0):
    t = tt(d); f = hz(m)
    s = square(f, t) * .6 + square(f * 1.4818, t) * .45
    s = filt(s, 380, 2800 + 3000 * bright)
    env = np.minimum(t / .0015, 1) * (.65 * np.exp(-t * 34) + .35 * np.exp(-t * 7.5))
    return np.tanh(s * env * 2.0) * .55


@lru_cache(maxsize=None)
def bass808(m, d, m2=None, punch=True, drive=3.2):
    """808: pitch punch on the attack, optional glide to m2 over the last 40 % of the note, hard saturation."""
    t = tt(d); f0 = hz(m)
    f = np.full(len(t), f0)
    if punch: f *= 1 + 1.6 * np.exp(-t * 45)
    if m2 is not None:
        g = np.clip((t - d * .6) / (d * .4), 0, 1); f *= 2 ** ((m2 - m) / 12 * (g * g * (3 - 2 * g)))
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) + .25 * np.sin(2 * ph)
    env = np.minimum(t / .002, 1) * (.55 * np.exp(-t * 7) + .45 * np.exp(-t * 1.6)) * np.clip((d - t) / .03, 0, 1)
    s = np.tanh(s * env * drive) / np.tanh(drive)
    s = filt(s, 25, 3800) * .9
    click = noise(d, 1500, 9000) * np.exp(-t * 350) * .5
    return s + click


@lru_cache(maxsize=None)
def kick():
    t = tt(.3); f = 55 + 190 * np.exp(-t * 55)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16)
    return np.tanh(s * 2.5) * .9 + noise(.3, 2500, 9000) * np.exp(-t * 300) * .35


@lru_cache(maxsize=None)
def clap():
    t = tt(.45); s = np.zeros(len(t))
    for k, off in enumerate((0, .009, .019, .031)):
        i = int(off * SR); seg = noise(.45 - off, 900, 7000) * np.exp(-tt(.45 - off) * (140 if k < 3 else 16))
        s[i:i + len(seg)] += seg * (1.0 if k < 3 else .9)
    return s * 1.1


@lru_cache(maxsize=None)
def hat(open_=False):
    d = .35 if open_ else .06; t = tt(d)
    s = sum(square(f, t, 5) for f in (205.3, 304.4, 369.6, 522.7, 540.0, 800.0))
    s = filt(s, 7000, 16000) / 3 + noise(d, 8000, 17000) * .4
    return s * np.exp(-t * (11 if open_ else 75)) * .7


@lru_cache(maxsize=None)
def snare(p=1.0):
    t = tt(.2)
    return (noise(.2, 1500, 12000) * np.exp(-t * 26) + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 35) * .5) * p


def crash(d=2.0):
    t = tt(d); return noise(d, 3500, 16000) * np.exp(-t * 2.2) * 1.0


def pad(ms, d, cut=1600):
    t = tt(d); s = np.zeros(len(t))
    for m in ms:
        for det in (-.006, -.002, .002, .006):
            ph = 2 * np.pi * hz(m) * (1 + det) * t + RNG.uniform(0, 6)
            s += sum(np.sin(ph * k) / k for k in range(1, 8))
    s = filt(s, 120, cut) * .6 + filt(s, 650, 900) * .5 + filt(s, 1100, 1300) * .3     # "ah" formants
    s /= len(ms) * 4
    return s * np.minimum(t / .6, 1) * np.clip((d - t) / .5, 0, 1)


def tsuzumi(high=True):
    t = tt(.5); f0 = 420 if high else 210
    f = f0 * (1 + .5 * np.exp(-t * 40))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) + noise(.5, 800, 5000) * np.exp(-t * 80) * .3


def flute(m, d):
    t = tt(d); f = hz(m) * (1 + .006 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(t / .3, 1))
    ph = 2 * np.pi * np.cumsum(f) / SR
    breath = filt(RNG.normal(size=len(t)), hz(m) * .8, hz(m) * 3) * .25
    return (np.sin(ph) * .6 + .12 * np.sin(2 * ph) + breath) * np.minimum(t / .08, 1) * np.clip((d - t) / .15, 0, 1)


def clang(f=1000, d=.7):
    t = tt(d)
    s = sum(np.sin(2 * np.pi * f * r * t + RNG.uniform(0, 6)) * np.exp(-t * (6 + 3 * k)) / (k + 1)
            for k, r in enumerate([1, 1.41, 2.03, 2.76, 3.51, 4.62]))
    return s * .5 + noise(d, 3000, 14000) * np.exp(-t * 120) * .5


def whoosh(d=.25, lo=500, hi=8000):
    t = tt(d); return filt(RNG.normal(size=len(t)), lo, hi) * .3 * np.sin(np.pi * t / d) ** 2


def riser(d):
    t = tt(d); u = t / d; s = np.zeros(len(t))
    for i in range(8):
        a, z = int(i * len(t) / 8), int(min(len(t), (i + 1.6) * len(t) / 8)); lo = 500 * 2 ** (i * .5)
        s[a:z] += filt(RNG.normal(size=z - a), lo, lo * 3) * np.hanning(z - a)
    return s / max(1e-6, np.std(s)) * .2 * u ** 2


def boom(d=3.0):
    t = tt(d)
    sub = np.sin(2 * np.pi * (34 * t + 10 * (1 - np.exp(-t * 15)))) * np.exp(-t * 1.6)
    return np.tanh(sub * 2) + noise(d, 100, 9000) * np.exp(-t * 7) * .7


def glass(d=1.0):
    t = tt(d); s = noise(d, 2500, 14000) * np.exp(-t * 8)
    for _ in range(16):
        i = int(RNG.uniform(0, .45) * SR); seg = tt(.1)
        s[i:i + len(seg)] += np.sin(2 * np.pi * RNG.uniform(2500, 6500) * seg) * np.exp(-seg * 45) * .35
    return s


def spin(d):
    t = tt(d); rate = 6 + 14 * t / d
    am = (.5 + .5 * np.sin(2 * np.pi * np.cumsum(rate) / SR)) ** 2
    return filt(RNG.normal(size=len(t)), 400, 6500) * .3 * am * np.minimum(t / .1, 1) * (t / d + .3)


# ---------------------------------------------------------------- the hook (E phrygian), eighth notes per bar
HOOK = [[76, 0, 76, 79, 0, 76, 77, 76],
        [74, 0, 74, 76, 0, 79, 77, 74],
        [76, 0, 76, 79, 0, 81, 79, 77],
        [76, 74, 72, 74, 76, 0, 0, 0]]
ROOTS = [28, 28, 31, 26]          # 808 roots per bar: E1 E1 G1 D1 (glides into the next)


def bar_hook(at_b, idx, gain=1.0, octave=0, bright=1.0, send=.35):
    for e, m in enumerate(HOOK[idx % 4]):
        if m: place('bell', cowbell(m + 12 * octave, .32, bright), b(at_b + e / 2), .5 * gain, (-.25, .25)[e % 2], send)


def hats(at_b, kind, s1):
    """8ths in a drop with a trap roll at the end of every second bar; 16ths in drop2."""
    bar_i = int(at_b // 4)
    step = .25 if kind == 'drop2' else .5
    x = 0.0
    while x < 4 and at_b + x < s1:
        acc = .32 if x % 1 == 0 else .2
        place('drums', hat(), b(at_b + x), acc, .3 if (x * 2) % 2 else -.15)
        x += step
    if kind == 'drop' and bar_i % 2 == 1 and at_b + 4 <= s1:          # roll: 16th triplets then 32nds
        for k in range(6): place('drums', hat(), b(at_b + 3 + k / 6), .12 + .03 * k, .35)
    if kind == 'drop2': place('drums', hat(True), b(at_b + 3.5), .22, .4)


# ---------------------------------------------------------------- arrangement
KICKS, CLAPS = drum_hits()
for kb in KICKS:
    s0, s1, kind = next(s for s in SECTIONS if s[0] <= kb < s[1])
    bar = int((kb - s0) // 4); root = ROOTS[bar % 4]
    nxt = min([k for k in KICKS if k > kb] + [s1])
    d = min(b(nxt - kb), b(1.5)) + .02
    glide = ROOTS[(bar + 1) % 4] if (kb - s0) % 4 == 2.5 and root != ROOTS[(bar + 1) % 4] else None
    up = 12 if (kb - s0) % 4 == .75 and kind == 'drop' else 0
    place('bass', bass808(root + up, round(d, 4), glide), b(kb), .85)
    place('drums', kick(), b(kb), .75)
for cb in CLAPS:
    place('drums', clap(), b(cb), 1.0, 0, .45)
    place('drums', snare(), b(cb), .22)

for s0, s1, kind in SECTIONS:
    for k, at_b in enumerate(range(s0, s1, 4)):
        if kind in ('drop', 'drop2'):
            hats(at_b, kind, s1)
            bar_hook(at_b, k, 1.0, 1 if kind == 'drop2' else 0, 1.0)
            if kind == 'drop2': bar_hook(at_b, k, .25, 0, .6, .6)      # octave doubling
        if kind == 'drop' and k % 4 == 0:
            place('drums', crash(1.6), b(at_b), .32, -.2)

# intro: filtered hook, sub swell, hits on the name stamps, roll + riser into the drop
for k in range(1):
    bar_hook(0, 0, .55, 0, .15, .7)
place('bass', bass808(28, b(4), None, False, 2.0), 0, .45)
for at_b in (.85, 1.85, 2.45):
    place('drums', clap(), b(at_b), .55, 0, .5); place('bass', bass808(28, .35), b(at_b), .7)
for k in range(8): place('drums', snare(.5 + .07 * k), b(3) + k * S16 / 2, .15 + .05 * k, (-1) ** k * .2)
place('fx', riser(b(2)), b(2), .7)

# break (the passage): pad, sparse filtered hook, one long 808, quarter hats
place('pad', pad([52, 55, 59], b(4) + .3), b(20), .55, 0)
bar_hook(20, 0, .5, 0, .2, .8); bar_hook(22, 1, .45, 0, .2, .8)
place('bass', bass808(28, b(3.6), 26, False, 2.2), b(20), .6)
for q in range(4): place('drums', hat(), b(22 + q), .18, .3)
place('fx', riser(b(1.6)), b(22.4), .6)

# the Noh stage: tsuzumi, flute, pad, drone
for at_b, hi in [(36, True), (36.75, False), (37.25, True), (37.75, True)]:
    place('pad', tsuzumi(hi), b(at_b), .5, -.3 if hi else .2, .4)
place('pad', flute(76, b(1.0)), b(36.1), .25, .2, .6); place('pad', flute(74, b(.9)), b(37.1), .25, .2, .6)
place('pad', pad([52, 55, 59], b(2) + .2, 1200), b(36), .35)
place('bass', bass808(28, b(2), None, False, 1.6), b(36), .4)
place('fx', glass(1.1), b(38), .7, .2); place('drums', crash(2), b(38), .4)

# build (mirror -> hammer): hook through an opening filter, accelerating snare roll, riser, 808 climbing
for k, at_b in enumerate(range(56, 64, 4)):
    bar_hook(at_b, k, .7, 0, .25 + .5 * k, .5); bar_hook(at_b + 2, k + 1, .7, 0, .5 + .5 * k, .5)
place('pad', pad([52, 55, 59, 62], b(8), 2200), b(56), .5)
for q in range(4): place('drums', hat(), b(56 + q * .5), .15, .3)
roll = [(60 + i * .5) for i in range(4)] + [(62 + i * .25) for i in range(4)] + [(63 + i * .125) for i in range(8)]
for k, rb in enumerate(roll): place('drums', snare(.5 + .03 * k), b(rb), .14 + .03 * k, (-1) ** k * .25)
place('fx', riser(b(4)), b(60), .8)
place('bass', bass808(28, b(4), 40, False, 2.5), b(60), .5)
place('fx', spin(b(4)), b(60), .8)

# silence, then a reversed cowbell swell into the blow
place('fx', cowbell(88, .6)[::-1] * np.linspace(0, 1, round(.6 * SR)), b(66) - .6, .5)
place('fx', boom(3.0), b(66), .9); place('drums', crash(2.4), b(66), .5)

# soft: "...a reason to kill you" - pad, slow hook in quarter notes, soft 808
place('pad', pad([52, 55, 59], b(6) + .3, 1400), b(74), .55)
for k, m in enumerate([76, 74, 72, 71, 72, 74]):
    place('bell', cowbell(m, .5, .4), b(74 + k), .35, (-1) ** k * .3, .9)
for at_b, r in [(74, 28), (76, 24 + 7), (78, 26)]:
    place('bass', bass808(r, b(1.9), None, False, 1.5), b(at_b), .45)

# end: last hit rings
place('bass', bass808(28, b(2) + .6, 16, True, 3.5), b(88), .9)
place('drums', clap(), b(88), .6, 0, .7); place('drums', crash(2.6), b(88), .5)
place('bell', cowbell(76, .8), b(88), .5, 0, 1.0)

# ---------------------------------------------------------------- cuts and contacts
for j, c in enumerate(CUTS):
    if c in (64, 66, 74): continue
    place('fx', whoosh(.2), b(c) - .19, .3, (-1) ** j * .6)
for hb, st in HITS:
    place('fx', clang(900 + 160 * (hb % 4), .5 + .2 * st), b(hb), .1 + .05 * st, (-1) ** int(hb * 2) * .3, .2)
    if st >= 2: place('drums', clap(), b(hb), .25 + .1 * st, 0, .4)
    if st == 3 and hb != 66: place('bass', bass808(28, .5), b(hb), .5)

# ---------------------------------------------------------------- mix
def reverb_ir(rt=1.6):
    t = tt(rt); ir = RNG.normal(size=(len(t), 2)) * np.exp(-t * 6.9 / rt)[:, None]
    ir = filt(ir, 200, 6000); ir[:int(.012 * SR)] *= 0
    return ir / np.sqrt((ir ** 2).sum() / 2)


ir = reverb_ir()
n = N + len(ir)
nfft = 1 << (n - 1).bit_length()
wet = np.stack([np.fft.irfft(np.fft.rfft(BUS['verb'][:, c], nfft) * np.fft.rfft(ir[:, c], nfft), nfft)[:N]
                for c in range(2)], 1) * .22

kick_env = np.zeros(N)
for kb in KICKS:
    i = round(b(kb) * SR); seg = np.exp(-tt(.18) * 18); kick_env[i:i + len(seg)] = np.maximum(kick_env[i:i + len(seg)], seg[:N - i])
duck = (1 - .35 * kick_env)[:, None]

bass = BUS['bass'].mean(1, keepdims=True).repeat(2, 1)        # 808 in mono
mix = (BUS['drums'] * 1.0 + bass * .42 + BUS['bell'] * duck * 1.9 + BUS['pad'] * duck * 1.1 + BUS['fx'] * .9 + wet * duck * 1.4)
tm = np.arange(N) / SR
gate = np.interp(tm, [0, b(64), b(64) + .04, b(66) - .62, b(66) - .6, DUR - .9, DUR], [1, 1, .02, .02, 1, 1, 0])
mix *= gate[:, None]
mix = np.tanh(mix * 1.15) / np.tanh(1.15)
mix *= .93 / max(.93, np.max(np.abs(mix)))
with wave.open(str(HERE / 'score_short.wav'), 'wb') as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR)
    f.writeframes((mix * 32767).astype('<i2').tobytes())
print(f'score_short.wav: {DUR:.2f}s, {NB} beats @ {60 / BEAT:.0f} BPM, {len(KICKS)} kicks, {len(CLAPS)} claps, '
      f'peak {20 * np.log10(np.max(np.abs(mix))):.2f} dBFS')
