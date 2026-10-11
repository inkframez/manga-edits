"""Steel Ball Run ch.18 v3 score -> music_v3.wav + beatmap_v3.json. 140 BPM, D minor, 104 beats = 44.57 s.

Slower and roomier than v2 (172 BPM): a western breakbeat with two set pieces scored beat for beat.
  0-16    intro      twang melody over a gallop, riser
  16-28   Tim        drop: breakbeat, reese riff, guitar stabs
  28-44   magnet     half-time, wobble bass speeding up, riser, silence at 43.5     -> 44 hit
  44-51   STEEL BALL the ball spins up in Gyro's hand (whirr rising), charge riser
  51      THROW      whoosh + hit; 52.5 the ball strikes the rock (clang + debris)
  51-62   flight     breakbeat + the spin tone flying along the arc; 62 Tim is hit (big)
  62-74   aftermath  groove
  74-78   break      pad + twang (Tim: "I threw a rope...")
  78      STAND      rope whip crack + hit, build
  82      SPLIT      drop 2, everything + guitar lead
  94      title hit; 100 tape stop; 101 "to be continued" arpeggio
Usage: python music_v3.py
"""
import os, json, wave, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR, BPM = 44100, 140.0
BEAT = 60.0 / BPM
NB = 104
DUR = NB * BEAT
N = int(SR * DUR)
rng = np.random.default_rng(1803)

def bt(beat): return beat * BEAT
def idx(beat): return int(round(beat * BEAT * SR))
BUS = {k: np.zeros((N, 2)) for k in ('drums', 'bass', 'music', 'fx')}
MAP = dict(bpm=BPM, beat=BEAT, dur=DUR, kick=[], snare=[], hat=[], hit=[], whoosh=[])

def put(sig, beat, gain=1.0, pan=0.0, bus='music'):
    i = idx(beat)
    if i >= N or len(sig) == 0: return
    if i < 0: sig = sig[-i:]; i = 0
    s = sig[:N - i] * gain
    BUS[bus][i:i + len(s), 0] += s * np.sqrt((1 - pan) / 2) * 1.414
    BUS[bus][i:i + len(s), 1] += s * np.sqrt((1 + pan) / 2) * 1.414
def env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-5)) * np.exp(-t / d)
def fftf(x, lo=None, hi=None, order=4):
    n = len(x); X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR) + 1e-6
    if hi: X *= 1 / np.sqrt(1 + (f / hi) ** (2 * order))
    if lo: X *= 1 / np.sqrt(1 + (lo / f) ** (2 * order))
    return np.fft.irfft(X, n)
def movavg(x, k):
    if k <= 1: return x
    c = np.cumsum(np.r_[np.zeros(k), x]); return (c[k:] - c[:-k]) / k
def saw(ph): return 2 * (ph % 1.0) - 1
def hz(note): return 440.0 * 2 ** ((note - 69) / 12)
D2, Bb1, C2, A1 = 38, 34, 36, 33

# ---------------------------------------------------------------- drums
def kick():
    k = int(SR * 0.4); t = np.arange(k) / SR
    f = 42 + 110 * np.exp(-t * 28) + 40 * np.exp(-t * 300)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(k, 0.0008, 0.2)
    return np.tanh(2.2 * (s + fftf(rng.normal(0, 1, k), lo=2500) * env(k, 0.0002, 0.004) * 0.5))
def snare():
    k = int(SR * 0.35); t = np.arange(k) / SR
    tone = np.sin(2 * np.pi * (180 + 50 * np.exp(-t * 40)) * t) * env(k, 0.0008, 0.07)
    nz = fftf(rng.normal(0, 1, k), lo=1100, hi=9000) * env(k, 0.0008, 0.14)
    return np.tanh(1.8 * (0.7 * tone + 0.9 * nz))
def hat(open_=False):
    k = int(SR * (0.25 if open_ else 0.05))
    return fftf(rng.normal(0, 1, k), lo=7000) * env(k, 0.0003, 0.1 if open_ else 0.014) * 0.5
def crash(d=2.0):
    k = int(SR * d); t = np.arange(k) / SR
    ring = sum(np.sin(2 * np.pi * f * t) for f in (3150, 4270, 5330, 6680)) * 0.08
    return (fftf(rng.normal(0, 1, k), lo=3500) + ring) * env(k, 0.001, d * 0.35) * 0.55
def boom(d=1.8):
    k = int(SR * d); t = np.arange(k) / SR
    f = 33 + 70 * np.exp(-t * 6)
    s = np.tanh(2.0 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(k, 0.002, d * 0.35))
    return s + 0.5 * fftf(rng.normal(0, 1, k), hi=300) * env(k, 0.001, 0.3)
def clang(f0=520):
    k = int(SR * 1.6); t = np.arange(k) / SR
    s = sum(g * np.sin(2 * np.pi * f0 * m * t) * np.exp(-t * dcy) for m, g, dcy in
            ((1, 1, 2.5), (2.76, 0.6, 3.5), (5.4, 0.4, 5), (8.9, 0.25, 7)))
    return np.tanh(1.5 * s) * 0.5
def whip():
    """rope crack: a short swish, then a snap"""
    a = int(SR * 0.18); u = np.linspace(0, 1, a)
    sw = fftf(rng.normal(0, 1, a), lo=800, hi=6000) * u ** 3 * 0.6
    k = int(SR * 0.12); snap = fftf(rng.normal(0, 1, k), lo=1800) * env(k, 0.0002, 0.012) * 2.2
    return np.r_[sw, snap]
def debris(b0, n=40, spread=1.2, g=0.5):
    for i in range(n):
        kk = int(SR * 0.012); tt = b0 + rng.uniform(0, spread) ** 1.6 * spread / BEAT
        put(fftf(rng.normal(0, 1, kk), lo=2500) * env(kk, 0.0005, 0.004) * 2, tt, g * rng.uniform(0.4, 1), rng.uniform(-.7, .7), bus='fx')

def K(b_, g=1.0): put(kick(), b_, g, bus='drums'); MAP['kick'].append(bt(b_))
def S(b_, g=1.0, mark=True):
    put(snare(), b_, g, 0.05, bus='drums')
    if mark: MAP['snare'].append(bt(b_))
def Hh(b_, g=0.5, o=False): put(hat(o), b_, g, 0.35 if int(b_ * 2) % 2 else -0.25, bus='drums'); MAP['hat'].append(bt(b_))
def HIT(b_, g=1.0, cr=True):
    put(boom(2.2), b_, 1.1 * g, bus='fx')
    if cr: put(crash(), b_, 0.8 * g, bus='drums')
    MAP['hit'].append(bt(b_))
def breaks(b0, b1, g=1.0):
    """breakbeat: kick 0 & 2.5, snare 1 & 3, swung 16th ghosts, 8th hats"""
    for bar in np.arange(b0, b1, 4):
        K(bar, g); K(bar + 2.5, 0.85 * g); K(bar + 2.75, 0.4 * g) if int(bar) % 8 == int(b0) % 8 else None
        S(bar + 1, g); S(bar + 3, g); S(bar + 3.75, 0.2 * g, mark=False); S(bar + 1.5, 0.15 * g, mark=False)
        for h in np.arange(0, 4, 0.5): Hh(bar + h, 0.4 * g if h % 1 else 0.28 * g, o=(h == 3.5))
def halftime(b0, b1, g=1.0):
    for bar in np.arange(b0, b1, 4):
        K(bar, g); K(bar + 2.75, 0.6 * g); S(bar + 2, g)
        for h in np.arange(0, 4, 0.5): Hh(bar + h, 0.22 * g)
def roll(b0, b1, g=0.7):
    b_ = b0
    while b_ < b1 - 1e-6:
        u = (b_ - b0) / (b1 - b0)
        step = 1.0 if u < 0.25 else 0.5 if u < 0.5 else 0.25 if u < 0.8 else 0.125
        S(b_, g * (0.45 + 0.6 * u), mark=u < 0.5); b_ += step

# ---------------------------------------------------------------- guitars + synths
def ks(f, dur, bright=0.6, decay=0.997):
    n = int(SR * dur); P = max(2, int(round(SR / f)))
    y = np.zeros(n + 2 * P + 2); burst = rng.uniform(-1, 1, P + 1)
    y[:P + 1] = bright * burst + (1 - bright) * np.convolve(burst, np.ones(4) / 4, 'same')
    i = P + 1
    while i < n: y[i:i + P] = decay * 0.5 * (y[i - P:i] + y[i - P - 1:i - 1]); i += P
    return y[:n]
def twang(note, dur=1.6, g=1.0):
    s = ks(hz(note), dur, 0.55, 0.9978) + 0.5 * ks(hz(note) * 1.003, dur, 0.4, 0.9975)
    t = np.arange(len(s)) / SR
    s *= 1 + 0.25 * np.sin(2 * np.pi * 6.0 * t) * np.minimum(1, t / 0.3)
    return s * env(len(s), 0.001, dur * 0.6) * 0.8 * g
def power(note, dur=0.7, drive=7.0):
    s = ks(hz(note), dur, 0.8, 0.996) + ks(hz(note + 7), dur, 0.8, 0.996) + 0.6 * ks(hz(note + 12), dur, 0.8, 0.996)
    return fftf(np.tanh(drive * s), lo=90, hi=4200) * env(len(s), 0.001, dur * 0.7) * 0.5
def line(schedule, b0, b1, glide=0.012):
    i0, i1 = idx(b0), idx(b1); n = i1 - i0
    f = np.zeros(n); g = np.zeros(n); sch = sorted(e for e in schedule if e[0] < b1)
    for (ba, na), nxt in zip(sch, sch[1:] + [(b1, None)]):
        a, c = idx(ba) - i0, min(idx(nxt[0]) - i0, n)
        if na is None: continue
        f[a:c] = hz(na); g[a:c] = 1
        rel = min(c - a, int(SR * 0.012)); g[c - rel:c] *= np.linspace(1, 0, rel)
    f = movavg(np.r_[np.full(int(SR * glide), f[0]), f], max(1, int(SR * glide)))[-n:]
    return f, g, i0
def reese(schedule, b0, b1, cut=700, g=1.0):
    f, gate, i0 = line(schedule, b0, b1); ph = np.cumsum(f) / SR
    s = np.tanh(1.6 * (saw(ph * 1.0035) + saw(ph * 0.9965 + 0.3) + 0.9 * np.sin(2 * np.pi * ph * 0.5))) * gate
    out = np.zeros(N); out[i0:i0 + len(s)] = fftf(s, hi=cut, order=3) * 0.55 * g; return out
def wobble(schedule, b0, b1, rate0=1.0, rate1=8.0, g=1.0):
    f, gate, i0 = line(schedule, b0, b1, glide=0.04); ph = np.cumsum(f) / SR
    s = np.tanh(1.8 * (saw(ph * 1.004) + saw(ph * 0.996))) * gate
    dark, bright = fftf(s, hi=180, order=3), fftf(s, hi=2400, order=2)
    u = np.linspace(0, 1, len(s)); rate = (rate0 + (rate1 - rate0) * u ** 2) / BEAT
    lfo = 0.5 - 0.5 * np.cos(2 * np.pi * np.cumsum(rate) / SR)
    out = np.zeros(N); out[i0:i0 + len(s)] = (dark * (1 - lfo) + bright * lfo + 0.6 * np.sin(2 * np.pi * ph * 0.5) * gate) * 0.5 * g
    return out
def supersaw(chords, b0, b1, cut=3200, g=1.0):
    out = np.zeros(N)
    for v in range(3):
        for d in (-0.012, -0.005, 0.0, 0.006, 0.013):
            f, gate, i0 = line([(ba, c[v] if c else None) for ba, c in chords], b0, b1, glide=0.001)
            out[i0:i0 + len(f)] += saw(np.cumsum(f * (1 + d)) / SR + rng.random()) * gate
    sm = movavg(np.abs(out), int(SR * 0.08)); att = np.clip(sm / (sm.max() + 1e-9) * 3, 0, 1)
    return fftf(out, lo=150, hi=cut, order=2) * att * 0.07 * g
def bell(note, d=1.6):
    k = int(SR * d); t = np.arange(k) / SR; f = hz(note)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 2.2) + 0.45 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 4)
    s += 0.2 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 7)
    return np.tanh(1.3 * s) * 0.5
def spin(b0, beats, f0, f1, g=1.0, shape='arc'):
    k = int(SR * beats * BEAT); u = np.linspace(0, 1, k)
    f = f0 * (f1 / f0) ** u; ph = 2 * np.pi * np.cumsum(f) / SR
    s = 0.6 * np.sin(ph) + 0.35 * np.sin(ph * 1.5 + 2 * np.sin(ph * 0.25)) + 0.2 * np.sin(ph * 3.01)
    am = 0.6 + 0.4 * np.sin(2 * np.pi * np.cumsum(f * 0.05) / SR)
    e = np.sin(np.pi * u) ** 0.6 if shape == 'arc' else u ** 1.5
    put(np.tanh(1.4 * s) * am * e * 0.45 * g, b0, bus='fx')
def riser(b0, beats, g=1.0):
    k = int(SR * beats * BEAT); u = np.linspace(0, 1, k); nz = rng.normal(0, 1, k)
    s = fftf(nz, hi=500) * (1 - u) + fftf(nz, lo=2000) * u
    tone = np.sin(2 * np.pi * np.cumsum(180 * (2400 / 180) ** (u ** 1.6)) / SR) * 0.35
    put((0.6 * s + tone) * u ** 2.2 * 0.6 * g, b0, bus='fx')
def whoosh(b_, d=0.55, g=1.0):
    k = int(SR * d); u = np.linspace(0, 1, k)
    s = fftf(rng.normal(0, 1, k), lo=500, hi=5000) * np.sin(np.pi * u ** 0.7) ** 2
    put(s * 0.45 * g, b_ - d * 0.7 / BEAT, pan=float(rng.uniform(-.5, .5)), bus='fx'); MAP['whoosh'].append(bt(b_))
def sub_drop(b_, beats=2, g=1.0):
    k = int(SR * beats * BEAT); t = np.arange(k) / SR
    put(np.sin(2 * np.pi * np.cumsum(90 * np.exp(-t * 1.8) + 30) / SR) * env(k, 0.002, beats * BEAT * 0.6) * 0.9 * g, b_, bus='bass')
def addbass(sig): BUS['bass'][:, 0] += sig; BUS['bass'][:, 1] += sig
def addmusic(sig): BUS['music'][:, 0] += sig; BUS['music'][:, 1] += sig

ROOTS = [D2, D2, Bb1 + 12, C2 + 12, D2, D2, Bb1 + 12, A1 + 12]
def bass_riff(b0, b1):
    sch = []
    for i, bar in enumerate(np.arange(b0, b1, 4)):
        r = ROOTS[i % 8]
        for off, n in ((0, r), (0.75, r + 12), (1.5, r), (2.5, r), (3.0, r + 10), (3.5, r + 12)): sch.append((bar + off, n))
    return sch
CH = {D2: (62, 65, 69), Bb1 + 12: (58, 62, 65), C2 + 12: (60, 64, 67), A1 + 12: (57, 61, 64)}
def chords(b0, b1): return [(bar, CH[ROOTS[i % 8]]) for i, bar in enumerate(np.arange(b0, b1, 4))]
def stabs(b0, b1, g=0.5):
    for i, bar in enumerate(np.arange(b0, b1, 4)):
        put(power(ROOTS[i % 8] + 12, 0.6), bar, g, -0.3); put(power(ROOTS[i % 8] + 12, 0.4), bar + 2.5, g * 0.75, 0.3)

# ================================================================ arrangement
# 0-16 intro: gallop + twang melody (two phrases), riser into Tim
for b_ in np.arange(0, 14, 1):
    for off, gn, pan in ((0, 0.5, -0.3), (0.25, 0.35, 0.1), (0.5, 0.6, 0.35)):
        k = int(SR * 0.05); put(fftf(rng.normal(0, 1, k), lo=300, hi=3000) * env(k, 0.0005, 0.015) * 1.6, b_ + off, gn, pan, bus='drums')
    if b_ % 2 == 0: K(b_, 0.45)
mel = [(0, 57), (1, 62), (1.5, 65), (2, 67), (3, 69), (4, 70), (4.5, 69), (5, 67), (5.5, 65), (6, 62),
       (8, 57), (9, 62), (9.5, 65), (10, 69), (11, 72), (12, 70), (12.5, 69), (13, 67), (14, 69)]
for b_, n in mel: put(twang(n, 1.8), b_, 0.7, -0.2)
put(twang(50, 3.5), 0, 0.5, 0.2); put(twang(50, 3.5), 8, 0.5, 0.2)
roll(14, 16, 0.7); riser(11, 5, 0.8)
put(crash(1.0)[::-1] * 0.8, 16 - 1.0 / BEAT, bus='fx')
# 16-28 Tim
HIT(16); breaks(16, 28); addbass(reese(bass_riff(16, 28), 16, 28)); stabs(16, 28)
for b_ in (20,): whoosh(b_)
# 28-44 magnet
HIT(28, 0.7); halftime(28, 40)
addbass(wobble([(28 + 4 * i, ROOTS[i % 4]) for i in range(4)], 28, 43.5, 1.0, 10.0))
for b_ in (30, 34, 38): put(bell(86, 0.7), b_ + 0.5, 0.3, 0.5)
roll(40, 43.5, 0.8); riser(36, 7.5, 1.1)
for b_ in (34, 38, 40, 41, 42, 42.5, 43): put(boom(0.35), b_, 0.25, bus='fx')
# 44-51 the steel ball spins up in his hand
HIT(44, 1.2)
sub_drop(44, 4)
for b_ in (44, 46, 48, 49, 50): K(b_, 0.55)
spin(45, 6, 140, 1400, 1.0, shape='rise')
for b_, n in ((44, 74), (45, 77), (46, 81), (47, 86), (48, 81), (49, 86), (50, 89)): put(bell(n, 1.4), b_, 0.32, 0.3)
riser(48, 3, 0.9)
# 51 throw -> 52.5 rock -> flight back -> 62 Tim is hit
HIT(51, 1.0); whoosh(51, 0.7, 1.4)
put(clang(560), 52.5, 0.7, -0.3, bus='fx'); put(boom(1.0), 52.5, 0.6, bus='fx'); debris(52.5, 50, 1.2, 0.45)
breaks(52, 62); addbass(reese(bass_riff(52, 62), 52, 62, 900))
spin(52.5, 4.5, 2400, 600, 0.9); spin(57, 5, 400, 1600, 0.6)
roll(60, 62, 0.6)
HIT(62, 1.4); debris(62, 70, 1.0, 0.5)
# 62-74 aftermath
breaks(62, 74); addbass(reese(bass_riff(62, 74), 62, 74, 900)); stabs(62, 74, 0.45)
HIT(66, 0.5, cr=False); HIT(70, 0.6)
# 74-78 break: Tim talks
sub_drop(74, 4); addmusic(supersaw(chords(74, 78), 74, 77.75, 1400, 0.9))
put(twang(62, 2.6), 74, 0.6, -0.2); put(twang(65, 2.2), 76, 0.5, 0.2)
# 78 STAND: the rope cracks; build to the split
put(whip(), 78 - 0.18 / BEAT, 1.3, 0.2, bus='fx'); HIT(78, 1.0)
halftime(78, 82, 0.8); riser(78, 4, 1.2); roll(80, 82, 0.75)
put(whip(), 80 - 0.18 / BEAT, 0.8, -0.4, bus='fx')
# 82 SPLIT: drop 2
HIT(82, 1.5)
breaks(82, 94); addbass(reese(bass_riff(82, 94), 82, 94, 1100)); addmusic(supersaw(chords(82, 94), 82, 94, 4200))
stabs(82, 94, 0.5)
lead = [(82, 74), (83, 77), (83.5, 79), (84, 81), (85.5, 79), (86, 77), (87, 74), (90, 82), (91, 81), (91.5, 79), (92, 77), (93, 81)]
for b_, n in lead: put(np.tanh(3 * twang(n, 1.2)) * 0.5, b_, 0.55, 0.25)
for b_ in (84, 86, 88): put(whip(), b_ - 0.18 / BEAT, 0.5, (-1) ** int(b_) * 0.4, bus='fx')
# 94 title, groove to 100, tape stop
HIT(94, 1.4); breaks(94, 100); addbass(reese(bass_riff(94, 100), 94, 100, 1100)); addmusic(supersaw(chords(94, 100), 94, 100, 4200))
for b_ in (8, 12, 16, 28, 34, 38, 51, 58, 62, 66, 70, 74, 78, 90, 94): whoosh(b_, 0.5, 0.7)

# ================================================================ mix
duck = np.ones(N); tt = np.arange(int(SR * 0.3)) / SR; shape = 1 - 0.6 * np.exp(-tt / 0.08)
for k_ in MAP['kick']:
    i = int(k_ * SR); n = min(len(shape), N - i); duck[i:i + n] = np.minimum(duck[i:i + n], shape[:n])
def reverb(x, sec=1.8, mix=0.25):
    k = int(SR * sec); ir = rng.normal(0, 1, k) * np.exp(-np.arange(k) / (SR * sec / 6)); ir /= np.sqrt((ir ** 2).sum()) * 3
    n = 1 << int(np.ceil(np.log2(len(x) + k)))
    return x + mix * np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[:len(x)]
mus = BUS['music'] * duck[:, None]; mus = np.stack([reverb(mus[:, 0]), reverb(mus[:, 1])], 1)
fx = np.stack([reverb(BUS['fx'][:, 0], 2.2, 0.3), reverb(BUS['fx'][:, 1], 2.2, 0.3)], 1)
mx = 1.0 * BUS['drums'] + 0.85 * BUS['bass'] * duck[:, None] + 0.8 * mus + 0.75 * fx
for a, c in ((idx(43.5), idx(44)), (idx(81.75), idx(82))): mx[a:c] *= np.linspace(1, 0, c - a)[:, None] ** 4
a = idx(100); ts = int(SR * 0.8); pos = np.cumsum(np.linspace(1, 0, ts) ** 1.3)
for ch in range(2): mx[a:a + ts, ch] = np.interp(a + pos, np.arange(N), mx[:, ch]) * np.linspace(1, 0.3, ts)
mx[a + ts:] = 0
BUS['music'][:] = 0
for i, n in enumerate((50, 57, 62, 65, 69, 74)): put(twang(n, 3.4), 101.0 + i * 0.25, 0.7, -0.4 + i * 0.16)
put(boom(2.4), 101.0, 0.5)
arp = BUS['music']; mx += np.stack([reverb(arp[:, 0], 2.4, 0.4), reverb(arp[:, 1], 2.4, 0.4)], 1) * 0.9
mx = np.tanh(1.25 * mx / (np.abs(mx).max() + 1e-9) * 1.6)
fade = np.ones(N); fi, fo = int(SR * 0.02), int(SR * 0.6); fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo)
mx = (mx * fade[:, None] / (np.abs(mx).max() + 1e-9) * 0.93 * 32767).astype(np.int16)
with wave.open(os.path.join(HERE, 'music_v3.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(mx.tobytes())
for k in ('kick', 'snare', 'hat', 'whoosh'): MAP[k] = sorted(round(x, 4) for x in MAP[k] if x < 100 * BEAT)
MAP['hit'] = sorted(round(x, 4) for x in MAP['hit'])
with open(os.path.join(HERE, 'beatmap_v3.json'), 'w') as f: json.dump(MAP, f, indent=0)
print('wrote music_v3.wav + beatmap_v3.json', {k: len(v) for k, v in MAP.items() if isinstance(v, list)})
