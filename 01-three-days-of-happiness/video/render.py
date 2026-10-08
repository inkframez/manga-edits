"""Three Days of Happiness - 60s motion piece (1920x1080, 30fps).

Usage:
  python render.py stills 0,2.5,17.5        -> PNG stills + contact sheet in ./stills
  python render.py video                    -> ../three-days-of-happiness.mp4
Concept: colour = worth. Cold grayscale until the firefly drop, amber takes over,
drains during the doubt beat, returns for the ending. Music window: song 189.5s-249.5s.
"""
import os, sys, math, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAN = os.path.join(ROOT, 'panels')
SONG = os.path.join(ROOT, '01-tdoh-bg-song.mp3')
OUT = os.path.join(ROOT, 'three-days-of-happiness.mp4')
W, H, FPS, N = 1920, 1080, 30, 1800
SONG_START = 189.5
FD = 'C:/Windows/Fonts/' if os.name == 'nt' else os.path.join(os.path.dirname(ROOT), 'fonts') + '/'   # tools/setup_fonts.py
cv2.setNumThreads(1)

# ---------------------------------------------------------------- easing
def clamp(u): return min(max(u, 0.0), 1.0)
def eout(u): u = clamp(u); return 1 - (1 - u) ** 3
def eio(u):
    u = clamp(u); return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2
def lerp(a, b, u): return a + (b - a) * u
def keys(t, pts):
    """piecewise smooth interpolation through [(t, v), ...]"""
    if t <= pts[0][0]: return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t1: return lerp(v0, v1, eio((t - t0) / max(t1 - t0, 1e-6)))
    return pts[-1][1]

# ---------------------------------------------------------------- beats (video time)
DROP = 17.19          # song 206.69 - the big hit
BEAT = 0.835          # 72 bpm grid, phase from loud section
def g(n): return 24.97 + (n - 9) * BEAT   # g(9)=24.97

# ---------------------------------------------------------------- pages
PAGES = {}
def page(n):
    if n not in PAGES:
        fn = [p for p in os.listdir(PAN) if p.split('.')[0] == n][0]
        im = np.asarray(Image.open(os.path.join(PAN, fn)).convert('L'), np.float32) / 255
        h, w = im.shape
        s = 3.0 if w < 700 else 2.0
        up = cv2.resize(im, (int(w * s), int(h * s)), interpolation=cv2.INTER_LANCZOS4)
        bl = cv2.GaussianBlur(up, (0, 0), 1.4)
        up = np.clip(up + 0.7 * (up - bl), 0, 1)
        PAGES[n] = (im, up, s)
    return PAGES[n]

# ---------------------------------------------------------------- shots
# card keys: p page, r src rect [x,y,w,h] (page px), h|w frame size, cx/cy centre,
# s0/s1 scale drift, d0/d1 offset drift, kz/f inner Ken Burns zoom + focus,
# t_in delay, ent entrance dur, frm entrance offset, tilt entrance Y-rotation,
# bleed full-frame, blend 'mul', shatter (rel time), warp hair, shake (rel t, amp)
S = []
def shot(t0, t1, cards, bg='blur', **kw): S.append(dict(t0=t0, t1=t1, cards=cards, bg=bg, **kw))

# Act I - the sale
shot(0.0, 2.58, [], bg='black')
shot(2.58, 5.55, [
    dict(p='01', r=[37, 0, 566, 487], h=690, cx=515, cy=540, frm=(-60, 0), ent=0.7, tilt=-16, s1=1.035),
    dict(p='01', r=[37, 509, 537, 451], h=690, cx=1405, cy=540, t_in=0.83, frm=(60, 0), ent=0.7, tilt=16, s1=1.035)])
shot(5.55, 6.32, [], bg='black')
shot(6.32, 8.78, [dict(p='02', r=[37, 0, 537, 448], h=780, cx=1250, cy=540, tilt=20, ent=0.8,
                       kz=1.10, f=(0.62, 0.35))])
shot(8.78, 11.55, [dict(p='02', r=[335, 468, 276, 492], h=900, cx=1370, cy=540, frm=(0, 50), ent=0.9,
                        kz=1.14, f=(0.45, 0.3))])
# Act II - the observer
shot(11.55, 13.61, [
    dict(p='03', r=[56, 136, 213, 487], h=760, cx=380, cy=540, d0=(-40, 0), d1=(70, 0), ent=0.5),
    dict(p='03', r=[274, 136, 572, 487], h=760, cx=1210, cy=540, d0=(60, 0), d1=(-50, 0), t_in=0.25, ent=0.5)])
shot(13.61, 14.45, [dict(p='03', r=[474, 942, 372, 369], h=840, ent=0.3, es=1.12, frm=(0, 0))])
shot(14.45, 15.25, [dict(p='06', r=[56, 136, 790, 378], w=1560, ent=0.3, es=1.12, frm=(0, 0))])
shot(15.25, 16.07, [dict(p='06', r=[446, 532, 400, 352], h=820, ent=0.3, es=1.12, frm=(0, 0), kz=1.15)])
shot(16.07, 16.62, [dict(p='09', r=[37, 271, 537, 359], w=1380, ent=0.2, es=1.06, frm=(0, 0))])
shot(16.62, DROP, [dict(p='07', r=[56, 525, 790, 302], w=1560, ent=0.2, es=1.08, frm=(0, 0), s1=1.08)])
# Act III - fireflies
shot(DROP, 21.63, [dict(p='10', r=[0, 30, 611, 344], bleed=True, ent=0, rB=[60, 392, 491, 276])])
shot(21.63, 23.30, [
    dict(p='11', r=[37, 0, 268, 410], h=820, cx=680, cy=540, ent=0.6, frm=(0, 40), kz=1.12, f=(0.4, 0.75)),
    dict(p='11', r=[309, 0, 265, 410], h=820, cx=1240, cy=540, ent=0.6, frm=(0, -40), t_in=0.42)])
shot(23.30, g(9), [dict(p='11', r=[37, 682, 537, 278], w=1420, ent=0.5, tilt=-14, kz=1.08, f=(0.7, 0.5))])
shot(g(9), g(12), [
    dict(p='12', r=[37, 369, 270, 269], h=760, cx=560, cy=540, ent=0.5, frm=(-50, 0)),
    dict(p='12', r=[311, 369, 263, 269], h=760, cx=1360, cy=540, ent=0.5, frm=(50, 0), t_in=BEAT)])
shot(g(12), g(17), [dict(p='13', r=[53, 20, 927, 521], bleed=True, ent=0, kz=1.32, f=(0.43, 0.52),
                         warp=True, shake=(0.0, 14))])
shot(g(17), g(20), [dict(p='14', r=[37, 0, 537, 455], h=900, ent=0.4, s0=1.45, s1=1.0, frm=(0, 0))])
# Act IV - warmth, then doubt
shot(g(20), 36.6, [dict(p='15', r=[37, 0, 537, 273], w=1500, ent=0.6, frm=(0, 40))])
shot(36.6, 38.92, [dict(p='15', r=[37, 295, 537, 252], w=1500, ent=0.6, tilt=12, kz=1.1, f=(0.5, 0.5))])
shot(38.92, 43.59, [dict(p='16', r=[37, 327, 537, 560], h=900, ent=0.9, frm=(0, 40), s1=1.06, kz=1.08, f=(0.4, 0.4))])
shot(43.59, 47.77, [dict(p='17', r=[37, 0, 537, 960], h=950, ent=0.6, s1=1.05, shatter=2.5)])
shot(47.77, 50.0, [dict(p='18', r=[0, 47, 548, 913], h=1010, ent=0.8, kz=1.28, f=(0.5, 0.32))])
# Act V - value
shot(50.0, 51.73, [dict(p='19', r=[37, 0, 537, 313], w=1500, ent=0.5, frm=(-80, 0), kz=1.05)])
shot(51.73, 53.44, [dict(p='19', r=[37, 335, 537, 298], w=1500, ent=0.5, frm=(-80, 0), kz=1.05)])
shot(53.44, 55.85, [dict(p='19', r=[37, 654, 537, 306], w=1500, ent=0.5, frm=(-80, 0), kz=1.08, f=(0.5, 0.6))])
shot(55.85, 60.01, [dict(p='20', r=[205, 400, 220, 440], h=640, cy=600, ent=1.6, frm=(0, 30), blend='mul',
                         s0=1.0, s1=1.07, d1=(0, -16), m=0)], bg='paper')

# ---------------------------------------------------------------- text
SERIF_I = FD + 'georgiai.ttf'
TITLE = FD + 'constan.ttf'
MONO = FD + 'consola.ttf'
CREAM = (0.97, 0.93, 0.86)
INK = (0.13, 0.10, 0.08)
TEXTS = [
    dict(t=0.24, end=2.55, lines=['What is a life worth?'], font=SERIF_I, size=68, align='c', y=500),
    dict(t=6.62, end=8.70, lines=['I sold off all', 'but three months', 'of my life.'], font=SERIF_I, size=60,
         x=150, y=370, lt=[6.62, 7.12, 7.62]),
    dict(t=9.55, end=11.45, lines=['Then, the next day,', 'a girl came to my room.'], font=SERIF_I, size=62,
         x=150, y=440, lt=[9.55, 10.66]),
    dict(t=17.75, end=21.35, lines=['THREE DAYS OF HAPPINESS'], font=TITLE, size=70, align='c', y=230,
         track=22, stagger=0.045, cdur=0.9, glow=True),
    dict(t=56.59, end=60.5, lines=['were of much, much more value.'], font=SERIF_I, size=58, align='c', y=120,
         color=INK, shadow=False, stagger=0.04),
    dict(t=57.75, end=60.5, lines=['THREE DAYS OF HAPPINESS'], font=TITLE, size=30, align='c', y=968,
         track=12, color=(0.36, 0.30, 0.25), shadow=False, stagger=0.02),
]
_FONTS = {}
def font(path, size):
    k = (path, size)
    if k not in _FONTS: _FONTS[k] = ImageFont.truetype(path, size)
    return _FONTS[k]

def draw_text(L, spec, t):
    """draw animated text spec into PIL 'L' image (alpha). returns True if drawn."""
    if t < spec['t'] - 0.01 or t > spec['end']: return False
    f = font(spec['font'], spec['size'])
    track = spec.get('track', 0); stg = spec.get('stagger', 0.028); cd = spec.get('cdur', 0.55)
    rise = spec.get('rise', 22); lh = spec['size'] * 1.32
    fade = clamp((spec['end'] - t) / 0.45)
    d = ImageDraw.Draw(L)
    lts = spec.get('lt', [spec['t']] * len(spec['lines']))
    for li, line in enumerate(spec['lines']):
        widths = [f.getlength(ch) + track for ch in line]
        tw = sum(widths) - track
        x = (W - tw) / 2 if spec.get('align') == 'c' else spec['x']
        y = spec['y'] + li * lh
        for ci, ch in enumerate(line):
            u = eout((t - lts[li] - ci * stg) / cd)
            if u > 0 and ch != ' ':
                d.text((x, y + rise * (1 - u)), ch, font=f, fill=int(255 * u * fade))
            x += widths[ci]
    return True

# ---------------------------------------------------------------- HUD counter
def days_at(t):
    if t < 6.32: return 30 * 365
    if t < 7.8: return int(lerp(30 * 365, 92, eio((t - 6.32) / 1.48)))
    return int(lerp(92, 30, clamp((t - 7.8) / (53.44 - 7.8))))
def sold_at(t):
    if t < 6.32: return '0'
    if t < 25.80: return f"{int(lerp(0, 300000, eio((t - 6.32) / 1.48))):,}"
    return '30'
def hud(Lr, t):
    if t < 1.61 or t > 54.6: return 0.0
    a = clamp((t - 1.61) / 0.5) * clamp((54.6 - t) / 0.6)
    d = ImageDraw.Draw(Lr); lab = font(MONO, 17); val = font(MONO, 30)
    dd = days_at(t); y, m, dy = dd // 365, (dd % 365) // 30, (dd % 365) % 30
    rows = [('LIFESPAN', f'{y:02d}Y {m:02d}M {dy:02d}D'), ('SOLD FOR', f'\u00a5 {sold_at(t)}')]
    glitch = 25.80 <= t < 26.25
    for i, (l, v) in enumerate(rows):
        yy = 952 + i * 46
        d.text((80, yy + 9), ' '.join(l), font=lab, fill=int(170 * a))
        if glitch and i == 1:
            rng = np.random.default_rng(int(t * 97))
            v = '\u00a5 ' + ''.join(rng.choice(list('0123456789#%$/\\')) for _ in range(rng.integers(2, 8)))
        d.text((280, yy), v, font=val, fill=int(240 * a))
    # strike-through: the price stops meaning anything
    if t > 53.44:
        u = eout((t - 53.44) / 0.45)
        for i in range(2):
            yy = 952 + i * 46 + 18
            d.line([(76, yy), (76 + 380 * u, yy)], fill=int(240 * a), width=3)
    return a

# ---------------------------------------------------------------- fireflies
rng = np.random.default_rng(7)
NP = 190
FX = rng.random(NP); FY = rng.random(NP); DEP = rng.random(NP) ** 1.8
VX = (rng.random(NP) - .5) * 0.018; VY = -(0.004 + rng.random(NP) * 0.016)
PH = rng.random(NP) * 6.283; SP = 0.7 + rng.random(NP) * 2.4; WOB = rng.random(NP) * 0.014
RANK = rng.permutation(NP)
SIGS = np.geomspace(0.7, 16, 18)
def _sprite(s):
    r = int(math.ceil(s * 3)); yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return np.exp(-(xx ** 2 + yy ** 2) / (2 * s * s)).astype(np.float32)
SPR = [_sprite(s) for s in SIGS]

def density(t):
    return keys(t, [(13.5, 0), (13.61, 0.06), (DROP - 0.01, 0.10), (DROP, 0.0), (DROP + 0.05, 1.0),
                    (34.0, 0.95), (36.0, 0.55), (43.6, 0.5), (45.5, 0.12), (49.0, 0.15), (51.0, 0.65),
                    (55.8, 0.65), (56.5, 0.4), (60, 0.35)])

def fireflies(t):
    dn = density(t)
    if dn <= 0.001: return None
    hw, hh = W // 2, H // 2
    buf = np.zeros((hh, hw), np.float32)
    x = (FX + VX * t + WOB * np.sin(t * 0.9 + PH)) % 1.1 - 0.05
    y = (FY + VY * t + WOB * np.cos(t * 0.7 + PH)) % 1.1 - 0.05
    if DROP <= t < DROP + 2.2:          # bloom outward from the couple on the drop
        k = lerp(0.08, 1.0, eout((t - DROP) / 2.2))
        x = 0.5 + (x - 0.5) * k; y = 0.6 + (y - 0.6) * k
    vis = np.clip((dn * NP - RANK) / 10, 0, 1)
    tw = 0.45 + 0.55 * (0.5 + 0.5 * np.sin(t * SP + PH))
    for i in range(NP):
        if vis[i] <= 0: continue
        si = int(DEP[i] * (len(SIGS) - 1)); spr = SPR[si]; r = spr.shape[0] // 2
        amp = vis[i] * tw[i] * lerp(1.0, 0.16, DEP[i])
        cx, cy = int(x[i] * hw), int(y[i] * hh)
        x0, y0, x1, y1 = cx - r, cy - r, cx + r + 1, cy + r + 1
        sx0, sy0 = max(0, -x0), max(0, -y0)
        x0c, y0c, x1c, y1c = max(x0, 0), max(y0, 0), min(x1, hw), min(y1, hh)
        if x1c <= x0c or y1c <= y0c: continue
        buf[y0c:y1c, x0c:x1c] += amp * spr[sy0:sy0 + (y1c - y0c), sx0:sx0 + (x1c - x0c)]
    bloom = cv2.GaussianBlur(buf, (0, 0), 9)
    out = cv2.resize(buf + 0.9 * bloom, (W, H), interpolation=cv2.INTER_LINEAR)
    return out

# ---------------------------------------------------------------- look
def warmth(t):
    return keys(t, [(0, 0), (13.6, 0), (DROP - 0.01, 0.18), (DROP, 0.6), (27.4, 0.85), (27.5, 1.0),
                    (34.2, 1.0), (43.6, 0.85), (45.6, 0.06), (49.0, 0.06), (51.0, 1.0), (60, 1.0)])
SH_C, HI_C = np.array([0.030, 0.035, 0.045]), np.array([0.90, 0.93, 0.96])
SH_W, HI_W = np.array([0.075, 0.045, 0.030]), np.array([1.00, 0.92, 0.78])
AMBER = np.array([1.0, 0.70, 0.32], np.float32)
FLASHES = [(16.07, 0.75, 0.16), (DROP, 1.0, 0.45), (g(12), 0.85, 0.32), (38.92, 0.30, 0.5), (55.85, 0.55, 0.6)]

_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx / W - .5) * 2) ** 2 * 0.85 + ((_yy / H - .5) * 2) ** 2 * 0.85)
VIG = (1 - 0.42 * np.clip((_r - 0.45) / 0.85, 0, 1) ** 1.5).astype(np.float32)
_g = np.random.default_rng(3)
GRAIN = [cv2.resize(_g.normal(0, 0.03, (H // 2, W // 2)).astype(np.float32), (W, H)) for _ in range(8)]
_lr = np.mgrid[0:H, 0:W].astype(np.float32)
LEAK = np.exp(-(((_lr[1] - W) / (W * 0.45)) ** 2 + ((_lr[0] - H * 0.2) / (H * 0.6)) ** 2)).astype(np.float32)
del _lr, _yy, _xx, _r

# ---------------------------------------------------------------- card rendering
def quad(cx, cy, fw, fh, tilt):
    f = 1800.0; pts = []
    for X, Y in [(-fw / 2, -fh / 2), (fw / 2, -fh / 2), (fw / 2, fh / 2), (-fw / 2, fh / 2)]:
        z = X * math.sin(tilt); k = f / (f + z)
        pts.append((cx + X * math.cos(tilt) * k, cy + Y * k))
    return np.float32(pts)

def poly_mask(q, bx, by, bw, bh):
    m = np.zeros((bh, bw), np.uint8)
    cv2.fillConvexPoly(m, np.int32(np.round((q - [bx, by]) * 16)), 255, cv2.LINE_AA, 4)
    return m.astype(np.float32) / 255

SHARDS = {}
def shards(key, bw, bh):
    if key not in SHARDS:
        r = np.random.default_rng(11); pts = [(0, 0), (bw - 1, 0), (bw - 1, bh - 1), (0, bh - 1)]
        for gx in range(5):
            for gy in range(7):
                pts.append((min(bw - 1, max(0, (gx + 0.5 + r.uniform(-.35, .35)) * bw / 5)),
                            min(bh - 1, max(0, (gy + 0.5 + r.uniform(-.35, .35)) * bh / 7))))
        sd = cv2.Subdiv2D((0, 0, bw + 1, bh + 1))
        for p in pts: sd.insert((float(p[0]), float(p[1])))
        tris = [np.float32(t).reshape(3, 2) for t in sd.getTriangleList()
                if all(0 <= v <= bw + 1 for v in t[0::2]) and all(0 <= v <= bh + 1 for v in t[1::2])]
        SHARDS[key] = [(tr, r.uniform(-1, 1), r.uniform(0.6, 1.4), r.uniform(0, 0.3)) for tr in tris]
    return SHARDS[key]

def render_card(cv, c, t, sh):
    lt = t - sh['t0'] - c.get('t_in', 0)
    if lt < 0: return
    dur = sh['t1'] - sh['t0'] - c.get('t_in', 0); u = lt / dur
    ent = c.get('ent', 0.5); e = eout(lt / ent) if ent > 0 else 1.0
    a = e * (clamp((sh['t1'] - t) / c.get('exit', 0.1)) if c.get('exit', 0.1) > 0 else 1)
    im, up, s = page(c['p'])
    x, y, w, h = c['r']
    if 'rB' in c:   # explicit Ken Burns between two rects
        xb, yb, wb, hb = c['rB']; k = eio(u)
        x, y, w, h = lerp(x, xb, k), lerp(y, yb, k), lerp(w, wb, k), lerp(h, hb, k)
        asp = c['r'][2] / c['r'][3]
    else:
        asp = w / h
        z = lerp(1, c.get('kz', 1), eio(u)); fx, fy = c.get('f', (0.5, 0.5))
        w2, h2 = w / z, h / z; x, y = x + (w - w2) * fx, y + (h - h2) * fy; w, h = w2, h2
    src = np.float32([[x, y], [x + w, y], [x + w, y + h], [x, y + h]]) * s
    bleed = c.get('bleed', False)
    if bleed: fw, fh = W, H
    elif 'h' in c: fh = c['h']; fw = fh * asp
    else: fw = c['w']; fh = fw / asp
    sc = lerp(c.get('s0', 1.0), c.get('s1', 1.04), eio(u)) * lerp(c.get('es', 1.06), 1, e)
    if bleed: sc = max(sc, 1.0)
    d0, d1, fr = c.get('d0', (0, 0)), c.get('d1', (0, 0)), c.get('frm', (0, 30))
    cx = c.get('cx', W / 2) + lerp(d0[0], d1[0], eio(u)) + fr[0] * (1 - e)
    cy = c.get('cy', H / 2) + lerp(d0[1], d1[1], eio(u)) + fr[1] * (1 - e)
    if 'shake' in c:
        st, amp = c['shake']; k = math.exp(-max(0, lt - st) * 7) * amp
        cx += k * math.sin(lt * 61); cy += k * math.cos(lt * 47)
    fw *= sc; fh *= sc
    tilt = math.radians(c.get('tilt', 0)) * (1 - e)
    q = quad(cx, cy, fw, fh, tilt)
    m = 0 if bleed else c.get('m', 10) * sc
    qm = quad(cx, cy, fw + 2 * m, fh + 2 * m, tilt)
    bx, by = int(max(0, math.floor(qm[:, 0].min()) - 2)), int(max(0, math.floor(qm[:, 1].min()) - 2))
    bx1, by1 = int(min(W, math.ceil(qm[:, 0].max()) + 2)), int(min(H, math.ceil(qm[:, 1].max()) + 2))
    bw, bh = bx1 - bx, by1 - by
    if bw <= 2 or bh <= 2: return
    M = cv2.getPerspectiveTransform(src, q - np.float32([bx, by]))
    content = cv2.warpPerspective(up, M, (bw, bh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    if c.get('warp'):   # breeze through her hair (right side of frame)
        yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
        mk = np.clip((xx / bw - 0.52) / 0.3, 0, 1) * np.clip((yy / bh - 0.15) / 0.3, 0, 1)
        dx = 7 * np.sin(yy / 85 + lt * 2.1 + xx / 260) * mk
        dy = 3 * np.sin(xx / 120 + lt * 1.6) * mk
        content = cv2.remap(content, xx + dx, yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    mc = poly_mask(q, bx, by, bw, bh)
    # assemble the card layer (value + alpha) inside bbox
    if m > 0:
        mm = poly_mask(qm, bx, by, bw, bh)
        val = 0.95 * (1 - mc) + content * mc; alp = mm
    else:
        val, alp = content, mc
    region = cv[by:by1, bx:bx1]
    shat = c.get('shatter')
    if shat is not None and lt > shat:
        p = clamp((lt - shat) / (dur - shat - 0.15))
        layer_v = np.zeros_like(cv); layer_a = np.zeros_like(cv)
        ccx, ccy = bw / 2, bh / 2
        for tri, rot, spd, dl in shards(c['p'], bw, bh):
            pp = clamp((p - dl) / (1 - dl)) ** 1.6
            tc = tri.mean(0); dv = tc - [ccx, ccy]; dv = dv / (np.linalg.norm(dv) + 1e-3)
            off = dv * pp * 520 * spd + np.float32([0, -pp * 120])
            R = cv2.getRotationMatrix2D((float(tc[0]), float(tc[1])), rot * 50 * pp, 1 - 0.2 * pp)
            R[:, 2] += [bx + off[0], by + off[1]]
            tm = np.zeros((bh, bw), np.float32); cv2.fillConvexPoly(tm, np.int32(tri), 1.0, cv2.LINE_AA)
            fa = (1 - pp) * a
            wa = cv2.warpAffine(alp * tm * fa, R, (W, H))
            wv = cv2.warpAffine(val, R, (W, H))
            layer_v = layer_v * (1 - wa) + wv * wa; layer_a = layer_a + wa * (1 - layer_a)
        # thin shadow under shards
        cv *= 1 - 0.4 * cv2.GaussianBlur(layer_a, (0, 0), 14)
        cv[:] = cv * (1 - layer_a) + layer_v * layer_a
        return
    if not bleed and c.get('blend') != 'mul':   # drop shadow
        hm = cv2.resize(alp, (max(1, bw // 4), max(1, bh // 4)))
        hm = cv2.GaussianBlur(hm, (0, 0), 6)
        hm = cv2.resize(hm, (bw, bh))
        sy = 18; sh_ = np.zeros_like(hm); sh_[sy:] = hm[:-sy]
        region *= 1 - 0.55 * a * sh_
    if c.get('blend') == 'mul':
        region[:] = region * (1 - a * alp + a * alp * val)
    else:
        aa = a * alp; region[:] = region * (1 - aa) + val * aa

BGC = {}
def background(si, sh, t):
    if sh['bg'] == 'black': return np.full((H, W), 0.03, np.float32)
    if sh['bg'] == 'paper': return np.full((H, W), 0.95, np.float32)
    if si not in BGC:
        c = sh['cards'][0]; im = page(c['p'])[0]; x, y, w, h = c['r']
        cr = im[y:y + h, x:x + w]; k = max(480 / w, 270 / h)
        sm = cv2.resize(cr, (int(w * k) + 1, int(h * k) + 1), interpolation=cv2.INTER_AREA)
        oy, ox = (sm.shape[0] - 270) // 2, (sm.shape[1] - 480) // 2
        sm = cv2.GaussianBlur(sm[oy:oy + 270, ox:ox + 480], (0, 0), 7)
        BGC[si] = (0.035 + 0.26 * cv2.resize(sm, (W, H), interpolation=cv2.INTER_CUBIC)).astype(np.float32)
    u = (t - sh['t0']) / (sh['t1'] - sh['t0']); z = 1.0 + 0.06 * u
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
    return cv2.warpAffine(BGC[si], M, (W, H), borderMode=cv2.BORDER_REFLECT)

# ---------------------------------------------------------------- frame
def frame(fi):
    t = fi / FPS
    si = next(i for i, s in enumerate(S) if s['t0'] <= t < s['t1'])
    sh = S[si]
    cv = background(si, sh, t)
    for c in sh['cards']: render_card(cv, c, t, sh)
    cv = np.clip(cv, 0, 1)
    # grade: colour = worth
    w = warmth(t)
    sh_c = lerp(SH_C, SH_W, w).astype(np.float32); hi_c = lerp(HI_C, HI_W, w).astype(np.float32)
    rgb = sh_c + (hi_c - sh_c) * cv[..., None]
    # light leak + fireflies
    if w > 0.05:
        ox = int(140 * math.sin(t * 0.37)); M = np.float32([[1, 0, ox], [0, 1, 0]])
        lk = cv2.warpAffine(LEAK, M, (W, H))
        rgb += (0.16 * w * lk)[..., None] * AMBER
    ff = fireflies(t)
    if ff is not None:
        gain = 1.0 if sh['bg'] != 'paper' else 0.5
        rgb += (gain * ff)[..., None] * AMBER
        rgb += (0.35 * gain * np.clip(ff - 0.6, 0, None))[..., None]
    # text (on graded image)
    TL = Image.new('L', (W, H), 0); col = None; any_t = False; shadow = True
    for sp in TEXTS:
        if draw_text(TL, sp, t):
            any_t = True; col = sp.get('color', CREAM); shadow = sp.get('shadow', True)
    if any_t:
        ta = np.asarray(TL, np.float32) / 255
        if shadow: rgb *= (1 - 0.55 * cv2.GaussianBlur(ta, (0, 0), 9))[..., None]
        rgb = rgb * (1 - ta[..., None]) + np.float32(col) * ta[..., None]
        if t > 17.7 and t < 21.4:   # title glow
            rgb += (0.5 * cv2.GaussianBlur(ta, (0, 0), 14))[..., None] * AMBER
    HL = Image.new('L', (W, H), 0); ha = hud(HL, t)
    if ha > 0:
        h_ = np.asarray(HL, np.float32) / 255
        rgb *= (1 - 0.6 * cv2.GaussianBlur(h_, (0, 0), 6))[..., None]
        if 25.80 <= t < 26.25:   # RGB split glitch
            for ch, dx in ((0, 7), (2, -7)):
                sh_h = np.roll(h_, dx, axis=1); rgb[..., ch] = rgb[..., ch] * (1 - sh_h) + sh_h
        rgb = rgb * (1 - h_[..., None]) + np.float32(CREAM) * h_[..., None]
    # flashes
    fl = sum(pk * math.exp(-(t - tf) / dc) for tf, pk, dc in FLASHES if t >= tf)
    if fl > 0.003: rgb = rgb + (np.float32([1.0, 0.97, 0.92]) - rgb) * min(fl, 1)
    rgb *= VIG[..., None]
    rgb += GRAIN[fi % 8][..., None]
    rgb *= keys(t, [(0, 1), (59.0, 1), (60.0, 0)])
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)

# ---------------------------------------------------------------- main
def stills(times):
    os.makedirs(os.path.join(HERE, 'stills'), exist_ok=True)
    thumbs = []
    for tt in times:
        fr = frame(int(round(tt * FPS)))
        cv2.imwrite(os.path.join(HERE, 'stills', f'{tt:05.2f}.png'), fr[..., ::-1])
        th = cv2.resize(fr[..., ::-1], (480, 270), interpolation=cv2.INTER_AREA)
        cv2.putText(th, f'{tt:.2f}', (8, 22), 0, 0.6, (0, 255, 255), 2); thumbs.append(th)
    while len(thumbs) % 4: thumbs.append(np.zeros_like(thumbs[0]))
    rows = [np.hstack(thumbs[i:i + 4]) for i in range(0, len(thumbs), 4)]
    cv2.imwrite(os.path.join(HERE, 'stills', 'contact.jpg'), np.vstack(rows))

def video():
    import imageio_ffmpeg
    from multiprocessing import Pool
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmpv = os.path.join(HERE, '_video.mp4'); tmpa = os.path.join(HERE, '_audio.m4a')
    subprocess.run([ff, '-y', '-v', 'error', '-ss', str(SONG_START), '-t', '60', '-i', SONG,
                    '-af', 'afade=t=in:d=0.35,afade=t=out:st=58.9:d=1.1,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000',
                    '-c:a', 'aac', '-b:a', '320k', tmpa], check=True)
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
                          '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmpv], stdin=subprocess.PIPE)
    with Pool(max(1, os.cpu_count() - 1)) as pool:
        for i, fr in enumerate(pool.imap(frame, range(N), chunksize=6)):
            p.stdin.write(fr.tobytes())
            if i % 150 == 0: print(f'frame {i}/{N}', flush=True)
    p.stdin.close(); p.wait()
    subprocess.run([ff, '-y', '-v', 'error', '-i', tmpv, '-i', tmpa, '-map', '0:v', '-map', '1:a', '-c', 'copy',
                    '-t', '60', '-movflags', '+faststart', OUT], check=True)
    os.remove(tmpv); os.remove(tmpa)
    print('wrote', OUT)

if __name__ == '__main__':
    if sys.argv[1] == 'stills':
        stills([float(x) for x in sys.argv[2].split(',')])
    else:
        video()
