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

A **52.7-second romance edit** (1080 × 1920, 30 fps, H.264 + AAC) of Subaru's realisation and the snowy
confession, cut to **BEAUZ & JVNA – Crazy [NCS Release]** (0:34.3–1:27.0 of the song, 136 BPM).

| Edit | Song | Picture |
|---|---|---|
| 0:00–0:10.6 | end of verse 1 | the fairy tale, Subaru reading, the café (her monologue typeset) |
| 0:10.6–0:24.7 | chorus | the nap, "still in love with you" on her realisation, the shape of her love, "when I'm next to you" on the lean, the car, her tears |
| 0:24.7–0:31.8 | pre-drop | December 29th, the umbrella, "...a cold!", then "I..." held through the riser |
| 0:31.8 | **the drop** | white bloom; "...like you, Natsusawa-kun." |
| 0:31.8–0:47.6 | drop | her close-up, then a cut on every bar: his face, her tears, "hurting you", "understood my own feelings", two faces, "show me that face", the couple |
| 0:47.6–0:52.7 | piano break | title and credits |

- **Sync:** the drop is edit beat 72 on a 136 BPM grid anchored at the song's drop (1:06.04). The video's
  audio was cross-correlated against the song: it starts exactly at 0:34.275 and the drop lands at 0:31.77.
  Zoom pulses and drop flashes follow the song's real kick and snare hits (`video/beatmap_ff.json`).
- **Lyrics:** three short fragments ("so crazy", "still in love with you", "when I'm next to you") appear word
  by word on the sung syllables. Their timing comes from transcribing the vocal in short windows. Only these
  fragments are shown, not the full lyric.
- **Text:** every line sits on a soft dark plate and stays out of the bottom of the frame, where the Shorts
  caption overlay goes.

### Music credit
Song: BEAUZ & JVNA - Crazy [NCS Release]
Music provided by NoCopyrightSounds
Free Download/Stream: http://ncs.io/_Crazy
Watch: http://youtu.be/xgcLwtGlgLU

The end card carries the credit too. The song is not stored in this repo: download it from the link above and
save it as `video/crazy.mp3` to re-render.

```bash
cd video
python analyze_song.py              # cuts video/song_cut.wav and writes beatmap_ff.json
python render_ff.py stills 4,14,32  # PNGs in video/stills_ff/
python render_ff.py sheet 1         # contact sheet
python render_ff.py video           # ../fragrant-flower-short.mp4 (about 4 min on 4 cores)
```

Verified: 1,581 frames at 1080 × 1920 / 30 fps, 52.7 s; audio −14.0 LUFS integrated.
`contact-sheet.jpg` shows one frame per second; `cover.jpg` is the close-up after the drop.
