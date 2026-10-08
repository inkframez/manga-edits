"""Toki Doki (刻どキ) - LYRIC version. Pastel-pop manga MV (full song 3:34, 1920x1080, 30fps) with the Japanese
lyrics as the hero typography layer (J-pop lyric-MV motion graphics) over the v1 story edit.

Built on render.py (v1). Same palette, panels, ECG heartbeat line, beats-left HUD, transitions.
Lyric layer: per-character kanji/kana reveals on the (estimated) vocal timing - pop / stamp / blur-in / drop / rise /
slide / masked top-down wipe; horizontal rows and 縦書き columns (right-to-left, small kana shifted, ー/… rotated);
hero words (ドキドキ pulsing on the kick, 鼓動, 君の色, 光, 青さ, 声, ありがとう); ときどき outline echoes; ドキ SFX
bursts on ECG spikes; small English translation (Segoe UI Semilight) under each line; J-MV decoration (rule lines with
romaji + line numbers, 「」 corner brackets, hanko-style seals, repeated-text bands); backing plates over busy panels.
Lyric timings: table at "LYRIC TIMING" below (lyrics_timing.json + RETIME overrides).

Usage:
  python render_lyrics.py stills 10,60,120   -> ./stills_lyrics/<t>.jpg + contact_00.jpg
  python render_lyrics.py lines [full]       -> one still per lyric line -> stills_lyrics/contact_*.jpg
  python render_lyrics.py sheet [step]       -> stills_lyrics/sheet_*.jpg
  python render_lyrics.py video              -> ../tokidoki-lyrics.mp4
"""
import os, sys, json, math, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAN = os.path.join(ROOT, 'panels')
SONG = os.path.join(ROOT, 'tokidoki-bg-song.mp3')
OUT = os.path.join(ROOT, 'tokidoki-lyrics.mp4')
W, H, FPS = 1920, 1080, 30
BM = json.load(open(os.path.join(HERE, 'beatmap.json')))
DUR = math.floor(BM['duration'] * FPS) / FPS
N = int(round(DUR * FPS))
BEATS = np.array(BM['beats'])
FD = 'C:/Windows/Fonts/' if os.name == 'nt' else os.path.join(os.path.dirname(ROOT), 'fonts') + '/'   # tools/setup_fonts.py
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
    ev = np.array(e['events'], np.float64) if 'events' in e else ecg_events(e.get('mode', 'beat'))
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


# ================================================================ LYRIC TIMING (centralised - retime here)
# Source: lyrics_timing.json (estimated). RETIME overrides (start, end) per line index; None = keep.
LYR_SRC = json.load(open(os.path.join(HERE, 'lyrics_timing.json'), encoding='utf-8'))['lines']
VSEG = json.load(open(os.path.join(HERE, 'vocal_segments.json'), encoding='utf-8'))['vocal_segments']
RETIME = {
    0: (None, 25.30),    # end just before line 2 (was 24.88)
    1: (25.40, None),    # 24.88 -> B(10): the 0.4 s blip at 24.88 is a breath; sung phrase starts 26.0, cut lands on B(10)
}
ROMAJI = [
    'kazoerareta kodou no hitotsu', 'sotto mune ni te wo ateta', 'shizuka ni ikiru sore ga tadashii to',
    'zutto jibun ni iikikaseta', 'soko e kimi ga tobira wo akete', 'tomatta jikan ga ugokidashita',
    'dokidoki shite iin da yo', 'watashi no mune wa kimi no iro', 'ichibyou goto ni hikari ga fueru',
    'tokidoki itakute tokidoki ureshii', 'kono sora no shita motto hashiritai',
    'te wo tsunaidara hayaku naru oto', 'kowakunai yo to kimi ga warau', 'shiranakatta sekai no aosa',
    'shiranakatta watashi no koe', 'ashita no kazu wo wasureru kurai', 'kyou ga mabushikute nakisou da',
    'dokidoki shite iin da yo', 'watashi no mune wa kimi no iro', 'ichibyou goto ni hikari ga fueru',
    'tokidoki itakute tokidoki ureshii', 'kono sora no shita motto hashiritai',
    'tatoe kodou ga tsukiru hi ga kite mo', 'kimi ga kureta natsu wa kienai', 'hitotsu hitotsu kizanda omoi',
    'sora ni tokete mo tsuzuiteku', 'dokidoki shite iin da yo', 'watashi no mune wa kimi no iro',
    'ichibyou goto ni hikari ga fueru', 'tokidoki itakute tokidoki ureshii', 'arigatou koi wo sasete kurete',
    'doki...', 'doki...',
]
def LT(i):
    a, b = LYR_SRC[i]['start'], LYR_SRC[i]['end']
    r = RETIME.get(i, (None, None))
    return (a if r[0] is None else r[0]), (b if r[1] is None else r[1])

# ================================================================ JAPANESE TYPOGRAPHY ENGINE
JPF = {'B': FD + 'YuGothB.ttc', 'M': FD + 'YuGothM.ttc', 'L': FD + 'YuGothL.ttc'}
ENF, ROF, NUMF = FD + 'segoeuisl.ttf', FD + 'segoeui.ttf', FD + 'consola.ttf'
SMALLK = set('ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ')
ROTK = set('ー…〜～')
GST = {   # glyph styles: fill, stroke colour + width (em), flat offset shadow colour + offset (em)
    'ink': dict(fill=NAV, st=WH, sw=0.08), 'inkb': dict(fill=NAV, st=WH, sw=0.08, sh=SKY2, so=0.06),
    'inkp': dict(fill=NAV, st=WH, sw=0.08, sh=PNK, so=0.06),
    'white': dict(fill=WH, st=NAV, sw=0.04, sh=NAV, so=0.07), 'whiteb': dict(fill=WH, st=BLU, sw=0.04, sh=BLU, so=0.07),
    'whiter': dict(fill=WH, st=RED, sw=0.04, sh=RED, so=0.07), 'whitep': dict(fill=WH, st=NAV, sw=0.04, sh=ROS, so=0.07),
    'red': dict(fill=RED, st=WH, sw=0.08), 'redn': dict(fill=RED, st=WH, sw=0.07, sh=NAV, so=0.06),
    'blue': dict(fill=BLU, st=WH, sw=0.08), 'bluen': dict(fill=BLU, st=WH, sw=0.07, sh=NAV, so=0.06),
    'sky': dict(fill=SKY2, st=WH, sw=0.08, sh=NAV, so=0.06), 'pink': dict(fill=ROS, st=WH, sw=0.08),
    'pinkn': dict(fill=ROS, st=WH, sw=0.07, sh=NAV, so=0.06), 'grey': dict(fill=SLT, st=WH, sw=0.08),
    'out': dict(fill=None, st=NAV, sw=0.035), 'outr': dict(fill=None, st=ROS, sw=0.035),
    'outw': dict(fill=None, st=WH, sw=0.035), 'outb': dict(fill=None, st=SKY2, sw=0.035),
    'soft': dict(fill=NAV, st=None), 'softr': dict(fill=RED, st=None),
}
_EMC = {}
def em_cy(w, size):
    k = (w, size)
    if k not in _EMC:
        _, t_, _, b_ = font(JPF[w], size).getbbox('口'); _EMC[k] = (t_ + b_) / 2
    return _EMC[k]

_GL = {}
def glyph(ch, w, size, st, vert=False):
    """premultiplied RGBA sprite of one character, em box centred on the sprite centre.
    vert=True: tategaki forms - small kana shifted to the upper right, ー/… rotated 90 deg."""
    key = (ch, w, size, st, vert)
    g = _GL.get(key)
    if g is not None: return g
    if len(_GL) > 1500: _GL.clear()
    d = GST[st]; f = font(JPF[w], size)
    sw = int(round(size * d.get('sw', 0))) if d.get('st') else 0
    so = int(round(size * d.get('so', 0))) if d.get('sh') else 0
    pad = sw + so + int(size * 0.2) + 4
    S_ = size + 2 * pad
    ox, oy = S_ / 2 - f.getlength(ch) / 2, S_ / 2 - em_cy(w, size)
    if vert and ch in SMALLK: ox += size * 0.10; oy -= size * 0.12
    def mask(stw):
        im = Image.new('L', (S_, S_), 0)
        ImageDraw.Draw(im).text((ox, oy), ch, font=f, fill=255, stroke_width=stw, stroke_fill=255)
        m = np.asarray(im, np.float32) / 255
        if vert and ch in ROTK: m = np.ascontiguousarray(np.rot90(m, -1))
        return m
    mf = mask(0); ms = mask(sw) if sw else mf
    out = np.zeros((S_, S_, 4), np.float32)
    def over(col, m):
        a = m[..., None]; out[..., :3] = out[..., :3] * (1 - a) + hexc(col) * a; out[..., 3:] = out[..., 3:] * (1 - a) + a
    if so: over(d['sh'], np.roll(np.roll(ms, so, 0), so, 1))
    if d.get('fill') is None: over(d['st'], np.clip(ms - mf, 0, 1))
    else:
        if sw: over(d['st'], ms)
        over(d['fill'], mf)
    _GL[key] = out
    return out

_GLW = {}
def glow_spr(ch, w, size, st, vert, col=CRML):
    key = (ch, w, size, st, vert, col)
    if key not in _GLW:
        g = glyph(ch, w, size, st, vert); a = cv2.GaussianBlur(g[..., 3], (0, 0), size * 0.12)
        a = np.clip(a * 1.8, 0, 1); o = np.zeros_like(g); o[..., 3] = a; o[..., :3] = hexc(col) * a[..., None]
        _GLW[key] = o
    return _GLW[key]

_LS = {}
def latin_spr(s, size, col, fp=ENF, trk=0.04, maxw=99999, al=1.0):
    """premultiplied RGBA sprite of (word-wrapped, letter-spaced) Latin text, lines centred."""
    key = (s, size, col, fp, trk, maxw, al)
    if key in _LS: return _LS[key]
    f = font(fp, size); tk = size * trk
    def wid(x): return sum(f.getlength(c) + tk for c in x) - tk
    lines, cur = [], ''
    for wd in s.split(' '):
        tr = (cur + ' ' + wd).strip()
        if cur and wid(tr) > maxw: lines.append(cur); cur = wd
        else: cur = tr
    lines.append(cur)
    asc, desc = f.getmetrics(); lh = int((asc + desc) * 1.02)
    Wd = int(max(wid(l) for l in lines)) + 8; Hd = lh * len(lines) + 6
    im = Image.new('L', (Wd, Hd), 0); dr = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        x = (Wd - wid(l)) / 2
        for c in l: dr.text((x, 3 + i * lh), c, font=f, fill=255); x += f.getlength(c) + tk
    a = np.asarray(im, np.float32) / 255 * al
    o = np.zeros((Hd, Wd, 4), np.float32); o[..., 3] = a; o[..., :3] = hexc(col) * a[..., None]
    _LS[key] = o
    return o

def blit2(rgb, spr, cx, cy, sc=1.0, rot=0.0, a=1.0, fy=1.0, blur=0.0):
    if fy < 1:
        if fy <= 0.01: return
        spr = spr.copy(); spr[int(spr.shape[0] * fy):] = 0
    if blur > 0.6: spr = cv2.GaussianBlur(spr, (0, 0), blur)
    blit(rgb, spr, cx, cy, sc, rot, a)

def line_rect(rgb, x0, y0, x1, y1, th, col, a, t=None):
    """thin rule as an anti-aliased rect from (x0,y0) to (x1,y1)."""
    L_ = math.hypot(x1 - x0, y1 - y0)
    if L_ < 1 or a <= 0.01: return
    ang = -math.degrees(math.atan2(y1 - y0, x1 - x0))
    draw_shape(rgb, dict(k='rect', x=(x0 + x1) / 2, y=(y0 + y1) / 2, s=(L_ / 2, th / 2), c=col, t=-9, ent='none', rot=ang, a=a), 0)

def parse_jp(jp):
    rows, tag = [[]], 0
    for ch in jp:
        if ch == '|': rows.append([]); continue
        if ch in '{[': tag = 1 if ch == '{' else 2; continue
        if ch in '}]': tag = 0; continue
        rows[-1].append((ch, tag))
    return rows

def near_beat(t):
    i = int(np.argmin(np.abs(BEATS - t))); return float(BEATS[i])

def auto_pt(t0, t1, n):
    """phrase start times: even estimate, pulled to the nearest detected vocal onset (vocal_segments.json)."""
    pts = [t0]; dur = t1 - t0
    starts = [s for s, e in VSEG if t0 + 0.35 < s < t1 - 0.5]
    for k in range(1, n):
        est = t0 + dur * 0.9 * k / n
        c = [s for s in starts if abs(s - est) < 0.9 and s > pts[-1] + 0.35]
        v = min(c, key=lambda s: abs(s - est)) if c else est
        v = min(v, t0 + 0.7 * dur)          # every phrase in by 70% of the line -> fully readable before it leaves
        pts.append(max(v, pts[-1] + 0.35))
    return pts

LINES, SFX = [], []
def lyric(idx, jp, mode='h', x=W / 2, y=200, size=100, w='B', st='ink', hs=1.0, hst=None, hs2=1.0, hst2=None, hw=None,
          hcols=None, align='c', pos=None, sizes=None, rst=None, anim='pop', anims=None, hanim=None, ed=0.32, cps=None,
          pt=None, exit='up', plate=None, pc=WH, psc=None, pa=0.95, prot=0, ppad=None, pol=True, pr=None,
          deco=('meta',), dc=NAV, en=True, enc=NAV, ena=0.82, ens=26, en_pos=None, en_w=None, en_t=None,
          echo=None, ecol='outr', glow=False, gcol=CRML, ripple=False, hbp=0.0, bp=0.0, col_dy=None, shapes=(),
          t0=None, t1=None, lh=0.22, trk=0.98):
    """One lyric line. jp markup: '|' = new row (h) / new column (v, right-to-left), ' ' = phrase gap,
    {..} = hero chars (size hs, style hst / hcols), [..] = alt chars (hs2, hst2)."""
    a0, a1 = LT(idx); t0 = a0 if t0 is None else t0; t1 = a1 if t1 is None else t1
    rows = parse_jp(jp); vert = mode == 'v'
    G, ph = [], -1
    rowinfo = []
    for r, row in enumerate(rows):
        sz0 = sizes[r] if sizes else size; st0 = rst[r] if rst else st
        plain = ''.join(c for c, _ in row)
        ech = set()
        if echo:
            i = plain.find(echo)
            while i >= 0: ech.update(range(i, i + len(echo))); i = plain.find(echo, i + 1)
        items, ph, new, hk = [], ph + 1, True, 0
        for ci, (ch, tag) in enumerate(row):
            if ch == ' ':
                items.append(dict(sp=True, sz=sz0)); ph += 1; continue
            s_ = int(round(sz0 * (hs if tag == 1 else hs2 if tag == 2 else 1.0)))
            if tag == 1: sty = hcols[hk % len(hcols)] if hcols else (hst or st0); hk += 1
            elif tag == 2: sty = hst2 or st0
            else: sty = st0
            items.append(dict(ch=ch, sz=s_, st=sty, w=(hw or w) if tag == 1 else w, hero=tag == 1, ph=ph, echo=ci in ech))
        rowinfo.append((items, sz0))
    # ---- layout
    cur_y, prev_x, prev_w = None, None, None
    for r, (items, sz0) in enumerate(rowinfo):
        if not vert:
            adv = [(0.4 * it['sz'] if it.get('sp') else it['sz'] * trk) for it in items]
            rw = sum(adv); rh = max((it['sz'] for it in items if not it.get('sp')), default=sz0)
            if pos: cx_, top = pos[r]
            else:
                cx_ = x; top = y if cur_y is None else cur_y
            cur_y = top + rh + lh * sz0
            left = cx_ - rw / 2 if align == 'c' else (cx_ if align == 'l' else cx_ - rw)
            acc = 0
            for it, a_ in zip(items, adv):
                if not it.get('sp'):
                    G.append(dict(it, x=left + acc + a_ / 2, y=top + rh - it['sz'] / 2))
                acc += a_
        else:
            cw = max((it['sz'] for it in items if not it.get('sp')), default=sz0)
            if pos: cx_, top = pos[r]
            else:
                cx_ = x if prev_x is None else prev_x - (prev_w / 2 + cw / 2 + 0.3 * sz0); top = y
            if col_dy: top += col_dy[r]
            prev_x, prev_w = cx_, cw
            acc = 0
            for it in items:
                if it.get('sp'): acc += 0.45 * it['sz']; continue
                G.append(dict(it, x=cx_, y=top + acc + it['sz'] / 2)); acc += it['sz'] * trk
    # ---- timing
    nph = max(g['ph'] for g in G) + 1
    pts = pt if pt is not None else auto_pt(t0, t1, nph)
    cnt = [0] * nph
    for g in G: g['i'] = cnt[g['ph']]; cnt[g['ph']] += 1
    for gi, g in enumerate(G):
        k = g['ph']; win = (pts[k + 1] if k + 1 < nph else t1) - pts[k]
        cc = cps[k] if isinstance(cps, (list, tuple)) else cps
        c = cc if cc is not None else min(0.11, 0.5 * win / max(cnt[k], 1))
        g['tin'] = pts[k] + g['i'] * c
        g['tout'] = t1 + 0.006 * gi
        g['anim'] = (hanim if (g['hero'] and hanim) else (anims[k] if anims else anim))
        g['ed'] = ed
        g['bp'] = hbp if g['hero'] else bp
        g['glow'] = glow and g['hero']; g['rip'] = ripple and g['hero']
        g['vert'] = vert
    bx0 = min(g['x'] - g['sz'] / 2 for g in G); bx1 = max(g['x'] + g['sz'] / 2 for g in G)
    by0 = min(g['y'] - g['sz'] / 2 for g in G); by1 = max(g['y'] + g['sz'] / 2 for g in G)
    L = dict(idx=idx, t0=t0, t1=t1, G=G, exit=exit, xd=0.55 if exit == 'melt' else 0.17, ecol=ecol, gcol=gcol,
             vert=vert, shapes=list(shapes), deco=list(deco), dc=dc, size=size)
    # ---- english translation
    E = None
    if en:
        txt = LYR_SRC[idx]['en']
        mw = en_w or max(bx1 - bx0 + 20, 380)
        spr = latin_spr(txt, ens, enc, maxw=mw, al=ena)
        if en_pos: ex, ey = en_pos
        else:
            ex = (bx0 + spr.shape[1] / 2 - 4) if align == 'l' and not vert else (bx0 + bx1) / 2
            ey = by1 + 0.3 * size + spr.shape[0] / 2
        E = dict(spr=spr, x=ex, y=ey, t=(en_t if en_t is not None else t0 + 0.3))
        bx0, bx1 = min(bx0, ex - spr.shape[1] / 2), max(bx1, ex + spr.shape[1] / 2)
        by0, by1 = min(by0, ey - spr.shape[0] / 2), max(by1, ey + spr.shape[0] / 2)
    L['E'] = E
    # ---- plate (backing shape so lines stay readable over busy panels)
    pad = ppad if ppad is not None else 0.3 * size
    px0, py0, px1, py1 = bx0 - pad, by0 - pad, bx1 + pad, by1 + pad
    L['box'] = (px0, py0, px1, py1)
    pcx, pcy, pw, ph_ = (px0 + px1) / 2, (py0 + py1) / 2, (px1 - px0) / 2, (py1 - py0) / 2
    tp, te = t0 - 0.12, t1 + 0.22
    pl = []
    if plate in ('card', 'soft'):
        if psc and plate == 'card':
            pl.append(dict(k='rect', x=pcx + 14, y=pcy + 14, s=(pw, ph_), c=psc, t=tp, end=te, ent='grow', ed=0.25, rot=prot, a=pa))
        pl.append(dict(k='rect', x=pcx, y=pcy, s=(pw, ph_), c=pc, t=tp, end=te, ent='grow', ed=0.25, rot=prot, a=pa,
                       **({'ol': 4, 'oc': NAV} if (pol and plate == 'card') else {})))
    elif plate == 'band':
        pl.append(dict(k='rect', x=W / 2, y=pcy, s=(W / 2 + 40, ph_), c=pc, t=tp, end=te, ent='slide-r', ed=0.3, rot=prot, a=pa, dist=1200))
        L['box'] = (40, py0, W - 40, py1)
    elif plate == 'circle':
        r_ = pr or max(pw, ph_) * 1.02
        if psc: pl.append(dict(k='circle', x=pcx + 14, y=pcy + 14, s=r_, c=psc, t=tp, end=te, ent='pop', ed=0.3, a=pa))
        pl.append(dict(k='circle', x=pcx, y=pcy, s=r_, c=pc, t=tp, end=te, ent='pop', ed=0.3, a=pa, **({'ol': 4, 'oc': NAV} if pol else {})))
        L['box'] = (pcx - r_, pcy - r_, pcx + r_, pcy + r_)
    L['plates'] = pl
    b = L['box']
    if b[0] < 16 or b[1] < 16 or b[2] > W - 16 or b[3] > H - 16:
        print(f'WARNING line {idx}: box {tuple(int(v) for v in b)} near/over frame edge', flush=True)
    LINES.append(L)
    return L

def draw_deco(rgb, L, t):
    t0, t1 = L['t0'], L['t1']
    fin = eout((t - t0 + 0.05) / 0.5); fo = 1 - clamp((t - t1) / 0.3)
    a = fin * fo
    if a <= 0.01: return
    x0, y0, x1, y1 = L['box']; dc = L['dc']
    for d in L['deco']:
        kind = d if isinstance(d, str) else d['k']
        if kind == 'meta':
            ro = latin_spr(ROMAJI[L['idx']], 17, dc, fp=ROF, trk=0.22, al=0.75)
            nm = latin_spr(f'{L["idx"] + 1:02d} / 33', 17, dc, fp=NUMF, trk=0.1, al=0.75)
            if not L['vert']:
                above = y0 - 44 > 10
                ry = y0 - 14 if above else y1 + 14
                line_rect(rgb, x0, ry, x0 + (x1 - x0) * fin, ry, 2.5, dc, a * 0.8)
                ty = ry - 14 if above else ry + 15
                blit(rgb, nm, x0 + nm.shape[1] / 2, ty, a=a)
                blit(rgb, ro, x1 - ro.shape[1] / 2, ty, a=a)
            else:
                left = x0 - 44 > 10
                rx = x0 - 14 if left else x1 + 14
                line_rect(rgb, rx, y0, rx, y0 + (y1 - y0) * fin, 2.5, dc, a * 0.8)
                tx = rx - 15 if left else rx + 15
                blit(rgb, ro, tx, y0 + ro.shape[1] / 2, rot=-90, a=a)
                blit(rgb, nm, tx, y1 - nm.shape[1] / 2, rot=-90, a=a)
        elif kind == 'brk':     # 「 」 corner frame
            col = d.get('c', RED) if isinstance(d, dict) else RED
            g = d.get('g', 18) if isinstance(d, dict) else 18
            ln = 0.18 * (x1 - x0) * fin + 30; lv = min(0.5 * (y1 - y0), 0.25 * (y1 - y0) * fin + 30)
            X0, Y0, X1, Y1 = x0 - g, y0 - g, x1 + g, y1 + g
            line_rect(rgb, X0, Y0, X0 + ln, Y0, 7, col, a); line_rect(rgb, X0, Y0 - 3.5, X0, Y0 + lv, 7, col, a)
            line_rect(rgb, X1 - ln, Y1, X1, Y1, 7, col, a); line_rect(rgb, X1, Y1 - lv, X1, Y1 + 3.5, 7, col, a)
        elif kind == 'seal':    # circular hanko-style stamp
            ts = d.get('t', t0 + 0.25)
            if t < ts: continue
            e = clamp((t - ts) / 0.3); sc = lerp(1.8, 1, eout(e)); aa = clamp(e * 3) * fo
            draw_shape(rgb, dict(k='ring', x=d['x'], y=d['y'], s=d['r'] * sc, c=d.get('c', RED), t=-9, ent='none',
                                 ring=5, a=aa * 0.9), t)
            draw_shape(rgb, dict(k='ring', x=d['x'], y=d['y'], s=d['r'] * 0.84 * sc, c=d.get('c', RED), t=-9, ent='none',
                                 ring=2, a=aa * 0.9), t)
            gs = int(d['r'] * 1.05)
            blit(rgb, glyph(d['ch'], 'B', gs, d.get('st', 'softr')), d['x'], d['y'], sc, d.get('rot', -12) + 6 * math.sin(t), aa)
            if d.get('sub'):
                sp = latin_spr(d['sub'], 15, d.get('c', RED), fp=NUMF, trk=0.2)
                blit(rgb, sp, d['x'], d['y'] + d['r'] * 1.25, a=aa)

def draw_glyph(rgb, L, g, t):
    lt = t - g['tin']
    if lt < 0: return
    e = clamp(lt / g['ed']); an = g['anim']; sz = g['sz']
    sc, a, dx, dy, rot, blur, fy = 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0
    if an == 'pop': sc = lerp(0.3, 1, eback(e)); a = clamp(e * 3)
    elif an == 'stamp': sc = lerp(2.0, 1, eout(e)); a = clamp(e * 2.5); rot = 10 * (1 - eout(e))
    elif an == 'blur': sc = lerp(1.35, 1, eout(e)); a = eout(e); blur = 9 * (1 - eout(e)) * sz / 100
    elif an == 'drop': dy = -(1 - eback(e)) * sz * 0.9; a = clamp(e * 3)
    elif an == 'rise': dy = sz * 0.5 * (1 - eout(e)); a = eout(e); blur = 4 * (1 - e) * sz / 100
    elif an == 'slide': dx = -sz * 1.4 * (1 - eout(e)); a = eout(e); rot = 8 * (1 - eout(e))
    elif an == 'wipe': fy = eout(e); dy = -0.08 * sz * (1 - eout(e))
    elif an == 'spin': sc = eback(e); rot = 90 * (1 - eout(e))
    k = clamp((t - g['tout']) / L['xd'])
    if k > 0:
        if L['exit'] == 'melt': a *= 1 - k; dy -= 0.6 * sz * k; blur = max(blur, 10 * k * sz / 100); sc *= 1 + 0.15 * k
        elif L['exit'] == 'pop': a *= 1 - k; sc *= 1 - 0.6 * k
        else: a *= 1 - k; dy -= 0.3 * sz * k
    if a <= 0.01 or sc <= 0.01: return
    if g['bp']: sc *= 1 + g['bp'] * math.exp(-since_beat(t) * 9)
    x, y = g['x'] + dx, g['y'] + dy
    if g['rip']:
        for bt in BEATS[(BEATS > g['tin']) & (BEATS <= t) & (BEATS > t - 1.2)]:
            u = (t - bt) / 1.2
            draw_shape(rgb, dict(k='ring', x=x, y=y, s=sz * 0.62 + sz * 0.9 * eout(u), c=ROS, t=-9, ent='none',
                                 ring=5, a=(1 - u) * 0.75 * a), t)
    if g['glow']:
        gl = glow_spr(g['ch'], g['w'], sz, g['st'], g['vert'], L['gcol'])
        blit(rgb, gl, x, y, sc * 1.1, rot, a * (0.75 + 0.25 * math.sin(t * 6)))
    if g['echo']:
        eo = eout(clamp(lt / 0.6))
        for j, aj in ((2, 0.35), (1, 0.6)):
            blit(rgb, glyph(g['ch'], g['w'], sz, L['ecol'], g['vert']), x + j * 0.09 * sz * eo, y - j * 0.09 * sz * eo, sc, rot, a * aj)
    blit2(rgb, glyph(g['ch'], g['w'], sz, g['st'], g['vert']), x, y, sc, rot, a, fy, blur)

def draw_line(rgb, L, t):
    if t < L['t0'] - 0.3 or t > L['t1'] + 0.9: return
    for s in L['plates']: draw_shape(rgb, s, t)
    for s in L['shapes']: draw_shape(rgb, s, t)
    draw_deco(rgb, L, t)
    for g in L['G']: draw_glyph(rgb, L, g, t)
    E = L['E']
    if E and t >= E['t']:
        e = eout((t - E['t']) / 0.4); k = clamp((t - L['t1']) / 0.2)
        blit(rgb, E['spr'], E['x'], E['y'] + 14 * (1 - e) - 10 * k, a=e * (1 - k))

def sfx(t, x, y, size=72, st='redn', rot=-8, s='ドキ'):
    SFX.append(dict(t=t, x=x, y=y, size=size, st=st, rot=rot, s=s))
def ecg_sfx(e, a, b, size=70, st='redn', every=1, dx=0, dy=0):
    ev = np.array(e['events']) if 'events' in e else BEATS
    sel = [float(v) for v in ev if a <= v < b][::every]
    for i, te in enumerate(sel):
        sfx(te, e.get('x1', W) + dx, e['y'] - e['amp'] * 1.05 - size * 0.6 + dy, size, st, rot=(-9 if i % 2 else 7))
def draw_sfx(rgb, s, t):
    lt = t - s['t']
    if lt < 0 or lt > 0.62: return
    sc = lerp(1.8, 1, eout(lt / 0.14)); a = clamp(lt / 0.04) * (1 - clamp((lt - 0.36) / 0.26))
    n = len(s['s']); sz = s['size']; c, si = math.cos(math.radians(s['rot'])), math.sin(math.radians(s['rot']))
    for i, ch in enumerate(s['s']):
        ox = (i - (n - 1) / 2) * sz * 0.92 * sc
        blit(rgb, glyph(ch, 'B', sz, s['st']), s['x'] + ox * c, s['y'] - ox * si - 18 * lt, sc, s['rot'], a)

def lyrics_layer(rgb, t):
    for L in LINES: draw_line(rgb, L, t)
    for s in SFX: draw_sfx(rgb, s, t)

# ---------------------------------------------------------------- repeated-text bands (shot level, behind cards)
_BS = {}
def band_spr(s, size, col, w='B'):
    key = (s, size, col, w)
    if key not in _BS:
        f = font(JPF[w], size) if any(ord(c) > 255 for c in s) else font(BLACKF, size)
        tw = int(f.getlength(s)) + 2; asc, desc = f.getmetrics()
        im = Image.new('L', (tw, asc + desc + 4), 0); ImageDraw.Draw(im).text((0, 2), s, font=f, fill=255)
        a = np.asarray(im, np.float32) / 255
        o = np.zeros(a.shape + (4,), np.float32); o[..., 3] = a; o[..., :3] = hexc(col) * a[..., None]
        reps = W // tw + 2
        _BS[key] = np.tile(o, (1, reps, 1)), tw
    return _BS[key]
def band(s, y, size=80, col=WH, a=0.15, v=-50, w='B'): return dict(s=s, y=y, size=size, col=col, a=a, v=v, w=w)
def draw_band(rgb, b, t):
    spr, per = band_spr(b['s'], b['size'], b['col'], b['w'])
    off = int((t * b['v']) % per)
    strip = spr[:, off:off + W]
    h = strip.shape[0]; y0 = int(b['y'] - h / 2); y1 = y0 + h
    sy0, sy1 = max(0, y0), min(H, y1)
    if sy1 <= sy0: return
    st_ = strip[sy0 - y0:sy1 - y0]; ww = st_.shape[1]
    reg = rgb[sy0:sy1, :ww]; al = st_[..., 3:4] * b['a']
    reg[:] = reg * (1 - al) + st_[..., :3] * b['a']

# ---------------------------------------------------------------- timeline helpers
S = []
FLASH, SHAKE, GLITCH = [], [], []
def shot(t0, t1, bg, cards=(), shapes=(), texts=(), ecg=(), tr=None, pulse=0.0, bands=()):
    S.append(dict(t0=t0, t1=t1, bg=bg, cards=list(cards), shapes=list(shapes), texts=list(texts),
                  ecg=list(ecg), tr=tr, pulse=pulse, bands=list(bands)))
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

R['02chest'] = ('02', [250, 420, 600, 600])     # her hand on her chest (colour spread)

# ================================================================ TIMELINE (story edit of v1, re-cut so lines meet their panels)
END_HIS = B(73) + 0.25
END_HERS = B(85)
HERS_START = B(8, 1)

# ---- INTRO (instrumental 0-19.1): v1 cold open + title moments kept
shot(0.0, B(1), bgp('grid', WH, SKYL, P=120, v=(0, 0)),
     ecg=[dict(t=0.25, y=560, amp=150, mode='calm', c=SKY2, gc=SKY, th=6, don=1.6, glow=0.6)],
     bands=[band('TOKI DOKI   ときどき   刻どキ   ', 180, 44, SKY2, 0.35, v=-40), band('ときどき   TOKI DOKI   刻どキ   ', 900, 44, SKY2, 0.35, v=40)],
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

# ---- VERSE 1 (19.1-48.6): counted heartbeats -> hand on chest -> living quietly -> he opens the door
E7 = dict(t=B(7), y=930, amp=70, mode='beat', c=RED, gc=PNK, th=5, don=0.6, x0=0, x1=1380)
shot(B(7), B(8), bgp('grid', WH, '#FBE3E7', P=120),
     cards=row(B(7), ['05ecg', '05gp', '05hp'], h=470, cy=450, cx=740), ecg=[E7], tr=('wipe', PNK))
ecg_sfx(E7, B(7, 1), B(8), size=60, every=2)
shot(B(8), B(10), bgp('dots', PNKL, WH, P=64, r=8),
     cards=[card('05scr', mode='frame', w=1000, cx=720, cy=480, ent='zoom', kz=1.15, f=(0.6, 0.6), sc=RED)],
     shapes=hearts(B(8, 2), 6, 15, (RED, ROS), size=(16, 30), area=(80, 80, 1380, 1000)))
lyric(0, '数えられた|{鼓動}のひとつ', 'v', x=1765, y=170, size=100, hs=1.25, hst='redn', anim='wipe', ed=0.4,
      plate='card', pc=WH, psc=PNK, en_w=320,
      deco=('meta', dict(k='seal', x=1418, y=180, r=40, ch='鼓', sub='221,124,617')))
shot(B(10), B(11, 2), bgp('dots', SKY, SKYL, P=64, r=9),
     cards=[card('02chest', mode='frame', h=880, cx=1310, cy=540, rot=3, ent='slide-r', sc=BLU, kz=1.15, f=(0.65, 0.9))],
     shapes=[shp('circle', 1310, 540, 450, CRM, B(10), layer='back', ent='grow', ed=0.45)] + sprinkle(B(10), 8, 10, (WH, CRM, BLU)),
     tr=('iris', 'circle', WH))
lyric(1, 'そっと{胸}に|手をあてた', 'v', x=600, y=190, size=108, hs=1.3, hst='redn', anim='blur', ed=0.45,
      plate='card', pc=CRML, psc=SKY2, en_w=330)
shot(B(11, 2), B(13), bgp('stripes', SKYL, SKY, P=100, r=0.5, v=(1, 1)),
     cards=[card('04a', mode='frame', h=960, cx=540, cy=545, rot=-2, ent='slide-l', kz=1.1, f=(0.55, 0.3), sc=BLU)],
     shapes=[shp('diamond', 1330, 520, 420, SKY2, B(11, 2), layer='back', ent='spin', a=0.35)])
lyric(2, '静かに生きる|それが正しいと', 'h', x=1330, y=360, size=100, w='M', st='ink', anim='rise', ed=0.5,
      plate='soft', pc=WH, pa=0.9, deco=('meta',))
shot(B(13), B(15), bgp('dots', GRY, WH, P=60, r=7),
     cards=[card('04b', mode='mul', bleed=True, kz=1.15, f=(0.85, 0.5))], tr=('wipe', SKY))
lyric(3, 'ずっと自分に|言い聞かせた', 'v', x=470, y=170, size=104, anim='drop', plate='card', pc=WH, psc=LIL, en_w=320)
E15 = dict(t=B(15), y=950, amp=60, mode='calm', c=SKY2, gc=SKYL, th=4, don=0.8, x0=520, x1=1820)
shot(B(15), B(15, 3), bgp('stripes', WH, SKYL, P=90, r=0.5, v=(1, 1)),
     cards=[card('05bench', mode='frame', w=860, cx=W / 2, cy=520, rot=-3, ent='slide-l', sc=SKY2, kz=1.1)],
     ecg=[E15], texts=label(B(15) + 0.1, "THERE'S ABOUT 220 MILLION BEATS LEFT...", W / 2, 140, 28))
shot(B(15, 3), B(17), bgp('dots', SKY, SKYL, P=60, r=8),
     cards=[card('03a', mode='mul', bleed=True, kz=1.08, f=(0.55, 0.4))], tr=('wipe', CRM))
shot(B(17), B(18), bgp('stars', SKYL, WH, P=110, r=14),
     cards=[card('03c', mode='mul', bleed=True, kz=1.22, f=(0.85, 0.35))],
     shapes=hearts(B(17, 2), 5, 9, (ROS, RED), area=(1300, 150, 1750, 450), size=(20, 40), step=0.12),
     tr=('iris', 'circle', CRM))
lyric(4, 'そこへ{君}が|扉を開けて', 'h', x=W / 2, y=620, size=96, sizes=[96, 128], hs=1.15, hst='redn', anim='pop',
      plate='card', pc=WH, psc=CRM, deco=('meta', dict(k='brk', c=RED)))
shot(B(18), B(19), bgp('dots', SKYL, WH, P=56, r=7, v=(-1, 0)),
     cards=[card('06top', mode='frame', w=1500, cy=330, rot=-1, ent='slide-u', sc=NAV)],
     shapes=sprinkle(B(18, 1), 6, 19, (SKY2, NAV), kinds=('plus',), area=(60, 620, 1860, 1000)))
FLASH.append((B(19), 1.0, 0.25, WH)); SHAKE.append((B(19), 18, 5))
shot(B(19), B(20), bgp('dots', PNK, PNKL, P=60, r=9),
     cards=[card('06shout', mode='mul', bleed=True, kz=1.1, f=(0.4, 0.4), shake=(0, 10))], pulse=0.02)
lyric(5, '止まった時間が|動き出した', 'h', x=W / 2, y=630, size=92, sizes=[92, 140], anims=['blur', 'stamp'],
      pt=[LT(5)[0], B(19)], cps=[None, 0.29], plate='card', pc=WH, psc=RED, prot=-1.5)

# ---- CHORUS 1 (49.2-74.4)
FLASH.append((B(20), 1.0, 0.3, WH))
E20 = dict(t=B(20), y=930, amp=110, mode='fast', c=WH, gc=WH, th=7, don=0.5, glow=0.3, x0=0, x1=1700)
shot(B(20), B(22), bgp('hearts', RED, '#EE5F6C', P=120, r=20, v=(0, -2)),
     bands=[band('ドキドキ ', 800, 96, WH, 0.13, v=-70)],
     shapes=[shp('heart', 250, 760, 90, WH, B(20, 2), bp=0.2, a=0.9), shp('heart', 1690, 330, 80, WH, B(21), bp=0.2, a=0.9)],
     ecg=[E20], pulse=0.03)
ecg_sfx(E20, B(20, 1), B(22), size=70, st='whiter')
lyric(6, '{ドキドキ}|して いいんだよ', 'h', x=W / 2, y=210, size=100, hs=2.5, st='white', hst='white', hanim='stamp',
      hbp=0.10, echo='ドキドキ', ecol='outw', enc=WH, ena=0.9, ens=28, dc=WH, cps=[0.29, None, None])
shot(B(22), B(23), bgp('stars', CRM, CRML, P=110, r=15),
     cards=[card('06girl', mode='mul', bleed=True, kz=1.12, f=(0.6, 0.4))], tr=('wipe', PNK))
shot(B(23), B(24), bgp('dots', LILL, WH, P=60, r=8),
     cards=[card('07top', mode='frame', w=1050, cx=1340, cy=560, rot=1, ent='slide-r', sc=LIL)],
     shapes=sprinkle(B(23, 1), 6, 23, (LIL, NAV, WH), kinds=('plus', 'circle'), area=(900, 80, 1860, 1000)))
lyric(7, '私の胸は|{君の色}', 'h', x=560, y=250, size=92, hs=2.5, hcols=['pinkn', 'bluen', 'redn'], hanim='stamp',
      plate='circle', pc=WH, psc=ROS, pr=350, deco=('meta', dict(k='seal', x=880, y=180, r=46, ch='色', c=ROS, st='softr')))
shot(B(24), B(26), bgp('stripes', LILL, PNKL, P=120, r=0.5, v=(1, 1)),
     cards=[card('07mid', mode='mul', bleed=True, kz=1.12, f=(0.75, 0.3))],
     shapes=[shp('burst', 440, 540, 470, CRM, B(24), layer='front', a=0.9, ent='grow', spin=6)] + sprinkle(B(25), 8, 24, (WH, PNK, LIL)),
     tr=('iris', 'diamond', LIL))
lyric(8, '一秒ごとに|{光}が増える', 'v', x=540, y=240, size=100, hs=1.6, hst='whiteb', glow=True, gcol=CRM,
      anim='wipe', hanim='blur', ed=0.4, plate='circle', pc=WH, psc=LIL, pr=380, en_pos=(440, 845), en_w=380)
shot(B(26), B(27), bgp('dots', SKYL, WH, P=64, r=8),
     cards=[card('07br', mode='frame', h=640, cx=1420, rot=2, ent='slide-r', sc=SKY2, kz=1.1)])
shot(B(27), B(28), bgp('plain', GRY),
     cards=[card('07bl', mode='frame', h=760, cx=1420, rot=-2, ent='pop', sc=SLT)])
lyric(9, 'ときどき [痛くて]|ときどき {嬉しい}', 'h', x=540, y=330, size=100, hs=1.25, hst='pinkn', hst2='grey',
      echo='ときどき', anim='pop', plate='card', pc=WH, psc=PNK, prot=-1)
FLASH.append((B(28), 0.6, 0.2, WH))
shot(B(28), B(29), bgp('stars', CRM, '#FFE36E', P=120, r=18, v=(1, 0)),
     cards=[card('08a', mode='frame', h=760, cx=560, cy=640, rot=-3, ent='spin', sc=ROS)],
     shapes=sprinkle(B(28), 10, 28, (ROS, SKY2, WH), area=(1100, 300, 1860, 1000)), pulse=0.02)
shot(B(29), B(30), bgp('dots', MNT, WH, P=60, r=8, v=(-1, 0)),
     cards=[card('08b', mode='frame', h=760, cx=1360, cy=640, rot=3, ent='slide-r', sc=SKY2)],
     shapes=sprinkle(B(29), 8, 29, (CRM, ROS, WH), area=(60, 300, 900, 1000)), pulse=0.015)
shot(B(30), B(31), bgp('dots', SLT, '#8792A8', P=60, r=8),
     cards=[card('08girl', mode='frame', h=780, cx=W / 2, cy=650, rot=0, ent='drop', sc=NAV)])
lyric(10, 'この{空}の下 もっと走りたい', 'h', x=W / 2, y=85, size=92, hs=1.3, st='whiteb', hst='white', anim='slide',
      plate='band', pc=SKY2, pa=0.96, enc=WH, ena=0.95, dc=WH, ppad=22, deco=())
shot(B(31), B(32), bgp('stars', CRM, CRML, P=110, r=15),
     cards=[card('08laugh', mode='frame', h=900, cx=600, rot=-3, ent='pop', sc=ROS)],
     bands=[band('ときどき  ', 1000, 70, ROS, 0.25, v=-60)],
     texts=label(B(31), 'BUT IN REALITY', 1400, 330, 32) + words(B(31, 1), 'SHE_CAN|TELL_A_JOKE', 1400, 540, 110, ent='stamp', sh=ROS),
     shapes=sprinkle(B(31), 10, 31, (ROS, SKY2, WH)), tr=('iris', 'star', CRM), pulse=0.02)

# ---- VERSE 2 (77.9-95.3): hands, his laugh, the blue world, her voice
E32 = dict(t=B(32), y=210, amp=70, mode='fast', c=RED, gc=PNK, th=5, don=0.6, x0=1300, x1=1790)
shot(B(32), B(34), bgp('hearts', PNKL, WH, P=120, r=20, v=(0, -1)),
     cards=[card('12girl', mode='frame', h=980, cx=480, cy=545, rot=-2, ent='slide-l', kz=1.12, f=(0.6, 0.25), sc=ROS),
            card('12hands', mode='frame', h=540, cx=1560, cy=650, rot=6, ent='pop', t_in=B(33) - B(32), sc=RED)],
     ecg=[E32], shapes=hearts(B(33), 8, 49, area=(1320, 400, 1880, 1040), size=(18, 36)), pulse=0.02)
ecg_sfx(E32, B(32, 2), B(34), size=58, dy=200, every=2)
lyric(11, '手をつないだら|{速く}なる音', 'v', x=1160, y=150, size=98, hs=1.15, hst='redn', anim='wipe', ed=0.35,
      plate='card', pc=WH, psc=RED, en_w=300)
_m = [('09m1', CRM, CRML, 'dots'), ('09m2', SKY, SKYL, 'stars'), ('09m3', PNK, PNKL, 'hearts'), ('09m4', MNT, WH, 'dots')]
for i in range(4):
    k, c1, c2, pat = _m[i]
    shot(B(34, i), B(34, i + 1) if i < 3 else B(35), bgp(pat, c1, c2, P=90, r=12),
         cards=[card(k, mode='frame', h=620, cx=1420 + (-60 if i % 2 else 60), cy=560, rot=(-4 if i % 2 else 4), ent='punch', sc=NAV)],
         pulse=0.03)
shot(B(35), B(36), bgp('stripes', CRML, CRM, P=90, r=0.5, v=(1, 1)),
     cards=[card('02hato', mode='norm', h=900, cx=1420, cy=560, rot=4, ent='slide-r')],
     shapes=[shp('circle', 1420, 520, 420, SKY, B(35), layer='back', ent='grow', ed=0.45)] + sprinkle(B(35), 8, 35, (WH, ROS, BLU)))
lyric(12, '怖くないよと|{君}が笑う', 'h', x=560, y=330, size=108, hs=1.2, hst='pinkn', anim='drop',
      plate='card', pc=CRML, psc=ROS, deco=('meta', dict(k='brk', c=ROS)))
shot(B(36), B(37, 2), bgp('plain', WH),
     cards=[card('10bike', mode='mul', bleed=True, kz=1.12, f=(0.4, 0.55), d0=(40, 0), d1=(-40, 0), ent='fade', ed=0.6)],
     shapes=[shp('circle', 300 + 230 * i, 150 + 90 * (i % 3), 40 + 12 * (i % 4), SKYL, B(36) + 0.2 * i, a=0.8, bob=(10, 0.3, i))
             for i in range(7)], tr=('wipe', SKY))
lyric(13, '知らなかった|世界の{青さ}', 'h', x=130, y=140, size=96, sizes=[84, 110], hs=2.3, hst='bluen', align='l',
      anim='rise', hanim='blur', plate='soft', pc=WH, pa=0.88)
shot(B(37, 2), B(39), bgp('pluses', LIL, LILL, P=90, r=16, v=(1, 0)),
     cards=[card('11sing', mode='frame', h=900, cx=1400, rot=3, ent='pop', sc=NAV, kz=1.08)],
     shapes=sprinkle(B(37, 2), 10, 45, (WH, CRM, NAV), kinds=('plus', 'star'), area=(900, 60, 1860, 1020)), pulse=0.015)
shot(B(39), B(40), bgp('dots', CRM, CRML, P=60, r=8),
     cards=[card('11mid', mode='frame', w=1100, cx=1340, cy=600, rot=-1, ent='slide-r', sc=BLU)])
lyric(14, '知らなかった|私の{声}', 'v', x=650, y=170, size=94, hs=2.7, hst='pinkn', ripple=True, hanim='stamp',
      anim='wipe', plate='card', pc=WH, psc=LIL, en_w=360)

# ---- PRE-CHORUS 2 (96.4-105.8)
FLASH.append((B(40), 0.6, 0.25, WH))
shot(B(40), B(42), bgp('hearts', PNK, PNKL, P=110, r=18, v=(0, -1)),
     cards=[card('09fun', mode='mul', bleed=True, kz=1.15, f=(0.75, 0.4))],
     shapes=hearts(B(41), 10, 36, area=(900, 300, 1850, 1000)), pulse=0.02)
lyric(15, '明日の{数}を|忘れるくらい', 'h', x=120, y=150, size=104, hs=1.3, hst='redn', align='l', anim='pop',
      plate='card', pc=CRML, psc=PNK, deco=('meta', dict(k='seal', x=820, y=200, r=44, ch='数', sub='TOMORROWS')))
shot(B(42), B(44), bgp('dots', SKYL, WH, P=64, r=8),
     cards=[card('10girl', mode='frame', h=960, cx=560, rot=-2, ent='slide-l', sc=SKY2, kz=1.08)])
lyric(16, '今日が{眩しくて}|泣きそうだ', 'v', x=1570, y=140, size=100, hst='bluen', glow=True, gcol=CRM, anim='blur',
      ed=0.45, plate='card', pc=WH, psc=SKY2, en_w=330)
shot(B(44), B(45), bgp('stripes', LILL, WH, P=100, r=0.5, v=(1, 1)),
     cards=[card('11top', mode='frame', w=1600, cy=600, rot=1, ent='slide-u', sc=LIL)],
     bands=[band('ドキドキ   ', 160, 90, LIL, 0.5, v=80)])

# ---- CHORUS 2 (108.1-131.5)
FLASH.append((B(45), 1.0, 0.3, WH))
E45 = dict(t=B(45), y=600, amp=200, mode='fast', c=WH, gc=WH, th=7, don=0.45, glow=0.3, x0=0, x1=1150)
shot(B(45), B(46), bgp('hearts', RED, '#EE5F6C', P=120, r=20, v=(0, -2)),
     shapes=[shp('heart', 560, 600, 250, WH, B(45), bp=0.12, ent='pop', a=0.25)], ecg=[E45], pulse=0.03,
     bands=[band('ドキドキ ', 120, 80, WH, 0.12, v=60)])
ecg_sfx(E45, B(45, 1), B(46), size=66, st='whiter')
shot(B(46), B(48), bgp('stars', PNKL, WH, P=110, r=15),
     cards=[card('11br', mode='frame', h=960, cx=560, rot=2, ent='slide-l', sc=ROS, kz=1.06)],
     shapes=sprinkle(B(46), 10, 47, (ROS, SKY2, CRM), area=(1000, 60, 1860, 1020)), pulse=0.015)
lyric(17, '{ドキドキ}|して いいんだよ', 'v', x=1580, y=120, size=100, sizes=[100, 88], hs=2.0, st='white', hst='white',
      hanim='stamp', hbp=0.10, echo='ドキドキ', ecol='outw', cps=[0.29, None, None], en_pos=(1500, 1000), en_w=420,
      enc=NAV, ena=0.9, deco=())
shot(B(48), B(49), bgp('dots', MNT, '#D9F5E8', P=64, r=9),
     cards=[card('08br', mode='frame', h=900, cx=560, rot=3, ent='slide-l', sc=ROS)], pulse=0.02)
lyric(18, '私の胸は|{君の色}', 'h', x=1370, y=250, size=92, hs=2.4, hcols=['redn', 'bluen', 'pinkn'], hanim='spin',
      plate='circle', pc=WH, psc=SKY2, pr=345)
shot(B(49), B(51), bgp('hearts', PNKL, WH, P=120, r=20, v=(0, -1)),
     cards=[card('12girl', mode='frame', h=1000, cx=1400, rot=2, ent='slide-r', kz=1.12, f=(0.6, 0.25), sc=ROS)],
     shapes=[shp('burst', 560, 520, 330, CRM, B(49), layer='front', a=0.95, ent='grow', spin=8)])
lyric(19, '一秒ごとに|{光}が増える', 'h', x=560, y=250, size=96, hs=2.6, hst='whiteb', glow=True, gcol=CRM, hanim='blur',
      anim='pop', deco=('meta', dict(k='seal', x=930, y=220, r=40, ch='秒', c=BLU, st='bluen', sub='01 SEC')))
shot(B(51), B(53), bgp('stripes', CRM, CRML, P=100, r=0.5, v=(1, 1)),
     cards=[card('12bot', mode='frame', w=1150, cx=1270, cy=600, rot=2, ent='slide-r', sc=ROS)])
lyric(20, '{ときどき}|[痛くて]|{ときどき}|嬉しい', 'v', x=600, y=170, size=96, st='ink', hst='inkp', hst2='grey',
      rst=['ink', 'ink', 'ink', 'pinkn'], col_dy=[0, 150, 0, 150], echo='ときどき', anim='drop', plate='card', pc=WH,
      psc=CRM, en_w=540)
FLASH.append((B(53), 1.0, 0.18, '#FF5A68')); SHAKE.append((B(53), 22, 6)); GLITCH.append((B(53), B(53) + 0.5))
shot(B(53), B(55), bgp('grid', GRY, '#C9CFD9', P=120),
     cards=[card('13phone', mode='frame', h=1000, cx=1300, ent='punch', kz=1.45, f=(0.55, 0.5), sc=RED)],
     ecg=[dict(t=B(53), y=930, amp=60, mode='beat', c=RED, gc=PNK, th=5, don=0.5, x0=0, x1=420)])
lyric(21, 'この{空}の下|もっと走りたい', 'v', x=590, y=150, size=100, hs=1.2, hst='bluen', anim='slide',
      plate='card', pc=CRML, psc=RED, en_w=330)

# ---- INSTRUMENTAL (131.5-150.1): v1 manga-line beats kept
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

# ---- BRIDGE (150.1-168.7): his counter, the summer, the hug
shot(B(63), B(64), bgp('plain', '#E3E8F0'),
     cards=[card('13phone', mode='frame', h=880, cx=640, rot=-2, ent='fade', ed=0.6, kz=1.5, f=(0.35, 0.8), sc=SLT)],
     ecg=[dict(t=B(63), y=960, amp=55, mode='calm', c=RED, gc=PNK, th=4, don=1.2, x0=520, x1=1240, a=0.8)])
lyric(22, 'たとえ{鼓動}が|尽きる日が来ても', 'v', x=1610, y=130, size=96, w='L', hw='B', hs=1.2, hst='redn',
      anim='blur', ed=0.6, plate='soft', pc=WH, pa=0.92, en_w=330)
shot(B(64), B(65), bgp('plain', WH),
     cards=[card('15cry', mode='mul', bleed=True, kz=1.2, f=(0.35, 0.4), ent='fade', ed=0.5)],
     ecg=[dict(t=B(64), y=990, amp=50, mode='calm', c=SKY2, gc=SKYL, th=4, don=2.0, a=0.8, x0=520, x1=1300)])
shot(B(65), B(66), bgp('dots', SKYL, WH, P=64, r=6),
     cards=row(B(65), ['15crowd', '15sky'], h=600, cy=640, step=0.58))
shot(B(66), B(67), bgp('grid', WH, PNKL, P=120, v=(3, 0)),
     cards=[card('16top', mode='frame', w=1500, cy=630, rot=-1, ent='slide-u', sc=ROS)],
     ecg=[dict(t=B(66), y=995, amp=55, mode='fast', c=RED, gc=PNK, th=5, don=0.5, x0=520, x1=1880)])
lyric(23, '君がくれた {夏}は消えない', 'h', x=W / 2, y=95, size=92, w='M', hw='B', hs=1.45, hst='redn', anim='rise',
      plate='band', pc=CRML, pa=0.95, ppad=24)
_g = [g for g in LINES[-1]['G'] if g['ch'] == '夏'][0]
LINES[-1]['shapes'].append(shp('burst', _g['x'], _g['y'], _g['sz'] * 0.78, CRM, _g['tin'] - 0.05, ol=4, spin=15, end=LT(23)[1] + 0.1))
FLASH.append((B(67), 1.0, 0.35, WH)); SHAKE.append((B(67), 24, 5))
shot(B(67), B(69), bgp('hearts', PNK, PNKL, P=120, r=20, v=(0, -2)),
     cards=[card('16hug', mode='mul', bleed=True, kz=1.12, f=(0.5, 0.5))],
     shapes=[shp('heart', 380, 590, 300, WH, B(67), layer='front', a=0.94, bp=0.06),
             shp('heart', 1560, 590, 280, WH, B(67, 2), layer='front', a=0.94, bp=0.06)] + hearts(B(67), 16, 67, step=0.12),
     pulse=0.03)
_t24 = LT(24)
lyric(24, 'ひとつ|ひとつ|{刻}んだ想い', 'h', pos=[(380, 520), (1560, 520), (W / 2, 52)], sizes=[118, 112, 100],
      rst=['redn', 'redn', 'white'], hs=1.25, hst='redn', anim='stamp', pt=[_t24[0], B(67, 2), B(68)],
      en_pos=(W / 2, 228), enc=WH, ena=0.9, deco=(),
      shapes=[shp('rect', W / 2, 148, (440, 118), NAV, _t24[0] + 0.0, ent='grow', a=0.9, rot=-1, end=_t24[1] + 0.2)])
shot(B(69), B(70), bgp('dots', RED, '#EE6170', P=64, r=9),
     cards=row(B(69), ['16bl', '16br'], h=600, cy=650, step=0.58, sc=NAV), shapes=hearts(B(69), 10, 69, cols=(WH, PNK)), pulse=0.03)
shot(B(70), B(71), bgp('hearts', PNKL, WH, P=110, r=18, v=(0, -1)),
     cards=[card('16couple', mode='frame', h=760, cx=W / 2, cy=630, ent='zoom', sc=RED, kz=1.08)],
     ecg=[dict(t=B(70), y=630, amp=150, mode='beat', c=RED, gc=PNK, th=7, don=0.6, a=0.9)],
     shapes=hearts(B(70), 12, 70, size=(18, 40)), pulse=0.02)
lyric(25, '{空}に溶けても 続いてく', 'h', x=W / 2, y=95, size=96, w='M', hw='B', hs=1.3, hst='bluen', anim='blur',
      ed=0.5, exit='melt', plate='band', pc=WH, pa=0.9, ppad=24)

# ---- DIP (168.7-175.7, instrumental): his last beats (v1)
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

# ---- FINAL CHORUS (175.7-203.5)
FLASH.append((B(74), 1.0, 0.3, WH))
E74 = dict(t=B(74), y=930, amp=80, mode='beat', c=WH, gc=SKY, th=6, don=0.6, x0=520, x1=1780)
shot(B(74), B(75), bgp('dots', SKY, SKYL, P=64, r=9),
     shapes=sprinkle(B(74), 14, 74, (WH, CRM, BLU), area=(60, 60, 760, 860)), ecg=[E74], pulse=0.02,
     bands=[band('ドキドキ ', 120, 90, WH, 0.35, v=-80), band('ドキドキ ', 800, 90, WH, 0.35, v=80)])
E75 = dict(E74, t=B(75), don=0.01)
shot(B(75), B(76), bgp('stars', CRM, CRML, P=110, r=15),
     cards=[card('18sing', mode='frame', h=900, cx=470, rot=-3, ent='slide-l', sc=BLU)], ecg=[E75], pulse=0.02)
ecg_sfx(E74, B(74, 1), B(76), size=66, st='redn')
lyric(26, '{ドキドキ}|して いいんだよ', 'h', x=1310, y=250, size=100, hs=2.5, st='white', hst='white', hanim='stamp',
      hbp=0.10, echo='ドキドキ', ecol='outw', cps=[0.29, None, None], plate=None, enc=NAV, ena=0.9)
shot(B(76), B(77), bgp('dots', PNKL, WH, P=64, r=8, v=(-1, 0)),
     cards=[card('18conc', mode='frame', w=1150, cx=1250, cy=430, rot=1, ent='slide-r', sc=ROS)], pulse=0.02)
shot(B(77), B(78), bgp('stripes', SKYL, WH, P=100, r=0.5, v=(1, 1)),
     cards=[card('18mid', mode='frame', w=1200, cx=1240, cy=520, ent='slide-u', sc=BLU)], pulse=0.02)
lyric(27, '私の胸は|{君の色}', 'v', x=600, y=160, size=100, hs=2.0, hcols=['pinkn', 'bluen', 'redn'], hanim='stamp',
      plate='card', pc=WH, psc=PNK, en_w=380)
_fb = [('02hatsu', 'norm', SKY, SKYL, 'dots'), ('06shout', 'mul', PNK, PNKL, 'dots'), ('08laugh', 'mul', CRM, CRML, 'stars'),
       ('09fun', 'mul', PNK, PNKL, 'hearts'), ('10girl', 'frame', SKYL, WH, 'stars'), ('11br', 'frame', CRM, CRML, 'dots'),
       ('12hands', 'frame', RED, '#EE6170', 'dots'), ('07mid', 'mul', LILL, WH, 'dots')]
for i, (k, md, c1, c2, pat) in enumerate(_fb):
    t0_, t1_ = B(78 + i // 2, 2 * (i % 2)), (B(78 + (i + 1) // 2, 2 * ((i + 1) % 2)))
    if md == 'mul': cd = card(k, mode='mul', bleed=True, kz=1.1, f=(0.5, 0.35))
    else: cd = card(k, mode=md, h=680, cx=W / 2 + (330 if i % 2 else -330), cy=390, rot=(3 if i % 2 else -3), ent='punch', sc=NAV)
    shot(t0_, t1_, bgp(pat, c1, c2, P=100, r=14), cards=[cd], pulse=0.03,
         shapes=sprinkle(t0_, 5, 100 + i, (WH, CRM, ROS), kinds=('plus', 'heart'), area=(60, 60, W - 60, 640)))
lyric(28, '一秒ごとに {光}が増える', 'h', x=1190, y=745, size=92, hs=1.8, hst='whiteb', glow=True, gcol=CRM, hanim='blur',
      plate='card', pc=WH, psc=SKY2, prot=-1, ppad=26)
lyric(29, 'ときどき [痛くて] ときどき {嬉しい}', 'h', x=1190, y=790, size=82, hs=1.25, hst='pinkn', hst2='grey',
      echo='ときどき', plate='card', pc=WH, psc=PNK, prot=1, ppad=26)
shot(B(82), B(84), bgp('dots', SKYL, WH, P=70, r=8),
     cards=[card('18face', mode='frame', h=960, cx=1010, ent='zoom', kz=1.12, f=(0.5, 0.4), sc=BLU)],
     shapes=sprinkle(B(82), 12, 85, (WH, CRM, SKY2), kinds=('plus', 'star')), pulse=0.02)
shot(B(84), B(86), bgp('hearts', PNKL, WH, P=110, r=18, v=(0, -1)),
     cards=[card('16couple', mode='frame', h=860, cx=1010, rot=-2, ent='fade', ed=0.5, sc=RED, kz=1.06)],
     shapes=hearts(B(84), 12, 84, area=(700, 60, 1300, 1000), size=(16, 34)), pulse=0.02)
_t30 = LT(30)
lyric(30, '{ありがとう}|[恋]をさせて|くれて', 'v', pos=[(430, 120), (1610, 170), (1460, 170)], sizes=[150, 108, 108],
      hs=1.0, hs2=1.3, hst2='pinkn', rst=['redn', 'ink', 'ink'], hst='redn', anims=['rise', 'blur', 'blur'], ed=0.5,
      cps=[0.2, None, None], en_pos=(1530, 880), en_w=460, deco=())
for g in LINES[-1]['G']:
    if g['ch'] == '恋': g['glow'] = True
# ---- OUTRO (203.5-end)
shot(B(86), B(87), bgp('plain', WH),
     cards=[card('18mid', mode='frame', w=1300, cx=W / 2, cy=420, ent='fade', ed=0.5, sc=SLT)],
     texts=label(B(86, 1), 'FINALLY, HER PARENTS TOOK CARE OF HER', W / 2, 760, 30) +
           label(B(86, 2), 'UNTIL HER LAST BREATH.', W / 2, 830, 30, st='tag'))
FLASH.append((B(87), 1.0, 0.4, WH))
DOKI = [LT(31)[0], LT(32)[0]]
shot(B(87), B(88), bgp('plain', WH),
     cards=[card('01face', mode='norm', bleed=True, kz=1.15, f=(0.62, 0.55))],
     ecg=[dict(t=B(87), y=960, amp=90, events=DOKI, c=RED, gc=PNK, th=6, don=0.8, x0=0, x1=1500)],
     shapes=sprinkle(B(87), 14, 87, (WH, CRM, PNK), kinds=('plus', 'star', 'heart'), size=(14, 34)))
shot(B(88), DUR + 0.1, bgp('grid', WH, SKYL, P=120, v=(1, 0)),
     cards=[card('02logo', mode='norm', w=1000, cx=900, cy=420, ent='pop', s1=1.03)],
     texts=label(B(88, 2), 'BY KOMI NAOSHI', 900, 690, 30),
     ecg=[dict(t=B(88), y=900, amp=110, events=DOKI, c=BLU, gc=SKY, th=6, don=1.0, x0=160, x1=1700)],
     bands=[band('ときどき   刻どキ   TOKI DOKI   ', 1020, 34, SKY2, 0.35, v=-30)],
     shapes=sprinkle(B(88, 1), 12, 88, (SKY2, CRM, PNK)), tr=('iris', 'heart', PNK))
lyric(31, 'ドキ[…]', 'h', x=1590, y=650, size=130, hs2=0.6, hst2='red', st='redn', anim='stamp', deco=(), pt=[DOKI[0]], cps=0.12, ens=24)
lyric(32, 'ドキ[…]', 'h', x=1640, y=560, size=120, hs2=0.6, hst2='red', st='redn', anim='stamp', deco=(), pt=[DOKI[1]], cps=0.12, ens=24)

# ---------------------------------------------------------------- HUD: beats left
V_HERS = 221124617
def hers_left(t): return V_HERS - beats_between(HERS_START, t)
V_HERS2 = hers_left(B(53))
HUDS = [
    dict(t0=HERS_START, t1=B(53), name='HATSU TAKAGI', f=hers_left),
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
    for b in sh['bands']: draw_band(rgb, b, t)
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
    rgb = np.clip(rgb, 0, 1).astype(np.float32)
    hud(rgb, t)
    lyrics_layer(rgb, t)          # Japanese lyric layer: above shots/transitions, so lines carry across cuts
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
STILLS = 'stills_lyrics'
def _sheet(thumbs, d, name):
    while len(thumbs) % 6: thumbs.append(np.zeros_like(thumbs[0]))
    rows = [np.hstack(thumbs[i:i + 6]) for i in range(0, len(thumbs), 6)]
    for j in range(0, len(rows), 6):
        cv2.imwrite(os.path.join(d, f'{name}_{j // 6:02d}.jpg'), np.vstack(rows[j:j + 6]), [cv2.IMWRITE_JPEG_QUALITY, 85])

def _still(tt):
    return tt, frame(int(round(tt * FPS)))

def stills(times, d=STILLS, full=True):
    from multiprocessing import Pool
    d = os.path.join(HERE, d); os.makedirs(d, exist_ok=True)
    thumbs = {}
    with Pool(max(1, min(len(times), os.cpu_count() - 1))) as pool:
        for tt, fr in pool.imap(_still, times):
            if full: cv2.imwrite(os.path.join(d, f'{tt:06.2f}.jpg'), fr[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 90])
            th = cv2.resize(fr[..., ::-1], (480, 270), interpolation=cv2.INTER_AREA)
            cv2.putText(th, f'{tt:.2f}', (6, 22), 0, 0.6, (0, 0, 255), 2); thumbs[tt] = th
    _sheet([thumbs[t] for t in times], d, 'contact')

def sheet(step):
    from multiprocessing import Pool
    times = [round(x, 2) for x in np.arange(0.5, DUR, step)]
    d = os.path.join(HERE, STILLS); os.makedirs(d, exist_ok=True)
    thumbs = {}
    with Pool(max(1, os.cpu_count() - 1)) as pool:
        for tt, fr in pool.imap(_still, times):
            th = cv2.resize(fr[..., ::-1], (384, 216), interpolation=cv2.INTER_AREA)
            cv2.putText(th, f'{tt:.1f}', (6, 20), 0, 0.55, (0, 0, 255), 2); thumbs[tt] = th
    _sheet([thumbs[t] for t in times], d, 'sheet')

def video():
    import imageio_ffmpeg
    from multiprocessing import Pool
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmpv = os.path.join(HERE, '_video_lyrics.mp4'); tmpa = os.path.join(HERE, '_audio_lyrics.m4a')
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
    elif sys.argv[1] == 'lines':      # one still per lyric line, at 75% through it (+ its end)
        ts = sorted(set(round(L['t0'] + 0.75 * (L['t1'] - L['t0']), 2) for L in LINES))
        stills(ts, full=len(sys.argv) > 2)
    elif sys.argv[1] == 'sheet': sheet(float(sys.argv[2]) if len(sys.argv) > 2 else 2.0)
    else: video()
