"""Eerie score for the Ibitsu Short (27 s) -> music.wav. Fully synthesised (no samples); timed to render.EV.

Layers: sub drone with slow beating, dissonant string cluster, wind, a detuned music-box lullaby that slows and sags,
breathy whispers (formant-filtered noise), door creaks, a heartbeat that speeds up, camcorder static/hum,
crawling clicks, reverse-swell stingers, a dead-silent gap, then the scare: screech cluster + boom.
Usage: python music.py
"""
import os, wave, numpy as np
from render import EV, DUR

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100; N = int(SR * DUR)
rng = np.random.default_rng(66)
L = np.zeros(N); R_ = np.zeros(N)
t_all = np.arange(N) / SR

def put(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N or i + len(sig) <= 0: return
    s = sig[:N - i] * gain
    L[i:i + len(s)] += s * np.sqrt((1 - pan) / 2) * 1.41; R_[i:i + len(s)] += s * np.sqrt((1 + pan) / 2) * 1.41
def env(n, a, d): t = np.arange(n) / SR; return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)
def lp(x, a):
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)): acc += a * (x[i] - acc); y[i] = acc
    return y
def bp(x, f, q=8):   # simple resonant band-pass (biquad)
    w = 2 * np.pi * f / SR; al = np.sin(w) / (2 * q)
    b0, b2, a0, a1, a2 = al, -al, 1 + al, -2 * np.cos(w), 1 - al
    y = np.zeros_like(x); x1 = x2 = y1 = y2 = 0.0
    for i in range(len(x)):
        v = (b0 * x[i] + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1, y2, y1 = x1, x[i], y1, v; y[i] = v
    return y
def sec(a, b): return slice(int(a * SR), int(min(b, DUR) * SR))
def swell(t, a, b, fi=1.0, fo=1.0):
    return np.clip((t - a) / fi, 0, 1) * np.clip((b - t) / fo, 0, 1)

# ---------------------------------------------------------------- drone + strings + wind (beds)
mute = np.ones(N); mute[sec(EV['silence'], EV['scare'])] = 0             # the dead-silent beat
drone = (0.5 * np.sin(2 * np.pi * 36.7 * t_all) + 0.4 * np.sin(2 * np.pi * 38.1 * t_all) +
         0.25 * np.sin(2 * np.pi * 55.0 * t_all + 2 * np.sin(2 * np.pi * 0.11 * t_all)))
dlev = np.interp(t_all, [0, 2, 9, 14, 20, 21.25, 21.6, 23.6, 25.3, DUR], [0, .5, .6, .8, 1, 1, 1.1, .9, .4, .1])
put(drone * dlev * mute * 0.55, 0)
clus = sum(np.sin(2 * np.pi * f * t_all * (1 + 0.003 * np.sin(2 * np.pi * (4.6 + k) * t_all)))
           for k, f in enumerate([622.3, 659.3, 698.5, 932.3, 987.8]))
clev = np.interp(t_all, [0, 6, 9, 14.6, 17.3, 18, 20, 21.25, 21.6, DUR], [0, 0, .12, .2, .35, .12, .45, .7, 0, 0])
put(clus * clev * mute * 0.18, 0, pan=0.2)
wind = lp(rng.normal(0, 1, N), 0.02); wind = bp(wind, 420, 1.2) * 4
wlev = 0.5 + 0.5 * np.sin(2 * np.pi * 0.17 * t_all) ** 2
put(wind * wlev * np.interp(t_all, [0, 3, 14, 21.25, 21.6, 23.6, DUR], [.2, .5, .6, .6, 0, .5, .3]) * mute * 0.35, 0, pan=-0.3)

# ---------------------------------------------------------------- music box (detuned lullaby, sagging pitch)
def bell(f, dur=1.6, wob=0.0):
    k = int(SR * dur); t = np.arange(k) / SR
    f_t = f * (1 + wob * np.sin(2 * np.pi * 5 * t)) * (1 - 0.0 * t)
    ph = 2 * np.pi * np.cumsum(f_t) / SR
    s = np.sin(ph + 1.8 * np.sin(3.5 * ph) * np.exp(-t * 6)) + 0.3 * np.sin(2.76 * ph) * np.exp(-t * 3)
    return s * env(k, 0.002, 0.45) * 0.35
A4 = 440.0
def note(n): return A4 * 2 ** (n / 12)
mel = [7, 10, 12, 10, 7, 5, 7, -100, 7, 10, 12, 15, 14, 12, 10, -100]       # minor, lullaby-like
def play_box(t0, step, gain, sag=0.0, count=16):
    for i in range(count):
        n = mel[i % len(mel)]
        if n < -50: continue
        detune = 1 - sag * i / count
        put(bell(note(n + 12) * detune * (1 + rng.normal(0, 0.003)), wob=0.004), t0 + i * step * (1 + sag * i / count), gain, pan=0.35)
play_box(0.6, 0.36, 0.55, count=8)
play_box(EV['bars'], 0.42, 0.5, sag=0.06, count=6)
play_box(EV['title'] + 0.2, 0.45, 0.55, sag=0.18, count=10)                 # winds down, flat and slow

# ---------------------------------------------------------------- whispers (formant noise)
def whisper(dur, seed):
    r = np.random.default_rng(seed); k = int(SR * dur); n = r.normal(0, 1, k)
    out = np.zeros(k)
    for f, g in ((700, 1.0), (1150, 0.7), (2600, 0.5)):
        out += g * bp(n, f * r.uniform(0.9, 1.1), 6)
    syl = np.abs(np.sin(np.linspace(0, np.pi * r.integers(3, 6), k))) ** 0.6
    return out * syl * np.minimum(1, np.arange(k) / (SR * 0.05)) * np.minimum(1, (k - np.arange(k)) / (SR * 0.1)) * 0.6
put(whisper(1.3, 1), EV['q_en'] - 0.2, 0.9, pan=-0.6)
put(whisper(1.0, 2), EV['onii'], 1.0, pan=0.6); put(whisper(1.0, 3), EV['onii'] + 0.9, 0.7, pan=-0.6)
put(whisper(1.6, 4), EV['last_q'] + 0.2, 1.0, pan=0.0)

# ---------------------------------------------------------------- foley
def creak(dur, f0, f1, seed):
    r = np.random.default_rng(seed); k = int(SR * dur); t = np.arange(k) / SR
    f = np.interp(t, [0, dur], [f0, f1]) * (1 + 0.15 * r.normal(0, 1, k).cumsum() / np.sqrt(k))
    pulses = (np.sin(2 * np.pi * np.cumsum(f) / SR) > 0.97).astype(float)
    s = bp(pulses + 0.05 * r.normal(0, 1, k), 900, 3) + 0.6 * bp(pulses, 2200, 4)
    return s * np.minimum(1, t / 0.1) * np.minimum(1, (dur - t) / 0.2) * 3
put(creak(1.4, 18, 34, 1), EV['behind'] + 0.2, 0.6, pan=-0.4)
put(creak(2.0, 12, 40, 2), EV['door'] + 0.1, 0.8, pan=0.3)
def heartbeat(t0, t1, bpm0, bpm1):
    t = t0
    while t < t1:
        bpm = np.interp(t, [t0, t1], [bpm0, bpm1])
        for off, g in ((0, 1.0), (0.18, 0.7)):
            k = int(SR * 0.25); tt = np.arange(k) / SR
            put(np.sin(2 * np.pi * (48 + 30 * np.exp(-tt * 30)) * tt) * env(k, 0.003, 0.07), t + off, g * 0.9)
        t += 60 / bpm
heartbeat(EV['back'], EV['eye'], 64, 132)
heartbeat(EV['face'], EV['silence'] - 0.1, 90, 160)
k = int(SR * (EV['crawl'] - EV['rec'])); st = rng.normal(0, 1, k) * 0.12 + 0.05 * np.sin(2 * np.pi * 60 * np.arange(k) / SR)
put(st * np.minimum(1, np.arange(k) / (SR * 0.05)), EV['rec'], 0.8)
put(rng.normal(0, 1, int(SR * 0.25)) * 0.6, EV['rec'], 0.9)                 # static burst at the cut
for i in range(46):                                                         # crawling clicks ("kasa kasa")
    tt = EV['crawl'] + i * 0.019 + rng.uniform(0, 0.01)
    kk = int(SR * 0.012); put(bp(rng.normal(0, 1, kk), 3000, 2) * env(kk, 0.0005, 0.003) * 2, tt, 0.5, pan=rng.uniform(-.6, .6))

# ---------------------------------------------------------------- stingers
def boom(dur=3.0):
    k = int(SR * dur); t = np.arange(k) / SR
    return np.tanh(2 * np.sin(2 * np.pi * (30 + 60 * np.exp(-t * 5)) * t) * env(k, 0.003, 0.9)) + 0.4 * lp(rng.normal(0, 1, k), 0.04) * env(k, 0.002, 0.5)
def screech(dur, f=1180):
    k = int(SR * dur); t = np.arange(k) / SR
    s = sum(np.sin(2 * np.pi * ff * t + 3 * np.sin(2 * np.pi * ff * 1.41 * t)) for ff in (f, f * 1.06, f * 1.5, f * 0.71))
    return np.tanh(1.5 * s) * env(k, 0.005, dur * 0.5) * 0.35
def reverse_swell(dur):
    k = int(SR * dur); n = lp(rng.normal(0, 1, k), 0.2); return n * (np.arange(k) / k) ** 3 * 0.8
put(reverse_swell(0.6), EV['sub1'] - 0.6, 0.6); put(screech(0.5, 1500), EV['sub1'], 0.6); put(boom(1.2), EV['sub1'], 0.5)
put(reverse_swell(1.0), EV['eye'] - 1.0, 0.8); put(screech(1.0), EV['eye'], 0.9); put(boom(2.0), EV['eye'], 0.9)
put(reverse_swell(1.8), EV['silence'] - 1.8, 1.0)
put(screech(2.2, 980), EV['scare'], 1.3); put(screech(1.5, 1730), EV['scare'] + 0.05, 0.8, pan=0.5)
put(boom(4.0), EV['scare'], 1.4)
for i in range(10):                                                         # stuttering hits under the laughter
    put(boom(0.4), EV['scare'] + 0.3 + i * 0.17, 0.35, pan=(-1) ** i * 0.5)
put(boom(3.0), EV['title'], 0.6)
k = int(SR * 0.08); put(rng.normal(0, 1, k) * env(k, 0.001, 0.02), EV['last_eye'], 1.0)   # final click
put(screech(0.25, 2100), EV['last_eye'], 0.8)

# ---------------------------------------------------------------- reverb + master
def reverb(x, sec_=2.8, mix=0.35):
    k = int(SR * sec_); ir = rng.normal(0, 1, k) * np.exp(-np.arange(k) / (SR * sec_ / 6)); ir /= np.sqrt((ir ** 2).sum()) * 4
    n = 1 << int(np.ceil(np.log2(len(x) + k)))
    return x + mix * np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[:len(x)]
L, R_ = reverb(L), reverb(R_)
mx = np.stack([L, R_], 1)
mx[sec(EV['silence'] + 0.05, EV['scare'])] *= 0.0                             # keep the gap truly silent
mx = np.tanh(1.3 * mx / (np.abs(mx).max() + 1e-9) * 1.4)
fade = np.ones(N); fl = int(SR * 0.3); fade[-fl:] = np.linspace(1, 0, fl); mx *= fade[:, None]
mx = (mx / np.abs(mx).max() * 0.95 * 32767).astype(np.int16)
with wave.open(os.path.join(HERE, 'music.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(mx.tobytes())
print('wrote music.wav')
