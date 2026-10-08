"""Fetch free (OFL) stand-ins for the Windows fonts the render scripts use -> ../fonts/<windows name>.

The renders were written on Windows and load fonts as FD + 'georgiai.ttf' etc. On Windows FD is C:/Windows/Fonts/;
everywhere else it is this repo's fonts/ folder, filled by this script with look-alikes saved under the Windows names.
Usage:  python tools/setup_fonts.py
"""
import os, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DST = os.path.join(ROOT, 'fonts')
GF = 'https://raw.githubusercontent.com/google/fonts/main/ofl/'

# windows file name -> google/fonts path (static instances only: PIL loads a variable font at its default weight)
FONTS = {
    'georgiai.ttf': 'crimsontext/CrimsonText-Italic.ttf',        # Georgia Italic      -> Crimson Text Italic
    'constan.ttf': 'crimsontext/CrimsonText-SemiBold.ttf',       # Constantia          -> Crimson Text SemiBold
    'consola.ttf': 'ibmplexmono/IBMPlexMono-Regular.ttf',        # Consolas            -> IBM Plex Mono
    'consolab.ttf': 'ibmplexmono/IBMPlexMono-Bold.ttf',          # Consolas Bold       -> IBM Plex Mono Bold
    'ARLRDBD.TTF': 'mplusrounded1c/MPLUSRounded1c-ExtraBold.ttf',  # Arial Rounded Bold -> M PLUS Rounded 1c
    'seguibl.ttf': 'lato/Lato-Black.ttf',                        # Segoe UI Black      -> Lato Black
    'segoeui.ttf': 'lato/Lato-Regular.ttf',                      # Segoe UI            -> Lato
    'segoeuisl.ttf': 'lato/Lato-Light.ttf',                      # Segoe UI Semilight  -> Lato Light
    'segoeprb.ttf': 'kalam/Kalam-Bold.ttf',                      # Segoe Print Bold    -> Kalam Bold
    'YuGothB.ttc': 'mplus1p/MPLUS1p-Bold.ttf',                   # Yu Gothic Bold      -> M PLUS 1p
    'YuGothM.ttc': 'mplus1p/MPLUS1p-Medium.ttf',
    'YuGothL.ttc': 'mplus1p/MPLUS1p-Light.ttf',
}

if __name__ == '__main__':
    os.makedirs(DST, exist_ok=True)
    for name, src in FONTS.items():
        out = os.path.join(DST, name)
        if os.path.exists(out):
            continue
        with urllib.request.urlopen(GF + src) as r, open(out, 'wb') as f:
            f.write(r.read())
        print('fetched', name, '<-', src)
    print('fonts ready in', DST)
