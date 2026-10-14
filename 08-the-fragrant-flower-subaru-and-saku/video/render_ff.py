"""The Fragrant Flower Blooms with Dignity - Subaru and Saku. 47 s romance Short, 1080x1920, 30 fps.

A romance edit is built from different tools than a fight edit:
  * time: slow cameras that ease in and out, cuts on the bar, held moments; nothing snaps
  * light: a duotone grade per scene (warm cafe, dusk car, faded memory, blue snow, rose confession),
    bloom on the highlights, drifting light leaks and bokeh, film grain
  * air: falling snow in three depths (sharp behind, soft in front of the art), dust motes in the cafe light,
    and a slow "living" displacement on the art; in the last close-up the wind moves her hair
  * words: her inner monologue is set in an italic serif and revealed word by word; the drawn dialogue
    balloons stay exactly as Saka Mikami lettered them
Picture and score share timeline_ff.py (80 BPM). The beat pulse is a 0.6 % breath, not a punch.

Usage (from this folder):
  python music_ff.py                         -> score_ff.wav
  python render_ff.py stills 2,15,37         -> stills_ff/*.png
  python render_ff.py sheet 1                -> stills_ff/sheet.jpg
  python render_ff.py video [--workers 3]    -> ../fragrant-flower-short.mp4
"""
import os, sys, math, json, subprocess, argparse
from functools import lru_cache
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
from timeline_ff import BEAT, FPS, NB, DUR, drum_hits, section_at, b

cv2.setNumThreads(1)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FD = 'C:/Windows/Fonts/' if os.name == 'nt' else str(ROOT.parent / 'fonts') + '/'   # tools/setup_fonts.py
SERIF_I = FD + 'georgiai.ttf'        # Georgia Italic on Windows; Cormorant Garamond Italic elsewhere
SERIF = FD + 'constan.ttf'           # Constantia on Windows; Cormorant Garamond SemiBold elsewhere
JP = FD + 'NotoSerifJP-M.ttf'
W, H = 1080, 1920
NF = int(round(DUR * FPS))
OUT = ROOT / 'fragrant-flower-short.mp4'
AUDIO = HERE / 'score_ff.wav'
KICKS, _ = drum_hits()


def hexc(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)
CREAM = hexc('#FFF4E6'); ROSE = hexc('#FF9FB6'); AMBER = hexc('#FFB36B')
GRADES = {   # shadow, highlight, gamma, bloom colour, bloom amount
    'warm': (hexc('#22160F'), hexc('#FFF1DC'), 1.18, AMBER, .22),
    'dusk': (hexc('#1A1730'), hexc('#F6E8F2'), 1.05, hexc('#C9A8FF'), .2),
    'memory': (hexc('#3E3029'), hexc('#FFF6E6'), 1.1, hexc('#FFE2B8'), .18),
    'snow': (hexc('#101828'), hexc('#EEF4FB'), 1.05, hexc('#BFD8FF'), .26),
    'rose': (hexc('#1E1322'), hexc('#FFEDF1'), 1.0, ROSE, .3),
}


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, c=1.0): return max(a, min(c, x))
def eout(u, p=3): return 1 - (1 - clamp(u)) ** p
def ein(u, p=2): return clamp(u) ** p
def eio(u): u = clamp(u); return u * u * (3 - 2 * u)
def eio2(u): u = clamp(u); return u * u * u * (u * (6 * u - 15) + 10)
def lerp(a, c, u): return a + (c - a) * u


# ---------------------------------------------------------------- fixed fields
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
def smooth_noise(scale, seed, w=W, h=H):
    r = np.random.default_rng(seed); n = r.random((h // scale + 3, w // scale + 3)).astype(np.float32)
    return cv2.resize(n, (w + 3 * scale, h + 3 * scale), interpolation=cv2.INTER_CUBIC)[:h, :w] * 2 - 1
NX1, NY1, NX2, NY2 = (smooth_noise(260, s) for s in (11, 12, 13, 14))
_vr = np.sqrt(((_xx / W - .5) * 2) ** 2 * .75 + ((_yy / H - .5) * 2) ** 2 * .55)
VIG = (1 - .42 * np.clip(_vr - .35, 0, 1) ** 1.5)[..., None].astype(np.float32)
_g = np.random.default_rng(7)
GRAIN = [cv2.resize(_g.normal(0, .022, (H // 2, W // 2)).astype(np.float32), (W, H))[..., None] for _ in range(4)]


# ---------------------------------------------------------------- pages
@lru_cache(maxsize=None)
def page(n, mip):
    g = cv2.imread(str(ROOT / 'panels' / f'panel_{n:03d}.png'), cv2.IMREAD_GRAYSCALE)
    if g is None: raise FileNotFoundError(n)
    if mip == 2:
        g = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        g = cv2.addWeighted(g, 1.5, cv2.GaussianBlur(g, (0, 0), 1.6), -.5, 0)
    return g


def view(n, cx, cy, hs, size=(W, H), rect=None, rot=0.0):
    """Luminance 0..1 of page n through a camera centred on (cx, cy) whose output height covers hs page px.
    rect=(x, y, w, h) keeps the window inside a panel so gutters never show."""
    w, h = size; ws = hs * w / h
    if rect:
        x, y, rw, rh = rect
        cx = clamp(cx, x + ws / 2, x + rw - ws / 2) if rw > ws else x + rw / 2
        cy = clamp(cy, y + hs / 2, y + rh - hs / 2) if rh > hs else y + rh / 2
    s = h / hs; mip = 2 if s > 1.1 else 1
    src = page(n, mip); s /= mip
    M = cv2.getRotationMatrix2D((cx * mip, cy * mip), rot, s)
    M[0, 2] += w / 2 - cx * mip; M[1, 2] += h / 2 - cy * mip
    g = cv2.warpAffine(src, M, (w, h), flags=cv2.INTER_LINEAR if s > .8 else cv2.INTER_AREA,
                       borderMode=cv2.BORDER_REPLICATE)
    if s < .8: g = cv2.GaussianBlur(g, (0, 0), .45 / s)
    return np.clip((g.astype(np.float32) / 255 - .04) / .92, 0, 1)


def living(L, t, amp=1.3, hair=None):
    """Slow breathing displacement; hair=(x_max_frac, strength) adds a travelling wind wave on the left side."""
    h, w = L.shape
    nx1, ny1, nx2, ny2 = (a[:h, :w] for a in (NX1, NY1, NX2, NY2))
    dx = amp * (nx1 * math.sin(.8 * t) + nx2 * math.cos(.63 * t))
    dy = amp * (ny1 * math.sin(.71 * t) + ny2 * math.cos(.9 * t))
    if hair:
        xm, k = hair
        m = np.clip((xm * w - _xx[:h, :w]) / (xm * w * .5), 0, 1) ** 1.5
        dx = dx + k * m * np.sin(2 * np.pi * (_yy[:h, :w] / 230 - .45 * t)) + k * .6 * m * np.sin(2 * np.pi * (_yy[:h, :w] / 97 - .8 * t))
        dy = dy + k * .25 * m * np.sin(2 * np.pi * (_xx[:h, :w] / 180 - .5 * t))
    return cv2.remap(L, _xx[:h, :w] + dx, _yy[:h, :w] + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def grade(L, name):
    sh, hi, gm, _, _ = GRADES[name]
    Lg = L ** gm if gm != 1 else L
    return sh + (hi - sh) * Lg[..., None]


def bloom(img, L, name, k=1.0):
    _, _, _, col, amt = GRADES[name]
    small = cv2.resize(np.clip((L - .72) / .28, 0, 1), (W // 4, img.shape[0] // 4), interpolation=cv2.INTER_AREA)
    glow = cv2.resize(cv2.GaussianBlur(small, (0, 0), 7), (W, img.shape[0]))
    return img + glow[..., None] * col * amt * k


# ---------------------------------------------------------------- layouts
def full(n, rect, c0, c1, u, t, name, e=eio2, hair=None, rot=(0, 0), pulse=1.0):
    cx, cy, hs = (lerp(a, c, e(u)) for a, c in zip(c0, c1))
    L = view(n, cx, cy, hs / pulse, rect=rect, rot=lerp(rot[0], rot[1], e(u)))
    L = living(L, t, 1.3, hair)
    return bloom(grade(L, name), L, name)


def backdrop(n, rect, name, u, dim=.5):
    """The panel itself, enlarged, blurred and darkened: the dreamy field behind a band."""
    x, y, rw, rh = rect
    L = view(n, x + rw / 2, y + rh / 2, rh * .8 * (1 + .05 * u), size=(W // 6, H // 6), rect=rect)
    L = cv2.GaussianBlur(L, (0, 0), 6)
    img = cv2.resize(grade(L, name), (W, H), interpolation=cv2.INTER_CUBIC)
    return img * dim


def band(dst, n, rect, yc, u, t, name, z=(1.0, 1.06), drift=(0, 0), a=1.0, maxh=None, pulse=1.0):
    x, y, rw, rh = rect; bh = int(round(W * rh / rw)); bh = min(bh, maxh or bh)
    zz = lerp(z[0], z[1], eio(u)) * pulse
    hs = (rw * bh / W) / zz
    L = view(n, x + rw / 2 + drift[0] * (u - .5), y + rh / 2 + drift[1] * (u - .5), hs, (W, bh), rect=rect)
    L = living(L, t, 1.0)
    img = bloom(grade(L, name), L, name)
    top = int(round(yc - bh / 2))
    # soft shadow, then the band with feathered top and bottom edges
    sh = np.zeros((H, 1), np.float32); sh[max(0, top + 18):min(H, top + bh + 34)] = 1
    sh = cv2.GaussianBlur(sh, (0, 0), 22)
    dst *= (1 - .45 * sh[..., None] * a)
    fe = np.ones((bh, 1), np.float32); r = min(14, bh // 6)
    fe[:r, 0] = np.linspace(0, 1, r); fe[-r:, 0] = np.linspace(1, 0, r)
    y0, y1 = max(0, top), min(H, top + bh)
    if y1 > y0:
        m = fe[y0 - top:y1 - top][..., None] * a
        dst[y0:y1] = dst[y0:y1] * (1 - m) + img[y0 - top:y1 - top] * m
    return top, bh


# ---------------------------------------------------------------- atmosphere
def _flakes(seed, n, r0, r1, v0, v1):
    g = np.random.default_rng(seed)
    return dict(x=g.uniform(0, W, n), y=g.uniform(0, H + 200, n), r=g.uniform(r0, r1, n), v=g.uniform(v0, v1, n),
                a=g.uniform(15, 55, n), w=g.uniform(.4, 1.3, n), p=g.uniform(0, 6.28, n), o=g.uniform(.5, 1, n))
SNOW = [(_flakes(1, 150, 1.4, 2.6, 55, 105), 0.0, .75), (_flakes(2, 60, 3.0, 5.0, 130, 200), 1.2, .85),
        (_flakes(3, 14, 15, 28, 260, 380), 7.0, .45)]


def snow(img, t, k=1.0, layers=(0, 1, 2), wind=40.0):
    for li in layers:
        fl, blur, op = SNOW[li]
        m = np.zeros((H, W), np.float32)
        ys = (fl['y'] + fl['v'] * t) % (H + 200) - 100
        xs = (fl['x'] + wind * t * (1 + li * .4) + fl['a'] * np.sin(fl['w'] * t + fl['p'])) % (W + 60) - 30
        for x, y, r, o in zip(xs, ys, fl['r'], fl['o']):
            cv2.circle(m, (int(x * 4), int(y * 4)), max(1, int(r * 4)), float(o), -1, cv2.LINE_AA, shift=2)
        if blur: m = cv2.GaussianBlur(m, (0, 0), blur)
        img[:] = img * (1 - m[..., None] * op * k) + CREAM * (m[..., None] * op * k)


def _bokeh(seed, n):
    g = np.random.default_rng(seed)
    return dict(x=g.uniform(0, W, n), y=g.uniform(0, H, n), r=g.uniform(50, 150, n), vx=g.uniform(-14, 14, n),
                vy=g.uniform(-22, -6, n), o=g.uniform(.08, .2, n), c=g.integers(0, 3, n))
BOKEH = _bokeh(5, 12)


def bokeh(img, t, k=1.0, cols=(AMBER, ROSE, CREAM)):
    s = 6; acc = np.zeros((H // s, W // s, 3), np.float32)
    for i in range(len(BOKEH['x'])):
        x = (BOKEH['x'][i] + BOKEH['vx'][i] * t) % (W + 300) - 150
        y = (BOKEH['y'][i] + BOKEH['vy'][i] * t) % (H + 300) - 150
        m = np.zeros((H // s, W // s), np.float32)
        cv2.circle(m, (int(x / s), int(y / s)), int(BOKEH['r'][i] / s), 1.0, -1, cv2.LINE_AA)
        acc += m[..., None] * cols[BOKEH['c'][i] % len(cols)] * BOKEH['o'][i] * (.75 + .25 * math.sin(t * 1.3 + i))
    acc = cv2.GaussianBlur(acc, (0, 0), 2.5)
    img += cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * k


DUST = np.random.default_rng(9).uniform(0, 1, (70, 5))


def dust(img, t, k=1.0):
    m = np.zeros((H, W), np.float32)
    for x0, y0, sp, ph, r in DUST:
        x = (x0 * W + 18 * math.sin(t * .4 + ph * 6) + 12 * t * (sp - .5)) % W
        y = (y0 * H - 16 * t * (.4 + sp)) % H
        tw = .5 + .5 * math.sin(t * (1 + sp * 2) + ph * 9)
        cv2.circle(m, (int(x), int(y)), 1 + int(r * 2.5), tw, -1, cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), 1.6)
    img += m[..., None] * AMBER * .55 * k


def leak(img, t, k, warm=True):
    """A drifting light leak (screen blend), k 0..1."""
    if k <= .01: return img
    s = 8; h, w = H // s, W // s
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx1 = w * (.15 + .25 * math.sin(t * .35)); cy1 = h * (.2 + .15 * math.cos(t * .27))
    cx2 = w * (.9 - .2 * math.sin(t * .31 + 1)); cy2 = h * (.75 + .1 * math.sin(t * .4))
    g1 = np.exp(-(((xx - cx1) / (w * .45)) ** 2 + ((yy - cy1) / (h * .3)) ** 2))
    g2 = np.exp(-(((xx - cx2) / (w * .5)) ** 2 + ((yy - cy2) / (h * .28)) ** 2))
    c1, c2 = (AMBER, ROSE) if warm else (hexc('#9EC8FF'), ROSE)
    L = g1[..., None] * c1 + g2[..., None] * c2 * .8
    L = cv2.resize(L, (W, H), interpolation=cv2.INTER_LINEAR) * k
    return 1 - (1 - np.clip(img, 0, 1)) * (1 - np.clip(L, 0, 1))


# ---------------------------------------------------------------- type
@lru_cache(maxsize=256)
def word_mask(word, font, size):
    f = ImageFont.truetype(font, size); asc, desc = f.getmetrics(); wd = int(f.getlength(word))
    im = Image.new('L', (wd + 40, asc + desc + 40)); ImageDraw.Draw(im).text((20, 20), word, font=f, fill=255)
    return np.asarray(im, np.float32) / 255, asc      # every word shares the font's ascent: one baseline


def paste_mask(img, m, x, y, col, a):
    x, y = int(round(x)), int(round(y)); h, w = m.shape
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0 or a <= 0: return
    mm = m[y0 - y:y1 - y, x0 - x:x1 - x][..., None] * a
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - mm) + np.asarray(col) * mm


def verse(img, lines, t0, t, y, size=74, font=SERIF_I, col=CREAM, align='center', per_word=.16, out_at=None, x=None):
    """Lines of text revealed word by word: each word rises 16 px, sharpens from a blur and fades in."""
    fade = 1.0 if out_at is None else 1 - eio((t - out_at) / .45)
    if fade <= 0: return
    space = size * .28; lh = size * 1.22; k = 0
    for li, line in enumerate(lines):
        words = line.split(' ')
        ms = [word_mask(wd, font, size) for wd in words]
        total = sum(m.shape[1] - 40 for m, _ in ms) + space * (len(words) - 1)
        cx = (W - total) / 2 if align == 'center' else (x if x is not None else 90)
        for wd, (m, _) in zip(words, ms):
            u = (t - t0 - k * per_word) / .5; k += 1
            if u > 0:
                e = eout(u)
                mm = m if e > .97 else cv2.GaussianBlur(m, (0, 0), .2 + 5 * (1 - e))
                sh = cv2.GaussianBlur(m, (0, 0), 7)
                paste_mask(img, sh, cx - 20 + 2, y + li * lh - 20 + 16 * (1 - e) + 3, (0, 0, 0), .55 * e * fade)
                paste_mask(img, mm, cx - 20, y + li * lh - 20 + 16 * (1 - e), col, e * fade)
            cx += m.shape[1] - 40 + space


# ---------------------------------------------------------------- shots (beats)
def s_fairy(tl, u, t, bt):
    img = backdrop(1, (90, 0, 470, 340), 'warm', u, .4)
    band(img, 1, (95, 0, 470, 340), 820, u, t, 'warm', z=(1.08, 1.0), drift=(-30, 0))
    dust(img, t, .6)
    verse(img, ['It was an out-of-reach'], b(.6), tl, 1300, size=84)
    verse(img, ['fairy tale.'], b(1.8), tl, 1405, size=104)
    return img


def s_reading(tl, u, t, bt):
    img = full(2, (0, 90, 870, 1288), (540, 470, 980), (520, 500, 780), u, t, 'warm')
    dust(img, t)
    verse(img, ['It never felt like it fit me,'], b(.4), tl, 1420, size=76)
    verse(img, ['nor did I understand it.'], b(1.6), tl, 1515, size=76)
    return img


def s_cafe(tl, u, t, bt):
    img = backdrop(1, (90, 905, 870, 473), 'warm', u, .45)
    band(img, 1, (90, 905, 870, 473), 840, u, t, 'warm', z=(1.0, 1.08), drift=(60, 0))
    dust(img, t)
    verse(img, ['But... it didn\'t have to'], b(.5), tl, 1290, size=84)
    verse(img, ['fit me.'], b(1.7), tl, 1395, size=104)
    return img


def s_nap(tl, u, t, bt):
    img = full(8, (90, 350, 870, 1028), (600, 860, 1028), (585, 900, 900), u, t, 'warm')
    dust(img, t)
    return img


def s_sip(tl, u, t, bt):
    img = backdrop(10, (90, 0, 870, 1080), 'warm', u, .4)
    band(img, 10, (90, 0, 870, 1080), 960, u, t, 'warm', z=(1.0, 1.07), drift=(0, 40))
    dust(img, t)
    return img


def s_lean(tl, u, t, bt):
    img = backdrop(14, (90, 900, 870, 478), 'warm', u, .42)
    band(img, 14, (90, 900, 870, 478), 820, u, t, 'warm', z=(1.12, 1.0), drift=(-40, 0))
    dust(img, t)
    verse(img, ['My heart feels calm'], b(.3), tl, 1280, size=84)
    verse(img, ['whenever I\'m with him.'], b(1.2), tl, 1380, size=84)
    return img


def s_peace(tl, u, t, bt):
    img = backdrop(15, (400, 80, 470, 500), 'dusk', u, .45)
    band(img, 15, (400, 80, 470, 500), 940, u, t, 'dusk', z=(1.0, 1.08), drift=(0, -30))
    bokeh(img, t, .8)
    return img


def s_car(tl, u, t, bt):
    img = backdrop(16, (90, 265, 870, 480), 'dusk', u, .45)
    band(img, 16, (90, 265, 870, 480), 900, u, t, 'dusk', z=(1.0, 1.1), drift=(0, 0))
    bokeh(img, t, 1.0)
    return img


def s_memory(tl, u, t, bt):
    img = backdrop(17, (0, 330, 870, 305), 'memory', u, .7)
    band(img, 17, (0, 330, 870, 305), 940, u, t, 'memory', z=(1.12, 1.22), drift=(60, 0))
    img = img * .9 + cv2.GaussianBlur(img, (0, 0), 14) * .15          # dreamy halation
    return leak(img, t, .2)


def s_dec(tl, u, t, bt):
    img = backdrop(21, (240, 965, 470, 413), 'snow', u, .5)
    band(img, 21, (240, 965, 470, 413), 760, u, t, 'snow', z=(1.0, 1.08), drift=(0, -20))
    snow(img, t, .8 * eio(tl / .8))
    verse(img, ['December 29th.'], b(.3), tl, 1340, size=84)
    verse(img, ['the final day of this year\'s winter classes'], b(.9), tl, 1430, size=48)
    return img


def s_street(tl, u, t, bt):
    img = backdrop(23, (0, 910, 870, 468), 'snow', u, .45)
    band(img, 23, (0, 635, 870, 235), 600, u, t, 'snow', z=(1.0, 1.06), drift=(-30, 0))
    if tl > b(.8):
        a = eio((tl - b(.8)) / .4)
        band(img, 23, (0, 910, 870, 468), 1250, u, t, 'snow', z=(1.0, 1.05), a=a)
    snow(img, t)
    return img


def s_umbrella(tl, u, t, bt, pulse=1.0):
    img = full(24, (90, 0, 870, 1080), (600, 560, 1080), (585, 520, 940), u, t, 'snow', pulse=pulse)
    snow(img, t)
    bokeh(img, t, .5, (CREAM, hexc('#BFD8FF')))
    return img


def s_cold(tl, u, t, bt, pulse=1.0):
    img = backdrop(27, (0, 0, 870, 770), 'snow', u, .45)
    band(img, 27, (0, 0, 870, 770), 930, u, t, 'snow', z=(1.0, 1.06), drift=(0, 30), pulse=pulse)
    snow(img, t)
    return img


def s_her(tl, u, t, bt, pulse=1.0):
    img = full(26, (90, 0, 870, 733), (520, 400, 733), (500, 340, 600), u, t, 'snow', pulse=pulse)
    snow(img, t, 1.0, (1, 2))
    return img


def s_hurt(tl, u, t, bt, pulse=1.0):
    img = backdrop(29, (0, 688, 870, 365), 'snow', u, .45)
    band(img, 29, (0, 688, 870, 365), 640, u, t, 'snow', z=(1.0, 1.05), pulse=pulse)
    if tl > b(1):
        band(img, 29, (0, 1090, 870, 288), 1250, u, t, 'snow', z=(1.0, 1.05), a=eio((tl - b(1)) / .4))
    snow(img, t, .9)
    return img


def s_understood(tl, u, t, bt):
    img = backdrop(31, (0, 0, 870, 583), 'snow', u, .5)
    band(img, 31, (0, 0, 870, 583), 930, u, t, 'snow', z=(1.0, 1.1), drift=(30, 0))
    snow(img, t)
    return img


def s_i(tl, u, t, bt):
    img = full(32, (0, 0, 715, 1378), (480, 300, 560), (470, 290, 520), u, t, 'rose')
    snow(img, t * .6, 1.0, (0, 1))
    return img


def s_likeyou(tl, u, t, bt):
    img = full(32, (0, 0, 715, 1378), (470, 290, 520), (350, 660, 1300), u, t, 'rose', e=eio2)
    snow(img, t)
    bokeh(img, t, .9, (ROSE, CREAM, AMBER))
    return leak(img, t, .25 * (1 - u))


def s_face(tl, u, t, bt):
    img = full(32, (740, 0, 1180, 1378), (1380, 700, 1378), (1390, 600, 980), u, t, 'rose', hair=(.42, 7.0))
    snow(img, t)
    bokeh(img, t, .6, (ROSE, CREAM))
    return img


def s_title(tl, u, t, bt):
    L = view(32, 1380, 680, 1200 * (1 + .04 * u), rect=(740, 0, 1180, 1378))
    L = cv2.GaussianBlur(L, (0, 0), 9)
    img = grade(L, 'rose') * .42
    bokeh(img, t, 1.0, (ROSE, CREAM, AMBER))
    snow(img, t)
    verse(img, ['薫る花は凛と咲く'], b(.2), tl, 380, size=58, font=JP, per_word=0)
    verse(img, ['The Fragrant Flower'], b(.6), tl, 740, size=112, font=SERIF, per_word=.12)
    verse(img, ['Blooms with Dignity'], b(1.0), tl, 870, size=112, font=SERIF, per_word=.12)
    verse(img, ['Chapter 204  ·  Subaru and Saku'], b(1.8), tl, 1040, size=58)
    verse(img, ['Saka Mikami / Kodansha'], b(2.6), tl, 1440, size=40, col=CREAM * .8)
    verse(img, ['@inkframez'], b(3.0), tl, 1500, size=46, col=ROSE)
    return img


# (start beat, end beat, function, entering transition, transition beats, beat pulse?)
SHOTS = [
    (0, 4, s_fairy, 'black', 1.2, False),
    (4, 8, s_reading, 'dissolve', .8, False),
    (8, 12, s_cafe, 'leak', .8, True),
    (12, 16, s_nap, 'dissolve', .7, True),
    (16, 20, s_sip, 'dissolve', .7, True),
    (20, 23, s_lean, 'dissolve', .7, True),
    (23, 26, s_peace, 'leak', .9, True),
    (26, 28, s_car, 'dissolve', .6, True),
    (28, 30, s_memory, 'dissolve', .6, False),
    (30, 32, s_dec, 'dissolve', .8, False),
    (32, 34, s_street, 'leak', .6, True),
    (34, 38, s_umbrella, 'dissolve', .5, True),
    (38, 40, s_cold, 'cut', 0, True),
    (40, 42, s_her, 'dissolve', .5, True),
    (42, 44, s_hurt, 'dissolve', .5, True),
    (44, 46, s_understood, 'dissolve', .6, False),
    (46, 48, s_i, 'black', .9, False),
    (48, 50, s_likeyou, 'white', .8, False),
    (50, 56, s_face, 'dissolve', .9, False),
    (56, NB + 3, s_title, 'leak', 1.4, False),
]


def shot_at(bt):
    for i, s in enumerate(SHOTS):
        if s[0] <= bt < s[1]: return i
    return len(SHOTS) - 1


def pulse_at(t):
    return 1 + sum(.006 * math.exp(-(t - b(k)) * 7) for k in KICKS if 0 <= t - b(k) < .6)


def draw(i, t):
    s = SHOTS[i]; tl = t - b(s[0]); u = tl / b(s[1] - s[0])
    if s[5]:
        try: return s[2](tl, u, t, t / BEAT, pulse=pulse_at(t))
        except TypeError:
            img = s[2](tl, u, t, t / BEAT); p = pulse_at(t)
            return img if p < 1.001 else cv2.warpAffine(img, cv2.getRotationMatrix2D((W / 2, H / 2), 0, p), (W, H), borderMode=cv2.BORDER_REFLECT)
    return s[2](tl, u, t, t / BEAT)


def softblur(img, s):
    if s < .3: return img
    small = cv2.resize(img, (W // 3, H // 3), interpolation=cv2.INTER_AREA)
    return cv2.resize(cv2.GaussianBlur(small, (0, 0), s / 3), (W, H), interpolation=cv2.INTER_LINEAR)


def transition(i, t, img):
    s = SHOTS[i]; kind, dur = s[3], b(s[4]); tl = t - b(s[0])
    if kind in (None, 'cut') or tl >= dur: return img
    u = tl / dur
    if kind == 'black':
        return img * eio(u)
    P = draw(i - 1, t) if i > 0 else np.zeros_like(img)
    k = eio(u); bl = 14 * math.sin(math.pi * u)
    out = softblur(P, bl) * (1 - k) + softblur(img, bl) * k
    if kind == 'leak': out = leak(out, t, .55 * math.sin(math.pi * u))
    if kind == 'white': out = out + (1 - eout(u, 2)) * .85 * CREAM
    return out


def frame(fi):
    t = fi / FPS; bt = t / BEAT; i = shot_at(bt)
    img = transition(i, t, draw(i, t))
    img = img * VIG + GRAIN[fi % 4]
    if t < .4: img *= t / .4
    if fi > NF - 18: img *= (NF - fi) / 18
    return np.clip(img, 0, 1)


def to8(img): return (img * 255 + .5).astype(np.uint8)
def frame_bytes(fi): return to8(frame(fi)).tobytes()
def frame_small(fi): return cv2.resize(to8(frame(fi)), (270, 480), interpolation=cv2.INTER_AREA)


def stills(times):
    d = HERE / 'stills_ff'; d.mkdir(exist_ok=True)
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
    d = HERE / 'stills_ff'; d.mkdir(exist_ok=True)
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
    if not AUDIO.exists(): sys.exit('run music_ff.py first')
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
