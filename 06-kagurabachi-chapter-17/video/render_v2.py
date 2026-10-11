"""Kagurabachi v2 - "Zero Distance". 33.5 s vertical Short, 1080x1920, 30 fps, cut to music_v2.py (160 BPM).

A rebuild of the v1 edit (render.py), designed around three rules:
  1. The art is the frame. Tall panels run full-bleed under a moving camera; wide panels become full-width bands
     on flat ink / crimson fields. No permanent HUD rails or footers eat the screen.
  2. One accent. Paper, ink and a single Kagurabachi crimson. Colour is used for meaning (time, energy, blood).
  3. Type belongs to the page. Big condensed type is printed *under* the ink (the drawing's black lines pass over
     it), the countdown uses the same seven-segment digits the manga draws, and the clock that opens the video
     flies into the corner and keeps counting the story's twelve seconds.
Motion: every cut lands on the beat with an expo-out camera (fast in, settle), sub-frame motion blur on the fast
moves, slash / ink / push / zoom-through transitions motivated by the action, and impact frames (white, inverted,
shake, chromatic split) on the hits listed in timeline_v2.HITS.

Usage (from this folder):
  python music_v2.py                          -> score_v2.wav
  python render_v2.py stills 1.2,9.5,24.1     -> stills_v2/*.png
  python render_v2.py sheet 1                 -> stills_v2/sheet.jpg (a frame every second)
  python render_v2.py video [--workers 3]     -> ../kagurabachi-short-v2.mp4
"""
import os, sys, math, json, subprocess, argparse
from functools import lru_cache
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
from timeline_v2 import BEAT, FPS, NB, DUR, HITS, GLITCH, clock_at, b

cv2.setNumThreads(1)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FD = 'C:/Windows/Fonts/' if os.name == 'nt' else str(ROOT.parent / 'fonts') + '/'   # tools/setup_fonts.py
DISPLAY = FD + 'impact.ttf'          # Impact on Windows; Anton elsewhere
LABEL = FD + 'bahnschrift.ttf'       # Bahnschrift on Windows; Barlow Condensed SemiBold elsewhere
JP = FD + ('NotoSerifJP-B.ttf' if os.path.exists(FD + 'NotoSerifJP-B.ttf') else 'yumindb.ttf')
W, H = 1080, 1920
NF = int(round(DUR * FPS))
OUT = ROOT / 'kagurabachi-short-v2.mp4'
AUDIO = HERE / 'score_v2.wav'


def hexc(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)
INK, PAPER, RED, RED_D = hexc('#0B0B0D'), hexc('#EFEAE0'), hexc('#E4002B'), hexc('#7A0016')
MX = 72                               # left margin of the type grid


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, c=1.0): return max(a, min(c, x))
def eout(u, p=4): return 1 - (1 - clamp(u)) ** p
def ein(u, p=3): return clamp(u) ** p
def eio(u): u = clamp(u); return u * u * (3 - 2 * u)
def lerp(a, c, u): return a + (c - a) * u
def eback(u, s=1.7): u = clamp(u) - 1; return 1 + (s + 1) * u ** 3 + s * u ** 2


# ---------------------------------------------------------------- fixed fields
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
def smooth_noise(scale, seed):
    r = np.random.default_rng(seed)
    n = r.random((H // scale + 3, W // scale + 3)).astype(np.float32)
    return cv2.resize(n, (W + 3 * scale, H + 3 * scale), interpolation=cv2.INTER_CUBIC)[:H, :W]
INKF = .55 * smooth_noise(160, 1) + .3 * smooth_noise(40, 2) + .15 * smooth_noise(9, 3)
INKF = (INKF - INKF.min()) / (INKF.max() - INKF.min())
_vr = np.sqrt(((_xx / W - .5) * 2) ** 2 * .7 + ((_yy / H - .5) * 2) ** 2 * .5)
VIG = (1 - .32 * np.clip(_vr - .45, 0, 1) ** 1.6)[..., None].astype(np.float32)
_g = np.random.default_rng(9)
GRAIN = [cv2.resize(_g.normal(0, .02, (H // 2, W // 2)).astype(np.float32), (W, H))[..., None] for _ in range(3)]


def field(col): return np.zeros((H, W, 3), np.float32) + col


# ---------------------------------------------------------------- pages and cameras
@lru_cache(maxsize=None)
def page(n, mip):
    """Greyscale page. mip 2 = 2x cubic upscale with an ink-sharpening unsharp mask (for close crops)."""
    g = cv2.imread(str(ROOT / 'panels' / f'{n:02}.png'), cv2.IMREAD_GRAYSCALE)
    if g is None: raise FileNotFoundError(n)
    if mip == 2:
        g = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        g = cv2.addWeighted(g, 1.7, cv2.GaussianBlur(g, (0, 0), 1.8), -.7, 0)
    return g


def view(n, cx, cy, hs, size=(W, H), rot=0.0, rect=None):
    """Luminance (0 ink .. 1 paper) of page n seen by a camera centred on (cx, cy) whose frame height covers
    hs page pixels. rect=(x, y, w, h) keeps the window inside a panel so gutters never show."""
    w, h = size; ws = hs * w / h
    if rect:
        x, y, rw, rh = rect
        pad = 1 + abs(math.sin(math.radians(rot))) * .6
        cx = clamp(cx, x + ws * pad / 2, x + rw - ws * pad / 2) if rw > ws * pad else x + rw / 2
        cy = clamp(cy, y + hs * pad / 2, y + rh - hs * pad / 2) if rh > hs * pad else y + rh / 2
    s = h / hs
    mip = 2 if s > 1.15 else 1
    src = page(n, mip); s /= mip
    M = cv2.getRotationMatrix2D((cx * mip, cy * mip), rot, s)
    M[0, 2] += w / 2 - cx * mip; M[1, 2] += h / 2 - cy * mip
    g = cv2.warpAffine(src, M, (w, h), flags=cv2.INTER_LINEAR if s > .8 else cv2.INTER_AREA,
                       borderMode=cv2.BORDER_CONSTANT, borderValue=255)
    if s < .8:    # downsampling: pre-blur the tones so screentone does not moire
        g = cv2.GaussianBlur(g, (0, 0), .45 / s)
    L = (g.astype(np.float32) / 255 - .07) / .86
    return np.clip(L, 0, 1)


def to_screen(px, py, cx, cy, hs, size=(W, H)):
    s = size[1] / hs
    return size[0] / 2 + (px - cx) * s, size[1] / 2 + (py - cy) * s


def tone(L, under=None):
    """Print the ink layer L over a paper layer (default plain paper). Anything drawn into `under` sits beneath
    the drawing: the black linework passes over it, white paper shows it."""
    U = (np.zeros(L.shape + (3,), np.float32) + PAPER) if under is None else under
    return INK + (U - INK) * L[..., None]


def cam(u, a, c, e=eout):
    k = e(u); return tuple(lerp(x, y, k) for x, y in zip(a, c))


def punch(t, hits, amt=.045, k=9.0):
    return 1 + sum(amt * math.exp(-(t - h) * k) for h in hits if t >= h)


# ---------------------------------------------------------------- compositing
def paste(dst, src, x, y, mask=None, a=1.0):
    """src HxWx3 (or colour + mask) onto dst at integer (x, y), clipped."""
    x, y = int(round(x)), int(round(y)); h, w = (mask if mask is not None else src).shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 <= x0 or y1 <= y0: return
    sl = (slice(y0 - y, y1 - y), slice(x0 - x, x1 - x))
    d = dst[y0:y1, x0:x1]
    s = src if src.ndim == 1 else src[sl]
    if mask is None: d[:] = d * (1 - a) + s * a if a < 1 else s; return
    m = mask[sl][..., None] * a
    d[:] = d * (1 - m) + s * m


@lru_cache(maxsize=512)
def spr(text, font, size, track=0.0, vertical=False):
    """Text mask (float32 0..1), tight-ish box. track = extra spacing in em/100."""
    f = ImageFont.truetype(font, size)
    if vertical:
        cw = size; ch = int(size * 1.05)
        im = Image.new('L', (cw + 8, ch * len(text) + 8)); d = ImageDraw.Draw(im)
        for i, c in enumerate(text): d.text((4 + cw / 2, 4 + i * ch + ch / 2), c, font=f, fill=255, anchor='mm')
    else:
        asc, desc = f.getmetrics()
        adv = [f.getlength(c) + track * size / 100 for c in text]
        wid = int(sum(adv) - (track * size / 100 if text else 0)) + 8
        im = Image.new('L', (max(1, wid), asc + desc + 8)); d = ImageDraw.Draw(im); x = 4
        for c, a in zip(text, adv): d.text((x, 4), c, font=f, fill=255); x += a
    m = np.asarray(im, np.float32) / 255
    ys, xs = np.nonzero(m > .02)
    if len(ys) == 0: return m
    return np.ascontiguousarray(m[max(0, ys.min() - 2):ys.max() + 3, max(0, xs.min() - 2):xs.max() + 3])


def put(dst, m, x, y, col, a=1.0, anchor=(0, 0), sc=1.0, rot=0.0, reveal=1.0, shadow=0):
    """Colour `col` through mask m. anchor (0..1, 0..1) picks the reference point; reveal wipes left->right."""
    if sc != 1 or rot:
        h, w = m.shape; R = cv2.getRotationMatrix2D((w / 2, h / 2), rot, sc)
        nw, nh = int(w * sc * 1.3 + 8), int(h * sc * 1.3 + 8)
        R[0, 2] += nw / 2 - w / 2; R[1, 2] += nh / 2 - h / 2
        m = cv2.warpAffine(m, R, (nw, nh), flags=cv2.INTER_LINEAR)
        x -= (nw - w * sc) / 2 + 0; y -= (nh - h * sc) / 2
        bw, bh = w * sc, h * sc
    else:
        bw, bh = m.shape[1], m.shape[0]
    if reveal < 1:
        m = m.copy(); m[:, int(m.shape[1] * clamp(reveal)):] = 0
    px, py = x - anchor[0] * bw, y - anchor[1] * bh
    if shadow: paste(dst, INK, px + shadow, py + shadow, m, a * .85)
    paste(dst, np.asarray(col, np.float32), px, py, m, a)
    return px, py, bw, bh


def bar_type(dst, m, x, y, col, u, bar=RED, anchor=(0, 0), sc=1.0, shadow=0):
    """Motion-graphics reveal: a bar sweeps in over the text box, then retracts to the right uncovering the text."""
    h, w = m.shape; bw, bh = w * sc, h * sc
    px, py = x - anchor[0] * bw, y - anchor[1] * bh
    if u <= 0: return
    a = eout(u / .45, 3); r = eout((u - .4) / .5, 3)
    if u > .4: put(dst, m, px, py, col, sc=sc, shadow=shadow)
    x0, x1 = px + bw * r, px + bw * a
    if x1 - x0 > 1:
        dst[int(max(0, py)):int(min(H, py + bh)), int(max(0, x0)):int(min(W, x1))] = bar


def tag(dst, text, x, y, a, right=False, size=32):
    """Small label set in paper on an ink tab, readable over any art."""
    if a <= 0: return
    m = spr(text, LABEL, size, 30); w = (m.shape[1] + 28) * eout(a / .6)
    slab(dst, x - w + 14 if right else x - 14, y - 10, w, m.shape[0] + 20, INK, .92)
    put(dst, m, x, y, PAPER, clamp((a - .3) / .7), (1 if right else 0, 0))


def slab(dst, x, y, w, h, col, a=1.0):
    x0, y0, x1, y1 = int(max(0, x)), int(max(0, y)), int(min(W, x + w)), int(min(H, y + h))
    if x1 > x0 and y1 > y0:
        dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - a) + np.asarray(col) * a


def poly_mask(pts, size=(W, H)):
    m = np.zeros((size[1], size[0]), np.uint8)
    cv2.fillPoly(m, [np.int32(np.round(pts))], 255, cv2.LINE_AA)
    return m.astype(np.float32) / 255


# ---------------------------------------------------------------- seven-segment clock (the manga's own digits)
SEG = {'0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc', '5': 'afgcd', '6': 'afgedc',
       '7': 'abc', '8': 'abcdefg', '9': 'abcdfg'}


@lru_cache(maxsize=256)
def seg_mask(text, hgt, lit=None):
    """Segment digits as bevelled hexagons. lit = frozenset of (char index, segment) to draw (None = all)."""
    dw, k, gap = hgt * .52, hgt * .1, hgt * .018
    cw = dw + hgt * .2
    width = int(sum(hgt * .22 if c == ':' else cw for c in text) + 8)
    m = np.zeros((int(hgt + 8), width), np.uint8)
    x = 4.0
    def hseg(x0, y0, x1):
        return [(x0 + gap, y0), (x0 + k / 2 + gap, y0 - k / 2), (x1 - k / 2 - gap, y0 - k / 2), (x1 - gap, y0),
                (x1 - k / 2 - gap, y0 + k / 2), (x0 + k / 2 + gap, y0 + k / 2)]
    def vseg(x0, y0, y1):
        return [(x0, y0 + gap), (x0 + k / 2, y0 + k / 2 + gap), (x0 + k / 2, y1 - k / 2 - gap), (x0, y1 - gap),
                (x0 - k / 2, y1 - k / 2 - gap), (x0 - k / 2, y0 + k / 2 + gap)]
    for i, c in enumerate(text):
        if c == ':':
            for q in (.3, .7):
                if lit is None or (i, ':') in lit:
                    cv2.circle(m, (int(x + hgt * .08), int(4 + hgt * q)), max(2, int(k * .55)), 255, -1, cv2.LINE_AA)
            x += hgt * .22; continue
        y0, ym, y1 = 4 + k / 2, 4 + hgt / 2, 4 + hgt - k / 2
        xl, xr = x + k / 2, x + dw - k / 2
        P = {'a': hseg(xl, y0, xr), 'g': hseg(xl, ym, xr), 'd': hseg(xl, y1, xr),
             'f': vseg(xl, y0, ym), 'b': vseg(xr, y0, ym), 'e': vseg(xl, ym, y1), 'c': vseg(xr, ym, y1)}
        for s in SEG.get(c, ''):
            if lit is None or (i, s) in lit:
                cv2.fillPoly(m, [np.int32(np.round(np.array(P[s]) * 4))], 255, cv2.LINE_AA, shift=2)
        x += cw
    return m.astype(np.float32) / 255


def clock_text(v): q = max(0, int(round(v * 100))); return f'{q // 100:02}:{q % 100:02}'


# ---------------------------------------------------------------- graphic FX
def focus_lines(dst, cx, cy, seed, n=90, r0=420, col=None, a=1.0, thick=1.0):
    """Manga focus lines (shuchusen) toward (cx, cy), redrawn on twos."""
    r = np.random.default_rng(seed); m = np.zeros((H, W), np.uint8); R = 2400
    for _ in range(n):
        ang = r.uniform(0, 2 * np.pi); wid = r.uniform(.004, .016) * thick
        ri = r0 * r.uniform(.85, 1.6)
        p = [(cx + math.cos(ang) * ri, cy + math.sin(ang) * ri),
             (cx + math.cos(ang - wid) * R, cy + math.sin(ang - wid) * R),
             (cx + math.cos(ang + wid) * R, cy + math.sin(ang + wid) * R)]
        cv2.fillPoly(m, [np.int32(p)], 255, cv2.LINE_AA)
    paste(dst, INK if col is None else np.asarray(col), 0, 0, m.astype(np.float32) / 255, a)


def speed_lines(dst, seed, y0, y1, a=1.0, col=None, n=40):
    r = np.random.default_rng(seed); m = np.zeros((H, W), np.uint8)
    for _ in range(n):
        y = r.uniform(y0, y1); x = r.uniform(-300, W); ln = r.uniform(200, 900); th = r.uniform(1, 5)
        cv2.line(m, (int(x), int(y)), (int(x + ln), int(y)), 255, int(th), cv2.LINE_AA)
    paste(dst, PAPER if col is None else np.asarray(col), 0, 0, m.astype(np.float32) / 255, a)


def bolt_pts(p0, p1, seed, rough=.22, depth=6):
    r = np.random.default_rng(seed); pts = [np.array(p0, float), np.array(p1, float)]
    for d in range(depth):
        out = [pts[0]]
        for a, c in zip(pts, pts[1:]):
            mid = (a + c) / 2; v = c - a; nrm = np.array([-v[1], v[0]])
            mid = mid + nrm * r.normal(0, rough / (1.35 ** d)) * .5
            out += [mid, c]
        pts = out
    return np.int32(np.round(pts))


def lightning(dst, bolts, a=1.0):
    """bolts: list of (p0, p1, seed). Crimson glow + paper core, added on top."""
    core = np.zeros((H, W), np.uint8)
    for p0, p1, seed in bolts:
        pts = bolt_pts(p0, p1, seed)
        cv2.polylines(core, [pts], False, 255, 3, cv2.LINE_AA)
        r = np.random.default_rng(seed + 7)
        for _ in range(3):    # branches
            i = r.integers(4, len(pts) - 4); q = pts[i]
            e = q + r.normal(0, 140, 2)
            cv2.polylines(core, [bolt_pts(q, e, seed + i, .3, 4)], False, 255, 1, cv2.LINE_AA)
    c = core.astype(np.float32) / 255
    glow = cv2.GaussianBlur(c, (0, 0), 9) * 2.2
    paste(dst, RED, 0, 0, np.clip(glow, 0, 1), a * .9)
    paste(dst, PAPER, 0, 0, c, a)


def chroma(img, k):
    if k < .5: return img
    k = int(round(k)); out = img.copy()
    out[:, k:, 0] = img[:, :-k, 0]; out[:, :-k, 2] = img[:, k:, 2]
    return out


def shift(img, dx, dy, fill=-1.0):
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_CONSTANT, borderValue=(fill, fill, fill))


def zoom_img(img, s, cx=W / 2, cy=H / 2):
    M = cv2.getRotationMatrix2D((cx, cy), 0, s)
    return cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)


def lum(img): return img @ np.float32([.3, .59, .11])


# ---------------------------------------------------------------- layout blocks
def band(dst, n, rect, yc, u=0.0, z=(1.0, 1.08), drift=(0, 0), slide=0.0, under=None, edge=None, a=1.0):
    """A wide panel as a full-width band centred at yc. The band shows `rect` scaled to the frame width; z zooms
    inside it over u, drift pans (page px). slide offsets it horizontally (px); edge draws a rule under it."""
    x, y, rw, rh = rect; bh = int(round(W * rh / rw))
    zz = lerp(z[0], z[1], eio(u))
    L = view(n, x + rw / 2 + drift[0] * (u - .5), y + rh / 2 + drift[1] * (u - .5), rh / zz, (W, bh), rect=rect)
    img = tone(L, under)
    top = yc - bh / 2
    if abs(slide) > 2:   # horizontal motion blur while it slides
        img = cv2.blur(img, (int(min(81, abs(slide) * .08)) | 1, 1))
    paste(dst, img, slide, top, a=a)
    if edge is not None:
        slab(dst, slide, top + bh - 4, W, 8, edge, a)
    return top, bh


def card(dst, n, rect, xc, yc, hgt, u=0.0, z=(1.0, 1.05), rot=0.0, border=PAPER):
    x, y, rw, rh = rect; wd = int(round(hgt * rw / rh))
    zz = lerp(z[0], z[1], eio(u))
    L = view(n, x + rw / 2, y + rh / 2, rh / zz, (wd, hgt), rect=rect)
    img = tone(L)
    b_ = 6; fr = np.zeros((hgt + 2 * b_, wd + 2 * b_, 3), np.float32) + border; fr[b_:-b_, b_:-b_] = img
    if rot:
        R = cv2.getRotationMatrix2D((fr.shape[1] / 2, fr.shape[0] / 2), rot, 1)
        msk = cv2.warpAffine(np.ones(fr.shape[:2], np.float32), R, (fr.shape[1], fr.shape[0]))
        fr = cv2.warpAffine(fr, R, (fr.shape[1], fr.shape[0]))
    else:
        msk = np.ones(fr.shape[:2], np.float32)
    paste(dst, INK * .0, xc - fr.shape[1] / 2 + 18, yc - fr.shape[0] / 2 + 24, msk, .6)
    paste(dst, fr, xc - fr.shape[1] / 2, yc - fr.shape[0] / 2, msk)


def full(n, rect, c0, c1, tl, dur, e=eout, rot=(0, 0), under=None, hits=()):
    """Full-bleed camera move from c0 to c1 = (cx, cy, hs) over `dur` s, with beat punches."""
    u = tl / dur
    cx, cy, hs = cam(u, c0, c1, e)
    hs /= punch(tl, hits)
    L = view(n, cx, cy, hs, rot=lerp(rot[0], rot[1], e(u)), rect=rect)
    return tone(L, under), (cx, cy, hs)


# ---------------------------------------------------------------- the shots (beats; each returns an RGB frame)
def s_open(tl, u, bt):
    img = field(INK)
    # Segments of 12:00 light up in a shuffled order over the first two ticks; each flashes paper, then crimson.
    txt = '12:00'; hgt = 250
    allseg = [(i, s) for i, c in enumerate(txt) for s in (SEG.get(c, ':') if c != ':' else ':')]
    order = np.random.default_rng(12).permutation(len(allseg))
    times = {allseg[j]: b(2.0) * (k / len(allseg)) for k, j in enumerate(order)}
    lit = frozenset(s for s, t0 in times.items() if tl >= t0)
    fresh = frozenset(s for s, t0 in times.items() if 0 <= tl - t0 < 2.5 / FPS)
    fly = eio((bt - 3.4) / .6)
    if fly <= 0:
        full_m = seg_mask(txt, hgt, lit)
        pulse = 1 + .025 * math.exp(-((bt % 1) * 6)) if bt > 2 else 1
        mw = seg_mask(txt, hgt).shape[1]
        x, y = W / 2 - mw / 2 * pulse, 860 - hgt / 2 * pulse
        put(img, full_m, x, y, RED, sc=pulse)
        if fresh: put(img, seg_mask(txt, hgt, fresh), x, y, PAPER, sc=pulse)
        a = eout((bt - .5) / 1.5)
        put(img, spr('KAGURABACHI  —  CHAPTER 17', LABEL, 34, 30), W / 2, 640, PAPER, a * .7, (.5, .5))
        put(img, spr('SECONDS ON THE CLOCK', LABEL, 34, 30), W / 2, 1080, PAPER, eout((bt - 1.5) / 1) * .7, (.5, .5))
        put(img, spr('十二秒', JP, 50, vertical=True), 1000, 860, RED, eout((bt - 2) / 1), (.5, .5))
    return img


def hud(img, bt, scale=1.0, x=MX, y=118, a=1.0):
    """Corner countdown: seven-segment story clock + twelve ticks for the twelve seconds."""
    v = clock_at(bt); txt = clock_text(v); hgt = int(56 * scale)
    m = seg_mask(txt, hgt)
    blink = 1.0 if v > 0 or int(bt * 2) % 2 == 0 else .35
    put(img, m, x, y, RED, a * blink, shadow=3)
    for i in range(12):
        on = v > i
        slab(img, x + i * 13 * scale, y + hgt + 14 * scale, 6 * scale, 16 * scale, PAPER if on else PAPER * .3,
             a * (.95 if on else .5))


def s_castle(tl, u, bt):
    img = field(INK)
    rect = (0, 130, 1000, 468)
    # the band bleeds in through an ink mask
    full_ = img.copy()
    top, bh = band(full_, 1, rect, 930, u, z=(1.0, 1.1), drift=(-60, 0))
    k = eout(tl / .5, 2)
    msk = np.clip((k * 1.25 - INKF) / .06, 0, 1)[..., None]
    img = img * (1 - msk) + full_ * msk
    bar_type(img, spr('TWELVE', DISPLAY, 250), MX, top - 40, PAPER, (bt - 4.1) / 1.0, anchor=(0, 1))
    bar_type(img, spr('SECONDS.', DISPLAY, 250), MX, top + bh + 40, RED, (bt - 5.0) / 1.0, bar=PAPER)
    put(img, spr('ONE OPENING.', LABEL, 46, 40), MX, top + bh + 330, PAPER, eout((bt - 6.2) / .8), reveal=eout((bt - 6.2) / .8))
    return img


def s_contact(tl, u, bt):
    rect = (0, 782, 1000, 818)
    img, c = full(1, rect, (760, 1000, 600), (330, 1190, 818), tl, b(4), hits=[0])
    if tl < .7:
        sx, sy = to_screen(560, 1000, *c)
        focus_lines(img, sx, sy, int(tl * 15), n=70, r0=520, col=PAPER, a=.85 * (1 - tl / .7))
    bar_type(img, spr('FIRST CONTACT', DISPLAY, 150), MX, 1340, PAPER, (bt - 9) / .9, shadow=7)
    tag(img, '12:00  /  11:52', MX, 1520, eout((bt - 9.8) / .5))
    return img


def s_versus(tl, u, bt):
    img = field(INK)
    sA = -W * (1 - eout(tl / .32))
    sB = W * (1 - eout((tl - b(1)) / .32)) if bt >= 13 else W
    top = view(2, 740 - 40 * u, 1320, 520, (W, 1060))
    bot = view(2, 1760 + 40 * u, 1330, 470, (W, 1060))
    tA = tone(top); tB = tone(bot)
    mA = poly_mask([(0, 0), (W, 0), (W, 860), (0, 1060)])
    mB = poly_mask([(0, 1060 + 6), (W, 860 + 6), (W, H), (0, H)])
    A = np.zeros_like(img); paste(A, tA, sA, 0)
    B = np.zeros_like(img); paste(B, tB, sB, 860)
    mA2 = shift(mA[..., None].repeat(3, 2), sA, 0, 0)[..., 0]
    mB2 = shift(mB[..., None].repeat(3, 2), sB, 0, 0)[..., 0]
    img = img * (1 - mA2[..., None]) + A * mA2[..., None]
    img = img * (1 - mB2[..., None]) + B * mB2[..., None]
    if bt >= 13:
        seam = poly_mask([(0, 1052), (W, 852), (W, 868), (0, 1068)])
        paste(img, RED, 0, 0, seam, eout((tl - b(1)) / .2))
    ka = eout((bt - 12.3) / .5); kb = eout((bt - 13.3) / .5)
    put(img, spr('SOJO', DISPLAY, 230), MX + (1 - ka) * -120, 760, PAPER, ka, (0, 1), shadow=6)
    tag(img, 'WIELDER OF CLOUD GOUGER', MX, 790, ka)
    put(img, spr('CHIHIRO', DISPLAY, 230), W - MX + (1 - kb) * 120, 1150, PAPER, kb, (1, 0), shadow=6)
    tag(img, 'WIELDER OF ENTEN', W - MX, 1400, kb, right=True)
    return img


def s_fall(tl, u, bt):
    img, _ = full(2, (445, 0, 555, 1040), (560, 470, 800), (640, 520, 975), tl, b(2), rot=(-5, 0))
    return img


def s_clash(tl, u, bt):
    img, _ = full(3, (0, 0, 1067, 975), (330, 500, 900), (720, 487, 975), tl, b(2))
    return img


def s_shup(tl, u, bt):
    img = field(INK)
    speed_lines(img, int(tl * 15), 0, H, .35, PAPER, 60)
    k = eback(tl / .22, 2.2)
    band(img, 3, (40, 1005, 1000, 215), 960, u, z=(1.25 + .3 * (1 - k), 1.3), drift=(120, 0), edge=RED)
    return img


def s_leap(tl, u, bt):
    rect = (0, 380, 1067, 950)
    img, c = full(6, rect, (330, 900, 760), (560, 830, 950), tl, b(3))
    sx, sy = to_screen(400, 660, *c)
    focus_lines(img, sx, sy, int(tl * 15), n=60, r0=480, col=INK, a=.55 * (1 - eio(u)))
    return img


def s_arm(tl, u, bt):
    img = field(INK)
    top, bh = band(img, 5, (0, 0, 1000, 640), 840, u, z=(1.0, 1.16), drift=(140, 60), slide=-W * (1 - eout(tl / .3)))
    bar_type(img, spr('AN ARM', DISPLAY, 230), MX, top - 50, PAPER, (bt - 24.2) / .9, anchor=(0, 1))
    bar_type(img, spr('FOR AN ANGLE.', DISPLAY, 150), MX, top + bh + 50, RED, (bt - 25.0) / .9, bar=PAPER)
    put(img, spr('09:04  —  HE SACRIFICED HIS ARM TO CHANGE THE TRAJECTORY', LABEL, 30, 12), MX, top + bh + 260,
        PAPER, eout((bt - 25.6) / .6) * .85, reveal=eout((bt - 25.6) / .6))
    return img


def s_faster(tl, u, bt):
    img = field(INK)
    out = ein((bt - 31.35) / .65, 2)          # everything is shoved up and out on the last beat
    lift = -out * 1700
    def enter(at, side):
        return side * W * (1 - eout((bt - at) / .3)) if bt < at + .3 else 0
    bands = [(27, -1, 5, (0, 668, 1000, 255), 430, (0, 0)), (28, 1, 5, (0, 948, 1000, 222), 735, (0, 0)),
             (29, 0, 4, (0, 672, 1067, 145), 975, (0, 0)), (30, -1, 4, (90, 242, 977, 198), 1200, (0, 0))]
    for k, (at, side, n, rect, yc, dr) in enumerate(bands):
        if bt < at: continue
        if side == 0:   # 07:68 slams in from scale with a flash
            s_ = 1 + .5 * (1 - eout((bt - at) / .25))
            tmp = field(INK); band(tmp, n, rect, H / 2, (bt - at) / 3, z=(1, 1.04))
            tmp = zoom_img(tmp, s_)
            hh = int(W * rect[3] / rect[2] * s_) + 10
            y0 = int(yc + lift * (1 + k * .08) - hh / 2)
            paste(img, tmp[int(H / 2 - hh / 2):int(H / 2 + hh / 2)], 0, y0)
            if (bt - at) * BEAT < 2 / FPS: slab(img, 0, y0, W, hh, PAPER, .8)
        else:
            band(img, n, rect, yc + lift * (1 + k * .08), (bt - at) / 4, z=(1, 1.06), drift=(40 * side, 0),
                 slide=enter(at, side))
    put(img, spr('FASTER THAN BEFORE.', LABEL, 38, 30), MX, 1390 + lift, PAPER, eout((bt - 30.4) / .5) * .9,
        reveal=eout((bt - 30.4) / .5))
    return img


def s_tricks(tl, u, bt):
    img = field(RED)
    rise = H * (1 - eout(tl / .35))
    top, bh = band(img, 7, (0, 178, 975, 625), 1060 + rise, u, z=(1.0, 1.12), drift=(260, 0), edge=INK)
    word = 'PRIDE.' if bt < 34 else 'TRICKS.'
    k = eout((bt - (32.15 if bt < 34 else 34)) / .3)
    put(img, spr('NO MORE', DISPLAY, 200), MX, 300 + rise * .6, INK, eout((bt - 32.1) / .3))
    m = spr(word, DISPLAY, 200)
    if bt >= 34 and bt < 34.2:   # glitch swap
        put(img, m, MX + 22, 510, PAPER, .6); put(img, m, MX - 14, 510, INK, .5)
    put(img, m, MX, 510 + (1 - k) * 60, PAPER, k)
    put(img, spr('SOJO DROPS EVERYTHING ELSE', LABEL, 34, 30), MX, top + bh + 60, INK, eout((bt - 33) / .5) * .9)
    return img


def s_double(tl, u, bt):
    img = field(INK)
    top, bh = band(img, 7, (0, 1122, 975, 478), 1215, u, z=(1.0, 1.1), drift=(-120, 0), edge=RED)
    # 06:00 -> glitch -> 03:00
    v = clock_at(bt); txt = clock_text(v)
    m = seg_mask(txt, 150)
    x = W / 2 - m.shape[1] / 2
    g = 0 < bt - GLITCH < .5
    if g:
        r = np.random.default_rng(int(bt * 60))
        for _ in range(3): put(img, seg_mask(clock_text(6.0), 150), x + r.uniform(-40, 40), 200 + r.uniform(-14, 14), PAPER, .35)
    put(img, m, x, 200, RED if not g else PAPER)
    put(img, spr('2×', DISPLAY, 520), W / 2, 450, RED, eout((bt - 36.2) / .3), (.5, 0), sc=1 + .25 * (1 - eout((bt - 36.2) / .3)))
    put(img, spr('TWICE THE SPIRIT ENERGY HIS BODY ALLOWS', LABEL, 32, 16), W / 2, top - 46, PAPER,
        eout((bt - 37) / .6) * .9, (.5, 1))
    pw = eio((bt - 36) / 2) * .8 + .2
    if int(bt * 8) % 3 != 1:
        s0 = int(bt * 8)
        lightning(img, [((0, top + r_ * 30), (W, top + 40 - r_ * 30), s0 + r_) for r_ in range(2)] +
                       [((0, top + bh - 20), (W, top + bh + 30), s0 + 9)], pw)
    return img


def s_triple(tl, u, bt):
    img = field(PAPER)
    card(img, 8, (5, 540, 595, 460), W / 2, 1110, 640, u, z=(1.0, 1.06), rot=-2 + 2 * eout(tl / .3))
    k = eout(tl / .25)
    put(img, spr('3×', DISPLAY, 560), MX - 10, 250, RED, k, sc=1 + .3 * (1 - k))
    put(img, spr('CHIHIRO  —  THREE TIMES HIS LIMIT', LABEL, 34, 24), MX, 1480, INK, eout((bt - 40.4) / .4))
    return img


def s_above(tl, u, bt):
    rect = (600, 0, 1225, 1200)
    if bt < 44:
        img, c = full(8, rect, (930, 300, 520), (960, 330, 470), tl, b(2), e=eio)
        if int(bt * 10) % 2 == 0:
            lightning(img, [((0, 300), (W, 1200), int(bt * 10)), ((W, 200), (300, H), int(bt * 10) + 3)], .7)
    else:
        img, c = full(8, rect, (960, 330, 470), (1120, 600, 1200), tl - b(2), b(4), hits=[0])
        sx, sy = to_screen(940, 600, *c)
        focus_lines(img, sx, sy, int(tl * 15), n=110, r0=560, col=INK, a=.75 * (1 - eout((bt - 44) / 3)))
        k = (bt - 44.15) / .8
        bar_type(img, spr('FROM ABOVE', DISPLAY, 210), MX, 1260, RED, k, bar=INK)
    return img


def s_react(tl, u, bt):
    img, c = full(9, (0, 0, 1067, 1230), (330, 620, 1000), (620, 600, 1230), tl, b(4), hits=[0])
    if bt > 49:
        k = eout((bt - 49) / .4)
        m = spr('HE CAN STILL REACT.', LABEL, 54, 20)
        slab(img, MX - 18, 1400 - 14, (m.shape[1] + 36) * k, m.shape[0] + 28, INK, .92)
        put(img, m, MX, 1400, PAPER, k, reveal=k)
    return img


def s_faces(tl, u, bt):
    img = field(INK)
    dim = .45 * eout((bt - 54) / .3) if bt >= 54 else 0
    band(img, 9, (40, 1262, 1000, 338), 620, (bt - 52) / 4, z=(1.05, 1.15), drift=(-40, 0),
         slide=-W * (1 - eout(tl / .3)), edge=RED)
    if dim: slab(img, 0, 400, W, 440, INK, dim)
    if bt >= 54:
        band(img, 12, (0, 662, 1000, 566), 1185, (bt - 54) / 2, z=(1.0, 1.12), drift=(80, 30),
             slide=W * (1 - eout((bt - 54) / .3)))
        if bt - 54 < 2 / FPS / BEAT: slab(img, 0, 900, W, 620, PAPER, .7)
    return img


def s_kuro(tl, u, bt):
    rect = (250, 0, 817, 1200)
    under = field(PAPER)
    if bt >= 58:
        k = eout((bt - 58) / .35)
        put(under, spr('KURO.', DISPLAY, 360), MX, 1020 + (1 - k) * 80, RED, k)
    img, c = full(10, rect, (650, 560, 960), (640, 600, 1190), tl, b(4), e=eio, under=under)
    put(img, spr('HE LETS GO OF NISHIKI.', LABEL, 40, 26), MX, 280, INK, eout((bt - 56.5) / .5),
        reveal=eout((bt - 56.5) / .5))
    return img


def s_timing(tl, u, bt):
    img = field(INK)
    top, bh = band(img, 10, (330, 1217, 670, 383), 900, u, z=(1.0, 1.08), edge=RED)
    g = 1 - eout(tl / .45)
    if g > .02:   # the timing skews: horizontal slices slide out of register
        r = np.random.default_rng(int(tl * 30))
        for _ in range(9):
            y0 = int(r.uniform(top, top + bh - 40)); hh = int(r.uniform(12, 70)); dx = int(r.uniform(-90, 90) * g)
            img[y0:y0 + hh] = np.roll(img[y0:y0 + hh], dx, axis=1)
    put(img, spr('THE TIMING BREAKS.', DISPLAY, 120), MX, top + bh + 60, PAPER, eout((bt - 60.4) / .4),
        reveal=eout((bt - 60.4) / .4))
    return img


def s_vacuum(tl, u, bt):
    img = field(INK)
    txt = clock_text(clock_at(bt)); m = seg_mask(txt, 130)
    put(img, m, W / 2, 900, RED, 1, (.5, .5))
    put(img, spr('ZERO DISTANCE', LABEL, 34, 60), W / 2, 1050, PAPER, .75, (.5, .5))
    put(img, spr('零距離', JP, 48, vertical=True), 978, 900, PAPER, .5, (.5, .5))
    k = ein((bt - 63.3) / .7, 2)
    if k > 0:   # the edge: a single line opens across the frame
        hw = k * W * .6
        slab(img, W / 2 - hw, 1180, hw * 2, 3 + 3 * k, PAPER)
        glow = np.zeros((H, W), np.float32); glow[1170:1195, int(W / 2 - hw):int(W / 2 + hw)] = 1
        paste(img, RED, 0, 0, cv2.GaussianBlur(glow, (0, 0), 14) * 1.5 * k, .8)
    return img


def s_impact(tl, u, bt):
    rect = (468, 0, 1665, 1225)
    img, c = full(11, rect, (1420, 840, 860), (1180, 640, 1225), tl, b(4))
    f = int(tl * FPS + .01)
    if f < 2: return field(PAPER)
    if f < 4: return 1.0 - img
    return img


def s_gouger(tl, u, bt):
    rect = (0, 0, 1067, 1600)
    img, c = full(13, rect, (760, 330, 900), (533, 800, 1600), tl, b(4))
    sp = eout((bt - 70) / .6) if bt >= 70 else 0
    lines = [('CLOUD', 1050), ('GOUGER', 1290)]
    ang = math.radians(-28); dx, dy = math.cos(ang), math.sin(ang)
    k = eout((bt - 68.2) / .35)
    layer = np.zeros((H, W, 1), np.float32)
    for word, y in lines:
        paste(layer, np.float32([1]), MX, y, spr(word, DISPLAY, 250))
    layer = layer[..., 0]
    nrm = (_xx - W / 2) * -dy + (_yy - 1260) * dx
    side = (nrm > 0).astype(np.float32)
    if sp > 0:
        d = sp * 70
        A = shift((layer * side)[..., None].repeat(3, 2), dx * d, dy * d, 0)[..., 0]
        B = shift((layer * (1 - side))[..., None].repeat(3, 2), -dx * d, -dy * d, 0)[..., 0]
        layer = A + B
    sh = shift(layer[..., None].repeat(3, 2), 7, 7, 0)[..., 0]
    paste(img, INK, 0, 0, sh * k, .8)
    paste(img, PAPER, 0, 0, layer * k)
    if 0 <= bt - 70 < .5:
        w_ = 1 - (bt - 70) / .5
        line = np.exp(-(nrm / (3 + 10 * w_)) ** 2) * (np.abs((_xx - W / 2) * dx + (_yy - 1260) * dy) < 900 * eout((bt - 70) / .15))
        paste(img, PAPER, 0, 0, line.astype(np.float32), 1)
        paste(img, RED, 0, 0, cv2.GaussianBlur(line.astype(np.float32), (0, 0), 12) * 2 * w_, .9)
    if bt >= 70.4:
        put(img, spr('BROKEN.', DISPLAY, 120), MX, 1560 - 30, RED, eout((bt - 70.4) / .3), (0, 0), shadow=4)
    return img


def s_hilt(tl, u, bt):
    img, _ = full(11, (0, 0, 452, 1600), (226, 420, 800), (226, 1180, 800), tl, b(3), e=eio)
    return img


def s_price(tl, u, bt):
    img, _ = full(14, (322, 0, 650, 805), (640, 360, 700), (610, 400, 805), tl, b(3))
    k = eout((bt - 75.4) / .4)
    m = spr('THE PRICE.', DISPLAY, 150)
    slab(img, MX - 22, 1300 - 18, (m.shape[1] + 44) * k, m.shape[0] + 36, INK, .95)
    put(img, m, MX, 1300, PAPER, k, reveal=k)
    return img


def s_stand(tl, u, bt):
    img = field(INK)
    card(img, 14, (358, 860, 440, 740), W / 2, 860, 1220, u, z=(1.0, 1.07))
    return img


def s_end(tl, u, bt):
    img = field(INK)
    k0 = eout(tl / .5)
    top, bh = band(img, 12, (0, 1292, 1000, 308), 520 - (1 - k0) * 80, u, z=(1.0, 1.06), a=k0, edge=RED)
    bar_type(img, spr('KAGURA', DISPLAY, 270), MX, 760, PAPER, (bt - 81.6) / .9)
    bar_type(img, spr('BACHI', DISPLAY, 270), MX, 1030, RED, (bt - 82.0) / .9, bar=PAPER)
    put(img, spr('カグラバチ', JP, 56, vertical=True), 978, 1040, PAPER, eout((bt - 82.6) / .6) * .8, (.5, .5))
    ka = eout((bt - 83) / .6)
    put(img, spr('CH.17 TEA  /  CH.18 ROAR   ·   MANGA BY TAKERU HOKAZONO', LABEL, 30, 14), MX, 1330, PAPER, ka * .75)
    put(img, spr('TWELVE SECONDS. ONE OPENING.', LABEL, 40, 30), MX, 1390, PAPER, ka)
    put(img, spr('@inkframez', LABEL, 40, 20), MX, 1460, RED, eout((bt - 83.6) / .6))
    return img


# (start beat, end beat, function, entering transition, transition beats, hud?)
SHOTS = [
    (0, 4, s_open, None, 0, False),
    (4, 8, s_castle, None, 0, True),
    (8, 12, s_contact, 'flash', 0, True),
    (12, 16, s_versus, 'flash', 0, True),
    (16, 18, s_fall, 'invert', 0, True),
    (18, 20, s_clash, 'slash-20', .7, True),
    (20, 21, s_shup, 'cut', 0, True),
    (21, 24, s_leap, 'zoom', .6, True),
    (24, 27, s_arm, 'flash', 0, True),
    (27, 32, s_faster, 'push', .7, True),
    (32, 36, s_tricks, 'cut', 0, True),
    (36, 40, s_double, 'slash80', .7, False),
    (40, 42, s_triple, 'flash', 0, True),
    (42, 48, s_above, 'zoom', .6, True),
    (48, 52, s_react, 'cut', 0, True),
    (52, 56, s_faces, 'push', .7, True),
    (56, 60, s_kuro, 'redflash', 1.6, True),
    (60, 62, s_timing, 'cut', 0, True),
    (62, 64, s_vacuum, 'cut', 0, False),
    (64, 68, s_impact, 'cut', 0, True),
    (68, 72, s_gouger, 'slash-30', .8, True),
    (72, 75, s_hilt, 'ink', 1.4, True),
    (75, 78, s_price, 'cut', 0, True),
    (78, 81, s_stand, 'push', .7, True),
    (81, NB + 1, s_end, 'fade', 1.0, True),
]
FAST = {21, 42}          # cuts whose first frames get sub-frame motion blur (never on flash / slash / impact frames)
SHAKE = {48: 18, 64: 46, 44: 14, 29: 10, 8: 12}
CHROMA = {48: 9, 64: 16, 40: 7, 8: 6}


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
        return img * (1 - [.85, .4, 0][min(f, 2)]) + PAPER * [.85, .4, 0][min(f, 2)]
    if kind == 'invert':
        return 1 - img if f < 2 else img
    if tl >= dur: return img
    u = tl / dur
    P = draw(i - 1, t)
    if kind.startswith('slash'):
        ang = math.radians(float(kind[5:])); dx, dy = math.cos(ang), math.sin(ang)
        d = eout(u, 3) * 1500
        nrm = (_xx - W / 2) * -dy + (_yy - H / 2) * dx
        P1 = shift(P, dx * d, dy * d); P2 = shift(P, -dx * d, -dy * d)
        side = (nrm < 0)[..., None]
        Q = np.where(side, P1, P2); valid = Q[..., :1] >= 0
        out = np.where(valid, Q, img)
        w = max(0.0, 1 - u * 1.6)
        if w > 0:
            core = np.exp(-(nrm / (2 + 6 * w)) ** 2).astype(np.float32)
            paste(out, PAPER, 0, 0, core, w)
            paste(out, RED, 0, 0, cv2.GaussianBlur(core, (0, 0), 16) * 3, w * .8)
        return out
    if kind == 'zoom':
        if u < .5:
            k = u / .5; return zoom_img(P, 1 + .6 * ein(k, 2)) * (1 - k * .9) + PAPER * k * .9
        k = (u - .5) / .5; return zoom_img(img, 1.2 - .2 * eout(k)) * (.1 + .9 * k) + PAPER * (1 - k) * .9
    if kind == 'push':
        k = eout(u, 3); off = int(k * H)
        out = np.empty_like(img)
        out[:H - off] = P[off:]; out[H - off:] = img[:off] if off else out[H - off:]
        sp = int((1 - k) * 30) | 1
        return cv2.blur(out, (1, sp)) if sp > 3 else out
    if kind == 'ink':
        m = np.clip((u * 1.25 - INKF) / .05, 0, 1)[..., None]
        edge = np.clip(1 - np.abs(u * 1.25 - INKF - .03) / .03, 0, 1)[..., None]
        out = P * (1 - m) + img * m
        return out * (1 - edge) + INK * edge
    if kind == 'redflash':
        Lm = lum(img)[..., None]
        k = 1 - eio(u)
        red = INK + (RED - INK) * Lm
        return img * (1 - k) + red * k
    if kind == 'fade':
        if u < .4: return P * (1 - u / .4)
        return img * min(1, (u - .4) / .4)
    return img


def frame(fi):
    t = fi / FPS; bt = t / BEAT; i = shot_at(bt); s = SHOTS[i]
    cut_dt = t - b(s[0])
    n = 3 if (s[0] in FAST and cut_dt < .22) or (s[0] == 42 and 0 <= bt - 44 < .6) else 1
    acc = None
    for k in range(n):
        tk = t - k / FPS / n * 0.9
        if tk < b(s[0]): tk = b(s[0])
        img = transition(i, tk, draw(i, tk))
        acc = img if acc is None else acc + img
    img = acc / n
    # hits: shake + chromatic split
    for h, amp in SHAKE.items():
        dt = t - b(h)
        if 0 <= dt < .8:
            a = amp * math.exp(-dt * 6)
            img = shift(img, a * math.sin(dt * 71), a * math.cos(dt * 53), fill=float(INK[0]))
    for h, amp in CHROMA.items():
        dt = t - b(h)
        if 0 <= dt < .5: img = chroma(img, amp * math.exp(-dt * 7))
    if s[5]:
        hud(img, bt, a=eout((bt - 3.95) / .1) if bt < 4.1 else 1.0)
    elif s[2] is s_open:
        fly = eio((bt - 3.4) / .6)
        if fly > 0:     # the opening 12:00 flies into the corner and becomes the HUD
            hgt = lerp(250, 56, fly)
            m = seg_mask('12:00', int(hgt))
            x = lerp(W / 2 - seg_mask('12:00', 250).shape[1] / 2, MX, fly); y = lerp(860 - 125, 118, fly)
            put(img, m, x, y, RED)
    img = img * VIG + GRAIN[fi % 3]
    if fi > NF - 10: img *= (NF - fi) / 10
    return np.clip(img, 0, 1)


def to8(img): return (img * 255 + .5).astype(np.uint8)


def frame_bytes(fi): return to8(frame(fi)).tobytes()


# ---------------------------------------------------------------- outputs
def stills(times):
    d = HERE / 'stills_v2'; d.mkdir(exist_ok=True)
    for t in times:
        fi = int(round(t * FPS)); cv2.imwrite(str(d / f'{t:06.2f}.png'), cv2.cvtColor(to8(frame(fi)), cv2.COLOR_RGB2BGR))
        print('still', t)


def sheet(step, workers):
    from multiprocessing import Pool
    times = [round(x, 3) for x in np.arange(0, DUR, step)]
    with Pool(workers) as p: ims = p.map(frame_small, [int(round(t * FPS)) for t in times])
    cols = 8; rows = (len(ims) + cols - 1) // cols; h, w = ims[0].shape[:2]
    sh = np.zeros((rows * (h + 22), cols * w, 3), np.uint8) + 30
    for k, (t, im) in enumerate(zip(times, ims)):
        r, c = divmod(k, cols); sh[r * (h + 22) + 22:r * (h + 22) + 22 + h, c * w:(c + 1) * w] = im
        cv2.putText(sh, f'{t:.2f}s b{t / BEAT:.1f}', (c * w + 4, r * (h + 22) + 16), cv2.FONT_HERSHEY_SIMPLEX, .45, (220, 220, 220), 1)
    d = HERE / 'stills_v2'; d.mkdir(exist_ok=True)
    cv2.imwrite(str(d / 'sheet.jpg'), cv2.cvtColor(sh, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print('sheet', d / 'sheet.jpg')


def frame_small(fi): return cv2.resize(to8(frame(fi)), (270, 480), interpolation=cv2.INTER_AREA)


def loudnorm_filter(ff):
    """Two-pass EBU R128 to -14 LUFS / -1.5 dBTP (linear gain, no pumping)."""
    r = subprocess.run([ff, '-hide_banner', '-i', str(AUDIO), '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json',
                        '-f', 'null', '-'], capture_output=True, text=True)
    j = json.loads(r.stderr[r.stderr.rindex('{'):r.stderr.rindex('}') + 1])
    return (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
            f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")


def video(workers, out=OUT):
    from multiprocessing import Pool
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    if not AUDIO.exists(): sys.exit('run music_v2.py first')
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
    a = ap.parse_args()
    if a.mode == 'stills': stills([float(x) for x in a.arg.split(',')])
    elif a.mode == 'sheet': sheet(float(a.arg or 1), a.workers)
    else: video(a.workers)
