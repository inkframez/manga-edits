"""Toki Doki - LYRIC Short: chorus 2 (song 106.85-126.85 s), 1080x1920, 20 s.

Built on the lyric engine in render_lyrics.py (Japanese glyph animation, tategaki columns, hero words, English
translation, romaji rule lines, seals, plates, ECG, transitions) re-laid out for a vertical frame:
  * lyric zone on top (y 150-1150), manga panel zone below (y 1150-1900), so every line stays readable.
  * one lyric line per two bars: ドキドキして いいんだよ / 私の胸は 君の色 / 一秒ごとに 光が増える /
    ときどき 痛くて ときどき 嬉しい. The 1.2 s build before the drop is the loop point (ends on B(53)).
  * the "beats left" heart counter (HATSU TAKAGI) moves to the top-left corner.
Times below are SONG time.
Usage:  python render_lyrics_short.py stills 107,109,114,119,124   |   python render_lyrics_short.py sheet [step]
        python render_lyrics_short.py video -> ../tokidoki-short-lyrics.mp4
"""
import os, sys, subprocess
import numpy as np, cv2
import render_lyrics as E
from render_lyrics import B, shot, card, shp, sprinkle, hearts, bgp, band, lyric, ecg_sfx, label, blit, sprite, draw_shape
from render_lyrics import WH, SKY, SKYL, SKY2, BLU, PNK, PNKL, ROS, RED, CRM, CRML, MNT, LIL, LILL, NAV, GRY, SLT

T0, LEN = 106.85, 20.0
T1 = T0 + LEN                      # = B(53), the downbeat of the next line: the Short loops back into the build
W, H = 1080, 1920
E.W, E.H = W, H
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
E.PMAP = (_xx + 0.4 * _yy) / (W + 0.4 * H)
del _yy, _xx
E.PATC.clear()
E.DUR = 9999.0                     # no fade-to-white; the Short loops
for lst in (E.S, E.LINES, E.SFX, E.FLASH, E.SHAKE, E.GLITCH): lst.clear()
OUT = os.path.join(E.ROOT, 'tokidoki-short-lyrics.mp4')

PZ = 1520                          # centre of the panel zone

# ---------------------------------------------------------------- build (106.85-108.09): two beats into the drop
shot(T0, B(45), bgp('stripes', LILL, WH, P=100, r=0.5, v=(1, 1)),
     cards=[card('11sing', mode='frame', h=900, cy=PZ - 60, rot=-2, ent='slide-u', sc=LIL, kz=1.06, f=(0.5, 0.3))],
     bands=[band('ドキドキ   ', 330, 120, LIL, 0.55, v=90), band('ドキドキ   ', 560, 120, LIL, 0.35, v=-70)],
     texts=label(T0 + 0.05, 'TOKI DOKI  /  CHORUS', W / 2, 820, 30) +
           label(B(44, 3), '刻どキ', W / 2, 890, 34, st='tag'),
     shapes=sprinkle(T0, 8, 101, (LIL, PNK, SKY2), area=(80, 950, 1000, 1880)))

# ---------------------------------------------------------------- line 17: ドキドキして いいんだよ (108.09-112.76)
E.FLASH.append((B(45), 1.0, 0.3, WH)); E.SHAKE.append((B(45), 18, 6))
ECG = dict(t=B(45), y=1450, amp=230, mode='fast', c=WH, gc=WH, th=8, don=0.45, glow=0.3, x0=0, x1=W)
shot(B(45), B(46), bgp('hearts', RED, '#EE5F6C', P=120, r=20, v=(0, -2)),
     shapes=[shp('heart', W / 2, 640, 420, WH, B(45), bp=0.12, ent='pop', a=0.22)], ecg=[ECG], pulse=0.03,
     bands=[band('ドキドキ ', 1780, 90, WH, 0.14, v=60)])
ecg_sfx(ECG, B(45, 1), B(46), size=72, st='whiter', dx=-120)
shot(B(46), B(47), bgp('stars', PNKL, WH, P=110, r=15),
     cards=[card('11br', mode='frame', w=660, cy=PZ + 50, rot=2, ent='slide-u', sc=ROS, kz=1.08, f=(0.5, 0.35))],
     shapes=sprinkle(B(46), 10, 47, (ROS, SKY2, CRM), area=(60, 1150, 1020, 1880)), pulse=0.015)
lyric(17, '{ドキドキ}|して いいんだよ', 'v', x=640, y=170, size=112, sizes=[112, 92], hs=2.0, st='white', hst='white',
      hanim='stamp', hbp=0.10, echo='ドキドキ', ecol='outw', cps=[0.29, None, None], en_pos=(W / 2, 1150), en_w=760,
      enc=NAV, ena=0.92, ens=34, deco=())

# ---------------------------------------------------------------- line 18: 私の胸は 君の色 (112.76-117.54)
shot(B(47), B(48), bgp('dots', MNT, '#D9F5E8', P=64, r=9),
     cards=[card('08br', mode='frame', h=780, cx=W / 2, cy=PZ + 20, rot=3, ent='slide-u', sc=ROS)], pulse=0.02)
E.FLASH.append((B(48), 0.7, 0.2, WH))
shot(B(48), B(49), bgp('hearts', PNKL, WH, P=120, r=20, v=(0, -1)),
     cards=[card('02chest', mode='norm', w=720, cx=W / 2, cy=PZ, rot=-2, ent='punch', kz=1.1)],
     shapes=hearts(B(48), 12, 48, area=(60, 1150, 1020, 1880), size=(18, 40)), pulse=0.02)
lyric(18, '私の胸は|{君の色}', 'h', x=W / 2, y=300, size=112, hs=2.4, hcols=['redn', 'bluen', 'pinkn'], hanim='spin',
      plate='circle', pc=WH, psc=SKY2, pr=440, ens=34)

# ---------------------------------------------------------------- line 19: 一秒ごとに 光が増える (117.54-122.18)
E.FLASH.append((B(49), 0.9, 0.3, WH))
shot(B(49), B(50), bgp('stripes', CRM, CRML, P=100, r=0.5, v=(1, 1)),
     cards=[card('12girl', mode='frame', h=880, cx=W / 2, cy=PZ - 20, rot=2, ent='slide-u', kz=1.12, f=(0.6, 0.25), sc=ROS)],
     shapes=[shp('burst', W / 2, 560, 470, CRM, B(49), layer='back', a=0.95, ent='grow', spin=8)])
shot(B(50), B(51), bgp('plain', SKYL),
     cards=[card('10bike', mode='mul', w=1000, cx=W / 2, cy=PZ, ent='zoom', kz=1.12, f=(0.5, 0.5))],
     shapes=[shp('burst', W / 2, 560, 500, WH, B(50), layer='back', a=0.7, ent='grow', spin=12)] +
            sprinkle(B(50), 16, 50, (WH, CRM, SKY2), kinds=('plus', 'star'), size=(14, 34), step=0.05,
                     area=(60, 1120, 1020, 1880)),
     tr=('iris', 'circle', WH), pulse=0.02)
lyric(19, '一秒ごとに|{光}が増える', 'h', x=W / 2, y=280, size=104, hs=2.6, hst='whiteb', glow=True, gcol=CRM, hanim='blur',
      anim='pop', ens=34, deco=('meta', dict(k='seal', x=900, y=200, r=50, ch='秒', c=BLU, st='bluen', sub='01 SEC')))

# ---------------------------------------------------------------- line 20: ときどき 痛くて ときどき 嬉しい (122.18-126.85)
shot(B(51), B(52), bgp('grid', GRY, '#C9CFD9', P=120),
     cards=[card('14cry', mode='frame', w=940, cx=W / 2, cy=PZ, rot=-2, ent='slide-u', kz=1.1, f=(0.5, 0.4), sc=SLT)],
     pulse=0.015)
E.FLASH.append((B(52), 0.9, 0.25, '#FF8FB0'))
shot(B(52), T1 + 0.1, bgp('hearts', PNK, PNKL, P=120, r=20, v=(0, -2)),
     cards=[card('16hug', mode='frame', w=980, cx=W / 2, cy=PZ, rot=2, ent='zoom', kz=1.08, sc=RED)],
     shapes=hearts(B(52), 14, 52, area=(60, 1150, 1020, 1880), size=(18, 42), step=0.06), pulse=0.03)
lyric(20, '{ときどき}|[痛くて]|{ときどき}|嬉しい', 'v', x=780, y=190, size=104, st='ink', hst='inkp', hst2='grey',
      rst=['ink', 'ink', 'ink', 'pinkn'], col_dy=[0, 160, 0, 160], echo='ときどき', anim='drop', plate='card', pc=WH,
      psc=CRM, en_pos=(W / 2, 1010), en_w=620, ens=32)

# ---------------------------------------------------------------- HUD: her beats-left counter, top-left
HERS = lambda t: E.V_HERS - E.beats_between(E.HERS_START, t)
def hud(rgb, t):
    a = E.clamp((t - T0) / 0.3)
    v = HERS(t)
    nm = sprite('HATSU TAKAGI', 'label', 20, box='#111111')
    vs = sprite(f'{v:,} bts', 'mono', 36, box=NAV)
    x0, y0 = 60, 92
    blit(rgb, nm, x0 + 46 + nm.shape[1] / 2, y0 - 32, a=a)
    blit(rgb, vs, x0 + 46 + vs.shape[1] / 2, y0 + 12, a=a)
    draw_shape(rgb, dict(k='heart', x=x0 + 18, y=y0 + 10, s=20, c=RED, t=-9, ent='none', bp=0.45, a=a), t)
E.hud = hud

# ---------------------------------------------------------------- render
F0 = int(round(T0 * E.FPS)); NF = int(round(LEN * E.FPS))
STILLS = os.path.join(E.HERE, 'stills_lyrics_short')

def _still(tt): return tt, E.frame(int(round(tt * E.FPS)))

def stills(times, full=True):
    from multiprocessing import Pool
    os.makedirs(STILLS, exist_ok=True); th = {}
    with Pool(max(1, min(len(times), os.cpu_count()))) as pool:
        for tt, fr in pool.imap(_still, times):
            fr = fr[..., ::-1]
            if full: cv2.imwrite(os.path.join(STILLS, f'{tt:06.2f}.jpg'), fr, [cv2.IMWRITE_JPEG_QUALITY, 92])
            s = cv2.resize(fr, (270, 480), interpolation=cv2.INTER_AREA)
            cv2.putText(s, f'{tt - T0:.1f}s', (6, 22), 0, 0.6, (0, 0, 255), 2); th[tt] = s
    th = [th[t] for t in times]
    while len(th) % 8: th.append(np.zeros_like(th[0]))
    cv2.imwrite(os.path.join(STILLS, 'contact.jpg'), np.vstack([np.hstack(th[i:i + 8]) for i in range(0, len(th), 8)]))

def video():
    import imageio_ffmpeg
    from multiprocessing import Pool
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmpv = os.path.join(E.HERE, '_video_lyrics_short.mp4'); tmpa = os.path.join(E.HERE, '_audio_lyrics_short.m4a')
    subprocess.run([ff, '-y', '-v', 'error', '-ss', f'{T0:.3f}', '-t', f'{LEN:.3f}', '-i', E.SONG,
                    '-af', f'afade=t=in:d=0.08,afade=t=out:st={LEN - 0.5:.2f}:d=0.5,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000',
                    '-c:a', 'aac', '-b:a', '192k', tmpa], check=True)
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(E.FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                          '-tune', 'animation', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmpv],
                         stdin=subprocess.PIPE)
    with Pool(max(1, os.cpu_count() - 1)) as pool:
        for i, fr in enumerate(pool.imap(E.frame, range(F0, F0 + NF), chunksize=4)):
            p.stdin.write(fr.tobytes())
            if i % 150 == 0: print(f'frame {i}/{NF}', flush=True)
    p.stdin.close(); p.wait()
    subprocess.run([ff, '-y', '-v', 'error', '-i', tmpv, '-i', tmpa, '-map', '0:v', '-map', '1:a', '-c', 'copy',
                    '-t', f'{LEN:.3f}', '-movflags', '+faststart', OUT], check=True)
    os.remove(tmpv); os.remove(tmpa)
    print('wrote', OUT)

if __name__ == '__main__':
    if sys.argv[1] == 'stills': stills([float(x) for x in sys.argv[2].split(',')])
    elif sys.argv[1] == 'sheet':
        step = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
        stills([round(T0 + 0.3 + k * step, 2) for k in range(int((LEN - 0.3) / step) + 1)], full=False)
    else: video()
