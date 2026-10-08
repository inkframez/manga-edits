"""Character cut-outs for Toki Doki -> ../cutouts/<name>.png (RGBA, 2x upscaled).
colour art: GrabCut (rect or polygon-initialised). B/W art: hand polygon, then the edge band is snapped to the
line art by removing white paper that is connected to the outside."""
import os, numpy as np, cv2
from PIL import Image
PAN, OUTD = '../panels', '../cutouts'
os.makedirs(OUTD, exist_ok=True)
def load(n):
    fn = [f for f in os.listdir(PAN) if f.startswith(n + '.')][0]
    return np.asarray(Image.open(os.path.join(PAN, fn)).convert('RGB'))
def disp(pts, ox, oy, sc): return [(ox + x / sc, oy + y / sc) for x, y in pts]
CUTS = {
    'hatsu_color': dict(p='02', rect=[150, 230, 700, 1170], method='grab'),
    'hato_color': dict(p='02', method='grabpoly', poly=disp(
        [(150, 110), (165, 60), (200, 35), (250, 30), (300, 40), (330, 70), (345, 110), (340, 160), (325, 200), (330, 240),
         (318, 290), (300, 320), (330, 340), (420, 380), (445, 410), (450, 500), (452, 640), (40, 640), (35, 560), (45, 450),
         (60, 400), (140, 345), (190, 330), (200, 290), (185, 250), (170, 215), (155, 170)], 1000, 40, 0.6)),
    'hatsu_stand': dict(p='08', method='snap', poly=disp(
        [(120, 10), (160, 8), (185, 30), (190, 70), (205, 110), (225, 170), (235, 240), (240, 300), (232, 340), (200, 345),
         (195, 400), (185, 470), (165, 480), (160, 560), (160, 650), (165, 700), (172, 740), (140, 748), (110, 748), (95, 738),
         (100, 700), (105, 640), (108, 560), (100, 480), (80, 470), (78, 400), (70, 345), (45, 340), (40, 290), (48, 200),
         (70, 120), (90, 70), (98, 30)], 360, 500, 0.85)),
    'hato_shout': dict(p='06', method='snap', poly=disp(
        [(150, 100), (200, 40), (260, 10), (300, 2), (480, 2), (500, 60), (480, 130), (470, 200), (455, 250), (480, 260),
         (560, 300), (650, 340), (700, 380), (740, 460), (760, 490), (600, 490), (560, 500), (470, 560), (330, 620),
         (275, 620), (268, 540), (272, 430), (260, 300), (225, 260), (215, 220), (205, 180), (170, 150)], 47, 355, 0.85)),
    'hatsu_smile': dict(p='12', method='snap', poly=disp(
        [(60, 2), (350, 2), (370, 60), (395, 170), (405, 300), (410, 440), (440, 470), (470, 520), (495, 600), (500, 670),
         (460, 690), (440, 740), (430, 800), (215, 800), (215, 640), (190, 500), (140, 455), (60, 450), (2, 430), (2, 60)],
        0, 0, 0.85)),
    'hato_smile': dict(p='14', method='snap', poly=[(380, 345), (450, 330), (560, 335), (650, 345), (700, 380), (715, 470),
        (712, 600), (690, 680), (670, 740), (700, 800), (720, 870), (365, 870), (380, 800), (420, 760), (420, 700),
        (390, 640), (372, 560), (370, 450)]),
    'couple': dict(p='16', method='snap', poly=[(492, 522), (512, 516), (536, 540), (540, 575), (548, 620), (552, 700),
        (556, 780), (562, 850), (560, 868), (455, 868), (452, 840), (462, 760), (468, 720), (458, 700), (452, 690),
        (424, 690), (420, 650), (432, 620), (462, 600), (490, 580), (488, 545)]),
}
def snap(gray, poly, band=10):
    h, w = gray.shape
    pm = np.zeros((h, w), np.uint8); cv2.fillPoly(pm, [np.int32(np.round(np.float32(poly)))], 255)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * band + 1, 2 * band + 1))
    outer = cv2.dilate(pm, k)
    white = (gray > 200).astype(np.uint8)
    # region that can be eaten: outside the dilated poly, plus white paper inside the band
    edible = ((outer == 0) | ((white == 1) & (cv2.erode(pm, k) == 0))).astype(np.uint8)
    n, lab = cv2.connectedComponents(edible)
    outside_labels = set(np.unique(lab[outer == 0])) - {0}
    eaten = np.isin(lab, list(outside_labels))
    fg = ((outer > 0) & ~eaten).astype(np.uint8) * 255
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
    if n > 1: fg = np.where(lab == 1 + np.argmax(st[1:, 4]), 255, 0).astype(np.uint8)
    return fg
tiles = []
for name, c in CUTS.items():
    rgb = load(c['p']); g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    if c['method'] == 'grab':
        x, y, w, h = c['rect']; im = rgb[y:y + h, x:x + w]
        mask = np.zeros(im.shape[:2], np.uint8); b_, f_ = np.zeros((1, 65)), np.zeros((1, 65))
        cv2.grabCut(cv2.cvtColor(im, cv2.COLOR_RGB2BGR), mask, (6, 6, w - 12, h - 12), b_, f_, 6, cv2.GC_INIT_WITH_RECT)
        fgc = np.where((mask == 1) | (mask == 3), 255, 0).astype(np.uint8)
        fg = np.zeros(g.shape, np.uint8); fg[y:y + h, x:x + w] = fgc
        n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
        fg = np.where(lab == 1 + np.argmax(st[1:, 4]), 255, 0).astype(np.uint8)
    elif c['method'] == 'grabpoly':
        pm = np.zeros(g.shape, np.uint8); cv2.fillPoly(pm, [np.int32(np.round(np.float32(c['poly'])))], 255)
        k = np.ones((25, 25), np.uint8)
        mask = np.full(g.shape, cv2.GC_BGD, np.uint8)
        mask[cv2.dilate(pm, k) > 0] = cv2.GC_PR_BGD; mask[pm > 0] = cv2.GC_PR_FGD; mask[cv2.erode(pm, k) > 0] = cv2.GC_FGD
        b_, f_ = np.zeros((1, 65)), np.zeros((1, 65))
        cv2.grabCut(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), mask, None, b_, f_, 5, cv2.GC_INIT_WITH_MASK)
        fg = np.where((mask == 1) | (mask == 3), 255, 0).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
        fg = np.where(lab == 1 + np.argmax(st[1:, 4]), 255, 0).astype(np.uint8)
    else:
        fg = snap(g, c['poly'])
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    ys, xs = np.nonzero(fg); x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    im = rgb[y0:y1, x0:x1].astype(np.float32) / 255; a = fg[y0:y1, x0:x1].astype(np.float32) / 255
    s = 2
    up = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_LANCZOS4)
    bl = cv2.GaussianBlur(up, (0, 0), 1.2); up = np.clip(up + 0.5 * (up - bl), 0, 1)
    au = cv2.GaussianBlur(cv2.resize(a, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR), (0, 0), 0.8)
    if c['p'] != '02':   # B/W: clean paper to white
        up = np.clip((up - 0.03) / 0.9, 0, 1)
    rgba = np.dstack([up, au]); Image.fromarray((rgba * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUTD, name + '.png'))
    bg = np.ones_like(up) * np.array([0.98, 0.74, 0.82])
    yy, xx = np.mgrid[0:up.shape[0], 0:up.shape[1]]; dots = ((xx % 40 - 20) ** 2 + (yy % 40 - 20) ** 2) < 49
    bg[dots] = [1, 1, 1]
    vis = bg * (1 - au[..., None]) + up * au[..., None]
    hh = 420; vis = cv2.resize((vis * 255).astype(np.uint8), (int(vis.shape[1] * hh / vis.shape[0]), hh))
    cv2.putText(vis, name, (4, 16), 0, 0.5, (0, 0, 0), 1); tiles.append(cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
    print(name, rgba.shape)
cv2.imwrite('check/cutouts.jpg', np.hstack(tiles))
