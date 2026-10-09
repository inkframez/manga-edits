"""Steel Ball Run ch.18 v2 - 30 s action Short, 1080x1920, 30 fps, cut to music_v2.py (172 BPM, 86 beats).

Rebuilt from scratch (render.py only lends page loading and type sprites). Everything is timed in beats, and the
camera bumps on every kick / snare listed in beatmap_v2.json (written by music_v2.py), so picture and score share
one beat map.
  * beat-cut camera tours with sub-frame motion blur, 3D-tilted panel cards over JoJo burst backgrounds
  * morph transitions: liquid morph, steel-ball swirl (vortex), magnetic pull (into a point / out of it),
    plus slash, zoom-through, shatter, glitch, whip, halftone
  * Japanese type: menacing ゴゴゴ / ドドド kana, vertical kanji (三時間, 磁石, 鉄球, 爆発 ...), katakana name cards
  * magnetism: iron-filing particle streams + dipole field lines + a MAGNETIC FORCE meter; golden spiral on the ball
  * hits: ink / inverted frames, radial zoom blur, shake, chromatic split, flashes, bloom
  * ending: sepia freeze + TO BE CONTINUED arrow (tape stop in the score)
Story (ch.18): Mountain Tim keeps pace for three hours; the Boom Boom magnetism makes the three of them pull on
each other; Gyro's steel ball and the iron in the rock scraps drag Tim off his horse; Tim's Stand, Oh! Lonesome Me,
splits his body along his rope so they can't meet.
Usage:  python music_v2.py            (score + beatmap)
        python render_v2.py stills 0.5,3,9.5     |   python render_v2.py video   -> ../mountain-tim-short-v2.mp4
"""
import os, sys, math, json, subprocess
import numpy as np, cv2
import render as R
from render import clamp, eout, ein, eio, lerp, hexc, page, sprite, blit, slab, W, H, FPS, INK, PAPER, PINK

HERE = R.HERE; ROOT = R.ROOT
BM = json.load(open(os.path.join(HERE, 'beatmap_v2.json')))
BEAT = BM['beat']; DUR = BM['dur']; N = int(round(DUR * FPS))
def b(n): return n * BEAT
ASP = W / H
IMP, LAB, MONO, JP = 'impact.ttf', 'bahnschrift.ttf', 'consolab.ttf', 'YuGothB.ttc'
GOLD, MAG, VIOLET, TEAL = hexc('#FFC83D'), hexc('#FF2E88'), hexc('#A24BFF'), hexc('#29E3C1')
LIME, RED, CREAM, DEEP = hexc('#7CFF4F'), hexc('#FF2D3A'), hexc('#F6E7C1'), hexc('#140A22')
def eback(u, c=1.9): u = clamp(u); return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2

# ---------------------------------------------------------------- fixed fields
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
def smooth_noise(scale, seed):
    r = np.random.default_rng(seed)
    n = r.random((H // scale + 3, W // scale + 3)).astype(np.float32)
    return cv2.resize(n, (W + 3 * scale, H + 3 * scale), interpolation=cv2.INTER_CUBIC)[:H, :W]
DX = (smooth_noise(150, 4) - 0.5) * 2; DY = (smooth_noise(150, 5) - 0.5) * 2
INKF = 0.6 * smooth_noise(90, 1) + 0.4 * smooth_noise(24, 2); INKF = (INKF - INKF.min()) / (INKF.max() - INKF.min())
BCX, BCY = W / 2, H * 0.42
ANG = np.arctan2(_yy - BCY, _xx - BCX).astype(np.float32)
RADN = (np.sqrt((_xx - BCX) ** 2 + (_yy - BCY) ** 2) / math.hypot(W / 2, H * 0.58)).astype(np.float32)
SPC = 26.0
DGRID = np.sqrt(((_xx % SPC) - SPC / 2) ** 2 + ((_yy % SPC) - SPC / 2) ** 2).astype(np.float32)
DIAG = ((_xx + _yy) / (W + H)).astype(np.float32)
_vr = np.sqrt(((_xx / W - .5) * 2) ** 2 * 0.8 + ((_yy / H - .5) * 2) ** 2 * 0.6)
VIG = (1 - 0.55 * np.clip((_vr - 0.5) / 0.9, 0, 1) ** 1.5).astype(np.float32)[..., None]
_g = np.random.default_rng(9)
GRAIN = [cv2.resize(_g.normal(0, 0.012, (H // 2, W // 2)).astype(np.float32), (W, H))[..., None] for _ in range(4)]

def make_shards(seed=11, nx=4, ny=7):
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

# ---------------------------------------------------------------- grade
GR = {  # shadow tint, highlight tint, strength
    'desert': (hexc('#3A1A40'), hexc('#FFD9A0'), 1.0), 'magnet': (hexc('#2A0A55'), hexc('#F2C8FF'), 1.15),
    'steel': (hexc('#06301E'), hexc('#DDFFC0'), 1.0), 'blood': (hexc('#4A0410'), hexc('#FFD0C8'), 1.1),
    'rope': (hexc('#3A0640'), hexc('#FFC0EA'), 1.1), 'none': (None, None, 0)}
def grade(rgb, g):
    sh, hi, k = GR[g]
    out = np.clip((rgb - 0.5) * 1.1 + 0.5, 0, 1)
    l = out.mean(2, keepdims=True)
    out = np.clip(l + (out - l) * 1.18, 0, 1)
    if sh is None: return out
    out = out + (sh - out) * (0.3 * k * (1 - l) ** 2)
    out = out * (1 + (hi - 1) * (0.28 * k * l ** 2))
    return np.clip(out, 0, 1).astype(np.float32)

# ---------------------------------------------------------------- camera
def cam(cx, cy, h, rot=0.0): return (cx, cy, h, rot)
def view_M(c):
    cx, cy, h, rot = c; w = h * ASP; k = H / h
    M = np.float32([[k, 0, W / 2 - k * cx], [0, k, H / 2 - k * cy], [0, 0, 1]])
    if rot:
        Rm = np.vstack([cv2.getRotationMatrix2D((W / 2, H / 2), rot, 1.0), [0, 0, 1]]).astype(np.float32); M = Rm @ M
    return M
def view(p, c):
    up, s = page(p); M = view_M(c)[:2].copy(); M[:, :2] /= s
    return cv2.warpAffine(up, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

MOVE = 0.17
def tour_cam(sh, t):
    ks = sh['keys']; moving = 0.0
    c = ks[0][1]
    for (ta, ca), (tb, cb) in zip(ks, ks[1:]):
        if t >= tb: c = cb; continue
        u = clamp((t - tb + MOVE) / MOVE)
        if u > 0: c = tuple(lerp(p, q, eio(u)) for p, q in zip(ca, cb)); moving = math.sin(math.pi * u)
        else:
            hold = clamp((t - ta) / max(tb - MOVE - ta, 1e-3)); c = (ca[0], ca[1], ca[2] / (1 + 0.07 * eio(hold)), ca[3])
        break
    else:
        hold = clamp((t - ks[-1][0]) / max(sh['t1'] - ks[-1][0], 1e-3)); cl = ks[-1][1]
        c = (cl[0], cl[1], cl[2] / (1 + 0.07 * eio(hold)), cl[3])
    return c, moving

def to_screen(sh, t, pt):
    if sh['kind'] != 'tour': return pt
    c, _ = tour_cam(sh, t); q = view_M(c) @ np.float32([pt[0], pt[1], 1]); return (float(q[0]), float(q[1]))

# ---------------------------------------------------------------- backgrounds + cards
def burst(t, c1, c2, n=18, speed=0.5):
    rays = np.clip(np.sin(ANG * n + t * speed) * 6, -1, 1) * 0.5 + 0.5
    img = c1 * rays[..., None] + c2 * (1 - rays[..., None])
    img = img * (1 - 0.55 * np.clip(RADN, 0, 1) ** 1.3)[..., None]
    dots = (DGRID < SPC * 0.22 * (0.4 + RADN)).astype(np.float32)[..., None]
    return (img * (1 - 0.18 * dots)).astype(np.float32)

_CARD, _BLUR = {}, {}
def card_img(p, r, cw):
    key = (p, tuple(r), cw)
    if key not in _CARD:
        up, s = page(p); x, y, w, h = r
        cr = up[int(y * s):int((y + h) * s), int(x * s):int((x + w) * s)]
        ch = int(round(cw * h / w)); im = cv2.resize(cr, (cw, ch), interpolation=cv2.INTER_AREA)
        im = cv2.copyMakeBorder(im, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=(0.97, 0.95, 0.9))
        im = cv2.copyMakeBorder(im, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=(0.02, 0.02, 0.03))
        _CARD[key] = im.astype(np.float32)
    return _CARD[key]
def blur_bg(p, r):
    key = (p, tuple(r))
    if key not in _BLUR:
        up, s = page(p); x, y, w, h = r
        cr = up[int(y * s):int((y + h) * s), int(x * s):int((x + w) * s)]
        k = max(108 / cr.shape[1], 192 / cr.shape[0])
        sm = cv2.resize(cr, (int(cr.shape[1] * k) + 1, int(cr.shape[0] * k) + 1), interpolation=cv2.INTER_AREA)
        oy, ox = (sm.shape[0] - 192) // 2, (sm.shape[1] - 108) // 2
        sm = cv2.GaussianBlur(sm[oy:oy + 192, ox:ox + 108], (0, 0), 5)
        _BLUR[key] = cv2.resize(sm, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    return _BLUR[key]

def project_card(rgb, im, cx, cy, sc, rz, ry, rx, f=1900.0, shadow=0.55):
    h, w = im.shape[:2]; hw, hh = w * sc / 2, h * sc / 2
    P = np.float32([[-hw, -hh, 0], [hw, -hh, 0], [hw, hh, 0], [-hw, hh, 0]])
    a, bb, c = math.radians(ry), math.radians(rx), math.radians(rz)
    Ry = np.float32([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    Rx = np.float32([[1, 0, 0], [0, math.cos(bb), -math.sin(bb)], [0, math.sin(bb), math.cos(bb)]])
    Rz = np.float32([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    Q = P @ (Rz @ Rx @ Ry).T
    dst = np.float32([[cx + f * q[0] / (f + q[2]), cy + f * q[1] / (f + q[2])] for q in Q])
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    Hm = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(im, Hm, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    m = cv2.warpPerspective(np.ones((h, w), np.float32), Hm, (W, H), flags=cv2.INTER_LINEAR)[..., None]
    if shadow:
        sm = cv2.GaussianBlur(m[..., 0], (0, 0), 22); sm = np.roll(np.roll(sm, 34, 0), 22, 1)[..., None]
        rgb[:] = rgb * (1 - shadow * sm)
    rgb[:] = rgb * (1 - m) + warped * m

# ---------------------------------------------------------------- timeline
S, TEXT, MEN, HITS, DIM = [], [], [], [], []
def tour(t0, t1, p, keys, g, tr=None, **kw): S.append(dict(kind='tour', t0=t0, t1=t1, p=p, keys=keys, grade=g, tr=tr, **kw))
def card(t0, t1, p, r, g, tr=None, **kw): S.append(dict(kind='card', t0=t0, t1=t1, p=p, r=r, grade=g, tr=tr, **kw))
def T(t, s, x, y, size, end=None, fnt=IMP, ent='slam', **kw): TEXT.append(dict(t=t, s=s, x=x, y=y, size=size, end=end, fnt=fnt, ent=ent, **kw))
def BAR(t, x, y, w, h, col, end=None, skew=-12, a=0.9): TEXT.append(dict(t=t, ent='bar', x=x, y=y, w=w, h=h, col=col, end=end, skew=skew, a=a, s=''))
def menace(t0, t1, s, x, y, dx, dy, size, col=VIOLET, rot=-10): MEN.append(dict(t0=t0, t1=t1, s=s, x=x, y=y, dx=dx, dy=dy, size=size, col=col, rot=rot))
JPS = dict(fnt=JP, stroke=0.07)

# ---- INTRO 0-8: three hours, same pace
tour(b(0), b(4), '01', [(b(0), cam(285, 140, 330)), (b(2), cam(690, 230, 420)), (b(3), cam(855, 250, 300, -3))], 'desert',
     lines='gallop')
T(b(0) + 0.05, '三時間', 130, 300, 150, b(4), vertical=True, **JPS)
BAR(b(1), W / 2, 1462, 1250, 190, INK, b(4))
T(b(1), 'THREE HOURS', W / 2, 1455, 150, b(4), glint=b(2.5), slant=-8)
T(b(2), 'SAME PACE.', W / 2, 1600, 92, b(4), fill=tuple(PINK), stroke=0.05, slant=-8)
tour(b(4), b(6), '02', [(b(4), cam(445, 900, 270)), (b(5.5), cam(470, 915, 190))], 'desert', tr='slash')
T(b(4) + 0.05, '誰だ…？', 950, 230, 120, b(6), vertical=True, **JPS)
T(b(4.5), 'WHO IS THAT?', W / 2, 1560, 120, b(6), stroke=0.05, slant=-8)
card(b(6), b(8), '03', [40, 440, 608, 240], 'desert', tr='zoom', cw=1000, pos=(540, 980), rz=(-5, -2), ry=(24, -6),
     bg=('burst', hexc('#5B2A86'), hexc('#1A0B2E')))
menace(b(6), b(8), 'ドドドド', 160, 330, 120, 30, 150, PINK, -12)
T(b(6.5), 'SOMEONE IS', W / 2, 1450, 110, b(8), slant=-8, stroke=0.05)
T(b(7), 'CATCHING UP', W / 2, 1580, 130, b(8), slant=-8, stroke=0.05, fill=tuple(GOLD))

# ---- DROP 1 8-16: Mountain Tim
tour(b(8), b(10), '04', [(b(8), cam(470, 290, 620)), (b(9.4), cam(470, 200, 400))], 'desert', tr='flash', lines='radial')
menace(b(8), b(10), 'ドドドドド', 120, 520, 30, 165, 150, PINK, -8)
T(b(8.5), 'ALREADY UP', 600, 1450, 120, b(10), slant=-8, stroke=0.05)
T(b(9), 'THE ROCKS?!', 600, 1585, 130, b(10), slant=-8, stroke=0.05, fill=tuple(GOLD))
card(b(10), b(14), '03', [262, 694, 206, 330], 'desert', tr='liquid', cw=600, pos=(560, 1200), rz=(3, 1), ry=(-18, -4),
     bg=('burst', hexc('#7A3FC2'), hexc('#24103E')))
BAR(b(10) + 0.05, W / 2, 470, 1300, 430, INK, b(14), skew=-10, a=0.88)
T(b(10) + 0.1, 'MOUNTAIN', 560, 390, 190, b(14), stg=0.035, glint=b(12))
T(b(10.6), 'TIM', 560, 590, 250, b(14), fill=tuple(GOLD), stroke=0.04, glint=b(12.5))
T(b(10.4), 'マウンテン・ティム', 990, 210, 66, b(14), vertical=True, fill=tuple(GOLD), **JPS)
T(b(11.5), 'THE COWBOY  //  RACE ENTRANT', W / 2, 165, 40, b(14), fnt=LAB, ent='type', trk=0.12)
tour(b(14), b(16), '04', [(b(14), cam(160, 790, 470)), (b(15.4), cam(165, 720, 360))], 'desert', tr='glitch')
T(b(14) + 0.05, '速すぎる…！', 960, 210, 110, b(16), vertical=True, **JPS)
T(b(14.5), 'TOO FAST.', W / 2, 1560, 150, b(16), slant=-8, stroke=0.05, fill=tuple(PINK))

# ---- MAGNET 16-40
MAG0, MAG1 = b(16), b(40)
tour(b(16), b(20), '05', [(b(16), cam(370, 330, 640)), (b(18), cam(420, 300, 480)), (b(19.3), cam(435, 300, 390, 3))],
     'magnet', tr='magnet', mag=(440, 330), field=True)
T(b(16) + 0.05, '引っ張られる！', 110, 210, 96, b(20), vertical=True, **JPS)
BAR(b(17), W / 2, 1555, 1200, 230, VIOLET, b(20), a=0.92)
T(b(17), 'PULLED!', W / 2, 1550, 230, b(20), glint=b(18.5), slant=-8, stroke=0.03)
tour(b(20), b(24), '08', [(b(20), cam(230, 200, 400)), (b(21.5), cam(300, 185, 340, -4)), (b(23), cam(210, 235, 300, 4))],
     'magnet', tr='zoom', mag=(240, 190))
T(b(20) + 0.05, '金属が…！', 960, 220, 120, b(24), vertical=True, **JPS)
T(b(20.5), 'THE METAL', W / 2, 1440, 130, b(24), slant=-8, stroke=0.05)
T(b(21), 'IS FLYING AT ME', W / 2, 1575, 104, b(24), slant=-8, stroke=0.05, fill=tuple(PINK))
tour(b(24), b(28), '09', [(b(24), cam(400, 190, 380)), (b(26), cam(395, 175, 320, 3)), (b(27.2), cam(390, 165, 270))],
     'magnet', tr='liquid', field=True)
T(b(24.3), '磁石', W / 2, 1380, 300, b(28), fill=tuple(MAG), glint=b(26), **JPS)
T(b(25), 'GYRO TOO?!', W / 2, 1610, 130, b(28), slant=-8, stroke=0.05, fill=tuple(LIME))
tour(b(28), b(30), '11', [(b(28), cam(530, 215, 420)), (b(29.3), cam(540, 235, 350))], 'magnet', tr='slash')
T(b(28.3), 'MOUNTAIN TIM...', W / 2, 1600, 76, b(30), fnt=LAB, ent='type', trk=0.1)
tour(b(30), b(32), '12', [(b(30), cam(500, 720, 560)), (b(31.3), cam(490, 640, 380))], 'magnet', tr='whip', mag=(490, 580))
T(b(30) + 0.05, '三人とも', 120, 260, 120, b(32), vertical=True, **JPS)
T(b(30.4), 'ALL THREE OF US', W / 2, 1560, 112, b(32), slant=-8, stroke=0.05)
tour(b(32), b(40), '13', [(b(32), cam(900, 520, 560)), (b(34), cam(555, 540, 600, -4)), (b(36), cam(330, 470, 420)),
                          (b(38), cam(300, 575, 290, 5))], 'blood', tr='liquid', mag=(520, 640), field=True)
menace(b(32), b(36), 'ゴゴゴゴ', 140, 280, 40, 170, 140, VIOLET, -10)
T(b(36.1), 'THE IRON IN OUR BLOOD', W / 2, 1560, 62, b(38), fnt=LAB, ent='type', trk=0.08)
T(b(38), '爆発', W / 2, 860, 300, b(39.5), ent='grow', fill=tuple(RED), **JPS)
T(b(38.6), 'WE WILL EXPLODE', W / 2, 1300, 110, b(39.5), slant=-8, stroke=0.05, fill=tuple(RED))
DIM.append((b(39.5), b(40)))

# ---- STEEL BALL 40-56
tour(b(40), b(44), '16', [(b(40), cam(330, 820, 440)), (b(42), cam(290, 812, 330)), (b(43.2), cam(272, 815, 255, -6))],
     'steel', tr='swirl', spiral=(270, 822))
T(b(40) + 0.05, '鉄球', 950, 230, 170, b(44), vertical=True, fill=tuple(LIME), **JPS)
BAR(b(41), W / 2, 1575, 1150, 200, INK, b(44))
T(b(41), 'STEEL BALL', W / 2, 1570, 160, b(44), glint=b(42.5), slant=-8)
tour(b(44), b(48), '17', [(b(44), cam(275, 545, 330)), (b(45.4), cam(115, 690, 310, 8)), (b(46.8), cam(298, 832, 290, -4))],
     'steel', tr='zoom', spiral=(300, 832), spiral_from=b(46.6), lines='radial')
T(b(44.4), 'ギュルルルルル', W / 2, 1520, 120, b(48), fill=tuple(LIME), rot=-10, **JPS)
tour(b(48), b(50), '17', [(b(48), cam(530, 720, 520)), (b(49.3), cam(540, 735, 360, 6))], 'steel', tr='halftone',
     spiral=(540, 722))
T(b(48) + 0.05, '回転', 130, 260, 200, b(50), vertical=True, fill=tuple(LIME), **JPS)
T(b(48.4), 'THE IRON COMES BACK', W / 2, 1560, 96, b(50), slant=-8, stroke=0.05)
tour(b(50), b(52), '18', [(b(50), cam(470, 215, 440)), (b(51.3), cam(485, 190, 360, -5))], 'blood', tr='flash')
T(b(50) + 0.03, 'ドギャーン', W / 2, 1500, 190, b(52), fill=tuple(PINK), rot=-8, **JPS)
tour(b(52), b(54), '19', [(b(52), cam(165, 760, 560)), (b(53.3), cam(150, 700, 420, 4))], 'blood', tr='shatter')
T(b(52) + 0.05, '覚悟しろ', 960, 220, 110, b(54), vertical=True, **JPS)
T(b(52.4), 'BRACE YOURSELF,', W / 2, 1450, 100, b(54), slant=-8, stroke=0.05)
T(b(52.9), 'JOHNNY!!', W / 2, 1600, 170, b(54), slant=-8, stroke=0.05, fill=tuple(PINK))
tour(b(54), b(56), '20', [(b(54), cam(490, 250, 440)), (b(55.2), cam(500, 225, 350))], 'steel', tr='whip')
T(b(54) + 0.05, 'やったぞ！', 110, 230, 110, b(56), vertical=True, **JPS)
T(b(54.4), 'OFF HIS', W / 2, 1440, 130, b(56), slant=-8, stroke=0.05)
T(b(54.8), 'HORSE!!', W / 2, 1590, 170, b(56), slant=-8, stroke=0.05, fill=tuple(LIME))

# ---- BREAK 56-62
card(b(56), b(58), '20', [170, 800, 478, 224], 'blood', tr='glitch', cw=1050, pos=(540, 1000), rz=(-3, -1), ry=(20, 0),
     bg=('burst', hexc('#8E1020'), hexc('#1E0306')))
T(b(56) + 0.05, '近すぎる', W / 2, 520, 170, b(58), fill=tuple(RED), **JPS)
T(b(56.5), 'TOO CLOSE.', W / 2, 1450, 190, b(58), slant=-8, stroke=0.05)
tour(b(58), b(62), '21', [(b(58), cam(760, 300, 560)), (b(59.5), cam(790, 420, 520, -5)), (b(61), cam(800, 520, 420, 4))],
     'magnet', tr='halftone', lines='radial')
T(b(58) + 0.05, '飛んでる！', 120, 230, 120, b(62), vertical=True, fill=tuple(PINK), **JPS)
T(b(58.6), "HE'S FLYING!", W / 2, 1560, 150, b(62), slant=-8, stroke=0.05)
DIM.append((b(61.75), b(62)))

# ---- DROP 2 62-78: the rope
tour(b(62), b(70), '23', [(b(62), cam(380, 400, 560)), (b(64), cam(190, 650, 430, -8)), (b(66), cam(760, 235, 440, 6)),
                          (b(68), cam(520, 420, 790))], 'rope', tr='magnet', lines='radial')
T(b(62) + 0.1, 'STAND', 200, 330, 60, b(66), fnt=LAB, ent='type', trk=0.3, fill=tuple(GOLD))
BAR(b(62.2), W / 2, 470, 1300, 200, INK, b(66), a=0.85)
T(b(62.2), 'OH! LONESOME ME', W / 2, 465, 128, b(66), stg=0.03, glint=b(64), slant=-6)
T(b(62.6), 'オー！ロンサム・ミー', 990, 640, 64, b(66), vertical=True, fill=tuple(GOLD), **JPS)
T(b(66), 'HE SPLIT HIS BODY', W / 2, 1440, 110, b(70), slant=-8, stroke=0.05)
T(b(66.5), 'ALONG THE ROPE', W / 2, 1580, 130, b(70), slant=-8, stroke=0.05, fill=tuple(LIME))
card(b(70), b(72), '24', [0, 330, 648, 270], 'rope', tr='slash', cw=1060, pos=(540, 980), rz=(-10, -6), ry=(-22, 0),
     bg=('burst', hexc('#C0207A'), hexc('#2A0420')))
T(b(70) + 0.05, 'ロープ', W / 2, 520, 220, b(72), fill=tuple(LIME), **JPS)
tour(b(72), b(74), '24', [(b(72), cam(220, 800, 420)), (b(73.3), cam(245, 790, 330, -6))], 'rope', tr='whip')
T(b(72.2), 'シュルルル', W / 2, 1520, 140, b(74), fill=tuple(PINK), rot=-10, **JPS)
tour(b(74), b(76), '25', [(b(74), cam(270, 190, 330)), (b(75.3), cam(258, 170, 255))], 'desert', tr='liquid')
T(b(74) + 0.05, 'バラバラ', 120, 260, 110, b(76), vertical=True, **JPS)
T(b(74.4), 'I CAN SEPARATE', W / 2, 1450, 108, b(76), slant=-8, stroke=0.05)
T(b(74.9), 'MY BODY.', W / 2, 1600, 170, b(76), slant=-8, stroke=0.05, fill=tuple(GOLD))
for k, (p, c, g) in enumerate((('03', cam(330, 865, 330), 'desert'), ('05', cam(430, 290, 420), 'magnet'),
                               ('09', cam(390, 160, 300), 'magnet'), ('16', cam(272, 815, 300), 'steel'))):
    tour(b(76 + 0.5 * k), b(76.5 + 0.5 * k), p, [(b(76 + 0.5 * k), c)], g, inkhit=True)
menace(b(76), b(78), 'ゴゴゴゴ', 150, 300, 50, 175, 150, VIOLET, -10)

# ---- OUTRO 78-86: title, freeze, to be continued
card(b(78), DUR + 0.1, '23', [90, 50, 900, 700], 'rope', tr='flash', cw=1060, pos=(540, 680), rz=(-4, -2), ry=(10, -6),
     bg=('burst', hexc('#D8A21E'), hexc('#2A1606')), zoom=(1.12, 1.0))
T(b(78.2), 'STEEL', W / 2, 1220, 220, None, stg=0.04, glint=b(80))
T(b(78.6), 'BALL RUN', W / 2, 1410, 220, None, stg=0.04, fill=tuple(GOLD), glint=b(80.5))
T(b(79.2), 'スティール・ボール・ラン', W / 2, 1555, 58, None, fill=(1, 1, 1), **JPS)
T(b(79.8), 'CHAPTER 18  //  MOUNTAIN TIM', W / 2, 200, 44, None, fnt=LAB, ent='type', trk=0.14)
FREEZE, ARROW = b(82), b(83)

# ---------------------------------------------------------------- hits from the beat map
BIG = {8, 40, 50, 62, 78}
for ht in BM['hit']:
    k = int(round(ht / BEAT))
    HITS.append(dict(t=ht, big=k in BIG, mode='ink' if k in BIG else 'inv'))
KICKS, SNARES = np.array(BM['kick']), np.array(BM['snare'])
def pulse(arr, t, d):
    a = arr[(arr <= t) & (arr > t - 4 * d)]
    return float(np.exp(-(t - a) / d).sum()) if len(a) else 0.0

# ---------------------------------------------------------------- shot rendering + fx
def spiral(rgb, P, t, a0, col=LIME):
    cx, cy = P; lay = np.zeros((H, W), np.float32)
    bphi = math.log((1 + 5 ** 0.5) / 2) / (math.pi / 2)
    th = np.linspace(-5.5 * math.pi, 0, 500); r = 340 * np.exp(bphi * th)
    rot = -t * 7.0
    pts = np.int32(np.stack([cx + r * np.cos(th + rot), cy + r * np.sin(th + rot)], 1) * 16)
    cv2.polylines(lay, [pts], False, 1.0, 5, cv2.LINE_AA, 4)
    for k in range(3):                                       # rotating rings around the ball
        ang = (t * 300 + k * 60) % 360
        cv2.ellipse(lay, (int(cx), int(cy)), (int(150 + 25 * k), int(48 + 10 * k)), ang, 0, 300, 0.8, 3, cv2.LINE_AA)
    glow = cv2.GaussianBlur(lay, (0, 0), 9)
    rgb[:] = rgb + (col * (glow * 1.4 + lay * 0.5)[..., None] + lay[..., None] * 0.5) * a0

def particles(rgb, P, t, t0, n=230, a0=1.0):
    r = np.random.default_rng(5); lt = t - t0
    ang = r.uniform(0, 2 * math.pi, n); r0 = r.uniform(380, 1500, n); sp = r.uniform(0.5, 1.2, n); ph = r.random(n)
    u = (lt * sp + ph) % 1.0; rad = r0 * (1 - u) ** 1.6 + 30
    ln = 30 + 140 * u * sp; th = r.integers(2, 5, n)
    for i in range(n):
        c, s = math.cos(ang[i]), math.sin(ang[i])
        p0 = (int(P[0] + c * rad[i]), int(P[1] + s * rad[i])); p1 = (int(P[0] + c * (rad[i] + ln[i])), int(P[1] + s * (rad[i] + ln[i])))
        col = (0.2, 0.18, 0.24) if i % 3 else (0.85, 0.82, 0.95)
        cv2.line(rgb, p0, p1, col, int(th[i]), cv2.LINE_AA)

def field(rgb, P, t, a0=1.0):
    lay = np.zeros((H, W), np.float32); cx, cy = P
    th = np.linspace(0.12, math.pi - 0.12, 160)
    for C in (260, 420, 640, 900, 1250, 1700):
        r = C * np.sin(th) ** 2
        for side in (-1, 1):
            xs, ys = cx + side * r * np.sin(th), cy - r * np.cos(th)
            seg = np.cumsum(np.r_[0, np.hypot(np.diff(xs), np.diff(ys))])
            on = ((seg / 60 - t * 3.0) % 1.0) < 0.55
            pts = np.stack([xs, ys], 1)
            for i in range(len(pts) - 1):
                if on[i]: cv2.line(lay, (int(pts[i, 0]), int(pts[i, 1])), (int(pts[i + 1, 0]), int(pts[i + 1, 1])), 1.0, 2, cv2.LINE_AA)
    glow = cv2.GaussianBlur(lay, (0, 0), 6)
    rgb[:] = rgb + VIOLET * ((glow * 0.9 + lay * 0.35) * 0.55 * a0)[..., None]

def render_shot(sh, t):
    lt = t - sh['t0']; dur = sh['t1'] - sh['t0']
    if sh['kind'] == 'tour':
        c, mv = tour_cam(sh, t)
        if mv > 0.05:
            acc = 0; n = 4
            for i in range(n): acc = acc + view(sh['p'], tour_cam(sh, t - (i / n) * (1 / FPS) * 0.9)[0])
            img = acc / n
        else: img = view(sh['p'], c)
        rgb = grade(img, sh['grade'])
    else:
        bgk, c1, c2 = sh['bg']
        rgb = burst(t, c1, c2) * 0.7 + grade(blur_bg(sh['p'], sh['r']), sh['grade']) * 0.3
        u = eio(lt / dur); e = eout(lt / 0.35)
        z0, z1 = sh.get('zoom', (1.0, 1.06))
        sc = lerp(z0, z1, u) * lerp(1.35, 1.0, e)
        rz = lerp(*sh['rz'], u) + (1 - e) * 12; ry = lerp(*sh['ry'], u); rx = 6 * math.sin(lt * 1.3)
        im = card_img(sh['p'], sh['r'], sh['cw'])
        im = grade(im, sh['grade'])
        project_card(rgb, im, sh['pos'][0], sh['pos'][1] + (1 - e) * 120, sc, rz, ry, rx)
    rgb = np.ascontiguousarray(rgb, np.float32)
    if sh.get('lines'): R.speed_lines(rgb, t, sh['lines'], seed=int(sh['p']))
    if sh.get('field'): field(rgb, to_screen(sh, t, sh.get('mag', (W / 2, H / 2))) if sh.get('mag') else (W / 2, H * 0.45), t)
    if sh.get('mag'): particles(rgb, to_screen(sh, t, sh['mag']), t, sh['t0'])
    if sh.get('spiral') and t >= sh.get('spiral_from', 0):
        a0 = clamp((t - max(sh['t0'], sh.get('spiral_from', 0))) / 0.15)
        spiral(rgb, to_screen(sh, t, sh['spiral']), t, a0)
    return rgb

# ---------------------------------------------------------------- transitions (cur = new shot, prev = old shot)
D_TR = {'liquid': 0.42, 'swirl': 0.5, 'magnet': 0.45, 'slash': 0.3, 'zoom': 0.28, 'shatter': 0.5, 'glitch': 0.2,
        'whip': 0.18, 'halftone': 0.35, 'flash': 0.12}
def remap(img, mx, my): return cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
def transition(cur, prev, tr, u):
    if tr == 'liquid':
        a = 170 * math.sin(math.pi * u)
        A = remap(prev, _xx + DX * a * u, _yy + DY * a * u); B = remap(cur, _xx - DX * a * (1 - u), _yy - DY * a * (1 - u))
        e = eio(u); return A * (1 - e) + B * e
    if tr == 'swirl':                                         # the steel ball's spin twists one shot into the next
        cx, cy = W / 2, H * 0.45; dx, dy = _xx - cx, _yy - cy
        r = np.sqrt(dx * dx + dy * dy) / (H * 0.62); fall = np.clip(1 - r, 0, 1) ** 2
        out = None
        for img, s in ((prev, 9 * eio(u)), (cur, -9 * eio(1 - u))):
            a = s * fall; ca, sa = np.cos(a), np.sin(a)
            z = 1 + 0.25 * abs(s) / 9
            w_ = remap(img, cx + (dx * ca - dy * sa) / z, cy + (dx * sa + dy * ca) / z)
            out = w_ if out is None else out * (1 - eio(u)) + w_ * eio(u)
        return out
    if tr == 'magnet':                                        # pulled into the centre, the next shot pours out of it
        cx, cy = W / 2, H * 0.45; dx, dy = _xx - cx, _yy - cy
        r = np.sqrt(dx * dx + dy * dy) + 1e-3; rn = r / (H * 0.6)
        sa = 1 + 7 * ein(u) * np.exp(-rn * 0.6); sb = 1 + 7 * ein(1 - u) * np.exp(-rn * 0.6)
        tw = 1.6 * u; ca, sn = math.cos(tw), math.sin(tw)
        A = remap(prev, cx + (dx * ca - dy * sn) * sa, cy + (dx * sn + dy * ca) * sa)
        B = remap(cur, cx + dx * sb, cy + dy * sb)
        e = clamp((u - 0.35) / 0.3); out = A * (1 - e) + B * e
        ring = np.exp(-((rn - 1.2 * (1 - u)) / 0.03) ** 2)[..., None] * math.sin(math.pi * u)
        return out + VIOLET * ring * 1.2
    if tr == 'slash':
        e = eout(u); dm = (_xx * 0.42 - _yy * 0.9 + 600); side = (dm > 0)[..., None]; off = e * 760
        A = cv2.warpAffine(prev, np.float32([[1, 0, off * 0.42], [0, 1, -off * 0.9]]), (W, H))
        B = cv2.warpAffine(prev, np.float32([[1, 0, -off * 0.42], [0, 1, off * 0.9]]), (W, H))
        out = np.where((np.abs(dm) < off * 0.99)[..., None], cur, np.where(side, A, B))
        return out + np.exp(-(dm / (3 + 30 * (1 - u))) ** 2)[..., None] * (1 - u) * 1.6
    if tr == 'zoom':
        A = cv2.warpAffine(prev, cv2.getRotationMatrix2D((W / 2, H / 2), 0, 1 + 2.5 * ein(u)), (W, H), borderMode=cv2.BORDER_REFLECT)
        A = cv2.GaussianBlur(A, (0, 0), 1 + 16 * u)
        B = cv2.warpAffine(cur, cv2.getRotationMatrix2D((W / 2, H / 2), 0, lerp(1.45, 1.0, eout(u))), (W, H), borderMode=cv2.BORDER_REFLECT)
        e = eout(u); return A * (1 - e) + B * e
    if tr == 'shatter':
        out = cur.copy()
        for tri, c, d, rot, spd, dl in SHARDS:
            p = clamp((u - dl) / (1 - dl)) ** 1.5
            if p >= 1: continue
            M = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), rot * 70 * p, 1 + 0.25 * p)
            M[:, 2] += d * p * 900 * spd + np.float32([0, p * p * 600])
            q = np.float32(tri) @ M[:, :2].T + M[:, 2]
            bx, by = int(max(0, q[:, 0].min() - 2)), int(max(0, q[:, 1].min() - 2))
            bx1, by1 = int(min(W, q[:, 0].max() + 2)), int(min(H, q[:, 1].max() + 2))
            if bx1 - bx < 2 or by1 - by < 2: continue
            M2 = M.copy(); M2[:, 2] -= (bx, by)
            piece = cv2.warpAffine(prev, M2, (bx1 - bx, by1 - by), flags=cv2.INTER_LINEAR)
            m = np.zeros((by1 - by, bx1 - bx), np.float32)
            cv2.fillConvexPoly(m, np.int32((q - [bx, by]) * 16), 1.0, cv2.LINE_AA, 4); m = m[..., None]
            edge = cv2.morphologyEx(m[..., 0], cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))[..., None]
            reg = out[by:by1, bx:bx1]; reg[:] = reg * (1 - m) + (piece * (1 - 0.3 * p) + 0.7 * edge) * m
        return out
    if tr == 'glitch':
        r = np.random.default_rng(int(u * 41)); out = (prev if u < 0.45 else cur).copy()
        for _ in range(16):
            y0 = int(r.integers(0, H - 40)); hh = int(r.integers(12, 150)); src = cur if r.random() < u else prev
            out[y0:y0 + hh] = np.roll(src[y0:y0 + hh], int(r.integers(-180, 180)), 1)
        out[..., 0] = np.roll(out[..., 0], 14, 1); out[..., 2] = np.roll(out[..., 2], -14, 1)
        return out
    if tr == 'whip':
        e = eio(u); dy = e * H
        A = cv2.warpAffine(prev, np.float32([[1, 0, 0], [0, 1, -dy]]), (W, H), borderMode=cv2.BORDER_REFLECT)
        B = cv2.warpAffine(cur, np.float32([[1, 0, 0], [0, 1, H - dy]]), (W, H), borderMode=cv2.BORDER_REFLECT)
        out = np.where((_yy < H - dy)[..., None], A, B)
        kb = int(1 + 150 * math.sin(math.pi * u)) * 2 + 1
        return cv2.blur(out, (1, kb))
    if tr == 'halftone':
        r = np.clip(u * 1.7 - DIAG * 0.7, 0, 1) * SPC * 0.8
        m = np.clip((r - DGRID) / 1.5 + 0.5, 0, 1)[..., None]
        rim = np.clip((r + 4 - DGRID) / 1.5 + 0.5, 0, 1)[..., None] - m
        return (prev * (1 - rim) + MAG * rim) * (1 - m) + cur * m
    if tr == 'flash':
        return cur + (PAPER - cur) * (1 - u)
    return cur

# ---------------------------------------------------------------- type
def text_items(it):
    s, size = it['s'], it['size']; f = R.font(it['fnt'], size); trk = it.get('trk', 0.0) * size
    kw = dict(fill=tuple(it.get('fill', (1, 1, 1))), stroke=it.get('stroke', 0.0), sfill=(0.02, 0.01, 0.04), slant=it.get('slant', 0.0))
    items = []
    if it.get('vertical'):
        for i, ch in enumerate(s):
            rot = -90 if ch in 'ー…～' else 0
            dx = size * 0.28 if ch in 'ッャュョァィゥェォ、。' else 0
            items.append((ch, it['x'] + dx, it['y'] + i * size * 1.02, rot))
    else:
        adv = [f.getlength(ch) + trk for ch in s]; tw = sum(adv) - trk; x = it['x'] - tw / 2
        for ch, a in zip(s, adv): items.append((ch, x + a / 2, it['y'], 0)); x += a
    return items, kw

def draw_texts(rgb, t):
    for it in TEXT:
        lt = t - it['t']
        if lt < 0 or (it['end'] is not None and t > it['end']): continue
        fade = clamp((it['end'] - t) / 0.07) if it['end'] is not None else 1.0
        if it['ent'] == 'bar':
            slab(rgb, it['x'], it['y'], it['w'], it['h'], it['col'], skew=it['skew'], a=it['a'] * fade, u=lt / 0.18); continue
        if it['ent'] == 'type':
            n = int(len(it['s']) * clamp(lt / (len(it['s']) * 0.03)))
            if n <= 0: continue
            kw = dict(fill=tuple(it.get('fill', (1, 1, 1))), trk=it.get('trk', 0.0), stroke=0.04, sfill=(0, 0, 0))
            full = sprite(it['s'], it['fnt'], it['size'], **kw); spr = sprite(it['s'][:n], it['fnt'], it['size'], **kw)
            blit(rgb, spr, it['x'] - full.shape[1] / 2 + spr.shape[1] / 2, it['y'], a=fade); continue
        items, kw = text_items(it)
        if it['ent'] == 'grow':                               # swells and shakes until it bursts
            u = clamp(lt / max(it['end'] - it['t'], 1e-3)); r = np.random.default_rng(int(t * FPS))
            for ch, x, y, rot in items:
                spr = sprite(ch, it['fnt'], it['size'], **kw)
                blit(rgb, spr, x + r.normal(0, 4 + 14 * u), y + r.normal(0, 4 + 14 * u), lerp(0.55, 1.35, u ** 1.5), rot, fade)
            continue
        stg = it.get('stg', 0.02); base_rot = it.get('rot', 0)
        if base_rot and not it.get('vertical'):              # rotate the whole line about its centre
            cr, sr = math.cos(math.radians(-base_rot)), math.sin(math.radians(-base_rot))
            items = [(ch, it['x'] + (x - it['x']) * cr, it['y'] + (x - it['x']) * sr, base_rot) for ch, x, y, _ in items]
        for i, (ch, x, y, rot) in enumerate(items):
            lc = lt - i * stg
            if lc < 0: continue
            e = eout(lc / 0.13)
            spr = sprite(ch, it['fnt'], it['size'], **kw)
            blit(rgb, spr, x, y + (1 - e) * -50, lerp(2.4, 1, e), rot, clamp(lc / 0.05) * fade, 8 * (1 - e))
        g = it.get('glint')
        if g is not None and 0 <= t - g < 0.45:
            u = (t - g) / 0.45
            xs = [x for _, x, _, _ in items]; x0, x1 = min(xs) - it['size'], max(xs) + it['size']
            px = lerp(x0, x1, eio(u)); y0, y1 = max(0, int(it['y'] - it['size'] * 0.7)), min(H, int(it['y'] + it['size'] * 0.7))
            xa, xb = int(max(0, x0)), int(min(W, x1))
            if xb > xa and y1 > y0:
                yy, xx = np.mgrid[y0:y1, xa:xb].astype(np.float32)
                band = np.exp(-(((xx - px) + (yy - it['y']) * 0.5) / 24) ** 2)
                reg = rgb[y0:y1, xa:xb]; reg += (band * (reg.mean(2) > 0.55) * 0.9)[..., None]

def draw_menace(rgb, t, bump):
    for m in MEN:
        if not (m['t0'] <= t < m['t1']): continue
        lt = t - m['t0']; fade = clamp((m['t1'] - t) / 0.08)
        for i, ch in enumerate(m['s']):
            lc = lt - i * 0.07
            if lc < 0: continue
            e = eback(lc / 0.18)
            x = m['x'] + i * m['dx'] + 10 * math.sin(t * 5 + i)
            y = m['y'] + i * m['dy'] + 14 * math.sin(t * 7.3 + i * 1.7)
            spr = sprite(ch, JP, m['size'], fill=tuple(m['col']), stroke=0.09, sfill=(0.03, 0.0, 0.05))
            blit(rgb, spr, x, y, max(0.05, e) * (1 + 0.1 * bump), m['rot'] + 6 * math.sin(t * 3 + i), fade)

def hud(rgb, t):
    if not (MAG0 <= t < b(44)): return
    a = clamp((t - MAG0) / 0.2) * clamp((b(44) - t) / 0.15)
    u = clamp((t - MAG0) / (MAG1 - MAG0)) ** 1.3
    x0, y0 = 70, 110
    blit(rgb, sprite('磁力  MAGNETIC FORCE', JP, 30, fill=(1, 1, 1), stroke=0.08, sfill=(0, 0, 0)), x0 + 190, y0, a=a)
    n = 20; lit = int(round(u * n))
    over = t >= MAG1
    for i in range(n):
        xa = x0 + i * 22
        on = i < lit or over
        col = (RED if (over or i >= 16) else VIOLET) if on else hexc('#2A2433')
        if over and int(t * 12) % 2: col = PAPER
        cv2.rectangle(rgb, (xa, y0 + 26), (xa + 15, y0 + 58), tuple(float(v) * a + float(rgb[y0 + 40, xa][j]) * (1 - a) for j, v in enumerate(col)), -1)
    txt = 'OVERLOAD' if over else f'{int(u * 100):3d}%'
    blit(rgb, sprite(txt, MONO, 34, fill=tuple(RED) if over or u > 0.8 else (1, 1, 1), stroke=0.1, sfill=(0, 0, 0)), x0 + 500, y0 + 42, a=a)

def tbc(rgb, t):
    """sepia freeze + the arrow"""
    l = rgb.mean(2, keepdims=True); l = np.clip((l - 0.05) * 1.15, 0, 1)
    sep = l * np.float32([1.08, 0.93, 0.68]) + np.float32([0.04, 0.02, 0.0])
    k = clamp((t - FREEZE) / 0.18); rgb = rgb * (1 - k) + sep * k
    if t >= ARROW:
        e = eback((t - ARROW) / 0.4, 1.4); x0 = lerp(W + 40, 70, e); y = 1715
        pts = np.int32([[x0, y], [x0 + 110, y - 92], [x0 + 110, y - 48], [x0 + 860, y - 48], [x0 + 860, y + 48],
                        [x0 + 110, y + 48], [x0 + 110, y + 92]])
        cv2.fillPoly(rgb, [pts], tuple(float(v) for v in hexc('#F1DDA8')), cv2.LINE_AA)
        cv2.polylines(rgb, [pts], True, tuple(float(v) for v in hexc('#3A2A12')), 9, cv2.LINE_AA)
        blit(rgb, sprite('TO BE CONTINUED', IMP, 70, fill=tuple(hexc('#3A2A12')), slant=-10), x0 + 485, y + 2)
    return rgb

# ---------------------------------------------------------------- frame
def shot_at(t):
    for i, s in enumerate(S):
        if s['t0'] <= t < s['t1']: return i
    return len(S) - 1

def frame_core(t):
    si = shot_at(t); sh = S[si]
    rgb = render_shot(sh, t)
    tr = sh.get('tr')
    if tr and si > 0 and t < sh['t0'] + D_TR[tr]:
        rgb = transition(rgb, render_shot(S[si - 1], t), tr, (t - sh['t0']) / D_TR[tr])
    bump_k, bump_s = pulse(KICKS, t, 0.08), pulse(SNARES, t, 0.06)
    draw_menace(rgb, t, bump_k)
    draw_texts(rgb, t)
    hud(rgb, t)
    # hits: radial zoom blur, ink/inverted frames, shake, flash
    ox = oy = ca = 0.0; flash = 0.0
    for h in HITS:
        lt = t - h['t']
        if lt < 0 or lt > 1.0: continue
        if lt < 0.18:
            k = 1 - lt / 0.18; acc = rgb.copy(); n = 5
            for i in range(1, n):
                acc += cv2.warpAffine(rgb, cv2.getRotationMatrix2D((W / 2, H * 0.45), 0, 1 + 0.04 * k * i), (W, H), borderMode=cv2.BORDER_REFLECT)
            rgb = acc / n
        if lt < (3 if h['big'] else 2) / FPS:
            l = rgb.mean(2, keepdims=True); bw = (l > 0.45).astype(np.float32)
            rgb = np.repeat(1 - bw, 3, 2) if h['mode'] == 'inv' else bw * PAPER + (1 - bw) * INK
        amp = (34 if h['big'] else 18) * math.exp(-lt * 8)
        ox += amp * math.sin(t * 83); oy += amp * math.cos(t * 61); ca += amp * 0.5
        flash = max(flash, (0.75 if h['big'] else 0.35) * math.exp(-lt / 0.07))
    if sh.get('inkhit') and t - sh['t0'] < 1.5 / FPS:
        l = rgb.mean(2, keepdims=True); bw = (l > 0.45).astype(np.float32); rgb = bw * PAPER + (1 - bw) * INK
    # the beat: zoom bump on kicks, a smaller one + colour split on snares
    z = 1.0 + 0.03 * min(bump_k, 1.5) + 0.016 * min(bump_s, 1.5)
    ca += 5 * min(bump_s, 1)
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z); M[:, 2] += (ox, oy)
    if abs(z - 1) > 1e-3 or abs(ox) + abs(oy) > 0.3:
        rgb = cv2.warpAffine(rgb, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    if ca > 1:
        d = int(min(ca, 24)); rgb[..., 0] = np.roll(rgb[..., 0], d, 1); rgb[..., 2] = np.roll(rgb[..., 2], -d, 1)
    if flash > 0.01: rgb = rgb + (PAPER - rgb) * min(flash, 1)
    if t < 0.2: rgb = rgb + (PAPER - rgb) * (1 - t / 0.2) ** 2           # open on a white hit
    for d0, d1 in DIM:
        if d0 <= t < d1: rgb = rgb * 0.12
    # bloom + vignette
    sm = cv2.resize(rgb, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    br = cv2.GaussianBlur(np.maximum(sm - 0.7, 0), (0, 0), 8)
    rgb = np.clip(rgb + cv2.resize(br, (W, H), interpolation=cv2.INTER_LINEAR) * 0.9, 0, 1) * VIG
    return rgb.astype(np.float32)

def frame(fi):
    t = fi / FPS
    if t >= FREEZE: rgb = tbc(frame_core(FREEZE - 1 / FPS), t)
    else: rgb = frame_core(t)
    rgb = rgb + GRAIN[fi % 4]
    rgb = rgb * clamp((DUR - t) / 0.4)
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)

# ---------------------------------------------------------------- main
def stills(times):
    d = os.path.join(HERE, 'stills_v2'); os.makedirs(d, exist_ok=True); th = []
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
    tmp = os.path.join(HERE, '_v2_video.mp4'); out = os.path.join(ROOT, 'mountain-tim-short-v2.mp4')
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p',
                          '-movflags', '+faststart', tmp], stdin=subprocess.PIPE)
    with Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        for i, fr in enumerate(pool.imap(frame, range(N), chunksize=3)):
            p.stdin.write(fr.tobytes())
            if i % 90 == 0: print(f'frame {i}/{N}', flush=True)
    p.stdin.close(); p.wait()
    if p.returncode: raise SystemExit(f'ffmpeg video failed {p.returncode}')
    subprocess.run([ff, '-y', '-v', 'error', '-i', tmp, '-i', os.path.join(HERE, 'music_v2.wav'), '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-af', 'loudnorm=I=-13:TP=-1.0:LRA=9,aresample=48000', '-c:a', 'aac', '-b:a', '192k',
                    '-t', f'{DUR:.3f}', '-movflags', '+faststart', out], check=True)
    os.remove(tmp); print('wrote', out)

if __name__ == '__main__':
    if sys.argv[1] == 'stills': stills([float(x) for x in sys.argv[2].split(',')])
    else: video()
