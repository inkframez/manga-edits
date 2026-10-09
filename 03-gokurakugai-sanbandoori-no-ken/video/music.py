"""Synthesised 20 s action cue for the Gokurakugai Short (150 BPM, E minor) -> music.wav.

Original sounds made from oscillators and noise (no samples): taiko/kick, snare, hats, a distorted bass riff,
a detuned saw stab, risers, gunshots and booms. The arrangement follows the shot list in render.py (same beat numbers):
  0-4 intro drone + two taiko hits | 4-8 three punches | 8-14 groove (gate) | 14-22 name cards | 22-26 build + roll
  26-42 the fight (full drums, bass riff, gunshots at 37/38) | 42-46 filtered breakdown | 46 final boom + tail.
Usage: python music.py
"""
import os, numpy as np, wave

HERE = os.path.dirname(os.path.abspath(__file__))
SR, BPM, DUR = 44100, 150.0, 20.0
BEAT = 60 / BPM
N = int(SR * DUR)
rng = np.random.default_rng(11)
L = np.zeros(N); R = np.zeros(N)
def at(beat): return int(round(beat * BEAT * SR))
def env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR; return np.minimum(1, t / a) * np.exp(-t / d)
def put(sig, beat, gain=1.0, pan=0.0):
    i = at(beat)
    if i >= N: return
    s = sig[:N - i] * gain
    L[i:i + len(s)] += s * (1 - pan) ** 0.5 * 1.0; R[i:i + len(s)] += s * (1 + pan) ** 0.5 * 1.0
def lp(x, a):   # one-pole low-pass, a in (0,1]
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)): acc += a * (x[i] - acc); y[i] = acc
    return y
def hp(x, a): return x - lp(x, a)

# ---------------------------------------------------------------- instruments
def kick(n=0.45):
    k = int(SR * n); t = np.arange(k) / SR
    f = 45 + 110 * np.exp(-t * 28); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(2.2 * np.sin(ph) * env(k, 0.001, 0.16)) + 0.25 * rng.normal(0, 1, k) * env(k, 0.0005, 0.004)
def taiko(n=0.9, f0=70):
    k = int(SR * n); t = np.arange(k) / SR
    f = f0 + 60 * np.exp(-t * 18); ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * env(k, 0.002, 0.28) + 0.5 * np.sin(1.6 * ph) * env(k, 0.002, 0.12)
    skin = lp(rng.normal(0, 1, k), 0.08) * env(k, 0.001, 0.03)
    return np.tanh(1.6 * (body + 1.5 * skin))
_SN = None
def snare():
    k = int(SR * 0.3); t = np.arange(k) / SR
    tone = np.sin(2 * np.pi * 190 * t) * env(k, 0.001, 0.05)
    noise = hp(rng.normal(0, 1, k), 0.25) * env(k, 0.001, 0.11)
    return np.tanh(1.5 * (0.6 * tone + 0.9 * noise))
def hat(open_=False):
    k = int(SR * (0.25 if open_ else 0.05))
    return hp(rng.normal(0, 1, k), 0.6) * env(k, 0.0005, 0.08 if open_ else 0.018) * 0.5
def boom(n=2.5):
    k = int(SR * n); t = np.arange(k) / SR
    f = 32 + 70 * np.exp(-t * 6); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(1.8 * np.sin(ph) * env(k, 0.003, 0.9)) + 0.6 * lp(rng.normal(0, 1, k), 0.05) * env(k, 0.002, 0.4)
def gunshot():
    k = int(SR * 0.6); n = rng.normal(0, 1, k)
    crack = hp(n, 0.5) * env(k, 0.0003, 0.02)
    body = lp(n, 0.06) * env(k, 0.001, 0.12)
    t = np.arange(k) / SR; thump = np.sin(2 * np.pi * (60 + 80 * np.exp(-t * 30)) * t) * env(k, 0.001, 0.1)
    return np.tanh(2.5 * (crack + 1.2 * body + thump))
def crash(n=1.8):
    k = int(SR * n); return hp(rng.normal(0, 1, k), 0.35) * env(k, 0.001, 0.6) * 0.45
def riser(beats, f0=200, f1=5000):
    k = int(SR * beats * BEAT); t = np.linspace(0, 1, k)
    n = rng.normal(0, 1, k); out = np.zeros(k); acc = 0.0
    a = (f0 + (f1 - f0) * t ** 2) / SR * 2 * np.pi
    for i in range(k): acc += min(a[i], 1.0) * (n[i] - acc); out[i] = acc
    return out * t ** 1.5 * 0.6
def saw(f, k, detune=0.0):
    t = np.arange(k) / SR; s = 0
    for d in (-detune, 0, detune): s = s + 2 * ((t * f * (1 + d)) % 1) - 1
    return s / 3
def bass_note(f, beats, drive=3.0):
    k = int(SR * beats * BEAT); s = saw(f, k, 0.004) + 0.6 * np.sin(2 * np.pi * f / 2 * np.arange(k) / SR)
    return np.tanh(drive * lp(s, 0.06)) * env(k, 0.003, beats * BEAT * 0.9) * 0.55
def stab(fs, beats=0.5):
    k = int(SR * beats * BEAT); s = sum(saw(f, k, 0.008) for f in fs) / len(fs)
    return lp(s, 0.12) * env(k, 0.002, 0.12) * 0.5
def drone(beats):
    k = int(SR * beats * BEAT); t = np.arange(k) / SR
    s = 0.5 * np.sin(2 * np.pi * 41.2 * t) + 0.3 * np.sin(2 * np.pi * 61.7 * t) + 0.15 * lp(saw(82.4, k, 0.01), 0.02)
    return s * np.minimum(1, t / 1.0) * np.minimum(1, (k / SR - t) / 0.3)

E1, G1, A1, B1, D2, E2 = 41.2, 49.0, 55.0, 61.7, 73.4, 82.4
# ---------------------------------------------------------------- arrangement
put(drone(8), 0, 0.5)
put(riser(3, 100, 1500), 0, 0.25)
for bt, g in ((3, 1.0), (3.5, 0.8)): put(taiko(f0=60), bt, g)
for bt in (4, 5, 6): put(taiko(f0=75), bt, 1.0, pan=(bt - 5) * 0.4); put(kick(), bt, 0.7); put(snare(), bt, 0.4)
put(crash(), 6, 0.7); put(boom(1.5), 6, 0.5)
put(snare(), 7, 0.5); put(snare(), 7.5, 0.35); put(snare(), 7.75, 0.45)
# groove 8-22 (half-time: kick on 1, snare on 3 of each 4)
for bar in range(8, 22, 4):
    for k_ in (0, 1.5, 2.5): put(kick(), bar + k_, 0.9)
    put(snare(), bar + 2, 0.75)
    for e in range(8): put(hat(), bar + e * 0.5, 0.5 if e % 2 else 0.8, pan=0.3)
    put(hat(True), bar + 3.5, 0.5, pan=-0.3)
put(crash(), 8, 0.6)
riff = [E1, E1, G1, E1, A1, G1, E1, D2]
for i in range(8, 22, 2): put(bass_note(riff[(i // 2) % 8] * 2, 1.9, 2.0), i, 0.6)
for bt in (14, 18): put(stab([E2 * 2, B1 * 4, G1 * 4]), bt, 0.6); put(taiko(f0=70), bt, 0.8)
# build 22-26
put(riser(4, 300, 9000), 22, 0.7)
for i in range(16): put(snare(), 22 + i * 0.25, 0.25 + 0.04 * i)
for i in range(8): put(snare(), 25 + i * 0.125, 0.6)
put(kick(), 22, 1.0); put(kick(), 24, 1.0)
# fight 26-42: full kit + riff
put(boom(1.2), 26, 0.8); put(crash(), 26, 0.8)
for bar in range(26, 42, 4):
    for k_ in (0, 0.75, 1.5, 2.5, 3.0): put(kick(), bar + k_, 1.0)
    for k_ in (1, 3): put(snare(), bar + k_, 0.9)
    for e in range(16): put(hat(), bar + e * 0.25, 0.65 if e % 2 else 0.9, pan=0.25 if e % 4 < 2 else -0.25)
riff2 = [E1, E1, E2, E1, G1, E1, A1, B1]
for i in range(32):
    bt = 26 + i * 0.5
    put(bass_note(riff2[i % 8] * 2, 0.45, 4.0), bt, 0.75)
for bt in (26, 30, 34): put(stab([E2 * 2, B1 * 4, E2 * 4, G1 * 8], 1.0), bt, 0.55)
for bt in (30, 32, 35, 40): put(taiko(f0=65), bt, 1.0)
for bt in (37, 38): put(gunshot(), bt, 1.1, pan=0.2)
put(crash(), 34, 0.6)
# breakdown 42-46: filtered pad + heartbeat kick
pad_k = int(SR * 4 * BEAT); t = np.arange(pad_k) / SR
pad = lp(sum(saw(f, pad_k, 0.01) for f in (E2 * 2, B1 * 4, G1 * 4)) / 3, 0.03) * np.minimum(1, t / 0.4)
put(pad, 42, 0.5); put(kick(), 42, 0.9); put(kick(), 44, 0.8)
put(riser(2, 400, 7000), 44, 0.6)
put(snare(), 45.5, 0.6); put(snare(), 45.75, 0.8)
# title 46
put(boom(3.5), 46, 1.2); put(taiko(f0=55), 46, 1.0); put(crash(3.0), 46, 0.9)
put(stab([E1 * 4, B1 * 4, E2 * 4, G1 * 8], 6.0), 46, 0.6)
for bt in (48, 49): put(taiko(f0=60), bt, 0.5)

# ---------------------------------------------------------------- mix: simple reverb, glue, fade
def reverb(x, sec=1.2, mix=0.18):
    k = int(SR * sec); ir = rng.normal(0, 1, k) * np.exp(-np.arange(k) / (SR * sec / 5)); ir /= np.abs(ir).sum() ** 0.5 * 30
    n = 1 << int(np.ceil(np.log2(len(x) + k)))
    y = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[:len(x)]
    return x + mix * y
L, R = reverb(L), reverb(R)
mx = np.stack([L, R], 1)
mx = np.tanh(1.2 * mx / (np.abs(mx).max() + 1e-9) * 1.6)
fade = np.ones(N); fl = int(SR * 0.4); fade[-fl:] = np.linspace(1, 0, fl)
mx *= fade[:, None]
mx = (mx / np.abs(mx).max() * 0.92 * 32767).astype(np.int16)
with wave.open(os.path.join(HERE, 'music.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(mx.tobytes())
print('wrote music.wav', mx.shape[0] / SR, 's')
