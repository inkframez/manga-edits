"""Ibitsu (イビツ, Ryou Haruto) - 27 s horror Short, 1080x1920, 30 fps.

Concept: the urban legend's question 「妹、いる？」 ("do you have a little sister?"). The film creeps slowly, then breaks.
Look: cold sickly monochrome, crimson only for blood / the question, flickering fluorescent light, gate weave, film dust
and scratches, camcorder REC section with a hunting flashlight, subliminal 1-2 frame faces, hair-drip and static
transitions, a dead-silent beat before the final scare. All times live in EV / shot list below; music.py reads EV.
Usage:  python render.py stills 1,5,12   |   python render.py video   (muxes music.wav from music.py)
"""
import os, sys, math, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
PAN = os.path.join(ROOT, 'panels')
W, H, FPS = 1080, 1920, 30
DUR = 27.0; N = int(DUR * FPS)
FD = 'C:/Windows/Fonts/' if os.name == 'nt' else os.path.join(os.path.dirname(ROOT), 'fonts') + '/'
cv2.setNumThreads(1)

# ---------------------------------------------------------------- timeline (seconds) - shared with music.py
EV = dict(
    question=0.5, q_en=1.7, spot=3.2, girl=6.0, behind=9.0, sub1=10.15, door=10.8, back=13.0, rec=14.6,
    crawl=16.4, eye=17.3, bars=18.0, onii=18.6, face=20.0, silence=21.25, scare=21.6, title=23.6,
    last_q=25.3, last_eye=26.75,
)

def clamp(u, a=0.0, c=1.0): return min(max(u, a), c)
def eout(u): u = clamp(u); return 1 - (1 - u) ** 3
def ein(u): u = clamp(u); return u ** 3
def eio(u): u = clamp(u); return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2
def lerp(a, c, u): return a + (c - a) * u
def hexc(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)
CRIM, BLOOD, PALE, INKC = hexc('#B3121D'), hexc('#5E0409'), hexc('#DCE2DD'), hexc('#040506')

# ---------------------------------------------------------------- pages
PAGES = {}
def page(n):
    if n not in PAGES:
        fn = [f for f in os.listdir(PAN) if f.startswith(n + '.')][0]
        a = np.asarray(Image.open(os.path.join(PAN, fn)).convert('RGB'), np.float32) / 255
        s = 2.0
        up = cv2.resize(a, None, fx=s, fy=s, interpolation=cv2.INTER_LANCZOS4)
        bl = cv2.GaussianBlur(up, (0, 0), 1.3); up = np.clip(up + 0.5 * (up - bl), 0, 1)
        PAGES[n] = (up.astype(np.float32), s)
    return PAGES[n]

def view(n, rect, warp=None):
    x, y, w, h = rect
    k = max(W / w, H / h)
    M = np.float32([[k, 0, W / 2 - k * (x + w / 2)], [0, k, H / 2 - k * (y + h / 2)]])
    up, s = page(n); Ms = M.copy(); Ms[:, :2] /= s
    img = cv2.warpAffine(up, Ms, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    return img

def grade(img, keep_red=False):
    """B/W -> cold sickly ramp; optional: keep the cover's reds as crimson."""
    l = img.mean(2, keepdims=True)
    l = np.clip((l - 0.04) / 0.9, 0, 1) ** 1.15
    sh, mid, hi = hexc('#030405'), hexc('#4E5659'), hexc('#D5DBD4')
    out = np.where(l < 0.5, sh + (mid - sh) * (l * 2), mid + (hi - mid) * (l * 2 - 1))
    if keep_red:
        red = np.clip((img[..., 0:1] - np.maximum(img[..., 1:2], img[..., 2:3]) - 0.18) * 4, 0, 1)
        out = out * (1 - red) + CRIM * (0.6 + 0.6 * l) * red
    return out.astype(np.float32)

# ---------------------------------------------------------------- shots: (t0, t1, page, r0, r1, opts)
def R(x, y, w, h): return [x, y, w, h]
SHOTS = [
    (0.0, 3.2, '01', R(60, 40, 260, 462), R(95, 95, 190, 338), dict(red=True, on=0.45)),
    (3.2, 6.0, '01', R(1270, 330, 290, 515), R(1325, 480, 190, 338), dict(red=True)),
    (6.0, 9.0, '02', R(200, 40, 420, 747), R(255, 300, 400, 711), dict(tr='drip')),
    (9.0, 10.8, '03', R(120, 590, 200, 355), R(170, 650, 130, 231), dict()),
    (10.8, 13.0, '04', R(130, 0, 460, 818), R(235, 130, 230, 409), dict(tr='flick')),
    (13.0, 14.6, '13', R(60, 280, 560, 996), R(110, 330, 420, 747), dict(tr='drip')),
    (14.6, 16.4, '09', R(130, 560, 440, 782), R(215, 630, 300, 533), dict(tr='static', rec=True)),
    (16.4, 17.3, '10', R(560, 0, 400, 711), R(600, 30, 330, 587), dict(rec=True, shake=8)),
    (17.3, 18.0, '10', R(650, 950, 300, 533), R(735, 1015, 190, 338), dict(punch=True)),
    (18.0, 20.0, '11', R(300, 600, 440, 782), R(405, 770, 250, 444), dict(tr='flick')),
    (20.0, 21.25, '14', R(500, 240, 460, 818), R(575, 330, 290, 516), dict(tr='drip', uncanny=True)),
    (21.25, 21.6, None, None, None, dict()),                                   # dead silence: black
    (21.6, 23.6, '15', R(300, 260, 560, 996), R(330, 380, 450, 800), dict(scare=True)),
    (23.6, 25.3, '01', R(300, 0, 472, 840), R(330, 60, 420, 747), dict(red=True, tr='blood')),
    (25.3, DUR + 0.1, None, None, None, dict()),
]
SUBLIM = [(EV['sub1'], 2, '15', R(450, 520, 400, 711)), (13.9, 1, '14', R(560, 330, 300, 533)),
          (19.4, 1, '15', R(420, 480, 420, 747)), (EV['last_eye'], 3, '11', R(450, 860, 160, 284))]
FLICK_DROPS = [2.6, 5.1, 7.7, 8.3, 11.9, 12.2, 15.8, 19.0, 20.6, 24.4]           # brief light failures
SCARES = [(EV['sub1'], 0.5), (EV['eye'], 0.9), (EV['scare'], 1.6)]

# ---------------------------------------------------------------- text
_F, _SP = {}, {}
def font(name, size):
    k = (name, size)
    if k not in _F: _F[k] = ImageFont.truetype(FD + name, size)
    return _F[k]
JP, JPL, HAND = 'YuGothB.ttc', 'YuGothL.ttc', 'Inkfree.ttf'

def distressed(s, fnt, size, vertical=False, seed=0, rough=0.5):
    key = (s, fnt, size, vertical, seed, rough)
    if key in _SP: return _SP[key]
    f = font(fnt, size)
    if vertical: Wd, Hd = int(size * 1.5), int(len(s) * size * 1.08 + size * 0.5)
    else: Wd, Hd = int(f.getlength(s) + size * 0.6), int(size * 1.6)
    img = Image.new('L', (Wd, Hd), 0); d = ImageDraw.Draw(img)
    if vertical:
        for i, ch in enumerate(s):
            cx, cy = Wd / 2, size * 0.35 + i * size * 1.08 + size / 2
            if ch in 'ー…':
                t = Image.new('L', (size * 2, size * 2), 0); ImageDraw.Draw(t).text((size, size), ch, font=f, fill=255, anchor='mm')
                img.paste(t.rotate(-90), (int(cx - size), int(cy - size)), t.rotate(-90))
            elif ch in '、。': d.text((cx + size * 0.32, cy - size * 0.32), ch, font=f, fill=255, anchor='mm')
            else: d.text((cx, cy), ch, font=f, fill=255, anchor='mm')
    else:
        d.text((size * 0.3, size * 0.2), s, font=f, fill=255)
    a = np.asarray(img, np.float32) / 255
    if rough:
        r = np.random.default_rng(seed)
        n = cv2.resize(r.random((Hd // 3 + 1, Wd // 3 + 1)).astype(np.float32), (Wd, Hd))
        a = a * np.clip((n - rough * 0.35) * 3, 0, 1)                         # eaten-away ink
        dx = cv2.resize(r.normal(0, 1, (Hd // 12 + 2, Wd // 12 + 2)).astype(np.float32), (Wd, Hd)) * 2.5 * rough
        yy, xx = np.mgrid[0:Hd, 0:Wd].astype(np.float32)
        a = cv2.remap(a, xx + dx, yy, cv2.INTER_LINEAR)
    _SP[key] = a
    return a

def put(rgb, alpha, cx, cy, col, a=1.0, glow=0.0):
    h, w = alpha.shape
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xb <= xa or yb <= ya: return
    al = alpha[ya - y0:yb - y0, xa - x0:xb - x0][..., None] * a
    reg = rgb[ya:yb, xa:xb]
    if glow: reg += cv2.GaussianBlur(al[..., 0], (0, 0), 18)[..., None] * col * glow
    reg[:] = reg * (1 - al) + col * al

TEXT = [   # t, t_end, text, font, size, x, y, vertical, colour, mode
    (EV['q_en'], 3.1, 'do you have a little sister?', HAND, 60, W / 2, 1520, False, PALE, 'type'),
    (6.6, 8.9, 'ゴミ捨て場の少女', JPL, 74, 930, 640, True, PALE, 'reveal'),
    (14.9, 16.3, 'WHOA... ARE THOSE SCRATCHES?', HAND, 40, W / 2, 1640, False, PALE, 'type'),
    (EV['onii'], 19.95, 'お兄ちゃん…', JP, 120, 900, 560, True, CRIM, 'reveal'),
    (20.3, 21.2, 'THE WOMAN NEXT DOOR', HAND, 44, W / 2, 1700, False, PALE, 'type'),
    (EV['scare'] + 0.15, 23.5, 'アハハハハハハ', JP, 150, 140, 900, True, CRIM, 'scroll'),
    (EV['last_q'] + 0.3, DUR, '妹、いる？', JP, 150, W / 2, 900, True, CRIM, 'reveal'),
    (EV['last_q'] + 1.4, DUR, 'IBITSU  —  RYOU HARUTO', HAND, 40, W / 2, 1640, False, PALE, 'type'),
]

def draw_text(rgb, t, fi):
    for t0, t1, s, fnt, size, x, y, vert, col, mode in TEXT:
        if not (t0 <= t < t1): continue
        lt = t - t0; fade = clamp((t1 - t) / 0.12)
        if mode == 'type':
            n = int(len(s) * clamp(lt / (len(s) * 0.045)))
            if n <= 0: continue
            full = distressed(s, fnt, size, vert, seed=1, rough=0.25); part = distressed(s[:n], fnt, size, vert, seed=1, rough=0.25)
            put(rgb, part, x - full.shape[1] / 2 + part.shape[1] / 2, y, col, 0.9 * fade)
        elif mode == 'reveal':          # characters bleed in one by one, jitter like a bad signal
            for i, ch in enumerate(s):
                lc = lt - i * 0.22
                if lc < 0: break
                a = clamp(lc / 0.35) * fade
                jx = (np.random.default_rng(fi * 7 + i).normal(0, 1.5)) if lc < 0.6 else 0
                spr = distressed(ch, fnt, size, False, seed=i + 3, rough=0.6)
                cy = y + i * size * 1.08 if vert else y
                cx = x if vert else x + (i - (len(s) - 1) / 2) * size
                if vert and ch in '、。': cx += size * 0.3; cy -= size * 0.3
                put(rgb, spr, cx + jx, cy, col, a)
        elif mode == 'scroll':          # column of laughter crawling down, shaking
            for i, ch in enumerate(s):
                lc = lt - i * 0.09
                if lc < 0: break
                r = np.random.default_rng(fi * 13 + i)
                spr = distressed(ch, fnt, size, False, seed=i + 9, rough=0.5)
                put(rgb, spr, x + r.normal(0, 6), y - 520 + i * size * 0.95 + 120 * lt + r.normal(0, 6), col, fade)

# ---------------------------------------------------------------- textures
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx / W - .5) * 2) ** 2 * 0.9 + ((_yy / H - .5) * 2) ** 2 * 0.55)
VIG = (1 - 0.82 * np.clip((_r - 0.25) / 1.0, 0, 1) ** 1.3).astype(np.float32)[..., None]
_g = np.random.default_rng(4)
GRAIN = [cv2.resize(_g.normal(0, 0.05, (H // 3, W // 3)).astype(np.float32), (W, H))[..., None] for _ in range(6)]
COLSPEED = np.repeat(np.random.default_rng(8).uniform(0.55, 1.6, W // 6 + 1), 6)[:W].astype(np.float32)
COLSPEED = cv2.GaussianBlur(COLSPEED[None, :], (0, 0), 2)[0]
SCAN = (1 - 0.12 * (np.arange(H) % 4 < 2)).astype(np.float32)[:, None, None]

def static(fi):
    n = np.random.default_rng(fi).random((H // 4, W // 4)).astype(np.float32)
    n = cv2.resize(n, (W, H), interpolation=cv2.INTER_NEAREST)
    return np.repeat(n[..., None], 3, 2)

def transition(cur, prev, kind, u, fi):
    if kind == 'drip':                  # long black hair / ink dripping down reveals the next shot
        front = (u * 1.5 * COLSPEED)[None, :] * H
        m = (_yy < front - 40).astype(np.float32)[..., None]
        ink = ((_yy >= front - 40) & (_yy < front + 140 * COLSPEED[None, :])).astype(np.float32)[..., None]
        out = prev * (1 - m) + cur * m
        return out * (1 - ink) + INKC * ink
    if kind == 'blood':
        front = (u * 1.4 * COLSPEED)[None, :] * H
        m = (_yy < front - 60).astype(np.float32)[..., None]
        bl = ((_yy >= front - 60) & (_yy < front + 90 * COLSPEED[None, :])).astype(np.float32)[..., None]
        return (prev * (1 - m) + cur * m) * (1 - bl) + BLOOD * bl
    if kind == 'static':
        s = static(fi) * 0.9
        return s if u < 0.6 else cur * 0.6 + s * 0.4
    if kind == 'flick':
        return prev * 0.15 if u < 0.5 else cur * (0.3 if int(u * 6) % 2 else 1.0)
    return cur

D_TR = {'drip': 0.5, 'blood': 0.6, 'static': 0.25, 'flick': 0.2}

def render_shot(i, t, fi):
    t0, t1, p, r0, r1, o = SHOTS[i]
    if p is None: return np.zeros((H, W, 3), np.float32) + INKC
    u = clamp((t - t0) / (t1 - t0))
    e = eio(u) if not o.get('punch') else eout(min(1, u * 3))
    rect = [lerp(a, b_, e) for a, b_ in zip(r0, r1)]
    img = view(p, rect)
    if o.get('uncanny'):                # the face slowly stretches: mouth drags downward
        k = 70 * eio(u)
        dy = k * np.exp(-((_xx - W * 0.52) / 300) ** 2) * np.clip((_yy - H * 0.35) / (H * 0.4), 0, 1)
        img = cv2.remap(img, _xx, _yy - dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    out = grade(img, o.get('red', False))
    if o.get('on') is not None:         # light flickers on
        on = o['on']
        if t < on: out = out * 0
        elif t < on + 0.5: out = out * (1 if int((t - on) * 30) % 3 else 0.2)
    return out

def shot_at(t):
    for i, s in enumerate(SHOTS):
        if s[0] <= t < s[1]: return i
    return len(SHOTS) - 1

def rec_hud(rgb, t, fi):
    lt = t - EV['rec']
    # flashlight: only a wandering circle is lit
    cx = W / 2 + 180 * math.sin(lt * 1.9) + 60 * math.sin(lt * 5.3)
    cy = H * 0.45 + 160 * math.cos(lt * 1.4)
    d = np.sqrt((_xx - cx) ** 2 + (_yy - cy) ** 2)
    light = (0.12 + 0.95 * np.clip(1 - (d - 330) / 260, 0, 1))[..., None]
    rgb[:] = rgb * light * SCAN
    col = (0.95, 0.95, 0.95)
    if int(t * 2) % 2 == 0: cv2.circle(rgb, (110, 150), 20, (0.85, 0.08, 0.1), -1, cv2.LINE_AA)
    for txt, (px, py), sz in (('REC', (210, 150), 56), (f'00:18:{int((lt + 8) * 30) % 60:02d}', (840, 1810), 54)):
        put(rgb, distressed(txt, 'consolab.ttf', sz, rough=0), px, py, np.float32(col))
    for (x0, y0), (dx, dy) in (((60, 90), (1, 1)), ((W - 60, 90), (-1, 1)), ((60, H - 90), (1, -1)), ((W - 60, H - 90), (-1, -1))):
        cv2.line(rgb, (x0, y0), (x0 + 70 * dx, y0), col, 4); cv2.line(rgb, (x0, y0), (x0, y0 + 70 * dy), col, 4)
    cv2.rectangle(rgb, (880, 135), (980, 175), col, 3); cv2.rectangle(rgb, (884, 139), (884 + 30, 171), col, -1)

def frame(fi):
    t = fi / FPS
    si = shot_at(t); o = SHOTS[si][5]
    rgb = render_shot(si, t, fi)
    tr = o.get('tr')
    if tr and t < SHOTS[si][0] + D_TR[tr]:
        u = (t - SHOTS[si][0]) / D_TR[tr]
        rgb = transition(rgb, render_shot(si - 1, t, fi), tr, u, fi)
    # subliminal frames
    for ts, nf, p, r in SUBLIM:
        if ts <= t < ts + nf / FPS:
            img = grade(view(p, r)); rgb = 1 - img if nf == 1 else img * (0.7 + 0.6 * (fi % 2))
            rgb[..., 0] += 0.25; break
    if o.get('rec'): rec_hud(rgb, t, fi)
    draw_text(rgb, t, fi)
    # scares: red wash, inverted strobe, chromatic split, shake
    ox = oy = 0.0; ca = 0
    for ts, power in SCARES:
        lt = t - ts
        if 0 <= lt < power:
            k = math.exp(-lt * 5)
            ox += 40 * power * k * math.sin(t * 91); oy += 40 * power * k * math.cos(t * 67); ca += int(22 * power * k)
            rgb = rgb * (1 - 0.55 * k) + CRIM * 0.55 * k * rgb.mean(2, keepdims=True) * 2.2
            if power > 1 and int(lt * 15) % 2 == 0 and lt < 0.7: rgb = 1 - rgb
    if o.get('scare'):
        lt = t - EV['scare']; k = 1 + 0.06 * math.sin(lt * 40) * math.exp(-lt)
        ox += 10 * math.sin(t * 57); oy += 10 * math.cos(t * 43)
    if o.get('shake'): ox += o['shake'] * math.sin(t * 71); oy += o['shake'] * math.cos(t * 53)
    ox += np.random.default_rng(fi).normal(0, 1.2); oy += np.random.default_rng(fi + 1).normal(0, 1.2)   # gate weave
    rgb = cv2.warpAffine(rgb, np.float32([[1.02, 0, ox - W * 0.01], [0, 1.02, oy - H * 0.01]]), (W, H), borderMode=cv2.BORDER_REFLECT)
    if ca > 1: rgb[..., 0] = np.roll(rgb[..., 0], ca, 1); rgb[..., 2] = np.roll(rgb[..., 2], -ca, 1)
    # fluorescent flicker
    r = np.random.default_rng(fi * 3)
    fl = 1 - 0.07 * r.random()
    for d in FLICK_DROPS:
        if d <= t < d + 0.1: fl *= 0.25 if int((t - d) * 30) % 2 == 0 else 0.7
    rgb = rgb * fl
    # dust + scratches
    if r.random() < 0.5:
        for _ in range(int(r.integers(1, 6))):
            cv2.circle(rgb, (int(r.integers(0, W)), int(r.integers(0, H))), int(r.integers(1, 4)), (0.85, 0.85, 0.85), -1)
    if r.random() < 0.25:
        x = int(r.integers(0, W)); cv2.line(rgb, (x, 0), (x + int(r.integers(-20, 20)), H), (0.6, 0.6, 0.6), 1)
    rgb = rgb * VIG + GRAIN[fi % 6]
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)

# ---------------------------------------------------------------- main
def stills(times):
    d = os.path.join(HERE, 'stills'); os.makedirs(d, exist_ok=True); th = []
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
    tmp = os.path.join(HERE, '_video.mp4'); out = os.path.join(ROOT, 'ibitsu-short.mp4')
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '27', '-tune', 'grain',
                          '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmp], stdin=subprocess.PIPE)
    with Pool(max(1, os.cpu_count() - 1)) as pool:
        for i, fr in enumerate(pool.imap(frame, range(N), chunksize=4)):
            p.stdin.write(fr.tobytes())
            if i % 150 == 0: print(f'frame {i}/{N}', flush=True)
    p.stdin.close(); p.wait()
    subprocess.run([ff, '-y', '-v', 'error', '-i', tmp, '-i', os.path.join(HERE, 'music.wav'), '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-af', 'loudnorm=I=-15:TP=-1.0:LRA=14,aresample=48000', '-c:a', 'aac', '-b:a', '192k',
                    '-t', f'{DUR:.3f}', '-movflags', '+faststart', out], check=True)
    os.remove(tmp); print('wrote', out)

if __name__ == '__main__':
    if sys.argv[1] == 'stills': stills([float(x) for x in sys.argv[2].split(',')])
    else: video()
