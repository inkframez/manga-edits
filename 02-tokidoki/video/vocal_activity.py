"""Estimate vocal phrases: centre (mid) energy in the vocal band minus side energy -> active segments."""
import subprocess, numpy as np, imageio_ffmpeg, json
SR = 22050
raw = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-i', '../tokidoki-bg-song.mp3', '-ac', '2', '-ar', str(SR),
                      '-f', 'f32le', '-'], capture_output=True).stdout
y = np.frombuffer(raw, np.float32).reshape(-1, 2)
M, Sd = (y[:, 0] + y[:, 1]) / 2, (y[:, 0] - y[:, 1]) / 2
NF, HOP = 2048, 441  # 20 ms hop
def stft(x):
    n = 1 + (len(x) - NF) // HOP
    fr = np.lib.stride_tricks.as_strided(x, (n, NF), (x.strides[0] * HOP, x.strides[0]))
    return np.abs(np.fft.rfft(fr * np.hanning(NF), axis=1))
Mm, Ss = stft(M), stft(Sd)
f = np.fft.rfftfreq(NF, 1 / SR); band = (f > 250) & (f < 3500)
# centre-only magnitude (soft mask: where mid dominates side)
mask = np.clip((Mm[:, band] - 1.6 * Ss[:, band]) / (Mm[:, band] + 1e-6), 0, 1)
v = (mask * Mm[:, band]).sum(1)
# harmonicity: peaky spectrum in band (vocals are harmonic) via spectral flatness inverse
lb = np.log(Mm[:, band] + 1e-6); flat = np.exp(lb.mean(1)) / (Mm[:, band].mean(1) + 1e-6)
v = v * (1 - flat)
k = np.hanning(15); v = np.convolve(v, k / k.sum(), 'same')
fps = SR / HOP
# adaptive threshold vs rolling median of 8 s
from numpy.lib.stride_tricks import sliding_window_view as swv
pad = int(4 * fps); vp = np.pad(v, pad, mode='edge')
med = np.median(swv(vp, 2 * pad + 1)[::5], axis=1); med = np.repeat(med, 5)[:len(v)]
act = v > np.maximum(med * 1.15, np.percentile(v, 30))
# segments
segs = []; on = None
for i, a in enumerate(act):
    if a and on is None: on = i
    if not a and on is not None:
        if i - on > 0.25 * fps: segs.append([on / fps, i / fps])
        on = None
merged = []
for s in segs:
    if merged and s[0] - merged[-1][1] < 0.30: merged[-1][1] = s[1]
    else: merged.append(s)
print('n segments', len(merged))
for a, b in merged: print(f'{a:7.2f} - {b:7.2f}  ({b-a:4.1f}s)')
json.dump(dict(vocal_segments=[[round(a, 2), round(b, 2)] for a, b in merged]), open('vocal_segments.json', 'w'))
# per-second vocal curve (normalised)
vs = v[: int(len(v) // fps) * int(fps)].reshape(-1, int(fps)).mean(1); vs = vs / vs.max()
print('vocal/s:', ' '.join(f'{x*9:.0f}' for x in vs))
