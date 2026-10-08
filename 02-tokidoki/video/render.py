"""Toki Doki (刻どキ) - pastel-pop manga music video, full song (3:34), 1920x1080, 30fps.

Style: taken from the romance reference MMVs (video-samples-references/romance) - B/W manga multiplied
over flat pastel colour + dot/star/heart/stripe patterns, pop-in geometric shapes, white/navy kinetic
words on the beat, label boxes, iris/diamond/heart wipes, frequent cuts.
Concept: the heartbeat. An ECG line pulses on the kick through the film, and a "beats left" counter
(her 221,124,617 bts / his 1,264 bts, both from the pages) counts down - his flatlines at 17,
hers reaches zero at 21. Palette from the manga's colour spread: sky blue, white, scarf red, cream.
Text: only lines printed on the pages.

Usage:
  python render.py stills 10,60,120      -> ./stills/<t>.png + stills/contact.jpg
  python render.py sheet [step]          -> stills every `step` s (default 2) + contact sheet
  python render.py video                 -> ../tokidoki.mp4
"""
import os, sys, json, math, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAN = os.path.join(ROOT, 'panels')
SONG = os.path.join(ROOT, 'tokidoki-bg-song.mp3')
OUT = os.path.join(ROOT, 'tokidoki.mp4')
W, H, FPS = 1920, 1080, 30
BM = json.load(open(os.path.join(HERE, 'beatmap.json')))
DUR = math.floor(BM['duration'] * FPS) / FPS
N = int(round(DUR * FPS))
BEATS = np.array(BM['beats'])
FD = 'C:/Windows/Fonts/'
cv2.setNumThreads(1)

# ---------------------------------------------------------------- easing / time
def clamp(u, a=0.0, b=1.0): return min(max(u, a), b)
def eout(u): u = clamp(u); return 1 - (1 - u) ** 3
def ein(u): u = clamp(u); return u ** 3
def eio(u):
    u = clamp(u); return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2
def eback(u):
    u = clamp(u); c1 = 1.70158; c3 = c1 + 1; return 1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2
def lerp(a, b, u): return a + (b - a) * u
def keys(t, pts):
    if t <= pts[0][0]: return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t1: return lerp(v0, v1, eio((t - t0) / max(t1 - t0, 1e-6)))
    return pts[-1][1]
def B(j, k=0):
    """time of beat k of bar j (bars start on the detected downbeat, BEATS[2])."""
    return float(BEATS[min(2 + 4 * j + k, len(BEATS) - 1)])
def nb(t, k=0):
    """k-th beat at/after t."""
    i = int(np.searchsorted(BEATS, t - 0.02)); return float(BEATS[min(i + k, len(BEATS) - 1)])
def since_beat(t):
    i = int(np.searchsorted(BEATS, t, side='right')) - 1
    return t - BEATS[i] if i >= 0 else 9.0
def beats_between(a, b): return int(np.searchsorted(BEATS, b) - np.searchsorted(BEATS, a))

# ---------------------------------------------------------------- palette (hex; from the colour spread)
WH, SKY, SKYL, SKY2, BLU = '#FFFFFF', '#A9DDF6', '#D6EFFB', '#74C3EE', '#3D8ED6'
PNK, PNKL, ROS, RED = '#F9BDD2', '#FDE0EA', '#F27BA0', '#E5404F'
CRM, CRML, MNT, LIL, LILL = '#FFF0A3', '#FFF8D8', '#BDEBD7', '#CFC0F5', '#E8E0FB'
NAV, GRY, SLT, INKH = '#1F2F5C', '#DEE2E9', '#9AA4B8', '#151A2E'
_HC = {}
def hexc(h):
    if h not in _HC: _HC[h] = np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)
    return _HC[h]
INKC = np.array([0.08, 0.10, 0.19], np.float32)   # manga black -> deep navy ink

# ---------------------------------------------------------------- pages / panels
COLOR = {'01', '02'}
PAGES = {}
def page(n):
    if n not in PAGES:
        fn = [p for p in os.listdir(PAN) if p[:2] == n and p[2] == '.'][0]
        im = Image.open(os.path.join(PAN, fn)).convert('RGB' if n in COLOR else 'L')
        a = np.asarray(im, np.float32) / 255
        if n not in COLOR: a = np.clip((a - 0.03) / 0.90, 0, 1)        # clean paper to pure white
        s = 1.0 if n == '02' else 2.0
        up = cv2.resize(a, (int(a.shape[1] * s), int(a.shape[0] * s)), interpolation=cv2.INTER_LANCZOS4)
        bl = cv2.GaussianBlur(up, (0, 0), 1.2)
        up = np.clip(up + 0.6 * (up - bl), 0, 1)
        PAGES[n] = ((up * 255 + 0.5).astype(np.uint8), s)
    return PAGES[n]

R = {
    '01alt': ('01', [300, 130, 320, 790]), '01face': ('01', [250, 975, 653, 425]),
    '02pan': ('02', [0, 0, 1240, 698]), '02pan2': ('02', [640, 0, 1240, 698]),
    '02hatsu': ('02', [150, 230, 700, 1170]), '02hato': ('02', [1010, 60, 710, 1010]),
    '02logo': ('02', [10, 10, 700, 232]),
    '03a': ('03', [47, 0, 912, 525]), '03b': ('03', [47, 540, 912, 255]), '03c': ('03', [47, 815, 912, 585]),
    '04a': ('04', [330, 0, 629, 960]), '04b': ('04', [0, 975, 650, 425]),
    '05ecg': ('05', [0, 0, 208, 335]), '05gp': ('05', [213, 0, 355, 335]), '05hp': ('05', [576, 0, 383, 335]),
    '05scr': ('05', [190, 375, 560, 395]), '05bench': ('05', [0, 1060, 525, 340]),
    '05app': ('05', [530, 1000, 240, 400]),
    '06top': ('06', [47, 0, 912, 310]), '06shout': ('06', [47, 355, 912, 513]),
    '06girl': ('06', [349, 960, 610, 440]),
    '07top': ('07', [0, 0, 959, 295]), '07mid': ('07', [0, 330, 959, 560]), '07bl': ('07', [0, 905, 560, 495]),
    '07br': ('07', [556, 1100, 400, 300]),
    '08a': ('08', [0, 0, 560, 500]), '08b': ('08', [570, 0, 389, 500]), '08girl': ('08', [380, 505, 270, 895]),
    '08laugh': ('08', [0, 1000, 420, 400]), '08br': ('08', [600, 850, 359, 550]),
    '09t1': ('09', [0, 0, 380, 300]), '09t2': ('09', [380, 0, 330, 300]), '09t3': ('09', [700, 0, 259, 300]),
    '09m1': ('09', [0, 330, 320, 230]), '09m2': ('09', [300, 320, 330, 380]), '09m3': ('09', [620, 320, 339, 560]),
    '09m4': ('09', [0, 560, 330, 320]), '09fun': ('09', [47, 880, 912, 520]),
    '10girl': ('10', [0, 0, 265, 430]), '10mid': ('10', [0, 460, 959, 240]), '10bike': ('10', [0, 860, 640, 360]),
    '11top': ('11', [47, 0, 912, 400]), '11sing': ('11', [420, 0, 300, 400]), '11mid': ('11', [47, 430, 820, 275]),
    '11br': ('11', [320, 720, 639, 680]), '11bl': ('11', [47, 720, 270, 680]),
    '12girl': ('12', [0, 0, 620, 1000]), '12hands': ('12', [600, 0, 359, 470]), '12bot': ('12', [250, 980, 709, 420]),
    '13phone': ('13', [47, 0, 912, 930]), '13why': ('13', [47, 975, 600, 425]), '13pi': ('13', [640, 975, 319, 425]),
    '14top': ('14', [47, 0, 912, 300]), '14hato': ('14', [370, 330, 340, 540]), '14cry': ('14', [200, 880, 759, 520]),
    '15cry': ('15', [150, 330, 560, 315]), '15crowd': ('15', [47, 990, 400, 410]), '15sky': ('15', [450, 990, 509, 410]),
    '16top': ('16', [0, 0, 959, 330]), '16hug': ('16', [0, 375, 959, 560]), '16bl': ('16', [0, 975, 440, 425]),
    '16br': ('16', [440, 975, 519, 425]), '16couple': ('16', [370, 470, 300, 420]),
    '17r1': ('17', [655, 0, 304, 450]), '17sky': ('17', [47, 0, 610, 720]), '17lie': ('17', [270, 700, 480, 280]),
    '18sing': ('18', [57, 0, 286, 394]), '18conc': ('18', [319, 0, 593, 394]), '18mid': ('18', [95, 410, 819, 200]),
    '18face': ('18', [250, 780, 450, 620]),
}

# ---------------------------------------------------------------- patterns & shapes
def shape_pts(k, s, rot=0.0):
    if isinstance(s, (tuple, list)): sx, sy = s
    else: sx = sy = s
    if k in ('circle', 'ring'):
        a = np.linspace(0, 2 * np.pi, 72, endpoint=False); p = np.stack([np.cos(a), np.sin(a)], 1)
    elif k == 'diamond': p = np.float32([[0, -1], [1, 0], [0, 1], [-1, 0]])
    elif k in ('square', 'rect'): p = np.float32([[-1, -1], [1, -1], [1, 1], [-1, 1]])
    elif k == 'tri': a = np.radians([-90, 30, 150]); p = np.stack([np.cos(a), np.sin(a)], 1)
    elif k in ('star', 'burst', 'plus'):
        n, ins = {'star': (5, 0.45), 'burst': (12, 0.72), 'plus': (4, 0.2)}[k]
        a = np.linspace(-np.pi / 2, 1.5 * np.pi, 2 * n, endpoint=False)
        r = np.where(np.arange(2 * n) % 2 == 0, 1.0, ins); p = np.stack([np.cos(a) * r, np.sin(a) * r], 1)
    elif k == 'heart':
        a = np.linspace(0, 2 * np.pi, 80, endpoint=False)
        p = np.stack([16 * np.sin(a) ** 3, -(13 * np.cos(a) - 5 * np.cos(2 * a) - 2 * np.cos(3 * a) - np.cos(4 * a))], 1) / 16.5
        p[:, 1] += 0.12
    else: raise ValueError(k)
    p = p * np.float32([sx, sy])
    if rot:
        c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        p = p @ np.float32([[c, s_], [-s_, c]])
    return p.astype(np.float32)

def make_tile(kind, P, r):
    q = 4; S_ = P * q; m = np.zeros((S_, S_), np.uint8)
    pts = [(S_ / 2, S_ / 2), (0, 0), (S_, 0), (0, S_), (S_, S_)]
    if kind == 'dots':
        for x, y in pts: cv2.circle(m, (int(x), int(y)), int(r * q), 255, -1, cv2.LINE_AA)
    elif kind in ('stars', 'hearts', 'diamonds', 'pluses'):
        k = {'stars': 'star', 'hearts': 'heart', 'diamonds': 'diamond', 'pluses': 'plus'}[kind]
        for i, (x, y) in enumerate(pts):
            pp = shape_pts(k, r * q, 12 if i == 0 else 0) + np.float32([x, y])
            cv2.fillPoly(m, [np.int32(pp * 16)], 255, cv2.LINE_AA, 4)
    elif kind == 'stripes':
        yy, xx = np.mgrid[0:S_, 0:S_]; m = ((((xx + yy) % S_) < S_ * r) * 255).astype(np.uint8)
    elif kind == 'grid':
        for i in range(0, S_, S_ // 4):
            th = 2 * q if i == 0 else q
            m[i:i + th, :] = 255; m[:, i:i + th] = 255
    return cv2.resize(m, (P, P), interpolation=cv2.INTER_AREA).astype(np.float32) / 255

PATC = {}
def pat_canvas(spec):
    if spec not in PATC:
        if len(PATC) > 6: PATC.clear()
        kind, c1, c2, P, r = spec
        a, b = hexc(c1), hexc(c2)
        if kind == 'plain': can = np.broadcast_to(a, (H + P, W + P, 3)).astype(np.float32)
        else:
            t = make_tile(kind, P, r)
            m = np.tile(t, ((H + P) // P + 2, (W + P) // P + 2))[:H + P, :W + P]
            can = (a + (b - a) * m[..., None]).astype(np.float32)
        PATC[spec] = can
    return PATC[spec]

def bgp(kind, c1, c2=None, P=64, r=9, v=(1, 0)):
    return dict(spec=(kind, c1, c2 or c1, P, r), v=v)

def background(sh, t):
    bg = sh['bg']; can = pat_canvas(bg['spec']); P = bg['spec'][3]
    fi = int(round(t * FPS)); vx, vy = bg['v']
    ox, oy = (fi * vx) % P, (fi * vy) % P
    return can[oy:oy + H, ox:ox + W].copy()

def poly_mask(pts, bx, by, bw, bh, ring=0):
    m = np.zeros((bh, bw), np.uint8)
    p = [np.int32(np.round((pts - [bx, by]) * 16))]
    if ring: cv2.polylines(m, p, True, 255, int(ring), cv2.LINE_AA, 4)
    else: cv2.fillPoly(m, p, 255, cv2.LINE_AA, 4)
    return m.astype(np.float32) / 255

def bbox_of(pts, pad=3):
    bx, by = int(max(0, math.floor(pts[:, 0].min()) - pad)), int(max(0, math.floor(pts[:, 1].min()) - pad))
    bx1, by1 = int(min(W, math.ceil(pts[:, 0].max()) + pad)), int(min(H, math.ceil(pts[:, 1].max()) + pad))
    return bx, by, bx1, by1

DIRS = {'l': (-1, 0), 'r': (1, 0), 'u': (0, -1), 'd': (0, 1)}

def draw_shape(rgb, s, t, frame_t=None):
    lt = t - s['t']
    if lt < 0: return
    end = s.get('end')
    if end is not None and t > end + 0.15: return
    ent = s.get('ent', 'pop'); e = clamp(lt / s.get('ed', 0.32))
    sc, dx, dy, a = 1.0, 0.0, 0.0, s.get('a', 1.0)
    rot = s.get('rot', 0) + s.get('spin', 0) * lt
    if ent == 'pop': sc = eback(e)
    elif ent == 'grow': sc = eout(e)
    elif ent == 'spin': sc = eback(e); rot -= 120 * (1 - eout(e))
    elif ent.startswith('slide'):
        vx, vy = DIRS[ent[6:]]; d = s.get('dist', 900) * (1 - eout(e)); dx, dy = -vx * d, -vy * d
    elif ent == 'fade': a *= eout(e)
    if end is not None and t > end: sc *= 1 - clamp((t - end) / 0.15)
    if s.get('bp'): sc *= 1 + s['bp'] * math.exp(-since_beat(t) * 8)
    if 'bob' in s:
        am, fq, ph = s['bob']; dy += am * math.sin(lt * fq * 6.283 + ph); dx += 0.5 * am * math.cos(lt * fq * 4.1 + ph)
    if sc <= 0.01 or a <= 0.01: return
    size = s['s']
    size = (size[0] * sc, size[1] * sc) if isinstance(size, (tuple, list)) else size * sc
    pts = shape_pts(s['k'], size, rot) + np.float32([s['x'] + dx, s['y'] + dy])
    ring = s.get('ring', 0) or (8 if s['k'] == 'ring' else 0)
    ol = s.get('ol', 0)
    bx, by, bx1, by1 = bbox_of(pts, pad=int(ring + ol + 3))
    if bx1 - bx < 2 or by1 - by < 2: return
    bw, bh = bx1 - bx, by1 - by
    reg = rgb[by:by1, bx:bx1]
    m = poly_mask(pts, bx, by, bw, bh, ring) * a
    if 'pat' in s:
        can = pat_canvas(s['pat']); P = s['pat'][3]; fi = int(round(t * FPS))
        ox, oy = (fi + bx) % P, (fi // 2 + by) % P
        col = can[oy:oy + bh, ox:ox + bw]
    else:
        col = hexc(s['c'])
    reg[:] = reg * (1 - m[..., None]) + col * m[..., None]
    if ol:
        mo = poly_mask(pts, bx, by, bw, bh, ol) * a
        reg[:] = reg * (1 - mo[..., None]) + hexc(s.get('oc', NAV)) * mo[..., None]

# ---------------------------------------------------------------- cards (manga panels)
def render_card(rgb, c, t, sh):
    lt = t - sh['t0'] - c.get('t_in', 0)
    if lt < 0: return
    dur = max(sh['t1'] - sh['t0'] - c.get('t_in', 0), 0.1); u = clamp(lt / dur)
    p, r = R[c['key']]
    up, s = page(p)
    x, y, w, h = r
    if 'pan' in c:
        xb, yb, wb, hb = R[c['pan']][1]; k = eio(u)
        x, y, w, h = lerp(x, xb, k), lerp(y, yb, k), lerp(w, wb, k), lerp(h, hb, k)
    z = lerp(1, c.get('kz', 1), eio(u)); fx, fy = c.get('f', (0.5, 0.5))
    w2, h2 = w / z, h / z; x, y = x + (w - w2) * fx, y + (h - h2) * fy; w, h = w2, h2
    asp = w / h
    mode = c.get('mode', 'frame'); bleed = c.get('bleed', False)
    if bleed: k0 = max(W / w, H / h); fw, fh = w * k0, h * k0
    elif 'h' in c: fh = c['h']; fw = fh * asp
    else: fw = c['w']; fh = fw / asp
    ent = c.get('ent', 'punch' if bleed else 'pop'); e = clamp(lt / c.get('ed', 0.38))
    sc = lerp(c.get('s0', 1.0), c.get('s1', 1.035), eio(u))
    ang = c.get('rot', 0) + c.get('spin', 0) * lt
    cx, cy = c.get('cx', W / 2), c.get('cy', H / 2); a = 1.0
    if ent == 'pop': sc *= lerp(0.25, 1, eback(e)); a = clamp(e * 4)
    elif ent == 'punch': sc *= lerp(1.14, 1, eout(e))
    elif ent == 'zoom': sc *= lerp(1.35, 1, eout(e)); a = clamp(e * 3)
    elif ent == 'drop': cy -= (1 - eback(e)) * 700
    elif ent == 'spin': sc *= eback(e); ang += 25 * (1 - eout(e))
    elif ent.startswith('slide'):
        vx, vy = DIRS[ent[6:]]; d = c.get('dist', 1300) * (1 - eout(e)); cx -= vx * d; cy -= vy * d
        ang += vx * 6 * (1 - eout(e))
    elif ent == 'fade': a = eout(e)
    d0, d1 = c.get('d0', (0, 0)), c.get('d1', (0, 0))
    cx += lerp(d0[0], d1[0], eio(u)); cy += lerp(d0[1], d1[1], eio(u))
    if 'shake' in c:
        st, amp = c['shake']
        if lt >= st:
            k = math.exp(-(lt - st) * 6) * amp; cx += k * math.sin(lt * 63); cy += k * math.cos(lt * 49)
    if 'bob' in c: cy += c['bob'] * math.sin(lt * 2.2)
    if bleed: sc = max(sc, 1.0)
    k = fw * sc / (w * s)
    pcx, pcy = (x + w / 2) * s, (y + h / 2) * s
    M = cv2.getRotationMatrix2D((pcx, pcy), ang, k); M[:, 2] += (cx - pcx, cy - pcy)
    def quad(m_):
        e_ = m_ / k
        cs = np.float32([[x * s - e_, y * s - e_], [(x + w) * s + e_, y * s - e_],
                         [(x + w) * s + e_, (y + h) * s + e_], [x * s - e_, (y + h) * s + e_]])
        return cs @ M[:, :2].T + M[:, 2]
    q = quad(0)
    m = 0 if (bleed or mode != 'frame') else c.get('m', 12) * sc
    qm = quad(m)
    so = np.float32(c.get('so', (16, 16))) * sc if mode == 'frame' and not bleed else np.float32([0, 0])
    allp = np.vstack([qm, qm + so])
    bx, by, bx1, by1 = bbox_of(allp)
    bw, bh = bx1 - bx, by1 - by
    if bw <= 2 or bh <= 2: return
    M2 = M.copy(); M2[:, 2] -= (bx, by)
    cont = cv2.warpAffine(up, M2, (bw, bh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    val = cont.astype(np.float32) / 255
    if val.ndim == 2: val = INKC + (1 - INKC) * val[..., None]
    reg = rgb[by:by1, bx:bx1]
    mc = poly_mask(q, bx, by, bw, bh) * a
    if mode == 'frame' and not bleed:
        ms = poly_mask(qm + so, bx, by, bw, bh) * a
        reg[:] = reg * (1 - ms[..., None]) + hexc(c.get('sc', NAV)) * ms[..., None]
        mb = poly_mask(qm, bx, by, bw, bh) * a
        reg[:] = reg * (1 - mb[..., None]) + mb[..., None]
        reg[:] = reg * (1 - mc[..., None]) + val * mc[..., None]
        mo = poly_mask(qm, bx, by, bw, bh, ring=4) * a
        reg[:] = reg * (1 - mo[..., None]) + hexc(NAV) * mo[..., None]
    elif mode == 'mul':
        reg[:] = reg * (1 - mc[..., None] + mc[..., None] * val)
        if c.get('ol'):
            mo = poly_mask(q, bx, by, bw, bh, ring=c['ol']) * a
            reg[:] = reg * (1 - mo[..., None]) + hexc(NAV) * mo[..., None]
    else:
        reg[:] = reg * (1 - mc[..., None]) + val * mc[..., None]

# ---------------------------------------------------------------- text
ROUND, BLACKF, HAND, MONO, JP = FD + 'ARLRDBD.TTF', FD + 'seguibl.ttf', FD + 'segoeprb.ttf', FD + 'consolab.ttf', FD + 'YuGothB.ttc'
STY = {
    'big': dict(font=ROUND, fill=WH, sh=NAV, so=0.075, stroke=NAV, sw=0.035),
    'ink': dict(font=ROUND, fill=NAV, stroke=WH, sw=0.075),
    'red': dict(font=ROUND, fill=RED, stroke=WH, sw=0.075),
    'hand': dict(font=HAND, fill=RED, stroke=WH, sw=0.09),
    'label': dict(font=BLACKF, fill=WH, box='#111111', trk=0.16, px=0.6, py=0.32),
    'tag': dict(font=BLACKF, fill=NAV, box=WH, trk=0.12, px=0.5, py=0.28, sh=NAV, so=0.18),
    'mono': dict(font=MONO, fill=WH, box=NAV, px=0.35, py=0.18),
    'jp': dict(font=JP, fill=BLU, stroke=WH, sw=0.06),
}
_FONTS, SPR = {}, {}
def font(path, size):
    k = (path, size)
    if k not in _FONTS: _FONTS[k] = ImageFont.truetype(path, size)
    return _FONTS[k]

def sprite(s, st, size, fill=None, sh=None, stroke=None, box=None):
    key = (s, st, size, fill, sh, stroke, box)
    if key in SPR: return SPR[key]
    if len(SPR) > 400: SPR.clear()
    d = STY[st]; f = font(d['font'], size)
    fill = fill or d.get('fill'); sh = d.get('sh') if sh is None else sh
    stroke = d.get('stroke') if stroke is None else stroke; box = d.get('box') if box is None else box
    sw = int(round(size * d.get('sw', 0))) if stroke else 0
    trk = size * d.get('trk', 0)
    asc, desc = f.getmetrics()
    if trk: adv = [f.getlength(ch) + trk for ch in s]; tw = sum(adv) - trk
    else: tw = f.getlength(s)
    so = int(round(size * d.get('so', 0.07))) if sh else 0
    px, py = int(size * d.get('px', 0.1)) + sw, int(size * d.get('py', 0.06)) + sw
    Wd, Hd = int(tw + 2 * px + so + 2), int(asc + desc + 2 * py + so + 2)
    img = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0)); dr = ImageDraw.Draw(img)
    def put(ox, oy, col, scol):
        if trk:
            xx = px + ox
            for ch, a_ in zip(s, adv):
                dr.text((xx, py + oy), ch, font=f, fill=col, stroke_width=sw, stroke_fill=scol); xx += a_
        else: dr.text((px + ox, py + oy), s, font=f, fill=col, stroke_width=sw, stroke_fill=scol)
    if sh:
        if box: dr.rectangle([so, so, Wd - 1, Hd - 1], fill=sh)
        else: put(so, so, sh, sh)
    if box: dr.rectangle([0, 0, Wd - 1 - so, Hd - 1 - so], fill=box)
    put(0, 0, fill, stroke)
    arr = np.asarray(img, np.float32) / 255
    arr[..., :3] *= arr[..., 3:4]
    SPR[key] = arr
    return arr

def blit(rgb, spr, cx, cy, sc=1.0, rot=0.0, a=1.0, frac=1.0):
    if sc <= 0.01 or a <= 0.01: return
    h, w = spr.shape[:2]
    if frac < 1: spr = spr.copy(); spr[:, int(w * clamp(frac)):] = 0
    M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, sc); M[:, 2] += (cx - w / 2, cy - h / 2)
    cs = np.float32([[0, 0], [w, 0], [w, h], [0, h]]) @ M[:, :2].T + M[:, 2]
    bx, by, bx1, by1 = bbox_of(cs, 2)
    if bx1 - bx < 2 or by1 - by < 2: return
    M[:, 2] -= (bx, by)
    o = cv2.warpAffine(spr, M, (bx1 - bx, by1 - by), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    reg = rgb[by:by1, bx:bx1]; al = o[..., 3:4] * a
    reg[:] = reg * (1 - al) + o[..., :3] * a

def draw_text(rgb, it, t):
    lt = t - it['t']
    if lt < 0: return
    end = it.get('end')
    if end is not None and t > end + 0.16: return
    st, size, s = it['st'], it['size'], it['s']
    kw = dict(fill=it.get('fill'), sh=it.get('sh'), stroke=it.get('stroke'), box=it.get('box'))
    full = sprite(s, st, size, **kw)
    ent = it.get('ent', 'pop'); e = clamp(lt / it.get('ed', 0.3))
    sc, a, dx, dy, frac, spr = 1.0, 1.0, 0.0, 0.0, 1.0, full
    rot = it.get('rot', 0)
    x, y = it['x'], it['y']
    wf = full.shape[1]
    anc = it.get('anchor', 'c')
    cx = x if anc == 'c' else (x + wf / 2 if anc == 'l' else x - wf / 2)
    if ent == 'pop': sc = lerp(0.2, 1, eback(e)); a = clamp(e * 3)
    elif ent == 'stamp': sc = lerp(2.3, 1, eout(e)); a = clamp(e * 2.5); rot += 8 * (1 - eout(e))
    elif ent == 'type':
        n = int(len(s) * clamp(lt / (len(s) * it.get('cps', 0.032))))
        if n <= 0: return
        if n < len(s):
            spr = sprite(s[:n], st, size, **kw); cx = cx - wf / 2 + spr.shape[1] / 2
    elif ent.startswith('slide'):
        vx, vy = DIRS[ent[6:]]; d = it.get('dist', 160) * (1 - eout(e)); dx, dy = -vx * d, -vy * d; a = eout(e)
    elif ent == 'drop': dy = -(1 - eback(e)) * 170; a = clamp(e * 3)
    elif ent == 'fade': a = eout(e)
    elif ent == 'wipe': frac = eout(e)
    elif ent == 'rise': dy = 40 * (1 - eout(e)); a = eout(e)
    if end is not None and t > end: k = clamp((t - end) / 0.16); sc *= 1 - 0.6 * k; a *= 1 - k
    if it.get('bp'): sc *= 1 + it['bp'] * math.exp(-since_beat(t) * 9)
    if it.get('bob'): dy += it['bob'] * math.sin(lt * 2.4 + x * 0.01)
    if it.get('sway'): rot += it['sway'] * math.sin(lt * 2.0 + y * 0.01)
    blit(rgb, spr, cx + dx, y + dy, sc, rot, a, frac)

def words(t, lines, x, y, size, st='big', step=None, anchor='c', lh=1.08, ent='pop', **kw):
    """One token per beat from t (or every `step` s). '|' = new line, '_' binds words into one token."""
    out, k = [], 0
    f = font(STY[st]['font'], size); ls = lines.split('|')
    y0 = y - (len(ls) - 1) * size * lh / 2
    for li, line in enumerate(ls):
        toks = [w.replace('_', ' ') for w in line.split(' ')]
        ws = [sprite(w, st, size, kw.get('fill'), kw.get('sh'), kw.get('stroke'), kw.get('box')).shape[1] for w in toks]
        gap = f.getlength(' ') * 0.9
        tw = sum(ws) + gap * (len(toks) - 1)
        xx = x - tw / 2 if anchor == 'c' else (x if anchor == 'l' else x - tw)
        for wi, w in enumerate(toks):
            tt = nb(t, k) if step is None else t + k * step
            out.append(dict(s=w, st=st, size=size, x=xx + ws[wi] / 2, y=y0 + li * size * lh, t=tt, ent=ent, **kw))
            xx += ws[wi] + gap; k += 1
    return out

def label(t, s, x, y, size=30, st='label', ent='type', **kw):
    return [dict(s=s, st=st, size=size, x=x, y=y, t=t, ent=ent, **kw)]

# ---------------------------------------------------------------- ECG heartbeat line
def qrs(d):
    return (0.10 * np.exp(-((d + 0.13) / 0.032) ** 2) - 0.16 * np.exp(-((d + 0.028) / 0.009) ** 2)
            + 1.0 * np.exp(-(d / 0.0125) ** 2) - 0.38 * np.exp(-((d - 0.032) / 0.012) ** 2)
            + 0.20 * np.exp(-((d - 0.22) / 0.05) ** 2))
_HALF = (BEATS[:-1] + BEATS[1:]) / 2
def ecg_events(mode):
    if mode == 'calm': return BEATS[::2]
    if mode == 'fast': return np.sort(np.concatenate([BEATS, _HALF]))
    return BEATS

def draw_ecg(rgb, e, t):
    lt = t - e['t']
    if lt < 0 or (e.get('end') is not None and t > e['end']): return
    x0, x1, y, amp = e.get('x0', 0), e.get('x1', W), e['y'], e['amp']
    sp = e.get('speed', 560); th = e.get('th', 6)
    head = x0 + (x1 - x0) * eout(lt / e.get('don', 0.9))
    xs = np.arange(x0, head + 1, 3, dtype=np.float32)
    if len(xs) < 2: return
    tx = t - (head - xs) / sp
    ev = ecg_events(e.get('mode', 'beat'))
    ev = ev[(ev > tx.min() - 0.5) & (ev < tx.max() + 0.5)]
    v = qrs(tx[:, None] - ev[None, :]).sum(1) if len(ev) else np.zeros_like(tx)
    if 'flat' in e: v = v * (tx < e['flat'])
    if 'gain' in e: v = v * e['gain']
    pts = np.stack([xs, y - v * amp], 1)
    by, by1 = int(max(0, y - amp * 1.25 - th - 30)), int(min(H, y + amp * 0.55 + th + 30))
    if by1 - by < 4: return
    a = e.get('a', 1.0) * (1 - clamp((lt - e['fo']) / 0.4) if 'fo' in e else 1.0)
    m = poly_mask(pts, 0, by, W, by1 - by, ring=th) * a
    reg = rgb[by:by1]
    col = hexc(e.get('c', WH))
    if e.get('glow', 0.5):
        g = cv2.GaussianBlur(m, (0, 0), 10) * e.get('glow', 0.5)
        reg += g[..., None] * hexc(e.get('gc', WH)) * 0.9
    reg[:] = reg * (1 - m[..., None]) + col * m[..., None]
    hx, hy = pts[-1]
    if by <= hy < by1:
        cv2.circle(reg, (int(hx), int(hy - by)), int(th * 1.6), tuple(float(v_) for v_ in hexc(e.get('hc', WH))), -1, cv2.LINE_AA)

# ---------------------------------------------------------------- timeline helpers
S = []
FLASH, SHAKE, GLITCH = [], [], []
def shot(t0, t1, bg, cards=(), shapes=(), texts=(), ecg=(), tr=None, pulse=0.0):
    S.append(dict(t0=t0, t1=t1, bg=bg, cards=list(cards), shapes=list(shapes), texts=list(texts),
                  ecg=list(ecg), tr=tr, pulse=pulse))
def card(key, **kw): d = dict(key=key); d.update(kw); return d
def shp(k, x, y, s, c, t, **kw): d = dict(k=k, x=x, y=y, s=s, c=c, t=t); d.update(kw); return d
def row(t0, keys_, h=600, gap=50, cy=H / 2, step=None, cx=W / 2, rots=None, **kw):
    asp = [R[k][1][2] / R[k][1][3] for k in keys_]
    tot = sum(a * h for a in asp) + gap * (len(keys_) - 1)
    if tot > 1720: h *= 1720 / tot; tot = 1720
    x = cx - tot / 2; out = []
    for i, (k, a) in enumerate(zip(keys_, asp)):
        w = a * h
        tin = (nb(t0, i) - t0) if step is None else i * step
        out.append(card(k, h=h, cx=x + w / 2, cy=cy, t_in=tin, rot=(rots[i] if rots else (-3, 2, -2, 3)[i % 4]), **kw))
        x += w + gap
    return out
def sprinkle(t, n, seed, cols, area=(60, 60, W - 60, H - 60), kinds=('plus', 'circle', 'star'), size=(10, 26),
             step=0.06, layer='front', **kw):
    r = np.random.default_rng(seed); out = []
    for i in range(n):
        out.append(dict(k=str(r.choice(kinds)), x=float(r.uniform(area[0], area[2])), y=float(r.uniform(area[1], area[3])),
                        s=float(r.uniform(*size)), c=str(r.choice(cols)), t=t + i * step, rot=float(r.uniform(0, 90)),
                        spin=float(r.uniform(-50, 50)), bob=(float(r.uniform(4, 12)), float(r.uniform(0.3, 0.8)), float(r.uniform(0, 6))),
                        layer=layer, bp=0.25, **kw))
    return out
def hearts(t, n, seed, cols=(RED, ROS, WH), **kw): return sprinkle(t, n, seed, cols, kinds=('heart',), **kw)

# ================================================================ TIMELINE
# Song map (102 bpm, bar = 4 beats ~2.35s): intro 0-8.7 | verse 8.7-49.2 | lift 49.2-75.2 | chorus 77.6-108.1
# | build 108.1-150.1 | breakdown 150.1-159.5 | DROP 159.5 | dip 168.7-175.7 | final chorus 175.7-208.2 | outro
END_HIS = B(73) + 0.25          # his heart stops ("left this world at the age of 17")
END_HERS = B(85)                # hers reaches 0 ("died at the age of 21")

# ---- INTRO: the heartbeat, then the funeral (the manga's own cold open)
shot(0.0, B(1), bgp('grid', WH, SKYL, P=120, v=(0, 0)),
     ecg=[dict(t=0.25, y=560, amp=150, mode='calm', c=SKY2, gc=SKY, th=6, don=1.6, glow=0.6)],
     texts=label(B(0), 'TOKI DOKI', W / 2, 330, 34) + label(B(0, 2), 'BY KOMI NAOSHI', W / 2, 800, 26, st='tag'))
shot(B(1), B(2), bgp('dots', SKYL, WH, P=70, r=8),
     cards=[card('01alt', mode='norm', h=900, cx=620, rot=-3, ent='pop', s1=1.05)],
     shapes=[shp('circle', 620, 560, 470, SKY, B(1), layer='back', ent='grow', ed=0.5),
             shp('ring', 620, 560, 520, WH, B(1, 1), ring=6, layer='back', spin=10)] + sprinkle(B(1, 1), 8, 1, (WH, SKY2, CRM)),
     texts=words(B(1, 1), 'TAKAGI|HATSU', 1360, 400, 150, st='ink', step=0.29) +
           label(B(1, 2) + 0.2, 'DIED AT THE AGE OF', 1360, 620, 34) +
           [dict(s='21', st='red', size=230, x=1360, y=800, t=B(1, 3), ent='stamp')],
     tr=('iris', 'circle', WH))
shot(B(2), B(3), bgp('plain', WH),
     cards=[card('01face', mode='norm', bleed=True, kz=1.18, f=(0.62, 0.55), ent='fade', ed=0.5)],
     texts=[dict(s='That face...', st='hand', size=110, x=470, y=860, t=B(2, 1), ent='type', cps=0.07, fill=NAV)],
     shapes=sprinkle(B(2, 2), 7, 2, (WH, CRM), kinds=('plus',), size=(14, 30)))

# ---- VERSE 1: introductions (cool sky + cream)
FLASH.append((B(3), 0.9, 0.3, WH))
shot(B(3), B(4), bgp('plain', SKY),
     cards=[card('02pan', pan='02pan2', mode='norm', bleed=True, s1=1.02)],
     shapes=sprinkle(B(3, 1), 10, 3, (WH, CRM), kinds=('plus', 'star'), size=(12, 28), step=0.15))
shot(B(4), B(5), bgp('dots', SKY, SKYL, P=64, r=9),
     cards=[card('02hatsu', mode='norm', h=980, cx=560, cy=560, rot=-4, ent='slide-l', sc=BLU)],
     shapes=[shp('circle', 560, 540, 430, CRM, B(4), layer='back', ent='grow', ed=0.45),
             shp('rect', 1350, 920, (420, 22), WH, B(4, 2), rot=-4, ent='slide-r')] + sprinkle(B(4), 8, 4, (WH, CRM, BLU)),
     texts=words(B(4) + 0.15, 'TAKAGI|HATSU', 1350, 470, 190, step=0.45, ent='stamp', sh=BLU))
shot(B(5), B(6), bgp('stripes', CRML, CRM, P=90, r=0.5, v=(1, 1)),
     cards=[card('02hato', mode='norm', h=1000, cx=1370, cy=560, rot=4, ent='slide-r', sc=ROS)],
     shapes=[shp('circle', 1370, 520, 440, SKY, B(5), layer='back', ent='grow', ed=0.45),
             shp('rect', 560, 920, (420, 22), WH, B(5, 2), rot=4, ent='slide-l')] + sprinkle(B(5), 8, 5, (WH, ROS, BLU)),
     texts=words(B(5) + 0.15, 'IIJIMA|HATO', 570, 470, 190, step=0.45, ent='stamp', sh=ROS))
shot(B(6), B(7), bgp('grid', WH, SKYL, P=120, v=(2, 0)),
     cards=[card('02logo', mode='norm', w=1150, cx=W / 2, cy=430, ent='pop', s1=1.04)],
     ecg=[dict(t=B(6), y=880, amp=110, mode='beat', c=BLU, gc=SKY, th=6, don=0.8)],
     texts=label(B(6, 2), 'BY KOMI NAOSHI', W / 2, 700, 30),
     shapes=sprinkle(B(6, 1), 10, 6, (SKY2, CRM, PNK), kinds=('plus', 'star', 'circle')),
     tr=('iris', 'diamond', SKY2))
shot(B(7), B(8), bgp('dots', SKY, SKYL, P=60, r=8),
     cards=[card('03a', mode='mul', bleed=True, kz=1.08, f=(0.55, 0.4))],
     shapes=[shp('burst', 430, 820, 230, CRM, B(7, 2), ol=5, spin=12)],
     texts=label(B(7, 1), 'EVERYONE AROUND ME CALL ME', 430, 640, 28) +
           [dict(s='POPPO', st='big', size=130, x=430, y=820, t=B(7, 2), ent='stamp', sh=BLU, bp=0.06)],
     tr=('wipe', CRM))
shot(B(8), B(9), bgp('dots', CRM, CRML, P=56, r=7, v=(-1, 0)),
     cards=[card('03b', mode='frame', w=1650, cy=640, rot=-1.5, ent='slide-r', sc=SKY2)],
     texts=label(B(8, 1), 'AND I JOINED THE', W / 2, 150, 30) +
           words(B(8, 2), 'LIGHT MUSIC CLUB', W / 2, 270, 120, step=0.29, sh=BLU),
     shapes=sprinkle(B(8), 8, 8, (SKY2, WH, ROS)))
shot(B(9), B(10), bgp('stars', SKYL, WH, P=110, r=14),
     cards=[card('03c', mode='mul', bleed=True, kz=1.22, f=(0.85, 0.35))],
     texts=label(B(9, 1), 'RIGHT NOW,', 330, 300, 34) +
           words(B(9, 2), 'KIND_OF|INTERESTED', 360, 480, 96, st='ink', step=0.3),
     shapes=hearts(B(9, 3), 5, 9, (ROS, RED), area=(1300, 250, 1750, 600), size=(20, 40), step=0.12),
     tr=('iris', 'circle', CRM))
shot(B(10), B(12), bgp('stripes', SKYL, SKY, P=100, r=0.5, v=(1, 1)),
     cards=[card('04a', mode='frame', h=960, cx=1340, cy=545, rot=2, ent='slide-r', kz=1.1, f=(0.55, 0.3), sc=BLU)],
     shapes=[shp('diamond', 540, 540, 380, SKY2, B(10), layer='back', ent='spin', a=0.45)],
     texts=label(B(10, 1), 'DURING THE 2ND YEAR OF HIGH SCHOOL,', 540, 330, 28) +
           [dict(s='TRANSFERRED', st='big', size=104, x=540, y=520, t=B(10, 3), ent='stamp', sh=BLU)] +
           label(B(11, 1), 'TO A SCHOOL IN A REMOTE COUNTRYSIDE', 540, 720, 26, st='tag'))
shot(B(12), B(14), bgp('dots', GRY, WH, P=60, r=7),
     cards=[card('04b', mode='mul', bleed=True, kz=1.15, f=(0.85, 0.5))],
     shapes=[shp('rect', 560, 720, (470, 190), SKYL, B(12, 1), ol=5, rot=-2, layer='front', ent='slide-l')],
     texts=label(B(12, 1), 'EVER SINCE SHE TRANSFERRED HERE,', 520, 600, 28) +
           words(B(12, 3), "I'VE_NEVER SEEN_HER|MINGLE WITH_OTHERS", 560, 790, 84, step=0.58, sh=SLT),
     tr=('wipe', SKY))
shot(B(14), B(15), bgp('grid', WH, '#FBE3E7', P=120),
     cards=row(B(14), ['05ecg', '05gp', '05hp'], h=640, cy=500),
     ecg=[dict(t=B(14), y=960, amp=70, mode='beat', c=RED, gc=PNK, th=5, don=0.6)])
shot(B(15), B(16), bgp('dots', PNKL, WH, P=64, r=8),
     cards=[card('05scr', mode='frame', w=1080, cx=W / 2, cy=470, ent='zoom', kz=1.15, f=(0.6, 0.6), sc=RED)],
     texts=label(B(15, 1), 'THE AMOUNT OF HEARTBEATS THAT I HAVE LEFT ...', W / 2, 930, 30),
     shapes=hearts(B(15, 2), 6, 15, (RED, ROS), size=(16, 30)))
shot(B(16), B(18), bgp('stripes', WH, SKYL, P=90, r=0.5, v=(1, 1)),
     cards=[card('05bench', mode='frame', w=880, cx=540, cy=560, rot=-3, ent='slide-l', sc=SKY2, kz=1.1)],
     ecg=[dict(t=B(16), y=170, amp=70, mode='calm', c=SKY2, gc=SKYL, th=5, don=0.8, x0=980, x1=1840)],
     texts=label(B(16, 1), "THERE'S ABOUT 220 MILLION BEATS LEFT...", 1410, 330, 26) +
           words(B(17), 'BUT_IN|6_TO_7|YEARS,', 1410, 560, 112, step=0.45, sh=BLU) +
           [dict(s='my heart will stop beating', st='hand', size=62, x=1410, y=860, t=B(17, 3), ent='type', cps=0.03)],
     tr=('iris', 'heart', PNK))
shot(B(18), B(19), bgp('hearts', PNKL, WH, P=110, r=18, v=(0, -1)),
     cards=[card('05app', mode='frame', h=900, cx=1380, rot=3, ent='pop', sc=ROS, kz=1.06)],
     shapes=[shp('circle', 1380, 540, 420, PNK, B(18), layer='back', ent='grow')],
     texts=label(B(18, 1), 'IF YOU HAVE THE PERSONAL APP', 600, 430, 28) +
           label(B(18, 2), 'AND YOUR ID,', 600, 500, 28) +
           words(B(18, 3), 'YOU_CAN_CHECK|YOUR_OWN_HEART.', 600, 670, 76, st='ink', step=0.3))
shot(B(19), B(20), bgp('dots', SKYL, WH, P=56, r=7, v=(-1, 0)),
     cards=[card('06top', mode='frame', w=1700, cy=560, rot=-1, ent='slide-u', sc=NAV)],
     shapes=sprinkle(B(19, 1), 6, 19, (SKY2, NAV), kinds=('plus',)))

# ---- LIFT: "I'll help you!!" (pink + cream, faster)
FLASH.append((B(20), 1.0, 0.25, WH)); SHAKE.append((B(20), 18, 5))
shot(B(20), B(21), bgp('dots', PNK, PNKL, P=60, r=9),
     cards=[card('06shout', mode='mul', bleed=True, kz=1.1, f=(0.4, 0.4), shake=(0, 10))],
     shapes=[shp('burst', 1440, 470, 380, CRM, B(20), ol=6, spin=10, layer='front')],
     texts=words(B(20) + 0.05, "I'LL HELP|YOU!!", 1440, 470, 128, ent='stamp', sh=RED), pulse=0.02)
shot(B(21), B(22), bgp('hearts', RED, '#EE5F6C', P=120, r=20, v=(0, -2)),
     shapes=[shp('heart', W / 2, 560, 330, WH, B(21), bp=0.12, ent='pop', a=0.95)],
     ecg=[dict(t=B(21), y=560, amp=260, mode='fast', c=RED, gc=WH, th=8, don=0.4, glow=0.3)],
     texts=words(B(21), 'MAKE YOUR', W / 2, 190, 90, step=0.29, sh=NAV) +
           words(B(21, 2), 'HEART_BEAT', W / 2, 560, 150, st='red', ent='stamp') +
           words(B(21, 3), 'LIKE_CRAZY!!', W / 2, 920, 120, ent='stamp', sh=NAV), pulse=0.03)
shot(B(22), B(23), bgp('stars', CRM, CRML, P=110, r=15),
     cards=[card('06girl', mode='mul', bleed=True, kz=1.12, f=(0.6, 0.4))],
     shapes=[shp('circle', 330, 360, 200, WH, B(22, 2), ol=6, layer='front')],
     texts=[dict(s='HUH?', st='ink', size=120, x=330, y=360, t=B(22, 2), ent='pop')],
     tr=('wipe', PNK))
shot(B(23), B(24), bgp('dots', LILL, WH, P=60, r=8),
     cards=[card('07top', mode='frame', w=1700, cy=560, rot=1, ent='slide-l', sc=LIL)],
     shapes=sprinkle(B(23, 1), 6, 23, (LIL, NAV, WH), kinds=('plus', 'circle')))
shot(B(24), B(26), bgp('stripes', LILL, PNKL, P=120, r=0.5, v=(1, 1)),
     cards=[card('07mid', mode='mul', bleed=True, kz=1.12, f=(0.75, 0.3))],
     shapes=[shp('circle', 400, 520, 360, WH, B(24), layer='front', a=0.93, ent='grow')] + sprinkle(B(25), 8, 24, (WH, PNK, LIL)),
     texts=words(B(24, 1), 'TO_LIVE|MY_LIFE_OUT|WITH_EVERY|SECOND|I_HAVE_LEFT', 400, 520, 74, st='ink', step=0.58),
     tr=('iris', 'diamond', LIL))
shot(B(26), B(27), bgp('dots', SKYL, WH, P=64, r=8),
     cards=[card('07br', mode='frame', h=640, cx=1350, rot=2, ent='slide-r', sc=SKY2, kz=1.1)],
     texts=label(B(26, 1), "I'M AFRAID TO DO IT,", 560, 380, 30) +
           words(B(26, 2), 'SINCE_IT_WOULD|SHORTEN_MY|LIFESPAN...', 560, 600, 80, step=0.3, sh=BLU))
shot(B(27), B(28), bgp('plain', GRY),
     cards=[card('07bl', mode='frame', h=860, cx=600, rot=-2, ent='pop', sc=SLT)],
     texts=label(B(27, 1), 'AS SHE TOLD ME ABOUT IT,', 1380, 470, 30) +
           [dict(s='she looked so sad', st='hand', size=78, x=1380, y=620, t=B(27, 2), ent='type', fill=NAV, cps=0.04)])
FLASH.append((B(28), 0.6, 0.2, WH))
shot(B(28), B(29), bgp('stars', CRM, '#FFE36E', P=120, r=18, v=(1, 0)),
     cards=[card('08a', mode='frame', h=900, cx=600, rot=-3, ent='spin', sc=ROS)],
     shapes=[shp('burst', 1370, 560, 400, WH, B(28, 1), ol=6, spin=-8)] + sprinkle(B(28), 10, 28, (ROS, SKY2, WH)),
     texts=words(B(28, 1), "IT'S_SO|FUN!!", 1370, 560, 140, st='red', ent='stamp'), pulse=0.02)
shot(B(29), B(30), bgp('dots', MNT, WH, P=60, r=8, v=(-1, 0)),
     cards=[card('08b', mode='frame', h=880, cx=1360, rot=3, ent='slide-r', sc=SKY2)],
     texts=label(B(29, 1), 'THE FIRST THING THAT SURPRISED ME', 600, 420, 28) +
           label(B(29, 2), 'WHEN I SPENT TIME WITH TAKAGI-SAN', 600, 490, 28, st='tag'),
     shapes=sprinkle(B(29), 8, 29, (CRM, ROS, WH)), pulse=0.015)
shot(B(30), B(31), bgp('dots', SLT, '#8792A8', P=60, r=8),
     cards=[card('08girl', mode='frame', h=1000, cx=W / 2, rot=0, ent='drop', sc=NAV)],
     texts=label(B(30, 1), 'HER IMAGE IN SCHOOL IS OF', 420, 420, 26) +
           words(B(30, 2), 'A_SILENT|AND_GLOOMY|PERSON', 1500, 560, 90, step=0.29, sh=NAV))
shot(B(31), B(32), bgp('stars', CRM, CRML, P=110, r=15),
     cards=[card('08laugh', mode='frame', h=900, cx=600, rot=-3, ent='pop', sc=ROS)],
     texts=label(B(31), 'BUT IN REALITY', 1400, 330, 32) +
           words(B(31, 1), 'SHE_CAN|TELL_A_JOKE', 1400, 540, 110, ent='stamp', sh=ROS),
     shapes=sprinkle(B(31), 10, 31, (ROS, SKY2, WH)), tr=('iris', 'star', CRM), pulse=0.02)

# ---- CHORUS: so much fun (cream / mint / pink / sky, 2-beat cuts)
shot(B(32), B(33), bgp('dots', MNT, '#D9F5E8', P=64, r=9),
     cards=[card('08br', mode='frame', h=930, cx=1380, rot=3, ent='slide-r', sc=ROS)],
     texts=words(B(32), 'SHE_LOVES|TO_TALK|AND_MOVE|AROUND', 580, 540, 100, step=0.29, sh=ROS),
     shapes=sprinkle(B(32), 10, 32, (CRM, ROS, WH)), pulse=0.02)
shot(B(33), B(34), bgp('stripes', PNKL, WH, P=100, r=0.5, v=(1, 1)),
     cards=row(B(33), ['09t1', '09t2', '09t3'], h=560, cy=470),
     texts=label(B(33, 2), 'THE ONLY ONE WHO KNOWS THIS SIDE OF HER IS ME', W / 2, 900, 30), pulse=0.02)
_m = [('09m1', CRM, CRML, 'dots'), ('09m2', SKY, SKYL, 'stars'), ('09m3', PNK, PNKL, 'hearts'), ('09m4', MNT, WH, 'dots')]
_w = ['EACH', 'AND', 'EVERY', 'DAY']
for i in range(8):
    k, c1, c2, pat = _m[i % 4]
    t0, t1 = B(34, i) if i < 4 else B(35, i - 4), (B(34, i + 1) if i < 3 else (B(35, i - 3) if i < 7 else B(36)))
    shot(t0, t1, bgp(pat, c1, c2, P=90, r=12),
         cards=[card(k, mode='frame', h=820, cx=W / 2 + (-260 if i % 2 else 260), rot=(-4 if i % 2 else 4), ent='punch', sc=NAV)],
         texts=[dict(s=_w[i % 4], st='big', size=170, x=W / 2 + (520 if i % 2 else -520), y=540, t=t0, ent='stamp', sh=NAV)],
         pulse=0.03)
FLASH.append((B(36), 0.7, 0.25, WH))
shot(B(36), B(38), bgp('hearts', PNK, PNKL, P=110, r=18, v=(0, -1)),
     cards=[card('09fun', mode='mul', bleed=True, kz=1.15, f=(0.75, 0.4))],
     shapes=[shp('rect', 330, 540, (290, 330), CRM, B(36), ol=6, rot=-4, layer='front', ent='slide-l')] + hearts(B(37), 10, 36, area=(800, 80, 1850, 1000)),
     texts=words(B(36, 1), 'WE_HAD|SO_MUCH|FUN|TOGETHER', 330, 540, 80, st='ink', step=0.58), pulse=0.02)
shot(B(38), B(39), bgp('dots', SKYL, WH, P=64, r=8),
     cards=[card('10girl', mode='frame', h=960, cx=560, rot=-2, ent='slide-l', sc=SKY2)],
     texts=words(B(38), "RIGHT_NOW,|I'M_REALLY|HAPPY", 1330, 470, 120, step=0.58, sh=BLU) +
           [dict(s='...though I feel a little sad', st='hand', size=58, x=1330, y=800, t=B(38, 3), ent='type', fill=NAV, cps=0.025)])
shot(B(39), B(40), bgp('plain', GRY),
     cards=[card('10mid', mode='frame', w=1700, cy=540, rot=-1, ent='slide-r', sc=SLT, kz=1.05)])
shot(B(40), B(42), bgp('plain', WH),
     cards=[card('10bike', mode='mul', bleed=True, kz=1.12, f=(0.4, 0.55), d0=(40, 0), d1=(-40, 0), ent='fade', ed=0.6)],
     shapes=[shp('circle', 300 + 230 * i, 150 + 90 * (i % 3), 40 + 12 * (i % 4), SKYL, B(40) + 0.2 * i, a=0.8, bob=(10, 0.3, i))
             for i in range(7)],
     texts=label(B(41), 'TAKAGI-SAN', 1500, 200, 30), tr=('wipe', SKY))
shot(B(42), B(44), bgp('dots', SKYL, WH, P=70, r=8, v=(-1, 0)),
     cards=[card('10bike', mode='frame', w=820, cx=560, cy=640, rot=-4, ent='slide-l', sc=SKY2)],
     texts=words(B(42), "DON'T|SAY|IT", 1400, 540, 190, st='ink', step=0.58),
     ecg=[dict(t=B(42), y=180, amp=60, mode='calm', c=SKY2, gc=SKYL, th=4, don=1.2, x0=60, x1=1050)])
shot(B(44), B(45), bgp('stripes', LILL, WH, P=100, r=0.5, v=(1, 1)),
     cards=[card('11top', mode='frame', w=1600, cy=600, rot=1, ent='slide-u', sc=LIL)],
     texts=words(B(44, 1), 'IT_TUGS_AT_OUR|HEARTSTRINGS', W / 2, 140, 66, st='ink', step=0.58))

# ---- BUILD: the band, the festival, the hand (lilac / sky / pink)
FLASH.append((B(45), 0.6, 0.25, WH))
shot(B(45), B(46), bgp('pluses', LIL, LILL, P=90, r=16, v=(1, 0)),
     cards=[card('11sing', mode='frame', h=900, cx=1360, rot=3, ent='pop', sc=NAV, kz=1.08)],
     texts=words(B(45), 'YOU_HAVE_A|SUCH|BEAUTIFUL|VOICE', 580, 540, 104, step=0.58, sh=NAV),
     shapes=sprinkle(B(45), 10, 45, (WH, CRM, NAV), kinds=('plus', 'star')), pulse=0.015)
shot(B(46), B(47), bgp('dots', CRM, CRML, P=60, r=8),
     cards=[card('11mid', mode='frame', w=1550, cy=470, rot=-1, ent='slide-r', sc=BLU)],
     texts=label(B(46, 1), "IT'S EVEN GIVING ME GOOSE BUMPS!!", W / 2, 880, 34) +
           [dict(s='sounds like a pro!!', st='hand', size=60, x=1500, y=150, t=B(46, 2), ent='pop', rot=-6)])
shot(B(47), B(49), bgp('stars', PNKL, WH, P=110, r=15),
     cards=[card('11br', mode='frame', h=960, cx=1380, rot=2, ent='slide-r', sc=ROS, kz=1.06)],
     texts=words(B(47), 'WOULD_YOU_PLEASE_BE|THE_VOCALIST|FOR_OUR_BAND?!', 590, 420, 76, step=0.58, sh=ROS) +
           label(B(48), "LET'S PERFORM AT THE CULTURAL FESTIVAL", 590, 760, 26) +
           label(B(48, 1), 'IN OCTOBER!', 590, 830, 30, st='tag'),
     shapes=sprinkle(B(47), 10, 47, (ROS, SKY2, CRM)), pulse=0.015)
FLASH.append((B(49), 0.8, 0.25, WH))
shot(B(49), B(51), bgp('hearts', PNKL, WH, P=120, r=20, v=(0, -1)),
     cards=[card('12girl', mode='frame', h=1000, cx=560, rot=-2, ent='slide-l', kz=1.12, f=(0.6, 0.25), sc=ROS),
            card('12hands', mode='frame', h=520, cx=1560, cy=780, rot=6, ent='pop', t_in=B(50) - B(49), sc=RED)],
     texts=words(B(49, 1), 'THIS_IN_ITSELF|FEELS|EXCITING', 1250, 330, 100, ent='stamp', step=0.58, sh=RED),
     shapes=hearts(B(50), 8, 49, area=(1000, 520, 1880, 1040), size=(18, 36)), pulse=0.02)
shot(B(51), B(52), bgp('dots', RED, '#EE6170', P=70, r=10),
     cards=[card('12hands', mode='frame', h=900, cx=W / 2, rot=-3, ent='punch', sc=NAV)],
     shapes=hearts(B(51), 14, 51, cols=(WH, PNK, CRM), size=(20, 46), step=0.08), pulse=0.03)
shot(B(52), B(53), bgp('stripes', CRM, CRML, P=100, r=0.5, v=(1, 1)),
     cards=[card('12bot', mode='frame', w=1150, cx=1230, cy=600, rot=2, ent='slide-r', sc=ROS)],
     texts=words(B(52), 'THE_MOST|EXCITING|MOMENT', 360, 470, 84, step=0.58, sh=ROS) +
           label(B(52, 3), 'IN MY LIFE.', 360, 700, 34))

# ---- TWIST: his counter (colour drains, glitch)
FLASH.append((B(53), 1.0, 0.18, '#FF5A68')); SHAKE.append((B(53), 22, 6)); GLITCH.append((B(53), B(53) + 0.5))
shot(B(53), B(55), bgp('grid', GRY, '#C9CFD9', P=120),
     cards=[card('13phone', mode='frame', h=1000, cx=W / 2, ent='punch', kz=1.45, f=(0.55, 0.5), sc=RED)],
     texts=label(B(53, 2), 'HATO IIJIMA', 300, 200, 34, box=RED),
     ecg=[dict(t=B(53), y=930, amp=60, mode='beat', c=RED, gc=PNK, th=5, don=0.5, x0=0, x1=420)])
GLITCH.append((B(55), B(55) + 0.25))
shot(B(55), B(56), bgp('plain', '#C9CFD9'),
     cards=row(B(55), ['13why', '13pi'], h=700, cy=520, step=0.29, sc=RED),
     texts=[dict(s='Pi', st='hand', size=90, x=1700, y=170, t=B(55, 2), ent='pop'),
            dict(s='Pi', st='hand', size=90, x=1780, y=300, t=B(55, 3), ent='pop')])
shot(B(56), B(58), bgp('dots', SKYL, WH, P=64, r=8),
     cards=[card('14top', mode='frame', w=1650, cy=380, rot=-1, ent='slide-l', sc=SKY2)],
     texts=label(B(56, 2), 'IF I WERE TO DIE,', W / 2, 760, 34) +
           words(B(57), "I'D_LIKE_TO_LIVE_MY_LIFE|FULL_OF_EXCITEMENT", W / 2, 900, 72, step=0.58, sh=BLU),
     tr=('wipe', SKY))
shot(B(58), B(60), bgp('stars', SKYL, WH, P=120, r=15),
     cards=[card('14hato', mode='frame', h=960, cx=W / 2, ent='pop', kz=1.06, sc=BLU)],
     texts=words(B(58), "BECAUSE_OF_YOU,|I'VE_HAD_SO|MUCH_FUN", 380, 470, 64, st='ink', step=0.58) +
           words(B(59), "THAT'S_WHY...|I_WANT_TO|CHEER_YOU_ON", 1540, 470, 64, st='ink', step=0.58) +
           label(B(59, 3), 'WITH ALL MY HEART', 1540, 680, 28, box=RED),
     shapes=sprinkle(B(58), 8, 58, (SKY2, CRM, WH), kinds=('plus',)))
shot(B(60), B(63), bgp('dots', SKYL, WH, P=60, r=7),
     cards=[card('14cry', mode='mul', bleed=True, kz=1.12, f=(0.4, 0.5))],
     texts=words(B(61), 'THANK_YOU,|TAKAGI-SAN', 400, 470, 104, step=1.16, sh=BLU),
     shapes=sprinkle(B(62), 10, 60, (WH, SKY2), kinds=('plus',), size=(10, 22), step=0.1), tr=('iris', 'circle', WH))

# ---- BREAKDOWN: "let me hear your singing..." (white, soft)
shot(B(63), B(65), bgp('plain', WH),
     cards=[card('15cry', mode='mul', bleed=True, kz=1.2, f=(0.45, 0.4), ent='fade', ed=0.8)],
     shapes=[shp('circle', 160 + 270 * i, 120 + 160 * (i % 4), 30 + 14 * (i % 3), SKYL, B(63) + 0.3 * i, a=0.7,
                 bob=(14, 0.25, i), ent='grow') for i in range(7)],
     texts=words(B(63, 2), 'LET_ME_HEAR', 1420, 760, 100, step=0.58, sh=NAV) +
           words(B(64, 1), 'YOUR_SINGING...', 1420, 900, 100, step=0.58, sh=NAV),
     ecg=[dict(t=B(63), y=960, amp=60, mode='calm', c=SKY2, gc=SKYL, th=4, don=2.0, a=0.8)])
shot(B(65), B(66), bgp('dots', SKYL, WH, P=64, r=6),
     cards=row(B(65), ['15crowd', '15sky'], h=720, cy=540, step=0.58))
shot(B(66), B(67), bgp('grid', WH, PNKL, P=120, v=(3, 0)),
     cards=[card('16top', mode='frame', w=1600, cy=430, rot=-1, ent='slide-u', sc=ROS)],
     ecg=[dict(t=B(66), y=880, amp=110, mode='fast', c=RED, gc=PNK, th=6, don=0.5)])

# ---- DROP: the hug (red / pink hearts)
FLASH.append((B(67), 1.0, 0.35, WH)); SHAKE.append((B(67), 24, 5))
shot(B(67), B(69), bgp('hearts', PNK, PNKL, P=120, r=20, v=(0, -2)),
     cards=[card('16hug', mode='mul', bleed=True, kz=1.12, f=(0.5, 0.5))],
     shapes=[shp('heart', 380, 520, 330, WH, B(67), layer='front', a=0.94, bp=0.06),
             shp('heart', 1560, 520, 300, WH, B(68), layer='front', a=0.94, bp=0.06)] + hearts(B(67), 16, 67, step=0.12),
     texts=words(B(67), "I'LL_BE|BESIDE_YOU,|POPPO-KUN!", 380, 520, 66, st='red', step=0.58) +
           words(B(68), 'I...|WILL_BE|WITH_YOU', 1560, 520, 76, st='ink', step=0.58), pulse=0.03)
shot(B(69), B(70), bgp('dots', RED, '#EE6170', P=64, r=9),
     cards=row(B(69), ['16bl', '16br'], h=700, cy=540, step=0.58, sc=NAV), shapes=hearts(B(69), 10, 69, cols=(WH, PNK)), pulse=0.03)
shot(B(70), B(71), bgp('hearts', PNKL, WH, P=110, r=18, v=(0, -1)),
     cards=[card('16couple', mode='frame', h=900, cx=W / 2, ent='zoom', sc=RED, kz=1.08)],
     ecg=[dict(t=B(70), y=540, amp=160, mode='beat', c=RED, gc=PNK, th=7, don=0.6, a=0.9)],
     shapes=hearts(B(70), 12, 70, size=(18, 40)), pulse=0.02)

# ---- DIP: his last beats
shot(B(71), B(72), bgp('plain', '#EEF2F7'),
     cards=[card('17r1', mode='frame', h=860, cx=1300, rot=2, ent='fade', ed=0.6, sc=SLT)],
     texts=label(B(71, 2), 'I, IIJIMA HATO', 520, 540, 34))
shot(B(72), B(73), bgp('plain', '#E3E8F0'),
     cards=[card('17sky', mode='frame', h=900, cx=W / 2, rot=-1, ent='fade', ed=0.6, sc=SLT, kz=1.06)])
shot(B(73), B(74), bgp('plain', '#D4DAE4'),
     cards=[card('17lie', mode='mul', bleed=True, kz=1.1, f=(0.4, 0.55), ent='fade', ed=0.4)],
     ecg=[dict(t=B(73) - 0.6, y=250, amp=120, mode='beat', c=RED, gc=PNK, th=6, don=0.01, flat=END_HIS)],
     texts=label(B(73, 1), 'LEFT THIS WORLD AT THE AGE OF', 1350, 560, 30) +
           [dict(s='17', st='big', size=200, x=1350, y=740, t=B(73, 2), ent='fade', ed=0.5, sh=SLT)])

# ---- FINAL CHORUS: her songs (sky / cream / pink, brightest)
FLASH.append((B(74), 1.0, 0.3, WH))
shot(B(74), B(75), bgp('dots', SKY, SKYL, P=64, r=9),
     shapes=[shp('rect', W / 2, 540, (760, 300), WH, B(74), ol=6, rot=-2, ent='pop')] + sprinkle(B(74), 14, 74, (WH, CRM, BLU)),
     texts=label(B(74), 'AFTERWARDS, TAKAGI HATSU', W / 2, 160, 32) +
           words(B(74, 1), 'DEBUTED_AS_A|SONG_WRITER', W / 2, 540, 120, st='ink', step=0.58),
     ecg=[dict(t=B(74), y=930, amp=80, mode='beat', c=WH, gc=SKY, th=6, don=0.6)], pulse=0.02)
shot(B(75), B(76), bgp('stars', CRM, CRML, P=110, r=15),
     cards=[card('18sing', mode='frame', h=900, cx=580, rot=-3, ent='slide-l', sc=BLU)],
     texts=words(B(75), 'SHE_KEPT|SINGING', 1360, 440, 130, step=0.58, sh=BLU) +
           label(B(75, 2), 'WITH ALL OF HER HEART AND SOUL', 1360, 700, 30), pulse=0.02)
shot(B(76), B(77), bgp('dots', PNKL, WH, P=64, r=8, v=(-1, 0)),
     cards=[card('18conc', mode='frame', w=1300, cx=W / 2, cy=470, rot=1, ent='slide-r', sc=ROS)],
     texts=label(B(76, 1), 'HER VOICE BECAME A HOT TOPIC IN SOCIETY', W / 2, 920, 32), pulse=0.02)
shot(B(77), B(78), bgp('stripes', SKYL, WH, P=100, r=0.5, v=(1, 1)),
     cards=[card('18mid', mode='frame', w=1500, cx=W / 2, cy=760, ent='slide-u', sc=BLU)],
     texts=label(B(77), 'ABOUT', W / 2, 140, 30) +
           words(B(77, 1), '40_THOUSAND|PEOPLE', W / 2, 360, 130, step=0.58, sh=BLU), pulse=0.02)
# flashback montage, two beats each
_fb = [('02hatsu', 'norm', SKY, SKYL, 'dots'), ('06shout', 'mul', PNK, PNKL, 'dots'), ('08laugh', 'mul', CRM, CRML, 'stars'),
       ('09fun', 'mul', PNK, PNKL, 'hearts'), ('07mid', 'mul', LILL, WH, 'dots'), ('10girl', 'frame', SKYL, WH, 'stars'),
       ('11br', 'frame', CRM, CRML, 'dots'), ('12girl', 'frame', PNKL, WH, 'hearts'), ('12hands', 'frame', RED, '#EE6170', 'dots'),
       ('14hato', 'frame', SKY, SKYL, 'stars'), ('16couple', 'frame', PNK, PNKL, 'hearts'), ('02hato', 'norm', CRM, CRML, 'stars')]
_ft = [B(78 + i // 2, 2 * (i % 2)) for i in range(12)] + [B(84)]
_lines = {0: ('TO_LIVE_MY_LIFE_OUT', 300), 2: ('WITH_EVERY_SECOND', 300), 4: ('I_HAVE_LEFT', 300),
          6: ('SO_MUCH_FUN', 820), 8: ('TOGETHER', 820), 10: ('EACH_AND_EVERY_DAY', 820)}
for i, (k, md, c1, c2, pat) in enumerate(_fb):
    t0, t1 = _ft[i], _ft[i + 1]
    if md == 'mul': cd = card(k, mode='mul', bleed=True, kz=1.1)
    else: cd = card(k, mode=md, h=960, cx=W / 2 + (300 if i % 2 else -300), rot=(3 if i % 2 else -3), ent='punch', sc=NAV)
    tx = []
    if i in _lines:
        s_, yy = _lines[i]; tx = [dict(s=s_.replace('_', ' '), st='big', size=96, x=W / 2, y=yy, t=t0, ent='stamp', sh=ROS)]
    shot(t0, t1, bgp(pat, c1, c2, P=100, r=14), cards=[cd], texts=tx, pulse=0.03,
         shapes=sprinkle(t0, 5, 100 + i, (WH, CRM, ROS), kinds=('plus', 'heart')))
shot(B(84), B(85), bgp('plain', WH),
     cards=[card('18mid', mode='frame', w=1300, cx=W / 2, cy=420, ent='fade', ed=0.5, sc=SLT)],
     texts=label(B(84, 1), 'FINALLY, HER PARENTS TOOK CARE OF HER', W / 2, 760, 30) +
           label(B(84, 2), 'UNTIL HER LAST BREATH.', W / 2, 830, 30, st='tag'))
shot(B(85), B(87), bgp('dots', SKYL, WH, P=70, r=8),
     cards=[card('18face', mode='frame', h=960, cx=W / 2, ent='zoom', kz=1.12, f=(0.5, 0.4), sc=BLU)],
     texts=words(B(85, 1), 'AND_HER|LAST|DYING_FACE', 320, 470, 76, step=0.58, st='ink') +
           words(B(86, 1), 'IS_OF_ONE|WHO_WAS|SATISFIED', 1600, 470, 76, step=0.58, st='ink'),
     shapes=sprinkle(B(85), 12, 85, (WH, CRM, SKY2), kinds=('plus', 'star')), pulse=0.02)
FLASH.append((B(87), 1.0, 0.4, WH))
shot(B(87), B(88), bgp('plain', WH),
     cards=[card('01face', mode='norm', bleed=True, kz=1.15, f=(0.62, 0.55))],
     shapes=sprinkle(B(87), 14, 87, (WH, CRM, PNK), kinds=('plus', 'star', 'heart'), size=(14, 34)))

# ---- OUTRO: title card
shot(B(88), DUR + 0.1, bgp('grid', WH, SKYL, P=120, v=(1, 0)),
     cards=[card('02logo', mode='norm', w=1100, cx=W / 2, cy=430, ent='pop', s1=1.03)],
     texts=label(B(88, 2), 'BY KOMI NAOSHI', W / 2, 700, 30),
     ecg=[dict(t=B(88), y=880, amp=110, mode='calm', c=BLU, gc=SKY, th=6, don=1.0, flat=B(90, 2))],
     shapes=sprinkle(B(88, 1), 12, 88, (SKY2, CRM, PNK)), tr=('iris', 'heart', PNK))

# ---------------------------------------------------------------- HUD: beats left
V_HERS = 221124617
def hers_left(t): return V_HERS - beats_between(B(15, 2), t)
V_HERS2 = hers_left(B(53))
HUDS = [
    dict(t0=B(15, 2), t1=B(53), name='HATSU TAKAGI', f=hers_left),
    dict(t0=B(53) + 0.25, t1=B(74), name='HATO IIJIMA', red=True,
         f=lambda t: 0 if t >= END_HIS else 1264 - beats_between(B(53), t)),
    dict(t0=B(74, 2), t1=B(87), name='HATSU TAKAGI',
         f=lambda t: 0 if t >= END_HERS else int(V_HERS2 * (1 - clamp((t - B(74, 2)) / (END_HERS - B(74, 2)))) ** 3)),
]
def hud(rgb, t):
    for h in HUDS:
        if not (h['t0'] <= t < h['t1']): continue
        a = clamp((t - h['t0']) / 0.3) * clamp((h['t1'] - t) / 0.3)
        v = h['f'](t); zero = v <= 0
        nm = sprite(h['name'], 'label', 20, box=RED if h.get('red') else '#111111')
        vs = sprite(f'{v:,} bts', 'mono', 40, box=RED if zero else NAV)
        x0, y0 = 70, 952
        blit(rgb, nm, x0 + 46 + nm.shape[1] / 2, y0 - 34, a=a)
        blit(rgb, vs, x0 + 46 + vs.shape[1] / 2, y0 + 14, a=a)
        if not zero:
            draw_shape(rgb, dict(k='heart', x=x0 + 18, y=y0 + 12, s=20, c=RED, t=-9, ent='none', bp=0.45, a=a), t)
        else:
            draw_shape(rgb, dict(k='heart', x=x0 + 18, y=y0 + 12, s=20, c=SLT, t=-9, ent='none', a=a), t)

# ---------------------------------------------------------------- transitions & frame
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
PMAP = (_xx + 0.4 * _yy) / (W + 0.4 * H)
del _yy, _xx
PRE, POST = 0.2, 0.28
def tr_mask(tr, phase, u):
    kind = tr[0]
    if kind == 'iris':
        k = tr[1]; scale = {'heart': 1.9, 'star': 2.6, 'diamond': 1.6}.get(k, 1.2) * math.hypot(W, H) / 2
        m = np.zeros((H, W), np.uint8)
        r = scale * (ein(u) if phase == 'A' else eout(u))
        if r > 1:
            pts = shape_pts(k, r, 25 * u) + np.float32([W / 2, H / 2])
            cv2.fillPoly(m, [np.int32(pts * 16)], 255, cv2.LINE_AA, 4)
        m = m.astype(np.float32) / 255
        return m if phase == 'A' else 1 - m
    if kind == 'wipe':
        if phase == 'A': return (PMAP < ein(u) * 1.05).astype(np.float32)
        return (PMAP > eout(u) * 1.05 - 0.05).astype(np.float32)
    return None

def shot_at(t):
    for i, s in enumerate(S):
        if s['t0'] <= t < s['t1']: return i
    return len(S) - 1

def render_shot(sh, t):
    rgb = background(sh, t)
    for s in sh['shapes']:
        if s.get('layer', 'back') == 'back': draw_shape(rgb, s, t)
    for c in sh['cards']: render_card(rgb, c, t, sh)
    for s in sh['shapes']:
        if s.get('layer', 'back') == 'front': draw_shape(rgb, s, t)
    for e in sh['ecg']: draw_ecg(rgb, e, t)
    for it in sh['texts']: draw_text(rgb, it, t)
    return rgb

def frame(fi):
    t = fi / FPS
    si = shot_at(t); sh = S[si]
    rgb = render_shot(sh, t)
    nxt = S[si + 1] if si + 1 < len(S) else None
    if nxt and nxt['tr'] and t >= nxt['t0'] - PRE:
        m = tr_mask(nxt['tr'], 'A', (t - (nxt['t0'] - PRE)) / PRE)
        if m is not None: rgb = rgb * (1 - m[..., None]) + hexc(nxt['tr'][-1]) * m[..., None]
    if sh['tr'] and t < sh['t0'] + POST:
        m = tr_mask(sh['tr'], 'B', (t - sh['t0']) / POST)
        if m is not None: rgb = rgb * (1 - m[..., None]) + hexc(sh['tr'][-1]) * m[..., None]
    rgb = np.clip(rgb, 0, 1)
    hud(rgb, t)
    # beat pulse / shake
    zoom = 1 + sh['pulse'] * math.exp(-since_beat(t) * 9)
    ox = oy = 0.0
    for ts, amp, dc in SHAKE:
        if ts <= t < ts + 1.0:
            k = amp * math.exp(-(t - ts) * dc); ox += k * math.sin(t * 71); oy += k * math.cos(t * 53)
    if zoom > 1.0005 or abs(ox) + abs(oy) > 0.3:
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, zoom); M[:, 2] += (ox, oy)
        rgb = cv2.warpAffine(rgb, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    for g0, g1 in GLITCH:
        if g0 <= t < g1:
            r_ = np.random.default_rng(fi)
            d = int(14 * (1 - (t - g0) / (g1 - g0))) + 2
            rgb[..., 0] = np.roll(rgb[..., 0], d, 1); rgb[..., 2] = np.roll(rgb[..., 2], -d, 1)
            for _ in range(6):
                y0 = int(r_.integers(0, H - 60)); hh = int(r_.integers(10, 60))
                rgb[y0:y0 + hh] = np.roll(rgb[y0:y0 + hh], int(r_.integers(-60, 60)), 1)
    for tf, pk, dc, col in FLASH:
        if tf <= t < tf + 2:
            f = pk * math.exp(-(t - tf) / dc)
            if f > 0.004: rgb = rgb + (hexc(col) - rgb) * min(f, 1)
    fo = clamp((DUR - t) / 1.4)
    if fo < 1: rgb = rgb * fo + (1 - fo)
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)

# ---------------------------------------------------------------- main
def stills(times, d='stills'):
    d = os.path.join(HERE, d); os.makedirs(d, exist_ok=True)
    thumbs = []
    for tt in times:
        fr = frame(int(round(tt * FPS)))
        cv2.imwrite(os.path.join(d, f'{tt:06.2f}.png'), fr[..., ::-1])
        th = cv2.resize(fr[..., ::-1], (384, 216), interpolation=cv2.INTER_AREA)
        cv2.putText(th, f'{tt:.2f}', (6, 20), 0, 0.55, (0, 0, 255), 2); thumbs.append(th)
    while len(thumbs) % 6: thumbs.append(np.zeros_like(thumbs[0]))
    rows = [np.hstack(thumbs[i:i + 6]) for i in range(0, len(thumbs), 6)]
    for j in range(0, len(rows), 6):
        cv2.imwrite(os.path.join(d, f'contact_{j // 6:02d}.jpg'), np.vstack(rows[j:j + 6]), [cv2.IMWRITE_JPEG_QUALITY, 85])

def _still(tt):
    return tt, frame(int(round(tt * FPS)))

def sheet(step):
    from multiprocessing import Pool
    times = [round(x, 2) for x in np.arange(0.5, DUR, step)]
    d = os.path.join(HERE, 'stills'); os.makedirs(d, exist_ok=True)
    thumbs = {}
    with Pool(max(1, os.cpu_count() - 1)) as pool:
        for tt, fr in pool.imap(_still, times):
            th = cv2.resize(fr[..., ::-1], (384, 216), interpolation=cv2.INTER_AREA)
            cv2.putText(th, f'{tt:.1f}', (6, 20), 0, 0.55, (0, 0, 255), 2); thumbs[tt] = th
    th = [thumbs[t] for t in times]
    while len(th) % 6: th.append(np.zeros_like(th[0]))
    rows = [np.hstack(th[i:i + 6]) for i in range(0, len(th), 6)]
    for j in range(0, len(rows), 6):
        cv2.imwrite(os.path.join(d, f'sheet_{j // 6:02d}.jpg'), np.vstack(rows[j:j + 6]), [cv2.IMWRITE_JPEG_QUALITY, 85])

def video():
    import imageio_ffmpeg
    from multiprocessing import Pool
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmpv = os.path.join(HERE, '_video.mp4'); tmpa = os.path.join(HERE, '_audio.m4a')
    subprocess.run([ff, '-y', '-v', 'error', '-i', SONG, '-t', f'{DUR:.3f}',
                    '-af', f'afade=t=in:d=0.2,afade=t=out:st={DUR - 1.6:.2f}:d=1.6,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000',
                    '-c:a', 'aac', '-b:a', '192k', tmpa], check=True)
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                          '-tune', 'animation', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmpv],
                         stdin=subprocess.PIPE)
    with Pool(max(1, os.cpu_count() - 1)) as pool:
        for i, fr in enumerate(pool.imap(frame, range(N), chunksize=6)):
            p.stdin.write(fr.tobytes())
            if i % 300 == 0: print(f'frame {i}/{N}', flush=True)
    p.stdin.close(); p.wait()
    subprocess.run([ff, '-y', '-v', 'error', '-i', tmpv, '-i', tmpa, '-map', '0:v', '-map', '1:a', '-c', 'copy',
                    '-t', f'{DUR:.3f}', '-movflags', '+faststart', OUT], check=True)
    os.remove(tmpv); os.remove(tmpa)
    print('wrote', OUT)

if __name__ == '__main__':
    if sys.argv[1] == 'stills': stills([float(x) for x in sys.argv[2].split(',')])
    elif sys.argv[1] == 'sheet': sheet(float(sys.argv[2]) if len(sys.argv) > 2 else 2.0)
    else: video()
