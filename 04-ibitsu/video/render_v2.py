"""Ibitsu v2 - a re-cut 20 s vertical Short (1080x1920, 30 fps) -> ../ibitsu-short-v2.mp4.

Same pages, grade, transitions and text engine as render.py; new running order and new times (EV2). The score for this
cut is music_v2.py, which reads EV2 so the stingers land on the same cuts.
Running order:
   0.0 s  cold stinger on the face (punch in)          9.4 s  first hit, the eye at 10.6 s
   1.1 s  "do you have a little sister?" over red       13.2 s  the stretched face (uncanny)
   3.6 s  REC, camcorder static                         14.6 s  silent beat
   5.6 s  the girl caption (drip)                       15.2 s  the scare, laughter column
   8.0 s  flicker into the hallway                      17.4 s  the red page, 妹、いる？ to 20 s
Usage:  python render_v2.py stills 0.5,4,9.5,15.5     (review frames in stills_v2/)
        python render_v2.py video                    (writes ../ibitsu-short-v2.mp4, mux music_v2.wav)
"""
import os, sys, subprocess
import numpy as np, cv2
import render as E
from render import FPS, JP, JPL, HAND

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
DUR = 20.0; N = int(round(DUR * FPS))
OUT = os.path.join(ROOT, 'ibitsu-short-v2.mp4')

def rc(x, y, w, h): return [x, y, w, h]

# ---------------------------------------------------------------- timeline (seconds) - shared with music_v2.py
EV2 = dict(cold=0.0, q=1.4, rec=3.6, girl=5.6, hit=8.0, sub1=9.4, eye=10.6, onii=11.5, uncanny=13.2,
           silence=14.6, scare=15.2, title=17.4, last_q=17.8)

SHOTS = [
    (0.0, 1.1, '15', rc(300, 260, 560, 996), rc(330, 380, 450, 800), dict(punch=True)),
    (1.1, 3.6, '01', rc(60, 40, 260, 462), rc(95, 95, 190, 338), dict(red=True)),
    (3.6, 5.6, '09', rc(130, 560, 440, 782), rc(215, 630, 300, 533), dict(tr='static', rec=True)),
    (5.6, 8.0, '02', rc(200, 40, 420, 747), rc(255, 300, 400, 711), dict(tr='drip')),
    (8.0, 9.4, '04', rc(130, 0, 460, 818), rc(235, 130, 230, 409), dict(tr='flick')),
    (9.4, 10.6, '10', rc(560, 0, 400, 711), rc(600, 30, 330, 587), dict(rec=True, shake=8)),
    (10.6, 11.5, '10', rc(650, 950, 300, 533), rc(735, 1015, 190, 338), dict(punch=True)),
    (11.5, 13.2, '11', rc(300, 600, 440, 782), rc(405, 770, 250, 444), dict(tr='flick')),
    (13.2, 14.6, '14', rc(500, 240, 460, 818), rc(575, 330, 290, 516), dict(tr='drip', uncanny=True)),
    (14.6, 15.2, None, None, None, dict()),                                        # the silent beat: black
    (15.2, 17.4, '15', rc(300, 260, 560, 996), rc(330, 380, 450, 800), dict(scare=True)),
    (17.4, DUR, '01', rc(300, 0, 472, 840), rc(330, 60, 420, 747), dict(red=True, tr='blood')),
]

TEXT = [   # t, t_end, text, font, size, x, y, vertical, colour, mode
    (EV2['q'], 3.4, 'do you have a little sister?', HAND, 60, E.W / 2, 1520, False, E.PALE, 'type'),
    (4.0, 5.5, 'WHOA... ARE THOSE SCRATCHES?', HAND, 40, E.W / 2, 1640, False, E.PALE, 'type'),
    (6.2, 7.9, 'ゴミ捨て場の少女', JPL, 74, 930, 640, True, E.PALE, 'reveal'),
    (EV2['onii'], 13.1, 'お兄ちゃん…', JP, 120, 900, 560, True, E.CRIM, 'reveal'),
    (EV2['scare'] + 0.15, 17.3, 'アハハハハハハ', JP, 150, 140, 900, True, E.CRIM, 'scroll'),
    (EV2['last_q'], DUR, '妹、いる？', JP, 150, E.W / 2, 900, True, E.CRIM, 'reveal'),
]

SUBLIM = [(EV2['sub1'], 2, '15', rc(450, 520, 400, 711)), (6.9, 1, '14', rc(560, 330, 300, 533)),
          (14.2, 1, '15', rc(420, 480, 420, 747)), (18.7, 3, '11', rc(450, 860, 160, 284))]
FLICK_DROPS = [2.2, 4.4, 7.1, 9.0, 12.0, 13.9, 16.6, 19.1]
SCARES = [(EV2['cold'], 0.4), (EV2['sub1'], 0.5), (EV2['eye'], 0.9), (EV2['scare'], 1.6)]

# the engine reads its timeline from these module globals, so point them at this cut
E.EV = EV2; E.SHOTS = SHOTS; E.TEXT = TEXT; E.SUBLIM = SUBLIM; E.FLICK_DROPS = FLICK_DROPS; E.SCARES = SCARES

def frame2(fi):                            # top-level so the Pool can pickle it
    return E.frame(fi)

def stills(times):
    d = os.path.join(HERE, 'stills_v2'); os.makedirs(d, exist_ok=True); th = []
    for tt in times:
        fr = E.frame(int(round(tt * FPS)))[..., ::-1]
        cv2.imwrite(os.path.join(d, f'{tt:06.2f}.png'), fr)
        s_ = cv2.resize(fr, (270, 480), interpolation=cv2.INTER_AREA)
        cv2.putText(s_, f'{tt:.2f}', (6, 22), 0, 0.6, (0, 255, 255), 2); th.append(s_)
    while len(th) % 8: th.append(np.zeros_like(th[0]))
    cv2.imwrite(os.path.join(d, 'contact.jpg'), np.vstack([np.hstack(th[i:i + 8]) for i in range(0, len(th), 8)]))

def video():
    import imageio_ffmpeg
    from multiprocessing import Pool
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmp = os.path.join(HERE, '_video_v2.mp4'); music = os.path.join(HERE, 'music_v2.wav')
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{E.W}x{E.H}', '-r', str(FPS),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '27', '-tune', 'grain',
                          '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmp], stdin=subprocess.PIPE)
    with Pool(max(1, os.cpu_count() - 1)) as pool:
        for i, fr in enumerate(pool.imap(frame2, range(N), chunksize=4)):
            p.stdin.write(fr.tobytes())
            if i % 150 == 0: print(f'frame {i}/{N}', flush=True)
    p.stdin.close(); p.wait()
    subprocess.run([ff, '-y', '-v', 'error', '-i', tmp, '-i', music, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-af', f'afade=t=in:st=0:d=0.1,afade=t=out:st={DUR - 0.5:.3f}:d=0.5,'
                    'loudnorm=I=-15:TP=-1.0:LRA=14,aresample=48000', '-c:a', 'aac', '-b:a', '192k',
                    '-t', f'{DUR:.3f}', '-movflags', '+faststart', OUT], check=True)
    os.remove(tmp); print('wrote', OUT)

if __name__ == '__main__':
    if sys.argv[1] == 'stills': stills([float(x) for x in sys.argv[2].split(',')])
    else: video()
