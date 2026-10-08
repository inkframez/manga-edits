"""Three Days of Happiness - 20 s vertical Short with Japanese kinetic type (song 109.06-129.06 s, 1080x1920).

Built on the Toki Doki engine (02-tokidoki/video/render.py: cards, shapes, sprites, transitions) loaded under another
module name, plus fireflies from render_full.py. Cold grey before the drop, warm cream + amber fireflies after.
Words: 寿命 / 一年につき一万円 / 三・日・間・の → 幸福 (= 三日間の幸福) / 蛍 / 価値 / 三十円.
Usage:  python render_short_jp.py stills 110,116,126   |   python render_short_jp.py video -> ../three-days-short-jp.mp4
"""
import os, sys, math, subprocess, importlib.util
import numpy as np, cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
_spec = importlib.util.spec_from_file_location(
    'tdk_engine', os.path.join(os.path.dirname(ROOT), '02-tokidoki', 'video', 'render.py'))
E = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(E)
shot, card, shp, sprinkle, bgp = E.shot, E.card, E.shp, E.sprinkle, E.bgp
clamp, eout, ein, eio, eback, lerp, hexc = E.clamp, E.eout, E.ein, E.eio, E.eback, E.lerp, E.hexc

SONG = os.path.join(ROOT, '01-tdoh-bg-song.mp3')
OUT = os.path.join(ROOT, 'three-days-short-jp.mp4')
BEAT = 0.8355
def bar(j, k=0): return 2.12 + (4 * j + k) * BEAT
T0 = bar(32); LEN = 20.0; T1 = T0 + LEN
DROP = bar(34); GL = bar(36, 3)
W, H = 1080, 1920
FPS = E.FPS

# ---------------------------------------------------------------- engine overrides (vertical, project-01 pages, 72 bpm)
E.W, E.H = W, H
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
E.PMAP = (_xx + 0.4 * _yy) / (W + 0.4 * H)
SPC = 64.0
DGRID = np.sqrt(((_xx % SPC) - SPC / 2) ** 2 + ((_yy % SPC) - SPC / 2) ** 2).astype(np.float32)
DIAG = ((_xx + _yy) / (W + H)).astype(np.float32)
_r = np.sqrt(((_xx / W - .5) * 2) ** 2 * 0.7 + ((_yy / H - .5) * 2) ** 2 * 0.55)
VIG = (1 - 0.45 * np.clip((_r - 0.5) / 0.8, 0, 1) ** 1.6).astype(np.float32)[..., None]
del _yy, _xx, _r
E.BEATS = np.array([2.12 + i * BEAT for i in range(320)])
E._HALF = (E.BEATS[:-1] + E.BEATS[1:]) / 2
E.DUR = 9999.0
E.S.clear(); E.FLASH.clear(); E.SHAKE.clear(); E.GLITCH.clear(); E.HUDS = []
E.INKC = np.array([0.05, 0.06, 0.09], np.float32)
PAN = os.path.join(ROOT, 'panels')
E.PAGES.clear()
def page(n):
    if n not in E.PAGES:
        fn = [p for p in os.listdir(PAN) if p.split('.')[0] == n][0]
        a = np.asarray(Image.open(os.path.join(PAN, fn)).convert('L'), np.float32) / 255
        a = np.clip((a - 0.02) / 0.93, 0, 1)
        s = 3.0 if a.shape[1] < 700 else 2.0
        up = cv2.resize(a, (int(a.shape[1] * s), int(a.shape[0] * s)), interpolation=cv2.INTER_LANCZOS4)
        bl = cv2.GaussianBlur(up, (0, 0), 1.4); up = np.clip(up + 0.6 * (up - bl), 0, 1)
        E.PAGES[n] = ((up * 255 + 0.5).astype(np.uint8), s)
    return E.PAGES[n]
E.page = page
E.R.update({
    '01clerk': ('01', [240, 40, 220, 400]), '02girl': ('02', [335, 468, 276, 492]), '09a': ('09', [37, 0, 537, 259]),
    '06c': ('06', [446, 532, 400, 352]), '03e': ('03', [474, 942, 372, 369]), '08a': ('08', [56, 136, 790, 560]),
    'p10': ('10', [0, 0, 611, 960]), '11a': ('11', [37, 0, 268, 410]), '12a': ('12', [37, 0, 337, 347]),
    '12d': ('12', [311, 369, 263, 269]), '13v': ('13', [30, 0, 600, 960]), '14a': ('14', [37, 0, 537, 455]),
})

# palette
INK, COLD, COLD2, PAPER, CREAM, AMB, AMBD, EMBER = '#10131A', '#DCE2EA', '#B9C2CE', '#F6EEDF', '#EFE2C8', '#FFC46B', '#3A2208', '#FF7A4F'
AMBER = np.array([1.0, 0.70, 0.32], np.float32)
JP, JPL = E.JP, E.FD + 'YuGothL.ttc'
E.STY.update({
    'jpw': dict(font=JP, fill='#FFFFFF', sh=INK, so=0.05, stroke=INK, sw=0.03),
    'jpk': dict(font=JP, fill=INK, stroke='#FFFFFF', sw=0.06),
    'jpa': dict(font=JP, fill=AMB, stroke=AMBD, sw=0.035),
    'jpe': dict(font=JP, fill=EMBER, stroke=AMBD, sw=0.04),
    'jpl': dict(font=JPL, fill=INK),
    'jpls': dict(font=JPL, fill='#FFFFFF', sh=INK, so=0.04),
})

# ---------------------------------------------------------------- cards with warp / squash (from Toki Doki short #2)
def render_card2(rgb, c, t, sh):
    lt = t - sh['t0'] - c.get('t_in', 0)
    if lt < 0: return
    dur = max(sh['t1'] - sh['t0'] - c.get('t_in', 0), 0.1); u = clamp(lt / dur)
    p, r = E.R[c['key']]
    up, s = page(p)
    x, y, w, h = r
    z = lerp(1, c.get('kz', 1), eio(u)); fx, fy = c.get('f', (0.5, 0.5))
    w2, h2 = w / z, h / z; x, y = x + (w - w2) * fx, y + (h - h2) * fy; w, h = w2, h2
    asp = w / h
    mode = c.get('mode', 'frame'); bleed = c.get('bleed', False)
    if bleed: k0 = max(W / w, H / h); fw, fh = w * k0, h * k0
    elif 'h' in c: fh = c['h']; fw = fh * asp
    else: fw = c['w']; fh = fw / asp
    ent = c.get('ent', 'none'); e = clamp(lt / c.get('ed', 0.38))
    sc = lerp(c.get('s0', 1.0), c.get('s1', 1.035), eio(u))
    ang = c.get('rot', 0) + c.get('sway', 0) * math.sin(lt * 1.7)
    cx, cy = c.get('cx', W / 2), c.get('cy', H / 2); a = 1.0
    if ent == 'pop': sc *= lerp(0.25, 1, eback(e)); a = clamp(e * 4)
    elif ent == 'punch': sc *= lerp(1.14, 1, eout(e))
    elif ent == 'zoom': sc *= lerp(1.35, 1, eout(e)); a = clamp(e * 3)
    elif ent == 'fade': a = eout(e)
    elif ent.startswith('slide'):
        vx, vy = E.DIRS[ent[6:]]; d = c.get('dist', 1500) * (1 - eout(e)); cx -= vx * d; cy -= vy * d
    if c.get('br'): sc *= 1 + c['br'] * math.sin(lt * 2.3)
    d0, d1 = c.get('d0', (0, 0)), c.get('d1', (0, 0))
    cx += lerp(d0[0], d1[0], eio(u)); cy += lerp(d0[1], d1[1], eio(u))
    if bleed: sc = max(sc, 1.0)
    k = fw * sc / (w * s)
    pcx, pcy = (x + w / 2) * s, (y + h / 2) * s
    M = cv2.getRotationMatrix2D((pcx, pcy), ang, k); M[:, 2] += (cx - pcx, cy - pcy)
    if 'sq' in c:
        st, amp = c['sq']; dt = lt - st
        if dt >= 0:
            q_ = amp * math.exp(-dt * 7) * math.sin(dt * 26); sx, sy = 1 + q_, 1 - q_
            Sx = np.float64([[sx, 0, cx - sx * cx], [0, sy, cy - sy * cy], [0, 0, 1]])
            M = (Sx @ np.vstack([M, [0, 0, 1]]))[:2]
    cs = np.float32([[x * s, y * s], [(x + w) * s, y * s], [(x + w) * s, (y + h) * s], [x * s, (y + h) * s]])
    q = cs @ M[:, :2].T + M[:, 2]
    m = 0 if (bleed or mode != 'frame') else c.get('m', 12) * sc
    if m:
        cen = q.mean(0); dirs = q - cen; dirs /= np.linalg.norm(dirs, axis=1, keepdims=True); qm = q + dirs * m * 1.414
    else: qm = q
    so = np.float32(c.get('so', (16, 16))) * sc if (mode == 'frame' and not bleed) else np.float32([0, 0])
    bx, by, bx1, by1 = E.bbox_of(np.vstack([qm, qm + so]))
    bw, bh = bx1 - bx, by1 - by
    if bw <= 2 or bh <= 2: return
    M2 = M.copy(); M2[:, 2] -= (bx, by)
    cont = cv2.warpAffine(up, M2, (bw, bh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    if 'warp' in c:
        amp, wl, spd, y0f = c['warp']
        yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
        ramp = np.clip((yy / bh - y0f) / max(1 - y0f, 1e-3), 0, 1) ** 1.3
        if c.get('wx'): ramp = ramp * np.clip((xx / bw - c['wx']) / max(1 - c['wx'], 1e-3), 0, 1)
        dx = amp * sc * ramp * np.sin(yy / wl + lt * spd) + 0.5 * amp * sc * ramp * np.sin(xx / (wl * 1.7) + lt * spd * 1.3)
        dy = 0.35 * amp * sc * ramp * np.sin(xx / (wl * 1.3) + lt * spd * 0.8)
        cont = cv2.remap(cont, xx + dx, yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    val = cont.astype(np.float32) / 255
    if val.ndim == 2: val = E.INKC + (1 - E.INKC) * val[..., None]
    reg = rgb[by:by1, bx:bx1]
    mc = E.poly_mask(q, bx, by, bw, bh) * a
    A = mc[..., None]
    if mode == 'frame' and not bleed:
        ms = E.poly_mask(qm + so, bx, by, bw, bh) * a
        reg[:] = reg * (1 - ms[..., None]) + hexc(c.get('sc', INK)) * ms[..., None]
        mb = E.poly_mask(qm, bx, by, bw, bh) * a
        reg[:] = reg * (1 - mb[..., None]) + hexc(c.get('paper', PAPER)) * mb[..., None]
        reg[:] = reg * (1 - A) + val * hexc(c.get('paper', PAPER)) * A
    elif mode == 'mul':
        reg[:] = reg * (1 - A + A * val)
    else:
        reg[:] = reg * (1 - A) + val * A
E.render_card = render_card2

# ---------------------------------------------------------------- text: glow + melt
def draw_text2(rgb, it, t):
    if t < it['t']: return
    if it.get('end') is not None and t > it['end'] + 0.16: return
    if it.get('glow'):
        spr = E.sprite(it['s'], it['st'], it['size'], it.get('fill'), it.get('sh'), it.get('stroke'), it.get('box'))
        e = clamp((t - it['t']) / 0.4); fl = 1 + 0.25 * math.sin((t - it['t']) * 3.1)
        pad = 50; g = cv2.GaussianBlur(np.pad(spr[..., 3], pad), (0, 0), 22)
        hh, ww = g.shape; x0, y0 = int(it['x'] - ww / 2), int(it['y'] - hh / 2)
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + ww), min(H, y0 + hh)
        if xb > xa and yb > ya:
            gg = g[ya - y0:yb - y0, xa - x0:xb - x0] * it['glow'] * e * fl
            rgb[ya:yb, xa:xb] += gg[..., None] * AMBER
    if 'melt' in it and t >= it['melt']:
        k = clamp((t - it['melt']) / it.get('md', 0.8))
        if k >= 1: return
        spr = E.sprite(it['s'], it['st'], it['size'], it.get('fill'), it.get('sh'), it.get('stroke'), it.get('box'))
        sg = 1 + 12 * k; pad = int(sg * 3)
        spr = cv2.GaussianBlur(np.pad(spr, ((pad, pad), (pad, pad), (0, 0))), (0, 0), sg)
        E.blit(rgb, spr, it['x'], it['y'] - 140 * eout(k), 1 + 0.12 * k, 0, 1 - k)
        return
    E.draw_text(rgb, it, t)

def jp(t, s, x, y, size, st='jpw', step=BEAT / 2, vertical=False, ent='stamp', **kw):
    out, n = [], len(s)
    for i, ch in enumerate(s):
        if vertical: cx, cy = x, y + i * size * 1.06
        else: cx, cy = x + (i - (n - 1) / 2) * size, y
        out.append(dict(s=ch, st=st, size=size, x=cx, y=cy, t=t + i * step, ent=ent, **kw))
    return out

# ---------------------------------------------------------------- fireflies (from render_full.py, vertical)
_rng = np.random.default_rng(7); NP = 170
FX, FY = _rng.random(NP), _rng.random(NP); DEP = _rng.random(NP) ** 1.8
VX = (_rng.random(NP) - .5) * 0.018; VY = -(0.004 + _rng.random(NP) * 0.016)
PH = _rng.random(NP) * 6.283; SPd = 0.7 + _rng.random(NP) * 2.4; WOB = _rng.random(NP) * 0.014
RANK = _rng.permutation(NP)
SIGS = np.geomspace(0.7, 16, 18)
def _sprite(sg):
    r = int(math.ceil(sg * 3)); yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return np.exp(-(xx ** 2 + yy ** 2) / (2 * sg * sg)).astype(np.float32)
SPRF = [_sprite(sg) for sg in SIGS]
def density(t):
    return E.keys(t, [(T0, 0.0), (bar(33), 0.0), (DROP - 0.6, 0.06), (DROP - 0.01, 0.08), (DROP, 0.0), (DROP + 0.05, 1.0),
                      (GL - 0.05, 0.9), (GL, 0.25), (bar(37) - 0.01, 0.35), (bar(37), 1.0), (T1 + 1, 1.0)])
def fireflies(t):
    dn = density(t)
    if dn <= 0.001: return None
    hw, hh = W // 2, H // 2
    buf = np.zeros((hh, hw), np.float32)
    x = (FX + VX * t + WOB * np.sin(t * 0.9 + PH)) % 1.1 - 0.05
    y = (FY + VY * t + WOB * np.cos(t * 0.7 + PH)) % 1.1 - 0.05
    for b in (DROP, bar(37)):
        if b <= t < b + 2.0:
            k = lerp(0.06, 1.0, eout((t - b) / 2.0)); x = 0.5 + (x - 0.5) * k; y = 0.55 + (y - 0.55) * k
    vis = np.clip((dn * NP - RANK) / 10, 0, 1)
    tw = 0.45 + 0.55 * (0.5 + 0.5 * np.sin(t * SPd + PH))
    for i in range(NP):
        if vis[i] <= 0: continue
        sp = SPRF[int(DEP[i] * (len(SIGS) - 1))]; r = sp.shape[0] // 2
        amp = vis[i] * tw[i] * lerp(1.0, 0.16, DEP[i])
        cx, cy = int(x[i] * hw), int(y[i] * hh)
        x0, y0, x1, y1 = cx - r, cy - r, cx + r + 1, cy + r + 1
        sx0, sy0 = max(0, -x0), max(0, -y0)
        xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x1, hw), min(y1, hh)
        if xb <= xa or yb <= ya: continue
        buf[ya:yb, xa:xb] += amp * sp[sy0:sy0 + (yb - ya), sx0:sx0 + (xb - xa)]
    bloom = cv2.GaussianBlur(buf, (0, 0), 9)
    return cv2.resize(buf + 0.9 * bloom, (W, H), interpolation=cv2.INTER_LINEAR)

# ================================================================ timeline (song time)
D_TR = {'whip': 0.32, 'zoom': 0.42, 'slices': 0.42, 'dots': 0.5, 'melt': 0.55}
# 1  the sale - cold grey
shot(T0, bar(32, 2), bgp('plain', COLD),
     cards=[card('01clerk', mode='mul', bleed=True, kz=1.12, f=(0.5, 0.4), br=0.006)],
     shapes=[shp('rect', W / 2, 440, (460, 300), '#F2F4F7', T0, a=0.9, ent='grow', ed=0.25, layer='front')],
     texts=jp(T0 + 0.05, '寿命', W / 2, 340, 260, st='jpk', step=0.2) +
           jp(bar(32, 1), '一年につき一万円', W / 2, 590, 62, st='jpk', step=0.06, ent='pop'))
E.SHAKE.append((bar(32, 2), 8, 4))
shot(bar(32, 2), bar(33), bgp('plain', COLD2),
     cards=[card('02girl', mode='mul', bleed=True, kz=1.12, f=(0.5, 0.35), d0=(0, 30), d1=(0, -30))],
     texts=[dict(s='¥ 300,000', st='mono', size=92, x=W / 2, y=1480, t=bar(32, 2) + 0.1, ent='type', cps=0.04)],
     tr=('whip', 'u'))
# 2  build - memory flicker, 三・日・間・の one per beat
for i, k in enumerate(['09a', '06c', '03e', '08a']):
    t0, t1 = bar(33, i), bar(33, i + 1)
    E.FLASH.append((t0, 0.35, 0.08, '#FFFFFF'))
    shot(t0, t1, bgp('plain', COLD if i % 2 else COLD2),
         cards=[card(k, mode='frame', w=1000, cy=1150, rot=(-3, 3, -2, 2)[i], ent='punch', sc=INK, kz=1.08)],
         texts=[dict(s=c_, st='jpk', size=210, x=W / 2 + (j - i * 0.5) * 0, y=300 + 0 * j, t=bar(33, j), ent='stamp')
                for j, c_ in enumerate('三日間の'[:i + 1]) if j == i] +
               [dict(s=c_, st='jpk', size=110, x=W / 2 + (j - 1.5) * 120, y=520, t=t0, ent='none')
                for j, c_ in enumerate('三日間の'[:i])])
# 3  DROP - the firefly field, warm, 幸福
E.FLASH.append((DROP, 1.0, 0.35, '#FFF6E6')); E.SHAKE.append((DROP, 18, 5))
shot(DROP, bar(35), bgp('plain', CREAM),
     cards=[card('p10', mode='mul', bleed=True, kz=1.22, f=(0.5, 0.62), sq=(0, 0.04))],
     texts=jp(DROP + 0.05, '三日間の', W / 2, 250, 96, st='jpls', step=0.06, ent='fade') +
           [dict(s='幸', st='jpa', size=290, x=W / 2 - 150, y=470, t=DROP + 0.15, ent='stamp', glow=0.55),
            dict(s='福', st='jpa', size=290, x=W / 2 + 150, y=470, t=DROP + 0.32, ent='stamp', glow=0.55)],
     tr=('zoom',), pulse=0.02)
# 4  Miyagi with a firefly - 蛍
shot(bar(35), bar(36), bgp('plain', CREAM),
     cards=[card('11a', mode='mul', bleed=True, kz=1.25, f=(0.45, 0.55), br=0.004)],
     texts=[dict(s='蛍', st='jpa', size=380, x=W / 2, y=420, t=bar(35) + 0.1, ent='stamp', glow=0.6, melt=bar(35, 3), md=0.7)],
     tr=('melt',), pulse=0.015)
# 5  "how much am I worth?" - 価値, then the glitch: 三十円
shot(bar(36), bar(36, 2), bgp('plain', PAPER),
     cards=[card('12a', mode='frame', w=1000, cy=1150, rot=2, ent='none', kz=1.1, sc=AMBD, paper=PAPER)],
     texts=jp(bar(36) + 0.05, '価値', W / 2, 360, 280, st='jpk', step=0.25) +
           [dict(s='は？', st='jpl', size=120, x=W / 2 + 230, y=580, t=bar(36, 1), ent='fade')],
     tr=('slices',))
E.GLITCH.append((GL, GL + 0.45)); E.FLASH.append((GL, 0.8, 0.15, '#FF9A6B')); E.SHAKE.append((GL, 22, 6))
shot(bar(36, 2), bar(37), bgp('plain', CREAM),
     cards=[card('12d', mode='mul', bleed=True, kz=1.18, f=(0.5, 0.45), ent='none')],
     texts=[dict(s='三十円', st='jpe', size=230, x=W / 2, y=420, t=GL, ent='stamp', glow=0.4)] +
           [dict(s='¥ 30', st='mono', size=110, x=W / 2, y=1480, t=GL + 0.1, ent='pop')])
# 6  the hug - hair in the wind, then the firefly hug and the title
E.FLASH.append((bar(37), 1.0, 0.3, '#FFF6E6')); E.SHAKE.append((bar(37), 26, 6))
shot(bar(37), bar(37, 2), bgp('plain', CREAM),
     cards=[card('13v', mode='mul', bleed=True, kz=1.12, f=(0.45, 0.35), sq=(0, 0.05), warp=(14, 55, 2.4, 0.05), wx=0.45)],
     pulse=0.025)
shot(bar(37, 2), T1 + 0.1, bgp('plain', '#2A2018'),
     cards=[card('14a', mode='frame', w=1000, cy=1340, rot=-1.5, kz=1.12, f=(0.4, 0.4), sc=AMB, paper=PAPER, br=0.005)],
     texts=jp(bar(37, 2) + 0.05, '三日間の幸福', W / 2, 250, 96, st='jpa', step=0.12, vertical=True, ent='fade', glow=0.35),
     tr=('dots', AMB))

# ---------------------------------------------------------------- frame
def render_shot2(sh, t):
    rgb = E.background(sh, t)
    for s in sh['shapes']:
        if s.get('layer', 'back') == 'back': E.draw_shape(rgb, s, t)
    for c in sh['cards']: render_card2(rgb, c, t, sh)
    for s in sh['shapes']:
        if s.get('layer', 'back') == 'front': E.draw_shape(rgb, s, t)
    ff = fireflies(t)
    if ff is not None:
        rgb += ff[..., None] * AMBER
        rgb += 0.35 * np.clip(ff - 0.6, 0, None)[..., None]
    for it in sh['texts']: draw_text2(rgb, it, t)
    return rgb

def move(img, dx, dy):
    return cv2.warpAffine(img, np.float32([[1, 0, dx], [0, 1, dy]]), (W, H), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_REPLICATE)

def transition(cur, prev, kind, u, arg=None):
    if kind == 'whip':
        e = eio(u); sgn = -1 if arg == 'u' else 1; off = e * H
        a = move(prev, 0, sgn * off); b = move(cur, 0, sgn * (off - H))
        cut = H - off if sgn < 0 else off
        out = np.where(np.arange(H)[:, None, None] < cut, a if sgn < 0 else b, b if sgn < 0 else a)
        kb = int(1 + 110 * math.sin(math.pi * u))
        return cv2.blur(out, (1, kb)) if kb > 2 else out
    if kind == 'zoom':
        a = cv2.warpAffine(prev, cv2.getRotationMatrix2D((W / 2, H / 2), 0, 1 + 2.2 * ein(u)), (W, H), borderMode=cv2.BORDER_REFLECT)
        a = cv2.GaussianBlur(a, (0, 0), 1 + 16 * u)
        b = cv2.warpAffine(cur, cv2.getRotationMatrix2D((W / 2, H / 2), 0, lerp(1.3, 1.0, eout(u))), (W, H), borderMode=cv2.BORDER_REFLECT)
        k = eout(u); return a * (1 - k) + b * k
    if kind == 'slices':
        n = 10; out = prev.copy(); bh = H // n + 1
        for i in range(n):
            p = eout(clamp((u - i * 0.035) / 0.6)); sh_ = int(round((1 - p) * W * (1 if i % 2 else -1)))
            y0, y1 = i * bh, min(H, (i + 1) * bh); band = cur[y0:y1]
            if sh_ >= 0: out[y0:y1, sh_:] = band[:, :W - sh_]
            else: out[y0:y1, :W + sh_] = band[:, -sh_:]
        return out
    if kind == 'dots':
        r = np.clip((u * 1.7 - DIAG * 0.7), 0, 1) * SPC * 0.78
        m = np.clip((r - DGRID) / 1.5 + 0.5, 0, 1)[..., None]
        if arg:
            rim = np.clip((r + 6 - DGRID) / 1.5 + 0.5, 0, 1)[..., None] - m
            prev = prev * (1 - rim) + hexc(arg) * rim
        return prev * (1 - m) + cur * m
    if kind == 'melt':
        k = eout(u); a = move(cv2.GaussianBlur(prev, (0, 0), 1 + 14 * u), 0, -80 * u)
        return a * (1 - k) + cur * k
    return cur

def frame(fi):
    t = fi / FPS
    si = E.shot_at(t); sh = E.S[si]
    rgb = render_shot2(sh, t)
    if sh['tr'] and si > 0:
        kind = sh['tr'][0]; d = D_TR.get(kind, 0)
        if t < sh['t0'] + d:
            rgb = transition(rgb, render_shot2(E.S[si - 1], t), kind, (t - sh['t0']) / d, sh['tr'][1] if len(sh['tr']) > 1 else None)
    rgb = np.clip(rgb, 0, 1.2)
    zoom = 1 + sh['pulse'] * math.exp(-E.since_beat(t) * 9)
    ox = oy = 0.0
    for ts, amp, dc in E.SHAKE:
        if ts <= t < ts + 2.0:
            k = amp * math.exp(-(t - ts) * dc); ox += k * math.sin(t * 71); oy += k * math.cos(t * 53)
    if zoom > 1.0005 or abs(ox) + abs(oy) > 0.3:
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, zoom); M[:, 2] += (ox, oy)
        rgb = cv2.warpAffine(rgb, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    for g0, g1 in E.GLITCH:
        if g0 <= t < g1:
            r_ = np.random.default_rng(fi); dd = int(16 * (1 - (t - g0) / (g1 - g0))) + 2
            rgb[..., 0] = np.roll(rgb[..., 0], dd, 1); rgb[..., 2] = np.roll(rgb[..., 2], -dd, 1)
            for _ in range(7):
                y0 = int(r_.integers(0, H - 80)); hh = int(r_.integers(10, 80))
                rgb[y0:y0 + hh] = np.roll(rgb[y0:y0 + hh], int(r_.integers(-80, 80)), 1)
    for tf, pk, dc, col in E.FLASH:
        if tf <= t < tf + 2:
            f = pk * math.exp(-(t - tf) / dc)
            if f > 0.004: rgb = rgb + (hexc(col) - rgb) * min(f, 1)
    rgb = rgb * VIG
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)

# ---------------------------------------------------------------- render
F0 = int(round(T0 * FPS)); NF = int(round(LEN * FPS))

def stills(times):
    d = os.path.join(HERE, 'stills_short_jp'); os.makedirs(d, exist_ok=True)
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
    tmpv = os.path.join(HERE, '_video_short_jp.mp4'); tmpa = os.path.join(HERE, '_audio_short_jp.m4a')
    subprocess.run([ff, '-y', '-v', 'error', '-ss', f'{T0:.3f}', '-t', f'{LEN:.3f}', '-i', SONG,
                    '-af', f'afade=t=in:d=0.08,afade=t=out:st={LEN - 0.7:.2f}:d=0.7,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000',
                    '-c:a', 'aac', '-b:a', '192k', tmpa], check=True)
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                          '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmpv], stdin=subprocess.PIPE)
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
