"""Gokurakugai Sanbandoori no Ken (極楽街三番通りの件) - 20 s action Short, 1080x1920, 30 fps.

Look (from video-samples-references/action): cinematic monochrome with a cool tint, lantern-red monochrome sections,
pure black/white "ink" impact frames, whip-pan motion blur, speed lines, sparks + anamorphic flares on gunshots,
rack-focus entries, film grain. Al's line "I won't even need three minutes!!" becomes a stopwatch over the fight.
Every cut sits on a 150 BPM grid (BPM / OFFSET below), so a real song can be dropped in later by retiming those two.

Usage:  python render.py stills 1,5,12          -> ./stills/<t>.png + contact.jpg
        python render.py video                 -> ../gokurakugai-short.mp4 (no audio) and
                                                  ../gokurakugai-short-music.mp4 (with music.wav from music.py)
"""
import os, sys, math, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAN = os.path.join(ROOT, 'panels')
W, H, FPS = 1080, 1920, 30
BPM, OFFSET = 150.0, 0.0
BEAT = 60.0 / BPM
def b(n): return OFFSET + n * BEAT
DUR = 20.0
N = int(DUR * FPS)
FD = 'C:/Windows/Fonts/' if os.name == 'nt' else os.path.join(os.path.dirname(ROOT), 'fonts') + '/'
cv2.setNumThreads(1)

# ---------------------------------------------------------------- easing
def clamp(u, a=0.0, c=1.0): return min(max(u, a), c)
def eout(u): u = clamp(u); return 1 - (1 - u) ** 3
def ein(u): u = clamp(u); return u ** 3
def eio(u): u = clamp(u); return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2
def eback(u): u = clamp(u); c1 = 2.2; return 1 + (c1 + 1) * (u - 1) ** 3 + c1 * (u - 1) ** 2
def lerp(a, c, u): return a + (c - a) * u
def hexc(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)

RED, RED2, GOLD, INK, PAPER = hexc('#D7262B'), hexc('#FF4A3D'), hexc('#FFB547'), hexc('#07080B'), hexc('#ECEFF1')
GRADES = {   # lum -> colour ramps (shadow, mid, highlight)
    'cool': (hexc('#06080C'), hexc('#5B6670'), hexc('#E9EEF0')),
    'red': (hexc('#120103'), hexc('#B0141B'), hexc('#FFE1DA')),
    'night': (hexc('#04060A'), hexc('#2E3B4C'), hexc('#C9D6E2')),
}

# ---------------------------------------------------------------- pages
PAGES = {}
def page(n):
    if n not in PAGES:
        im = Image.open(os.path.join(PAN, n + '.webp'))
        color = n == '01'
        a = np.asarray(im.convert('RGB' if color else 'L'), np.float32) / 255
        if not color: a = np.clip((a - 0.03) / 0.92, 0, 1)
        s = 2.0
        up = cv2.resize(a, None, fx=s, fy=s, interpolation=cv2.INTER_LANCZOS4)
        bl = cv2.GaussianBlur(up, (0, 0), 1.3); up = np.clip(up + 0.6 * (up - bl), 0, 1)
        PAGES[n] = (up.astype(np.float32), s)
    return PAGES[n]

def view_matrix(rect, ow, oh, cx=None, cy=None):
    """page rect (x,y,w,h) -> cover-fit affine into an ow x oh box centred at (cx,cy)."""
    x, y, w, h = rect
    k = max(ow / w, oh / h)
    cx = W / 2 if cx is None else cx; cy = H / 2 if cy is None else cy
    return np.float32([[k, 0, cx - k * (x + w / 2)], [0, k, cy - k * (y + h / 2)]]), k

def warp_page(n, M, size=(W, H), border=cv2.BORDER_REPLICATE):
    up, s = page(n)
    Ms = M.copy(); Ms[:, :2] /= s
    return cv2.warpAffine(up, Ms, size, flags=cv2.INTER_LINEAR, borderMode=border)

def lerp_rect(a, c, u): return [lerp(p, q, u) for p, q in zip(a, c)]

# ---------------------------------------------------------------- text sprites
_F, _SP = {}, {}
def font(name, size):
    k = (name, size)
    if k not in _F: _F[k] = ImageFont.truetype(FD + name, size)
    return _F[k]
JPB, IMP, MONO, LAB = 'YuGothB.ttc', 'impact.ttf', 'consolab.ttf', 'bahnschrift.ttf'

def sprite(s, fnt, size, fill=(1, 1, 1), stroke=0, sfill=(0, 0, 0), trk=0.0, vertical=False, slant=0.0):
    key = (s, fnt, size, tuple(fill), stroke, tuple(sfill), trk, vertical, slant)
    if key in _SP: return _SP[key]
    f = font(fnt, size); sw = int(stroke * size)
    asc, desc = f.getmetrics()
    if vertical:
        Wd, Hd = int(size * 1.3 + 2 * sw), int(len(s) * size * 1.05 + 2 * sw + size * 0.3)
    else:
        adv = [f.getlength(ch) + trk * size for ch in s]
        Wd, Hd = int(sum(adv) - trk * size + 2 * sw + size * 0.2), int(asc + desc + 2 * sw + 4)
    img = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    fc = tuple(int(v * 255) for v in fill) + (255,); sc = tuple(int(v * 255) for v in sfill) + (255,)
    if vertical:
        for i, ch in enumerate(s):
            d.text((Wd / 2, sw + size * 0.15 + i * size * 1.05 + size / 2), ch, font=f, fill=fc, anchor='mm',
                   stroke_width=sw, stroke_fill=sc)
    else:
        x = sw + size * 0.1
        for ch, a in zip(s, adv):
            d.text((x, sw + 2), ch, font=f, fill=fc, stroke_width=sw, stroke_fill=sc); x += a
    a = np.asarray(img, np.float32) / 255
    if slant:
        sh = math.tan(math.radians(slant)); M = np.float32([[1, -sh, sh * Hd], [0, 1, 0]])
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

def slab(rgb, cx, cy, w, h, col, skew=-12.0, a=1.0, u=1.0, from_left=True):
    """parallelogram colour slab, wiping in along x as u goes 0->1."""
    sh = math.tan(math.radians(skew)) * h / 2
    x0, x1 = cx - w / 2, cx + w / 2
    if from_left: x1 = lerp(x0, x1, eout(u))
    else: x0 = lerp(x1, x0, eout(u))
    pts = np.float32([[x0 - sh, cy - h / 2], [x1 - sh, cy - h / 2], [x1 + sh, cy + h / 2], [x0 + sh, cy + h / 2]])
    m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [np.int32(pts * 16)], 255, cv2.LINE_AA, 4)
    m = (m.astype(np.float32) / 255 * a)[..., None]
    rgb[:] = rgb * (1 - m) + col * m

# ---------------------------------------------------------------- shot list
S = []
def shot(t0, t1, kind, **kw): S.append(dict(t0=t0, t1=t1, kind=kind, **kw))
IMPACT = []      # (time, frames, mode)  mode: 'ink' | 'inv'
SHAKE = []       # (time, amp, decay)
FLASH = []       # (time, peak, decay, colour)
FLARE = []       # (time, x, y)
SPARK = []       # (time, x, y, seed)
TEXT = []        # dicts, absolute times

def T(t, s, x, y, size, fnt=JPB, end=None, ent='slam', **kw):
    TEXT.append(dict(t=t, s=s, x=x, y=y, size=size, fnt=fnt, end=end, ent=ent, **kw))

# 1  night street - rack focus in, cool
shot(b(0), b(4), 'card', p='02', r=[300, 0, 659, 470], cy=820, kz=1.10, f=(0.75, 0.4), grade='night', focus=1.2)
T(b(0) + 0.3, '極楽街', 130, 300, 120, vertical=True, ent='fade', end=b(4) - 0.1, fill=(0.92, 0.94, 0.96))
T(b(1), 'A DULL SOUND ECHOED', 650, 1300, 46, fnt=LAB, ent='type', end=b(4) - 0.1, trk=0.12)
T(b(1) + 0.45, 'THROUGH THE NIGHT...', 650, 1360, 46, fnt=LAB, ent='type', end=b(4) - 0.1, trk=0.12)
T(b(3), 'ゴッ', 820, 520, 190, ent='slam', end=b(4), fill=(1, 1, 1), stroke=0.06, rot=-10)
IMPACT += [(b(3), 2, 'ink')]; SHAKE += [(b(3), 20, 9)]
# 2  the beating - three hits on the beat
shot(b(4), b(5), 'card', p='02', r=[180, 505, 330, 155], cy=960, kz=1.15, f=(0.3, 0.5), grade='cool', ent='punch')
shot(b(5), b(6), 'card', p='02', r=[430, 660, 280, 200], cy=960, kz=1.2, f=(0.5, 0.5), grade='cool', ent='punch')
shot(b(6), b(8), 'bleed', p='02', r=[40, 880, 330, 520], r1=[90, 960, 250, 445], grade='red', ent='punch')
T(b(6) + 0.02, 'ゴッ!!', 700, 1450, 230, end=b(8), fill=(1, 1, 1), stroke=0.07, rot=8)
IMPACT += [(b(4), 2, 'ink'), (b(5), 2, 'inv'), (b(6), 3, 'ink'), (b(7), 2, 'inv')]
SHAKE += [(b(4), 14, 10), (b(5), 14, 10), (b(6), 30, 7)]
# 3  the gate - tilt up, title
shot(b(8), b(14), 'bleed', p='03', r=[290, 270, 340, 604], r1=[230, 0, 500, 889], grade='cool', ent='whip', focus=0.5)
T(b(9), '極楽街', W / 2, 1540, 260, end=b(14), fill=(1, 1, 1), stroke=0.0, slabc=RED, track=0.15)
T(b(10), 'EXTRATERRITORIAL DISTRICT  //  MUGEN GROUP', W / 2, 1720, 34, fnt=LAB, ent='type', end=b(14), trk=0.15)
FLASH += [(b(8), 0.8, 0.12, PAPER)]
# 4  Tao
shot(b(14), b(18), 'bleed', p='08', r=[320, 760, 370, 640], r1=[350, 800, 330, 586], grade='red', ent='whip',
     name=('TAO', 'タオ', 'THE BOSS'))
IMPACT += [(b(14), 2, 'ink')]; SHAKE += [(b(14), 18, 8)]
# 5  Al
shot(b(18), b(22), 'bleed', p='17', r=[130, 380, 380, 676], r1=[170, 420, 340, 604], grade='cool', ent='whip',
     name=('AL', 'アル', 'PHYSICAL LABOUR'))
T(b(20), "I WON'T EVEN NEED", W / 2, 1560, 92, fnt=IMP, end=b(22), stroke=0.0, fill=(1, 1, 1), slant=-8, slabc=INK)
T(b(20, ) + BEAT, 'THREE MINUTES!!', W / 2, 1680, 120, fnt=IMP, end=b(22), fill=RED2, slant=-8)
IMPACT += [(b(18), 2, 'inv')]; SHAKE += [(b(18), 18, 8)]
# 6  troubleshooters - diagonal split
shot(b(22), b(26), 'split', a=dict(p='15', r=[420, 0, 420, 747], r1=[450, 20, 380, 676], grade='cool'),
     c=dict(p='15', r=[930, 80, 520, 925], r1=[960, 120, 470, 836], grade='red'), ent='whip')
T(b(22) + 0.1, 'WASSUP,', 760, 300, 120, fnt=IMP, end=b(26), slant=-8)
T(b(23), '万事解決', 250, 1420, 150, end=b(26), slabc=RED, stroke=0.0)
T(b(24), 'GOKURAKU DISTRICT', 300, 1560, 58, fnt=IMP, end=b(26), ent='type', slant=-8)
T(b(24) + 0.35, 'TROUBLESHOOTERS', 300, 1630, 58, fnt=IMP, end=b(26), ent='type', slant=-8, fill=RED2)
FLASH += [(b(22), 0.6, 0.1, PAPER)]
# 7  FIGHT - stopwatch runs
FIGHT0, FIGHT1 = b(26), b(42)
shot(b(26), b(28), 'card', p='16', r=[60, 0, 420, 300], cy=900, kz=1.18, f=(0.45, 0.5), grade='cool', ent='punch', lines=True)
T(b(26) + 0.05, 'ドッ', 820, 1380, 230, end=b(28), stroke=0.07, rot=-8)
shot(b(28), b(30), 'bleed', p='16', r=[540, 300, 330, 587], r1=[580, 320, 300, 533], grade='cool', ent='whip', lines=True)
shot(b(30), b(32), 'bleed', p='16', r=[180, 560, 470, 836], r1=[230, 600, 420, 747], grade='red', ent='punch', lines=True)
shot(b(32), b(35), 'bleed', p='18', r=[380, 0, 579, 1030], r1=[380, 370, 579, 1030], grade='cool', ent='whip', lines=True)
T(b(32) + 0.05, 'ガッ!!', 300, 1500, 250, end=b(35), stroke=0.07, rot=-6, fill=RED2)
shot(b(35), b(37), 'bleed', p='19', r=[80, 0, 616, 1095], r1=[140, 60, 520, 924], grade='cool', ent='punch', lines=True)
shot(b(37), b(40), 'bleed', p='19', r=[1090, 0, 380, 676], r1=[1120, 30, 340, 604], grade='red', ent='whip')
T(b(37) + 0.02, 'ドン', 820, 980, 210, end=b(40), stroke=0.07, rot=10)
T(b(38) + 0.02, 'ドン', 820, 1250, 210, end=b(40), stroke=0.07, rot=-6)
shot(b(40), b(42), 'card', p='19', r=[760, 790, 420, 305], cy=980, kz=1.2, f=(0.3, 0.5), grade='cool', ent='punch', lines=True)
IMPACT += [(b(26), 2, 'ink'), (b(30), 2, 'inv'), (b(32), 3, 'ink'), (b(33), 1, 'inv'), (b(35), 3, 'ink'),
           (b(35.5), 1, 'inv'), (b(36), 2, 'ink'), (b(40), 2, 'inv')]
SHAKE += [(b(26), 22, 8), (b(30), 28, 7), (b(32), 34, 6), (b(35), 30, 6), (b(37), 24, 9), (b(38), 24, 9), (b(40), 20, 8)]
SPARK += [(b(37), 620, 330, 1), (b(38), 620, 330, 2)]
FLARE += [(b(37), 620, 330), (b(38), 620, 330)]
FLASH += [(b(37), 0.5, 0.06, GOLD), (b(38), 0.5, 0.06, GOLD)]
# 8  freeze - "we do as we please"
shot(b(42), b(46), 'bleed', p='20', r=[740, 0, 616, 1095], r1=[790, 30, 560, 996], grade='cool', ent='whip',
     patches=[[848, 548, 290, 255, 'circle']])
T(b(43), 'WE DO AS', 470, 1080, 120, fnt=IMP, end=b(46), slant=-8)
T(b(43) + BEAT, 'WE PLEASE.', 470, 1210, 120, fnt=IMP, end=b(46), slant=-8, fill=RED2)
FLASH += [(b(42), 1.0, 0.18, PAPER)]
# 9  title - the colour cover
shot(b(46), DUR + 0.1, 'bleed', p='01', r=[480, 150, 420, 747], r1=[60, 0, 899, 1400], grade=None, ent='zoomout',
     patches=[[600, 1170, 330, 175]])
T(b(46) + 0.2, '', 640, 1640, 10, fnt=IMP, end=None, ent='bar')
T(b(47), 'GOKURAKUGAI', 660, 1560, 92, fnt=IMP, end=None, ent='type', slant=-6)
T(b(47) + 0.3, 'SANBANDOORI NO KEN', 660, 1650, 64, fnt=IMP, end=None, ent='type', slant=-6, fill=RED2)
T(b(48), 'YUTO SANO', 660, 1730, 34, fnt=LAB, end=None, ent='type', trk=0.3)
IMPACT += [(b(46), 2, 'ink')]; SHAKE += [(b(46), 26, 6)]; FLASH += [(b(46), 1.0, 0.25, PAPER)]
FLARE += [(b(46) + 0.05, W / 2, 1600)]

# ---------------------------------------------------------------- precomputed textures
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx / W - .5) * 2) ** 2 * 0.8 + ((_yy / H - .5) * 2) ** 2 * 0.6)
VIG = (1 - 0.55 * np.clip((_r - 0.45) / 0.9, 0, 1) ** 1.5).astype(np.float32)[..., None]
_g = np.random.default_rng(5)
GRAIN = [cv2.resize(_g.normal(0, 0.02, (H // 2, W // 2)).astype(np.float32), (W, H))[..., None] for _ in range(4)]
del _r

def grade(lum, g):
    if g is None: return lum
    s, m, hgh = GRADES[g]; l = lum[..., None] if lum.ndim == 2 else lum.mean(2, keepdims=True)
    lo = s + (m - s) * np.clip(l * 2, 0, 1)
    return np.where(l < 0.5, lo, m + (hgh - m) * np.clip(l * 2 - 1, 0, 1)).astype(np.float32)

def speed_lines(rgb, t, cx=W / 2, cy=H * 0.45, seed=0):
    r = np.random.default_rng(seed * 1000 + int(t * FPS) // 2)
    lay = np.zeros((H, W), np.float32)
    for _ in range(70):
        a = r.uniform(0, 2 * np.pi); r0 = r.uniform(520, 820); r1 = r0 + r.uniform(300, 1100)
        p0 = (int(cx + r0 * math.cos(a)), int(cy + r0 * math.sin(a))); p1 = (int(cx + r1 * math.cos(a)), int(cy + r1 * math.sin(a)))
        cv2.line(lay, p0, p1, 1.0, int(r.uniform(2, 9)), cv2.LINE_AA)
    rgb[:] = rgb * (1 - 0.85 * lay[..., None]) + 0.85 * lay[..., None] * PAPER

# ---------------------------------------------------------------- shot rendering
def shot_view(sh, t):
    u = clamp((t - sh['t0']) / (sh['t1'] - sh['t0']))
    return u, eio(u)

def render_bleed(spec, t, t0, t1, ent='none'):
    u = clamp((t - t0) / (t1 - t0)); lt = t - t0
    r0, r1 = spec['r'], spec.get('r1', spec['r'])
    rect = lerp_rect(r0, r1, eio(u) if ent != 'zoomout' else eout(u))
    if ent == 'punch':
        k = lerp(1.25, 1.0, eout(lt / 0.22)); x, y, w, h = rect; rect = [x + w * (1 - 1 / k) / 2, y + h * (1 - 1 / k) / 2, w / k, h / k]
    M, k = view_matrix(rect, W, H)
    img = warp_page(spec['p'], M)
    return img, M

def render_shot(sh, t):
    lt = t - sh['t0']; ent = sh.get('ent', 'none')
    if sh['kind'] == 'bleed':
        img, M = render_bleed(sh, t, sh['t0'], sh['t1'], ent)
        for pt in sh.get('patches', []):                     # cover speech bubbles with ink
            px, py, pw, ph = pt[:4]
            p0 = M @ np.float32([px, py, 1]); p1 = M @ np.float32([px + pw, py + ph, 1])
            m = np.zeros((H, W), np.uint8)
            if len(pt) > 4:
                cv2.ellipse(m, (int((p0[0] + p1[0]) / 2), int((p0[1] + p1[1]) / 2)),
                            (int((p1[0] - p0[0]) / 2), int((p1[1] - p0[1]) / 2)), 0, 0, 360, 255, -1, cv2.LINE_AA)
            else:
                cv2.rectangle(m, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), 255, -1)
            m = (m.astype(np.float32) / 255)
            img = img * (1 - (m[..., None] if img.ndim == 3 else m)) + 0.01 * (m[..., None] if img.ndim == 3 else m)
        rgb = grade(img, sh.get('grade'))
    elif sh['kind'] == 'card':
        u = clamp(lt / (sh['t1'] - sh['t0']))
        x, y, w, h = sh['r']
        z = lerp(1, sh.get('kz', 1.1), eio(u)); fx, fy = sh.get('f', (0.5, 0.5))
        w2, h2 = w / z, h / z; rect = [x + (w - w2) * fx, y + (h - h2) * fy, w2, h2]
        if ent == 'punch':
            k = lerp(1.2, 1.0, eout(lt / 0.2)); x, y, w, h = rect; rect = [x + w * (1 - 1 / k) / 2, y + h * (1 - 1 / k) / 2, w / k, h / k]
        bgM, _ = view_matrix(rect, W, H)
        bgM4 = bgM.copy(); bgM4 /= 4; bgM4[:, 2] = bgM[:, 2] / 4
        bg = warp_page(sh['p'], bgM4, (W // 4, H // 4))
        bg = cv2.resize(cv2.GaussianBlur(bg, (0, 0), 9), (W, H)) * 0.5
        ch = W * rect[3] / rect[2]
        M, _ = view_matrix(rect, W, ch, cy=sh.get('cy', H / 2))
        fg = warp_page(sh['p'], M)
        m = np.zeros((H, W), np.float32); y0 = int(sh.get('cy', H / 2) - ch / 2); y1 = int(y0 + ch)
        m[max(0, y0):min(H, y1)] = 1
        sm = cv2.GaussianBlur(np.roll(m, 24, 0), (0, 0), 18)
        img = bg * (1 - 0.7 * sm) ; img = img * (1 - m) + fg * m
        rgb = grade(img, sh.get('grade'))
        # thin red rules framing the card
        for yy in (y0 - 14, y1 + 10):
            if 0 <= yy < H - 4: rgb[yy:yy + 4, :int(W * eout(lt / 0.25))] = RED
    elif sh['kind'] == 'split':
        A, _ = render_bleed(sh['a'], t, sh['t0'], sh['t1']); C, _ = render_bleed(sh['c'], t, sh['t0'], sh['t1'])
        A, C = grade(A, sh['a']['grade']), grade(C, sh['c']['grade'])
        e = eout(lt / 0.35)
        off = (1 - e) * W
        A = cv2.warpAffine(A, np.float32([[1, 0, -off], [0, 1, 0]]), (W, H), borderMode=cv2.BORDER_REPLICATE)
        C = cv2.warpAffine(C, np.float32([[1, 0, off], [0, 1, 0]]), (W, H), borderMode=cv2.BORDER_REPLICATE)
        line = _yy - (1150 - 0.9 * (_xx - W / 2))            # diagonal from lower-left to upper-right
        m = np.clip(line / 2 + 0.5, 0, 1)[..., None]
        rgb = A * (1 - m) + C * m
        band = (np.abs(line) < 9 * e)[..., None]
        rgb = np.where(band, RED, rgb)
    rgb = rgb.astype(np.float32)
    if sh.get('lines'): speed_lines(rgb, t, seed=len(sh['p']) if 'p' in sh else 3)
    foc = sh.get('focus', 0.0)
    if foc and lt < foc:
        sg = 18 * (1 - eout(lt / foc)); rgb = cv2.GaussianBlur(rgb, (0, 0), sg) if sg > 0.5 else rgb
    if sh.get('name'): name_card(rgb, sh, t)
    return rgb

def name_card(rgb, sh, t):
    lt = t - sh['t0'] - BEAT * 0.5
    if lt < 0: return
    big, jp, sub = sh['name']
    slab(rgb, 330, 300, 720, 210, RED, u=lt / 0.22)
    slab(rgb, 360, 420, 640, 54, INK, u=(lt - 0.08) / 0.22)
    if lt > 0.12:
        e = eout((lt - 0.12) / 0.25)
        blit(rgb, sprite(big, IMP, 190, fill=INK, slant=-8), 300 + 120 * (1 - e), 300, 1, 0, e)
        blit(rgb, sprite(jp, JPB, 82, fill=(1, 1, 1)), 610, 270, 1, 0, e)
        blit(rgb, sprite(sub, LAB, 34, fill=(1, 1, 1), trk=0.25), 360, 420, 1, 0, clamp((lt - 0.2) / 0.2))

# ---------------------------------------------------------------- text
def draw_texts(rgb, t):
    for it in TEXT:
        lt = t - it['t']
        if lt < 0 or (it['end'] is not None and t > it['end']): continue
        size, fnt = it['size'], it['fnt']
        kw = dict(fill=it.get('fill', (1, 1, 1)), stroke=it.get('stroke', 0.0), sfill=(0.02, 0.02, 0.03),
                  trk=it.get('trk', it.get('track', 0.0)), vertical=it.get('vertical', False), slant=it.get('slant', 0.0))
        s = it['s']
        if it['ent'] == 'bar':
            slab(rgb, it['x'], it['y'], 980, 300, INK, skew=-6, a=0.88, u=lt / 0.3); continue
        if it['ent'] == 'type':
            n = int(len(s) * clamp(lt / (len(s) * 0.03)))
            if n <= 0: continue
            spr_full = sprite(s, fnt, size, **kw); spr = sprite(s[:n], fnt, size, **kw)
            x = it['x'] - spr_full.shape[1] / 2 + spr.shape[1] / 2
            blit(rgb, spr, x, it['y'])
            continue
        spr = sprite(s, fnt, size, **kw)
        sc, a, bl = 1.0, 1.0, 0.0
        if it['ent'] == 'slam': e = eout(lt / 0.16); sc = lerp(2.4, 1, e); a = clamp(lt / 0.06); bl = 8 * (1 - e)
        elif it['ent'] == 'fade': a = eout(lt / 0.5); bl = 6 * (1 - eout(lt / 0.5))
        if it['end'] is not None: a *= clamp((it['end'] - t) / 0.08)
        if it.get('slabc') is not None:
            slab(rgb, it['x'], it['y'], spr.shape[1] + 120, spr.shape[0] * 0.9, it['slabc'], u=lt / 0.18, a=a)
        blit(rgb, spr, it['x'], it['y'], sc, it.get('rot', 0), a, bl)

# ---------------------------------------------------------------- stopwatch HUD
def stopwatch(rgb, t):
    if not (FIGHT0 - 0.05 <= t < FIGHT1 + 4 * BEAT): return
    run = clamp((t - FIGHT0) / (FIGHT1 - FIGHT0))
    secs = 73.4 * run ** 0.8                                     # 6.4 s of footage = 1:13 of fight
    a = clamp((t - FIGHT0) / 0.15)
    cx, cy, R = 900, 170, 92
    cv2.circle(rgb, (cx, cy), R + 10, tuple(float(v) for v in INK), -1, cv2.LINE_AA)
    cv2.circle(rgb, (cx, cy), R, (0.35, 0.37, 0.4), 3, cv2.LINE_AA)
    ang = 360 * secs / 180.0
    cv2.ellipse(rgb, (cx, cy), (R, R), -90, 0, ang, tuple(float(v) for v in RED2), 9, cv2.LINE_AA)
    hand = math.radians(-90 + 360 * (secs % 60) / 60)
    cv2.line(rgb, (cx, cy), (int(cx + 70 * math.cos(hand)), int(cy + 70 * math.sin(hand))), (1, 1, 1), 4, cv2.LINE_AA)
    txt = f'{int(secs) // 60:02d}:{int(secs) % 60:02d}.{int(secs * 100) % 100:02d}'
    slab(rgb, 600, 175, 330, 120, INK, a=0.85 * a)
    blit(rgb, sprite(txt, MONO, 62, fill=(1, 1, 1)), 610, 150, a=a)
    blit(rgb, sprite('/ 03:00', MONO, 32, fill=(0.6, 0.62, 0.66)), 660, 212, a=a)
    if t >= FIGHT1:
        e = eout((t - FIGHT1) / 0.2)
        blit(rgb, sprite('余裕', JPB, 120, fill=(1, 1, 1)), 900, 330, lerp(2.2, 1, e), -8, clamp((t - FIGHT1) / 0.05))

# ---------------------------------------------------------------- particles
def sparks(rgb, t):
    for ts, x, y, sd in SPARK:
        lt = t - ts
        if not (0 <= lt < 0.45): continue
        r = np.random.default_rng(sd)
        for _ in range(60):
            a = r.uniform(-math.pi, math.pi); v = r.uniform(300, 1500)
            d0, d1 = v * max(0, lt - 0.03), v * lt
            p0 = (int(x + d0 * math.cos(a)), int(y + d0 * math.sin(a) + 400 * lt * lt))
            p1 = (int(x + d1 * math.cos(a)), int(y + d1 * math.sin(a) + 400 * lt * lt))
            k = 1 - lt / 0.45
            cv2.line(rgb, p0, p1, tuple(float(c) for c in GOLD * (0.6 + 0.6 * k)), 3, cv2.LINE_AA)

def flares(rgb, t):
    for ts, x, y in FLARE:
        lt = t - ts
        if not (0 <= lt < 0.5): continue
        k = math.exp(-lt * 9)
        y0, y1 = int(max(0, y - 120)), int(min(H, y + 120))
        rows = np.arange(y0, y1, dtype=np.float32)[:, None]
        cols = np.arange(W, dtype=np.float32)[None, :]
        streak = np.exp(-((rows - y) / 7) ** 2) * np.exp(-((cols - x) / 900) ** 2)
        glow = np.exp(-((rows - y) ** 2 + (cols - x) ** 2) / (2 * 90 ** 2))
        rgb[y0:y1] += (k * (1.4 * streak[..., None] * hexc('#8FD3FF') + 1.2 * glow[..., None] * GOLD)).astype(np.float32)

# ---------------------------------------------------------------- frame
WHIP = 0.16
def shot_at(t):
    for i, s in enumerate(S):
        if s['t0'] <= t < s['t1']: return i
    return len(S) - 1

def whipped(img, dx):
    k = int(min(abs(dx) * 0.35, 160)) * 2 + 1
    o = cv2.warpAffine(img, np.float32([[1, 0, dx], [0, 1, 0]]), (W, H), borderMode=cv2.BORDER_REFLECT)
    return cv2.blur(o, (k, 1)) if k > 3 else o

def frame(fi):
    t = fi / FPS
    si = shot_at(t); sh = S[si]
    rgb = render_shot(sh, t)
    nxt = S[si + 1] if si + 1 < len(S) else None
    if nxt and nxt.get('ent') == 'whip' and t > nxt['t0'] - WHIP:          # leave: whip out to the left
        u = (t - (nxt['t0'] - WHIP)) / WHIP; rgb = whipped(rgb, -ein(u) * W * 0.6)
    if sh.get('ent') == 'whip' and t < sh['t0'] + WHIP:                    # arrive from the right
        u = (t - sh['t0']) / WHIP; rgb = whipped(rgb, (1 - eout(u)) * W * 0.6)
    draw_texts(rgb, t)
    stopwatch(rgb, t)
    sparks(rgb, t); flares(rgb, t)
    # impact frames
    for ts, nfr, mode in IMPACT:
        if ts <= t < ts + nfr / FPS:
            l = rgb.mean(2, keepdims=True)
            bw = (l > 0.42).astype(np.float32)
            rgb = (1 - bw) if mode == 'inv' else bw * PAPER + (1 - bw) * INK
            rgb = np.repeat(rgb, 3, 2) if rgb.shape[2] == 1 else rgb
            break
    # shake + chromatic split
    ox = oy = 0.0; ca = 0.0
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
    rgb = rgb * VIG + GRAIN[si % 4]                      # grain pattern changes per shot (static = cheap to encode)
    rgb = rgb * clamp((DUR - t) / 0.35)                                       # cut to black at the very end
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)

# ---------------------------------------------------------------- main
def stills(times):
    d = os.path.join(HERE, 'stills'); os.makedirs(d, exist_ok=True)
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
    out0 = os.path.join(ROOT, 'gokurakugai-short.mp4'); out1 = os.path.join(ROOT, 'gokurakugai-short-music.mp4')
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                          '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out0], stdin=subprocess.PIPE)
    with Pool(max(1, os.cpu_count() - 1)) as pool:
        for i, fr in enumerate(pool.imap(frame, range(N), chunksize=4)):
            p.stdin.write(fr.tobytes())
            if i % 150 == 0: print(f'frame {i}/{N}', flush=True)
    p.stdin.close(); p.wait()
    wav = os.path.join(HERE, 'music.wav')
    if os.path.exists(wav):
        subprocess.run([ff, '-y', '-v', 'error', '-i', out0, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                        '-af', 'loudnorm=I=-14:TP=-1.0:LRA=9,aresample=48000', '-c:a', 'aac', '-b:a', '192k',
                        '-t', f'{DUR:.3f}', '-movflags', '+faststart', out1], check=True)
    print('wrote', out0, out1 if os.path.exists(wav) else '(no music.wav)')

if __name__ == '__main__':
    if sys.argv[1] == 'stills': stills([float(x) for x in sys.argv[2].split(',')])
    else: video()
