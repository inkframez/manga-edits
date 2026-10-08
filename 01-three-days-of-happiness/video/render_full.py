"""Three Days of Happiness - FULL SONG version (4:09, 1920x1080, 30fps).

Separate from render.py (the 60s cut), which is left untouched.
Usage:
  python render_full.py stills 10,60,120     -> PNG stills + contact sheet in ./stills_full
  python render_full.py video                -> ../three-days-of-happiness-full.mp4
Concept: colour = worth. Cold grayscale; a hint of warmth on the dates (chorus 1),
full amber from the firefly reveal (115.75s), drains in the doubt breakdown, returns
on the final drop (206.69s). Times below are song time = video time.
"""
import os, sys, math, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAN = os.path.join(ROOT, 'panels')
SONG = os.path.join(ROOT, '01-tdoh-bg-song.mp3')
OUT = os.path.join(ROOT, 'three-days-of-happiness-full.mp4')
W, H, FPS = 1920, 1080, 30
DUR = 249.5
N = int(DUR * FPS)
FD = 'C:/Windows/Fonts/'
cv2.setNumThreads(1)

# ---------------------------------------------------------------- easing
def clamp(u): return min(max(u, 0.0), 1.0)
def eout(u): u = clamp(u); return 1 - (1 - u) ** 3
def eio(u):
    u = clamp(u); return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2
def lerp(a, b, u): return a + (b - a) * u
def keys(t, pts):
    if t <= pts[0][0]: return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t1: return lerp(v0, v1, eio((t - t0) / max(t1 - t0, 1e-6)))
    return pts[-1][1]

# ---------------------------------------------------------------- music map (72 bpm)
BEAT = 0.8355
def bar(j): return 2.12 + j * 4 * BEAT          # downbeats: 2.12, 5.46, 8.80 ...
def fb(n): return 214.47 + n * 0.835            # final-chorus grid (phase drifts late in the song)
DROP1, DROP2 = bar(34), 206.69                  # firefly reveal (115.75) / final drop
GLITCH = 133.29                                  # "...30 yen."
STRIKE = 220.32                                  # "the worthwhile 30 days"

# ---------------------------------------------------------------- pages (uint8 to keep workers light)
PAGES = {}
def page(n):
    if n not in PAGES:
        fn = [p for p in os.listdir(PAN) if p.split('.')[0] == n][0]
        im = np.asarray(Image.open(os.path.join(PAN, fn)).convert('L'), np.float32) / 255
        h, w = im.shape
        s = 3.0 if w < 700 else 2.0
        up = cv2.resize(im, (int(w * s), int(h * s)), interpolation=cv2.INTER_LANCZOS4)
        bl = cv2.GaussianBlur(up, (0, 0), 1.4)
        up = (np.clip(up + 0.7 * (up - bl), 0, 1) * 255 + 0.5).astype(np.uint8)
        PAGES[n] = (im, up, s)
    return PAGES[n]

# ---------------------------------------------------------------- panel rects (page px)
R = {
    '01a': ('01', [37, 0, 566, 487]), '01b': ('01', [37, 509, 537, 451]),
    '02room': ('02', [37, 0, 537, 448]), '02girl': ('02', [335, 468, 276, 492]),
    '03a': ('03', [56, 136, 213, 487]), '03b': ('03', [274, 136, 572, 487]), '03c': ('03', [56, 642, 790, 282]),
    '03d': ('03', [56, 942, 412, 369]), '03e': ('03', [474, 942, 372, 369]),
    '04a': ('04', [56, 136, 398, 237]), '04b': ('04', [459, 136, 387, 484]), '04c': ('04', [56, 392, 398, 228]),
    '04d': ('04', [56, 639, 790, 280]), '04e': ('04', [56, 938, 207, 373]), '04f': ('04', [268, 938, 302, 373]),
    '04g': ('04', [576, 938, 270, 373]),
    '06a': ('06', [56, 136, 790, 378]), '06b': ('06', [56, 532, 384, 352]), '06c': ('06', [446, 532, 400, 352]),
    '06d': ('06', [56, 902, 241, 409]), '06e': ('06', [302, 902, 229, 409]), '06f': ('06', [536, 902, 310, 409]),
    '07a': ('07', [56, 136, 303, 370]), '07b': ('07', [364, 136, 482, 370]), '07c': ('07', [56, 525, 790, 302]),
    '07d': ('07', [56, 846, 235, 465]), '07e': ('07', [296, 846, 232, 465]), '07f': ('07', [533, 846, 313, 465]),
    '08a': ('08', [56, 136, 790, 560]), '08b': ('08', [56, 714, 406, 284]), '08c': ('08', [468, 714, 378, 597]),
    '08d': ('08', [56, 1016, 407, 295]),
    '09a': ('09', [37, 0, 537, 259]), '09b': ('09', [37, 271, 537, 359]), '09c': ('09', [37, 651, 259, 309]),
    '09d': ('09', [300, 651, 274, 309]),
    '11a': ('11', [37, 0, 268, 410]), '11b': ('11', [309, 0, 265, 410]), '11c': ('11', [37, 427, 537, 234]),
    '11d': ('11', [37, 682, 537, 278]),
    '12a': ('12', [37, 0, 337, 347]), '12b': ('12', [379, 0, 195, 347]), '12c': ('12', [37, 369, 270, 269]),
    '12d': ('12', [311, 369, 263, 269]), '12e': ('12', [37, 659, 537, 301]),
    '13': ('13', [53, 20, 927, 521]),
    '14a': ('14', [37, 0, 537, 455]), '14b': ('14', [37, 476, 323, 197]), '14c': ('14', [365, 476, 209, 484]),
    '14d': ('14', [37, 695, 323, 265]),
    '15a': ('15', [37, 0, 537, 273]), '15b': ('15', [37, 295, 537, 252]), '15c': ('15', [55, 578, 500, 285]),
    '16a': ('16', [37, 0, 537, 305]), '16b': ('16', [37, 327, 537, 560]),
    '17': ('17', [37, 0, 537, 960]), '18': ('18', [0, 47, 548, 913]),
    '19a': ('19', [37, 0, 537, 313]), '19b': ('19', [37, 335, 537, 298]), '19c': ('19', [37, 654, 537, 306]),
    '20': ('20', [205, 400, 220, 440]),
}
def C(key, **kw):
    p, r = R[key]; d = dict(p=p, r=list(r)); d.update(kw); return d

# ---------------------------------------------------------------- timeline
S = []
FLASHES = []
def shot(t0, t1, cards, bg='blur', **kw): S.append(dict(t0=t0, t1=t1, cards=cards, bg=bg, **kw))
def one(t0, t1, key, size=('h', 860), **kw):
    kw.setdefault(size[0], size[1]); shot(t0, t1, [C(key, **kw)])
def row(t0, t1, keys_, h=760, gap=40, stagger=BEAT, **kw):
    """panels side by side, equal height, centred; enter one per beat."""
    asp = [R[k][1][2] / R[k][1][3] for k in keys_]
    tot = sum(a * h for a in asp) + gap * (len(keys_) - 1)
    if tot > 1720: h *= 1720 / tot; tot = 1720
    x = (W - tot) / 2; cards = []
    for i, (k, a) in enumerate(zip(keys_, asp)):
        w = a * h; side = -1 if i % 2 == 0 else 1
        cards.append(C(k, h=h, cx=x + w / 2, cy=H / 2, t_in=i * stagger, ent=0.55, frm=(0, 40 * side), **kw))
        x += w + gap
    shot(t0, t1, cards)
def flick(cuts, keys_, flash=0.22):
    """fast memory flicker: one panel per cut, white blip on each."""
    for (t0, t1), k in zip(zip(cuts, cuts[1:]), keys_):
        a, b = R[k][1][2], R[k][1][3]
        size = dict(w=1500) if a / b > 1.4 else dict(h=860)
        shot(t0, t1, [C(k, ent=0.18, es=1.10, frm=(0, 0), s1=1.06, **size)])
        FLASHES.append((t0, flash, 0.1))

# Intro (0 - 8.80): black, the question
shot(0.0, bar(2), [], bg='black')
# Verse 1 - the sale, she arrives (8.80 - 52.25)
one(bar(2), bar(3), '01a', h=760, tilt=-16, ent=0.9, s1=1.05)
one(bar(3), bar(4), '01b', h=760, tilt=16, ent=0.9, s1=1.05)
shot(bar(4), bar(6), [C('02room', h=780, cx=1250, tilt=20, ent=0.9, kz=1.16, f=(0.62, 0.35))])
shot(bar(6), bar(8), [C('02girl', h=900, cx=1370, frm=(0, 50), ent=1.0, kz=1.2, f=(0.45, 0.3))])
shot(bar(8), bar(9), [C('03a', h=760, cx=380, d0=(-40, 0), d1=(70, 0), ent=0.5),
                      C('03b', h=760, cx=1210, d0=(60, 0), d1=(-50, 0), t_in=BEAT, ent=0.5)])
one(bar(9), bar(10), '03c', size=('w', 1560), kz=1.06)
one(bar(10), bar(11), '03d', h=820, tilt=-12, kz=1.1, f=(0.3, 0.4))
one(bar(11), bar(12), '03e', h=840, s1=1.07)
row(bar(12), bar(13), ['04c', '04b'], h=660)
one(bar(13), bar(14), '04d', size=('w', 1560), kz=1.08, f=(0.5, 0.5))
row(bar(14), bar(15), ['04e', '04f', '04g'], h=720)
# Chorus 1 - the "practice" date (52.25 - 82.33); a first hint of warmth
FLASHES.append((bar(15), 0.45, 0.35))
one(bar(15), bar(16), '06a', size=('w', 1560), s1=1.07)
one(bar(16), bar(16) + 2 * BEAT, '06b', h=820, ent=0.3, es=1.1, frm=(0, 0))
one(bar(16) + 2 * BEAT, bar(17), '06c', h=820, ent=0.3, es=1.1, frm=(0, 0), kz=1.15)
row(bar(17), bar(18), ['06d', '06e', '06f'], h=720)
row(bar(18), bar(19), ['07a', '07b'], h=720)
one(bar(19), bar(20), '07c', size=('w', 1560), kz=1.08, f=(0.5, 0.5))
row(bar(20), bar(21), ['07d', '07e', '07f'], h=760)
one(bar(21), bar(22), '08a', h=860, kz=1.12, f=(0.5, 0.4))
row(bar(22), bar(23), ['08b', '08c'], h=720)
one(bar(23), bar(24), '08d', h=640, s0=1.0, s1=1.1)
# Breakdown - the camera (82.33 - 89.01)
one(bar(24), bar(26), '09a', size=('w', 1560), ent=1.2, kz=1.55, f=(0.40, 0.62))
# Verse 2 - photos, night falls (89.01 - 115.75)
FLASHES.append((bar(26), 0.85, 0.16))
one(bar(26), bar(27), '09b', size=('w', 1380), ent=0.25, es=1.08, frm=(0, 0))
one(bar(27), bar(28), '09d', h=780, tilt=12)
one(bar(28), bar(29), '09c', h=780, tilt=-12)
shot(bar(29), bar(31), [dict(p='10', r=[0, 0, 611, 344], bleed=True, ent=1.5, rB=[30, 50, 551, 310])])
one(bar(31), bar(32), '11b', h=860, ent=1.0, kz=1.25, f=(0.5, 0.3))
one(bar(32), bar(33), '11a', h=860, ent=0.8, kz=1.15, f=(0.4, 0.75))
flick([bar(33) + i * BEAT for i in range(5)], ['06c', '03e', '07c', '08a'])
# Big chorus - the fireflies (115.75 - 182.59)
shot(DROP1, bar(35), [dict(p='10', r=[0, 30, 611, 344], bleed=True, ent=0, rB=[60, 392, 491, 276])])
one(bar(35), bar(36), '11c', size=('w', 1500), tilt=-10)
one(bar(36), bar(37), '11d', size=('w', 1420), kz=1.1, f=(0.7, 0.5))
row(bar(37), bar(38), ['12a', '12b'], h=760)
row(bar(38), bar(39), ['12c', '12d'], h=760)
one(bar(39), bar(40), '12e', size=('w', 1500), kz=1.06)
one(bar(40), bar(41), '12d', h=900, ent=0.8, kz=1.5, f=(0.45, 0.4))
FLASHES.append((bar(41), 0.85, 0.32))
shot(bar(41), bar(43), [dict(p='13', r=[53, 20, 927, 521], bleed=True, ent=0, kz=1.45, f=(0.43, 0.52),
                             warp=True, shake=(0.0, 14))])
one(bar(43), bar(44), '14a', h=900, ent=0.4, s0=1.45, s1=1.0, frm=(0, 0))
row(bar(44), bar(45), ['14b', '14c'], h=760)
FLASHES.append((bar(45), 0.3, 0.4))
one(bar(45), bar(46), '14d', h=780, tilt=12, kz=1.1)
one(bar(46), bar(47), '15a', size=('w', 1500))
one(bar(47), bar(48), '15b', size=('w', 1500), tilt=12, kz=1.12)
one(bar(48), bar(50), '15c', size=('w', 1400), ent=1.0, s1=1.08)
one(bar(50), bar(51), '16a', size=('w', 1400), ent=0.8)
FLASHES.append((bar(51), 0.35, 0.5))
one(bar(51), bar(53), '16b', h=900, ent=0.9, frm=(0, 40), s1=1.08, kz=1.12, f=(0.4, 0.4))
# Breakdown - doubt (182.59 - 206.69)
shot(bar(53), bar(56), [C('17', h=950, ent=0.8, s1=1.05, shatter=bar(55) - bar(53))])
one(bar(56), 201.0, '18', h=1010, ent=1.2, kz=1.35, f=(0.5, 0.32))
one(201.0, 203.11, '12d', h=900, ent=0.6, kz=1.3, f=(0.45, 0.4))
flick([203.11, 203.95, 204.76, 205.57, 206.12, DROP2], ['03e', '06a', '06c', '09b', '07c'], flash=0.3)
# Final chorus - the answer (206.69 - 223.66)
shot(DROP2, fb(-7), [dict(p='10', r=[0, 474, 611, 344], bleed=True, ent=0, kz=1.12, f=(0.5, 0.5))])
FLASHES.append((fb(-7), 0.4, 0.15))
shot(fb(-7), fb(-6), [dict(p='13', r=[53, 20, 927, 521], bleed=True, ent=0, kz=1.15, f=(0.43, 0.5), warp=True)])
flick([fb(n) for n in range(-6, 1)], ['06c', '16b', '14a', '15b', '03e', '08a'], flash=0.25)
one(fb(0), fb(4), '19a', size=('w', 1500), frm=(-80, 0), kz=1.05)
one(fb(4), fb(8), '19b', size=('w', 1500), frm=(-80, 0), kz=1.05)
one(fb(8), fb(12), '19c', size=('w', 1500), frm=(-80, 0), kz=1.08, f=(0.5, 0.6))
# Outro - the ending, then credits
FLASHES.append((fb(12), 0.55, 0.6))
shot(fb(12), 236.5, [C('20', h=640, cy=600, ent=2.0, frm=(0, 30), blend='mul', s0=1.0, s1=1.14,
                       d1=(0, -30), m=0)], bg='paper')
shot(236.5, DUR + 0.1, [], bg='black')

# ---------------------------------------------------------------- text
SERIF_I = FD + 'georgiai.ttf'
TITLE = FD + 'constan.ttf'
MONO = FD + 'consola.ttf'
CREAM = (0.97, 0.93, 0.86)
INK = (0.13, 0.10, 0.08)
TEXTS = [
    dict(t=1.2, end=7.9, lines=['What is a life worth?'], font=SERIF_I, size=70, align='c', y=500, stagger=0.06,
         cdur=0.9),
    dict(t=16.2, end=21.9, lines=['I sold off all', 'but three months', 'of my life.'], font=SERIF_I, size=60,
         x=150, y=370, lt=[16.2, 17.05, 17.9]),
    dict(t=23.0, end=28.5, lines=['Then, the next day,', 'a girl came to my room.'], font=SERIF_I, size=62,
         x=150, y=440, lt=[23.0, 25.52]),
    dict(t=116.1, end=118.95, lines=['THREE DAYS OF HAPPINESS'], font=TITLE, size=70, align='c', y=230,
         track=22, stagger=0.05, cdur=1.0, glow=True),
    dict(t=224.4, end=236.4, lines=['were of much, much more value.'], font=SERIF_I, size=58, align='c', y=120,
         color=INK, shadow=False, stagger=0.05),
    dict(t=237.3, end=249.6, lines=['THREE DAYS OF HAPPINESS'], font=TITLE, size=62, align='c', y=455,
         track=20, stagger=0.06, cdur=1.2, glow=True),
    dict(t=239.6, end=249.6, lines=['story by Sugaru Miaki  \u00b7  art by Shouichi Taguchi'], font=SERIF_I,
         size=30, align='c', y=560, stagger=0.02, color=(0.80, 0.74, 0.66)),
]
_FONTS = {}
def font(path, size):
    k = (path, size)
    if k not in _FONTS: _FONTS[k] = ImageFont.truetype(path, size)
    return _FONTS[k]

def draw_text(L, spec, t):
    if t < spec['t'] - 0.01 or t > spec['end']: return False
    f = font(spec['font'], spec['size'])
    track = spec.get('track', 0); stg = spec.get('stagger', 0.028); cd = spec.get('cdur', 0.55)
    rise = spec.get('rise', 22); lh = spec['size'] * 1.32
    fade = clamp((spec['end'] - t) / 0.6)
    d = ImageDraw.Draw(L)
    lts = spec.get('lt', [spec['t']] * len(spec['lines']))
    for li, line in enumerate(spec['lines']):
        widths = [f.getlength(ch) + track for ch in line]
        tw = sum(widths) - track
        x = (W - tw) / 2 if spec.get('align') == 'c' else spec['x']
        y = spec['y'] + li * lh
        for ci, ch in enumerate(line):
            u = eout((t - lts[li] - ci * stg) / cd)
            if u > 0 and ch != ' ':
                d.text((x, y + rise * (1 - u)), ch, font=f, fill=int(255 * u * fade))
            x += widths[ci]
    return True

# ---------------------------------------------------------------- HUD counter
HUD_IN, HUD_OUT = 5.46, STRIKE + 1.4
def days_at(t):
    if t < bar(4): return 30 * 365
    if t < bar(4) + 1.7: return int(lerp(30 * 365, 92, eio((t - bar(4)) / 1.7)))
    return int(lerp(92, 30, clamp((t - bar(4) - 1.7) / (STRIKE - bar(4) - 1.7))))
def sold_at(t):
    if t < bar(4): return '0'
    if t < GLITCH: return f"{int(lerp(0, 300000, eio((t - bar(4)) / 1.7))):,}"
    return '30'
def hud(Lr, t):
    if t < HUD_IN or t > HUD_OUT: return 0.0
    a = clamp((t - HUD_IN) / 0.8) * clamp((HUD_OUT - t) / 0.6)
    d = ImageDraw.Draw(Lr); lab = font(MONO, 17); val = font(MONO, 30)
    dd = days_at(t); y, m, dy = dd // 365, (dd % 365) // 30, (dd % 365) % 30
    rows = [('LIFESPAN', f'{y:02d}Y {m:02d}M {dy:02d}D'), ('SOLD FOR', f'\u00a5 {sold_at(t)}')]
    for i, (l, v) in enumerate(rows):
        yy = 952 + i * 46
        d.text((80, yy + 9), ' '.join(l), font=lab, fill=int(200 * a))
        if GLITCH <= t < GLITCH + 0.45 and i == 1:
            rng = np.random.default_rng(int(t * 97))
            v = '\u00a5 ' + ''.join(rng.choice(list('0123456789#%$/\\')) for _ in range(rng.integers(2, 8)))
        d.text((280, yy), v, font=val, fill=int(240 * a))
    if t > STRIKE:
        u = eout((t - STRIKE) / 0.45)
        for i in range(2):
            yy = 952 + i * 46 + 18
            d.line([(76, yy), (76 + 380 * u, yy)], fill=int(240 * a), width=3)
    return a

# ---------------------------------------------------------------- fireflies
rng = np.random.default_rng(7)
NP = 190
FX = rng.random(NP); FY = rng.random(NP); DEP = rng.random(NP) ** 1.8
VX = (rng.random(NP) - .5) * 0.018; VY = -(0.004 + rng.random(NP) * 0.016)
PH = rng.random(NP) * 6.283; SP = 0.7 + rng.random(NP) * 2.4; WOB = rng.random(NP) * 0.014
RANK = rng.permutation(NP)
SIGS = np.geomspace(0.7, 16, 18)
def _sprite(s):
    r = int(math.ceil(s * 3)); yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return np.exp(-(xx ** 2 + yy ** 2) / (2 * s * s)).astype(np.float32)
SPR = [_sprite(s) for s in SIGS]
BURSTS = [DROP1, DROP2]

def density(t):
    return keys(t, [(99.0, 0), (105.7, 0.04), (112.4, 0.10), (DROP1 - 0.01, 0.12), (DROP1, 0.0),
                    (DROP1 + 0.05, 1.0), (165.9, 0.95), (182.6, 0.6), (186.0, 0.12), (201.0, 0.15),
                    (DROP2 - 0.01, 0.3), (DROP2, 0.0), (DROP2 + 0.05, 1.0), (fb(0), 0.7), (fb(12), 0.45),
                    (236.5, 0.45), (238.0, 0.75), (DUR, 0.75)])

def fireflies(t):
    dn = density(t)
    if dn <= 0.001: return None
    hw, hh = W // 2, H // 2
    buf = np.zeros((hh, hw), np.float32)
    x = (FX + VX * t + WOB * np.sin(t * 0.9 + PH)) % 1.1 - 0.05
    y = (FY + VY * t + WOB * np.cos(t * 0.7 + PH)) % 1.1 - 0.05
    for b in BURSTS:
        if b <= t < b + 2.2:
            k = lerp(0.08, 1.0, eout((t - b) / 2.2))
            x = 0.5 + (x - 0.5) * k; y = 0.6 + (y - 0.6) * k
    vis = np.clip((dn * NP - RANK) / 10, 0, 1)
    tw = 0.45 + 0.55 * (0.5 + 0.5 * np.sin(t * SP + PH))
    for i in range(NP):
        if vis[i] <= 0: continue
        si = int(DEP[i] * (len(SIGS) - 1)); spr = SPR[si]; r = spr.shape[0] // 2
        amp = vis[i] * tw[i] * lerp(1.0, 0.16, DEP[i])
        cx, cy = int(x[i] * hw), int(y[i] * hh)
        x0, y0, x1, y1 = cx - r, cy - r, cx + r + 1, cy + r + 1
        sx0, sy0 = max(0, -x0), max(0, -y0)
        x0c, y0c, x1c, y1c = max(x0, 0), max(y0, 0), min(x1, hw), min(y1, hh)
        if x1c <= x0c or y1c <= y0c: continue
        buf[y0c:y1c, x0c:x1c] += amp * spr[sy0:sy0 + (y1c - y0c), sx0:sx0 + (x1c - x0c)]
    bloom = cv2.GaussianBlur(buf, (0, 0), 9)
    return cv2.resize(buf + 0.9 * bloom, (W, H), interpolation=cv2.INTER_LINEAR)

# ---------------------------------------------------------------- look
def warmth(t):
    return keys(t, [(0, 0), (bar(15), 0), (bar(16), 0.22), (bar(23), 0.28), (bar(24), 0.04), (105.7, 0.04),
                    (112.4, 0.15), (DROP1 - 0.01, 0.2), (DROP1, 0.6), (bar(41) - 0.01, 0.85), (bar(41), 1.0),
                    (bar(53), 1.0), (bar(54), 0.05), (201.0, 0.06), (DROP2 - 0.01, 0.3), (DROP2, 1.0),
                    (DUR, 1.0)])
SH_C, HI_C = np.array([0.030, 0.035, 0.045]), np.array([0.90, 0.93, 0.96])
SH_W, HI_W = np.array([0.075, 0.045, 0.030]), np.array([1.00, 0.92, 0.78])
AMBER = np.array([1.0, 0.70, 0.32], np.float32)
FLASHES += [(DROP1, 1.0, 0.45), (DROP2, 1.0, 0.45), (bar(2), 0.18, 0.5)]

_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx / W - .5) * 2) ** 2 * 0.85 + ((_yy / H - .5) * 2) ** 2 * 0.85)
VIG = (1 - 0.42 * np.clip((_r - 0.45) / 0.85, 0, 1) ** 1.5).astype(np.float32)
_g = np.random.default_rng(3)
GRAIN = [cv2.resize(_g.normal(0, 0.024, (H // 2, W // 2)).astype(np.float32), (W, H)) for _ in range(8)]
LEAK = np.exp(-(((_xx - W) / (W * 0.45)) ** 2 + ((_yy - H * 0.2) / (H * 0.6)) ** 2)).astype(np.float32)
del _yy, _xx, _r

# ---------------------------------------------------------------- card rendering
def quad(cx, cy, fw, fh, tilt):
    f = 1800.0; pts = []
    for X, Y in [(-fw / 2, -fh / 2), (fw / 2, -fh / 2), (fw / 2, fh / 2), (-fw / 2, fh / 2)]:
        z = X * math.sin(tilt); k = f / (f + z)
        pts.append((cx + X * math.cos(tilt) * k, cy + Y * k))
    return np.float32(pts)

def poly_mask(q, bx, by, bw, bh):
    m = np.zeros((bh, bw), np.uint8)
    cv2.fillConvexPoly(m, np.int32(np.round((q - [bx, by]) * 16)), 255, cv2.LINE_AA, 4)
    return m.astype(np.float32) / 255

SHARDS = {}
def shards(key, bw, bh):
    if key not in SHARDS:
        r = np.random.default_rng(11); pts = [(0, 0), (bw - 1, 0), (bw - 1, bh - 1), (0, bh - 1)]
        for gx in range(5):
            for gy in range(7):
                pts.append((min(bw - 1, max(0, (gx + 0.5 + r.uniform(-.35, .35)) * bw / 5)),
                            min(bh - 1, max(0, (gy + 0.5 + r.uniform(-.35, .35)) * bh / 7))))
        sd = cv2.Subdiv2D((0, 0, bw + 1, bh + 1))
        for p in pts: sd.insert((float(p[0]), float(p[1])))
        tris = [np.float32(t).reshape(3, 2) for t in sd.getTriangleList()
                if all(0 <= v <= bw + 1 for v in t[0::2]) and all(0 <= v <= bh + 1 for v in t[1::2])]
        SHARDS[key] = [(tr, r.uniform(-1, 1), r.uniform(0.6, 1.4), r.uniform(0, 0.3)) for tr in tris]
    return SHARDS[key]

def render_card(cv, c, t, sh):
    lt = t - sh['t0'] - c.get('t_in', 0)
    if lt < 0: return
    dur = sh['t1'] - sh['t0'] - c.get('t_in', 0); u = lt / dur
    ent = c.get('ent', 0.5); e = eout(lt / ent) if ent > 0 else 1.0
    a = e * (clamp((sh['t1'] - t) / c.get('exit', 0.1)) if c.get('exit', 0.1) > 0 else 1)
    im, up, s = page(c['p'])
    x, y, w, h = c['r']
    if 'rB' in c:
        xb, yb, wb, hb = c['rB']; k = eio(u)
        x, y, w, h = lerp(x, xb, k), lerp(y, yb, k), lerp(w, wb, k), lerp(h, hb, k)
        asp = c['r'][2] / c['r'][3]
    else:
        asp = w / h
        z = lerp(1, c.get('kz', 1), eio(u)); fx, fy = c.get('f', (0.5, 0.5))
        w2, h2 = w / z, h / z; x, y = x + (w - w2) * fx, y + (h - h2) * fy; w, h = w2, h2
    src = np.float32([[x, y], [x + w, y], [x + w, y + h], [x, y + h]]) * s
    bleed = c.get('bleed', False)
    if bleed: fw, fh = W, H
    elif 'h' in c: fh = c['h']; fw = fh * asp
    else: fw = c['w']; fh = fw / asp
    sc = lerp(c.get('s0', 1.0), c.get('s1', 1.04), eio(u)) * lerp(c.get('es', 1.06), 1, e)
    if bleed: sc = max(sc, 1.0)
    d0, d1, fr = c.get('d0', (0, 0)), c.get('d1', (0, 0)), c.get('frm', (0, 30))
    cx = c.get('cx', W / 2) + lerp(d0[0], d1[0], eio(u)) + fr[0] * (1 - e)
    cy = c.get('cy', H / 2) + lerp(d0[1], d1[1], eio(u)) + fr[1] * (1 - e)
    if 'shake' in c:
        st, amp = c['shake']; k = math.exp(-max(0, lt - st) * 7) * amp
        cx += k * math.sin(lt * 61); cy += k * math.cos(lt * 47)
    fw *= sc; fh *= sc
    tilt = math.radians(c.get('tilt', 0)) * (1 - e)
    q = quad(cx, cy, fw, fh, tilt)
    m = 0 if bleed else c.get('m', 10) * sc
    qm = quad(cx, cy, fw + 2 * m, fh + 2 * m, tilt)
    bx, by = int(max(0, math.floor(qm[:, 0].min()) - 2)), int(max(0, math.floor(qm[:, 1].min()) - 2))
    bx1, by1 = int(min(W, math.ceil(qm[:, 0].max()) + 2)), int(min(H, math.ceil(qm[:, 1].max()) + 2))
    bw, bh = bx1 - bx, by1 - by
    if bw <= 2 or bh <= 2: return
    M = cv2.getPerspectiveTransform(src, q - np.float32([bx, by]))
    content = cv2.warpPerspective(up, M, (bw, bh), flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_REPLICATE).astype(np.float32) / 255
    if c.get('warp'):
        yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
        mk = np.clip((xx / bw - 0.52) / 0.3, 0, 1) * np.clip((yy / bh - 0.15) / 0.3, 0, 1)
        dx = 7 * np.sin(yy / 85 + lt * 2.1 + xx / 260) * mk
        dy = 3 * np.sin(xx / 120 + lt * 1.6) * mk
        content = cv2.remap(content, xx + dx, yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    mc = poly_mask(q, bx, by, bw, bh)
    if m > 0:
        mm = poly_mask(qm, bx, by, bw, bh)
        val = 0.95 * (1 - mc) + content * mc; alp = mm
    else:
        val, alp = content, mc
    region = cv[by:by1, bx:bx1]
    shat = c.get('shatter')
    if shat is not None and lt > shat:
        p = clamp((lt - shat) / (dur - shat - 0.15))
        layer_v = np.zeros_like(cv); layer_a = np.zeros_like(cv)
        ccx, ccy = bw / 2, bh / 2
        for tri, rot, spd, dl in shards(c['p'], bw, bh):
            pp = clamp((p - dl) / (1 - dl)) ** 1.6
            tc = tri.mean(0); dv = tc - [ccx, ccy]; dv = dv / (np.linalg.norm(dv) + 1e-3)
            off = dv * pp * 520 * spd + np.float32([0, -pp * 120])
            Rm = cv2.getRotationMatrix2D((float(tc[0]), float(tc[1])), rot * 50 * pp, 1 - 0.2 * pp)
            Rm[:, 2] += [bx + off[0], by + off[1]]
            tm = np.zeros((bh, bw), np.float32); cv2.fillConvexPoly(tm, np.int32(tri), 1.0, cv2.LINE_AA)
            fa = (1 - pp) * a
            wa = cv2.warpAffine(alp * tm * fa, Rm, (W, H))
            wv = cv2.warpAffine(val, Rm, (W, H))
            layer_v = layer_v * (1 - wa) + wv * wa; layer_a = layer_a + wa * (1 - layer_a)
        cv *= 1 - 0.4 * cv2.GaussianBlur(layer_a, (0, 0), 14)
        cv[:] = cv * (1 - layer_a) + layer_v * layer_a
        return
    if not bleed and c.get('blend') != 'mul':
        hm = cv2.resize(alp, (max(1, bw // 4), max(1, bh // 4)))
        hm = cv2.GaussianBlur(hm, (0, 0), 6)
        hm = cv2.resize(hm, (bw, bh))
        sy = 18; sh_ = np.zeros_like(hm); sh_[sy:] = hm[:-sy]
        region *= 1 - 0.55 * a * sh_
    if c.get('blend') == 'mul':
        region[:] = region * (1 - a * alp + a * alp * val)
    else:
        aa = a * alp; region[:] = region * (1 - aa) + val * aa

BGC = {}
def background(si, sh, t):
    if sh['bg'] == 'black': return np.full((H, W), 0.03, np.float32)
    if sh['bg'] == 'paper': return np.full((H, W), 0.95, np.float32)
    if si not in BGC:
        BGC.clear()   # only keep the current shot's backdrop
        c = sh['cards'][0]; im = page(c['p'])[0]; x, y, w, h = c['r']
        cr = im[y:y + h, x:x + w]; k = max(480 / w, 270 / h)
        sm = cv2.resize(cr, (int(w * k) + 1, int(h * k) + 1), interpolation=cv2.INTER_AREA)
        oy, ox = (sm.shape[0] - 270) // 2, (sm.shape[1] - 480) // 2
        sm = cv2.GaussianBlur(sm[oy:oy + 270, ox:ox + 480], (0, 0), 7)
        BGC[si] = (0.035 + 0.26 * cv2.resize(sm, (W, H), interpolation=cv2.INTER_CUBIC)).astype(np.float32)
    u = (t - sh['t0']) / (sh['t1'] - sh['t0']); z = 1.0 + 0.06 * u
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
    return cv2.warpAffine(BGC[si], M, (W, H), borderMode=cv2.BORDER_REFLECT)

# ---------------------------------------------------------------- frame
def frame(fi):
    t = fi / FPS
    si = next(i for i, s in enumerate(S) if s['t0'] <= t < s['t1'])
    sh = S[si]
    cv = background(si, sh, t)
    for c in sh['cards']: render_card(cv, c, t, sh)
    cv = np.clip(cv, 0, 1)
    w = warmth(t)
    sh_c = lerp(SH_C, SH_W, w).astype(np.float32); hi_c = lerp(HI_C, HI_W, w).astype(np.float32)
    rgb = sh_c + (hi_c - sh_c) * cv[..., None]
    if w > 0.05:
        ox = int(140 * math.sin(t * 0.37)); M = np.float32([[1, 0, ox], [0, 1, 0]])
        lk = cv2.warpAffine(LEAK, M, (W, H))
        rgb += (0.16 * w * lk)[..., None] * AMBER
    ff = fireflies(t)
    if ff is not None:
        gain = 1.0 if sh['bg'] != 'paper' else 0.5
        rgb += (gain * ff)[..., None] * AMBER
        rgb += (0.35 * gain * np.clip(ff - 0.6, 0, None))[..., None]
    for sp in TEXTS:   # each text spec composited with its own colour
        TL = Image.new('L', (W, H), 0)
        if not draw_text(TL, sp, t): continue
        ta = np.asarray(TL, np.float32) / 255
        if sp.get('shadow', True): rgb *= (1 - 0.55 * cv2.GaussianBlur(ta, (0, 0), 9))[..., None]
        rgb = rgb * (1 - ta[..., None]) + np.float32(sp.get('color', CREAM)) * ta[..., None]
        if sp.get('glow'): rgb += (0.5 * cv2.GaussianBlur(ta, (0, 0), 14))[..., None] * AMBER
    HL = Image.new('L', (W, H), 0); ha = hud(HL, t)
    if ha > 0:
        h_ = np.asarray(HL, np.float32) / 255
        rgb *= (1 - 0.6 * cv2.GaussianBlur(h_, (0, 0), 6))[..., None]
        if GLITCH <= t < GLITCH + 0.45:
            for ch, dx in ((0, 7), (2, -7)):
                sh_h = np.roll(h_, dx, axis=1); rgb[..., ch] = rgb[..., ch] * (1 - sh_h) + sh_h
        rgb = rgb * (1 - h_[..., None]) + np.float32(CREAM) * h_[..., None]
    fl = sum(pk * math.exp(-(t - tf) / dc) for tf, pk, dc in FLASHES if t >= tf)
    if fl > 0.003: rgb = rgb + (np.float32([1.0, 0.97, 0.92]) - rgb) * min(fl, 1)
    rgb *= VIG[..., None]
    rgb += GRAIN[fi % 8][..., None]
    rgb *= keys(t, [(0, 1), (DUR - 1.3, 1), (DUR, 0)])
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)

# ---------------------------------------------------------------- main
def stills(times):
    d = os.path.join(HERE, 'stills_full'); os.makedirs(d, exist_ok=True)
    thumbs = []
    for tt in times:
        fr = frame(int(round(tt * FPS)))
        cv2.imwrite(os.path.join(d, f'{tt:06.2f}.png'), fr[..., ::-1])
        th = cv2.resize(fr[..., ::-1], (480, 270), interpolation=cv2.INTER_AREA)
        cv2.putText(th, f'{tt:.2f}', (8, 22), 0, 0.6, (0, 255, 255), 2); thumbs.append(th)
    while len(thumbs) % 5: thumbs.append(np.zeros_like(thumbs[0]))
    rows = [np.hstack(thumbs[i:i + 5]) for i in range(0, len(thumbs), 5)]
    cv2.imwrite(os.path.join(d, 'contact.jpg'), np.vstack(rows))

def video():
    import imageio_ffmpeg
    from multiprocessing import Pool
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmpv = os.path.join(HERE, '_full_video.mp4'); tmpa = os.path.join(HERE, '_full_audio.m4a')
    subprocess.run([ff, '-y', '-v', 'error', '-i', SONG, '-t', str(DUR),
                    '-af', 'afade=t=out:st=248.3:d=1.2,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000',
                    '-c:a', 'aac', '-b:a', '320k', tmpa], check=True)
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19',
                          '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmpv], stdin=subprocess.PIPE)
    with Pool(max(1, os.cpu_count() - 1)) as pool:
        for i, fr in enumerate(pool.imap(frame, range(N), chunksize=6)):
            p.stdin.write(fr.tobytes())
            if i % 300 == 0: print(f'frame {i}/{N}', flush=True)
    p.stdin.close(); p.wait()
    subprocess.run([ff, '-y', '-v', 'error', '-i', tmpv, '-i', tmpa, '-map', '0:v', '-map', '1:a', '-c', 'copy',
                    '-t', str(DUR), '-movflags', '+faststart', OUT], check=True)
    os.remove(tmpv); os.remove(tmpa)
    print('wrote', OUT)

if __name__ == '__main__':
    if sys.argv[1] == 'stills':
        stills([float(x) for x in sys.argv[2].split(',')])
    else:
        video()
