"""Fetch free (OFL) fonts that stand in for the Windows fonts the render scripts use -> ../fonts/<windows name>.

The renders were written on Windows and load fonts as FD + 'georgiai.ttf' etc. On Windows FD is C:/Windows/Fonts/;
everywhere else it is this repo's fonts/ folder, filled by this script with the fonts below saved under the Windows
names. Variable fonts are cut to one static weight (fontTools instancer), since PIL loads a variable font at its
default weight. Re-run after changing FONTS: files whose source changed are rebuilt (fonts/manifest.json).
Usage:  python tools/setup_fonts.py [--force]
"""
import os, io, sys, json, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DST = os.path.join(ROOT, 'fonts')
GF = 'https://raw.githubusercontent.com/google/fonts/main/ofl/'

# windows file name -> (google/fonts path, variable axes to pin or None for a static file)
FONTS = {
    'georgiai.ttf': ('cormorantgaramond/CormorantGaramond-Italic[wght].ttf', {'wght': 500}),  # narration serif
    'constan.ttf': ('cormorantgaramond/CormorantGaramond[wght].ttf', {'wght': 600}),          # title serif
    'consola.ttf': ('jetbrainsmono/JetBrainsMono[wght].ttf', {'wght': 400}),                  # counters / HUD
    'consolab.ttf': ('jetbrainsmono/JetBrainsMono[wght].ttf', {'wght': 700}),
    'ARLRDBD.TTF': ('zenmarugothic/ZenMaruGothic-Black.ttf', None),                           # rounded pop words
    'seguibl.ttf': ('inter/Inter[opsz,wght].ttf', {'wght': 900, 'opsz': 32}),                # heavy labels
    'segoeui.ttf': ('inter/Inter[opsz,wght].ttf', {'wght': 400, 'opsz': 14}),
    'segoeuisl.ttf': ('inter/Inter[opsz,wght].ttf', {'wght': 350, 'opsz': 14}),              # English subtitles
    'segoeprb.ttf': ('kalam/Kalam-Bold.ttf', None),                                           # handwriting
    'YuGothB.ttc': ('notosansjp/NotoSansJP[wght].ttf', {'wght': 800}),                       # Japanese gothic
    'YuGothM.ttc': ('notosansjp/NotoSansJP[wght].ttf', {'wght': 500}),
    'YuGothL.ttc': ('notosansjp/NotoSansJP[wght].ttf', {'wght': 300}),
    'NotoSerifJP-B.ttf': ('notoserifjp/NotoSerifJP[wght].ttf', {'wght': 700}),               # Japanese mincho
    'NotoSerifJP-M.ttf': ('notoserifjp/NotoSerifJP[wght].ttf', {'wght': 500}),
}

_cache = {}
def fetch(src):
    if src not in _cache:
        url = GF + src.replace('[', '%5B').replace(']', '%5D')
        with urllib.request.urlopen(url) as r: _cache[src] = r.read()
    return _cache[src]

def build(src, axes):
    data = fetch(src)
    if not axes: return data
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    font = instantiateVariableFont(TTFont(io.BytesIO(data)), axes, updateFontNames=False)
    out = io.BytesIO(); font.save(out); return out.getvalue()

if __name__ == '__main__':
    os.makedirs(DST, exist_ok=True)
    man_path = os.path.join(DST, 'manifest.json')
    man = {} if '--force' in sys.argv or not os.path.exists(man_path) else json.load(open(man_path))
    for name, (src, axes) in FONTS.items():
        key = f'{src} {json.dumps(axes, sort_keys=True)}'
        out = os.path.join(DST, name)
        if man.get(name) == key and os.path.exists(out): continue
        with open(out, 'wb') as f: f.write(build(src, axes))
        man[name] = key
        print('built', name, '<-', key)
    json.dump(man, open(man_path, 'w'), indent=1)
    print('fonts ready in', DST)
