"""Character cut-outs for the v2 Short -> ../cutouts/<name>.png (RGBA at 2x, edges anti-aliased).

B/W art: hand polygon, then white paper connected to the outside of the polygon band is removed so the edge follows
the line art. Colour cover: GrabCut seeded with a polygon (definite fg inside an eroded copy, bg outside a dilated one),
then split into Tao / Al layers so they can move independently.
Usage: python extract.py   (writes cutouts + check/cutouts.jpg preview)
"""
import os, numpy as np, cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PAN, OUTD = os.path.join(os.path.dirname(HERE), 'panels'), os.path.join(os.path.dirname(HERE), 'cutouts')
os.makedirs(OUTD, exist_ok=True); os.makedirs(os.path.join(HERE, 'check'), exist_ok=True)
S = 2   # supersample

def load(n, mode='RGB'): return np.asarray(Image.open(os.path.join(PAN, n + '.webp')).convert(mode))

def poly_mask(shape, poly, s=1):
    m = np.zeros(shape, np.uint8)
    cv2.fillPoly(m, [np.int32(np.round(np.float32(poly) * s * 16))], 255, cv2.LINE_AA, 4)
    return m

def snap(gray, poly, close=3, thr=200):
    """background = paper regions (after closing small gaps in the line art) that reach the outside of the polygon."""
    pm = poly_mask(gray.shape, poly)
    ink = (gray <= thr).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * close + 1, 2 * close + 1))
    ink_c = cv2.dilate(ink, k)                                  # seal gaps so enclosed skin/cloth stays
    region = ((ink_c == 0) | (pm == 0)).astype(np.uint8)        # outside the polygon counts as background too
    n, lab = cv2.connectedComponents(region)
    outside = np.unique(lab[pm == 0]); outside = outside[outside != 0]
    bg = np.isin(lab, outside).astype(np.uint8)
    bg = cv2.dilate(bg, k) & (ink == 0)                         # give back the gap margin, never eat ink
    fg = ((pm > 0) | (cv2.dilate(pm, k) > 0) & (ink == 1)) & (bg == 0)
    fg = fg.astype(np.uint8) * 255
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
    if n > 1: fg = np.where(lab == 1 + np.argmax(st[1:, 4]), 255, 0).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

def save(name, rgb, fg, crop_pad=4):
    ys, xs = np.nonzero(fg)
    x0, x1 = max(0, xs.min() - crop_pad), min(fg.shape[1], xs.max() + crop_pad)
    y0, y1 = max(0, ys.min() - crop_pad), min(fg.shape[0], ys.max() + crop_pad)
    im = rgb[y0:y1, x0:x1].astype(np.float32) / 255; a = fg[y0:y1, x0:x1].astype(np.float32) / 255
    up = cv2.resize(im, None, fx=S, fy=S, interpolation=cv2.INTER_LANCZOS4)
    bl = cv2.GaussianBlur(up, (0, 0), 1.1); up = np.clip(up + 0.55 * (up - bl), 0, 1)
    # alpha: upsample the hard mask smoothly, then a 0.7 px feather -> clean anti-aliased edge
    au = cv2.resize(a, None, fx=S, fy=S, interpolation=cv2.INTER_CUBIC)
    au = np.clip(cv2.GaussianBlur(au, (0, 0), 0.7), 0, 1)
    if up.ndim == 2: up = np.repeat(up[..., None], 3, 2)
    Image.fromarray((np.dstack([up, au]) * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUTD, name + '.png'))
    print(name, 'origin', (x0, y0), 'size', (x1 - x0, y1 - y0))
    return (x0, y0)

CUTS_BW = {
    'tao_gun': ('19', [(1165, 5), (1222, 0), (1248, 22), (1252, 75), (1240, 125), (1238, 165), (1268, 198), (1290, 188),
                       (1296, 150), (1322, 138), (1362, 150), (1378, 182), (1382, 222), (1402, 262), (1432, 300),
                       (1462, 330), (1490, 360), (1499, 420), (1499, 612), (1238, 612), (1232, 520), (1240, 420),
                       (1250, 330), (1245, 282), (1215, 222), (1195, 178), (1180, 132), (1168, 80)]),
    'tao_point': ('08', [(298, 1000), (328, 900), (360, 820), (420, 770), (500, 755), (580, 765), (650, 800), (690, 860),
                         (702, 930), (760, 960), (818, 990), (845, 1050), (862, 1112), (900, 1180), (940, 1240),
                         (958, 1280), (958, 1399), (330, 1399), (318, 1330), (278, 1280), (268, 1200), (273, 1100),
                         (284, 1040)]),
    'al_grin': ('15', [(520, 40), (560, 15), (640, 8), (702, 28), (742, 80), (748, 150), (722, 230), (782, 250),
                       (842, 300), (862, 380), (862, 618), (432, 618), (432, 330), (472, 268), (530, 238), (502, 200),
                       (482, 140), (490, 80)]),
}
ORIG = {}
for name, (p, poly) in CUTS_BW.items():
    g = load(p, 'L'); fg = snap(g, poly)
    ORIG[name] = save(name, np.repeat(g[..., None], 3, 2), fg)

# colour cover duo -> GrabCut
rgb = load('01'); bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
duo = [(170, 1399), (168, 760), (205, 700), (262, 640), (300, 590), (318, 520), (350, 470), (410, 452), (462, 470),
       (500, 520), (528, 470), (560, 420), (600, 380), (612, 320), (650, 282), (700, 262), (770, 262), (822, 292),
       (845, 352), (842, 420), (880, 470), (928, 520), (958, 600), (958, 1399)]
pm = poly_mask(rgb.shape[:2], duo)
k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41))
mask = np.full(rgb.shape[:2], cv2.GC_BGD, np.uint8)
mask[cv2.dilate(pm, k) > 0] = cv2.GC_PR_BGD; mask[pm > 0] = cv2.GC_PR_FGD
mask[cv2.erode(pm, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (81, 81))) > 0] = cv2.GC_FGD
mask[1165:1345, 598:935] = cv2.GC_BGD                       # scanlation credit box
b_, f_ = np.zeros((1, 65)), np.zeros((1, 65))
cv2.grabCut(bgr, mask, None, b_, f_, 6, cv2.GC_INIT_WITH_MASK)
fg = np.where((mask == 1) | (mask == 3), 255, 0).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
fg = np.where(lab == 1 + np.argmax(st[1:, 4]), 255, 0).astype(np.uint8)
fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
ORIG['duo'] = save('duo', rgb, fg)
al_side = poly_mask(rgb.shape[:2], [(560, 200), (959, 200), (959, 1399), (640, 1399), (620, 1150), (560, 1000),
                                    (540, 880), (560, 700), (540, 560), (520, 470)])
ORIG['al_cover'] = save('al_cover', rgb, fg & al_side)
ORIG['tao_cover'] = save('tao_cover', rgb, fg & ~al_side)

# preview on a pink + dot background
tiles = []
for name in ['tao_gun', 'tao_point', 'al_grin', 'duo', 'al_cover', 'tao_cover']:
    a = np.asarray(Image.open(os.path.join(OUTD, name + '.png')), np.float32) / 255
    h, w = a.shape[:2]; yy, xx = np.mgrid[0:h, 0:w]
    bg = np.ones((h, w, 3)) * np.array([0.95, 0.3, 0.5]); bg[((xx % 40 - 20) ** 2 + (yy % 40 - 20) ** 2) < 30] = 1
    v = bg * (1 - a[..., 3:]) + a[..., :3] * a[..., 3:]
    v = cv2.resize((v * 255).astype(np.uint8), (int(w * 600 / h), 600), interpolation=cv2.INTER_AREA)
    cv2.putText(v, name, (4, 18), 0, 0.6, (0, 0, 0), 2); tiles.append(cv2.cvtColor(v, cv2.COLOR_RGB2BGR))
cv2.imwrite(os.path.join(HERE, 'check', 'cutouts.jpg'), np.hstack(tiles))
import json; json.dump({k: [int(v[0]), int(v[1])] for k, v in ORIG.items()}, open(os.path.join(OUTD, 'origins.json'), 'w'))
