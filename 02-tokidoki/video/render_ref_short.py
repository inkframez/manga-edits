"""Toki Doki - Short in the style of the romance reference MMVs (Frimizen), chorus 1 (song 49.20-69.20 s), 1080x1920.

Style rules taken frame-by-frame from video-samples-references/romance:
  * B/W manga only - colour comes from the backgrounds. Cut-outs have NO outline/shadow (the line art is the edge).
  * characters are BIG (busts/faces cropped by the frame edge), often two facing each other from opposite sides.
  * characters barely move: a fast 0.2 s slide-in, then a slow drift; the whole frame slowly pushes in.
  * flat pastel + small pattern (dots/stars/hearts/diamonds), big flat blocks (diagonal bands, rects, star, circle),
    small thin-outline decorations (rings, triangles, squares, asterisks).
  * words appear one by one beside the face; text cards with coloured bands; oval bubble; black label box.
  * transitions: white diamond ring, concentric circles, diagonal pattern wedge, heart iris, white flash, duotone strobe.
Usage:  python render_ref_short.py stills 50,52   |   python render_ref_short.py video -> ../tokidoki-short-ref.mp4
"""
import os, sys, math, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw
import render as E
from render import B, clamp, eout, ein, eio, eback, lerp, hexc, bgp

T0 = B(20); LEN = 20.0; T1 = T0 + LEN
W, H = 1080, 1920
FPS = E.FPS
E.W, E.H = W, H
OUT = os.path.join(E.ROOT, 'tokidoki-short-ref.mp4')
CUTD = os.path.join(E.ROOT, 'cutouts')
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
XX, YY = _xx, _yy
CX, CY = W / 2, H / 2

# reference palette (+ Toki Doki sky blue)
LIME, LIME2, PINK, PINK2, LAV, LAV2, YEL, YEL2 = '#C9EF7C', '#DDF6A8', '#F67EA2', '#FBB3C8', '#D7A3F0', '#E6C6F7', '#FFF27E', '#FFF8B8'
BLUE, BLUE2, WHT, GRY, INK = '#A9DDF6', '#D3EEFB', '#FFFFFF', '#BDBDBD', '#1B1B1B'
JP, ROUND = E.JP, E.ROUND
E.STY.update({
    'pk': dict(font=JP, fill=PINK, sh=WHT, so=0.05),
    'wt': dict(font=JP, fill=WHT, sh=GRY, so=0.06),
    'wtp': dict(font=JP, fill=WHT, sh=PINK, so=0.07),
    'wtd': dict(font=JP, fill=WHT, stroke=INK, sw=0.035),
    'lv': dict(font=JP, fill=LAV, sh=WHT, so=0.05),
    'sp': dict(font=JP, fill=WHT, stroke=INK, sw=0.06, trk=0.25),
})

# ---------------------------------------------------------------- assets
CUT = {}
def cut(name):
    if name not in CUT:
        a = np.asarray(Image.open(os.path.join(CUTD, name + '.png')), np.float32) / 255
        a[..., :3] = np.clip((a[..., :3] - 0.04) / 0.9, 0, 1)                   # crisp ink / paper
        pm = a.copy(); pm[..., :3] *= pm[..., 3:4]
        CUT[name] = pm
    return CUT[name]

OUTL = {}
def outline_sprite(s, size, col=WHT, sw=0.05):
    key = (s, size, col, sw)
    if key not in OUTL:
        f = E.font(JP, size); w = int(f.getlength(s) + size * 0.4); h = int(size * 1.5)
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
        c = tuple(int(v * 255) for v in hexc(col)) + (255,)
        d.text((size * 0.2, size * 0.1), s, font=f, fill=c, stroke_width=int(size * sw), stroke_fill=c)
        d.text((size * 0.2, size * 0.1), s, font=f, fill=(0, 0, 0, 0))
        a = np.asarray(img, np.float32) / 255; a[..., :3] *= a[..., 3:4]
        OUTL[key] = a
    return OUTL[key]

def warp_into(rgb, src, M, alpha=1.0):
    h, w = src.shape[:2]
    cs = np.float32([[0, 0], [w, 0], [w, h], [0, h]]) @ M[:, :2].T + M[:, 2]
    bx, by, bx1, by1 = E.bbox_of(cs, 2)
    if bx1 - bx < 2 or by1 - by < 2: return
    M2 = M.copy(); M2[:, 2] -= (bx, by)
    o = cv2.warpAffine(src, M2.astype(np.float32), (bx1 - bx, by1 - by), flags=cv2.INTER_CUBIC,
                       borderMode=cv2.BORDER_CONSTANT)
    reg = rgb[by:by1, bx:bx1]; al = o[..., 3:4] * alpha
    reg[:] = reg * (1 - al) + o[..., :3] * alpha

def slide(d, e, dist=900):
    if d is None: return 0.0, 0.0
    vx, vy = E.DIRS[d]; k = dist * (1 - eout(e)); return -vx * k, -vy * k

# ---------------------------------------------------------------- elements
def draw_cut(rgb, c, t, sh):
    lt = t - sh['t0'] - c.get('dt', 0)
    if lt < 0: return
    u = clamp((t - sh['t0']) / (sh['t1'] - sh['t0']))
    pm = cut(c['img']); h, w = pm.shape[:2]
    k = c['h'] / h * lerp(1.0, c.get('zs', 1.04), u)
    dx, dy = slide(c.get('ent'), clamp(lt / c.get('ed', 0.2)), c.get('dist', 900))
    dr = c.get('drift', (0, 0)); dx += dr[0] * u; dy += dr[1] * u
    fl = -1 if c.get('flip') else 1
    # anchor: bottom-centre of the cut-out at (x, y)
    M = np.float64([[fl * k, 0, c['x'] + dx - fl * k * w / 2], [0, k, c['y'] + dy - k * h]])
    warp_into(rgb, pm, M)

def draw_pan(rgb, c, t, sh):
    """rectangular manga panel, no border (Kiss You style)."""
    lt = t - sh['t0'] - c.get('dt', 0)
    if lt < 0: return
    u = clamp((t - sh['t0']) / (sh['t1'] - sh['t0']))
    p, (x, y, w, h) = E.R[c['key']]
    up, s = E.page(p)
    z = lerp(1, c.get('kz', 1.06), u); fx, fy = c.get('f', (0.5, 0.5))
    w2, h2 = w / z, h / z; x, y = x + (w - w2) * fx, y + (h - h2) * fy; w, h = w2, h2
    fw = c['w']; fh = c.get('hh', fw * h / w)
    if 'hh' in c:   # crop to requested box aspect
        asp = fw / fh
        if w / h > asp: nw = h * asp; x += (w - nw) / 2; w = nw
        else: nh = w / asp; y += (h - nh) / 2; h = nh
    dx, dy = slide(c.get('ent'), clamp(lt / c.get('ed', 0.2)), c.get('dist', 1000))
    dr = c.get('drift', (0, 0)); dx += dr[0] * u; dy += dr[1] * u
    cx, cy = c['cx'] + dx, c['cy'] + dy
    src = np.float32([[x * s, y * s], [(x + w) * s, y * s], [(x + w) * s, (y + h) * s]])
    dst = np.float32([[cx - fw / 2, cy - fh / 2], [cx + fw / 2, cy - fh / 2], [cx + fw / 2, cy + fh / 2]])
    M = cv2.getAffineTransform(src, dst)
    bx, by, bx1, by1 = int(max(0, cx - fw / 2)), int(max(0, cy - fh / 2)), int(min(W, cx + fw / 2)), int(min(H, cy + fh / 2))
    if bx1 - bx < 2 or by1 - by < 2: return
    M[:, 2] -= (bx, by)
    o = cv2.warpAffine(up, M, (bx1 - bx, by1 - by), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    v = o.astype(np.float32) / 255
    v = np.clip((v - 0.04) / 0.9, 0, 1)
    rgb[by:by1, bx:bx1] = v[..., None] if v.ndim == 2 else v

def draw_outl(rgb, it, t):
    if t < it['t']: return
    e = clamp((t - it['t']) / 0.22)
    E.blit(rgb, outline_sprite(it['s'], it['size'], it.get('c', WHT), it.get('sw', 0.05)), it['x'], it['y'], lerp(0.3, 1, eback(e)), it.get('rot', 0), clamp(e * 3))

def deco(t, n, seed, cols=(WHT,), area=(40, 120, 1040, 1800), size=(16, 40)):
    """small thin-outline decorations: rings, triangles, squares, asterisks."""
    r = np.random.default_rng(seed); out = []
    for i in range(n):
        k = str(r.choice(['ring', 'tri', 'square', 'plus', 'circle']))
        d = dict(k=('circle' if k == 'ring' else k), x=float(r.uniform(area[0], area[2])), y=float(r.uniform(area[1], area[3])),
                 s=float(r.uniform(*size)), c=str(r.choice(cols)), t=t + 0.05 * i, rot=float(r.uniform(0, 90)),
                 spin=float(r.uniform(-40, 40)), bob=(float(r.uniform(4, 10)), 0.4, float(r.uniform(0, 6))), layer='front')
        if k in ('ring', 'tri', 'square'): d['ring'] = 4
        if k == 'circle': d['s'] *= 0.4
        out.append(d)
    return out

def shp(k, x, y, s, c, t, **kw): d = dict(k=k, x=x, y=y, s=s, c=c, t=t, layer='back'); d.update(kw); return d
def band(y, c, t, rot=-28, th=170, ent='slide-l', **kw): return shp('rect', W / 2, y, (1500, th / 2), c, t, rot=rot, ent=ent, ed=0.22, **kw)
def word(s, x, y, size, st, t, **kw): d = dict(s=s, st=st, size=size, x=x, y=y, t=t, ent='pop', ed=0.22); d.update(kw); return d

S = []
def shot(t0, t1, bg, els=(), tr=None, duo=None, strobe=False):
    S.append(dict(t0=t0, t1=t1, bg=bg, els=list(els), tr=tr, duo=duo, strobe=strobe))
def C(img, x, y, h, **kw): d = dict(type='cut', img=img, x=x, y=y, h=h); d.update(kw); return d
def P(key, cx, cy, w, **kw): d = dict(type='pan', key=key, cx=cx, cy=cy, w=w); d.update(kw); return d
def SH(**kw): d = dict(type='shape'); d.update(kw); return d
def T(**kw): d = dict(type='text'); d.update(kw); return d
def O(**kw): d = dict(type='outl'); d.update(kw); return d
def EL(type_, d): d = dict(d); d['type'] = type_; return d

E.R.update({'08laughV': ('08', [0, 1065, 440, 335]), '14cryV': ('14', [200, 880, 759, 520]),
            '06girlV': ('06', [349, 960, 610, 440]), '10girlV': ('10', [0, 0, 265, 430]), '15skyV': ('15', [450, 990, 509, 410]),
            '12handsV': ('12', [600, 0, 359, 470])})

# ================================================================ timeline (bar = 4 beats = 2.35 s)
b = lambda j, k=0: B(j, k)
# -- line 1: ドキドキして いいんだよ
shot(b(20), b(20, 2), bgp('dots', LIME, LIME2, P=44, r=7, v=(0, -1)), els=[
    SH(**band(1250, PINK, b(20), th=420)),
    C('hatsu_smile', 640, 2110, 2150, ent='r', drift=(-30, 0)),
    T(**word('ドキ', 230, 430, 230, 'wtp', b(20) + 0.02)), T(**word('ドキ', 300, 690, 230, 'wtp', b(20, 1))),
    *[EL('shape', d) for d in deco(b(20), 7, 1)]],
    tr=('flash',))
shot(b(20, 2), b(21), bgp('stars', BLUE, BLUE2, P=60, r=10, v=(1, 0)), els=[
    SH(**shp('rect', 150, 670, (110, 330), YEL, b(20, 2), rot=0, ent='slide-l', ed=0.2)),
    C('hato_smile', 780, 1990, 1960, ent='r', drift=(-25, 0)),
    T(**word('し', 150, 560, 200, 'pk', b(20, 3))), T(**word('て', 150, 780, 200, 'pk', b(20, 3) + 0.12)), *[EL('shape', d) for d in deco(b(20, 2), 6, 2)]])
shot(b(21), b(21, 2), bgp('diamonds', LAV, LAV2, P=56, r=10), els=[
    SH(**shp('rect', 330, 560, (260, 330), BLUE, b(21), rot=0, ent='slide-u', ed=0.2)),
    SH(**shp('rect', 760, 1460, (300, 260), YEL, b(21), ent='slide-d', ed=0.2)),
    P('08laughV', 600, 1050, 900, ent='r', drift=(-20, 0)),
    P('06girlV', 420, 470, 640, hh=470, ent='l', dt=0.29, drift=(15, 0)),
    SH(**shp('circle', 300, 1520, (210, 150), BLUE, b(21, 1), ent='pop', ed=0.25, layer='front')),
    T(**word('いいんだよ', 300, 1500, 62, 'wt', b(21, 1) + 0.05)),
    SH(**shp('heart', 300, 1585, 22, PINK, b(21, 1) + 0.1, ent='pop', layer='front'))],
    tr=('diamond',))
shot(b(21, 2), b(22), bgp('plain', WHT), els=[
    SH(**shp('rect', W / 2, 760, (W, 230), YEL, b(21, 2), ent='slide-r', ed=0.18)),
    SH(**shp('rect', W / 2, 1180, (W, 230), LIME, b(21, 2) + 0.06, ent='slide-l', ed=0.18)),
    T(**word('いいん', W / 2, 760, 280, 'wt', b(21, 2) + 0.03)), T(**word('だよ', W / 2, 1180, 280, 'wt', b(21, 3)))],
    tr=('flash',))
# -- line 2: 私の胸は 君の色
shot(b(22), b(22, 2), bgp('stars', LIME, LIME2, P=60, r=10, v=(0, -1)), els=[
    SH(**shp('star', 560, 1150, 700, WHT, b(22), rot=8, spin=6, ent='pop', ed=0.3)),
    SH(**shp('tri', 900, 420, 520, PINK, b(22), rot=10, ent='slide-r', ed=0.2)),
    C('couple', 330, 1500, 900, ent='l', drift=(10, 0), zs=1.02),
    C('hatsu_stand', 790, 2060, 1650, ent='r', drift=(-20, 0)),
    *[T(**word(ch, 170, 300 + i * 165, 150, 'pk', b(22) + 0.1 + i * 0.14)) for i, ch in enumerate('私の胸は')],
    *[EL('shape', d) for d in deco(b(22), 6, 3, cols=(WHT, PINK))]],
    tr=('circles', (PINK2, PINK)))
shot(b(22, 2), b(23, 2), bgp('plain', PINK), els=[
    P('14cryV', W / 2, 960, 1080, hh=1920, kz=1.12, f=(0.45, 0.45)),
    SH(**shp('heart', W / 2, 980, 600, '#FFE3EE', b(22, 2), a=0.5, ent='grow', ed=0.4, layer='front', bp=0.06)),
    T(**word('君 の 色', W / 2, 980, 110, 'sp', b(22, 2) + 0.05))],
    duo=('#8E1F5A', '#FFD3E2'), strobe=True, tr=('heart',))
shot(b(23, 2), b(24), bgp('hearts', PINK, PINK2, P=56, r=10, v=(0, -2)), els=[
    SH(**shp('circle', W / 2, 980, 470, WHT, b(23, 2), ent='grow', ed=0.25)),
    C('couple', W / 2, 2000, 1560, ent='u', dist=600, drift=(0, -20)),
    O(s='色', x=W / 2, y=380, size=300, t=b(23, 2) + 0.1),
    *[EL('shape', d) for d in deco(b(23, 2), 7, 4)]],
    tr=('wedge', ('hearts', PINK, PINK2, 56, 10)))
# -- line 3: 一秒ごとに 光が増える
shot(b(24), b(24, 2), bgp('stars', YEL, YEL2, P=60, r=10, v=(1, 0)), els=[
    SH(**shp('burst', 540, 1200, 820, WHT, b(24), spin=8, ent='pop', ed=0.3)),
    SH(**shp('tri', 120, 300, 520, PINK, b(24), rot=-20, ent='slide-l', ed=0.2)),
    C('hato_shout', 600, 2060, 2150, ent='u', dist=500, drift=(0, -15)),
    T(**word('一秒', 760, 1450, 200, 'pk', b(24) + 0.03)), T(**word('ごとに', 760, 1680, 160, 'wtd', b(24, 1))),
    *[EL('shape', d) for d in deco(b(24), 6, 5, cols=(WHT, PINK))]],
    tr=('diamond',))
for i, (k, col, col2) in enumerate([('10girlV', BLUE, BLUE2), ('12handsV', LAV, LAV2)]):
    E_ = [P(k, W / 2, 1000, 900, hh=1280, kz=1.08, ent=('l' if i == 0 else 'r'), ed=0.15),
          SH(**shp('rect', W / 2, 1720, (W, 120), col, b(24, 2 + i), ent='slide-r', ed=0.15))]
    shot(b(24, 2 + i), b(24, 3 + i), bgp('dots', col, col2, P=44, r=7), els=E_, tr=('flash',))
shot(b(25), b(25, 2), bgp('dots', BLUE, BLUE2, P=44, r=7, v=(0, -1)), els=[
    SH(**shp('circle', 900, 520, 330, YEL, b(25), ent='grow', ed=0.25)),
    SH(**band(1500, LAV, b(25), rot=24, th=300, ent='slide-r')),
    C('hato_smile', 300, 1990, 1960, ent='l', drift=(25, 0)),
    O(s='光', x=900, y=430, size=300, t=b(25) + 0.05, c=PINK, sw=0.07),
    T(**word('が', 930, 700, 140, 'wtd', b(25, 1))),
    *[T(**word(ch, 930, 870 + i * 150, 140, 'pk', b(25, 1) + 0.15 + i * 0.1)) for i, ch in enumerate('増える')],
    *[EL('shape', d) for d in deco(b(25), 6, 6)]],
    tr=('circles', (YEL2, YEL)))
# -- line 4: ときどき 痛くて ときどき 嬉しい
shot(b(25, 2), b(26), bgp('diamonds', LAV, LAV2, P=56, r=10), els=[
    P('14cryV', W / 2, 960, 1080, hh=1920, kz=1.06, f=(0.4, 0.5), ent='u', ed=0.18),
    SH(**shp('rect', 190, 540, (150, 420), LAV, b(25, 2), ent='slide-l', ed=0.18, layer='front')),
    *[T(**word(ch, 190, 260 + i * 140, 130, 'wt', b(25, 2) + 0.05 + i * 0.1)) for i, ch in enumerate('ときどき')]],
    tr=('diamond',))
shot(b(26), b(26, 2), bgp('plain', LAV2), els=[
    P('14cryV', W / 2, 960, 1080, hh=1920, kz=1.06, f=(0.4, 0.5)),
    T(**word('痛くて', 540, 1650, 170, 'sp', b(26) + 0.05))],
    duo=('#43306E', '#E9DDFB'), strobe=True)
shot(b(26, 2), b(27, 2), bgp('hearts', PINK, PINK2, P=56, r=10, v=(0, -1)), els=[
    C('hato_smile', 330, 1090, 1380, ent='l', drift=(20, 0)),
    C('hatsu_smile', 720, 2110, 1180, ent='r', drift=(-20, 0)),
    SH(**band(1010, LIME, b(26, 2), rot=-14, th=300, ent='slide-l')),
    SH(**band(1010, YEL, b(26, 2) + 0.05, rot=-14, th=70, ent='slide-r')),
    T(**word('ときどき', 600, 990, 130, 'pk', b(26, 2) + 0.08, rot=-14)),
    SH(**shp('circle', 920, 420, (150, 120), BLUE, b(27), ent='pop', ed=0.25)),
    T(**word('嬉しい', 920, 410, 70, 'wt', b(27) + 0.05)),
    SH(**shp('heart', 920, 478, 18, PINK, b(27) + 0.15, ent='pop')),
    *[EL('shape', d) for d in deco(b(26, 2), 8, 7, cols=(WHT, PINK))]],
    tr=('wedge', ('hearts', PINK, PINK2, 56, 10)))
shot(b(27, 2), b(28), bgp('dots', LIME, LIME2, P=44, r=7), els=[
    P('12handsV', W / 2, 960, 1080, hh=1920, kz=1.1, ent='r', ed=0.18),
    SH(**shp('heart', 300, 380, 150, PINK, b(27, 2) + 0.1, ent='pop', layer='front', bp=0.1)),
    SH(**shp('heart', 800, 1500, 110, PINK2, b(27, 3), ent='pop', layer='front', bp=0.1))],
    tr=('flash',))
# -- line 5: この空の下
shot(b(28), T1 + 0.1, bgp('dots', BLUE, BLUE2, P=44, r=7, v=(0, -1)), els=[
    P('15skyV', W / 2, 760, 1080, hh=1520, kz=1.08, f=(0.6, 0.5)),
    C('couple', 300, 2010, 1250, ent='l', drift=(15, 0)),
    T(**word('この', 760, 260, 110, 'wtd', b(28) + 0.02)),
    O(s='空', x=760, y=520, size=300, t=b(28) + 0.05, c=PINK, sw=0.07),
    T(**word('の下', 760, 790, 110, 'wtd', b(28, 1))),
    *[EL('shape', d) for d in deco(b(28), 6, 8)]],
    tr=('circles', (WHT, BLUE2)))

# ---------------------------------------------------------------- rendering
def render_shot(sh, t):
    rgb = E.background(sh, t)
    for el in sh['els']:                       # painter's order
        ty = el['type']
        if ty == 'shape': E.draw_shape(rgb, el, t)
        elif ty == 'cut': draw_cut(rgb, el, t, sh)
        elif ty == 'pan': draw_pan(rgb, el, t, sh)
        elif ty == 'text': E.draw_text(rgb, el, t)
        elif ty == 'outl': draw_outl(rgb, el, t)
    if sh['duo']:
        lum = rgb.mean(2, keepdims=True); d0, d1 = hexc(sh['duo'][0]), hexc(sh['duo'][1])
        rgb = d0 + (d1 - d0) * lum
        if sh['strobe']:
            k = 1 - 2 * abs(((t - sh['t0']) / (E.nb(sh['t0'], 1) - sh['t0'])) % 1 - 0.5)   # 0..1..0 per beat
            rgb = rgb * (1 - 0.35 * k) + 0.35 * k * (d0 + (d1 - d0) * 0.55)
    # slow push-in of the whole composition
    u = clamp((t - sh['t0']) / (sh['t1'] - sh['t0']))
    z = 1 + 0.025 * u
    if z > 1.001:
        rgb = cv2.warpAffine(rgb, cv2.getRotationMatrix2D((CX, CY), 0, z), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return rgb

def diamond_mask(r):
    return (np.abs(XX - CX) + np.abs(YY - CY) < r).astype(np.float32)

D_TR = {'diamond': 0.36, 'circles': 0.42, 'wedge': 0.38, 'heart': 0.4, 'flash': 0.0}
DIAGMAX = W + H
def transition(cur, prev, tr, u):
    kind = tr[0]
    if kind == 'diamond':        # white diamond ring grows, next shot appears in its hole
        ro = (CX + CY + 380) * eio(u); ri = ro - 380
        mo, mi = diamond_mask(ro)[..., None], diamond_mask(ri)[..., None]
        return prev * (1 - mo) + mo * (hexc(WHT) * (1 - mi) + cur * mi)
    if kind == 'circles':        # concentric discs: colour, colour, next shot
        rr = np.sqrt((XX - CX) ** 2 + (YY - CY) ** 2)[..., None]; R = math.hypot(CX, CY) * 1.02
        out = prev
        for j, col in enumerate(tr[1] + ('shot',)):
            r = R * eout(clamp((u - j * 0.18) / 0.6)); m = np.clip(r - rr + 0.5, 0, 1)
            out = out * (1 - m) + (cur if col == 'shot' else hexc(col)) * m
        return out
    if kind == 'wedge':          # diagonal pattern band sweeps across
        spec = tr[1]; can = E.pat_canvas(spec)[:H, :W]
        edge = (XX * 0.8 + YY * 0.45) / (W * 0.8 + H * 0.45)
        p = lerp(-0.35, 1.35, eio(u))
        new = (edge < p - 0.25)[..., None]; patm = ((edge >= p - 0.25) & (edge < p + 0.05))[..., None]
        return np.where(new, cur, np.where(patm, can, prev))
    if kind == 'heart':
        m = np.zeros((H, W), np.uint8); r = 2.0 * math.hypot(CX, CY) * ein(u)
        if r > 1:
            pts = E.shape_pts('heart', r) + np.float32([CX, CY])
            cv2.fillPoly(m, [np.int32(pts * 16)], 255, cv2.LINE_AA, 4)
        m = (m.astype(np.float32) / 255)[..., None]
        return prev * (1 - m) + cur * m
    return cur

def shot_at(t):
    for i, s in enumerate(S):
        if s['t0'] <= t < s['t1']: return i
    return len(S) - 1

def frame(fi):
    t = fi / FPS
    si = shot_at(t); sh = S[si]
    rgb = render_shot(sh, t)
    if sh['tr'] and si > 0:
        d = D_TR.get(sh['tr'][0], 0)
        if d and t < sh['t0'] + d:
            rgb = transition(rgb, render_shot(S[si - 1], t), sh['tr'], (t - sh['t0']) / d)
        if sh['tr'][0] == 'flash':
            f = math.exp(-(t - sh['t0']) / 0.12)
            rgb = rgb + (1 - rgb) * f * 0.9
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)

# ---------------------------------------------------------------- render
F0 = int(round(T0 * FPS)); NF = int(round(LEN * FPS))

def stills(times):
    d = os.path.join(E.HERE, 'stills_ref'); os.makedirs(d, exist_ok=True)
    th = []
    for tt in times:
        fr = frame(int(round(tt * FPS)))[..., ::-1]
        cv2.imwrite(os.path.join(d, f'{tt:06.2f}.png'), fr)
        s_ = cv2.resize(fr, (270, 480), interpolation=cv2.INTER_AREA)
        cv2.putText(s_, f'{tt - T0:.2f}s', (6, 22), 0, 0.6, (0, 0, 255), 2); th.append(s_)
    while len(th) % 8: th.append(np.zeros_like(th[0]))
    cv2.imwrite(os.path.join(d, 'contact.jpg'), np.vstack([np.hstack(th[i:i + 8]) for i in range(0, len(th), 8)]))

def video():
    import imageio_ffmpeg
    from multiprocessing import Pool
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmpv = os.path.join(E.HERE, '_video_ref.mp4'); tmpa = os.path.join(E.HERE, '_audio_ref.m4a')
    subprocess.run([ff, '-y', '-v', 'error', '-ss', f'{T0:.3f}', '-t', f'{LEN:.3f}', '-i', E.SONG,
                    '-af', f'afade=t=in:d=0.08,afade=t=out:st={LEN - 0.6:.2f}:d=0.6,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000',
                    '-c:a', 'aac', '-b:a', '192k', tmpa], check=True)
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                          '-tune', 'animation', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmpv], stdin=subprocess.PIPE)
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
    else: video()
