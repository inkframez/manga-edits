"""Steel Ball Run ch.18 v3 - 44.6 s Short, 1080x1920, 30 fps, cut to music_v3.py (140 BPM, 104 beats).

Slower than v2: 2-8 beat shots, longer eased camera moves, softer beat bumps, fewer flash frames. Built on
render_v2.py's engine (camera tours, 3D cards, transitions, type, magnet fx); v3 adds two set pieces:
  STEEL BALL (beats 44-66)
    * a real spinning ball (cut from page 14) charges up in Gyro's hand: spin blur, specular, orbit rings, golden spiral
    * the throw: the ball flies at the camera and the next shot is revealed *inside* it (fisheye 'ball' morph)
    * the flight: the ball travels the drawn arc on page 17 (its painted ball is inpainted out) with a glowing trail,
      bursts off the rock in debris, lands on the panel's own ball; then the iron scraps rip into Tim
  OH! LONESOME ME (beats 74-94)
    * Stand reveal: a rope lashes across the card, Stand name + katakana
    * the 'split' transition: the frame is sliced across the rope line and the pieces slide apart along it, then the
      split body (page 23) slides together; a glint runs down the rope and each body part pulses as it passes
Usage:  python music_v3.py
        python render_v3.py stills 1,20,23   |   python render_v3.py video   -> ../mountain-tim-short-v3.mp4
"""
import os, sys, math, json, subprocess
import numpy as np, cv2
import render as R
import render_v2 as V
from render import clamp, eout, ein, eio, lerp, hexc, page, sprite, blit, W, H, FPS, INK, PAPER, PINK
from render_v2 import cam, tour_cam, to_screen, burst, eback, JPS, IMP, LAB, MONO, JP, GOLD, MAG, VIOLET, LIME, RED

HERE = R.HERE; ROOT = R.ROOT
BM = json.load(open(os.path.join(HERE, 'beatmap_v3.json')))
BEAT = BM['beat']; DUR = BM['dur']; N = int(round(DUR * FPS))
def b(n): return n * BEAT
V.MOVE = 0.45                                        # slower, longer camera moves
_yy, _xx = V._yy, V._xx
ROPE_C, ROPE_D, ROPE_L = hexc('#8A5A2B'), hexc('#2A1608'), hexc('#E2B878')

# ---------------------------------------------------------------- assets: the ball sprite, page 17 without its ball
def _ball_sprite():
    up, s = page('14'); cx, cy, r = 105 * s, 96 * s, 71 * s
    x0, y0 = int(cx - r), int(cy - r); d = int(2 * r)
    im = up[y0:y0 + d, x0:x0 + d].copy()
    yy, xx = np.mgrid[0:d, 0:d].astype(np.float32); rr = np.sqrt((xx - d / 2) ** 2 + (yy - d / 2) ** 2) / (d / 2)
    a = np.clip((1 - rr) / 0.03, 0, 1)
    im = np.clip((im - 0.5) * 1.1 + 0.5, 0, 1) * (1 - 0.35 * np.clip(rr - 0.6, 0, 1) / 0.4)[..., None]   # darker rim
    return np.dstack([im * a[..., None], a]).astype(np.float32)
BALL = _ball_sprite(); BALL_R = BALL.shape[0] / 2
_hy, _hx = np.mgrid[0:BALL.shape[0], 0:BALL.shape[0]].astype(np.float32)
SPEC = np.exp(-(((_hx - BALL_R * 0.62) ** 2 + (_hy - BALL_R * 0.55) ** 2) / (BALL_R * 0.32) ** 2))[..., None] * BALL[..., 3:4]
SPEC4 = np.dstack([SPEC * 0.9] * 3 + [SPEC * 0]).astype(np.float32)

def _inpaint17():
    up, s = page('17')
    u8 = (np.clip(up, 0, 1) * 255).astype(np.uint8)
    m = np.zeros(u8.shape[:2], np.uint8); cv2.ellipse(m, (int(262 * s), int(812 * s)), (int(66 * s), int(54 * s)), -8, 0, 360, 255, -1)
    R.PAGES['17i'] = (cv2.inpaint(u8, m, 7, cv2.INPAINT_TELEA).astype(np.float32) / 255, s)
_inpaint17()

def draw_ball(rgb, cx, cy, r, ang, spin=0.0, glow=1.0, rings=1.0, t=0.0):
    if r < 2: return
    sc = r / BALL_R
    if glow > 0.01:
        lay = np.zeros((H, W), np.float32); cv2.circle(lay, (int(cx), int(cy)), int(r * 1.05), 1.0, -1, cv2.LINE_AA)
        g = cv2.GaussianBlur(lay, (0, 0), max(4, r * 0.35)); rgb[:] = rgb + LIME * (g * 0.9 * glow)[..., None]
    n = 3 if spin > 2 else 1
    for k in range(n):                                   # spin blur: a few rotations of the sprite, averaged
        a = ang - k * min(spin, 40) * 0.6
        blit(rgb, BALL, cx, cy, sc, a, 1.0 / n if k else (1.0 if n == 1 else 0.55))
    blit(rgb, SPEC4, cx, cy, sc, 0, 1.0)                 # fixed highlight (additive: alpha 0)
    if rings > 0.01:
        lay = np.zeros((H, W), np.float32)
        for k in range(3):
            st = (t * (300 + 240 * k) + k * 120) % 360
            cv2.ellipse(lay, (int(cx), int(cy)), (int(r * (1.35 + 0.18 * k)), int(r * (0.42 + 0.08 * k))), -18 + 14 * k,
                        st, st + 250, 1.0, max(2, int(r * 0.06)), cv2.LINE_AA)
        g = cv2.GaussianBlur(lay, (0, 0), 5)
        rgb[:] = rgb + (LIME * g[..., None] * 1.3 + lay[..., None] * 0.6) * rings

def catmull(pts, u):
    pts = np.float32(pts); n = len(pts) - 1
    x = clamp(u) * n; i = min(int(x), n - 1); f = x - i
    p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, n)]
    return 0.5 * (2 * p1 + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (-p0 + 3 * p1 - 3 * p2 + p3) * f ** 3)

ARC = [(245, 505), (145, 545), (73, 618), (41, 700), (64, 773), (127, 818), (200, 828), (262, 812)]
ROPE = [(20, 780), (150, 690), (330, 560), (470, 450), (560, 380), (680, 300), (760, 215), (870, 110)]
PARTS = [(200, 650), (370, 520), (385, 410), (560, 330), (715, 245), (850, 120)]

# ---------------------------------------------------------------- timeline
S, TEXT, MEN, DIM = [], [], [], []
def tour(t0, t1, p, keys, g, tr=None, **kw): S.append(dict(kind='tour', t0=t0, t1=t1, p=p, keys=keys, grade=g, tr=tr, **kw))
def card(t0, t1, p, r, g, tr=None, **kw): S.append(dict(kind='card', t0=t0, t1=t1, p=p, r=r, grade=g, tr=tr, **kw))
def T(t, s, x, y, size, end=None, fnt=IMP, ent='slam', **kw): TEXT.append(dict(t=t, s=s, x=x, y=y, size=size, end=end, fnt=fnt, ent=ent, **kw))
def BAR(t, x, y, w, h, col, end=None, skew=-12, a=0.9): TEXT.append(dict(t=t, ent='bar', x=x, y=y, w=w, h=h, col=col, end=end, skew=skew, a=a, s=''))
def menace(t0, t1, s, x, y, dx, dy, size, col=VIOLET, rot=-10): MEN.append(dict(t0=t0, t1=t1, s=s, x=x, y=y, dx=dx, dy=dy, size=size, col=col, rot=rot))
ST = dict(stg=0.03)

# ---- 0-16 the chase
tour(b(0), b(8), '01', [(b(0), cam(285, 140, 330)), (b(3), cam(560, 200, 400)), (b(6), cam(850, 250, 310, -2))], 'desert', lines='gallop')
T(b(0.3), '三時間', 130, 300, 150, b(8), vertical=True, **JPS)
BAR(b(2), W / 2, 1462, 1250, 190, INK, b(8))
T(b(2), 'THREE HOURS', W / 2, 1455, 150, b(8), glint=b(4), slant=-8, **ST)
T(b(4), 'SAME PACE.', W / 2, 1600, 92, b(8), fill=tuple(PINK), stroke=0.05, slant=-8, **ST)
tour(b(8), b(12), '02', [(b(8), cam(445, 890, 300)), (b(11), cam(470, 915, 200))], 'desert', tr='liquid')
T(b(8.5), '誰だ…？', 950, 230, 120, b(12), vertical=True, **JPS)
T(b(9.5), 'WHO IS THAT?', W / 2, 1560, 120, b(12), stroke=0.05, slant=-8, **ST)
card(b(12), b(16), '03', [40, 440, 608, 240], 'desert', tr='zoom', cw=1000, pos=(540, 980), rz=(-5, -2), ry=(20, -6),
     bg=('burst', hexc('#5B2A86'), hexc('#1A0B2E')))
menace(b(12), b(16), 'ドドドド', 160, 330, 120, 30, 150, PINK, -12)
T(b(13), 'SOMEONE IS', W / 2, 1450, 110, b(16), slant=-8, stroke=0.05, **ST)
T(b(14), 'CATCHING UP', W / 2, 1580, 130, b(16), slant=-8, stroke=0.05, fill=tuple(GOLD), **ST)
# ---- 16-28 Mountain Tim
tour(b(16), b(20), '04', [(b(16), cam(470, 290, 620)), (b(18.5), cam(470, 205, 420))], 'desert', tr='flash', lines='radial')
menace(b(16), b(20), 'ドドドドド', 120, 520, 30, 165, 150, PINK, -8)
T(b(17), 'ALREADY UP', 600, 1450, 120, b(20), slant=-8, stroke=0.05, **ST)
T(b(18), 'THE ROCKS?!', 600, 1585, 130, b(20), slant=-8, stroke=0.05, fill=tuple(GOLD), **ST)
card(b(20), b(28), '03', [262, 694, 206, 330], 'desert', tr='liquid', cw=600, pos=(560, 1200), rz=(3, 0), ry=(-16, 4),
     bg=('burst', hexc('#7A3FC2'), hexc('#24103E')))
BAR(b(20.3), W / 2, 470, 1300, 430, INK, b(28), skew=-10, a=0.88)
T(b(20.4), 'MOUNTAIN', 560, 390, 190, b(28), glint=b(23), **ST)
T(b(21.2), 'TIM', 560, 590, 250, b(28), fill=tuple(GOLD), stroke=0.04, glint=b(24), **ST)
T(b(21), 'マウンテン・ティム', 990, 210, 66, b(28), vertical=True, fill=tuple(GOLD), **JPS)
T(b(22.5), 'THE COWBOY  //  RACE ENTRANT', W / 2, 165, 40, b(28), fnt=LAB, ent='type', trk=0.12)
# ---- 28-44 the magnetism
MAG0, MAG1 = b(28), b(44)
tour(b(28), b(34), '05', [(b(28), cam(370, 330, 640)), (b(31), cam(420, 300, 480)), (b(33), cam(435, 300, 400, 3))],
     'magnet', tr='magnet', mag=(440, 330), field=True)
T(b(28.4), '引っ張られる！', 110, 210, 96, b(34), vertical=True, **JPS)
BAR(b(29.5), W / 2, 1555, 1200, 230, VIOLET, b(34), a=0.92)
T(b(29.5), 'PULLED!', W / 2, 1550, 230, b(34), glint=b(31.5), slant=-8, stroke=0.03, **ST)
tour(b(34), b(38), '09', [(b(34), cam(400, 190, 380)), (b(36.5), cam(392, 170, 300, 3))], 'magnet', tr='liquid', field=True)
T(b(34.5), '磁石', W / 2, 1380, 300, b(38), fill=tuple(MAG), glint=b(36), **JPS)
T(b(35.5), 'GYRO TOO?!', W / 2, 1610, 130, b(38), slant=-8, stroke=0.05, fill=tuple(LIME), **ST)
tour(b(38), b(44), '13', [(b(38), cam(900, 520, 560)), (b(40), cam(555, 540, 600, -4)), (b(42), cam(320, 500, 380, 4))],
     'blood', tr='liquid', mag=(520, 640), field=True)
menace(b(38), b(41), 'ゴゴゴゴ', 140, 280, 40, 170, 140, VIOLET, -10)
T(b(38.4), 'ALL THREE OF US', W / 2, 1560, 104, b(40), slant=-8, stroke=0.05, **ST)
T(b(40.2), 'THE IRON IN OUR BLOOD', W / 2, 1560, 62, b(42), fnt=LAB, ent='type', trk=0.08)
T(b(42), '爆発', W / 2, 860, 300, b(43.5), ent='grow', fill=tuple(RED), **JPS)
T(b(42.5), 'WE WILL EXPLODE', W / 2, 1300, 110, b(43.5), slant=-8, stroke=0.05, fill=tuple(RED), **ST)
DIM.append((b(43.5), b(44)))
# ---- 44-66 THE STEEL BALL
HELD = (247, 812)
tour(b(44), b(51), '16', [(b(44), cam(330, 820, 470)), (b(47), cam(290, 812, 360)), (b(49.5), cam(262, 812, 270, -4))],
     'steel', tr='swirl', spiral=HELD, spiral_from=b(46), ball='held')
T(b(44.4), '鉄球', 950, 230, 170, b(50.5), vertical=True, fill=tuple(LIME), **JPS)
BAR(b(45.5), W / 2, 1575, 1150, 200, INK, b(50.5))
T(b(45.5), 'STEEL BALL', W / 2, 1570, 160, b(50.5), glint=b(47.5), slant=-8, **ST)
T(b(48), '回転', 130, 300, 170, b(50.5), vertical=True, fill=tuple(LIME), **JPS)
FLY0, FLY1 = b(52.5), b(56.5)
tour(b(51), b(58), '17i', [(b(51), cam(165, 660, 560)), (b(54), cam(175, 680, 520)), (b(56.5), cam(250, 795, 340, -4))],
     'steel', tr='ball', ball='arc')
T(b(52.6), 'ガリッ', 700, 470, 150, b(54), fill=tuple(PINK), rot=8, **JPS)
T(b(53.5), 'ギュルルルルル', W / 2, 1530, 118, b(57.5), fill=tuple(LIME), rot=-10, stg=0.04, **JPS)
T(b(54.5), 'IT COMES BACK', W / 2, 1660, 84, b(57.5), slant=-8, stroke=0.05)
tour(b(58), b(62), '17', [(b(58), cam(530, 720, 540)), (b(60.5), cam(535, 725, 380, 5))], 'steel', tr='swirl', ball='strip',
     mag=(535, 720))
T(b(58.5), 'WITH THE IRON', W / 2, 1450, 110, b(62), slant=-8, stroke=0.05, **ST)
T(b(59.3), 'IN THE ROCKS', W / 2, 1585, 130, b(62), slant=-8, stroke=0.05, fill=tuple(LIME), **ST)
tour(b(62), b(66), '18', [(b(62), cam(470, 215, 460)), (b(64.5), cam(485, 195, 360, -5))], 'blood', tr='flash', mag=(480, 210),
     scraps=True)
T(b(62.05), 'ドギャーン', W / 2, 1500, 190, b(66), fill=tuple(PINK), rot=-8, stg=0.04, **JPS)
# ---- 66-78 aftermath
tour(b(66), b(70), '20', [(b(66), cam(490, 250, 440)), (b(68.5), cam(500, 225, 350))], 'steel', tr='whip')
T(b(66.3), 'やったぞ！', 110, 230, 110, b(70), vertical=True, **JPS)
T(b(67), 'OFF HIS', W / 2, 1440, 130, b(70), slant=-8, stroke=0.05, **ST)
T(b(67.8), 'HORSE!!', W / 2, 1590, 170, b(70), slant=-8, stroke=0.05, fill=tuple(LIME), **ST)
tour(b(70), b(74), '21', [(b(70), cam(760, 300, 560)), (b(72), cam(790, 430, 500, -4))], 'magnet', tr='halftone', lines='radial')
T(b(70.3), '飛んでる！', 120, 230, 120, b(74), vertical=True, fill=tuple(PINK), **JPS)
T(b(71), "HE'S FLYING!", W / 2, 1560, 150, b(74), slant=-8, stroke=0.05, **ST)
tour(b(74), b(78), '25', [(b(74), cam(300, 200, 420)), (b(77), cam(262, 175, 270))], 'desert', tr='liquid')
T(b(74.6), 'I THREW A ROPE...', W / 2, 1560, 66, b(78), fnt=LAB, ent='type', trk=0.08)
# ---- 78-94 OH! LONESOME ME
ROPE0 = b(78)
card(b(78), b(82), '25', [0, 0, 600, 340], 'rope', tr='zoom', cw=980, pos=(540, 1060), rz=(-6, -3), ry=(16, -4),
     bg=('burst', hexc('#C0207A'), hexc('#2A0420')), rope=True)
T(b(78.4), 'STAND', W / 2, 250, 64, b(82), fnt=LAB, ent='type', trk=0.35, fill=tuple(GOLD))
BAR(b(78.6), W / 2, 420, 1300, 220, INK, b(82), a=0.9)
T(b(78.6), 'OH! LONESOME ME', W / 2, 415, 132, b(82), glint=b(80), slant=-6, **ST)
T(b(79.2), 'オー！ロンサム・ミー', W / 2, 580, 64, b(82), fill=tuple(GOLD), **JPS)
tour(b(82), b(90), '23', [(b(82), cam(520, 420, 790)), (b(85), cam(420, 440, 580, -3)), (b(88), cam(300, 560, 500, 2))],
     'rope', tr='split', rope_glint=True)
T(b(83), 'HE SPLIT HIS BODY', W / 2, 1440, 110, b(86.5), slant=-8, stroke=0.05, **ST)
T(b(84), 'ALONG THE ROPE', W / 2, 1580, 130, b(86.5), slant=-8, stroke=0.05, fill=tuple(LIME), **ST)
T(b(86.5), 'バラバラ', 120, 260, 120, b(90), vertical=True, fill=tuple(PINK), **JPS)
T(b(87), 'SO THE THREE', W / 2, 1450, 104, b(90), slant=-8, stroke=0.05, **ST)
T(b(88), "CAN'T MEET.", W / 2, 1590, 150, b(90), slant=-8, stroke=0.05, fill=tuple(GOLD), **ST)
tour(b(90), b(94), '24', [(b(90), cam(225, 805, 440)), (b(92.5), cam(245, 790, 330, -6))], 'rope', tr='whip', lines='gallop')
T(b(90.4), 'シュルルル', W / 2, 1520, 140, b(94), fill=tuple(PINK), rot=-10, stg=0.04, **JPS)
# ---- 94-104 title, freeze, to be continued
card(b(94), DUR + 0.1, '23', [90, 50, 900, 700], 'rope', tr='flash', cw=1060, pos=(540, 680), rz=(-4, -2), ry=(10, -6),
     bg=('burst', hexc('#D8A21E'), hexc('#2A1606')), zoom=(1.12, 1.0))
T(b(94.3), 'STEEL', W / 2, 1220, 220, None, glint=b(97), stg=0.04)
T(b(95), 'BALL RUN', W / 2, 1410, 220, None, fill=tuple(GOLD), glint=b(97.5), stg=0.04)
T(b(96), 'スティール・ボール・ラン', W / 2, 1555, 58, None, fill=(1, 1, 1), **JPS)
T(b(96.5), 'CHAPTER 18  //  MOUNTAIN TIM', W / 2, 200, 44, None, fnt=LAB, ent='type', trk=0.14)
V.FREEZE, V.ARROW = b(100), b(101)
V.TEXT[:] = TEXT; V.MEN[:] = MEN                    # the v2 type/menace engine draws this cut's lists

BIG = {16, 44, 51, 62, 78, 82, 94}
HITS = [dict(t=ht, big=int(round(ht / BEAT)) in BIG) for ht in BM['hit']]
KICKS, SNARES = np.array(BM['kick']), np.array(BM['snare'])

# ---------------------------------------------------------------- set-piece overlays
def held_ball(rgb, sh, t):
    """the ball in Gyro's hand spins up from beat 45; at 50 it lifts off toward the camera"""
    if t < b(45): return
    cx, cy = to_screen(sh, t, HELD); k = H / tour_cam(sh, t)[0][2]
    u = clamp((t - b(45)) / (b(50) - b(45)))
    spin = 2 + 38 * u ** 1.5; ang = -(t - b(45)) * (60 + 900 * u)
    lift = eio(clamp((t - b(50)) / (b(51) - b(50))))
    r = 40 * k * (1 + 0.15 * u) * lerp(1, 1.9, lift)
    cx, cy = lerp(cx, W / 2, lift * 0.6), lerp(cy, H * 0.47, lift * 0.6)
    draw_ball(rgb, cx, cy, r, ang, spin, glow=0.3 + 0.9 * u, rings=clamp((u - 0.2) * 2), t=t)
def held_pos(t):
    sh = S[_SI['held']]; cx, cy = to_screen(sh, t, HELD); k = H / tour_cam(sh, t)[0][2]
    return cx, cy, 40 * k * 1.15 * 1.9

def arc_ball(rgb, sh, t):
    """the flight along page 17's arc: rock strike, trail, landing on the panel's own ball"""
    k = H / tour_cam(sh, t)[0][2]
    if t < FLY0:                                       # the ball arrives at the rock from off-frame
        u = clamp((t - b(51.6)) / (FLY0 - b(51.6)))
        if u <= 0: return
        p = to_screen(sh, t, (330, 330)); q = to_screen(sh, t, ARC[0])
        draw_ball(rgb, lerp(p[0], q[0], ein(u)), lerp(p[1], q[1], ein(u)), 46 * k, -t * 900, 30, 0.8, 0.6, t); return
    u = eio(clamp((t - FLY0) / (FLY1 - FLY0)))
    lay = np.zeros((H, W), np.float32)                 # glowing trail over the path flown so far
    us = np.linspace(max(0, u - 0.45), u, 40)
    pts = np.int32([to_screen(sh, t, catmull(ARC, v)) for v in us])
    for i in range(len(pts) - 1):
        cv2.line(lay, tuple(int(c) for c in pts[i]), tuple(int(c) for c in pts[i + 1]), float(i / len(pts)), int(6 + 26 * i / len(pts)), cv2.LINE_AA)
    g = cv2.GaussianBlur(lay, (0, 0), 10)
    rgb[:] = rgb + GOLD * (g * 1.1)[..., None] + LIME * (lay * 0.5)[..., None]
    if t < FLY0 + 1.2:                                 # debris burst off the rock
        lt = t - FLY0; r_ = np.random.default_rng(3); o = to_screen(sh, t, ARC[0])
        for i in range(70):
            a = r_.uniform(-2.6, 0.6); sp = r_.uniform(250, 1100); x = o[0] + math.cos(a) * sp * lt; y = o[1] + math.sin(a) * sp * lt + 900 * lt * lt
            s = int(r_.uniform(3, 10)); c = (0.12, 0.1, 0.1) if i % 3 else (0.85, 0.8, 0.7)
            cv2.line(rgb, (int(x), int(y)), (int(x - math.cos(a) * sp * 0.03), int(y - math.sin(a) * sp * 0.03)), c, s, cv2.LINE_AA)
    p = to_screen(sh, t, tuple(catmull(ARC, u)))
    settle = clamp((t - FLY1) / 0.5)
    draw_ball(rgb, p[0], p[1], lerp(50, 52, settle) * k, -t * lerp(1100, 500, settle), lerp(35, 10, settle), 0.9, 1.0, t)

def strip_ball(rgb, sh, t):
    k = H / tour_cam(sh, t)[0][2]; p = to_screen(sh, t, (535, 718))
    draw_ball(rgb, p[0], p[1], 84 * k, -t * 700, 20, 0.6, 0.8, t)

def rope_lash(rgb, t):
    """Oh! Lonesome Me: a rope whips across the card and settles, twisted strands and a highlight"""
    lt = t - ROPE0
    if lt < 0: return
    f = eout(lt / 0.35)
    A0, A1 = np.float32([-120, 1420]), np.float32([1200, 760])
    d = A1 - A0; nrm = np.float32([-d[1], d[0]]) / np.linalg.norm(d)
    s = np.linspace(0, f, 120)
    amp = 220 * math.exp(-lt * 4.5) * math.sin(lt * 22) + 30 * math.sin(lt * 2)
    pts = np.float32([A0 + d * v + nrm * (amp * math.sin(math.pi * v) + 18 * math.sin(2 * math.pi * v + lt * 3)) for v in s])
    P = np.int32(pts * 16)
    cv2.polylines(rgb, [P], False, tuple(float(v) for v in ROPE_D), 38, cv2.LINE_AA, 4)
    cv2.polylines(rgb, [P], False, tuple(float(v) for v in ROPE_C), 28, cv2.LINE_AA, 4)
    seg = np.cumsum(np.r_[0, np.hypot(*np.diff(pts, axis=0).T)])
    for i in range(1, len(pts)):                         # twist marks
        if int(seg[i] / 20) != int(seg[i - 1] / 20):
            tx, ty = pts[i] - pts[i - 1]; L = math.hypot(tx, ty) + 1e-6; tx, ty = tx / L, ty / L
            q0 = pts[i] + np.float32([-ty, tx]) * 12 - np.float32([tx, ty]) * 6; q1 = pts[i] - np.float32([-ty, tx]) * 12 + np.float32([tx, ty]) * 6
            cv2.line(rgb, (int(q0[0]), int(q0[1])), (int(q1[0]), int(q1[1])), tuple(float(v) for v in ROPE_D), 3, cv2.LINE_AA)
    cv2.polylines(rgb, [np.int32((pts + nrm * -7) * 16)], False, tuple(float(v) for v in ROPE_L), 4, cv2.LINE_AA, 4)
    if lt < 0.5:                                         # the crack: a flash at the tip
        tip = pts[-1]; lay = np.zeros((H, W), np.float32); cv2.circle(lay, (int(tip[0]), int(tip[1])), 40, 1.0, -1)
        rgb[:] = rgb + PAPER * cv2.GaussianBlur(lay, (0, 0), 30)[..., None] * (1 - lt / 0.5) * 1.5

def rope_cut(rgb, t):
    """second crack: the card is cut in two along the rope and the halves drift apart"""
    lt = t - b(80); off = 46 * eout(lt / 0.3)
    A0, A1 = np.float32([-120, 1420]), np.float32([1200, 760]); d = (A1 - A0) / np.linalg.norm(A1 - A0); n = np.float32([-d[1], d[0]])
    side = ((_xx - A0[0]) * n[0] + (_yy - A0[1]) * n[1]) > 0
    up = cv2.warpAffine(rgb, np.float32([[1, 0, -n[0] * off], [0, 1, -n[1] * off]]), (W, H), borderMode=cv2.BORDER_REFLECT)
    dn = cv2.warpAffine(rgb, np.float32([[1, 0, n[0] * off], [0, 1, n[1] * off]]), (W, H), borderMode=cv2.BORDER_REFLECT)
    out = np.where(side[..., None], dn, up)
    dist = np.abs((_xx - A0[0]) * n[0] + (_yy - A0[1]) * n[1])
    out = out * np.where(dist < off, 0.25, 1.0)[..., None] + MAG * (np.exp(-((dist - off) / 5) ** 2) * 1.2)[..., None]
    if lt < 0.25: out = out + (PAPER - out) * (1 - lt / 0.25) * 0.5
    return out.astype(np.float32)

def rope_glint(rgb, sh, t):
    """a glint runs down the rope; each body part pulses as it passes"""
    pts = np.float32(ROPE); seg = np.cumsum(np.r_[0, np.hypot(*np.diff(pts, axis=0).T)]); L = seg[-1]
    u = ((t - sh['t0']) / 1.6) % 1.0; sdist = u * L
    i = min(np.searchsorted(seg, sdist) - 1, len(pts) - 2); i = max(i, 0); f = (sdist - seg[i]) / (seg[i + 1] - seg[i])
    g = to_screen(sh, t, tuple(pts[i] + (pts[i + 1] - pts[i]) * f))
    lay = np.zeros((H, W), np.float32)
    cv2.circle(lay, (int(g[0]), int(g[1])), 10, 1.0, -1, cv2.LINE_AA)
    cv2.line(lay, (int(g[0] - 140), int(g[1])), (int(g[0] + 140), int(g[1])), 0.7, 3, cv2.LINE_AA)
    cv2.line(lay, (int(g[0]), int(g[1] - 70)), (int(g[0]), int(g[1] + 70)), 0.5, 2, cv2.LINE_AA)
    rgb[:] = rgb + (PAPER * lay[..., None] + MAG * cv2.GaussianBlur(lay, (0, 0), 14)[..., None] * 2.0)
    for px, py in PARTS:                                 # pulse rings when the glint reaches a part
        pd = np.argmin(np.hypot(pts[:, 0] - px, pts[:, 1] - py))
        sp = seg[pd] / L; lag = (u - sp) % 1.0
        if lag < 0.25:
            c = to_screen(sh, t, (px, py)); k = H / tour_cam(sh, t)[0][2]
            rr = int((30 + 120 * lag / 0.25) * k * 0.6); a = float(1 - lag / 0.25)
            cv2.circle(rgb, (int(c[0]), int(c[1])), rr, tuple(float(v) * a for v in MAG), max(2, int(6 * a)), cv2.LINE_AA)

# ---------------------------------------------------------------- new transitions
def t_ball(cur, prev, u, t):
    """the thrown ball flies at the camera; the next shot is revealed inside it through a fisheye"""
    p0x, p0y, r0 = held_pos(S[_SI['held']]['t1'] - 1e-3)
    cx, cy = lerp(p0x, W / 2, eio(u)), lerp(p0y, H / 2, eio(u))
    r = lerp(r0, math.hypot(W, H) * 0.62, ein(u) ** 1.1)
    out = prev.copy()
    dx, dy = _xx - cx, _yy - cy; rr = np.sqrt(dx * dx + dy * dy); inside = (rr < r)[..., None].astype(np.float32)
    kf = 0.9 * (1 - u)                                   # fisheye strength, relaxes to none
    rn = np.clip(rr / max(r, 1), 0, 1); sc = np.power(rn + 1e-4, kf)
    lens = cv2.remap(cur, (cx + dx * sc).astype(np.float32), (cy + dy * sc).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    ballimg = out.copy(); draw_ball(ballimg, cx, cy, r, -t * 1400, 40, 0.0, 0.0, t)
    mix = clamp((u - 0.3) / 0.35)
    inner = ballimg * (1 - mix) + lens * mix
    out = out * (1 - inside) + inner * inside
    ring = np.exp(-((rr - r) / (6 + 20 * u)) ** 2)[..., None]
    return out + LIME * ring * 1.4 * (1 - u * 0.6)

ROPE_ANG = math.radians(-34)
def t_split(cur, prev, u):
    """sliced across the rope line; the pieces slide apart along the rope, then the split body slides together"""
    dx, dy = math.cos(ROPE_ANG), math.sin(ROPE_ANG)
    s = (_xx - W / 2) * dx + (_yy - H / 2) * dy
    K = 7; smin, smax = -1150.0, 1150.0; bw = (smax - smin) / K
    if u < 0.5:
        img, base, sep = prev, cur * 0.35, eio(u / 0.5) * 170
    else:
        img, base, sep = cur, V.DEEP + 0 * cur, (1 - eio((u - 0.5) / 0.5)) * 170
    out = base.copy()
    for k in range(K):
        o = (k - (K - 1) / 2) * sep
        sh_img = cv2.warpAffine(img, np.float32([[1, 0, o * dx], [0, 1, o * dy]]), (W, H), borderMode=cv2.BORDER_REFLECT)
        ss = s - o; m = ((ss >= smin + k * bw) & (ss < smin + (k + 1) * bw))
        out = np.where(m[..., None], sh_img, out)
        edge = np.exp(-((ss - (smin + k * bw)) / 3.0) ** 2) * (np.abs(ss - (smin + k * bw)) < 12)
        out = out + MAG * (edge * 1.4 * math.sin(math.pi * u))[..., None]
    if 0.42 < u < 0.62: out = out + (PAPER - out) * (1 - abs(u - 0.52) / 0.1) * 0.6
    return out

D_TR = {'liquid': 0.7, 'swirl': 0.7, 'magnet': 0.7, 'slash': 0.45, 'zoom': 0.45, 'shatter': 0.6, 'glitch': 0.25,
        'whip': 0.35, 'halftone': 0.55, 'flash': 0.15, 'ball': b(1.6), 'split': 1.0}

# ---------------------------------------------------------------- frame
_SI = {s_.get('ball'): i for i, s_ in enumerate(S) if s_.get('ball')}
def shot_at(t):
    for i, s_ in enumerate(S):
        if s_['t0'] <= t < s_['t1']: return i
    return len(S) - 1

def render_shot(sh, t):
    rgb = V.render_shot(sh, t)
    bl = sh.get('ball')
    if bl == 'held': held_ball(rgb, sh, t)
    elif bl == 'arc': arc_ball(rgb, sh, t)
    elif bl == 'strip': strip_ball(rgb, sh, t)
    if sh.get('rope'):
        if t >= b(80): rgb = rope_cut(rgb, t)
        rope_lash(rgb, t)
    if sh.get('rope_glint'): rope_glint(rgb, sh, t)
    return rgb

def hud(rgb, t):
    if not (MAG0 <= t < b(46)): return
    a = clamp((t - MAG0) / 0.3) * clamp((b(46) - t) / 0.3); u = clamp((t - MAG0) / (MAG1 - MAG0)) ** 1.3
    x0, y0 = 70, 110; over = t >= MAG1
    blit(rgb, sprite('磁力  MAGNETIC FORCE', JP, 30, fill=(1, 1, 1), stroke=0.08, sfill=(0, 0, 0)), x0 + 190, y0, a=a)
    lit = int(round(u * 20))
    for i in range(20):
        col = (RED if (over or i >= 16) else VIOLET) if (i < lit or over) else hexc('#2A2433')
        if over and int(t * 8) % 2: col = PAPER
        xa = x0 + i * 22; bgp = rgb[y0 + 40, xa]
        cv2.rectangle(rgb, (xa, y0 + 26), (xa + 15, y0 + 58), tuple(float(c) * a + float(bgp[j]) * (1 - a) for j, c in enumerate(col)), -1)
    blit(rgb, sprite('OVERLOAD' if over else f'{int(u * 100):3d}%', MONO, 34, fill=tuple(RED) if over or u > 0.8 else (1, 1, 1),
                     stroke=0.1, sfill=(0, 0, 0)), x0 + 500, y0 + 42, a=a)

def frame_core(t):
    si = shot_at(t); sh = S[si]
    rgb = render_shot(sh, t)
    tr = sh.get('tr')
    if tr and si > 0 and t < sh['t0'] + D_TR[tr]:
        u = (t - sh['t0']) / D_TR[tr]; prev = render_shot(S[si - 1], t)
        if tr == 'ball': rgb = t_ball(rgb, prev, u, t)
        elif tr == 'split': rgb = t_split(rgb, prev, u)
        else: rgb = V.transition(rgb, prev, tr, u)
    if sh.get('scraps') and t < sh['t0'] + 1.6:          # the iron scraps rip into Tim
        V.particles(rgb, to_screen(sh, t, (480, 210)), t, sh['t0'], n=160)
    bump_k, bump_s = V.pulse(KICKS, t, 0.1), V.pulse(SNARES, t, 0.08)
    V.draw_menace(rgb, t, bump_k)
    V.draw_texts(rgb, t)
    hud(rgb, t)
    ox = oy = ca = 0.0; flash = 0.0
    for h in HITS:
        lt = t - h['t']
        if lt < 0 or lt > 1.2: continue
        if h['big'] and lt < 0.16:
            k = 1 - lt / 0.16; acc = rgb.copy()
            for i in range(1, 4):
                acc += cv2.warpAffine(rgb, cv2.getRotationMatrix2D((W / 2, H * 0.45), 0, 1 + 0.035 * k * i), (W, H), borderMode=cv2.BORDER_REFLECT)
            rgb = acc / 4
        if h['big'] and lt < 2 / FPS:
            l = rgb.mean(2, keepdims=True); bw = (l > 0.45).astype(np.float32); rgb = bw * PAPER + (1 - bw) * INK
        amp = (24 if h['big'] else 10) * math.exp(-lt * 7)
        ox += amp * math.sin(t * 71); oy += amp * math.cos(t * 53); ca += amp * 0.35
        flash = max(flash, (0.55 if h['big'] else 0.2) * math.exp(-lt / 0.09))
    z = 1.0 + 0.012 * min(bump_k, 1.5) + 0.006 * min(bump_s, 1.5)
    ca += 2 * min(bump_s, 1)
    if abs(z - 1) > 1e-3 or abs(ox) + abs(oy) > 0.3:
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z); M[:, 2] += (ox, oy)
        rgb = cv2.warpAffine(rgb, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    if ca > 1.5:
        d = int(min(ca, 16)); rgb[..., 0] = np.roll(rgb[..., 0], d, 1); rgb[..., 2] = np.roll(rgb[..., 2], -d, 1)
    if flash > 0.01: rgb = rgb + (PAPER - rgb) * min(flash, 1)
    if t < 0.4: rgb = rgb * (t / 0.4) ** 0.7                 # fade up from black
    for d0, d1 in DIM:
        if d0 <= t < d1: rgb = rgb * 0.12
    sm = cv2.resize(rgb, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    br = cv2.GaussianBlur(np.maximum(sm - 0.72, 0), (0, 0), 8)
    return (np.clip(rgb + cv2.resize(br, (W, H), interpolation=cv2.INTER_LINEAR) * 0.8, 0, 1) * V.VIG).astype(np.float32)

def frame(fi):
    t = fi / FPS
    rgb = V.tbc(frame_core(V.FREEZE - 1 / FPS), t) if t >= V.FREEZE else frame_core(t)
    rgb = (rgb + V.GRAIN[fi % 4]) * clamp((DUR - t) / 0.5)
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)

def stills(times):
    d = os.path.join(HERE, 'stills_v3'); os.makedirs(d, exist_ok=True); th = []
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
    tmp = os.path.join(HERE, '_v3_video.mp4'); out = os.path.join(ROOT, 'mountain-tim-short-v3.mp4')
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p',
                          '-movflags', '+faststart', tmp], stdin=subprocess.PIPE)
    with Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        for i, fr in enumerate(pool.imap(frame, range(N), chunksize=3)):
            p.stdin.write(fr.tobytes())
            if i % 120 == 0: print(f'frame {i}/{N}', flush=True)
    p.stdin.close(); p.wait()
    if p.returncode: raise SystemExit(f'ffmpeg video failed {p.returncode}')
    subprocess.run([ff, '-y', '-v', 'error', '-i', tmp, '-i', os.path.join(HERE, 'music_v3.wav'), '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-af', 'loudnorm=I=-13:TP=-1.0:LRA=9,aresample=48000', '-c:a', 'aac', '-b:a', '192k',
                    '-t', f'{DUR:.3f}', '-movflags', '+faststart', out], check=True)
    os.remove(tmp); print('wrote', out)

if __name__ == '__main__':
    if sys.argv[1] == 'stills': stills([float(x) for x in sys.argv[2].split(',')])
    else: video()
