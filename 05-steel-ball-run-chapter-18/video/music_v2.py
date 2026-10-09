"""Steel Ball Run ch.18 v2 score -> music_v2.wav + beatmap_v2.json. 172 BPM, D minor, 86 beats = 30.0 s.

A new piece (not music.py): western drum & bass. Fully synthesised - Karplus-Strong guitars (clean twang + distorted
power chords), reese bass, a wobble bass for the magnetism, supersaw pad, d&b drums, risers, spin sweeps, tape stop.
Every drum hit and accent is written to beatmap_v2.json, and render_v2.py cuts and bumps the camera on it.

  0-8    intro     twang riff over a gallop, snare roll                 -> 8  DROP 1 (Mountain Tim)
  8-24   drop 1    d&b, reese riff, guitar stabs
  24-40  magnet    half-time, wobble bass that speeds up, riser, silence -> 40 EXPLODE
  40-56  steel     d&b, spin sweeps (throw 44 / return 48), impacts 50 52
  56-62  break     pad + sub, riser                                      -> 62 DROP 2 (the rope)
  62-78  drop 2    everything + guitar lead
  78-86  outro     title hit, tape stop at 82, "to be continued" arpeggio
Usage: python music_v2.py
"""
import os, json, wave, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR, BPM = 44100, 172.0
BEAT = 60.0 / BPM
NB = 86
DUR = NB * BEAT
N = int(SR * DUR)
rng = np.random.default_rng(1718)

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
    """zero-phase low/high-pass by spectral shaping (fast, no python loops)"""
    n = len(x); X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR) + 1e-6
    if hi: X *= 1 / np.sqrt(1 + (f / hi) ** (2 * order))
    if lo: X *= 1 / np.sqrt(1 + (lo / f) ** (2 * order))
    return np.fft.irfft(X, n)
def saw(ph): return 2 * (ph % 1.0) - 1
def hz(note): return 440.0 * 2 ** ((note - 69) / 12)     # midi -> Hz
D2, F2, G2, A2, Bb1, C2, A1 = 38, 41, 43, 45, 34, 36, 33

# ---------------------------------------------------------------- drums
def kick():
    k = int(SR * 0.32); t = np.arange(k) / SR
    f = 44 + 120 * np.exp(-t * 32) + 40 * np.exp(-t * 300)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(k, 0.0008, 0.16)
    click = fftf(rng.normal(0, 1, k), lo=2500) * env(k, 0.0002, 0.004) * 0.5
    return np.tanh(2.2 * (s + click))
def snare():
    k = int(SR * 0.28); t = np.arange(k) / SR
    tone = np.sin(2 * np.pi * (185 + 60 * np.exp(-t * 40)) * t) * env(k, 0.0008, 0.06)
    nz = fftf(rng.normal(0, 1, k), lo=1200, hi=9000) * env(k, 0.0008, 0.11)
    return np.tanh(1.8 * (0.7 * tone + 0.9 * nz))
def hat(open_=False):
    k = int(SR * (0.22 if open_ else 0.05))
    return fftf(rng.normal(0, 1, k), lo=7000) * env(k, 0.0003, 0.09 if open_ else 0.014) * 0.5
def crash(d=1.8):
    k = int(SR * d); t = np.arange(k) / SR
    nz = fftf(rng.normal(0, 1, k), lo=3500)
    ring = sum(np.sin(2 * np.pi * f * t) for f in (3150, 4270, 5330, 6680)) * 0.08
    return (nz + ring) * env(k, 0.001, d * 0.35) * 0.55
def boom(d=1.6):
    k = int(SR * d); t = np.arange(k) / SR
    f = 34 + 70 * np.exp(-t * 7)
    s = np.tanh(2.0 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(k, 0.002, d * 0.35))
    return s + 0.5 * fftf(rng.normal(0, 1, k), hi=300) * env(k, 0.001, 0.3)

def K(b_, g=1.0): put(kick(), b_, g, bus='drums'); MAP['kick'].append(bt(b_))
def S(b_, g=1.0, mark=True):
    put(snare(), b_, g, 0.05, bus='drums')
    if mark: MAP['snare'].append(bt(b_))
def Hh(b_, g=0.5, o=False): put(hat(o), b_, g, 0.35 if int(b_ * 2) % 2 else -0.25, bus='drums'); MAP['hat'].append(bt(b_))
def HIT(b_, g=1.0, cr=True):
    put(boom(2.0), b_, 1.1 * g, bus='fx')
    if cr: put(crash(), b_, 0.8 * g, bus='drums')
    MAP['hit'].append(bt(b_))

def dnb(b0, b1, hats=True, ghost=True, g=1.0):
    """two-step: kick 0 & 2.5, snare 1 & 3 (per 4-beat bar), 8th hats, ghost snares"""
    for bar in np.arange(b0, b1, 4):
        K(bar, g); K(bar + 2.5, 0.9 * g); S(bar + 1, g); S(bar + 3, g)
        if ghost: S(bar + 1.75, 0.22 * g, mark=False); S(bar + 3.75, 0.18 * g, mark=False)
        if hats:
            for h in np.arange(0, 4, 0.5): Hh(bar + h, 0.42 * g if h % 1 else 0.3 * g, o=(h == 3.5))
def halftime(b0, b1, g=1.0):
    for bar in np.arange(b0, b1, 4):
        K(bar, g); K(bar + 2.75, 0.6 * g); S(bar + 2, g)
        for h in np.arange(0, 4, 0.5): Hh(bar + h, 0.25 * g)
def roll(b0, b1, g=0.7):
    """snare roll that accelerates 1/4 -> 1/32 and gets louder"""
    b_ = b0
    while b_ < b1 - 1e-6:
        u = (b_ - b0) / (b1 - b0)
        step = 1.0 if u < 0.25 else 0.5 if u < 0.5 else 0.25 if u < 0.8 else 0.125
        S(b_, g * (0.45 + 0.6 * u), mark=u < 0.5); b_ += step

# ---------------------------------------------------------------- guitars (Karplus-Strong, vectorised per period)
def ks(f, dur, bright=0.6, decay=0.997):
    n = int(SR * dur); P = max(2, int(round(SR / f)))
    y = np.zeros(n + 2 * P + 2)
    burst = rng.uniform(-1, 1, P + 1)
    sm = np.convolve(burst, np.ones(4) / 4, 'same'); y[:P + 1] = bright * burst + (1 - bright) * sm
    i = P + 1
    while i < n:
        y[i:i + P] = decay * 0.5 * (y[i - P:i] + y[i - P - 1:i - 1]); i += P
    return y[:n]
def twang(note, dur=1.4, g=1.0):
    s = ks(hz(note), dur, 0.55, 0.9975) + 0.5 * ks(hz(note) * 1.003, dur, 0.4, 0.997)
    k = len(s); t = np.arange(k) / SR
    s *= 1 + 0.25 * np.sin(2 * np.pi * 6.5 * t) * np.minimum(1, t / 0.3)      # surf tremolo
    return s * env(k, 0.001, dur * 0.6) * 0.8 * g
def power(note, dur=0.6, drive=7.0):
    s = ks(hz(note), dur, 0.8, 0.996) + ks(hz(note + 7), dur, 0.8, 0.996) + 0.6 * ks(hz(note + 12), dur, 0.8, 0.996)
    s = np.tanh(drive * s)
    return fftf(s, lo=90, hi=4200) * env(len(s), 0.001, dur * 0.7) * 0.5

# ---------------------------------------------------------------- synths (continuous lines -> one filter pass each)
def line(schedule, b0, b1, glide=0.012):
    """schedule: [(beat, midi or None)], returns per-sample freq + gate between b0..b1"""
    i0, i1 = idx(b0), idx(b1); n = i1 - i0
    f = np.zeros(n); g = np.zeros(n)
    sch = sorted(schedule)
    for (ba, na), nxt in zip(sch, sch[1:] + [(b1, None)]):
        a, c = idx(ba) - i0, idx(nxt[0]) - i0
        if na is None: continue
        f[a:c] = hz(na); g[a:c] = 1
        rel = min(c - a, int(SR * 0.012)); g[c - rel:c] *= np.linspace(1, 0, rel)     # tiny gap between notes
    f = movavg(np.r_[np.full(int(SR * glide), f[0]), f], max(1, int(SR * glide)))[-n:]
    return f, g, i0
def movavg(x, k):
    """trailing moving average via cumsum (fast for long kernels)"""
    if k <= 1: return x
    c = np.cumsum(np.r_[np.zeros(k), x]); return (c[k:] - c[:-k]) / k
def reese(schedule, b0, b1, cut=700, g=1.0):
    f, gate, i0 = line(schedule, b0, b1)
    ph = np.cumsum(f) / SR
    s = saw(ph * 1.0035) + saw(ph * 0.9965 + 0.3) + 0.9 * np.sin(2 * np.pi * ph * 0.5)
    s = np.tanh(1.6 * s) * gate
    s = fftf(s, hi=cut, order=3)
    out = np.zeros(N); out[i0:i0 + len(s)] = s * 0.55 * g; return out
def wobble(schedule, b0, b1, rate0=1.0, rate1=8.0, g=1.0):
    """wobble: dark/bright saw crossfaded by an LFO that speeds up (the magnet pulling harder)"""
    f, gate, i0 = line(schedule, b0, b1, glide=0.04)
    ph = np.cumsum(f) / SR; s = np.tanh(1.8 * (saw(ph * 1.004) + saw(ph * 0.996))) * gate
    dark, bright = fftf(s, hi=180, order=3), fftf(s, hi=2400, order=2)
    u = np.linspace(0, 1, len(s)); rate = (rate0 + (rate1 - rate0) * u ** 2) / BEAT     # in beats -> Hz
    lfo = 0.5 - 0.5 * np.cos(2 * np.pi * np.cumsum(rate) / SR)
    out = np.zeros(N); out[i0:i0 + len(s)] = (dark * (1 - lfo) + bright * lfo + 0.6 * np.sin(2 * np.pi * ph * 0.5) * gate) * 0.5 * g
    return out
def supersaw(chords, b0, b1, cut=3200, g=1.0):
    out = np.zeros(N)
    for v in range(3):
        for d in (-0.012, -0.005, 0.0, 0.006, 0.013):
            f, gate, i0 = line([(ba, c[v] if c else None) for ba, c in chords], b0, b1, glide=0.001)
            ph = np.cumsum(f * (1 + d)) / SR + rng.random()
            out[i0:i0 + len(f)] += saw(ph) * gate
    sm = movavg(np.abs(out), int(SR * 0.05))
    att = np.clip(sm / (sm.max() + 1e-9) * 3, 0, 1)
    return fftf(out, lo=150, hi=cut, order=2) * att * 0.07 * g
def bell(note, d=1.4):
    k = int(SR * d); t = np.arange(k) / SR; f = hz(note)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 2.4) + 0.45 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 4)
    s += 0.2 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 7)
    return np.tanh(1.3 * s) * 0.5
def spin(b0, beats, f0, f1, g=1.0):
    k = int(SR * beats * BEAT); u = np.linspace(0, 1, k)
    f = f0 * (f1 / f0) ** u; ph = 2 * np.pi * np.cumsum(f) / SR
    s = (0.6 * np.sin(ph) + 0.35 * np.sin(ph * 1.5 + 2 * np.sin(ph * 0.25)) + 0.2 * np.sin(ph * 3.01))
    am = 0.6 + 0.4 * np.sin(2 * np.pi * np.cumsum(f * 0.05) / SR)        # the ball's rotation, audible
    put(np.tanh(1.4 * s) * am * np.sin(np.pi * u) ** 0.6 * 0.45 * g, b0, bus='fx')
def riser(b0, beats, g=1.0):
    k = int(SR * beats * BEAT); u = np.linspace(0, 1, k)
    nz = rng.normal(0, 1, k); dark, br = fftf(nz, hi=500), fftf(nz, lo=2000)
    s = dark * (1 - u) + br * u
    f = 180 * (2400 / 180) ** (u ** 1.6); tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35
    put((0.6 * s + tone) * u ** 2.2 * 0.6 * g, b0, bus='fx')
def whoosh(b_, d=0.42, g=1.0):
    k = int(SR * d); u = np.linspace(0, 1, k); nz = rng.normal(0, 1, k)
    s = fftf(nz, lo=600, hi=5000) * (np.sin(np.pi * u ** 0.7) ** 2)
    put(s * 0.45 * g, b_ - d * 0.7 / BEAT, pan=float(rng.uniform(-.5, .5)), bus='fx'); MAP['whoosh'].append(bt(b_))
def sub_drop(b_, beats=2, g=1.0):
    k = int(SR * beats * BEAT); t = np.arange(k) / SR
    f = 90 * np.exp(-t * 2.2) + 30
    put(np.sin(2 * np.pi * np.cumsum(f) / SR) * env(k, 0.002, beats * BEAT * 0.6) * 0.9 * g, b_, bus='bass')

# ================================================================ arrangement
# riffs (D minor): per bar roots D D Bb C | D D Bb A
ROOTS = [D2, D2, Bb1 + 12, C2 + 12, D2, D2, Bb1 + 12, A1 + 12]
def bass_riff(b0, b1):
    sch = []
    for i, bar in enumerate(np.arange(b0, b1, 4)):
        r = ROOTS[i % 8]
        for off, n in ((0, r), (0.75, r + 12), (1.5, r), (2.5, r), (3.0, r + 10), (3.5, r + 12)):
            sch.append((bar + off, n))
    return sch
CH = {D2: (62, 65, 69), Bb1 + 12: (58, 62, 65), C2 + 12: (60, 64, 67), A1 + 12: (57, 61, 64)}
def chords(b0, b1): return [(bar, CH[ROOTS[i % 8]]) for i, bar in enumerate(np.arange(b0, b1, 4))]

# ---- intro 0-8: gallop + twang riff, roll into the drop
for b_ in np.arange(0, 6, 1):                       # canter: three hoof-falls
    for off, gn in ((0, 0.5), (0.25, 0.35), (0.5, 0.6)):
        put(fftf(rng.normal(0, 1, int(SR * 0.05)), lo=300, hi=3000) * env(int(SR * 0.05), 0.0005, 0.015) * 1.6,
            b_ + off, gn, (-0.3, 0.1, 0.35)[int(off * 4) % 3], bus='drums')
    K(b_, 0.5) if b_ % 2 == 0 else None
for b_, n in ((0, 57), (1, 62), (1.5, 65), (2, 67), (3, 69), (4, 70), (4.5, 69), (5, 67), (5.5, 65), (6, 62)):
    put(twang(n, 1.6), b_, 0.75, -0.2)
put(twang(50, 3.0), 0, 0.5, 0.2)
roll(6, 8, 0.75); riser(5, 3, 0.8)
put(crash(0.9)[::-1] * 0.8, 8 - 0.9 / BEAT, bus='fx')                        # reverse cymbal into the drop

# ---- drop 1 8-24
HIT(8)
dnb(8, 24)
BUS['bass'][:, 0] += reese(bass_riff(8, 24), 8, 24); BUS['bass'][:, 1] += reese(bass_riff(8, 24), 8, 24)
for bar in np.arange(8, 24, 4):
    put(power(ROOTS[int((bar - 8) / 4) % 8] + 12, 0.5), bar, 0.55, -0.3)
    put(power(ROOTS[int((bar - 8) / 4) % 8] + 12, 0.35), bar + 2.5, 0.4, 0.3)
roll(22, 24, 0.5)

# ---- magnet 24-40: half-time + wobble that speeds up, metal clangs, riser, silence at 39.5
HIT(16, 0.6, cr=False); HIT(24, 0.9)
halftime(24, 36)
wb = wobble([(24 + 4 * i, ROOTS[i % 4]) for i in range(4)], 24, 39.5, 1.0, 12.0)
BUS['bass'][:, 0] += wb; BUS['bass'][:, 1] += wb
for b_ in (26, 30, 34):
    put(bell(86, 0.6), b_ + 0.5, 0.3, 0.5)                                   # metal ping
roll(36, 39.5, 0.8); riser(32, 7.5, 1.1)
for b_ in (28, 30, 32, 34, 36, 37, 38, 38.5, 39, 39.25):
    put(boom(0.3), b_, 0.25, bus='fx')

# ---- steel ball 40-56
HIT(40, 1.3)
dnb(40, 56)
BUS['bass'][:, 0] += reese(bass_riff(40, 56), 40, 56, 900); BUS['bass'][:, 1] += reese(bass_riff(40, 56), 40, 56, 900)
spin(44, 4, 300, 2600, 1.0); spin(48, 2, 2600, 500, 0.8)
for b_, n in ((40, 74), (42, 77), (44, 81), (46, 86), (48, 74), (52, 77)):
    put(bell(n, 1.2), b_, 0.35, 0.3)
HIT(44, 0.6, cr=False); HIT(48, 0.6, cr=False); HIT(50, 1.1); HIT(52, 0.9)
for bar in (40, 44, 48, 52):
    put(power(ROOTS[int((bar - 40) / 4) % 8] + 12, 0.5), bar, 0.5, -0.3)

# ---- break 56-62
HIT(56, 0.7, cr=True)
sub_drop(56, 4)
BUS['music'] += np.stack([supersaw(chords(56, 62), 56, 61.75, 1400, 0.9)] * 2, 1)
for b_ in (56, 58, 60):
    K(b_, 0.7)
put(twang(62, 2.4), 56, 0.6, -0.2); put(twang(65, 2.0), 58, 0.5, 0.2)
riser(58, 3.75, 1.2); roll(60, 61.75, 0.75)

# ---- drop 2 62-78
HIT(62, 1.4)
dnb(62, 78)
BUS['bass'][:, 0] += reese(bass_riff(62, 78), 62, 78, 1100); BUS['bass'][:, 1] += reese(bass_riff(62, 78), 62, 78, 1100)
BUS['music'] += np.stack([supersaw(chords(62, 78), 62, 78, 4200, 1.0)] * 2, 1)
for bar in np.arange(62, 78, 4):
    put(power(ROOTS[int((bar - 62) / 4) % 8] + 12, 0.45), bar, 0.5, -0.35)
lead = [(62, 74), (63, 77), (63.5, 79), (64, 81), (65.5, 79), (66, 77), (67, 74), (70, 82), (71, 81), (71.5, 79),
        (72, 77), (73.5, 79), (74, 81), (76, 86)]
for b_, n in lead:
    put(np.tanh(3 * twang(n, 1.0)) * 0.5, b_, 0.55, 0.25)
HIT(70, 0.7); HIT(74, 0.5, cr=False)
roll(76, 78, 0.6)

# ---- outro 78-86: title hit, d&b to 82, then the tape stop and the arpeggio
HIT(78, 1.4)
dnb(78, 82)
BUS['bass'][:, 0] += reese(bass_riff(78, 82), 78, 82, 1100); BUS['bass'][:, 1] += reese(bass_riff(78, 82), 78, 82, 1100)
BUS['music'] += np.stack([supersaw(chords(78, 82), 78, 82, 4200, 1.0)] * 2, 1)

# transitions (match render_v2 cuts)
for b_ in (4, 6, 10, 14, 16, 20, 24, 28, 30, 32, 40, 44, 48, 54, 58, 62, 66, 70, 72, 74, 78):
    whoosh(b_, 0.38, 0.8)

# ================================================================ mix
kick_t = np.array(MAP['kick'])
duck = np.ones(N); tt = np.arange(int(SR * 0.25)) / SR; shape = 1 - 0.65 * np.exp(-tt / 0.07)
for k_ in kick_t:
    i = int(k_ * SR); n = min(len(shape), N - i); duck[i:i + n] = np.minimum(duck[i:i + n], shape[:n])
def reverb(x, sec=1.6, mix=0.25):
    k = int(SR * sec); ir = rng.normal(0, 1, k) * np.exp(-np.arange(k) / (SR * sec / 6)); ir /= np.sqrt((ir ** 2).sum()) * 3
    n = 1 << int(np.ceil(np.log2(len(x) + k)))
    return x + mix * np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[:len(x)]
mus = BUS['music'] * duck[:, None]; mus = np.stack([reverb(mus[:, 0]), reverb(mus[:, 1])], 1)
fx = np.stack([reverb(BUS['fx'][:, 0], 2.2, 0.3), reverb(BUS['fx'][:, 1], 2.2, 0.3)], 1)
bass = BUS['bass'] * duck[:, None]
mx = 1.0 * BUS['drums'] + 0.85 * bass + 0.8 * mus + 0.75 * fx
silence = (idx(39.5), idx(40)), (idx(61.75), idx(62))                         # the breath before each drop
for a, c in silence: mx[a:c] *= np.linspace(1, 0, c - a)[:, None] ** 4

# tape stop at 82 (the whole mix winds down), then silence for the arpeggio
a = idx(82); ts = int(SR * 0.75)
spd = np.linspace(1, 0, ts) ** 1.3; pos = np.cumsum(spd)
for ch in range(2):
    seg = np.interp(a + pos, np.arange(N), mx[:, ch]); mx[a:a + ts, ch] = seg * np.linspace(1, 0.3, ts)
mx[a + ts:] = 0
# "to be continued": clean twang arpeggio, ringing
arp = np.zeros((N, 2)); BUS['music'][:] = 0
for i, n in enumerate((50, 57, 62, 65, 69, 74)):
    put(twang(n, 3.2, 1.0), 83.0 + i * 0.25, 0.7, -0.4 + i * 0.16)
put(boom(2.2), 83.0, 0.5, bus='music')
arp = BUS['music']; arp = np.stack([reverb(arp[:, 0], 2.4, 0.4), reverb(arp[:, 1], 2.4, 0.4)], 1)
mx += arp * 0.9

mx = np.tanh(1.25 * mx / (np.abs(mx).max() + 1e-9) * 1.6)
fade = np.ones(N); fi, fo = int(SR * 0.02), int(SR * 0.5); fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo)
mx *= fade[:, None]
mx = (mx / (np.abs(mx).max() + 1e-9) * 0.93 * 32767).astype(np.int16)
with wave.open(os.path.join(HERE, 'music_v2.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(mx.tobytes())
for k in ('kick', 'snare', 'hat', 'hit', 'whoosh'): MAP[k] = sorted(round(x, 4) for x in MAP[k] if x < 82 * BEAT or k == 'hit')
with open(os.path.join(HERE, 'beatmap_v2.json'), 'w') as f: json.dump(MAP, f, indent=0)
print('wrote music_v2.wav + beatmap_v2.json', {k: len(v) for k, v in MAP.items() if isinstance(v, list)})
