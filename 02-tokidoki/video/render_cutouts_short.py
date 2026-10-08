"""Toki Doki - cut-out character Short (chorus 1, song 49.20-69.20 s), 1080x1920, 20 s.

Characters are extracted from the pages (extract.py -> ../cutouts/*.png) and animated as layers like the reference
MMVs: drops with squash, slides with overshoot, beat hops, sway from the feet, walk cycle, colour echo trails,
white sticker outline + flat colour shadow, on pastel pattern backgrounds with shapes and Japanese words.
Usage:  python render_cutouts_short.py stills 50,52,55   |   python render_cutouts_short.py video -> ../tokidoki-short-cutouts.mp4
"""
import os, sys, math, subprocess
import numpy as np, cv2
from PIL import Image
import render as E
from render import (B, shot, card, shp, sprinkle, hearts, bgp, clamp, eout, ein, eio, eback, lerp, hexc,
                    WH, SKY, SKYL, SKY2, BLU, PNK, PNKL, ROS, RED, CRM, CRML, MNT, LIL, LILL, NAV, GRY)

T0 = B(20); LEN = 20.0; T1 = T0 + LEN
W, H = 1080, 1920
E.W, E.H = W, H
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
E.PMAP = (_xx + 0.4 * _yy) / (W + 0.4 * H)
SPC = 64.0
DGRID = np.sqrt(((_xx % SPC) - SPC / 2) ** 2 + ((_yy % SPC) - SPC / 2) ** 2).astype(np.float32)
DIAG = ((_xx + _yy) / (W + H)).astype(np.float32)
del _yy, _xx
E.DUR = 9999.0
E.S.clear(); E.FLASH.clear(); E.SHAKE.clear(); E.GLITCH.clear(); E.HUDS = []
OUT = os.path.join(E.ROOT, 'tokidoki-short-cutouts.mp4')
CUTD = os.path.join(E.ROOT, 'cutouts')
JP = E.JP
E.STY.update({
    'jpw': dict(font=JP, fill=WH, sh=NAV, so=0.06, stroke=NAV, sw=0.03),
    'jpr': dict(font=JP, fill=RED, sh=NAV, so=0.05, stroke=WH, sw=0.07),
    'jpp': dict(font=JP, fill=ROS, sh=NAV, so=0.05, stroke=WH, sw=0.07),
    'jpb': dict(font=JP, fill=BLU, sh=NAV, so=0.05, stroke=WH, sw=0.07),
})

# ---------------------------------------------------------------- cut-out sprites
CUT = {}
PADC = 40
def cut(name):
    if name not in CUT:
        a = np.asarray(Image.open(os.path.join(CUTD, name + '.png')), np.float32) / 255
        k = min(1.0, 1400 / a.shape[0])
        if k < 1: a = cv2.resize(a, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        a = np.pad(a, ((PADC, PADC), (PADC, PADC), (0, 0)))
        pm = a.copy(); pm[..., :3] *= pm[..., 3:4]
        al = a[..., 3]
        dil = cv2.dilate(al, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (29, 29)))
        dil = cv2.GaussianBlur(dil, (0, 0), 1.2)
        CUT[name] = (pm, dil)
    return CUT[name]

def char_xform(c, t):
    """-> (x, y_bottom, scale, rot_deg, sx, sy) for a character item at time t, or None."""
    lt = t - c['t']
    if lt < 0: return None
    pm, _ = cut(c['img'])
    hsrc = pm.shape[0] - 2 * PADC
    k = c['h'] / hsrc
    x, y = c['x'], c['y']; rot = c.get('rot', 0.0); sx = sy = 1.0; sc = 1.0
    ent = c.get('ent', 'none'); ed = c.get('ed', 0.4); e = clamp(lt / ed)
    land = None
    if ent == 'drop':
        y -= 1500 * (1 - e) ** 2; land = ed
    elif ent.startswith('slide'):
        d = 1 if ent.endswith('r') else -1
        x += d * 1200 * (1 - eback(e)); rot += d * 12 * (1 - eout(e)); land = ed
    elif ent == 'rise':
        y += 1100 * (1 - eout(e)); land = ed
    elif ent == 'pop':
        sc *= eback(e)
    elif ent == 'spin':
        sc *= eback(e); rot -= 200 * (1 - eout(e))
    if land is not None and lt >= land:
        dl = lt - land; q = c.get('squash', 0.16) * math.exp(-dl * 7) * math.cos(dl * 24)
        sx *= 1 + q; sy *= 1 - q
    if 'walk' in c:
        x1, sps, amp = c['walk']; u = clamp(lt / max(c['dur'], 0.1))
        x = lerp(c['x'], x1, u); ph = lt * math.pi * sps
        y -= amp * abs(math.sin(ph)); rot += 4 * math.sin(ph)
    if c.get('hop'):
        amp, beats = c['hop']
        for bt in beats:
            db = t - bt
            if 0 <= db < 0.42:
                y -= amp * math.sin(math.pi * db / 0.42)
                if db < 0.1: sx *= 1 + 0.06 * (1 - db / 0.1); sy *= 1 - 0.06 * (1 - db / 0.1)
    if c.get('bob'): y += c['bob'] * math.sin(lt * 2.4 + c['x'] * 0.01)
    if c.get('sway'): rot += c['sway'] * math.sin(lt * 1.9 + c['x'] * 0.02)
    if c.get('br'): sy *= 1 + c['br'] * math.sin(lt * 2.6)
    if c.get('bp'): s_ = 1 + c['bp'] * math.exp(-E.since_beat(t) * 9); sx *= s_; sy *= s_
    if 'out' in c and t > c['out']:
        uo = clamp((t - c['out']) / 0.3); d = c.get('outdir', 1)
        x += d * 1300 * ein(uo); rot += d * 15 * uo
    return x, y, k * sc, rot, sx, sy

def char_M(pm, xf, dx=0.0, dy=0.0, flip=False):
    x, y, k, rot, sx, sy = xf
    h, w = pm.shape[:2]
    S_ = np.float64([[(-1 if flip else 1) * k * sx, 0, 0], [0, k * sy, 0], [0, 0, 1]])
    T1_ = np.float64([[1, 0, -w / 2], [0, 1, -(h - PADC)], [0, 0, 1]])       # pivot = bottom centre
    a = math.radians(rot); R_ = np.float64([[math.cos(a), math.sin(a), 0], [-math.sin(a), math.cos(a), 0], [0, 0, 1]])
    T2_ = np.float64([[1, 0, x + dx], [0, 1, y + dy], [0, 0, 1]])
    return (T2_ @ R_ @ S_ @ T1_)[:2]

def warp_into(rgb, src, M, col=None, alpha=1.0):
    h, w = src.shape[:2]
    cs = np.float32([[0, 0], [w, 0], [w, h], [0, h]]) @ M[:, :2].T + M[:, 2]
    bx, by, bx1, by1 = E.bbox_of(cs, 2)
    if bx1 - bx < 2 or by1 - by < 2: return
    M2 = M.copy(); M2[:, 2] -= (bx, by)
    o = cv2.warpAffine(src, M2.astype(np.float32), (bx1 - bx, by1 - by), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    reg = rgb[by:by1, bx:bx1]
    if col is None:
        al = o[..., 3:4] * alpha; reg[:] = reg * (1 - al) + o[..., :3] * alpha
    else:
        al = o[..., None] * alpha; reg[:] = reg * (1 - al) + hexc(col) * al

def draw_char(rgb, c, t):
    if c.get('end') is not None and t > c['end']: return
    xf = char_xform(c, t)
    if xf is None: return
    pm, dil = cut(c['img']); flip = c.get('flip', False)
    for i, col in enumerate(c.get('echo', ())):           # colour trail at lagged positions
        xe = char_xform(c, t - (i + 1) * c.get('lag', 0.07))
        if xe is not None: warp_into(rgb, dil, char_M(pm, xe, flip=flip), col, 0.75)
    so = c.get('so', (18, 18))
    warp_into(rgb, dil, char_M(pm, xf, so[0], so[1], flip), c.get('sc', NAV), 1.0)
    warp_into(rgb, dil, char_M(pm, xf, flip=flip), c.get('oc', WH), 1.0)
    warp_into(rgb, pm, char_M(pm, xf, flip=flip))

def chr_(img, t, x, y, h, **kw): d = dict(img=img, t=t, x=x, y=y, h=h); d.update(kw); return d

def speed_lines(rgb, t, sh, n=46, seed=3, col=WH):
    r = np.random.default_rng(seed + int(t * 30) % 4)
    cx, cy = W / 2, H * 0.42
    for i in range(n):
        a = r.uniform(0, 2 * np.pi); r0 = r.uniform(520, 760); r1 = r0 + r.uniform(300, 900)
        p0 = (int(cx + r0 * math.cos(a)), int(cy + r0 * math.sin(a)))
        p1 = (int(cx + r1 * math.cos(a)), int(cy + r1 * math.sin(a)))
        cv2.line(rgb, p0, p1, tuple(float(v) for v in hexc(col)), int(r.uniform(3, 11)), cv2.LINE_AA)

def jp(t, s, x, y, size, st='jpw', step=None, vertical=False, ent='stamp', styles=None, **kw):
    out, n = [], len(s)
    for i, ch in enumerate(s):
        cx, cy = (x, y + i * size * 1.04) if vertical else (x + (i - (n - 1) / 2) * size, y)
        tt = (E.nb(t, i) if step is None else t + i * step)
        out.append(dict(s=ch, st=(styles[i] if styles else st), size=size, x=cx, y=cy, t=tt, ent=ent, **kw))
    return out

def cshot(t0, t1, bg, chars=(), **kw):
    fx = kw.pop('fx_', None)
    shot(t0, t1, bg, **kw); E.S[-1]['chars'] = list(chars); E.S[-1]['fx'] = fx

# ================================================================ timeline (song time; bars of 2.35 s)
D_TR = {'whip': 0.32, 'zoom': 0.4, 'slices': 0.42, 'dots': 0.5}
beats = lambda j, ks: [B(j, k) for k in ks]
# 1  ドキドキ - Hatsu drops in on the downbeat
E.FLASH.append((B(20), 0.8, 0.22, WH))
cshot(B(20), B(21), bgp('dots', PNK, PNKL, P=70, r=10, v=(0, -2)),
      chars=[chr_('hatsu_color', B(20), W / 2, 1960, 1500, ent='drop', ed=0.32, echo=(ROS, CRM), lag=0.05,
                  hop=(26, beats(20, (2,))), sway=1.5, sc=RED)],
      shapes=[shp('heart', W / 2, 1000, 520, WH, B(20), a=0.9, bp=0.08, ent='pop')] +
             sprinkle(B(20, 1), 10, 1, (WH, RED, CRM), kinds=('plus', 'heart', 'star'), area=(40, 250, 1040, 1500)),
      ecg=[dict(t=B(20), y=560, amp=120, mode='fast', c=RED, gc=PNK, th=7, don=0.3, glow=0.3)],
      texts=jp(B(20) + 0.05, 'ドキドキ', W / 2, 270, 220, step=0.29, sh=RED))
# 2  both of them - slide in from opposite sides, alternate hops
cshot(B(21), B(22), bgp('stripes', CRML, CRM, P=110, r=0.5, v=(1, 1)),
      chars=[chr_('hatsu_color', B(21), 330, 1960, 1180, ent='slide-l', ed=0.45, hop=(40, beats(21, (0, 2))), sc=ROS),
             chr_('hato_color', B(21) + 0.12, 770, 1960, 1240, ent='slide-r', ed=0.45, hop=(40, beats(21, (1, 3))), sc=BLU)],
      shapes=hearts(B(21, 1), 8, 2, area=(380, 400, 700, 900), size=(20, 44), step=0.12),
      texts=[dict(s='いいんだよ', st='jpp', size=120, x=W / 2, y=300, t=B(21, 1), ent='pop')],
      tr=('slices',))
# 3  君の色 - diagonal split, smiling Hatsu rises
cshot(B(22), B(23), bgp('dots', PNK, PNKL, P=64, r=9),
      chars=[chr_('hatsu_smile', B(22), 470, 1990, 1450, ent='rise', ed=0.45, sway=2.0, br=0.01, sc=ROS, oc=WH)],
      shapes=[shp('rect', 900, 400, (900, 520), SKY, B(22), rot=-25, ent='slide-r', ed=0.35,
                  pat=('dots', SKY, SKYL, 64, 9))],
      texts=jp(B(22, 1), '君の色', 760, 330, 210, styles=['jpp', 'jpb', 'jpr'], step=0.29),
      tr=('whip', 'u'))
# 4  she walks through, giant 色 behind, colour echo trail
cshot(B(23), B(24), bgp('stripes', LILL, WH, P=100, r=0.5, v=(2, 0)),
      chars=[chr_('hatsu_stand', B(23), -180, 1840, 1500, walk=(1260, 1.72, 34), dur=B(24) - B(23),
                  echo=(PNK, SKY, CRM), lag=0.09, sc=LIL)],
      texts=[dict(s='色', st='jpp', size=820, x=W / 2, y=760, t=B(23), ent='pop', a=0.9)],
      tr=('dots', PNK))
# 5  光 - Hato spins in, light rays
E.FLASH.append((B(24), 0.9, 0.25, WH))
cshot(B(24), B(25), bgp('plain', CRM),
      chars=[chr_('hato_color', B(24), W / 2, 1960, 1450, ent='spin', ed=0.45, bp=0.02, sway=1.2, sc=SKY2)],
      shapes=[shp('burst', W / 2, 820, 1100, '#FFF7C9', B(24), spin=18, ent='grow', ed=0.4),
              shp('circle', W / 2, 820, 360, WH, B(24), a=0.7, bp=0.06, ent='grow')] +
             sprinkle(B(24), 16, 5, (WH, SKY2, '#FFD860'), kinds=('plus', 'star'), size=(14, 34), area=(40, 200, 1040, 1700)),
      texts=[dict(s='光', st='jpw', size=330, x=W / 2, y=300, t=B(24) + 0.08, ent='stamp', sh=SKY2, bp=0.05)],
      tr=('zoom',))
# 6  Hato bursts up - speed lines, shake
E.SHAKE.append((B(25), 22, 6)); E.FLASH.append((B(25), 0.6, 0.15, WH))
cshot(B(25), B(26), bgp('dots', SKY2, SKY, P=70, r=10),
      chars=[chr_('hato_shout', B(25), W / 2, 1980, 1400, ent='rise', ed=0.28, squash=0.2, hop=(30, beats(25, (2,))), sc=NAV)],
      fx_='speed',
      texts=[dict(s='ドキ!!', st='jpr', size=210, x=W / 2, y=330, t=B(25, 1), ent='stamp', rot=-6, bp=0.06)])
# 7  ときどき - four tiles, each character hops on its own beat
_tiles = [(270, 760, PNK, 'hatsu_color', 0), (810, 760, SKY, 'hato_color', 1),
          (270, 1420, CRM, 'hatsu_smile', 2), (810, 1420, MNT, 'hato_shout', 3)]
cshot(B(26), B(27), bgp('grid', WH, GRY, P=120),
      chars=[chr_(img, B(26, i), x, y + 290, 560, ent='pop', ed=0.3, hop=(34, beats(26, (i,)) + beats(27, (i,))), sc=NAV, so=(10, 10))
             for x, y, col, img, i in _tiles],
      shapes=[shp('rect', x, y, (250, 300), col, B(26, i), ol=6, ent='pop', ed=0.3) for x, y, col, img, i in _tiles],
      texts=[dict(s='ときどき', st='jpp', size=150, x=W / 2, y=240, t=B(26), ent='pop')],
      tr=('slices',))
# 8  嬉しい - the couple floats on hearts
cshot(B(27), B(28), bgp('hearts', PNK, PNKL, P=120, r=20, v=(0, -3)),
      chars=[chr_('couple', B(27), W / 2, 1700, 1250, ent='pop', ed=0.4, sway=3.0, bob=18, sc=RED)],
      shapes=[shp('circle', W / 2, 1100, 520, WH, B(27), a=0.85, ent='grow', bp=0.05)] +
             hearts(B(27), 18, 8, area=(40, 400, 1040, 1800), size=(18, 46), step=0.08),
      texts=jp(B(27, 1), '嬉しい', W / 2, 300, 210, st='jpr', step=0.2),
      tr=('dots', RED))
# 9  together + logo
E.FLASH.append((B(28), 0.8, 0.22, WH))
cshot(B(28), T1 + 0.1, bgp('dots', SKYL, WH, P=70, r=8),
      chars=[chr_('hatsu_color', B(28), 330, 1960, 1250, ent='slide-l', ed=0.35, sc=ROS),
             chr_('hato_color', B(28), 770, 1960, 1300, ent='slide-r', ed=0.35, sc=BLU)],
      cards=[card('02logo', mode='norm', w=900, cx=W / 2, cy=330, ent='pop', s1=1.03)])

# ---------------------------------------------------------------- frame
def render_shot_c(sh, t):
    rgb = E.background(sh, t)
    for s in sh['shapes']:
        if s.get('layer', 'back') == 'back': E.draw_shape(rgb, s, t)
    if sh.get('fx') == 'speed': speed_lines(rgb, t, sh)
    for it in sh['texts']:
        if it.get('size', 0) >= 600: E.draw_text(rgb, it, t)      # giant background glyphs sit behind characters
    for e in sh['ecg']: E.draw_ecg(rgb, e, t)
    for c in sh.get('chars', []): draw_char(rgb, c, t)
    for c in sh['cards']: E.render_card(rgb, c, t, sh)
    for s in sh['shapes']:
        if s.get('layer', 'back') == 'front': E.draw_shape(rgb, s, t)
    for it in sh['texts']:
        if it.get('size', 0) < 600: E.draw_text(rgb, it, t)
    return rgb

def move(img, dx, dy):
    return cv2.warpAffine(img, np.float32([[1, 0, dx], [0, 1, dy]]), (W, H), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_REPLICATE)

def transition(cur, prev, kind, u, arg=None):
    if kind == 'whip':
        e = eio(u); sgn = -1 if arg == 'u' else 1; off = e * H
        a = move(prev, 0, sgn * off); b = move(cur, 0, sgn * (off - H))
        cutr = H - off if sgn < 0 else off
        out = np.where(np.arange(H)[:, None, None] < cutr, a if sgn < 0 else b, b if sgn < 0 else a)
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
            p = eout(clamp((u - i * 0.035) / 0.6)); s_ = int(round((1 - p) * W * (1 if i % 2 else -1)))
            y0, y1 = i * bh, min(H, (i + 1) * bh); band = cur[y0:y1]
            if s_ >= 0: out[y0:y1, s_:] = band[:, :W - s_]
            else: out[y0:y1, :W + s_] = band[:, -s_:]
        return out
    if kind == 'dots':
        r = np.clip((u * 1.7 - DIAG * 0.7), 0, 1) * SPC * 0.78
        m = np.clip((r - DGRID) / 1.5 + 0.5, 0, 1)[..., None]
        if arg:
            rim = np.clip((r + 6 - DGRID) / 1.5 + 0.5, 0, 1)[..., None] - m
            prev = prev * (1 - rim) + hexc(arg) * rim
        return prev * (1 - m) + cur * m
    return cur

def frame(fi):
    t = fi / E.FPS
    si = E.shot_at(t); sh = E.S[si]
    rgb = render_shot_c(sh, t)
    if sh['tr'] and si > 0:
        kind = sh['tr'][0]; d = D_TR.get(kind, 0)
        if t < sh['t0'] + d:
            rgb = transition(rgb, render_shot_c(E.S[si - 1], t), kind, (t - sh['t0']) / d, sh['tr'][1] if len(sh['tr']) > 1 else None)
    rgb = np.clip(rgb, 0, 1)
    zoom = 1 + 0.02 * math.exp(-E.since_beat(t) * 9)
    ox = oy = 0.0
    for ts, amp, dc in E.SHAKE:
        if ts <= t < ts + 2.0:
            k = amp * math.exp(-(t - ts) * dc); ox += k * math.sin(t * 71); oy += k * math.cos(t * 53)
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, zoom); M[:, 2] += (ox, oy)
    rgb = cv2.warpAffine(rgb, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    for tf, pk, dc, col in E.FLASH:
        if tf <= t < tf + 2:
            f = pk * math.exp(-(t - tf) / dc)
            if f > 0.004: rgb = rgb + (hexc(col) - rgb) * min(f, 1)
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)

# ---------------------------------------------------------------- render
F0 = int(round(T0 * E.FPS)); NF = int(round(LEN * E.FPS))

def stills(times):
    d = os.path.join(E.HERE, 'stills_cutouts'); os.makedirs(d, exist_ok=True)
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
    tmpv = os.path.join(E.HERE, '_video_cut.mp4'); tmpa = os.path.join(E.HERE, '_audio_cut.m4a')
    subprocess.run([ff, '-y', '-v', 'error', '-ss', f'{T0:.3f}', '-t', f'{LEN:.3f}', '-i', E.SONG,
                    '-af', f'afade=t=in:d=0.08,afade=t=out:st={LEN - 0.6:.2f}:d=0.6,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000',
                    '-c:a', 'aac', '-b:a', '192k', tmpa], check=True)
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(E.FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                          '-tune', 'animation', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmpv], stdin=subprocess.PIPE)
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
