"""Gokurakugai Sanbandoori no Ken - v2 action Short (24 s, 1080x1920, 30 fps, 160 BPM).

Builds on render.py's helpers (pages, grades, text sprites) with:
  * page-tour camera: the camera flies over a whole manga page from panel to panel on the beat (sub-frame motion blur),
  * transitions: ink-bleed (red rim), katana slash, glass shatter, liquid morph, zoom-through, glitch slices, halftone,
  * impacts: radial zoom blur, B/W ink frames, chromatic split, shake, sparks, anamorphic flares,
  * per-letter slam text with a light sweep (glint), name cards, the 3-minute stopwatch over the fight.
Usage:  python render_v2.py stills 1,5,12   |   python render_v2.py video   (needs music_v2.wav from music_v2.py)
"""
import os, sys, math, subprocess
import numpy as np, cv2
import render as R
from render import (clamp, eout, ein, eio, eback, lerp, hexc, page, warp_page, sprite, blit, slab, grade,
                    speed_lines, RED, RED2, GOLD, INK, PAPER, JPB, IMP, MONO, LAB, W, H, FPS)

HERE = R.HERE; ROOT = R.ROOT
BPM = 160.0; BEAT = 60 / BPM
def b(n): return n * BEAT
DUR = 24.0; N = int(DUR * FPS)
ASP = W / H

# ---------------------------------------------------------------- noise fields (fixed, for ink / morph)
_rng = np.random.default_rng(21)
def smooth_noise(scale, seed):
    r = np.random.default_rng(seed)
    n = r.random((H // scale + 3, W // scale + 3)).astype(np.float32)
    return cv2.resize(n, (W + 3 * scale, H + 3 * scale), interpolation=cv2.INTER_CUBIC)[:H, :W]
INKF = 0.55 * smooth_noise(96, 1) + 0.3 * smooth_noise(32, 2) + 0.15 * smooth_noise(8, 3)
INKF = (INKF - INKF.min()) / (INKF.max() - INKF.min())
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
RAD = np.sqrt((_xx - W / 2) ** 2 + (_yy - H / 2) ** 2) / math.hypot(W / 2, H / 2)
DX = (smooth_noise(160, 4) - 0.5) * 2; DY = (smooth_noise(160, 5) - 0.5) * 2
SPC = 54.0
DGRID = np.sqrt(((_xx % SPC) - SPC / 2) ** 2 + ((_yy % SPC) - SPC / 2) ** 2).astype(np.float32)
DIAG = ((_xx + _yy) / (W + H)).astype(np.float32)

# shatter shards (triangulated random points)
def make_shards(seed=7, nx=5, ny=8):
    r = np.random.default_rng(seed)
    pts = [(0, 0), (W - 1, 0), (W - 1, H - 1), (0, H - 1)]
    for gx in range(nx):
        for gy in range(ny):
            pts.append((min(W - 1, max(0, (gx + 0.5 + r.uniform(-.4, .4)) * W / nx)),
                        min(H - 1, max(0, (gy + 0.5 + r.uniform(-.4, .4)) * H / ny))))
    sd = cv2.Subdiv2D((0, 0, W + 1, H + 1))
    for p in pts: sd.insert((float(p[0]), float(p[1])))
    out = []
    for t in sd.getTriangleList():
        tri = np.float32(t).reshape(3, 2)
        if (tri < -1).any() or (tri[:, 0] > W + 1).any() or (tri[:, 1] > H + 1).any(): continue
        c = tri.mean(0); d = c - [W / 2, H * 0.45]; d /= (np.linalg.norm(d) + 1e-3)
        out.append((tri, c, d, r.uniform(-1, 1), r.uniform(0.6, 1.5), r.uniform(0, 0.25)))
    return out
SHARDS = make_shards()

# ---------------------------------------------------------------- camera helpers
def cam(cx, cy, h): return [cx - h * ASP / 2, cy - h / 2, h * ASP, h]
def view(n, rect, border=0.03):
    M, _ = R.view_matrix(rect, W, H)
    up, s = page(n); Ms = M.copy(); Ms[:, :2] /= s
    img = cv2.warpAffine(up, Ms, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=border)
    return img, M

# ---------------------------------------------------------------- shots
S = []
def shot(t0, t1, **kw): S.append(dict(t0=t0, t1=t1, **kw))
IMPACT, SHAKE, FLASH, FLARE, SPARK, ZOOMB, TEXT = [], [], [], [], [], [], []

def T(t, s, x, y, size, fnt=JPB, end=None, ent='slam', **kw):
    TEXT.append(dict(t=t, s=s, x=x, y=y, size=size, fnt=fnt, end=end, ent=ent, **kw))

def hit(t, frames=2, mode='ink', shake=26, zoom=True):
    IMPACT.append((t, frames, mode)); SHAKE.append((t, shake, 8))
    if zoom: ZOOMB.append(t)

# 0-8  page 02: ink reveal, the camera reads the page - street, fist, armlet, the punch
shot(b(0), b(8), kind='tour', p='02', grade='night', tr=('ink',), keys=[
    (b(0), cam(480, 700, 1705)), (b(2), cam(720, 260, 600)), (b(4), cam(250, 585, 380)),
    (b(5), cam(560, 760, 400)), (b(6), cam(200, 1130, 560)), (b(7), cam(230, 1150, 470))])
T(b(0) + 0.15, '極楽街', 120, 330, 118, vertical=True, ent='stagger', end=b(2), fill=(0.93, 0.95, 0.97))
T(b(6) + 0.02, 'ゴッ!!', 700, 1500, 240, ent='stagger', end=b(8), stroke=0.07, rot=8)
for k in (4, 5, 6): hit(b(k), 2, 'ink' if k != 5 else 'inv', 22)
SHAKE.append((b(6), 34, 6)); FLASH.append((b(6), 0.5, 0.08, RED2))
# 8-16  the gate - katana slash in, tilt up, title
shot(b(8), b(16), kind='bleed', p='03', r=[290, 270, 340, 604], r1=[230, 0, 500, 889], grade='cool', tr=('slash',))
T(b(9), '極楽街', W / 2, 1530, 270, ent='stagger', end=b(16), slabc=RED, glint=b(11), track=0.15)
T(b(10), 'EXTRATERRITORIAL DISTRICT  //  MUGEN GROUP', W / 2, 1715, 34, fnt=LAB, ent='type', end=b(16), trk=0.15)
FLASH.append((b(8), 0.9, 0.1, PAPER)); SHAKE.append((b(8), 20, 9))
# 16-24  Tao - the gate shatters into her
shot(b(16), b(24), kind='tour', p='08', grade='red', tr=('shatter',), name=('TAO', 'タオ', 'THE BOSS'), keys=[
    (b(16), cam(500, 1080, 760)), (b(20), cam(500, 1060, 660)), (b(23), cam(500, 1050, 600))])
T(b(20), 'HURRY UP AND', W / 2, 1560, 96, fnt=IMP, end=b(24), slant=-8, ent='stagger', slabc=INK)
T(b(21), 'HAND OVER THE MONEY.', W / 2, 1680, 96, fnt=IMP, end=b(24), slant=-8, ent='stagger', fill=RED2)
hit(b(16), 3, 'ink', 30)
# 24-32  Al - liquid morph from Tao's face
shot(b(24), b(32), kind='tour', p='17', grade='cool', tr=('morph',), name=('AL', 'アル', 'PHYSICAL LABOUR'), keys=[
    (b(24), cam(320, 740, 700)), (b(28), cam(310, 730, 640)), (b(31), cam(300, 720, 600))])
T(b(28), "I WON'T EVEN NEED", W / 2, 1560, 96, fnt=IMP, end=b(32), slant=-8, ent='stagger', slabc=INK)
T(b(29), 'THREE MINUTES!!', W / 2, 1690, 128, fnt=IMP, end=b(32), slant=-8, ent='stagger', fill=RED2, glint=b(30))
# 32-36  troubleshooters - zoom through into the split
shot(b(32), b(36), kind='split', tr=('zoom',),
     a=dict(p='15', r=[420, 0, 420, 747], r1=[450, 20, 380, 676], grade='cool'),
     c=dict(p='15', r=[930, 80, 520, 925], r1=[960, 120, 470, 836], grade='red'))
T(b(32) + 0.1, 'WASSUP,', 760, 300, 124, fnt=IMP, end=b(36), slant=-8, ent='stagger')
T(b(33), '万事解決', 250, 1420, 150, end=b(36), slabc=RED, ent='stagger', glint=b(34))
T(b(34), 'GOKURAKU DISTRICT', 300, 1565, 58, fnt=IMP, end=b(36), ent='type', slant=-8)
T(b(34) + 0.3, 'TROUBLESHOOTERS', 300, 1635, 58, fnt=IMP, end=b(36), ent='type', slant=-8, fill=RED2)
# 36-52  THE FIGHT
FIGHT0, FIGHT1 = b(36), b(52)
R.FIGHT0, R.FIGHT1, R.BEAT = FIGHT0, FIGHT1, BEAT
shot(b(36), b(42), kind='tour', p='16', grade='cool', tr=('glitch',), lines=True, keys=[
    (b(36), cam(270, 150, 420)), (b(38), cam(700, 450, 440)), (b(40), cam(480, 980, 840)), (b(41), cam(470, 1020, 700))])
T(b(36) + 0.05, 'ドッ', 820, 1400, 240, end=b(38), stroke=0.07, rot=-8, ent='stagger')
T(b(40) + 0.05, 'ドッ!!', 300, 520, 240, end=b(42), stroke=0.07, rot=6, ent='stagger', fill=RED2)
shot(b(42), b(46), kind='tour', p='18', grade='red', tr=('whip',), lines=True, keys=[
    (b(42), cam(660, 330, 660)), (b(44), cam(660, 1080, 640)), (b(45), cam(660, 1110, 560))])
T(b(42) + 0.05, 'ガッ!!', 320, 1450, 260, end=b(46), stroke=0.07, rot=-6, ent='stagger')
shot(b(46), b(52), kind='tour', p='19', grade='cool', tr=('slash',), keys=[
    (b(46), cam(370, 547, 1095)), (b(48), cam(1280, 330, 660)), (b(50), cam(1060, 945, 340)), (b(51), cam(1070, 945, 300))])
T(b(48) + 0.02, 'ドン', 820, 1000, 220, end=b(50), stroke=0.07, rot=10, ent='stagger')
T(b(49) + 0.02, 'ドン', 820, 1260, 220, end=b(50), stroke=0.07, rot=-6, ent='stagger')
for k in (36, 38, 40, 42, 44, 46, 50): hit(b(k), 2 if k % 4 else 3, 'ink' if k % 4 == 0 else 'inv', 26)
for k in (37, 41, 45, 47): IMPACT.append((b(k + 0.5), 1, 'inv'))
SPARK += [(b(48), 600, 400, 1), (b(49), 600, 400, 2)]; FLARE += [(b(48), 600, 400), (b(49), 600, 400)]
FLASH += [(b(48), 0.55, 0.06, GOLD), (b(49), 0.55, 0.06, GOLD)]; SHAKE += [(b(48), 26, 9), (b(49), 26, 9)]
# 52-56  freeze - we do as we please (halftone in)
shot(b(52), b(56), kind='bleed', p='20', r=[752, 0, 616, 1095], r1=[790, 30, 560, 996], grade='cool', tr=('halftone',),
     patches=[[848, 548, 290, 255, 'circle']])
T(b(53), 'WE DO AS', 470, 1080, 124, fnt=IMP, end=b(56), slant=-8, ent='stagger')
T(b(54), 'WE PLEASE.', 470, 1215, 124, fnt=IMP, end=b(56), slant=-8, ent='stagger', fill=RED2, glint=b(55))
FLASH.append((b(52), 1.0, 0.16, PAPER))
# 56-64  colour bleeds in - the cover + title
shot(b(56), DUR + 0.1, kind='bleed', p='01', r=[480, 150, 420, 747], r1=[60, 0, 899, 1400], grade=None, tr=('ink', 'red'),
     ent='zoomout', patches=[[600, 1170, 330, 175]])
T(b(57), '', 640, 1640, 10, fnt=IMP, ent='bar')
T(b(58), 'GOKURAKUGAI', 660, 1560, 96, fnt=IMP, ent='stagger', slant=-6, glint=b(60))
T(b(58) + 0.35, 'SANBANDOORI NO KEN', 660, 1652, 66, fnt=IMP, ent='stagger', slant=-6, fill=RED2)
T(b(59), 'YUTO SANO', 660, 1732, 34, fnt=LAB, ent='type', trk=0.3)
hit(b(56), 2, 'ink', 30); FLASH.append((b(56), 0.7, 0.2, RED2)); FLARE.append((b(56) + 0.05, W / 2, 1600))

# ---------------------------------------------------------------- shot rendering
MOVE = 0.20       # camera move time between tour keys
def tour_rect(sh, t):
    ks = sh['keys']
    rect = ks[0][1]; moving = 0.0
    for (ta, ra), (tb, rb) in zip(ks, ks[1:]):
        if t >= tb:
            rect = rb; continue
        u = clamp((t - tb + MOVE) / MOVE)                     # move happens just before the key lands
        if u > 0: rect = R.lerp_rect(ra, rb, eio(u)); moving = math.sin(math.pi * u)
        else:                                                  # slow push while holding
            hold = clamp((t - ta) / max(tb - MOVE - ta, 1e-3))
            x, y, w, h = ra; k = 1 + 0.06 * eio(hold); rect = [x + w * (1 - 1 / k) / 2, y + h * (1 - 1 / k) / 2, w / k, h / k]
        break
    else:
        hold = clamp((t - ks[-1][0]) / max(sh['t1'] - ks[-1][0], 1e-3))
        x, y, w, h = ks[-1][1]; k = 1 + 0.06 * eio(hold); rect = [x + w * (1 - 1 / k) / 2, y + h * (1 - 1 / k) / 2, w / k, h / k]
    return rect, moving

def render_tour(sh, t):
    rect, mv = tour_rect(sh, t)
    if mv > 0.05:                                              # sub-frame motion blur
        acc = 0; n = 5
        for i in range(n):
            rr, _ = tour_rect(sh, t - (i / n) * (1 / FPS) * 1.6)
            acc = acc + view(sh['p'], rr)[0]
        img = acc / n
    else:
        img = view(sh['p'], rect)[0]
    return img

def render_bleed(spec, t, t0, t1, ent='none'):
    u = clamp((t - t0) / (t1 - t0))
    r0, r1 = spec['r'], spec.get('r1', spec['r'])
    rect = R.lerp_rect(r0, r1, eout(u) if ent == 'zoomout' else eio(u))
    img, M = view(spec['p'], rect)
    for pt in spec.get('patches', []):
        px, py, pw, ph = pt[:4]
        p0 = M @ np.float32([px, py, 1]); p1 = M @ np.float32([px + pw, py + ph, 1])
        m = np.zeros((H, W), np.uint8)
        if len(pt) > 4: cv2.ellipse(m, (int((p0[0] + p1[0]) / 2), int((p0[1] + p1[1]) / 2)),
                                    (int((p1[0] - p0[0]) / 2), int((p1[1] - p0[1]) / 2)), 0, 0, 360, 255, -1, cv2.LINE_AA)
        else: cv2.rectangle(m, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), 255, -1)
        m = m.astype(np.float32) / 255; m = m[..., None] if img.ndim == 3 else m
        img = img * (1 - m) + 0.01 * m
    return img

def render_shot(sh, t):
    k = sh['kind']; lt = t - sh['t0']
    if k == 'tour': rgb = grade(render_tour(sh, t), sh['grade'])
    elif k == 'bleed': rgb = grade(render_bleed(sh, t, sh['t0'], sh['t1'], sh.get('ent', 'none')), sh['grade'])
    elif k == 'split':
        A = grade(render_bleed(sh['a'], t, sh['t0'], sh['t1']), sh['a']['grade'])
        C = grade(render_bleed(sh['c'], t, sh['t0'], sh['t1']), sh['c']['grade'])
        e = eout(lt / 0.3); off = (1 - e) * W
        A = cv2.warpAffine(A, np.float32([[1, 0, -off], [0, 1, 0]]), (W, H), borderMode=cv2.BORDER_REPLICATE)
        C = cv2.warpAffine(C, np.float32([[1, 0, off], [0, 1, 0]]), (W, H), borderMode=cv2.BORDER_REPLICATE)
        line = _yy - (1150 - 0.9 * (_xx - W / 2)); m = np.clip(line / 2 + 0.5, 0, 1)[..., None]
        rgb = A * (1 - m) + C * m; rgb = np.where((np.abs(line) < 9 * e)[..., None], RED, rgb)
    rgb = np.ascontiguousarray(rgb, np.float32)
    if sh.get('lines'): speed_lines(rgb, t, seed=int(sh['p']))
    if sh.get('name'): R.name_card(rgb, dict(t0=sh['t0'], name=sh['name']), t)
    return rgb

# ---------------------------------------------------------------- transitions (cur = new shot, prev = old shot)
D_TR = {'ink': 0.55, 'slash': 0.32, 'shatter': 0.55, 'morph': 0.45, 'zoom': 0.3, 'glitch': 0.22, 'whip': 0.18,
        'halftone': 0.4}
def transition(cur, prev, tr, u):
    k = tr[0]
    if k == 'ink':
        th = eio(u) * 1.25
        f = INKF * 0.75 + RAD * 0.45
        m = np.clip((th - f) / 0.03, 0, 1)[..., None]
        rim = (np.clip((th - f + 0.05) / 0.03, 0, 1)[..., None] - m)
        out = prev * (1 - m) + cur * m
        return out * (1 - rim) + RED * rim
    if k == 'slash':                       # diagonal cut, halves of the old frame slide apart, white blade line
        e = eout(u); d = (_xx * 0.42 - _yy * 0.9 + 600) / 100.0
        side = (d > 0)[..., None]
        off = e * 700
        A = cv2.warpAffine(prev, np.float32([[1, 0, off * 0.42], [0, 1, -off * 0.9]]), (W, H), borderValue=(0, 0, 0))
        B = cv2.warpAffine(prev, np.float32([[1, 0, -off * 0.42], [0, 1, off * 0.9]]), (W, H), borderValue=(0, 0, 0))
        moved = np.where(side, A, B)
        dm = (_xx * 0.42 - _yy * 0.9 + 600)
        gap = (np.abs(dm) < off * 0.99)[..., None]
        out = np.where(gap, cur, moved)
        blade = np.exp(-(dm / (3 + 30 * (1 - u))) ** 2)[..., None] * (1 - u)
        return out + blade * 1.5
    if k == 'shatter':
        out = cur.copy()
        for tri, c, d, rot, spd, dl in SHARDS:
            p = clamp((u - dl) / (1 - dl)) ** 1.5
            if p >= 1: continue
            off = d * p * 900 * spd + np.float32([0, p * p * 600])
            M = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), rot * 70 * p, 1 + 0.25 * p)
            M[:, 2] += off
            q = np.float32(tri) @ M[:, :2].T + M[:, 2]
            bx, by = int(max(0, q[:, 0].min() - 2)), int(max(0, q[:, 1].min() - 2))
            bx1, by1 = int(min(W, q[:, 0].max() + 2)), int(min(H, q[:, 1].max() + 2))
            if bx1 - bx < 2 or by1 - by < 2: continue
            M2 = M.copy(); M2[:, 2] -= (bx, by)
            piece = cv2.warpAffine(prev, M2, (bx1 - bx, by1 - by), flags=cv2.INTER_LINEAR)
            m = np.zeros((by1 - by, bx1 - bx), np.float32)
            cv2.fillConvexPoly(m, np.int32((q - [bx, by]) * 16), 1.0, cv2.LINE_AA, 4)
            m = m[..., None]
            edge = cv2.morphologyEx(m[..., 0], cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))[..., None]
            reg = out[by:by1, bx:bx1]
            reg[:] = reg * (1 - m) + (piece * (1 - 0.3 * p) + 0.6 * edge) * m
        return out
    if k == 'morph':
        a = 140 * math.sin(math.pi * u)
        mx1, my1 = _xx + DX * a * u, _yy + DY * a * u
        mx2, my2 = _xx - DX * a * (1 - u), _yy - DY * a * (1 - u)
        A = cv2.remap(prev, mx1, my1, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        B = cv2.remap(cur, mx2, my2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        e = eio(u); return A * (1 - e) + B * e
    if k == 'zoom':
        A = cv2.warpAffine(prev, cv2.getRotationMatrix2D((W / 2, H / 2), 0, 1 + 2.5 * ein(u)), (W, H), borderMode=cv2.BORDER_REFLECT)
        A = cv2.GaussianBlur(A, (0, 0), 1 + 18 * u)
        B = cv2.warpAffine(cur, cv2.getRotationMatrix2D((W / 2, H / 2), 0, lerp(1.4, 1.0, eout(u))), (W, H), borderMode=cv2.BORDER_REFLECT)
        e = eout(u); return A * (1 - e) + B * e
    if k == 'glitch':
        r = np.random.default_rng(int(u * 37)); out = (prev if u < 0.45 else cur).copy()
        for _ in range(14):
            y0 = int(r.integers(0, H - 40)); hh = int(r.integers(12, 140)); src = cur if r.random() < u else prev
            out[y0:y0 + hh] = np.roll(src[y0:y0 + hh], int(r.integers(-160, 160)), 1)
        out[..., 0] = np.roll(out[..., 0], 12, 1); out[..., 2] = np.roll(out[..., 2], -12, 1)
        return out
    if k == 'whip':
        e = eio(u); dy = e * H
        A = cv2.warpAffine(prev, np.float32([[1, 0, 0], [0, 1, -dy]]), (W, H), borderMode=cv2.BORDER_REFLECT)
        B = cv2.warpAffine(cur, np.float32([[1, 0, 0], [0, 1, H - dy]]), (W, H), borderMode=cv2.BORDER_REFLECT)
        out = np.where((_yy < H - dy)[..., None], A, B)
        kb = int(1 + 140 * math.sin(math.pi * u)) * 2 + 1
        return cv2.blur(out, (1, kb))
    if k == 'halftone':
        r = np.clip(u * 1.7 - DIAG * 0.7, 0, 1) * SPC * 0.78
        m = np.clip((r - DGRID) / 1.5 + 0.5, 0, 1)[..., None]
        rim = np.clip((r + 6 - DGRID) / 1.5 + 0.5, 0, 1)[..., None] - m
        return (prev * (1 - rim) + RED * rim) * (1 - m) + cur * m
    return cur

# ---------------------------------------------------------------- text
def text_layout(it):
    s, size = it['s'], it['size']
    kw = dict(fill=it.get('fill', (1, 1, 1)), stroke=it.get('stroke', 0.0), sfill=(0.02, 0.02, 0.03), slant=it.get('slant', 0.0))
    f = R.font(it['fnt'], size); trk = it.get('track', it.get('trk', 0.0)) * size
    items = []
    if it.get('vertical'):
        for i, ch in enumerate(s): items.append((ch, it['x'], it['y'] + i * size * 1.05))
    else:
        adv = [f.getlength(ch) + trk for ch in s]; tw = sum(adv) - trk
        x = it['x'] - tw / 2
        for ch, a in zip(s, adv): items.append((ch, x + a / 2, it['y'])); x += a
    return items, kw

def draw_texts(rgb, t):
    for it in TEXT:
        lt = t - it['t']
        if lt < 0 or (it['end'] is not None and t > it['end']): continue
        fade = clamp((it['end'] - t) / 0.08) if it['end'] is not None else 1.0
        if it['ent'] == 'bar':
            slab(rgb, it['x'], it['y'], 980, 300, INK, skew=-6, a=0.88, u=lt / 0.3); continue
        if it['ent'] == 'type':
            n = int(len(it['s']) * clamp(lt / (len(it['s']) * 0.028)))
            if n <= 0: continue
            kw = dict(fill=it.get('fill', (1, 1, 1)), trk=it.get('trk', 0.0), slant=it.get('slant', 0.0))
            full = sprite(it['s'], it['fnt'], it['size'], **kw); spr = sprite(it['s'][:n], it['fnt'], it['size'], **kw)
            blit(rgb, spr, it['x'] - full.shape[1] / 2 + spr.shape[1] / 2, it['y'], a=fade); continue
        items, kw = text_layout(it)
        if it.get('slabc') is not None:
            f = R.font(it['fnt'], it['size'])
            tw = (items[-1][1] - items[0][1]) + it['size'] if not it.get('vertical') else it['size']
            slab(rgb, it['x'], it['y'] + it['size'] * 0.08, tw + 110, it['size'] * 1.05, it['slabc'], u=lt / 0.16, a=fade)
        stg = 0.045 if it['ent'] == 'stagger' else 0.0
        for i, (ch, x, y) in enumerate(items):
            lc = lt - i * stg
            if lc < 0: continue
            e = eout(lc / 0.14)
            spr = sprite(ch, it['fnt'], it['size'], **kw)
            blit(rgb, spr, x, y + (1 - e) * -40, lerp(2.3, 1, e), it.get('rot', 0), clamp(lc / 0.05) * fade, 7 * (1 - e))
        g = it.get('glint')
        if g is not None and 0 <= t - g < 0.5:                 # light sweep across the word
            u = (t - g) / 0.5
            xs = [x for _, x, _ in items]; x0, x1 = min(xs) - it['size'], max(xs) + it['size']
            px = lerp(x0, x1, eio(u)); y0, y1 = int(it['y'] - it['size'] * 0.7), int(it['y'] + it['size'] * 0.7)
            y0, y1 = max(0, y0), min(H, y1); xa, xb = int(max(0, x0)), int(min(W, x1))
            if xb > xa and y1 > y0:
                yy, xx = np.mgrid[y0:y1, xa:xb].astype(np.float32)
                band = np.exp(-(((xx - px) + (yy - it['y']) * 0.5) / 26) ** 2)
                reg = rgb[y0:y1, xa:xb]
                bright = (reg.mean(2) > 0.55).astype(np.float32)        # only on the light letters
                reg += (band * bright * 0.9)[..., None]

# ---------------------------------------------------------------- frame
def shot_at(t):
    for i, s in enumerate(S):
        if s['t0'] <= t < s['t1']: return i
    return len(S) - 1

def stopwatch(rgb, t):
    R.FIGHT0, R.FIGHT1 = FIGHT0, FIGHT1
    R.BEAT = BEAT
    R.stopwatch(rgb, t)

def frame(fi):
    t = fi / FPS
    si = shot_at(t); sh = S[si]
    rgb = render_shot(sh, t)
    tr = sh.get('tr')
    if tr:
        d = D_TR[tr[0]]
        if t < sh['t0'] + d:
            u = (t - sh['t0']) / d
            prev = render_shot(S[si - 1], t) if si > 0 else np.full((H, W, 3), 0.0, np.float32)
            rgb = transition(rgb, prev, tr, u)
    draw_texts(rgb, t)
    stopwatch(rgb, t)
    R.SPARK[:] = SPARK; R.FLARE[:] = FLARE
    R.sparks(rgb, t); R.flares(rgb, t)
    for ts in ZOOMB:                                          # radial zoom blur on hits
        if ts <= t < ts + 0.2:
            k = 1 - (t - ts) / 0.2; acc = rgb.copy(); n = 5
            for i in range(1, n):
                z = 1 + 0.035 * k * i
                acc += cv2.warpAffine(rgb, cv2.getRotationMatrix2D((W / 2, H * 0.45), 0, z), (W, H), borderMode=cv2.BORDER_REFLECT)
            rgb = acc / n; break
    for ts, nfr, mode in IMPACT:
        if ts <= t < ts + nfr / FPS:
            l = rgb.mean(2, keepdims=True); bw = (l > 0.42).astype(np.float32)
            rgb = np.repeat(1 - bw, 3, 2) if mode == 'inv' else bw * PAPER + (1 - bw) * INK
            break
    ox = oy = ca = 0.0
    for ts, amp, dc in SHAKE:
        if ts <= t < ts + 1.0:
            k = amp * math.exp(-(t - ts) * dc); ox += k * math.sin(t * 83); oy += k * math.cos(t * 61); ca += k * 0.5
    if abs(ox) + abs(oy) > 0.3:
        rgb = cv2.warpAffine(rgb, np.float32([[1.03, 0, ox - W * 0.015], [0, 1.03, oy - H * 0.015]]), (W, H),
                             borderMode=cv2.BORDER_REFLECT)
    if ca > 1:
        d = int(ca); rgb = rgb.copy(); rgb[..., 0] = np.roll(rgb[..., 0], d, 1); rgb[..., 2] = np.roll(rgb[..., 2], -d, 1)
    for ts, pk, dc, col in FLASH:
        if ts <= t < ts + 1.0:
            f = pk * math.exp(-(t - ts) / dc)
            if f > 0.004: rgb = rgb + (col - rgb) * min(f, 1)
    rgb = rgb * R.VIG + R.GRAIN[si % 4]
    rgb = rgb * clamp((DUR - t) / 0.3)
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)

# ---------------------------------------------------------------- main
def stills(times):
    d = os.path.join(HERE, 'stills_v2'); os.makedirs(d, exist_ok=True)
    th = []
    for tt in times:
        fr = frame(int(round(tt * FPS)))[..., ::-1]
        cv2.imwrite(os.path.join(d, f'{tt:06.2f}.png'), fr)
        s_ = cv2.resize(fr, (270, 480), interpolation=cv2.INTER_AREA)
        cv2.putText(s_, f'{tt:.2f}', (6, 22), 0, 0.6, (0, 255, 255), 2); th.append(s_)
    while len(th) % 8: th.append(np.zeros_like(th[0]))
    cv2.imwrite(os.path.join(d, 'contact.jpg'), np.vstack([np.hstack(th[i:i + 8]) for i in range(0, len(th), 8)]))

def video():
    import imageio_ffmpeg
    from multiprocessing import Pool
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmp = os.path.join(HERE, '_v2_video.mp4'); out = os.path.join(ROOT, 'gokurakugai-short-v2.mp4')
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p',
                          '-movflags', '+faststart', tmp], stdin=subprocess.PIPE)
    with Pool(max(1, os.cpu_count() - 1)) as pool:
        for i, fr in enumerate(pool.imap(frame, range(N), chunksize=4)):
            p.stdin.write(fr.tobytes())
            if i % 150 == 0: print(f'frame {i}/{N}', flush=True)
    p.stdin.close(); p.wait()
    subprocess.run([ff, '-y', '-v', 'error', '-i', tmp, '-i', os.path.join(HERE, 'music_v2.wav'), '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.0:LRA=9,aresample=48000', '-c:a', 'aac', '-b:a', '192k',
                    '-t', f'{DUR:.3f}', '-movflags', '+faststart', out], check=True)
    os.remove(tmp); print('wrote', out)

if __name__ == '__main__':
    if sys.argv[1] == 'stills': stills([float(x) for x in sys.argv[2].split(',')])
    else: video()
