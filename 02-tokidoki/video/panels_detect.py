"""Detect panel rectangles on each page; writes panels.json + panels_contact.jpg for review."""
import os, json, numpy as np, cv2
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); PAN = os.path.join(os.path.dirname(HERE), 'panels')
out = {}; sheets = []
for fn in sorted(os.listdir(PAN)):
    if not fn[:2].isdigit() or fn.startswith('00'): continue
    n = fn[:2]
    rgb = np.asarray(Image.open(os.path.join(PAN, fn)).convert('RGB'))
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY); h, w = g.shape
    white = (g > 235).astype(np.uint8)
    # gutters = white connected to the page border
    ff = np.pad(white, 1, constant_values=1); mask = np.zeros((h + 4, w + 4), np.uint8)
    cv2.floodFill(ff, mask, (0, 0), 2)
    gut = (ff[1:-1, 1:-1] == 2)
    gut = cv2.morphologyEx(gut.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    content = (1 - gut).astype(np.uint8)
    content = cv2.morphologyEx(content, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    nlab, lab, st, _ = cv2.connectedComponentsWithStats(content)
    rects = []
    for i in range(1, nlab):
        x, y, ww, hh, a = st[i]
        if a > 0.02 * h * w and ww > 80 and hh > 80: rects.append([int(x), int(y), int(ww), int(hh)])
    rects.sort(key=lambda r: (r[1] // 60, -r[0]))   # rows top->bottom, right->left (manga order)
    out[n] = rects
    vis = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR).copy()
    for k, (x, y, ww, hh) in enumerate(rects):
        cv2.rectangle(vis, (x, y), (x + ww, y + hh), (0, 0, 255), 4)
        cv2.putText(vis, f'{n}{chr(97 + k)}', (x + 10, y + 50), 0, 1.6, (0, 0, 255), 4)
    sheets.append(cv2.resize(vis, (int(w * 400 / h), 400)))
    print(n, rects)
json.dump(out, open(os.path.join(HERE, 'panels.json'), 'w'))
rows = []
for i in range(0, len(sheets), 6):
    r = sheets[i:i + 6]
    hh = 400; r = [np.pad(s, ((0, 0), (0, 0), (0, 0))) for s in r]
    while len(r) < 6: r.append(np.full((400, 274, 3), 255, np.uint8))
    rows.append(np.hstack([cv2.resize(s, (s.shape[1] if s.shape[1] < 600 else 548, 400)) if True else s for s in r]))
mw = max(r.shape[1] for r in rows)
rows = [np.pad(r, ((0, 0), (0, mw - r.shape[1]), (0, 0)), constant_values=255) for r in rows]
cv2.imwrite(os.path.join(HERE, 'panels_contact.jpg'), np.vstack(rows))
