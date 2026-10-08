import os, numpy as np, cv2
from PIL import Image
PAN = '../panels'; OUTD = '../cutouts'
def load(n, color):
    fn = [f for f in os.listdir(PAN) if f.startswith(n + '.')][0]
    return np.asarray(Image.open(os.path.join(PAN, fn)).convert('RGB'))
C = {  # name: (page, crop x,y,w,h)
    'hatsu_color': ('02', [150, 230, 700, 1170]), 'hato_color': ('02', [1010, 60, 710, 1020]),
    'hatsu_stand': ('08', [380, 505, 270, 895]), 'hatsu_smile': ('12', [0, 0, 620, 1000]),
    'hatsu_laugh': ('08', [0, 1000, 420, 400]), 'hato_smile': ('14', [370, 330, 340, 540]),
    'hato_shout': ('06', [47, 355, 912, 513]),
}
tiles = []
for name, (p, (x, y, w, h)) in C.items():
    im = load(p, True)[y:y + h, x:x + w].copy()
    mask = np.zeros(im.shape[:2], np.uint8)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    m = 6; rect = (m, m, w - 2 * m, h - 2 * m)
    cv2.grabCut(cv2.cvtColor(im, cv2.COLOR_RGB2BGR), mask, rect, bgd, fgd, 6, cv2.GC_INIT_WITH_RECT)
    fg = np.where((mask == 1) | (mask == 3), 255, 0).astype(np.uint8)
    n_, lab, st, _ = cv2.connectedComponentsWithStats(fg)
    if n_ > 1:
        big = 1 + np.argmax(st[1:, 4]); fg = np.where(lab == big, 255, 0).astype(np.uint8)
    rgba = np.dstack([im, fg]); Image.fromarray(rgba).save(os.path.join(OUTD, f'try_{name}.png'))
    vis = im.copy().astype(np.float32); vis[fg == 0] = vis[fg == 0] * 0.15 + np.array([255, 120, 160]) * 0.85
    vis = cv2.resize(vis.astype(np.uint8), (int(w * 360 / h), 360))
    cv2.putText(vis, name, (4, 16), 0, 0.5, (0, 0, 0), 1); tiles.append(cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
cv2.imwrite('check/grabcut_try.jpg', np.hstack(tiles))
print('ok')
