"""Ibitsu - 20 s vertical cut of the 27 s Short (film 6.6-26.6 s, 1080x1920, 30 fps) -> ../ibitsu-short-20s.mp4.

Same picture, grade, text and score as render.py / music.py: this only takes a window of them.
  6.6 s  the girl's caption starts (hook), the drip cut has already landed.
 10.15 s  the first scare, 17.3 s the eye, 21.25 s the dead-silent beat, 21.6 s the scare.
 25.6 s  妹、いる？ is revealed in full by 26.6 s; the title card (26.8 s) is left out.
Usage:  python render_short20.py stills 7,15,21.7   (film seconds; review frames in stills/)
        python render_short20.py video              (writes ../ibitsu-short-20s.mp4)
"""
import os, sys, subprocess
import render as R
from render import FPS

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
T0, LEN = 6.6, 20.0                       # window in the 27 s film
N = int(round(LEN * FPS)); OFF = int(round(T0 * FPS))
OUT = os.path.join(ROOT, 'ibitsu-short-20s.mp4')

def frame20(fi):                          # top-level so the Pool can pickle it
    return R.frame(fi + OFF)

def video():
    import imageio_ffmpeg
    from multiprocessing import Pool
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmp = os.path.join(HERE, '_video20.mp4'); music = os.path.join(HERE, 'music.wav')
    p = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{R.W}x{R.H}', '-r', str(FPS),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '27', '-tune', 'grain',
                          '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmp], stdin=subprocess.PIPE)
    with Pool(max(1, os.cpu_count() - 1)) as pool:
        for i, fr in enumerate(pool.imap(frame20, range(N), chunksize=4)):
            p.stdin.write(fr.tobytes())
            if i % 150 == 0: print(f'frame {i}/{N}', flush=True)
    p.stdin.close(); p.wait()
    # audio: the same score, cut at the same offset so the scare lands on the picture's scare
    subprocess.run([ff, '-y', '-v', 'error', '-i', tmp, '-ss', f'{T0:.3f}', '-i', music, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-af', f'afade=t=in:st=0:d=0.25,afade=t=out:st={LEN - 0.5:.3f}:d=0.5,'
                    'loudnorm=I=-15:TP=-1.0:LRA=14,aresample=48000', '-c:a', 'aac', '-b:a', '192k',
                    '-t', f'{LEN:.3f}', '-movflags', '+faststart', OUT], check=True)
    os.remove(tmp); print('wrote', OUT)

if __name__ == '__main__':
    if sys.argv[1] == 'stills': R.stills([float(x) for x in sys.argv[2].split(',')])
    else: video()
