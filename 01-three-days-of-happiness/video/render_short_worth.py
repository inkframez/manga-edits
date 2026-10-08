"""Three Days of Happiness - "What is a life worth?" 20 s vertical Short (song 203.93-223.93 s, 1080x1920).

The 60 s cut's concept (colour = worth) compressed onto the song's biggest drop (206.67 s) and laid out for 9:16.
Built on render.py (cards with 3D-tilt entrances, hair warp, 2.5D drift, amber grade, light leak, fireflies, grain).
  0.0 s  hook: "So really, how much am I worth?" over the two of them in the grass; the lifespan counter starts.
  1.6 s  the sale: the counter crashes 30Y -> 3M and the price runs up to Y300,000 (cold grey).
  2.7 s  DROP: amber floods in, fireflies bloom out of the firefly field.
  7.2 s  her price glitches to Y30.  8.8 s  the hug on the biggest hit (hair in the wind).
 12.2 s  page 19 as a vertical triptych, one panel per beat; the counter is struck out.
 15.5 s  "were of much, much more value." - they walk off into the light; title.
Text: only lines printed on the pages (12, 19, 20); bubbles already on screen are never repeated as type.
Usage:  python render_short_worth.py stills 204,206,208   |   python render_short_worth.py sheet [step]
        python render_short_worth.py video -> ../three-days-short-worth.mp4
"""
import os, sys, math, subprocess
import numpy as np, cv2
from PIL import Image
import render as R
from render import clamp, eout, eio, lerp, keys, shot, page, font

T0, LEN = 203.93, 20.0
T1 = T0 + LEN                     # 223.93: the last hit (223.53) rings out, the song drops back to the verse
W, H, FPS = 1080, 1920, R.FPS
DROP = 206.67                     # the hit (an onset, just ahead of the beat grid)
HIT = 205.55                      # the onset before it: the sale
def G(k): return 214.45 + k * 0.8355     # beat grid of the drop section (fits 208.58 212.77 216.12 219.46 222.81)
OUT = os.path.join(R.ROOT, 'three-days-short-worth.mp4')

# ---------------------------------------------------------------- engine overrides (vertical)
R.W, R.H = W, H
R.DROP = DROP                     # fireflies bloom outward from the centre on the drop
R.S.clear(); R.BGC.clear()
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx / W - .5) * 2) ** 2 * 0.75 + ((_yy / H - .5) * 2) ** 2 * 0.75)
VIG = (1 - 0.42 * np.clip((_r - 0.5) / 0.8, 0, 1) ** 1.5).astype(np.float32)
_g = np.random.default_rng(3)
GRAIN = [cv2.resize(_g.normal(0, 0.03, (H // 2, W // 2)).astype(np.float32), (W, H)) for _ in range(8)]
LEAK = np.exp(-(((_xx - W) / (W * 0.6)) ** 2 + ((_yy - H * 0.15) / (H * 0.45)) ** 2)).astype(np.float32)
del _yy, _xx, _r

def background(si, sh, t):
    """blurred, darkened copy of the shot's first card (9:16), slowly pushing in."""
    if sh['bg'] == 'black': return np.full((H, W), 0.03, np.float32)
    if sh['bg'] == 'paper': return np.full((H, W), 0.95, np.float32)
    if si not in R.BGC:
        c = sh['cards'][0]; im = page(c['p'])[0]; x, y, w, h = c['r']
        cr = im[y:y + h, x:x + w]; k = max(270 / w, 480 / h)
        sm = cv2.resize(cr, (int(w * k) + 1, int(h * k) + 1), interpolation=cv2.INTER_AREA)
        oy, ox = (sm.shape[0] - 480) // 2, (sm.shape[1] - 270) // 2
        sm = cv2.GaussianBlur(sm[oy:oy + 480, ox:ox + 270], (0, 0), 7)
        R.BGC[si] = (0.035 + 0.24 * cv2.resize(sm, (W, H), interpolation=cv2.INTER_CUBIC)).astype(np.float32)
    u = (t - sh['t0']) / (sh['t1'] - sh['t0']); z = 1.0 + 0.06 * u
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
    return cv2.warpAffine(R.BGC[si], M, (W, H), borderMode=cv2.BORDER_REFLECT)

# ---------------------------------------------------------------- shots (song time; bleed rects are 9:16)
# 1  hook: the two of them in the grass, the question (the bubble itself is on the next panel, not shown)
shot(T0, HIT, [dict(p='12', r=[37, 0, 337, 347], w=1000, cy=1180, ent=0.6, frm=(0, 50), s1=1.06, kz=1.08, f=(0.5, 0.4))],
     bg='black')
# 2  the sale: Miyagi by the suitcase, counter crash
shot(HIT, DROP, [dict(p='02', r=[335, 468, 276, 492], h=1120, cy=1140, ent=0.35, es=1.12, frm=(0, 0), kz=1.12, f=(0.5, 0.3))])
# 3  DROP: the firefly field (hero panel + the two of them below)
shot(DROP, G(-6), [dict(p='10', r=[60, 392, 491, 276], w=1080, cy=1080, ent=0, s0=1.3, s1=1.0, frm=(0, 0), kz=1.1,
                        f=(0.5, 0.6), m=0),
                   dict(p='10', r=[0, 30, 611, 344], w=900, cy=540, t_in=G(-8) - DROP, ent=0.6, tilt=-14, kz=1.08,
                        f=(0.5, 0.7))])
# 4  a firefly in her hand
shot(G(-6), G(-4), [dict(p='11', r=[37, 0, 231, 410], bleed=True, ent=0, kz=1.2, f=(0.5, 0.78))])
# 5  her price
shot(G(-4), G(-2), [dict(p='12', r=[311, 369, 263, 269], h=920, cy=1220, ent=0.4, es=1.1, frm=(0, 0), kz=1.1, f=(0.6, 0.4))])
# 6  the hug on the biggest hit, then the pull-out
shot(G(-2), G(0), [dict(p='13', r=[230, 0, 540, 960], bleed=True, ent=0, kz=1.2, f=(0.45, 0.32), warp=True, shake=(0.0, 16))])
shot(G(0), G(2), [dict(p='13', r=[0, 0, 1222, 960], w=1080, cy=980, ent=0.5, s0=1.3, s1=1.0, frm=(0, 0), warp=True)])
# 7  page 19 as a vertical triptych - one panel per beat (their bubbles carry the words)
shot(G(2), G(6), [dict(p='19', r=[37, 0, 537, 313], w=900, cy=452, ent=0.45, frm=(-70, 0), tilt=-10),
                  dict(p='19', r=[37, 335, 537, 298], w=900, cy=987, t_in=G(3) - G(2), ent=0.45, frm=(70, 0), tilt=10),
                  dict(p='19', r=[37, 654, 537, 306], w=900, cy=1517, t_in=G(4) - G(2), ent=0.45, frm=(-70, 0), tilt=-10,
                       kz=1.06, f=(0.5, 0.6))])
# 8  value: they walk off into the light
shot(G(6), T1 + 0.1, [dict(p='20', r=[205, 400, 220, 440], h=1050, cy=1230, ent=1.4, frm=(0, 40), blend='mul',
                           s0=1.0, s1=1.08, d1=(0, -24), m=0)], bg='paper')

# ---------------------------------------------------------------- look: colour = worth
def warmth(t):
    return keys(t, [(T0, 0.0), (DROP - 0.01, 0.1), (DROP, 0.65), (G(-6), 0.9), (G(-2), 1.0), (G(2), 0.75),
                    (G(6) - 0.2, 0.75), (G(6) + 0.6, 1.0), (T1 + 1, 1.0)])
def density(t):
    return keys(t, [(T0, 0.0), (HIT, 0.04), (DROP - 0.01, 0.07), (DROP, 0.0), (DROP + 0.05, 1.0), (G(-2), 0.85),
                    (G(0), 1.0), (G(2) - 0.1, 0.9), (G(2) + 0.4, 0.3), (G(6), 0.3), (G(6) + 1.0, 0.6), (T1 + 1, 0.6)])
R.density = density
FLASHES = [(HIT, 0.45, 0.10), (DROP, 1.0, 0.45), (G(-6), 0.35, 0.18), (G(-2), 0.85, 0.32), (G(2), 0.30, 0.25),
           (G(6), 0.55, 0.6)]
GLITCH = (G(-4) + 0.25, G(-4) + 0.75)

# ---------------------------------------------------------------- text (page lines only)
CREAM, INK, AMB = R.CREAM, R.INK, R.AMBER
TEXTS = [
    dict(t=T0 + 0.10, end=HIT - 0.05, lines=['So really,', 'how much', 'am I worth?'], font=R.SERIF_I, size=92,
         align='c', y=230, lt=[T0 + 0.10, T0 + 0.45, T0 + 0.80], stagger=0.03, cdur=0.45, color=CREAM),
    dict(t=G(6) + 0.35, end=T1 + 1, lines=['were of much,', 'much more value.'], font=R.SERIF_I, size=84, align='c',
         y=250, lt=[G(6) + 0.35, G(7) + 0.2], stagger=0.04, color=INK, shadow=False),
    dict(t=G(8), end=T1 + 1, lines=['THREE DAYS OF HAPPINESS'], font=R.TITLE, size=40, align='c', y=1760, track=10,
         stagger=0.03, color=(0.36, 0.30, 0.25), shadow=False),
]

# ---------------------------------------------------------------- the counter: lifespan + price
def days_at(t):
    if t < HIT: return 30 * 365
    return int(lerp(30 * 365, 92, eio((t - HIT) / 0.9)))
def price_at(t):
    if t < HIT: return 0
    if t < GLITCH[0]: return int(lerp(0, 300000, eio((t - HIT) / 0.9)))
    return 30
def big_price(t):
    """large centred price: the sale (shot 2) and her price (shot 5)."""
    if HIT <= t < DROP: a = clamp((t - HIT) / 0.12) * clamp((DROP - t) / 0.08)
    elif G(-4) <= t < G(-2): a = clamp((t - G(-4)) / 0.15) * clamp((G(-2) - t) / 0.12)
    else: return None
    v = price_at(t)
    s = f'¥ {v:,}'
    if GLITCH[0] <= t < GLITCH[1]:
        rng = np.random.default_rng(int(t * 97))
        s = '¥ ' + ''.join(rng.choice(list('0123456789#%$/\\')) for _ in range(int(rng.integers(2, 8))))
    return dict(t=-1, end=99999, lines=[s], font=R.MONO, size=118, align='c', y=360, stagger=0, cdur=0.01, a=a)

HUD_T0, HUD_T1, STRIKE = T0 + 0.35, G(6) + 0.4, G(5)
def hud(Lr, t):
    if t < HUD_T0 or t > HUD_T1: return 0.0
    a = clamp((t - HUD_T0) / 0.4) * clamp((HUD_T1 - t) / 0.5)
    from PIL import ImageDraw
    d = ImageDraw.Draw(Lr); lab = font(R.MONO, 22); val = font(R.MONO, 38)
    dd = days_at(t); y, m, dy = dd // 365, (dd % 365) // 30, (dd % 365) % 30
    rows = [('LIFESPAN', f'{y:02d}Y {m:02d}M {dy:02d}D'), ('SOLD FOR', f'¥ {price_at(t):,}')]
    for i, (l, v) in enumerate(rows):
        yy = 96 + i * 58
        d.text((70, yy + 12), ' '.join(l), font=lab, fill=int(170 * a))
        if i == 1 and GLITCH[0] <= t < GLITCH[1]:
            rng = np.random.default_rng(int(t * 131))
            v = '¥ ' + ''.join(rng.choice(list('0123456789#%$')) for _ in range(int(rng.integers(2, 7))))
        d.text((330, yy), v, font=val, fill=int(240 * a))
    if t > STRIKE:                # the price stops meaning anything
        u = eout((t - STRIKE) / 0.45)
        for i in range(2):
            yy = 96 + i * 58 + 24
            d.line([(66, yy), (66 + 560 * u, yy)], fill=int(240 * a), width=4)
    return a

# ---------------------------------------------------------------- frame
SH_C, HI_C, SH_W, HI_W = R.SH_C, R.HI_C, R.SH_W, R.HI_W
def text_layer(rgb, sp, t, a=1.0):
    L = Image.new('L', (W, H), 0)
    if not R.draw_text(L, sp, t): return rgb
    ta = np.asarray(L, np.float32) / 255 * a
    if sp.get('shadow', True): rgb *= (1 - 0.6 * cv2.GaussianBlur(ta, (0, 0), 10))[..., None]
    if sp.get('glow'): rgb += (0.5 * cv2.GaussianBlur(ta, (0, 0), 14))[..., None] * AMB
    return rgb * (1 - ta[..., None]) + np.float32(sp.get('color', CREAM)) * ta[..., None]

def frame(fi):
    t = fi / FPS
    si = next((i for i, s in enumerate(R.S) if s['t0'] <= t < s['t1']), len(R.S) - 1)
    sh = R.S[si]
    cv = background(si, sh, t)
    for c in sh['cards']: R.render_card(cv, c, t, sh)
    cv = np.clip(cv, 0, 1)
    w = warmth(t)
    sh_c = lerp(SH_C, SH_W, w).astype(np.float32); hi_c = lerp(HI_C, HI_W, w).astype(np.float32)
    rgb = sh_c + (hi_c - sh_c) * cv[..., None]
    if w > 0.05:
        ox = int(120 * math.sin(t * 0.37)); lk = cv2.warpAffine(LEAK, np.float32([[1, 0, ox], [0, 1, 0]]), (W, H))
        rgb += (0.16 * w * lk)[..., None] * AMB
    ff = R.fireflies(t)
    if ff is not None:
        gain = 1.0 if sh['bg'] != 'paper' else 0.5
        rgb += (gain * ff)[..., None] * AMB
        rgb += (0.35 * gain * np.clip(ff - 0.6, 0, None))[..., None]
    for sp in TEXTS: rgb = text_layer(rgb, sp, t)
    bp = big_price(t)
    if bp: rgb = text_layer(rgb, bp, t, bp['a'])
    HL = Image.new('L', (W, H), 0); ha = hud(HL, t)
    if ha > 0:
        h_ = np.asarray(HL, np.float32) / 255
        if sh['bg'] == 'paper': rgb = rgb * (1 - h_[..., None]) + np.float32(INK) * h_[..., None]
        else:
            rgb *= (1 - 0.6 * cv2.GaussianBlur(h_, (0, 0), 6))[..., None]
            rgb = rgb * (1 - h_[..., None]) + np.float32(CREAM) * h_[..., None]
    if GLITCH[0] <= t < GLITCH[1]:      # RGB split + slice jitter on her price
        r_ = np.random.default_rng(fi); d = int(14 * (1 - (t - GLITCH[0]) / (GLITCH[1] - GLITCH[0]))) + 3
        rgb[..., 0] = np.roll(rgb[..., 0], d, 1); rgb[..., 2] = np.roll(rgb[..., 2], -d, 1)
        for _ in range(6):
            y0 = int(r_.integers(0, H - 80)); hh = int(r_.integers(10, 70))
            rgb[y0:y0 + hh] = np.roll(rgb[y0:y0 + hh], int(r_.integers(-70, 70)), 1)
    fl = sum(pk * math.exp(-(t - tf) / dc) for tf, pk, dc in FLASHES if t >= tf)
    if fl > 0.003: rgb = rgb + (np.float32([1.0, 0.97, 0.92]) - rgb) * min(fl, 1)
    rgb *= VIG[..., None]
    rgb += GRAIN[fi % 8][..., None]
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)

# ---------------------------------------------------------------- render
F0 = int(round(T0 * FPS)); NF = int(round(LEN * FPS))
STILLS = os.path.join(R.HERE, 'stills_short_worth')

def _still(tt): return tt, frame(int(round(tt * FPS)))

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
    tmpv = os.path.join(R.HERE, '_video_short_worth.mp4'); tmpa = os.path.join(R.HERE, '_audio_short_worth.m4a')
    subprocess.run([ff, '-y', '-v', 'error', '-ss', f'{T0:.3f}', '-t', f'{LEN:.3f}', '-i', R.SONG,
                    '-af', f'afade=t=in:d=0.05,afade=t=out:st={LEN - 0.6:.2f}:d=0.6,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000',
                    '-c:a', 'aac', '-b:a', '192k', tmpa], check=True)
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-maxrate', '9M', '-bufsize', '18M',
                          '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmpv], stdin=subprocess.PIPE)
    with Pool(max(1, os.cpu_count() - 1)) as pool:
        for i, fr in enumerate(pool.imap(frame, range(F0, F0 + NF), chunksize=4)):
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
