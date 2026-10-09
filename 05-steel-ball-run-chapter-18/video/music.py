"""Original 46.15 s score for the Steel Ball Run ch.18 Short. 156 BPM, D minor.

No samples. A horseback gallop, then a magnetic drone, then the steel-ball spin.
Beat numbers match render.py (b(n) = n * 60/156):

  0-16    gallop. three hours, same pace, 15 km left
  16-64   the pull. hooves drop out. a sub drags all three of them
  56-76   the steel ball, sent out to warn him, singing as it returns
  76-90   the scraps come back with it. one hit, then space
  90-112  the rope. air, a slow pulse
  112     title. the chord rings out to beat 120

Usage: python music.py
"""
import os, numpy as np, wave

HERE = os.path.dirname(os.path.abspath(__file__))
SR, BPM = 44100, 156.0
BEAT = 60.0 / BPM
DUR = 120 * BEAT                       # 46.1538 s, same grid as render.py
N = int(SR * DUR)
rng = np.random.default_rng(18)
L = np.zeros(N); R = np.zeros(N)

def at(beat): return int(round(beat * BEAT * SR))
def env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)
def put(sig, beat, gain=1.0, pan=0.0):
    i = at(beat)
    if i >= N or len(sig) == 0: return
    s = sig[:N - i] * gain
    L[i:i + len(s)] += s * (1 - pan) ** 0.5
    R[i:i + len(s)] += s * (1 + pan) ** 0.5
def lp(x, a):
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc); y[i] = acc
    return y
def hp(x, a): return x - lp(x, a)

D2, F2, A2, C3 = 73.42, 87.31, 110.00, 130.81
D3, F3, A3, D4 = 146.83, 174.61, 220.00, 293.66
F4, A4 = 349.23, 440.00
D5, F5, A5, D6 = 587.33, 698.46, 880.00, 1174.66

def kick(n=0.28):
    k = int(SR * n); t = np.arange(k) / SR
    f = 48 + 90 * np.exp(-t * 26)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(2.4 * np.sin(ph) * env(k, 0.001, 0.12))

def hoof():
    k = int(SR * 0.045)
    n = rng.normal(0, 1, k)
    return np.tanh(2.4 * (lp(n, 0.18) * env(k, 0.0004, 0.018) + 0.7 * hp(n, 0.45) * env(k, 0.0002, 0.006)))

def hat():
    k = int(SR * 0.04)
    return hp(rng.normal(0, 1, k), 0.55) * env(k, 0.0004, 0.016) * 0.45

def tom(f0=140):
    k = int(SR * 0.22); t = np.arange(k) / SR
    f = f0 + 40 * np.exp(-t * 18)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(1.8 * np.sin(ph) * env(k, 0.001, 0.09))

def metal():
    k = int(SR * 0.35); t = np.arange(k) / SR
    f = 1400 + 500 * np.sin(2 * np.pi * 28 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    n = hp(rng.normal(0, 1, k), 0.45)
    return np.tanh(1.4 * (0.6 * np.sin(ph) * env(k, 0.001, 0.07) + 0.5 * n * env(k, 0.001, 0.1)))

def boom(n=1.6):
    k = int(SR * n); t = np.arange(k) / SR
    f = 36 + 50 * np.exp(-t * 8)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(1.7 * np.sin(ph) * env(k, 0.002, 0.55)) + 0.45 * lp(rng.normal(0, 1, k), 0.04) * env(k, 0.001, 0.25)

def bell(f, n=1.4):
    k = int(SR * n); t = np.arange(k) / SR
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 2.2)
    s += 0.45 * np.sin(2 * np.pi * f * 2.37 * t) * np.exp(-t * 3.4)
    s += 0.2 * np.sin(2 * np.pi * f * 4.1 * t) * np.exp(-t * 5.0)
    return np.tanh(1.4 * s)

def bass(f, beats):
    k = int(SR * beats * BEAT); t = np.arange(k) / SR
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2 * t)
    return np.tanh(1.6 * s) * env(k, 0.004, beats * BEAT * 0.85) * 0.7

def mag_drone(beats, f=55.0):
    k = int(SR * beats * BEAT); t = np.arange(k) / SR
    rate = 1.5 + 7.0 * (t / max(t[-1], 1))
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * np.cumsum(rate) / SR)
    s = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * f * 1.997 * t)
    return s * trem * np.minimum(1, t / 0.5)

def spin_tone(beats, f0=320.0, f1=1600.0):
    k = int(SR * beats * BEAT); t = np.linspace(0, 1, k)
    f = f0 + (f1 - f0) * t ** 2
    ph = 2 * np.pi * np.cumsum(f) / SR
    a = 0.55 * np.sin(ph) + 0.35 * np.sin(ph * 1.015) + 0.15 * np.sin(ph * 2.01)
    return a * (t ** 1.3)

def nails(n=0.08):
    k = int(SR * n)
    return hp(rng.normal(0, 1, k), 0.7) * env(k, 0.0002, 0.012)

def air(beats):
    k = int(SR * beats * BEAT)
    return hp(rng.normal(0, 1, k), 0.35) * np.linspace(0.2, 1, k) * 0.25

def gallop(b0, b1, gain=1.0):
    """Three hoof-falls and a gap, the way a canter sits in 4/4."""
    bt = b0
    while bt < b1 - 0.01:
        for off, g, pan in ((0, 0.85, -0.35), (0.5, 0.7, 0.15), (1.0, 1.0, 0.4)):
            put(hoof(), bt + off, gain * g, pan)
        put(kick(), bt, 0.75 * gain)
        put(tom(150), bt + 1.0, 0.35 * gain, 0.2)
        bt += 2.0

# ---------------------------------------------------------------- arrangement
# 0-16 chase
gallop(0, 16, 0.9)
riff = [D2, D2, A2, F2, D2, C3, A2, F2]
for i, f in enumerate(riff):
    put(bass(f, 1.9), i * 2, 0.55)
for bt in range(0, 16):
    put(hat(), bt, 0.28, 0.4 if bt % 2 else -0.2)
put(metal(), 12, 0.9, 0.3)
put(boom(0.8), 12, 0.7)

# 16-40 the pull. gallop dies. the ground starts winning.
put(mag_drone(48, 51.9), 16, 0.42)          # through the name, into the spin
put(mag_drone(24, 77.8), 16, 0.18)
for bt in (16, 20, 24, 28, 32, 36):
    put(metal(), bt, 0.55, (bt - 26) * 0.04)
    put(kick(), bt, 0.4)
put(boom(1.2), 16, 0.65)
put(boom(0.9), 28, 0.55)
put(boom(1.0), 32, 0.6)

# 40-64 still the pull. no gallop. the force gets heavier as they close.
for bt in (40, 44, 48, 52, 56, 60):
    put(kick(), bt, 0.55)
    put(metal(), bt, 0.35, 0.2 if bt % 8 else -0.2)
put(boom(1.4), 48, 0.85)                    # if the three of them meet

# 64-76 the ball leaves and has to return
put(spin_tone(12, 280, 1700), 64, 0.55)
for bt, f in ((64, D5), (68, F5), (72, A5), (76, D6)):
    put(bell(f, 1.6), bt, 0.65)
put(air(4), 72, 0.7)

# 76-90 the rock scraps come back with the ball. one blow, then quiet.
put(boom(1.1), 76, 0.8)
put(bell(D6, 0.7), 76, 0.3)
for i, bt in enumerate((76, 76.5, 77.2, 78.4, 80)):
    put(nails(), bt, 0.4, pan=(i - 2) * 0.3)
put(boom(0.8), 90, 0.7)                     # the pull takes Tim's body

# 92-112 the rope. air and a slow pulse.
put(air(20), 92, 0.7)
put(mag_drone(20, 49.0), 92, 0.22)
for bt in (92, 96, 100, 104, 108):
    put(kick(), bt, 0.55)
    put(bell(D4, 1.8), bt, 0.28)
put(spin_tone(8, 500, 900), 100, 0.25)

# 112 title
put(boom(3.2), 112, 1.2)
put(bell(D4, 3.5), 112, 0.55)
put(bell(F4, 3.2), 112, 0.4)
put(bell(A4, 3.0), 112, 0.45)
put(bell(D5, 2.6), 112, 0.35)
put(metal(), 112, 0.6)

def reverb(x, sec=1.15, mix=0.2):
    k = int(SR * sec)
    ir = rng.normal(0, 1, k) * np.exp(-np.arange(k) / (SR * sec / 5))
    ir /= np.abs(ir).sum() ** 0.5 * 30
    n = 1 << int(np.ceil(np.log2(len(x) + k)))
    y = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[:len(x)]
    return x + mix * y

L, R = reverb(L), reverb(R)
mx = np.stack([L, R], 1)
peak = np.abs(mx).max() + 1e-9
mx = np.tanh(1.15 * mx / peak * 1.5)
fade = np.ones(N)
fi = int(SR * 0.25); fo = int(SR * 0.7)
fade[:fi] = np.linspace(0, 1, fi)
fade[-fo:] = np.linspace(1, 0, fo)
mx *= fade[:, None]
mx = (mx / (np.abs(mx).max() + 1e-9) * 0.92 * 32767).astype(np.int16)
with wave.open(os.path.join(HERE, 'music.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(mx.tobytes())
print('wrote music.wav', round(mx.shape[0] / SR, 2), 's')
