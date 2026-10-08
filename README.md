# Manga Edits

Manga music videos (MMVs) rendered entirely in Python: manga panels + a song in, a beat-synced motion-graphics video out.
Each frame is drawn with numpy / OpenCV / Pillow and piped into ffmpeg. No video editor involved.

| Project | Song | Look | Outputs |
|---|---|---|---|
| [01 · Three Days of Happiness](01-three-days-of-happiness/) (三日間の幸福, Sugaru Miaki / Shouichi Taguchi) | `01-tdoh-bg-song.mp3`, 72 bpm | cold grey → amber fireflies; "colour = worth", a lifespan counter that drops to ¥30 | 60 s cut, full song (4:09), 20 s Japanese-type Short |
| [02 · Toki Doki](02-tokidoki/) (刻どキ, Komi Naoshi) | `tokidoki-bg-song.mp3`, 102 bpm | pastel pop with an ECG heartbeat line and a "beats left" counter | full MV (3:34), Japanese lyric MV, two 20 s Shorts |

The full-length videos are not in the repo (125–725 MB each, over GitHub's file limit). Re-render them with the commands below.
The 20 s Shorts are committed: `01-three-days-of-happiness/three-days-short-jp.mp4`, `02-tokidoki/tokidoki-short.mp4` and
`02-tokidoki/tokidoki-short-hug.mp4`.

## Layout

```
NN-<title>/
  panels/              manga pages (source art)
  <song>.mp3           the only audio track
  video/
    render*.py         one script per video; the timeline (shots, beats, text cues) lives at the top
    stills*/           review frames (gitignored)
```

Toki Doki also has `lyrics.txt`, `video/beatmap.json` (beats + energy per second), `video/lyrics_timing.json`
(estimated start/end, Japanese line and translation per lyric line) and `cutouts/` (characters extracted from the pages
as transparent PNGs, made by `video/extract.py`).

## Requirements

- Python 3 with `numpy`, `opencv-python`, `Pillow`, `imageio-ffmpeg` (it supplies the ffmpeg binary; no system ffmpeg is needed)
- Windows fonts: Yu Gothic (`YuGothB/M/L.ttc`), Arial Rounded, Segoe UI, Consolas, Georgia. The paths in the scripts point to `C:/Windows/Fonts/`.

```bash
pip install numpy opencv-python Pillow imageio-ffmpeg
```

## Rendering

Run the scripts from the project's `video/` folder:

```bash
python render.py stills 10,60,120    # PNG stills at those times + a contact sheet
python render.py sheet 2             # a frame every 2 s (Toki Doki render.py / render_lyrics.py only)
python render.py video               # the final MP4, written next to the song
```

| Script | Output |
|---|---|
| `01-three-days-of-happiness/video/render.py` | `three-days-of-happiness.mp4` (60 s) |
| `01-three-days-of-happiness/video/render_full.py` | `three-days-of-happiness-full.mp4` (full song) |
| `01-three-days-of-happiness/video/render_short_jp.py` | `three-days-short-jp.mp4` (20 s, 1080×1920) |
| `02-tokidoki/video/render.py` | `tokidoki.mp4` (full song, 1920×1080) |
| `02-tokidoki/video/render_lyrics.py` | `tokidoki-lyrics.mp4` (Japanese lyric version) |
| `02-tokidoki/video/render_short.py` | `tokidoki-short.mp4` (final chorus, 20 s) |
| `02-tokidoki/video/render_short2.py` | `tokidoki-short-hug.mp4` (the hug drop, 20 s) |

Rendering uses all CPU cores but one. On an 8-core machine a 20 s Short takes 1–3 min; a full song takes 25–35 min.
Videos are encoded as H.264 CRF 18, `-tune animation`, AAC 192k, at about 5 Mbps, so a 3:34 MV is about 130 MB.

Toki Doki's audio analysis can be re-run with `python analyze_audio.py` (beats and sections) and `python vocal_activity.py`
(vocal phrase estimate). Lyric timings are estimates; no transcription was used.

## Credits

All manga artwork belongs to its creators and publishers; the songs belong to their owners.
These are non-commercial fan edits, and the repo is private.
