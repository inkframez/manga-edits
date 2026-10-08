"""Beat / section analysis for tokidoki-bg-song.mp3 (numpy only). Writes beatmap.json."""
import os, json, subprocess, numpy as np, imageio_ffmpeg
HERE = os.path.dirname(os.path.abspath(__file__))
SONG = os.path.join(os.path.dirname(HERE), 'tokidoki-bg-song.mp3')
SR = 22050
raw = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-i', SONG, '-ac', '1', '-ar', str(SR),
                      '-f', 'f32le', '-'], capture_output=True).stdout
y = np.frombuffer(raw, np.float32); dur = len(y) / SR
HOP, NF = 512, 2048
nfr = 1 + (len(y) - NF) // HOP
win = np.hanning(NF).astype(np.float32)
S = np.abs(np.fft.rfft(np.lib.stride_tricks.as_strided(y, (nfr, NF), (y.strides[0] * HOP, y.strides[0])) * win, axis=1))
freqs = np.fft.rfftfreq(NF, 1 / SR)
L = np.log1p(100 * S)
flux = np.maximum(0, np.diff(L, axis=0)).sum(1); flux = np.concatenate([[0], flux])
low = np.maximum(0, np.diff(L[:, freqs < 150], axis=0)).sum(1); low = np.concatenate([[0], low])
fps = SR / HOP
def smooth(x, n): k = np.hanning(n); return np.convolve(x, k / k.sum(), 'same')
oenv = flux - smooth(flux, int(fps * 1)); oenv = np.maximum(oenv, 0); oenv = oenv / oenv.std()
# tempo via autocorrelation over 60-180 bpm
ac = np.correlate(oenv - oenv.mean(), oenv - oenv.mean(), 'full')[len(oenv) - 1:]
lags = np.arange(len(ac)); bpm = 60 * fps / np.maximum(lags, 1)
m = (bpm > 60) & (bpm < 180)
cand = sorted(((ac[l], 60 * fps / l) for l in lags[m]), reverse=True)[:8]
period = 60 * fps / cand[0][1]
# refine bpm: weight towards 90-140 range
best = None
for l in np.arange(fps * 60 / 180, fps * 60 / 60, 0.05):
    idx = np.arange(0, len(oenv) - 1, l)
    for ph in np.linspace(0, l, 24, endpoint=False):
        sc = oenv[np.round(idx + ph).astype(int).clip(0, len(oenv) - 1)].mean()
        b = 60 * fps / l; sc *= np.exp(-0.5 * (np.log2(b / 120) / 0.9) ** 2)
        if best is None or sc > best[0]: best = (sc, l, ph)
_, l, ph = best; l = 0.5876 * fps; BPM = 60 * fps / l   # comb-filter estimate (tempo2.py): 102.1 bpm
# beat tracking: DP (Ellis) around period l
alpha = 100; N = len(oenv); score = oenv.copy(); prev = -np.ones(N, int)
for i in range(N):
    lo, hi = int(i - 2 * l), int(i - l / 2)
    if hi <= 0: continue
    js = np.arange(max(lo, 0), hi)
    pen = -alpha * np.log((i - js) / l) ** 2
    k = np.argmax(score[js] + pen); score[i] += score[js][k] + pen[k]; prev[i] = js[k]
i = int(np.argmax(score[-int(l * 2):]) + N - int(l * 2)); beats = []
while i >= 0: beats.append(i); i = prev[i]
beats = np.array(beats[::-1]) / fps
rms = np.sqrt(smooth((y[:nfr * HOP:HOP] ** 2), 9))
sec = np.arange(0, dur, 1.0)
energy = [float(np.sqrt((y[int(s * SR):int((s + 1) * SR)] ** 2).mean())) for s in sec]
lowE = [float(S[int(s * fps):int((s + 1) * fps)][:, freqs < 150].mean()) if int(s*fps) < len(S) else 0.0 for s in sec]
cent = [float((S[int(s * fps):int((s + 1) * fps)] * freqs).sum() / (S[int(s * fps):int((s + 1) * fps)].sum() + 1e-9)) for s in sec]
# strongest onsets (top 40, min 1.5s apart)
order = np.argsort(-oenv); picks = []
for k in order:
    t = k / fps
    if all(abs(t - p) > 1.5 for p in picks): picks.append(t)
    if len(picks) >= 40: break
# downbeat phase: which of 4 beat phases has the most low-end onset energy
lb = [low[np.round(beats[p::4] * fps).astype(int).clip(0, N - 1)].mean() for p in range(4)]
db_phase = int(np.argmax(lb))
out = dict(duration=dur, bpm=BPM, beats=[round(float(b), 3) for b in beats], downbeat_phase=db_phase,
           energy_per_s=[round(e, 4) for e in energy], low_per_s=[round(e, 3) for e in lowE],
           centroid_per_s=[round(c) for c in cent], strong_onsets=sorted(round(p, 2) for p in picks))
json.dump(out, open(os.path.join(HERE, 'beatmap.json'), 'w'), indent=1)
print('dur', round(dur, 2), 'bpm', round(BPM, 2), 'nbeats', len(beats), 'first beats', beats[:8].round(2), 'db phase', db_phase)
print('beat intervals median', np.median(np.diff(beats)).round(4))
e = np.array(energy); print('energy/s (x100):'); print(' '.join(f'{v*100:.0f}' for v in e))
print('low/s:'); print(' '.join(f'{v:.0f}' for v in lowE))
print('centroid/s:'); print(' '.join(f'{c/100:.0f}' for c in cent))
print('strong onsets', out['strong_onsets'])
