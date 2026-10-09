"""@inkframez brand kit, built around the logo mark (三 panels: 墨 / red ink splash / INKFRAMEZ).

Outputs (in this folder):
  watermark.png           transparent corner watermark (mark + @inkframez), for overlaying on edits
  endcard.mp4             1.5 s vertical end card (1080x1920, 30 fps) with a synthesised ink-hit sound
  banner.png              YouTube banner 2560x1440 (everything important inside the 1546x423 safe area)
Usage: python make_brand.py
"""
import os, math, wave, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FD = 'C:/Windows/Fonts/' if os.name == 'nt' else os.path.join(os.path.dirname(HERE), 'fonts') + '/'
RED = (204, 18, 28); PAPER = (238, 238, 236); INK = (8, 8, 10)

def clamp(u): return min(max(u, 0.0), 1.0)
def eout(u): u = clamp(u); return 1 - (1 - u) ** 3
def eback(u): u = clamp(u); c = 1.9; return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2

def splash_mask(size, cx, cy, r, seed=9, grow=1.0):
    rng = np.random.default_rng(seed); m = np.zeros((size[1], size[0]), np.float32)
    if grow <= 0: return m
    cv2.circle(m, (int(cx), int(cy)), int(r * min(1, grow * 1.3)), 1, -1, cv2.LINE_AA)
    for _ in range(40):
        a = rng.uniform(0, 2 * np.pi); d = rng.uniform(r * 0.6, r * 1.9) * grow; rr = rng.uniform(r * 0.05, r * 0.28)
        cv2.circle(m, (int(cx + d * math.cos(a)), int(cy + d * math.sin(a))), max(1, int(rr * min(1, grow * 1.5))), 1, -1, cv2.LINE_AA)
    return cv2.GaussianBlur(m, (0, 0), 1.2)

def draw_mark(img, x, y, s, p=1.0, text=True):
    """mark with top-left at (x, y), unit width s (mark is ~1.0 s wide, ~0.97 s tall). p = 0..1 build-in progress."""
    d = ImageDraw.Draw(img)
    boxes = [(0, 0, 0.516, 0.516), (0.565, 0, 1.0, 0.516), (0, 0.565, 1.0, 0.97)]
    lw = max(2, int(s * 0.029))
    if not text: boxes = boxes[:2]
    for i, (a, b_, c, e) in enumerate(boxes):
        u = eout((p - i * 0.12) / 0.3)
        if u <= 0: continue
        x0, y0, x1, y1 = x + a * s, y + b_ * s, x + c * s, y + e * s
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; k = 0.6 + 0.4 * u
        d.rectangle([cx - (cx - x0) * k, cy - (cy - y0) * k, cx + (x1 - cx) * k, cy + (y1 - cy) * k], outline=PAPER, width=lw)
    u = eback((p - 0.35) / 0.3)
    if u > 0:
        f = ImageFont.truetype(FD + 'YuGothB.ttc', max(8, int(s * 0.34 * u)))
        d.text((x + 0.258 * s, y + 0.25 * s), '墨', font=f, fill=PAPER, anchor='mm')
    g = clamp((p - 0.5) / 0.25)
    if g > 0:
        arr = np.asarray(img).astype(np.float32)
        m = splash_mask(img.size, x + 0.78 * s, y + 0.255 * s, 0.13 * s, grow=g)[..., None]
        if arr.shape[2] == 4:
            arr[..., :3] = arr[..., :3] * (1 - m) + np.float32(RED) * m; arr[..., 3:] = np.maximum(arr[..., 3:], m * 255)
        else: arr = arr * (1 - m) + np.float32(RED) * m
        img.paste(Image.fromarray(arr.astype(np.uint8), img.mode))
        d = ImageDraw.Draw(img)
    if text:
        t = 'INKFRAMEZ'; n = int(len(t) * clamp((p - 0.6) / 0.3))
        if n > 0:
            f = ImageFont.truetype(FD + 'impact.ttf', int(s * 0.21))
            full = f.getlength(t); cx = x + 0.5 * s - full / 2
            d.text((cx, y + 0.767 * s), t[:n], font=f, fill=PAPER, anchor='lm')
    return img

# ---------------------------------------------------------------- watermark
def watermark():
    Wd, Hd = 560, 170
    img = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0))
    mk = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0))
    draw_mark(mk, 10, 45, 150, text=False)
    d = ImageDraw.Draw(mk); f = ImageFont.truetype(FD + 'impact.ttf', 64)
    d.text((182, 85), '@inkframez', font=f, fill=PAPER, anchor='lm')
    a = np.asarray(mk).astype(np.float32)
    sh = cv2.GaussianBlur(a[..., 3], (0, 0), 5) * 0.75                   # soft dark halo -> readable on white pages
    out = np.zeros_like(a); out[..., 3] = np.maximum(sh, a[..., 3])
    al = a[..., 3:4] / 255; out[..., :3] = a[..., :3] * al + np.float32(INK) * (1 - al)
    out[..., 3] = out[..., 3] * 0.85                                       # slightly see-through
    Image.fromarray(out.astype(np.uint8), 'RGBA').save(os.path.join(HERE, 'watermark.png'))

# ---------------------------------------------------------------- end card
def endcard():
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    W, H, FPS, DUR = 1080, 1920, 30, 1.5
    tmpv = os.path.join(HERE, '_ec.mp4'); wav = os.path.join(HERE, '_ec.wav'); out = os.path.join(HERE, 'endcard.mp4')
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', tmpv], stdin=subprocess.PIPE)
    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        img = Image.new('RGB', (W, H), INK)
        draw_mark(img, 230, 600, 620, p=clamp(t / 0.95))
        d = ImageDraw.Draw(img); f = ImageFont.truetype(FD + 'segoeuisl.ttf' if os.path.exists(FD + 'segoeuisl.ttf') else FD + 'arial.ttf', 44)
        a = clamp((t - 0.85) / 0.3)
        if a > 0: d.text((W / 2, 1300), 'follow for more edits', font=f, fill=tuple(int(c * a) for c in PAPER), anchor='mm')
        arr = np.asarray(img).astype(np.float32)
        fl = math.exp(-max(0, t - 0.45) / 0.06) * 0.6 if t >= 0.45 else 0          # flash on the splash
        arr = arr + (255 - arr) * fl
        p.stdin.write(np.clip(arr, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()
    # sound: brush swish -> ink hit on the splash -> soft tail
    SR = 48000; n = int(SR * DUR); rng = np.random.default_rng(3); t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    sw = np.convolve(noise, np.ones(30) / 30, 'same') * np.clip(t / 0.35, 0, 1) * np.exp(-np.clip(t - 0.4, 0, None) * 30) * 0.35
    h = t - 0.47; hit = np.where(h >= 0, np.sin(2 * np.pi * (55 + 90 * np.exp(-np.maximum(h, 0) * 25)) * np.maximum(h, 0)) *
                                np.exp(-np.maximum(h, 0) * 6), 0) * 0.9
    drop = np.where(h >= 0, np.convolve(noise, np.ones(6) / 6, 'same') * np.exp(-np.maximum(h, 0) * 18), 0) * 0.5
    s = np.tanh(1.4 * (sw + hit + drop)); s *= np.clip((DUR - t) / 0.15, 0, 1)
    st = (np.stack([s, s], 1) / np.abs(s).max() * 0.8 * 32767).astype(np.int16)
    with wave.open(wav, 'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())
    subprocess.run([ff, '-y', '-v', 'error', '-i', tmpv, '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                    '-shortest', '-movflags', '+faststart', out], check=True)
    os.remove(tmpv); os.remove(wav)

# ---------------------------------------------------------------- banner
def banner():
    W, H = 2560, 1440
    img = Image.new('RGB', (W, H), INK); d = ImageDraw.Draw(img)
    # faint manga-panel grid filling the full banner (visible on TV), kept dim
    rng = np.random.default_rng(5)
    for _ in range(60):
        x0, y0 = rng.integers(-100, W), rng.integers(-100, H); w, h = rng.integers(160, 520), rng.integers(120, 420)
        if x0 < (W + 1546) // 2 + 40 and x0 + w > (W - 1546) // 2 - 40 and y0 < (H + 423) // 2 + 40 and y0 + h > (H - 423) // 2 - 40: continue
        d.rectangle([x0, y0, x0 + w, y0 + h], outline=(34, 34, 38), width=6)
    # safe area 1546x423 centred: mark on the left, text on the right
    sx, sy = (W - 1546) // 2, (H - 423) // 2
    draw_mark(img, sx + 40, sy + 18, 400)
    d = ImageDraw.Draw(img)
    d.text((sx + 520, sy + 120), 'manga panels,', font=ImageFont.truetype(FD + 'impact.ttf', 104), fill=PAPER, anchor='lm')
    d.text((sx + 520, sy + 232), 'brought to life', font=ImageFont.truetype(FD + 'impact.ttf', 104), fill=RED, anchor='lm')
    d.text((sx + 524, sy + 335), 'ROMANCE  ·  HORROR  ·  ACTION', font=ImageFont.truetype(FD + 'bahnschrift.ttf', 46),
           fill=(170, 170, 176), anchor='lm')
    d.text((sx + 524, sy + 395), '@inkframez', font=ImageFont.truetype(FD + 'bahnschrift.ttf', 40), fill=(120, 120, 126), anchor='lm')
    img.save(os.path.join(HERE, 'banner.png'))
    # preview with the safe area outlined
    pv = img.copy(); ImageDraw.Draw(pv).rectangle([sx, sy, sx + 1546, sy + 423], outline=(0, 200, 255), width=4)
    pv.resize((1280, 720)).save(os.path.join(HERE, 'banner_preview.jpg'))

if __name__ == '__main__':
    watermark(); banner(); endcard(); print('done')
