"""Profile pictures for @inkframez -> pfp_*.png (1080x1080, circle-safe)."""
import os, math, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.abspath(__file__)); M = os.path.dirname(ROOT)
S = 1080; FD = 'C:/Windows/Fonts/'
def pg(p): return np.asarray(Image.open(os.path.join(M, p)).convert('L'), np.float32) / 255
def crop(a, x, y, w, h, out):
    c = a[y:y + h, x:x + w]; c = cv2.resize(c, out, interpolation=cv2.INTER_LANCZOS4)
    bl = cv2.GaussianBlur(c, (0, 0), 1.2); return np.clip((c + 0.5 * (c - bl) - 0.04) / 0.9, 0, 1)
RED = np.array([0.80, 0.07, 0.11], np.float32); INK = np.array([0.03, 0.03, 0.04], np.float32)
yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
def splash(seed, cx, cy, r):
    rng = np.random.default_rng(seed); m = np.zeros((S, S), np.float32)
    cv2.circle(m, (cx, cy), r, 1, -1, cv2.LINE_AA)
    for _ in range(40):
        a = rng.uniform(0, 2 * np.pi); d = rng.uniform(r * 0.6, r * 1.9); rr = int(rng.uniform(4, r * 0.28))
        cv2.circle(m, (int(cx + d * math.cos(a)), int(cy + d * math.sin(a))), rr, 1, -1, cv2.LINE_AA)
    return cv2.GaussianBlur(m, (0, 0), 1.5)
def label(img, text, y, size, col=(255, 255, 255), stroke=0):
    d = ImageDraw.Draw(img); f = ImageFont.truetype(FD + 'impact.ttf', size)
    d.text((S / 2, y), text, font=f, fill=col, anchor='mm', stroke_width=stroke, stroke_fill=(8, 8, 10))
def finish(rgb, name, text=True):
    im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
    if text: label(im, 'INKFRAMEZ', 860, 118, stroke=6)
    im.save(os.path.join(ROOT, name)); return im

# A: the Ibitsu eye inside a tilted manga panel, red ink splash
eye = crop(pg('04-ibitsu/panels/11.webp'), 390, 770, 300, 300, (640, 640))
rgb = np.ones((S, S, 3), np.float32) * 0.94
sp = splash(3, 690, 360, 120)[..., None]; rgb = rgb * (1 - sp) + RED * sp
panel = np.ones((S, S), np.float32) * 0; pm = np.zeros((S, S), np.uint8)
M_ = cv2.getRotationMatrix2D((320, 320), -6, 1.0); M_[:, 2] += (S / 2 - 320, 470 - 320)
ev = cv2.warpAffine(eye, M_, (S, S), borderValue=1.0)
q = np.float32([[0, 0], [640, 0], [640, 640], [0, 640]]) @ M_[:, :2].T + M_[:, 2]
cv2.fillConvexPoly(pm, np.int32(q * 16), 255, cv2.LINE_AA, 4); m = (pm / 255.0)[..., None]
sh = np.roll(np.roll(m, 18, 0), 18, 1); rgb = rgb * (1 - sh) + INK * sh
border = cv2.dilate(pm, np.ones((25, 25), np.uint8)) / 255.0
rgb = rgb * (1 - border[..., None]) + INK * border[..., None]
rgb = rgb * (1 - m) + ev[..., None] * m
finish(rgb, 'pfp_a_eye.png')
# B: Tao (Gokurakugai) in her sunglasses, red slab
tao = crop(pg('03-gokurakugai-sanbandoori-no-ken/panels/08.webp'), 250, 790, 440, 440, (S, S))
rgb = np.repeat(tao[..., None], 3, 2) * 0.95 + 0.02
band = (np.abs((yy - 860) + 0.12 * (xx - S / 2)) < 95)[..., None]
rgb = np.where(band, RED, rgb)
finish(rgb, 'pfp_b_tao.png')
# C: pure mark - black ink, white panel frames, red brush dot
rgb = np.ones((S, S, 3), np.float32) * INK
im = Image.fromarray((rgb * 255).astype(np.uint8)); d = ImageDraw.Draw(im)
for (x0, y0, x1, y1) in [(230, 200, 550, 520), (580, 200, 850, 520), (230, 550, 850, 800)]:
    d.rectangle([x0, y0, x1, y1], outline=(238, 238, 236), width=18)
rgb = np.asarray(im, np.float32) / 255
sp = splash(9, 715, 360, 80)[..., None]; rgb = rgb * (1 - sp) + RED * sp
im = Image.fromarray((rgb * 255).astype(np.uint8)); d = ImageDraw.Draw(im)
d.text((390, 360), '墨', font=ImageFont.truetype(FD + 'YuGothB.ttc', 210), fill=(238, 238, 236), anchor='mm')
label(im, 'INKFRAMEZ', 676, 128); im.save(os.path.join(ROOT, 'pfp_c_mark.png'))
# preview: how they look as circles at small size
prev = []
for n in ('pfp_a_eye.png', 'pfp_b_tao.png', 'pfp_c_mark.png'):
    a = np.asarray(Image.open(os.path.join(ROOT, n)).convert('RGB'))[..., ::-1].copy()
    c = np.zeros_like(a); mk = np.zeros((S, S), np.uint8); cv2.circle(mk, (S // 2, S // 2), S // 2, 255, -1)
    c[mk > 0] = a[mk > 0]; c[mk == 0] = 255
    prev.append(np.hstack([cv2.resize(c, (360, 360), interpolation=cv2.INTER_AREA),
                           np.pad(cv2.resize(c, (90, 90), interpolation=cv2.INTER_AREA), ((0, 270), (10, 10), (0, 0)), constant_values=255)]))
cv2.imwrite(os.path.join(ROOT, 'preview.jpg'), np.hstack(prev))
