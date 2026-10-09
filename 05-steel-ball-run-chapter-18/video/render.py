"""Steel Ball Run, chapter 18 — Johnny, Gyro, and Mountain Tim.

46.15 s vertical Short, 1080x1920, 30 fps, on a 156 BPM grid (120 beats).
Not a fight. Tim has been matching their pace for three hours. When he gets
close, the Boom Boom magnetism wakes up and all three pull on each other.
If they meet, the iron in their blood will finish it. Gyro throws a steel
ball to knock him off and warn him, then splits his own body along a rope
so the three of them cannot occupy the same point.

  0-16    the chase. 15 km left, and magnetism if he gets near
  16-40   the pull. Johnny, then Gyro, then all three
  40-64   the name. it started when Mountain Tim got close
  64-90   the warning. the steel ball goes out and comes back
  90-120  the rope. too close, so Gyro takes himself apart

The score is video/music.py. Dust in the chase, purple while the magnet
climbs, green on the spin. A meter fills until the moment they would meet.

Usage:  python render.py stills 0.4,6.2,16.2
        python render.py video
"""
import os, sys, math, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAN = os.path.join(ROOT, 'panels')
W, H, FPS = 1080, 1920, 30
BPM = 156.0
BEAT = 60.0 / BPM
def b(n): return n * BEAT
DUR = b(120)
N = int(round(DUR * FPS))
FD = 'C:/Windows/Fonts/' if os.name == 'nt' else os.path.join(os.path.dirname(ROOT), 'fonts') + '/'
cv2.setNumThreads(1)

def clamp(u, a=0.0, c=1.0): return min(max(u, a), c)
def eout(u): u = clamp(u); return 1 - (1 - u) ** 3
def ein(u): u = clamp(u); return u ** 3
def eio(u): u = clamp(u); return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2
def lerp(a, c, u): return a + (c - a) * u
def hexc(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)

INK = hexc('#07060A')
PAPER = hexc('#F4EFE6')
PINK = hexc('#FF4FA3')
GREEN = hexc('#3DDC4A')
DUST = hexc('#C4A574')
PURPLE = hexc('#6A3488')
BLOOD = hexc('#9A1E28')
SPIN = hexc('#2E9A45')

# A 9:16 window. h is in page pixels; width follows the frame.
def win(x, y, h):
    return [x, y, h * W / H, h]

# ---------------------------------------------------------------- pages
PAGES = {}
def page(n):
    if n not in PAGES:
        im = Image.open(os.path.join(PAN, n + '.jpg')).convert('RGB')
        a = np.asarray(im, np.float32) / 255
        s = 2.0
        up = cv2.resize(a, None, fx=s, fy=s, interpolation=cv2.INTER_LANCZOS4)
        bl = cv2.GaussianBlur(up, (0, 0), 1.1)
        up = np.clip(up + 0.45 * (up - bl), 0, 1)
        PAGES[n] = (up.astype(np.float32), s)
    return PAGES[n]

def view_matrix(rect, cx=None, cy=None):
    x, y, w, h = rect
    k = max(W / w, H / h)
    cx = W / 2 if cx is None else cx
    cy = H / 2 if cy is None else cy
    return np.float32([[k, 0, cx - k * (x + w / 2)], [0, k, cy - k * (y + h / 2)]]), k

def warp_page(n, M):
    up, s = page(n)
    Ms = M.copy(); Ms[:, :2] /= s
    return cv2.warpAffine(up, Ms, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

def lerp_rect(a, c, u):
    return [lerp(p, q, u) for p, q in zip(a, c)]

def grade(rgb, g):
    out = np.clip((rgb - 0.5) * 1.08 + 0.5, 0, 1)
    if not g: return out
    lum = out.mean(2, keepdims=True)
    sh = np.clip((0.58 - lum) / 0.58, 0, 1) ** 1.15
    tint = {'dust': DUST, 'pull': PURPLE, 'blood': BLOOD, 'spin': SPIN}[g]
    k = {'dust': 0.28, 'pull': 0.34, 'blood': 0.22, 'spin': 0.16}[g]
    return np.clip(out * (1 - k * sh) + tint * (k * sh), 0, 1)

# ---------------------------------------------------------------- type
_F, _SP = {}, {}
def font(name, size):
    k = (name, size)
    if k not in _F: _F[k] = ImageFont.truetype(FD + name, size)
    return _F[k]
IMP, LAB, MONO = 'impact.ttf', 'bahnschrift.ttf', 'consolab.ttf'

def sprite(s, fnt, size, fill=(1, 1, 1), stroke=0, sfill=(0, 0, 0), trk=0.0, slant=0.0):
    key = (s, fnt, size, tuple(np.round(fill, 3)), stroke, tuple(np.round(sfill, 3)), trk, slant)
    if key in _SP: return _SP[key]
    f = font(fnt, size); sw = int(stroke * size)
    asc, desc = f.getmetrics()
    adv = [f.getlength(ch) + trk * size for ch in s] or [0]
    Wd = int(sum(adv) - (trk * size if s else 0) + 2 * sw + size * 0.3)
    Hd = int(asc + desc + 2 * sw + 6)
    img = Image.new('RGBA', (max(Wd, 2), max(Hd, 2)), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    fc = tuple(int(v * 255) for v in fill) + (255,)
    sc = tuple(int(v * 255) for v in sfill) + (255,)
    x = sw + size * 0.1
    for ch, a in zip(s, adv):
        d.text((x, sw + 2), ch, font=f, fill=fc, stroke_width=sw, stroke_fill=sc); x += a
    a = np.asarray(img, np.float32) / 255
    if slant:
        sh = math.tan(math.radians(slant)); M = np.float32([[1, -sh, max(sh, 0) * Hd], [0, 1, 0]])
        a = cv2.warpAffine(a, M, (int(Wd + abs(sh) * Hd), Hd), flags=cv2.INTER_LINEAR)
    a[..., :3] *= a[..., 3:4]
    _SP[key] = a
    return a

def blit(rgb, spr, cx, cy, sc=1.0, rot=0.0, a=1.0, blur=0.0):
    if sc <= 0.01 or a <= 0.01: return
    if blur > 0.4:
        p = int(blur * 3) + 2
        spr = cv2.GaussianBlur(np.pad(spr, ((p, p), (p, p), (0, 0))), (0, 0), blur)
    h, w = spr.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, sc); M[:, 2] += (cx - w / 2, cy - h / 2)
    cs = np.float32([[0, 0], [w, 0], [w, h], [0, h]]) @ M[:, :2].T + M[:, 2]
    bx, by = int(max(0, cs[:, 0].min() - 2)), int(max(0, cs[:, 1].min() - 2))
    bx1, by1 = int(min(W, cs[:, 0].max() + 2)), int(min(H, cs[:, 1].max() + 2))
    if bx1 - bx < 2 or by1 - by < 2: return
    M[:, 2] -= (bx, by)
    o = cv2.warpAffine(spr, M, (bx1 - bx, by1 - by), flags=cv2.INTER_LINEAR)
    reg = rgb[by:by1, bx:bx1]; al = o[..., 3:4] * a
    reg[:] = reg * (1 - al) + o[..., :3] * a

def slab(rgb, cx, cy, w, h, col, skew=-14.0, a=1.0, u=1.0):
    sh = math.tan(math.radians(skew)) * h / 2
    x0, x1 = cx - w / 2, cx + w / 2
    x1 = lerp(x0, x1, eout(u))
    pts = np.float32([[x0 - sh, cy - h / 2], [x1 - sh, cy - h / 2], [x1 + sh, cy + h / 2], [x0 + sh, cy + h / 2]])
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.int32(pts * 16)], 255, cv2.LINE_AA, 4)
    m = (m.astype(np.float32) / 255 * a)[..., None]
    rgb[:] = rgb * (1 - m) + col * m

# ---------------------------------------------------------------- timeline
S, IMPACT, SHAKE, FLASH, TEXT = [], [], [], [], []
def shot(t0, t1, kind, **kw): S.append(dict(t0=t0, t1=t1, kind=kind, **kw))
def T(t, s, x, y, size, fnt=IMP, end=None, ent='slam', **kw):
    TEXT.append(dict(t=t, s=s, x=x, y=y, size=size, fnt=fnt, end=end, ent=ent, **kw))

# 1  three hours, same pace. the road is empty, then the pair.
shot(b(0), b(8), 'bleed', p='01', r=win(30, 8, 360), r1=win(720, 0, 380), grade='dust', lines='gallop', bob=True)
T(b(0.6), '3 HOURS', W / 2, 220, 72, fnt=LAB, ent='type', end=b(4.2), trk=0.2, fill=(1, 0.95, 0.86))
T(b(4.4), '15 KM', W / 2, 220, 96, fnt=LAB, ent='type', end=b(7.6), trk=0.22)
# 2  Gyro sees who has been keeping the pace
shot(b(8), b(12), 'bleed', p='02', r=win(160, 30, 700), r1=win(40, 720, 280), grade='dust', ent='whip', bob=True)
T(b(8.2), 'SAME PACE', W / 2, 250, 70, fnt=LAB, ent='type', end=b(12), trk=0.16)
# 3  not the Boom Boom family. Mountain Tim, already on the rocks.
shot(b(12), b(16), 'bleed', p='04', r=win(350, 0, 500), r1=win(370, 10, 460), grade='dust', ent='punch', lines='radial')
T(b(12.2), 'MOUNTAIN TIM', W / 2, 1580, 78, end=b(16), slant=-7, stroke=0.04)
SHAKE += [(b(12), 12, 8)]; FLASH += [(b(12), 0.45, 0.12, PAPER)]

# 4  Johnny's harness answers first. the bubble on the page says the line.
shot(b(16), b(22), 'bleed', p='05', r=win(180, 40, 620), r1=win(220, 60, 560), grade='pull', ent='whip')
FLASH += [(b(16), 0.35, 0.12, PURPLE)]
# 5  the onlookers think the chaser fell. he did not.
shot(b(22), b(26), 'bleed', p='07', r=win(200, 40, 520), r1=win(240, 60, 460), grade='pull', ent='punch')
# 6  the metal from the harness comes for Gyro too
shot(b(26), b(32), 'bleed', p='08', r=win(20, 40, 400), r1=win(30, 500, 500), grade='pull', ent='whip')
T(b(27.5), 'GYRO TOO', W / 2, 250, 90, end=b(32), slant=-6, stroke=0.04, fill=tuple(PINK))
SHAKE += [(b(28), 14, 8)]
# 7  it is not a new enemy. the old magnetism is awake.
shot(b(32), b(36), 'bleed', p='09', r=win(260, 0, 400), r1=win(280, 10, 370), grade='pull', ent='whip')
T(b(32.3), 'ME TOO', W / 2, 1680, 110, end=b(36), slant=-8, stroke=0.04)
FLASH += [(b(32), 0.35, 0.12, PURPLE)]
# 8  Johnny: it only started once he got close.
shot(b(36), b(40), 'bleed', p='11', r=win(370, 0, 420), r1=win(390, 8, 390), grade='pull', ent='whip')
T(b(36.3), 'HE GOT CLOSE', W / 2, 1700, 64, fnt=LAB, ent='type', end=b(40), trk=0.08)
# 9  the page names him. crop keeps his own words.
shot(b(40), b(44), 'bleed', p='11', r=win(390, 520, 460), r1=win(400, 540, 430), grade='pull', ent='punch')
FLASH += [(b(40), 0.4, 0.14, PAPER)]
# 10  the three of them, pulling on each other
shot(b(44), b(48), 'bleed', p='12', r=win(0, 20, 380), r1=win(400, 10, 390), grade='pull', ent='whip', lines='gallop')
T(b(44.3), 'ALL THREE', W / 2, 1680, 100, end=b(48), slant=-7, stroke=0.04)
# 11  closer means stronger. the iron in the blood.
shot(b(48), b(56), 'bleed', p='13', r=win(400, 0, 800), r1=win(430, 0, 760), grade='blood', lines='radial')
T(b(49), 'EXPLODE', W / 2, 1620, 130, end=b(56), slant=-8, stroke=0.05, fill=(1, 0.86, 0.84))
SHAKE += [(b(48), 10, 6)]; FLASH += [(b(48), 0.4, 0.16, PURPLE)]

# 12  the ball is a warning, so Tim gets off before he understands too late
shot(b(56), b(64), 'bleed', p='16', r=win(280, 540, 460), r1=win(360, 600, 380), grade='spin', ent='whip')
T(b(56.4), 'TELL HIM', W / 2, 240, 100, end=b(64), slant=-7, fill=tuple(GREEN), stroke=0.04)
FLASH += [(b(56), 0.4, 0.12, PAPER)]
# 13  it leaves, hits the rock, and has to come back
shot(b(64), b(76), 'bleed', p='17', r=win(0, 260, 720), r1=win(20, 280, 660), grade='spin', ent='whip')
# 14  the iron in the rock comes with it
shot(b(76), b(82), 'bleed', p='19', r=win(0, 450, 540), r1=win(10, 480, 490), grade='spin', ent='punch')
T(b(76.3), 'BRACE', W / 2, 250, 120, end=b(82), slant=-6, stroke=0.05)
SHAKE += [(b(76), 16, 7)]; FLASH += [(b(76), 0.45, 0.08, GREEN)]
# 15  off the horse, and already too close to speak
shot(b(82), b(90), 'bleed', p='20', r=win(0, 240, 500), r1=win(16, 260, 460), grade='pull', ent='whip')
T(b(82.3), 'TOO CLOSE', W / 2, 1680, 100, end=b(90), slant=-7, stroke=0.045, fill=tuple(PINK))
SHAKE += [(b(82), 12, 7)]
# 16  Tim's body is in the air because the pull won, not because anyone struck him
shot(b(90), b(98), 'bleed', p='21', r=win(450, 0, 780), r1=win(500, 0, 740), grade='pull', ent='whip')
T(b(90.4), 'TOO STRONG', W / 2, 1700, 80, fnt=LAB, ent='type', end=b(98), trk=0.1)
# 17  Gyro throws a rope and separates himself, so the three cannot meet
shot(b(98), b(112), 'bleed', p='23', r=win(120, 0, 790), r1=win(460, 0, 750), grade='spin', ent='whip')
T(b(99), 'THE ROPE', W / 2, 1680, 110, end=b(110), slant=-7, fill=tuple(GREEN), stroke=0.045)
# 18  title, low, where the page is open sky
shot(b(112), DUR + 0.05, 'bleed', p='23', r=win(400, 20, 760), r1=win(380, 0, 790), grade='spin', ent='none')
T(b(112.2), 'STEEL BALL RUN', W / 2, 1450, 64, fnt=LAB, ent='type', trk=0.14, fill=tuple(GREEN))
T(b(113.2), 'CHAPTER 18', W / 2, 1550, 52, fnt=LAB, ent='type', trk=0.26)
T(b(114.4), 'DON\'T MEET', W / 2, 1680, 78, end=None, slant=-7, stroke=0.04)
FLASH += [(b(112), 0.55, 0.2, PAPER)]

# ---------------------------------------------------------------- textures
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx / W - .5) * 2) ** 2 * 0.75 + ((_yy / H - .5) * 2) ** 2 * 0.55)
VIG = (1 - 0.5 * np.clip((_r - 0.55) / 0.85, 0, 1) ** 1.4).astype(np.float32)[..., None]
_g = np.random.default_rng(7)
GRAIN = [cv2.resize(_g.normal(0, 0.018, (H // 2, W // 2)).astype(np.float32), (W, H))[..., None] for _ in range(4)]
del _r

def speed_lines(rgb, t, kind, seed=1):
    r = np.random.default_rng(seed * 997 + int(t * FPS) // 2)
    lay = np.zeros((H, W), np.float32)
    if kind == 'gallop':
        for _ in range(46):
            y = int(r.uniform(0, H)); x = int(r.uniform(-200, W))
            leng = int(r.uniform(180, 700))
            cv2.line(lay, (x, y), (x + leng, y + int(r.uniform(-8, 8))), 1.0, int(r.uniform(2, 7)), cv2.LINE_AA)
        rgb[:] = np.clip(rgb * (1 - 0.22 * lay[..., None]) + PINK * (0.28 * lay[..., None]), 0, 1)
    else:
        cx, cy = W * 0.5, H * 0.42
        for _ in range(64):
            a = r.uniform(0, 2 * math.pi)
            r0, r1 = r.uniform(280, 700), 0
            r1 = r0 + r.uniform(280, 900)
            p0 = (int(cx + r0 * math.cos(a)), int(cy + r0 * math.sin(a)))
            p1 = (int(cx + r1 * math.cos(a)), int(cy + r1 * math.sin(a)))
            cv2.line(lay, p0, p1, 1.0, int(r.uniform(2, 8)), cv2.LINE_AA)
        rgb[:] = np.clip(rgb * (1 - 0.55 * lay[..., None]) + PAPER * (0.5 * lay[..., None]), 0, 1)

def render_bleed(sh, t):
    u = clamp((t - sh['t0']) / (sh['t1'] - sh['t0']))
    ent = sh.get('ent', 'none')
    rect = lerp_rect(sh['r'], sh.get('r1', sh['r']), eout(u) if ent == 'zoomout' else eio(u))
    lt = t - sh['t0']
    if ent == 'punch':
        k = lerp(1.22, 1.0, eout(lt / 0.2))
        x, y, w, h = rect
        rect = [x + w * (1 - 1 / k) / 2, y + h * (1 - 1 / k) / 2, w / k, h / k]
    M, _ = view_matrix(rect)
    if sh.get('bob'):
        M = M.copy()
        M[1, 2] += 16 * math.sin(t * 2 * math.pi * 3.1)
    return warp_page(sh['p'], M)

def meter(rgb, t):
    """Magnetism. Empty on the chase, full when the three of them would meet."""
    if not (b(16) - 0.05 <= t < b(78)): return
    u = clamp((t - b(16)) / (b(56) - b(16))) ** 1.35
    a = clamp((t - b(16)) / 0.2)
    if t >= b(48): u = clamp(u + 0.04 * math.sin(t * 46))
    x0, y0, x1, y1 = 46, 520, 78, 1500
    cv2.rectangle(rgb, (x0 - 8, y0 - 8), (x1 + 8, y1 + 8), tuple(float(v) for v in INK), -1, cv2.LINE_AA)
    col = BLOOD if u > 0.92 else PURPLE
    fill_y = int(lerp(y1, y0, u))
    cv2.rectangle(rgb, (x0, fill_y), (x1, y1), tuple(float(v) for v in col * a), -1, cv2.LINE_AA)
    blit(rgb, sprite('MAG', MONO, 28, fill=(1, 1, 1), trk=0.08), 62, 1560, a=a)
    if u > 0.92:
        blit(rgb, sprite('CRIT', MONO, 26, fill=tuple(BLOOD)), 70, 470, a=0.5 + 0.5 * math.sin(t * 30))

def draw_texts(rgb, t):
    for it in TEXT:
        lt = t - it['t']
        if lt < 0 or (it.get('end') is not None and t > it['end']): continue
        kw = dict(fill=it.get('fill', (1, 1, 1)), stroke=it.get('stroke', 0.0), sfill=(0.02, 0.01, 0.03),
                  trk=it.get('trk', 0.0), slant=it.get('slant', 0.0))
        s = it['s']
        if it['ent'] == 'type':
            n = max(1, int(len(s) * clamp(lt / max(len(s) * 0.045, 0.25))))
            spr_full = sprite(s, it['fnt'], it['size'], **kw)
            spr = sprite(s[:n], it['fnt'], it['size'], **kw)
            x = it['x'] - spr_full.shape[1] / 2 + spr.shape[1] / 2
            blit(rgb, spr, x, it['y'])
            continue
        spr = sprite(s, it['fnt'], it['size'], **kw)
        sc, a, bl = 1.0, 1.0, 0.0
        if it['ent'] == 'slam':
            e = eout(lt / 0.14); sc = lerp(2.2, 1, e); a = clamp(lt / 0.05); bl = 7 * (1 - e)
        if it.get('end') is not None: a *= clamp((it['end'] - t) / 0.1)
        blit(rgb, spr, it['x'], it['y'], sc, it.get('rot', 0), a, bl)

WHIP = 0.14
def shot_at(t):
    for i, s in enumerate(S):
        if s['t0'] <= t < s['t1']: return i
    return len(S) - 1

def whipped(img, dx):
    k = int(min(abs(dx) * 0.35, 140)) * 2 + 1
    o = cv2.warpAffine(img, np.float32([[1, 0, dx], [0, 1, 0]]), (W, H), borderMode=cv2.BORDER_REFLECT)
    return cv2.blur(o, (k, 1)) if k > 3 else o

def frame(fi):
    t = fi / FPS
    si = shot_at(t); sh = S[si]
    rgb = grade(render_bleed(sh, t), sh.get('grade'))
    if sh.get('lines'): speed_lines(rgb, t, sh['lines'], seed=si + 1)
    nxt = S[si + 1] if si + 1 < len(S) else None
    if nxt and nxt.get('ent') == 'whip' and t > nxt['t0'] - WHIP:
        rgb = whipped(rgb, -ein((t - (nxt['t0'] - WHIP)) / WHIP) * W * 0.55)
    if sh.get('ent') == 'whip' and t < sh['t0'] + WHIP:
        rgb = whipped(rgb, (1 - eout((t - sh['t0']) / WHIP)) * W * 0.55)
    meter(rgb, t)
    draw_texts(rgb, t)
    for ts, nfr, mode in IMPACT:
        if ts <= t < ts + nfr / FPS:
            l = rgb.mean(2, keepdims=True)
            bw = (l > 0.45).astype(np.float32)
            rgb = (1 - bw) if mode == 'inv' else bw * PAPER + (1 - bw) * INK
            if rgb.shape[-1] == 1: rgb = np.repeat(rgb, 3, 2)
            break
    ox = oy = 0.0; ca = 0.0
    for ts, amp, dc in SHAKE:
        if ts <= t < ts + 0.8:
            k = amp * math.exp(-(t - ts) * dc)
            ox += k * math.sin(t * 90); oy += k * math.cos(t * 67); ca += k * 0.45
    if abs(ox) + abs(oy) > 0.4:
        rgb = cv2.warpAffine(rgb, np.float32([[1.02, 0, ox - W * 0.01], [0, 1.02, oy - H * 0.01]]),
                             (W, H), borderMode=cv2.BORDER_REFLECT)
    if ca > 1.2:
        d = int(min(ca, 18)); rgb = rgb.copy()
        rgb[..., 0] = np.roll(rgb[..., 0], d, 1); rgb[..., 2] = np.roll(rgb[..., 2], -d, 1)
    for ts, pk, dc, col in FLASH:
        if ts <= t < ts + 0.6:
            f = pk * math.exp(-(t - ts) / dc)
            if f > 0.01: rgb = rgb + (col - rgb) * min(f, 1)
    rgb = np.clip(rgb, 0, 1) * VIG + GRAIN[si % 4]
    rgb *= clamp(t / 0.25) * clamp((DUR - t) / 0.45)
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)

def stills(times):
    d = os.path.join(HERE, 'stills'); os.makedirs(d, exist_ok=True)
    th = []
    for tt in times:
        fr = frame(int(round(tt * FPS)))
        cv2.imwrite(os.path.join(d, f'{tt:06.2f}.png'), fr[..., ::-1])
        s_ = cv2.resize(fr[..., ::-1], (270, 480), interpolation=cv2.INTER_AREA)
        cv2.putText(s_, f'{tt:.2f}', (6, 24), 0, 0.7, (0, 255, 255), 2)
        th.append(s_)
        print(tt, flush=True)
    while len(th) % 6: th.append(np.zeros_like(th[0]))
    cv2.imwrite(os.path.join(d, 'contact.jpg'), np.vstack([np.hstack(th[i:i + 6]) for i in range(0, len(th), 6)]))
    print('contact', os.path.join(d, 'contact.jpg'))

def video():
    import imageio_ffmpeg
    from multiprocessing import Pool
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    out = os.path.join(ROOT, 'mountain-tim-short.mp4')
    tmp = os.path.join(HERE, '_video.mp4')
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                          '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmp], stdin=subprocess.PIPE)
    with Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        for i, fr in enumerate(pool.imap(frame, range(N), chunksize=4)):
            p.stdin.write(fr.tobytes())
            if i % 120 == 0: print(f'frame {i}/{N}', flush=True)
    p.stdin.close(); p.wait()
    if p.returncode: raise SystemExit(f'ffmpeg video failed {p.returncode}')
    wav = os.path.join(HERE, 'music.wav')
    subprocess.run([ff, '-y', '-v', 'error', '-i', tmp, '-i', wav, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.0:LRA=11,aresample=48000',
                    '-c:a', 'aac', '-b:a', '192k', '-t', f'{DUR:.3f}', '-movflags', '+faststart', out], check=True)
    os.remove(tmp)
    print('wrote', out)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'stills':
        stills([float(x) for x in sys.argv[2].split(',')])
    else:
        video()
