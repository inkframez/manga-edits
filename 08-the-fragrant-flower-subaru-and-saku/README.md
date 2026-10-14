# The Fragrant Flower Blooms with Dignity — Subaru and Saku

Genre: **romance**. Artwork: Saka Mikami / Kodansha.

32 user-provided PNG images saved unchanged in `panels/`, numbered
`panel_001.png` through `panel_032.png` in attachment order.

The numbering preserves upload order; it does not assert chapter reading order
or printed page numbers. Image 002 visibly contains the title
“Chapter 204: Subaru and Saku.” The supplied set also includes the snowy
confession sequence; chapter numbers have not been assigned to individual
images without a visible identifier.

`sources.json` maps each saved image to its original attachment and records
its dimensions, byte size, and SHA-256 checksum. All copies were decoded and
verified byte-for-byte against the uploaded originals. No cropping, resizing,
layer extraction, audio, or video has been applied.

## Short — `fragrant-flower-short.mp4`

A **47-second romance edit** (1080 × 1920, 30 fps, H.264 + AAC) of Subaru's realisation and the snowy
confession: the fairy tale that never fit her, the café where she can fall asleep beside him, "this sense of
peace... is the shape of my love", "Do you... like him?", December 29th, the umbrella, "I..." and
"...like you, Natsusawa-kun.", then the title.

- **Score** (`video/music_ff.py` → `video/score_ff.wav`): an original piano / lofi ballad, 80 BPM in D major,
  on the J-pop "royal road" progression (IV–V–iii–vi). It has a modelled felt piano, a soft lofi beat, a
  string swell, celesta snow chimes, vinyl crackle and winter wind. It goes near-silent for "I...", swells on
  "...like you", and resolves to the home chord only on the title.
- **Picture** (`video/render_ff.py`): slow eased cameras; a duotone grade for each scene (warm café, dusk car,
  faded memory, blue snow, rose confession); bloom, light leaks, bokeh and grain; snow in three depth layers;
  a slow "living" displacement of the art, with wind in her hair in the last close-up. Her inner monologue is
  typeset word by word in an italic serif. The drawn dialogue balloons are untouched.
- `video/timeline_ff.py` holds the sections, chords, drum map and cuts, shared by both scripts.
  [`LESSON.md`](LESSON.md) explains how a romance edit differs from the fight edits.

```bash
cd video
python music_ff.py                  # about 1 min
python render_ff.py stills 2,15,37  # PNGs in video/stills_ff/
python render_ff.py sheet 1         # contact sheet
python render_ff.py video           # ../fragrant-flower-short.mp4 (about 4 min on 4 cores)
```

Verified: 1,410 frames at 1080 × 1920 / 30 fps, 47.0 s; audio −13.7 LUFS integrated, −1.2 dB peak.
`contact-sheet.jpg` shows one frame per second; `cover.jpg` is the close-up at 0:40.
