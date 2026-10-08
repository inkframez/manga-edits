"""Toki Doki - 20 s vertical Short (1080x1920), final-chorus window of the song.

Reuses the engine in render.py (patterns, cards, shapes, ECG, transitions) with a vertical layout and only a few
stand-out Japanese words: ドキドキ / 君の色 / 光 / ときどき (痛・嬉) / ありがとう. Times below are SONG time.
Usage:  python render_short.py stills 176,181,186   |   python render_short.py video  -> ../tokidoki-short.mp4
"""
import os, sys, math, subprocess
import numpy as np, cv2
import render as E
from render import B, shot, card, shp, sprinkle, hearts, bgp, nb
from render import WH, SKY, SKYL, SKY2, BLU, PNK, PNKL, ROS, RED, CRM, CRML, MNT, NAV, GRY, LILL

T0, LEN = 175.60, 20.0
T1 = T0 + LEN
W, H = 1080, 1920
E.W, E.H = W, H
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
E.PMAP = (_xx + 0.4 * _yy) / (W + 0.4 * H)
del _yy, _xx
E.DUR = 9999.0                     # no fade-to-white; the Short loops
E.S.clear(); E.FLASH.clear(); E.SHAKE.clear(); E.GLITCH.clear()
E.HUDS = []
OUT = os.path.join(E.ROOT, 'tokidoki-short.mp4')

E.R['10bikeV'] = ('10', [230, 800, 400, 450])
E.R['09funV'] = ('09', [520, 900, 439, 500])

JP = E.JP
E.STY.update({
    'jpw': dict(font=JP, fill=WH, sh=NAV, so=0.06, stroke=NAV, sw=0.03),
    'jpr': dict(font=JP, fill=RED, sh=NAV, so=0.05, stroke=WH, sw=0.07),
    'jpp': dict(font=JP, fill=ROS, sh=NAV, so=0.05, stroke=WH, sw=0.07),
    'jpb': dict(font=JP, fill=BLU, sh=NAV, so=0.05, stroke=WH, sw=0.07),
})

def jp(t, s, x, y, size, st='jpw', step=0.12, vertical=False, ent='stamp', styles=None, **kw):
    """one item per character; horizontal centred on x, or a vertical column starting at y."""
    out, n = [], len(s)
    for i, ch in enumerate(s):
        if vertical: cx, cy = x, y + i * size * 1.04
        else: cx, cy = x + (i - (n - 1) / 2) * size * 1.0, y
        out.append(dict(s=ch, st=(styles[i] if styles else st), size=size, x=cx, y=cy, t=t + i * step, ent=ent, **kw))
    return out

def seal(ch, x, y, r, col, t, k='circle', st='jpw'):
    """hanko-style stamp: coloured shape + one big character."""
    return ([shp(k, x, y, r, col, t, ol=6, oc=WH, layer='front', ent='spin', bp=0.08)],
            [dict(s=ch, st=st, size=int(r * 1.15), x=x, y=y + r * 0.02, t=t + 0.08, ent='stamp')])

# ---------------------------------------------------------------- the 20 s
E.FLASH.append((B(74), 1.0, 0.25, WH)); E.SHAKE.append((B(74), 20, 6))
shot(T0, B(75), bgp('hearts', RED, '#EE5F6C', P=120, r=20, v=(0, -2)),
     cards=[card('02hatsu', mode='norm', h=1250, cy=1150, rot=-3, ent='punch', sc=NAV)],
     ecg=[dict(t=T0, y=480, amp=90, mode='fast', c=WH, gc=PNK, th=7, don=0.35, glow=0.4)],
     texts=jp(B(74), 'ドキドキ', W / 2, 290, 230, step=0.29, sh=RED),
     shapes=hearts(B(74, 1), 8, 1, cols=(WH, PNK), area=(60, 560, 1020, 1800)), pulse=0.03)
shot(B(75), B(76), bgp('dots', PNK, PNKL, P=70, r=10),
     cards=[card('12hands', mode='frame', h=1150, cy=1080, rot=4, ent='pop', sc=RED)],
     texts=[dict(s='ドキ', st='jpr', size=170, x=300, y=330, t=B(75), ent='stamp', rot=-8),
            dict(s='ドキ', st='jpr', size=170, x=780, y=470, t=B(75, 2), ent='stamp', rot=8)],
     shapes=hearts(B(75), 12, 2, size=(20, 44), area=(80, 600, 1000, 1700), step=0.1), pulse=0.03)
shot(B(76), B(77), bgp('stripes', PNKL, WH, P=110, r=0.5, v=(1, 1)),
     cards=[card('12girl', mode='frame', h=1250, cy=1150, rot=-2, ent='slide-u', kz=1.1, f=(0.6, 0.25), sc=ROS)],
     texts=jp(B(76), '君の色', W / 2, 300, 250, step=0.29, styles=['jpp', 'jpb', 'jpr']),
     shapes=sprinkle(B(76, 1), 8, 3, (ROS, SKY2, RED), area=(60, 520, 1020, 1800)), pulse=0.02)
_ss, _st = seal('色', 860, 330, 130, ROS, B(77, 1))
shot(B(77), B(78), bgp('dots', MNT, '#D9F5E8', P=64, r=9),
     cards=[card('09funV', mode='frame', h=1200, cy=1080, rot=3, ent='pop', sc=ROS)],
     shapes=_ss + hearts(B(77), 8, 4, area=(60, 600, 1020, 1750)), texts=_st, pulse=0.025)
E.FLASH.append((B(78), 0.9, 0.3, WH))
shot(B(78), B(79), bgp('plain', SKYL),
     cards=[card('10bikeV', mode='mul', bleed=True, kz=1.1, f=(0.5, 0.5))],
     shapes=[shp('circle', W / 2, 520, 300, CRM, B(78), a=0.75, ent='grow', bp=0.08, layer='front'),
             shp('burst', W / 2, 520, 330, WH, B(78), a=0.5, spin=20, layer='back')] +
            sprinkle(B(78), 16, 5, (WH, CRM), kinds=('plus',), size=(14, 34), step=0.05),
     texts=[dict(s='光', st='jpw', size=420, x=W / 2, y=520, t=B(78) + 0.05, ent='stamp', sh=SKY2, bp=0.05)],
     tr=('iris', 'circle', WH), pulse=0.02)
_ss, _st = seal('光', 200, 330, 120, SKY2, B(79, 1), k='circle')
shot(B(79), B(80), bgp('stars', CRM, CRML, P=110, r=15),
     cards=[card('02hato', mode='norm', h=1250, cy=1100, rot=-3, ent='slide-l')],
     shapes=_ss + sprinkle(B(79), 10, 6, (WH, SKY2, CRM), kinds=('plus', 'star'), area=(60, 500, 1020, 1800)),
     texts=_st, pulse=0.025)
E.FLASH.append((B(80), 0.9, 0.18, '#FF5A68')); E.GLITCH.append((B(80), B(80) + 0.3))
_ss, _st = seal('痛', 850, 560, 120, RED, B(80, 2))
shot(B(80), B(81), bgp('grid', GRY, '#C9CFD9', P=120),
     cards=[card('13phone', mode='frame', h=1150, cy=1160, ent='punch', kz=1.25, f=(0.55, 0.5), sc=RED)],
     texts=jp(B(80), 'ときどき', W / 2, 300, 210, st='jpp', step=0.15, ent='pop') + _st, shapes=_ss)
_ss, _st = seal('嬉', 850, 560, 125, ROS, B(81, 2), k='heart')
shot(B(81), B(82), bgp('hearts', PNK, PNKL, P=120, r=20, v=(0, -2)),
     cards=[card('16couple', mode='frame', h=1250, cy=1150, ent='zoom', kz=1.08, sc=RED)],
     texts=jp(B(81), 'ときどき', W / 2, 300, 210, st='jpp', step=0.15, ent='pop') + _st,
     shapes=_ss + hearts(B(81), 14, 7, area=(60, 650, 1020, 1800), size=(18, 40)), pulse=0.03)
E.FLASH.append((B(82), 1.0, 0.35, WH))
shot(B(82), T1 + 0.1, bgp('dots', PNKL, WH, P=70, r=8),
     cards=[card('18face', mode='frame', h=1150, cx=640, cy=1000, ent='zoom', kz=1.1, f=(0.5, 0.4), sc=RED)],
     texts=jp(B(82) + 0.05, 'ありがとう', 130, 420, 150, st='jpr', step=0.11, vertical=True, ent='drop'),
     shapes=hearts(B(82), 14, 8, area=(60, 300, 1020, 1750), size=(18, 42), step=0.06), pulse=0.02)

# ---------------------------------------------------------------- render
F0 = int(round(T0 * E.FPS)); NF = int(round(LEN * E.FPS))

def stills(times):
    d = os.path.join(E.HERE, 'stills_short'); os.makedirs(d, exist_ok=True)
    th = []
    for tt in times:
        fr = E.frame(int(round(tt * E.FPS)))[..., ::-1]
        cv2.imwrite(os.path.join(d, f'{tt:06.2f}.png'), fr)
        s = cv2.resize(fr, (270, 480), interpolation=cv2.INTER_AREA)
        cv2.putText(s, f'{tt - T0:.1f}s', (6, 22), 0, 0.6, (0, 0, 255), 2); th.append(s)
    while len(th) % 8: th.append(np.zeros_like(th[0]))
    cv2.imwrite(os.path.join(d, 'contact.jpg'), np.vstack([np.hstack(th[i:i + 8]) for i in range(0, len(th), 8)]))

def video():
    import imageio_ffmpeg
    from multiprocessing import Pool
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmpv = os.path.join(E.HERE, '_video_short.mp4'); tmpa = os.path.join(E.HERE, '_audio_short.m4a')
    subprocess.run([ff, '-y', '-v', 'error', '-ss', f'{T0:.3f}', '-t', f'{LEN:.3f}', '-i', E.SONG,
                    '-af', f'afade=t=in:d=0.08,afade=t=out:st={LEN - 0.6:.2f}:d=0.6,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000',
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
    else: video()
