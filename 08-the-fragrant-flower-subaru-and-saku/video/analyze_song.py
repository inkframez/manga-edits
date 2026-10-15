"""Cut the excerpt of BEAUZ & JVNA - Crazy [NCS Release] used by the edit and map its real drum hits.

The song is not in the repo (it is NCS's file to distribute): download it from http://ncs.io/_Crazy and save it
as video/crazy.mp3. This writes video/song_cut.wav (the excerpt, also gitignored) and video/beatmap_ff.json
(kick and snare onsets in edit seconds), which render_ff.py uses for its beat pulses.
Usage:  python analyze_song.py
"""
import json, subprocess, wave
from pathlib import Path
import numpy as np
import imageio_ffmpeg
from timeline_ff import SONG_START, DUR

HERE = Path(__file__).resolve().parent
SR = 44100


def main():
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    src = HERE / 'crazy.mp3'
    if not src.exists(): raise SystemExit('download the song from http://ncs.io/_Crazy and save it as video/crazy.mp3')
    subprocess.run([ff, '-y', '-loglevel', 'error', '-ss', f'{SONG_START:.3f}', '-t', f'{DUR:.3f}', '-i', str(src),
                    '-af', f'afade=t=in:d=0.12,afade=t=out:st={DUR - 1.6:.3f}:d=1.6', '-ar', str(SR), '-ac', '2',
                    str(HERE / 'song_cut.wav')], check=True)
    w = wave.open(str(HERE / 'song_cut.wav')); x = np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, 2).mean(1) / 32768
    hop, win = 256, 2048; fps = SR / hop
    fr = np.lib.stride_tricks.sliding_window_view(x, win)[::hop] * np.hanning(win)
    S = np.log1p(np.abs(np.fft.rfft(fr, axis=1)) * 10); df = SR / win
    def onsets(lo, hi, k, gap):
        a = np.maximum(np.diff(S[:, int(lo / df):int(hi / df)], axis=0), 0).sum(1)
        out, last = [], -1
        for i in range(2, len(a) - 2):
            j0, j1 = max(0, i - int(2 * fps)), min(len(a), i + int(2 * fps))
            thr = a[j0:j1].mean() + k * a[j0:j1].std()
            t = (i + 1) * hop / SR + win / 2 / SR
            if a[i] > thr and a[i] == a[i - 2:i + 3].max() and t - last > gap:
                out.append(round(t, 3)); last = t
        return out
    kicks = onsets(30, 140, 1.6, .2); snares = onsets(1500, 7000, 1.8, .2)
    json.dump({'song_start': SONG_START, 'kicks': kicks, 'snares': snares}, open(HERE / 'beatmap_ff.json', 'w'), indent=1)
    print(f'song_cut.wav {DUR:.2f}s; {len(kicks)} kicks, {len(snares)} snares -> beatmap_ff.json')


if __name__ == '__main__':
    main()
