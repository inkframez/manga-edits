"""Toki Doki - Short #2: the hug drop (song 154.81-174.81 s), 1080x1920, 20 s.

Adds to the render.py engine:
  * 2.5D character layers - the couple (p16) and his phone (p13) are cut out of the page (bg inpainted) and dolly
    toward camera faster than their background; fg can be a white "sticker" with an outline.
  * character motion - hair/cloth sway (displacement warp), breathing, squash & stretch landings.
  * two-shot transitions - whip pan with motion blur, zoom-through, slices, halftone-dot wipe, blur melt.
Usage:  python render_short2.py stills 155,158,160   |   python render_short2.py video -> ../tokidoki-short-hug.mp4
"""
import os, sys, math, subprocess
import numpy as np, cv2
import render as E
from render import (B, shot, card, shp, sprinkle, hearts, bgp, clamp, eout, ein, eio, eback, lerp, hexc,
                    WH, SKY, SKYL, SKY2, BLU, PNK, PNKL, ROS, RED, CRM, NAV, GRY, SLT)

T0 = B(65); LEN = 20.0; T1 = T0 + LEN
W, H = 1080, 1920
E.W, E.H = W, H
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
E.PMAP = (_xx + 0.4 * _yy) / (W + 0.4 * H)
SPC = 64.0                                                    # halftone-dot wipe grid
_gx, _gy = (_xx % SPC) - SPC / 2, (_yy % SPC) - SPC / 2
DGRID = np.sqrt(_gx ** 2 + _gy ** 2).astype(np.float32)
DIAG = ((_xx + _yy) / (W + H)).astype(np.float32)
del _yy, _xx, _gx, _gy
E.DUR = 9999.0
E.S.clear(); E.FLASH.clear(); E.SHAKE.clear(); E.GLITCH.clear()
E.HUDS = []
OUT = os.path.join(E.ROOT, 'tokidoki-short-hug.mp4')
JP = E.JP
E.STY.update({
    'jpw': dict(font=JP, fill=WH, sh=NAV, so=0.06, stroke=NAV, sw=0.03),
    'jpr': dict(font=JP, fill=RED, sh=NAV, so=0.05, stroke=WH, sw=0.07),
    'jpp': dict(font=JP, fill=ROS, sh=NAV, so=0.05, stroke=WH, sw=0.07),
})

# ---------------------------------------------------------------- layered (cut-out) pages
LAYERS = {
    'hug': ('16', [(492, 522), (512, 516), (536, 540), (540, 575), (548, 620), (552, 700), (556, 780), (562, 850),
                   (560, 868), (455, 868), (452, 840), (462, 760), (468, 720), (458, 700), (452, 690), (424, 690),
                   (420, 650), (432, 620), (462, 600), (490, 580), (488, 545)]),
    'phone': ('13', [(47, 560), (150, 520), (197, 440), (560, 400), (600, 340), (700, 330), (959, 350), (959, 640),
                     (790, 700), (760, 800), (700, 930), (47, 930)]),
}
def make_layers(key):
    n, poly = LAYERS[key]
    up, s = E.page(n); g = up if up.ndim == 2 else up[..., 0]
    m = np.zeros(g.shape, np.uint8)
    cv2.fillPoly(m, [np.int32(np.float32(poly) * s * 16)], 255, cv2.LINE_AA, 4)
    m = cv2.GaussianBlur(m, (0, 0), 1.2)
    hs = (g.shape[1] // 2, g.shape[0] // 2)
    gm, mm = cv2.resize(g, hs, interpolation=cv2.INTER_AREA), cv2.resize(m, hs, interpolation=cv2.INTER_AREA)
    bg = cv2.inpaint(gm, cv2.dilate((mm > 8).astype(np.uint8) * 255, np.ones((9, 9), np.uint8)), 6, cv2.INPAINT_TELEA)
    bg = cv2.resize(bg, (g.shape[1], g.shape[0]), interpolation=cv2.INTER_CUBIC)
    a = m.astype(np.float32)[..., None] / 255
    bgf = (g[..., None] * (1 - a) + bg[..., None] * a + 0.5).astype(np.uint8)
    E.PAGES[n + key + 'bg'] = (bgf, s)
    E.PAGES[n + key + 'fg'] = (np.dstack([g, m]), s)
for _k in LAYERS: make_layers(_k)
E.R.update({
    'hugBG': ('16hugbg', [330, 380, 330, 560]), 'hugFG': ('16hugfg', [330, 380, 330, 560]),
    'phoneBG': ('13phonebg', [200, 0, 560, 930]), 'phoneFG': ('13phonefg', [200, 0, 560, 930]),
    '14cryV': ('14', [230, 880, 560, 520]), '17r2': ('17', [655, 470, 304, 230]), '16coupleV': ('16', [380, 470, 260, 420]),
    '15skyV': ('15', [700, 990, 259, 410]), '14hatoV': ('14', [370, 330, 340, 540]),
})

# ---------------------------------------------------------------- card renderer with layers / warp / squash
def render_card2(rgb, c, t, sh):
    lt = t - sh['t0'] - c.get('t_in', 0)
    if lt < 0: return
    dur = max(sh['t1'] - sh['t0'] - c.get('t_in', 0), 0.1); u = clamp(lt / dur)
    p, r = E.R[c['key']]
    up, s = E.page(p)
    x, y, w, h = r
    z = lerp(1, c.get('kz', 1), eio(u)); fx, fy = c.get('f', (0.5, 0.5))
    w2, h2 = w / z, h / z; x, y = x + (w - w2) * fx, y + (h - h2) * fy; w, h = w2, h2
    asp = w / h
    mode = c.get('mode', 'frame'); bleed = c.get('bleed', False)
    if bleed: k0 = max(W / w, H / h); fw, fh = w * k0, h * k0
    elif 'h' in c: fh = c['h']; fw = fh * asp
    else: fw = c['w']; fh = fw / asp
    ent = c.get('ent', 'punch' if bleed else 'pop'); e = clamp(lt / c.get('ed', 0.38))
    sc = lerp(c.get('s0', 1.0), c.get('s1', 1.035), eio(u))
    ang = c.get('rot', 0) + c.get('spin', 0) * lt + c.get('sway', 0) * math.sin(lt * 1.7)
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
    if 'shake' in c:
        st, amp = c['shake']
        if lt >= st:
            kk = math.exp(-(lt - st) * 6) * amp; cx += kk * math.sin(lt * 63); cy += kk * math.cos(lt * 49)
    if bleed: sc = max(sc, 1.0)
    k = fw * sc / (w * s)
    pcx, pcy = (x + w / 2) * s, (y + h / 2) * s
    M = cv2.getRotationMatrix2D((pcx, pcy), ang, k); M[:, 2] += (cx - pcx, cy - pcy)
    M3 = np.vstack([M, [0, 0, 1]])
    # extra layer dolly (about fc, page coords) and squash & stretch (about card centre)
    if 'fs' in c or 'sq' in c:
        sx = sy = 1.0
        if 'fs' in c: f0, f1, fe = c['fs']; sx = sy = lerp(f0, f1, fe(u))
        ox, oy = (M3 @ [c['fc'][0] * s, c['fc'][1] * s, 1])[:2] if 'fc' in c else (cx, cy)
        if 'sq' in c:
            st, amp = c['sq']; dt = lt - st
            if dt >= 0:
                q = amp * math.exp(-dt * 7) * math.sin(dt * 26); sx *= 1 + q; sy *= 1 - q
        Sx = np.float64([[sx, 0, ox - sx * ox], [0, sy, oy - sy * oy], [0, 0, 1]])
        M3 = Sx @ M3
    M = M3[:2]
    cs = np.float32([[x * s, y * s], [(x + w) * s, y * s], [(x + w) * s, (y + h) * s], [x * s, (y + h) * s]])
    q = cs @ M[:, :2].T + M[:, 2]
    m = 0 if (bleed or mode != 'frame') else c.get('m', 12) * sc
    if m:
        cen = q.mean(0); dirs = q - cen; dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
        qm = q + dirs * m * 1.414
    else: qm = q
    so = np.float32(c.get('so', (16, 16))) * sc if (mode == 'frame' and not bleed) else np.float32([0, 0])
    bx, by, bx1, by1 = E.bbox_of(np.vstack([qm, qm + so]))
    bw, bh = bx1 - bx, by1 - by
    if bw <= 2 or bh <= 2: return
    M2 = M.copy(); M2[:, 2] -= (bx, by)
    cont = cv2.warpAffine(up, M2, (bw, bh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    if cont.ndim == 2: cont = cont[..., None]
    if 'warp' in c:      # hair / cloth sway, stronger towards the bottom of the card
        amp, wl, spd, y0f = c['warp']
        yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
        ramp = np.clip((yy / bh - y0f) / max(1 - y0f, 1e-3), 0, 1) ** 1.3
        dx = amp * sc * ramp * np.sin(yy / wl + lt * spd) + 0.5 * amp * sc * ramp * np.sin(xx / (wl * 1.7) + lt * spd * 1.3)
        cont = cv2.remap(cont, xx + dx, yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        if cont.ndim == 2: cont = cont[..., None]
    cont = cont.astype(np.float32) / 255
    alpha = cont[..., -1:] if cont.shape[2] in (2, 4) else None
    val = cont[..., :-1] if alpha is not None else cont
    if val.shape[2] == 1: val = E.INKC + (1 - E.INKC) * val
    reg = rgb[by:by1, bx:bx1]
    mc = E.poly_mask(q, bx, by, bw, bh) * a
    A = mc[..., None] * (alpha if alpha is not None else 1.0)
    if alpha is not None:                                   # cut-out layer: sticker outline + opaque paper
        if c.get('stroke'):
            sk = int(c['stroke'])
            ring = cv2.dilate(A[..., 0], cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * sk + 1, 2 * sk + 1)))
            ring = cv2.GaussianBlur(ring, (0, 0), 1.0)[..., None]
            reg[:] = reg * (1 - ring) + hexc(c.get('sc', WH)) * ring
        paper = hexc(c.get('paper', WH))
        reg[:] = reg * (1 - A) + paper * val * A
        return
    if mode == 'frame' and not bleed:
        ms = E.poly_mask(qm + so, bx, by, bw, bh) * a
        reg[:] = reg * (1 - ms[..., None]) + hexc(c.get('sc', NAV)) * ms[..., None]
        mb = E.poly_mask(qm, bx, by, bw, bh) * a
        reg[:] = reg * (1 - mb[..., None]) + mb[..., None]
        reg[:] = reg * (1 - A) + val * A
        mo = E.poly_mask(qm, bx, by, bw, bh, ring=4) * a
        reg[:] = reg * (1 - mo[..., None]) + hexc(NAV) * mo[..., None]
    elif mode == 'mul':
        reg[:] = reg * (1 - A + A * val)
    else:
        reg[:] = reg * (1 - A) + val * A
E.render_card = render_card2

# text: add a blur "melt" exit
_draw_text = E.draw_text
def draw_text2(rgb, it, t):
    if 'melt' in it and t >= it['melt']:
        k = clamp((t - it['melt']) / it.get('md', 0.9))
        if k >= 1: return
        spr = E.sprite(it['s'], it['st'], it['size'], it.get('fill'), it.get('sh'), it.get('stroke'), it.get('box'))
        sg = 1 + 14 * k
        pad = int(sg * 3)
        spr = cv2.GaussianBlur(np.pad(spr, ((pad, pad), (pad, pad), (0, 0))), (0, 0), sg)
        E.blit(rgb, spr, it['x'], it['y'] - 160 * eout(k), 1 + 0.15 * k, 0, 1 - k)
        return
    _draw_text(rgb, it, t)
E.draw_text = draw_text2

def jp(t, s, x, y, size, st='jpw', step=0.12, vertical=False, ent='stamp', styles=None, **kw):
    out, n = [], len(s)
    for i, ch in enumerate(s):
        if vertical: cx, cy = x, y + i * size * 1.04
        else: cx, cy = x + (i - (n - 1) / 2) * size, y
        out.append(dict(s=ch, st=(styles[i] if styles else st), size=size, x=cx, y=cy, t=t + i * step, ent=ent, **kw))
    return out

# ================================================================ timeline (song time)
D_TR = {'whip': 0.34, 'zoom': 0.42, 'slices': 0.45, 'dots': 0.5, 'melt': 0.6}
# 1  "君がくれた 夏は消えない" - her crying face, hair moving
shot(T0, B(66), bgp('dots', WH, SKYL, P=70, r=8, v=(0, -1)),
     cards=[card('14cryV', mode='frame', w=1000, cy=1100, rot=-2, ent='none', kz=1.15, f=(0.5, 0.4), sc=SKY2,
                 warp=(9, 60, 2.2, 0.25), br=0.006)],
     shapes=[shp('circle', 120 + 160 * i, 300 + 330 * (i % 3) + 80 * (i % 2), 26 + 10 * (i % 3), SKY, T0 + 0.12 * i,
                 a=0.6, bob=(16, 0.25, i), ent='grow', layer='front') for i in range(7)],
     texts=[dict(s='夏', st='jpw', size=330, x=W / 2, y=330, t=T0 + 0.25, ent='stamp', sh=SKY2, bp=0.04)])
# 2  build: his phone - layered dolly, ドキ riser
E.SHAKE.append((B(66, 2), 6, 1.5))
shot(B(66), B(67), bgp('grid', GRY, '#C9CFD9', P=110, v=(0, 2)),
     cards=[card('phoneBG', mode='mul', bleed=True, ent='none', kz=1.04),
            card('phoneFG', mode='mul', bleed=True, ent='none', kz=1.04, fs=(1.0, 1.38, ein), fc=(470, 590),
                 paper=WH, stroke=6, sc=RED)],
     ecg=[dict(t=B(66), y=300, amp=110, mode='fast', c=RED, gc=PNK, th=7, don=0.35, glow=0.5)],
     texts=[dict(s='ドキ', st='jpr', size=int(110 + 22 * i), x=(250 if i % 2 == 0 else 830), y=560 + 120 * i,
                 t=B(66) + 0.293 * i, ent='stamp', rot=(-8 if i % 2 == 0 else 8)) for i in range(8)],
     tr=('slices',))
# 3  DROP - the hug, couple cut-out dollies forward, ひとつ ひとつ in the hearts
E.FLASH.append((B(67), 1.0, 0.32, WH)); E.SHAKE.append((B(67), 26, 6))
shot(B(67), B(68), bgp('hearts', PNK, PNKL, P=120, r=20, v=(0, -3)),
     cards=[card('hugBG', mode='mul', bleed=True, ent='none', kz=1.06),
            card('hugFG', mode='mul', bleed=True, ent='none', kz=1.06, fs=(1.0, 1.16, eout), fc=(490, 700),
                 paper=WH, stroke=9, sc=RED, sq=(0.0, 0.07), warp=(5, 40, 3.0, 0.15))],
     shapes=[shp('heart', 250, 430, 205, WH, B(67), ol=6, oc=RED, layer='front', bp=0.07, ent='spin'),
             shp('heart', 830, 430, 205, WH, B(67, 2), ol=6, oc=RED, layer='front', bp=0.07, ent='spin')] +
            hearts(B(67), 18, 11, area=(40, 700, 1040, 1850), size=(18, 46), step=0.08),
     texts=[dict(s='ひとつ', st='jpr', size=105, x=250, y=440, t=B(67) + 0.08, ent='stamp'),
            dict(s='ひとつ', st='jpr', size=105, x=830, y=440, t=B(67, 2) + 0.08, ent='stamp')],
     tr=('zoom',), pulse=0.035)
# 4  "刻んだ想い" - closer on the couple, hair in the wind
shot(B(68), B(69), bgp('dots', RED, '#EE6170', P=70, r=10, v=(0, -2)),
     cards=[card('16coupleV', mode='frame', h=1300, cx=600, cy=1080, rot=3, ent='none', kz=1.15, f=(0.5, 0.35),
                 sc=NAV, warp=(10, 45, 2.6, 0.2), br=0.008, sway=1.2)],
     texts=jp(B(68), '想い', 150, 480, 230, st='jpw', step=0.29, vertical=True, sh=NAV),
     shapes=hearts(B(68), 12, 12, cols=(WH, PNK), area=(300, 250, 1040, 1800), size=(16, 40)),
     tr=('whip', 'u'), pulse=0.03)
# 5  "空に溶けても" - sky, 空 melts upward
shot(B(69), B(70), bgp('plain', SKY),
     cards=[card('15skyV', mode='mul', bleed=True, ent='none', kz=1.12, d0=(0, 40), d1=(0, -40))],
     shapes=sprinkle(B(69), 14, 13, (WH,), kinds=('plus', 'circle'), size=(8, 22), step=0.08),
     texts=[dict(s='空', st='jpw', size=460, x=W / 2, y=760, t=B(69) + 0.05, ent='stamp', sh=SKY2, melt=B(69, 3), md=0.9)],
     tr=('dots', WH), pulse=0.015)
# 6  his smile
shot(B(70), B(71), bgp('stars', SKYL, WH, P=110, r=14, v=(1, -1)),
     cards=[card('14hatoV', mode='frame', h=1350, cy=1040, rot=-2, ent='none', kz=1.1, f=(0.5, 0.3), sc=SKY2,
                 br=0.007, sway=0.8, warp=(4, 50, 1.6, 0.0))],
     shapes=sprinkle(B(70), 10, 14, (SKY2, CRM, WH), kinds=('plus', 'star')),
     tr=('slices',))
# 7  dip: "such a beautiful voice" - 声 with ripples on each beat
_rings = [shp('ring', W / 2, 360, 150, WH, B(71, i), ring=6, ent='grow', ed=0.9, end=B(71, i) + 0.75, a=0.8, layer='front')
          for i in range(4)]
shot(B(71), B(72), bgp('plain', '#E9EEF5'),
     cards=[card('17r2', mode='frame', w=1000, cy=1150, rot=2, ent='none', kz=1.1, sc=SLT, br=0.006)],
     shapes=_rings, texts=[dict(s='声', st='jpw', size=230, x=W / 2, y=360, t=B(71) + 0.1, ent='fade', ed=0.5, sh=SLT)],
     tr=('melt',))
# 8  him on the rooftop - the heartbeat weakens
shot(B(72), B(73), bgp('plain', '#DCE2EA'),
     cards=[card('17lie', mode='frame', w=1000, cy=1100, rot=-1, ent='none', kz=1.12, f=(0.45, 0.55), sc=SLT)],
     ecg=[dict(t=B(72), y=520, amp=120, mode='calm', c=RED, gc=PNK, th=6, don=0.6, gain=0.55)],
     tr=('whip', 'd'))
# 9  flatline
E.GLITCH.append((B(73), B(73) + 0.25))
shot(B(73), T1 + 0.1, bgp('plain', '#CDD3DD'),
     ecg=[dict(t=B(73) - 0.5, y=960, amp=150, mode='beat', c=RED, gc=PNK, th=7, don=0.01, flat=B(73) + 0.25)],
     texts=[dict(s='ドキ…', st='jpr', size=150, x=W / 2, y=700, t=B(73), ent='pop', end=T1 - 0.45)])

# ---------------------------------------------------------------- frame with two-shot transitions
def move(img, dx, dy):
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

def transition(cur, prev, kind, u, arg=None):
    if kind == 'whip':
        e = eio(u); sgn = -1 if arg == 'u' else 1
        off = e * H
        a = move(prev, 0, sgn * off); b = move(cur, 0, sgn * (off - H))
        cut = H - off if sgn < 0 else off            # boundary row between the two images
        rows = np.arange(H)[:, None, None]
        out = np.where(rows < cut, a if sgn < 0 else b, b if sgn < 0 else a)
        kb = int(1 + 110 * math.sin(math.pi * u))
        return cv2.blur(out, (1, kb)) if kb > 2 else out
    if kind == 'zoom':
        z = 1 + 2.2 * ein(u)
        Mz = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
        a = cv2.warpAffine(prev, Mz, (W, H), borderMode=cv2.BORDER_REFLECT)
        a = cv2.GaussianBlur(a, (0, 0), 1 + 16 * u)
        z2 = lerp(1.3, 1.0, eout(u))
        b = cv2.warpAffine(cur, cv2.getRotationMatrix2D((W / 2, H / 2), 0, z2), (W, H), borderMode=cv2.BORDER_REFLECT)
        k = eout(u)
        return a * (1 - k) + b * k
    if kind == 'slices':
        n = 10; out = prev.copy(); bh = H // n + 1
        for i in range(n):
            p = eout(clamp((u - i * 0.035) / 0.6)); dx = (1 - p) * W * (1 if i % 2 else -1)
            y0, y1 = i * bh, min(H, (i + 1) * bh)
            band = cur[y0:y1]
            sh_ = int(round(dx))
            if sh_ >= 0: out[y0:y1, sh_:] = band[:, :W - sh_]
            else: out[y0:y1, :W + sh_] = band[:, -sh_:]
        return out
    if kind == 'dots':
        r = np.clip((u * 1.7 - DIAG * 0.7), 0, 1) * SPC * 0.78
        m = np.clip((r - DGRID) / 1.5 + 0.5, 0, 1)[..., None]
        if arg:   # coloured rim
            rim = np.clip((r + 6 - DGRID) / 1.5 + 0.5, 0, 1)[..., None] - m
            prev = prev * (1 - rim) + hexc(arg) * rim
        return prev * (1 - m) + cur * m
    if kind == 'melt':
        k = eout(u)
        a = move(cv2.GaussianBlur(prev, (0, 0), 1 + 14 * u), 0, -80 * u)
        return a * (1 - k) + cur * k
    return cur

def frame(fi):
    t = fi / E.FPS
    si = E.shot_at(t); sh = E.S[si]
    rgb = E.render_shot(sh, t)
    if sh['tr'] and si > 0:
        kind = sh['tr'][0]; d = D_TR.get(kind, 0)
        if t < sh['t0'] + d:
            prev = E.render_shot(E.S[si - 1], t)
            rgb = transition(rgb, prev, kind, (t - sh['t0']) / d, sh['tr'][1] if len(sh['tr']) > 1 else None)
    rgb = np.clip(rgb, 0, 1)
    zoom = 1 + sh['pulse'] * math.exp(-E.since_beat(t) * 9)
    ox = oy = 0.0
    for ts, amp, dc in E.SHAKE:
        if ts <= t < ts + 2.5:
            k = amp * math.exp(-(t - ts) * dc); ox += k * math.sin(t * 71); oy += k * math.cos(t * 53)
    if zoom > 1.0005 or abs(ox) + abs(oy) > 0.3:
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, zoom); M[:, 2] += (ox, oy)
        rgb = cv2.warpAffine(rgb, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    for g0, g1 in E.GLITCH:
        if g0 <= t < g1:
            r_ = np.random.default_rng(fi); dd = int(14 * (1 - (t - g0) / (g1 - g0))) + 2
            rgb[..., 0] = np.roll(rgb[..., 0], dd, 1); rgb[..., 2] = np.roll(rgb[..., 2], -dd, 1)
            for _ in range(6):
                y0 = int(r_.integers(0, H - 60)); hh = int(r_.integers(10, 60))
                rgb[y0:y0 + hh] = np.roll(rgb[y0:y0 + hh], int(r_.integers(-60, 60)), 1)
    for tf, pk, dc, col in E.FLASH:
        if tf <= t < tf + 2:
            f = pk * math.exp(-(t - tf) / dc)
            if f > 0.004: rgb = rgb + (hexc(col) - rgb) * min(f, 1)
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)

# ---------------------------------------------------------------- render
F0 = int(round(T0 * E.FPS)); NF = int(round(LEN * E.FPS))

def stills(times):
    d = os.path.join(E.HERE, 'stills_short2'); os.makedirs(d, exist_ok=True)
    th = []
    for tt in times:
        fr = frame(int(round(tt * E.FPS)))[..., ::-1]
        cv2.imwrite(os.path.join(d, f'{tt:06.2f}.png'), fr)
        s_ = cv2.resize(fr, (270, 480), interpolation=cv2.INTER_AREA)
        cv2.putText(s_, f'{tt - T0:.2f}s', (6, 22), 0, 0.6, (0, 0, 255), 2); th.append(s_)
    while len(th) % 8: th.append(np.zeros_like(th[0]))
    cv2.imwrite(os.path.join(d, 'contact.jpg'), np.vstack([np.hstack(th[i:i + 8]) for i in range(0, len(th), 8)]))

def video():
    import imageio_ffmpeg
    from multiprocessing import Pool
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmpv = os.path.join(E.HERE, '_video_short2.mp4'); tmpa = os.path.join(E.HERE, '_audio_short2.m4a')
    subprocess.run([ff, '-y', '-v', 'error', '-ss', f'{T0:.3f}', '-t', f'{LEN:.3f}', '-i', E.SONG,
                    '-af', f'afade=t=in:d=0.08,afade=t=out:st={LEN - 0.7:.2f}:d=0.7,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000',
                    '-c:a', 'aac', '-b:a', '192k', tmpa], check=True)
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(E.FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                          '-tune', 'animation', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmpv],
                         stdin=subprocess.PIPE)
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
