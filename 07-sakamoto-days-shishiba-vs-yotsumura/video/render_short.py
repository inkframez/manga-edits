"""Sakamoto Days ch.100 "Lightning Strikes" - Shishiba vs. Yotsumura. Full 32 s vertical Short, 1080x1920, 30 fps.

The fighters are the Canva-extracted layers (../layers.json) animated as 2.5D puppets: they wind up, lunge, collide,
freeze for a hit-stop, recoil and settle, with smears, afterimages, panel break-outs, ink / spark / debris particles,
and a camera that reacts to every contact. Picture and score share timeline_short.py (170 BPM).

Look: ink, paper and one accent (hazard yellow). Characters get a paper "sticker" rim when they sit on a flat field,
so they read as cut-outs on purpose. Wide panels become bands the characters break out of; tall panels run
full-bleed. Drawn sound effects stay as Yuto Suzuki lettered them; our own type is reserved for names, the quote,
and the title.

Usage (from this folder):
  python music_short.py                       -> score_short.wav
  python render_short.py stills 1.6,10.2      -> stills_short/*.png
  python render_short.py sheet 1              -> stills_short/sheet.jpg
  python render_short.py video [--workers 3]  -> ../sakamoto-days-short.mp4
"""
import os, sys, math, json, subprocess, argparse
from functools import lru_cache
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
from timeline_short import BEAT, FPS, NB, DUR, HITS, HITSTOP, b

cv2.setNumThreads(1)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FD = 'C:/Windows/Fonts/' if os.name == 'nt' else str(ROOT.parent / 'fonts') + '/'   # tools/setup_fonts.py
DISPLAY = FD + 'impact.ttf'          # Impact on Windows; Anton elsewhere
LABEL = FD + 'bahnschrift.ttf'       # Bahnschrift on Windows; Barlow Condensed elsewhere
JP = FD + 'YuGothB.ttc'              # Yu Gothic Bold on Windows; Noto Sans JP 800 elsewhere
W, H = 1080, 1920
NF = int(round(DUR * FPS))
OUT = ROOT / 'sakamoto-days-short.mp4'
AUDIO = HERE / 'score_short.wav'
LAYERS = {a['id']: a for a in json.loads((ROOT / 'layers.json').read_text())['assets']}


def hexc(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)
INK, PAPER, YEL = hexc('#0B0B0D'), hexc('#F2EDE3'), hexc('#FFD21F')
MX = 72


# ---------------------------------------------------------------- easing / time
def clamp(x, a=0.0, c=1.0): return max(a, min(c, x))
def eout(u, p=4): return 1 - (1 - clamp(u)) ** p
def ein(u, p=3): return clamp(u) ** p
def eio(u): u = clamp(u); return u * u * (3 - 2 * u)
def lerp(a, c, u): return a + (c - a) * u
def eback(u, s=1.8): u = clamp(u) - 1; return 1 + (s + 1) * u ** 3 + s * u ** 2


def held(bt):
    """Story time with hit-stops removed: during a hit-stop the puppets freeze (the camera still shakes)."""
    t = b(bt)
    for hb, st in HITS:
        h0, d = b(hb), HITSTOP[st]
        if t > h0: t -= min(d, t - h0)
    return t / BEAT


def since_hit(bt, hb):
    """Seconds since a hit, measured in held (hit-stopped) time."""
    return b(held(bt) - held(hb)) if bt >= hb else -1.0


def recoil(dt, amp, k=9.0, f=2.2):
    """Damped spring kick: jumps to amp and settles, for recoils after contact."""
    return 0.0 if dt < 0 else amp * math.exp(-dt * k) * math.cos(dt * f * 2 * math.pi)


# ---------------------------------------------------------------- fixed fields
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_vr = np.sqrt(((_xx / W - .5) * 2) ** 2 * .7 + ((_yy / H - .5) * 2) ** 2 * .5)
VIG = (1 - .3 * np.clip(_vr - .45, 0, 1) ** 1.6)[..., None].astype(np.float32)
_g = np.random.default_rng(5)
GRAIN = [cv2.resize(_g.normal(0, .018, (H // 2, W // 2)).astype(np.float32), (W, H))[..., None] for _ in range(3)]
def _noise(scale, seed):
    r = np.random.default_rng(seed); n = r.random((H // scale + 3, W // scale + 3)).astype(np.float32)
    return cv2.resize(n, (W + 3 * scale, H + 3 * scale), interpolation=cv2.INTER_CUBIC)[:H, :W]
INKF = .55 * _noise(160, 1) + .3 * _noise(40, 2) + .15 * _noise(9, 3)
INKF = (INKF - INKF.min()) / (INKF.max() - INKF.min())


def field(col): return np.zeros((H, W, 3), np.float32) + col


@lru_cache(maxsize=8)
def halftone(angle=45, spacing=26, lo=.0, hi=.42, axis='y'):
    """Ben-Day dot gradient (dot radius grows along `axis`) as a 0..1 mask."""
    a = math.radians(angle)
    u = _xx * math.cos(a) + _yy * math.sin(a); v = -_xx * math.sin(a) + _yy * math.cos(a)
    du = (u % spacing) - spacing / 2; dv = (v % spacing) - spacing / 2
    d = np.sqrt(du * du + dv * dv)
    g = (_yy / H) if axis == 'y' else (_xx / W)
    r = (lo + (hi - lo) * g) * spacing
    return np.clip(r - d + .5, 0, 1).astype(np.float32)


def yellow_field(dots=True):
    img = field(YEL)
    if dots: img -= halftone()[..., None] * (YEL - INK) * .16
    return img


# ---------------------------------------------------------------- pages
@lru_cache(maxsize=None)
def page(name, mip):
    g = cv2.imread(str(ROOT / 'panels' / f'{name}.jpg'), cv2.IMREAD_GRAYSCALE)
    if g is None: raise FileNotFoundError(name)
    if mip == 2:
        g = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        g = cv2.addWeighted(g, 1.6, cv2.GaussianBlur(g, (0, 0), 1.8), -.6, 0)
    return g


def view(name, cx, cy, hs, size=(W, H), rot=0.0, rect=None):
    """Luminance of a page seen by a camera centred on (cx, cy) whose frame height covers hs page px."""
    w, h = size; ws = hs * w / h
    if rect:
        x, y, rw, rh = rect
        cx = clamp(cx, x + ws / 2, x + rw - ws / 2) if rw > ws else x + rw / 2
        cy = clamp(cy, y + hs / 2, y + rh - hs / 2) if rh > hs else y + rh / 2
    s = h / hs; mip = 2 if s > 1.15 else 1
    src = page(name, mip); s /= mip
    M = cv2.getRotationMatrix2D((cx * mip, cy * mip), rot, s)
    M[0, 2] += w / 2 - cx * mip; M[1, 2] += h / 2 - cy * mip
    g = cv2.warpAffine(src, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=255)
    if s < .8: g = cv2.GaussianBlur(g, (0, 0), .45 / s)
    return np.clip((g.astype(np.float32) / 255 - .06) / .88, 0, 1)


def tone(L, under=None):
    U = (np.zeros(L.shape + (3,), np.float32) + PAPER) if under is None else under
    return INK + (U - INK) * L[..., None]


# ---------------------------------------------------------------- layers (2.5D puppets)
@lru_cache(maxsize=None)
def layer(name):
    """Premultiplied RGBA float32 in the edit's palette. Character alpha is firmed up so screentone does not
    turn see-through on coloured fields."""
    a = LAYERS[name]
    im = cv2.imread(str(ROOT / a['file']), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
    al = im[..., 3]
    if a['role'] in ('character', 'action_pair', 'prop', 'detail'):
        al = np.clip((al - .08) / .5, 0, 1)
    L = np.clip((cv2.cvtColor(im[..., :3], cv2.COLOR_BGR2GRAY) - .06) / .88, 0, 1)
    rgb = INK + (PAPER - INK) * L[..., None]
    if a['id'] == 'passage_sparks':           # white sparks drawn for a dark surface -> glowing yellow-white
        rgb = np.zeros_like(rgb) + PAPER; al = al * np.clip(L * 1.4, 0, 1)
    pm = np.dstack([rgb * al[..., None], al]).astype(np.float32)
    return np.ascontiguousarray(pm)


class Cam:
    """Source-space camera for one page: screen = centre + (p - c) * s, plus a screen offset (shake)."""
    def __init__(self, cx, cy, hs, ox=0.0, oy=0.0, rot=0.0):
        self.cx, self.cy, self.s, self.ox, self.oy, self.rot = cx, cy, H / hs, ox, oy, rot

    def pt(self, x, y):
        X, Y = (x - self.cx) * self.s, (y - self.cy) * self.s
        if self.rot:
            c, s_ = math.cos(math.radians(self.rot)), math.sin(math.radians(self.rot))
            X, Y = X * c - Y * s_, X * s_ + Y * c
        return W / 2 + X + self.ox, H / 2 + Y + self.oy

    def page(self, name, rect=None):
        g = view(name, self.cx - self.ox / self.s, self.cy - self.oy / self.s, H / self.s, rot=-self.rot, rect=rect)
        return g


def put_layer(dst, name, cam, dx=0.0, dy=0.0, sc=1.0, rot=0.0, a=1.0, vel=(0.0, 0.0), rim=None, rim_w=7,
              ghosts=0, tint=None):
    """Draw a layer at its recorded origin + (dx, dy) source px, scaled / rotated about its pivot.
    vel = screen-space smear vector (px) for motion blur; ghosts = afterimages trailing along -vel;
    rim = colour of a sticker outline drawn under the sprite."""
    L = LAYERS[name]; pm = layer(name); ss = L['sprite_scale']
    px, py = L['pivot']; ox, oy = L['origin']
    # sprite px -> source px:  origin + ss*(pivot + sc*R(p - pivot)) + d
    th = math.radians(rot); c, s_ = math.cos(th) * sc, math.sin(th) * sc
    A = np.array([[c, -s_], [s_, c]]) * ss
    t = np.array([ox + ss * px + dx, oy + ss * py + dy]) - A @ np.array([px, py])
    # source px -> screen
    k = cam.s; cr = math.radians(cam.rot); C = np.array([[math.cos(cr), -math.sin(cr)], [math.sin(cr), math.cos(cr)]]) * k
    A2 = C @ A; t2 = C @ (t - np.array([cam.cx, cam.cy])) + np.array([W / 2 + cam.ox, H / 2 + cam.oy])
    M = np.hstack([A2, t2[:, None]]).astype(np.float32)
    big = abs(np.linalg.det(A2)) ** .5
    src = pm
    if big < .6:   # pre-shrink to avoid aliasing
        f = max(.25, big * 1.4); src = cv2.resize(pm, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        M[:, :2] /= f
    spr = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    vx, vy = vel; ln = math.hypot(vx, vy)
    if ln > 3:
        n = int(min(ln, 120)) | 1; ker = np.zeros((n, n), np.float32)
        cv2.line(ker, (n // 2 - int(vx / ln * n / 2), n // 2 - int(vy / ln * n / 2)), (n // 2, n // 2), 1, 1)
        ker /= ker.sum(); spr = cv2.filter2D(spr, -1, ker)
    al = spr[..., 3]
    if ghosts and ln > 3:
        for g in range(ghosts, 0, -1):
            sh = np.float32([[1, 0, -vx * g * .9], [0, 1, -vy * g * .9]])
            gal = cv2.warpAffine(al, sh, (W, H)) * (.28 / g) * a
            col = YEL if tint is None else tint
            dst[:] = dst * (1 - gal[..., None]) + np.asarray(col) * gal[..., None]
    if rim is not None:
        ra = cv2.dilate((al > .35).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (rim_w * 2 + 1,) * 2))
        ra = cv2.GaussianBlur(ra.astype(np.float32), (0, 0), 1.0) * a
        dst[:] = dst * (1 - ra[..., None]) + np.asarray(rim) * ra[..., None]
    rgb = spr[..., :3]
    if tint is not None and ghosts == 0:
        rgb = rgb * 0 + np.asarray(tint) * al[..., None]
    dst[:] = dst * (1 - al[..., None] * a) + rgb * a
    return al


# ---------------------------------------------------------------- type
@lru_cache(maxsize=512)
def spr(text, font, size, track=0.0, vertical=False):
    f = ImageFont.truetype(font, size)
    if vertical:
        cw = size; ch = int(size * 1.02)
        im = Image.new('L', (cw + 8, ch * len(text) + 8)); d = ImageDraw.Draw(im)
        for i, c in enumerate(text): d.text((4 + cw / 2, 4 + i * ch + ch / 2), c, font=f, fill=255, anchor='mm')
    else:
        asc, desc = f.getmetrics()
        adv = [f.getlength(c) + track * size / 100 for c in text]
        wid = int(sum(adv)) + 8
        im = Image.new('L', (max(1, wid), asc + desc + 8)); d = ImageDraw.Draw(im); x = 4
        for c, a in zip(text, adv): d.text((x, 4), c, font=f, fill=255); x += a
    m = np.asarray(im, np.float32) / 255
    ys, xs = np.nonzero(m > .02)
    if len(ys) == 0: return m
    return np.ascontiguousarray(m[max(0, ys.min() - 2):ys.max() + 3, max(0, xs.min() - 2):xs.max() + 3])


def paste(dst, src, x, y, mask=None, a=1.0):
    x, y = int(round(x)), int(round(y)); h, w = (mask if mask is not None else src).shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 <= x0 or y1 <= y0: return
    sl = (slice(y0 - y, y1 - y), slice(x0 - x, x1 - x)); d = dst[y0:y1, x0:x1]
    s = src if src.ndim == 1 else src[sl]
    if mask is None: d[:] = d * (1 - a) + s * a; return
    m = mask[sl][..., None] * a; d[:] = d * (1 - m) + s * m


def put(dst, m, x, y, col, a=1.0, anchor=(0, 0), sc=1.0, rot=0.0, reveal=1.0, shadow=0, skew=0.0):
    if a <= 0: return
    if sc != 1 or rot or skew:
        h, w = m.shape; R = cv2.getRotationMatrix2D((w / 2, h / 2), rot, sc)
        R[0, 1] += skew * sc
        nw, nh = int(w * sc * 1.5 + 20), int(h * sc * 1.5 + 20)
        R[0, 2] += nw / 2 - w / 2; R[1, 2] += nh / 2 - h / 2
        m = cv2.warpAffine(m, R, (nw, nh), flags=cv2.INTER_LINEAR)
        x -= (nw - w * sc) / 2; y -= (nh - h * sc) / 2
        bw, bh = w * sc, h * sc
    else:
        bw, bh = m.shape[1], m.shape[0]
    if reveal < 1: m = m.copy(); m[:, int(m.shape[1] * clamp(reveal)):] = 0
    px, py = x - anchor[0] * bw, y - anchor[1] * bh
    if shadow: paste(dst, INK, px + shadow, py + shadow, m, a * .9)
    paste(dst, np.asarray(col, np.float32), px, py, m, a)


def slab(dst, x, y, w, h, col, a=1.0):
    x0, y0, x1, y1 = int(max(0, x)), int(max(0, y)), int(min(W, x + w)), int(min(H, y + h))
    if x1 > x0 and y1 > y0: dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - a) + np.asarray(col) * a


def stamp(dst, text, x, y, size, col, u, anchor=(0, 0), font=None, skew=-.12, shadow=8):
    """Type that lands like a rubber stamp: scales down from 1.6x with a 2-frame overshoot."""
    if u <= 0: return
    k = eback(u / .5, 2.4); sc = 1 + .6 * (1 - k)
    put(dst, spr(text, font or DISPLAY, size), x, y, col, min(1, u * 6), anchor, sc=sc, skew=skew, shadow=shadow)


def tag(dst, text, x, y, a, right=False, size=34, col=INK, bg=YEL):
    if a <= 0: return
    m = spr(text, LABEL, size, 28); w = (m.shape[1] + 30) * eout(a / .6)
    slab(dst, x - w + 15 if right else x - 15, y - 11, w, m.shape[0] + 22, bg, .96)
    put(dst, m, x, y, col, clamp((a - .3) / .7), (1 if right else 0, 0))


# ---------------------------------------------------------------- particles & graphic FX
def speed_lines(dst, seed, ang=0.0, n=55, col=None, a=1.0, y0=0, y1=H, thick=(1, 6), alpha_m=None):
    r = np.random.default_rng(seed); m = np.zeros((H, W), np.uint8)
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    for _ in range(n):
        cx, cy = r.uniform(-200, W + 200), r.uniform(y0, y1); ln = r.uniform(250, 1400)
        cv2.line(m, (int(cx - ca * ln / 2), int(cy - sa * ln / 2)), (int(cx + ca * ln / 2), int(cy + sa * ln / 2)),
                 255, int(r.uniform(*thick)), cv2.LINE_AA)
    mm = m.astype(np.float32) / 255
    if alpha_m is not None: mm *= alpha_m
    paste(dst, PAPER if col is None else np.asarray(col), 0, 0, mm, a)


def focus_lines(dst, cx, cy, seed, n=100, r0=380, col=None, a=1.0):
    r = np.random.default_rng(seed); m = np.zeros((H, W), np.uint8); R = 2600
    for _ in range(n):
        ang = r.uniform(0, 2 * np.pi); wd = r.uniform(.003, .014); ri = r0 * r.uniform(.8, 1.7)
        p = [(cx + math.cos(ang) * ri, cy + math.sin(ang) * ri), (cx + math.cos(ang - wd) * R, cy + math.sin(ang - wd) * R),
             (cx + math.cos(ang + wd) * R, cy + math.sin(ang + wd) * R)]
        cv2.fillPoly(m, [np.int32(p)], 255, cv2.LINE_AA)
    paste(dst, INK if col is None else np.asarray(col), 0, 0, m.astype(np.float32) / 255, a)


def ink_drops(dst, x0, y0, t, seed, n=34, spd=(500, 1500), ang=(-160, -20), g=2400, size=(5, 22), col=None):
    """Ballistic ink droplets from (x0, y0), stretched along velocity; t in seconds since emission."""
    if t < 0: return
    r = np.random.default_rng(seed); m = np.zeros((H, W), np.uint8)
    for _ in range(n):
        a = math.radians(r.uniform(*ang)); v = r.uniform(*spd); sz = r.uniform(*size); life = r.uniform(.5, 1.2)
        if t > life: continue
        vx, vy = math.cos(a) * v, math.sin(a) * v
        x = x0 + vx * t; y = y0 + vy * t + .5 * g * t * t
        vyt = vy + g * t; sp = math.hypot(vx, vyt)
        st = 1 + min(3.0, sp / 600); ang_d = math.degrees(math.atan2(vyt, vx))
        s = sz * (1 - .5 * t / life)
        cv2.ellipse(m, (int(x), int(y)), (max(1, int(s * st)), max(1, int(s))), ang_d, 0, 360, 255, -1, cv2.LINE_AA)
    paste(dst, INK if col is None else np.asarray(col), 0, 0, m.astype(np.float32) / 255)


def sparks(dst, x0, y0, t, seed, n=26, a=1.0, col=None):
    if t < 0 or t > .45: return
    r = np.random.default_rng(seed); m = np.zeros((H, W), np.uint8)
    for _ in range(n):
        ang = r.uniform(0, 2 * math.pi); v = r.uniform(900, 2600); ln = r.uniform(30, 140)
        d = v * t * (1 - t)
        x, y = x0 + math.cos(ang) * d, y0 + math.sin(ang) * d
        cv2.line(m, (int(x), int(y)), (int(x - math.cos(ang) * ln), int(y - math.sin(ang) * ln)), 255,
                 max(1, int(4 * (1 - t / .45))), cv2.LINE_AA)
    mm = m.astype(np.float32) / 255
    glow = cv2.GaussianBlur(mm, (0, 0), 8) * 2
    paste(dst, YEL if col is None else np.asarray(col), 0, 0, np.clip(glow, 0, 1), a * (1 - t / .45))
    paste(dst, PAPER, 0, 0, mm, a)


def burst(dst, x, y, t, r_max=520, col=None, seed=0):
    """A spiky impact star that blooms and vanishes in ~0.18 s."""
    if t < 0 or t > .2: return
    k = eout(t / .08); rng = np.random.default_rng(seed); n = 18
    pts = []
    for i in range(n * 2):
        ang = i * math.pi / n + rng.uniform(-.08, .08)
        rr = (r_max if i % 2 == 0 else r_max * .38) * k * rng.uniform(.7, 1.15)
        pts.append((x + math.cos(ang) * rr, y + math.sin(ang) * rr))
    m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [np.int32(pts)], 255, cv2.LINE_AA)
    o = np.zeros((H, W), np.uint8); cv2.polylines(o, [np.int32(pts)], True, 255, 7, cv2.LINE_AA)
    fade = 1 - clamp((t - .1) / .1)
    paste(dst, YEL if col is None else np.asarray(col), 0, 0, m.astype(np.float32) / 255, .3 * fade)
    paste(dst, YEL if col is None else np.asarray(col), 0, 0, o.astype(np.float32) / 255, fade)


def shards(dst, x0, y0, t, seed, n=16, col=None):
    if t < 0 or t > 1.2: return
    r = np.random.default_rng(seed); m = np.zeros((H, W), np.uint8)
    for _ in range(n):
        a = math.radians(r.uniform(-170, -10)); v = r.uniform(500, 1500); s = r.uniform(14, 46); sp = r.uniform(-12, 12)
        x = x0 + math.cos(a) * v * t; y = y0 + math.sin(a) * v * t + 1400 * t * t
        pts = [(x + math.cos(sp * t + q) * s * f, y + math.sin(sp * t + q) * s * f) for q, f in ((0, 1), (2.2, .6), (4.0, .9))]
        cv2.fillPoly(m, [np.int32(pts)], 255, cv2.LINE_AA)
    paste(dst, INK if col is None else np.asarray(col), 0, 0, m.astype(np.float32) / 255)


def shift(img, dx, dy, fill=0.0):
    return cv2.warpAffine(img, np.float32([[1, 0, dx], [0, 1, dy]]), (W, H), borderMode=cv2.BORDER_CONSTANT,
                          borderValue=(fill, fill, fill))


def zoom_img(img, s, cx=W / 2, cy=H / 2, rot=0.0):
    return cv2.warpAffine(img, cv2.getRotationMatrix2D((cx, cy), rot, s), (W, H), borderMode=cv2.BORDER_REFLECT)


def chroma(img, k):
    if k < .5: return img
    k = int(round(k)); out = img.copy(); out[:, k:, 0] = img[:, :-k, 0]; out[:, :-k, 2] = img[:, k:, 2]; return out


def band(dst, name, rect, yc, u=0.0, z=(1.0, 1.06), drift=(0, 0), slide=0.0, edge=YEL, a=1.0, h=None):
    """A wide panel as a full-width band centred at yc (optionally cropped to height h px)."""
    x, y, rw, rh = rect; bh = h or int(round(W * rh / rw))
    zz = lerp(z[0], z[1], eio(u))
    hs = (rw * bh / W) / zz
    L = view(name, x + rw / 2 + drift[0] * (u - .5), y + rh / 2 + drift[1] * (u - .5), hs, (W, bh), rect=rect)
    img = tone(L); top = yc - bh / 2
    if abs(slide) > 2: img = cv2.blur(img, (int(min(81, abs(slide) * .08)) | 1, 1))
    paste(dst, img, slide, top, a=a)
    if edge is not None: slab(dst, slide, top + bh - 5, W, 10, edge, a)
    return top, bh


# ---------------------------------------------------------------- shots
def s_versus(tl, u, bt):
    """Name card. Split field: yellow (Yotsumura) over ink (Shishiba); both slide in, names stamp, then they rush."""
    img = field(INK)
    cut = poly = np.zeros((H, W), np.float32)
    m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [np.int32([(0, 0), (W, 0), (W, 820), (0, 1100)])], 255, cv2.LINE_AA)
    top = m.astype(np.float32)[..., None] / 255
    img = yellow_field() * top + img * (1 - top)
    speed_lines(img, int(bt * 6), 0, 40, YEL, .22, 1000, H)
    rush = ein((bt - 3.4) / .6, 2)
    ka = eout((bt - 0) / .45); kb = eout((bt - 1.0) / .45)
    camA = Cam(560, 470, 1250); camB = Cam(1360, 470, 1250)
    camA.oy = -330; camB.oy = 560
    put_layer(img, 'clash_yotsumura', camA, dx=-900 * (1 - ka) + 700 * rush, dy=40 * rush, rot=-3 + 4 * rush,
              vel=(-260 * (1 - ka) * 2 + 500 * rush, 0), rim=PAPER, ghosts=2 if rush > 0 else 0)
    put_layer(img, 'clash_shishiba', camB, dx=900 * (1 - kb) - 700 * rush, dy=-40 * rush, rot=3 - 4 * rush,
              vel=(260 * (1 - kb) * 2 - 500 * rush, 0), rim=YEL, ghosts=2 if rush > 0 else 0)
    if bt > .5: slab(img, 0, 110, W * eout((bt - .5) / .3), 205, YEL)
    stamp(img, 'YOTSUMURA', MX, 120, 170, INK, (bt - .5) / .5, shadow=0)
    put(img, spr('ヨツムラ', JP, 46, vertical=True), W - 70, 140, INK, eout((bt - .8) / .5), (.5, 0))
    if bt > 1.5: slab(img, W * (1 - eout((bt - 1.5) / .3)), 1490, W, 205, INK)
    stamp(img, 'SHISHIBA', W - MX, 1500, 170, YEL, (bt - 1.5) / .5, anchor=(1, 0), shadow=0)
    put(img, spr('シシバ', JP, 46, vertical=True), 70, 1240, YEL, eout((bt - 1.8) / .5), (.5, 0))
    vs = eback((bt - 2.2) / .35, 2.5)
    if bt > 2.2:
        put(img, spr('VS', DISPLAY, 230), W / 2, 960, PAPER, 1, (.5, .5), sc=.4 + .6 * vs, rot=-8, shadow=10)
    tag(img, 'SAKAMOTO DAYS  ·  CH.100  LIGHTNING STRIKES', MX, 1780 - 1100, eout((bt - 2.6) / .5) * (1 - rush), size=28)
    if rush > .85: img = img * (1 - (rush - .85) / .15 * .9) + PAPER * (rush - .85) / .15 * .9
    return img


def s_rooftop(tl, u, bt):
    """BABAM: both fighters wind up off-frame and collide on the downbeat; hit-stop; recoil; the camera drifts."""
    img = field(PAPER)
    hb = 5.0; dt = since_hit(bt, hb)
    pre = clamp((bt - 4) / (hb - 4))                           # 0..1 wind-up -> contact
    lunge = ein(pre, 3) if bt < hb else 1.0
    back = (1 - lunge)
    zo = lerp(.9, 1.0, eout(tl / .35)) * (1 + .06 * math.exp(-max(dt, 0) * 8) if dt >= 0 else 1)
    cam = Cam(545 - 30 * clamp(dt / 1.2), 540, 1000 / zo)
    L = view('ch100_004', cam.cx, cam.cy, H / cam.s, rect=(0, 0, 1200, 960))
    img = tone(L)
    plate = layer('opening_rooftop')   # reconstructed rooftop behind the fighters
    put_layer(img, 'opening_rooftop', cam, a=1.0)
    if dt >= 0:
        bx, by = cam.pt(545, 450); burst(img, bx, by, dt, 560)
    ry = recoil(dt, -26); rs = recoil(dt, 30)
    vel = 900 * (ein(pre + .1, 3) - ein(pre, 3)) if bt < hb else 0
    put_layer(img, 'opening_yotsumura', cam, dx=-150 * back + ry, dy=-30 * back, rot=-6 * back,
              vel=(vel * cam.s * .3, 0), ghosts=1 if back > .05 else 0)
    put_layer(img, 'opening_shishiba', cam, dx=160 * back + rs, dy=40 * back, rot=7 * back,
              vel=(-vel * cam.s * .3, 0), ghosts=1 if back > .05 else 0)
    # the drawn BABAM strip stays on top, as lettered
    top = view('ch100_004', cam.cx, cam.cy, H / cam.s, rect=(0, 0, 1200, 960))
    m = np.zeros((H, W), np.float32)
    y1 = cam.pt(0, 300)[1]
    if y1 > 0 and dt >= 0:   # BABAM is the sound of the contact: it lands with it
        msk = (1 - top[:int(min(H, y1))]) * (top[:int(min(H, y1))] < .35)
        m[:int(min(H, y1))] = msk
        paste(img, INK, 0, 0, m)
    if dt >= 0:
        sx, sy = cam.pt(545, 450)
        sparks(img, sx, sy, dt, 5)
    return img


def s_vwam(tl, u, bt):
    img = field(INK)
    top, bh = band(img, 'ch100_004', (75, 952, 1035, 410), 900, u, z=(1.15, 1.32), drift=(-160, 0),
                   slide=-W * (1 - eout(tl / .25)))
    speed_lines(img, int(bt * 15), -12, 30, YEL, .5, top + bh + 30, H)
    speed_lines(img, int(bt * 15) + 3, -12, 30, YEL, .5, 0, top - 30)
    return img


def s_shwoo(tl, u, bt):
    img = yellow_field()
    top, bh = band(img, 'ch100_004', (180, 1400, 930, 400), 960, u, z=(1.25, 1.45), drift=(220, 0), edge=INK)
    if tl < .25: img = img * .4 + PAPER * .6 if tl < 1 / FPS * 2 else img
    tag(img, 'ROOFTOPS OF KYOTO', MX, top - 120, eout(tl / .5), col=YEL, bg=INK)
    return img


def s_shaft(tl, u, bt):
    """Crash down the building: the camera dives down the shaft, the fighters fall faster, debris flies up."""
    hs = 1150
    cy = lerp(560, 1240, eio(u))
    cam = Cam(323, cy, hs)
    L = view('ch100_006', cam.cx, cam.cy, hs, rect=(0, 0, 647, 1800))
    img = tone(L)
    fall = lerp(-500, 520, ein(u, 1.6))
    put_layer(img, 'descent_pair', cam, dy=fall, sc=1.05, rot=4 * math.sin(tl * 5), vel=(0, 45), ghosts=1,
              rim=YEL, rim_w=5)
    for k in range(3):
        shards(img, W / 2 + (k - 1) * 260, H * .55, (tl - k * .18) % 1.1, 30 + k, n=10)
    speed_lines(img, int(bt * 15), 90, 40, INK, .55)
    return img


def s_bam(tl, u, bt):
    """BAM BAM BAM BAM down the facade: four hits on the eighth notes, each a camera jolt."""
    hits = [14, 14.5, 15, 15.5]
    k = sum(1 for h in hits if bt >= h)
    cy = lerp(900, 1500, eio(u)) + sum(40 * math.exp(-(bt - h) * 12) for h in hits if bt >= h)
    hs = 1150 / (1 + .04 * k)
    L = view('ch100_006', 925, cy, hs, rect=(650, 640, 550, 1160))
    img = tone(L)
    for i, h in enumerate(hits):
        dt = since_hit(bt, h)
        if 0 <= dt < .2:
            sx, sy = W * (.55 + .1 * (i % 2)), lerp(500, 1500, i / 3)
            burst(img, sx, sy, dt, 300, seed=i)
    return img


def s_vwam2(tl, u, bt):
    img, = [tone(view('ch100_007', lerp(320, 380, eio(u)), 700, lerp(820, 900, eio(u)), rect=(0, 250, 690, 900)))]
    focus_lines(img, W * .6, H * .45, int(bt * 15), 70, 520, PAPER, .5 * (1 - u))
    return img


def s_house(tl, u, bt):
    """'Killing is like house-cleaning to me.' Shishiba close-up; the camera slides along the hammer."""
    hs = lerp(1100, 960, eio(u))
    img = tone(view('ch100_007', 945, lerp(550, 640, eio(u)), hs, rect=(690, 0, 510, 1120)))
    tag(img, 'SHISHIBA', MX, 1450, eout((bt - 18.4) / .5))
    put(img, spr('THE ORDER', LABEL, 30, 40), MX, 1512, PAPER, eout((bt - 18.8) / .5), shadow=3)
    return img


def s_passage(tl, u, bt):
    """The Channel of Rebirth: half-time tension. Shishiba walks into the dark; slow push."""
    if bt < 22:
        img = tone(view('ch100_008', lerp(860, 840, u * 2), 330, lerp(640, 600, eio(u * 2)), rect=(610, 0, 500, 610)))
        return img
    v = (bt - 22) / 2
    cam = Cam(700, 900, lerp(560, 430, eio(v)))
    L = view('ch100_008', cam.cx, cam.cy, H / cam.s, rect=(312, 655, 798, 480))
    img = tone(L)
    put_layer(img, 'passage_interior', cam)
    put_layer(img, 'passage_shishiba_small', cam, dy=-6 * v, sc=1 + .05 * v)
    slab(img, 0, 0, W, H, INK, .25)
    put(img, spr("HE'S BAITING ME...", LABEL, 44, 30), MX, 1430, PAPER, eout((bt - 22.6) / .6),
        reveal=eout((bt - 22.6) / .6), shadow=3)
    return img


def s_shing(tl, u, bt):
    """SHING: a blade out of the dark meets the hammer handle; sparks on black."""
    img = field(INK)
    hb = 24.0; dt = since_hit(bt, hb)
    cam = Cam(700, 1480, 900 / (1 + .06 * math.exp(-max(dt, 0) * 6)))
    mural = np.zeros_like(img); put_layer(mural, 'passage_mural', cam)
    img = img + mural * .35
    put_layer(img, 'passage_shishiba', cam, dx=recoil(dt, 22), dy=recoil(dt, -8), rot=recoil(dt, 2.5), rim=YEL, rim_w=5)
    sx, sy = cam.pt(470, 1550)
    if dt >= 0:
        burst(img, sx, sy, dt, 380)
        sparks(img, sx, sy, dt, 11, 40)
        put_layer(img, 'passage_sparks', cam, sc=1 + 1.2 * eout(dt / .25), a=clamp(1 - dt / .6))
    stamp(img, 'SHING', W - MX, 260, 260, YEL, (bt - 24) / .4, anchor=(1, 0))
    return img


def s_clash(tl, u, bt):
    """The spread, rebuilt as a fight. The fighters pull apart and slam together on 29, 31, 32 and 32.5; each
    contact freezes (hit-stop), sparks, and kicks them back. The camera breathes with the gap: wide while they
    are apart, tight on the contact, faces always in frame."""
    hits = [29, 31, 32, 32.5]
    img = field(INK)
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.int32([(0, 0), (W, 0), (W, 760), (0, 1160)])], 255, cv2.LINE_AA)
    t_ = m.astype(np.float32)[..., None] / 255
    img = yellow_field() * t_ + img * (1 - t_)
    put(img, spr('SHING', DISPLAY, 430), W / 2, 330, INK, 1, (.5, .5), rot=-12, sc=1 + .04 * math.sin(bt * 3))
    last = max([h for h in hits if h <= bt], default=None)
    nxt = min([h for h in hits if h > bt], default=None)
    # gap: 1 = fully apart, 0 = blades in contact
    if last is None:
        gap = 1 - ein((bt - 28) / (hits[0] - 28), 3)
    else:
        out_ = eout(clamp(since_hit(bt, last) / .22))           # kicked apart after the freeze
        if nxt is None:
            gap = .55 * out_ * math.exp(-max(0, since_hit(bt, last) - .3) * 2)
        else:
            span = nxt - last; w = clamp((bt - last) / span)
            amp = .75 if span >= 1 else .35
            gap = amp * out_ * (1 - ein(clamp((w - .45) / .55), 3))  # ...then slammed back together on the beat
    hs = 1500 + 650 * gap
    cam = Cam(1005, 400, hs); cam.rot = -8 + 3 * gap
    dt = since_hit(bt, last) if last is not None else -1
    if dt >= 0:
        sx, sy = cam.pt(930, 415); burst(img, sx, sy, dt, 520, seed=int(last * 2))
    closing = (last is None and bt > 28.5) or (nxt is not None and last is not None and bt - last > (nxt - last) * .6)
    v = 70 if (closing and gap > .05) else 0
    put_layer(img, 'clash_yotsumura', cam, dx=-190 * gap, dy=-40 * gap, rot=-6 * gap, rim=PAPER, rim_w=6,
              vel=(v, 0), ghosts=1 if v else 0)
    put_layer(img, 'clash_shishiba', cam, dx=190 * gap, dy=40 * gap, rot=6 * gap, rim=YEL, rim_w=6,
              vel=(-v, 0), ghosts=1 if v else 0)
    if dt >= 0:
        sx, sy = cam.pt(930, 415); sparks(img, sx, sy, dt, int(last * 2), 48)
    tag(img, 'YOTSUMURA', MX, 1500, eout((bt - 28.4) / .5), col=INK, bg=PAPER)
    tag(img, 'SHISHIBA', W - MX, 1570, eout((bt - 28.8) / .5), right=True)
    return img


def s_eyes(tl, u, bt):
    """Eyes lock: the authentic spread band on top, then the two eye strips slide in from opposite sides."""
    img = field(INK)
    band(img, 'ch100_010', (0, 0, 2133, 900), 520, u, z=(1.05, 1.15), drift=(-200, 0), h=760)
    a1 = eout((bt - 33.6) / .3); a2 = eout((bt - 34.2) / .3)
    band(img, 'ch100_010', (130, 930, 890, 175), 1080, u, z=(1.0, 1.06), slide=-W * (1 - a1), edge=YEL)
    band(img, 'ch100_010', (1110, 930, 890, 175), 1330, u, z=(1.0, 1.06), slide=W * (1 - a2), edge=YEL)
    return img


def s_noh(tl, u, bt):
    """Meanwhile, at the Noh stage. A breath of calm (drums drop out)."""
    img = tone(view('ch100_011', lerp(700, 760, eio(u)), lerp(330, 300, eio(u)), lerp(600, 560, eio(u)),
                    rect=(0, 0, 1150, 590)))
    return img


def s_krash(tl, u, bt):
    dt = since_hit(bt, 38)
    img = field(INK)
    top, bh = band(img, 'ch100_011', (100, 620, 1010, 370), 900, u, z=(1.1 + .12 * math.exp(-max(dt, 0) * 7), 1.2))
    shards(img, W * .55, top + 120, dt, 7, 24, PAPER)
    return img


def s_leap(tl, u, bt):
    """Onto the stage: Shishiba launches across the floor and lands the blow on 41; panel break-out."""
    img = yellow_field()
    hb = 41.0; dt = since_hit(bt, hb)
    pre = clamp((bt - 40) / (hb - 40))
    cam = Cam(600, 1390, 1150)
    # stage plate as a band; the fighter is drawn over its edges
    top, bh = band(img, 'ch100_011', (100, 1030, 1050, 750), 980, u, z=(1.0, 1.04), edge=INK)
    stage = np.zeros_like(img)
    lunge = ein(pre, 2.5) if bt < hb else 1
    dx = lerp(-520, 0, lunge) + recoil(dt, 30); dy = lerp(-260, 0, lunge) + recoil(dt, -20)
    put_layer(img, 'stage_shishiba', cam, dx=dx, dy=dy, sc=lerp(.8, 1.18, lunge), rot=lerp(-12, 0, lunge),
              vel=(140 * (1 - lunge) * 3, 70 * (1 - lunge) * 3), ghosts=3 if bt < hb else 0, rim=PAPER, rim_w=6)
    if dt >= 0:
        sx, sy = cam.pt(330, 1690); burst(img, sx, sy, dt, 420); ink_drops(img, sx, sy, dt, 3, 20)
    return img


def s_attack(tl, u, bt):
    dt = since_hit(bt, 45)
    if bt < 46:
        zo = 1 + .07 * math.exp(-max(dt, 0) * 7) if dt >= 0 else 1
        img = tone(view('ch100_014', lerp(330, 380, eio(u * 2)), 560, 1000 / zo, rect=(0, 0, 770, 1000)))
        if dt >= 0: burst(img, W * .45, H * .45, dt, 520)
        return img
    img = tone(view('ch100_014', 940, lerp(700, 760, eio((bt - 46) / 2)), lerp(600, 520, eio((bt - 46) / 2)),
                    rect=(770, 380, 345, 630)))
    tag(img, 'YOTSUMURA', MX, 1450, eout((bt - 46.3) / .5))
    return img


def s_disguise(tl, u, bt):
    """The Noh costume whips across the stage (SHFF); the camera tracks along it to Yotsumura waiting below."""
    img = field(INK)
    cam = Cam(lerp(330, 760, eio(u)), lerp(1440, 1480, eio(u)), lerp(700, 640, eio(u)))
    cam.rot = lerp(4, -2, eio(u))
    w = eout(u * 1.6, 3)
    put_layer(img, 'stage_disguise_plate', cam)
    put_layer(img, 'stage_yotsumura', cam, sc=1.0 + .08 * eio(u), dy=-10 * eio(u))
    put_layer(img, 'stage_disguise_pair', cam, dx=lerp(520, 0, w), dy=lerp(-110, 0, w), rot=lerp(12, 0, w) + 2 * math.sin(tl * 4),
              vel=(-120 * (1 - w), 0), ghosts=1 if w < .8 else 0)
    stamp(img, 'SHFF', W - MX, 260, 220, YEL, tl / .4, anchor=(1, 0), shadow=0)
    tag(img, 'THE NOH STAGE', MX, 1560, eout((bt - 49) / .5))
    return img


def s_reveal(tl, u, bt):
    """The disguise splits: Yotsumura's head and the costume burst toward camera together (never apart)."""
    img = yellow_field()
    hb = 52.0; dt = since_hit(bt, hb)
    burst_k = eout(clamp(dt / .25)) if dt >= 0 else 0
    cam = Cam(620, 560, lerp(1500, 1180, burst_k))
    focus_lines(img, *cam.pt(560, 560), int(bt * 15), 110, 300, INK, .7 * (1 - clamp(dt / 1.2)) if dt >= 0 else .3)
    sc = lerp(.75, 1.0, burst_k); d = lerp(160, 0, burst_k)
    for nm, extra in (('reveal_motion_trail', 1.0), ('reveal_disguise_cloth', 1.12), ('reveal_yotsumura_head', 1.0)):
        put_layer(img, nm, cam, dx=d * extra, dy=-d * .6 * extra, sc=sc, vel=(-70 * (1 - burst_k), 40 * (1 - burst_k)),
                  rim=PAPER if nm != 'reveal_motion_trail' else None, rim_w=5)
    if dt >= 0: ink_drops(img, *cam.pt(600, 600), dt, 9, 26)
    return img


def s_family(tl, u, bt):
    img = field(INK)
    band(img, 'ch100_015', (270, 1190, 660, 610), 820, u, z=(1.0, 1.08), drift=(0, 30),
         slide=W * (1 - eout(tl / .3)), edge=YEL)
    if bt >= 55:
        band(img, 'ch100_015', (75, 1190, 190, 610), 1510, (bt - 55), z=(1.0, 1.05), h=380,
             slide=-W * (1 - eout((bt - 55) / .3)), edge=None)
    return img


def s_mirror(tl, u, bt):
    """The hammer as a mirror: Yotsumura's face in the steel, a yellow glint sweeps the metal."""
    img = field(INK)
    cam = Cam(590, 210, lerp(760, 640, eio(u)))
    al = put_layer(img, 'hammer_reflection', cam)
    g = clamp((bt - 56.6) / 1.2)
    if 0 < g < 1:
        d = (_xx + _yy * .5) - lerp(-600, W + 1300, eio(g))
        glint = np.exp(-(d / 70) ** 2) * al * .85
        paste(img, PAPER, 0, 0, glint.astype(np.float32))
        paste(img, YEL, 0, 0, (np.exp(-(d / 220) ** 2) * al * .35).astype(np.float32))
    if bt >= 58:
        k = eout((bt - 58) / .3)
        band(img, 'ch100_016', (270, 1400, 930, 400), 1500, (bt - 58) / 2, z=(1.0, 1.06), slide=W * (1 - k), edge=YEL)
    return img


def s_hammer(tl, u, bt):
    """The hammer leaves the hand and spins toward the lens across a speed-line field."""
    img = field(PAPER)
    speed_lines(img, int(bt * 15), 20, 70, INK, .9)
    dt = since_hit(bt, 60)
    v = clamp(dt / b(4)) if dt >= 0 else 0
    cam = Cam(640, 620, 900)
    sc = lerp(1.0, 3.2, ein(v, 2)); rot = -720 * eout(v, 2)
    put_layer(img, 'hammer_flying', cam, dx=lerp(-200, 120, v), dy=lerp(-150, 140, v), sc=sc, rot=rot,
              vel=(40, 30), ghosts=2, rim=YEL, rim_w=6)
    stamp(img, 'THE HAMMER', MX, 200, 150, INK, (bt - 60.4) / .4, shadow=0)
    stamp(img, 'IS A MIRROR.', MX, 360, 150, YEL, (bt - 61.0) / .4, shadow=6)
    return img


def s_breath(tl, u, bt):
    img = field(INK)
    put(img, spr('...', DISPLAY, 120), W / 2, H / 2, PAPER, .8, (.5, .5))
    k = ein((bt - 65.4) / .6, 2)
    if k > 0:
        hw = k * W * .6; slab(img, W / 2 - hw, H / 2 + 120, hw * 2, 3 + 4 * k, YEL)
    return img


def s_impact(tl, u, bt):
    """The finishing blow. White frames, inverted frames, then the pair whips through; the ink arc blooms and
    droplets fall; hit-stop; long settle."""
    f = int(tl * FPS + .01)
    img = field(PAPER)
    dt = since_hit(bt, 66)
    k = eout(clamp(dt / .22))
    cam = Cam(1330 + 60 * eio(u), lerp(820, 860, eio(u)), lerp(1500, 1250, eio(u)))
    cam.rot = lerp(-4, 0, eout(dt / .6))
    speed_lines(img, int(bt * 15), -35, 30, YEL, .5 * (1 - u))
    put_layer(img, 'impact_ink_arc', cam, sc=lerp(.55, 1.0, k), a=clamp(dt / .1))
    put_layer(img, 'impact_pair', cam, dx=lerp(200, 0, k), dy=lerp(-160, 0, k), sc=lerp(.9, 1.0, k),
              rot=lerp(-9, 0, k), vel=(-220 * (1 - k), 160 * (1 - k)), ghosts=2 if k < .95 else 0)
    put_layer(img, 'impact_droplets', cam, dx=60 * eout(dt / 1.2), dy=120 * ein(dt / 1.2, 2), a=clamp(dt / .1))
    sx, sy = cam.pt(1300, 900)
    ink_drops(img, sx, sy, dt, 66, 46, ang=(-170, -60))
    ink_drops(img, sx, sy, dt - .12, 67, 22, ang=(-150, -90), size=(3, 12))
    ink_drops(img, sx + 120, sy - 300, (dt - .9) % 1.3, 68 + int((dt - .9) // 1.3), 14, spd=(200, 600), ang=(-120, -60))
    if bt > 69.5:
        k = eout((bt - 69.5) / .4)
        m = spr("BUT I'VE HAD ENOUGH.", DISPLAY, 110)
        slab(img, MX - 20, 1430 - 16, (m.shape[1] + 40) * k, m.shape[0] + 32, INK)
        put(img, m, MX, 1430, YEL, k, reveal=k)
    if f < 2: return field(PAPER)
    if f < 4: return 1 - img
    return img


def s_tired(tl, u, bt):
    """'...I get tired of trying to find a reason to kill you.' Slow push, no effects."""
    img = tone(view('ch100_017', 320, lerp(1040, 980, eio(u)), lerp(1060, 960, eio(u)), rect=(0, 570, 640, 1030)))
    return img


def s_title(tl, u, bt):
    img = field(INK)
    k = eout(tl / .5)
    top, bh = band(img, 'ch100_017', (650, 0, 1483, 1600), 640, u, z=(1.0, 1.06), h=900, a=k, edge=YEL)
    stamp(img, 'SAKAMOTO', MX, 1150, 215, PAPER, (bt - 80.6) / .5, shadow=0)
    stamp(img, 'DAYS', MX, 1375, 215, YEL, (bt - 81.0) / .5, shadow=0)
    put(img, spr('サカモトデイズ', JP, 52, vertical=True), W - 72, 1160, PAPER, eout((bt - 81.6) / .6) * .85, (.5, 0))
    a = eout((bt - 82.2) / .6)
    put(img, spr('CH.100  LIGHTNING STRIKES   ·   MANGA BY YUTO SUZUKI', LABEL, 30, 14), MX, 1660, PAPER, a * .8)
    put(img, spr('@inkframez', LABEL, 40, 20), MX, 1715, YEL, eout((bt - 82.8) / .6))
    return img


# (start beat, end beat, function, entering transition, transition beats)
SHOTS = [
    (0, 4, s_versus, None, 0),
    (4, 6, s_rooftop, 'flash', 0),
    (6, 8, s_vwam, 'cut', 0),
    (8, 10, s_shwoo, 'flash', 0),
    (10, 14, s_shaft, 'whipv', .6),
    (14, 16, s_bam, 'cut', 0),
    (16, 18, s_vwam2, 'slash-25', .7),
    (18, 20, s_house, 'whip', .6),
    (20, 24, s_passage, 'ink', 1.2),
    (24, 28, s_shing, 'flash', 0),
    (28, 33, s_clash, 'slash20', .7),
    (33, 36, s_eyes, 'cut', 0),
    (36, 38, s_noh, 'fade', .8),
    (38, 40, s_krash, 'flash', 0),
    (40, 44, s_leap, 'whip', .6),
    (44, 48, s_attack, 'slash-30', .7),
    (48, 52, s_disguise, 'whip', .6),
    (52, 54, s_reveal, 'flash', 0),
    (54, 56, s_family, 'cut', 0),
    (56, 60, s_mirror, 'ink', 1.0),
    (60, 64, s_hammer, 'flash', 0),
    (64, 66, s_breath, 'cut', 0),
    (66, 74, s_impact, 'cut', 0),
    (74, 80, s_tired, 'fade', 1.2),
    (80, NB + 3, s_title, 'ink', 1.4),
]
SHAKE = {5: 20, 14: 10, 14.5: 10, 15: 12, 15.5: 18, 24: 14, 29: 26, 31: 18, 32: 18, 32.5: 30, 38: 22, 41: 18,
         45: 16, 52: 20, 66: 48}
CHROMA = {5: 7, 29: 9, 32.5: 12, 52: 8, 66: 16}


def shot_at(bt):
    for i, s in enumerate(SHOTS):
        if s[0] <= bt < s[1]: return i
    return len(SHOTS) - 1


def draw(i, t):
    s = SHOTS[i]; tl = t - b(s[0]); u = tl / b(s[1] - s[0])
    return s[2](tl, u, t / BEAT)


def transition(i, t, img):
    s = SHOTS[i]; kind, dur = s[3], b(s[4]); tl = t - b(s[0])
    if kind in (None, 'cut') or i == 0: return img
    f = int(tl * FPS + .01)
    if kind == 'flash':
        return img * (1 - [.8, .35, 0][min(f, 2)]) + PAPER * [.8, .35, 0][min(f, 2)]
    if tl >= dur: return img
    u = tl / dur; P = draw(i - 1, t)
    if kind.startswith('slash'):
        ang = math.radians(float(kind[5:])); dx, dy = math.cos(ang), math.sin(ang)
        d = eout(u, 3) * 1600
        nrm = (_xx - W / 2) * -dy + (_yy - H / 2) * dx
        P1 = shift(P, dx * d, dy * d, -1); P2 = shift(P, -dx * d, -dy * d, -1)
        Q = np.where((nrm < 0)[..., None], P1, P2); out = np.where(Q[..., :1] >= 0, Q, img)
        w = max(0.0, 1 - u * 1.6)
        if w > 0:
            core = np.exp(-(nrm / (2 + 6 * w)) ** 2).astype(np.float32)
            paste(out, PAPER, 0, 0, core, w); paste(out, YEL, 0, 0, cv2.GaussianBlur(core, (0, 0), 16) * 3, w * .8)
        return out
    if kind in ('whip', 'whipv'):
        k = eio(u); off = k * (W if kind == 'whip' else H)
        if kind == 'whip':
            out = shift(P, -off, 0); out2 = shift(img, W - off, 0)
            m = (_xx >= W - off)[..., None]
            out = np.where(m, out2, out); out = cv2.blur(out, (int(10 + 120 * math.sin(math.pi * k)) | 1, 1))
        else:
            out = shift(P, 0, -off); out2 = shift(img, 0, H - off)
            m = (_yy >= H - off)[..., None]
            out = np.where(m, out2, out); out = cv2.blur(out, (1, int(10 + 160 * math.sin(math.pi * k)) | 1))
        return out
    if kind == 'ink':
        m = np.clip((u * 1.25 - INKF) / .05, 0, 1)[..., None]
        edge = np.clip(1 - np.abs(u * 1.25 - INKF - .03) / .03, 0, 1)[..., None]
        return (P * (1 - m) + img * m) * (1 - edge) + INK * edge
    if kind == 'fade':
        if u < .45: return P * (1 - u / .45) + INK * (u / .45)
        return img * min(1, (u - .45) / .4) + INK * (1 - min(1, (u - .45) / .4))
    return img


FAST = {10, 40, 48}          # sub-frame blur; never on flash / inverted / hit frames


def frame(fi):
    t = fi / FPS; bt = t / BEAT; i = shot_at(bt); s = SHOTS[i]
    n = 2 if (s[0] in FAST and .07 < t - b(s[0]) < .3) else 1
    acc = None
    for k in range(n):
        tk = max(b(s[0]), t - k / FPS / 2)
        im = transition(i, tk, draw(i, tk)); acc = im if acc is None else acc + im
    img = acc / n
    for h, amp in SHAKE.items():
        dt = t - b(h)
        if 0 <= dt < .7:
            a = amp * math.exp(-dt * 6.5)
            img = shift(img, a * math.sin(dt * 77), a * math.cos(dt * 59), float(INK[0]))
    for h, amp in CHROMA.items():
        dt = t - b(h)
        if 0 <= dt < .45: img = chroma(img, amp * math.exp(-dt * 8))
    img = img * VIG + GRAIN[fi % 3]
    if fi > NF - 12: img *= (NF - fi) / 12
    return np.clip(img, 0, 1)


def to8(img): return (img * 255 + .5).astype(np.uint8)
def frame_bytes(fi): return to8(frame(fi)).tobytes()
def frame_small(fi): return cv2.resize(to8(frame(fi)), (270, 480), interpolation=cv2.INTER_AREA)


def stills(times):
    d = HERE / 'stills_short'; d.mkdir(exist_ok=True)
    for t in times:
        cv2.imwrite(str(d / f'{t:06.2f}.png'), cv2.cvtColor(to8(frame(int(round(t * FPS)))), cv2.COLOR_RGB2BGR))
        print('still', t)


def sheet(step, workers, t0=0.0, t1=DUR):
    from multiprocessing import Pool
    times = [round(x, 3) for x in np.arange(t0, t1, step)]
    with Pool(workers) as p: ims = p.map(frame_small, [int(round(t * FPS)) for t in times])
    cols = 8; rows = (len(ims) + cols - 1) // cols; h, w = ims[0].shape[:2]
    sh = np.zeros((rows * (h + 22), cols * w, 3), np.uint8) + 30
    for k, (t, im) in enumerate(zip(times, ims)):
        r, c = divmod(k, cols); sh[r * (h + 22) + 22:r * (h + 22) + 22 + h, c * w:(c + 1) * w] = im
        cv2.putText(sh, f'{t:.2f}s b{t / BEAT:.1f}', (c * w + 4, r * (h + 22) + 16), cv2.FONT_HERSHEY_SIMPLEX, .45, (220, 220, 220), 1)
    d = HERE / 'stills_short'; d.mkdir(exist_ok=True)
    cv2.imwrite(str(d / 'sheet.jpg'), cv2.cvtColor(sh, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print('sheet', d / 'sheet.jpg')


def loudnorm_filter(ff):
    r = subprocess.run([ff, '-hide_banner', '-i', str(AUDIO), '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json',
                        '-f', 'null', '-'], capture_output=True, text=True)
    j = json.loads(r.stderr[r.stderr.rindex('{'):r.stderr.rindex('}') + 1])
    return (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
            f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")


def video(workers, out=OUT):
    from multiprocessing import Pool
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    if not AUDIO.exists(): sys.exit('run music_short.py first')
    af = loudnorm_filter(ff)
    cmd = [ff, '-y', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
           '-r', str(FPS), '-i', '-', '-i', str(AUDIO), '-af', af + ',aresample=48000', '-map', '0:v', '-map', '1:a',
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-tune', 'film', '-maxrate', '8M', '-bufsize', '16M',
           '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
           '-t', f'{NF / FPS:.3f}', str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(workers) as pool:
        for k, buf in enumerate(pool.imap(frame_bytes, range(NF), chunksize=3)):
            p.stdin.write(buf)
            if k % 60 == 0: print(f'frame {k}/{NF}', flush=True)
    p.stdin.close(); p.wait()
    print('wrote', out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['stills', 'sheet', 'video'])
    ap.add_argument('arg', nargs='?', default='')
    ap.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument('--from', dest='t0', type=float, default=0.0)
    ap.add_argument('--to', dest='t1', type=float, default=DUR)
    a = ap.parse_args()
    if a.mode == 'stills': stills([float(x) for x in a.arg.split(',')])
    elif a.mode == 'sheet': sheet(float(a.arg or 1), a.workers, a.t0, a.t1)
    else: video(a.workers)
