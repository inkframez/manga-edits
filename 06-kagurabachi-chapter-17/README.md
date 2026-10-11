# Kagurabachi — Twelve Seconds

A 36-second vertical manga motion edit of Chihiro vs. Sojo. The chapter 17 duel
builds into a brief chapter 18 aftermath. Created for @inkframez from the 14 supplied
page images. Manga by Takeru Hokazono.

## Deliverable

- `kagurabachi-short.mp4`: 1080 × 1920, 30 fps, H.264, stereo AAC at 48 kHz.
- `video/score.wav`: original 160 BPM score and synchronized sound effects, stereo
  48 kHz PCM. All sound is synthesized; there are no sampled songs or voiceovers.
- `video/render.py`: editable camera moves, panel layouts, effects and typography.
- `video/timeline.py`: 28 shots, music cues, and narrative-clock anchors.
- `video/music.py`: reproducible score and effects generator.
- `panels/01.png` through `14.png`: unchanged copies of the supplied artwork.

The 12-second story clock is stretched across the edit. The export itself lasts
36 seconds. Clock digits use seconds and hundredths, matching the pages.

## Direction

Paper-white panels against charcoal; restrained crimson for Chihiro and electric
cyan for Sojo. Panels enter along the attack direction, the camera punches in and
settles, and tight facial details separate the larger action compositions.
Clock and footer rails keep labels away from faces. The two energy escalations
introduce margin lightning and speed strokes. Nishiki's release slows the visual
motion and drains the rhythm. Kuro arrives after a 0.75-second near-silent hold.

The score combines a D-minor bass pulse, breakbeat percussion, low drum strikes,
metallic motifs, panned sword swishes, electrical crackle and a final low impact.
The delivery mix targets -14 LUFS and -1.2 dBTP before AAC encoding.

## Edit map

| Export time | Beat |
|---|---|
| 0:00–0:03 | Twelve-second hook and fighter introduction |
| 0:03–0:09 | First contact, aerial exchange, changing the angle |
| 0:09–0:12 | Chihiro's sacrificed arm and the fighters' reactions |
| 0:12–0:16.5 | Sojo commits; the clock and energy reserve contract |
| 0:16.5–0:19.5 | Sojo's doubled spirit-energy cloak |
| 0:19.5–0:24 | Chihiro's tripled Nishiki; attack from above |
| 0:24–0:27 | Sojo tracks the attack; reaction close-ups |
| 0:27–0:29.25 | Nishiki released; timing shifts |
| 0:29.25–0:30 | Kuro / zero-distance hold; near silence |
| 0:30–0:33 | Strike, impact spread, and full aftermath splash |
| 0:33–0:34.5 | Cloud Gouger's fracture and the fighters' cost |
| 0:34.5–0:36 | Closing title and creator credit |

## Page-based corrections to the supplied fan summary

- Attachment 5 contains `09:04` and comes before attachment 4's `07:68` in the edit.
- The arm sacrifice changes Chihiro's trajectory. It is not described as the arm
  loss itself creating additional spirit energy.
- Sojo concentrates twice the normally permitted spirit energy into his cloak;
  Chihiro subsequently uses three times his own normal allowance. These are energy
  multipliers, not claims that one fighter moves at exactly twice or triple speed.
- The supplied images do not clearly establish a separate beat in which Chihiro
  severs Sojo's arm before the finish; the edit does not invent that action.
- Releasing Nishiki disrupts Sojo's anticipated timing. The decisive attack is
  Kuro at close range, and Cloud Gouger breaks. “Sojo overshoots” is an interpretation,
  rather than a line asserted by the supplied pages.
- The supplied chapter 18 panels provide the aftermath and confirmation that the
  sword broke; the closing footer identifies the chapter 18 aftermath.

## v2 — "Zero Distance" (rebuild)

`kagurabachi-short-v2.mp4` is a ground-up redesign of the edit above: 33.5 s, 1080 × 1920, 30 fps, H.264 + AAC,
with a new original score (`video/score_v2.wav`, 160 BPM, D miyako-bushi: shamisen plucks, a ticking clock that
turns into the hi-hat, reese bass, taiko, a d&b break and sword / lightning / impact sound design).
[`LESSON.md`](LESSON.md) explains what was wrong with v1 and the rules v2 follows.

- **Full-bleed art.** Tall panels fill the screen under a moving camera; wide panels run edge to edge as bands
  on ink or crimson fields. No permanent HUD rails or footers.
- **One accent colour.** Paper, ink and Kagurabachi crimson; crimson means time, energy or blood.
- **Type that belongs to the page.** Condensed type is printed under the ink (the linework passes over it),
  wiped on the beat, cut in half when Cloud Gouger breaks. The countdown uses the manga's seven-segment
  digits: `12:00` assembles in the cold open, flies into the corner and keeps the story's clock (12:00 → 11:52 →
  09:04 → 07:68 → 06:00 / 03:00 → 01:47 → 00:89 → 00:00).
- **Motion.** Beat-locked cuts with expo-out cameras, slash / ink / push / zoom-through transitions, focus lines,
  lightning, sub-frame motion blur, a crimson flood for Nishiki's release, 0.75 s of near-silence before the
  strike, then white / inverted impact frames, shake and a chromatic split.

| File | Purpose |
|---|---|
| `video/timeline_v2.py` | Beats, cuts, hits and story-clock anchors shared by score and picture |
| `video/music_v2.py` | Generates `video/score_v2.wav` |
| `video/render_v2.py` | Renders stills, a contact sheet or the final MP4 |
| `cover_v2.jpg` | Thumbnail frame |

```bash
cd video
python music_v2.py
python render_v2.py stills 1.2,13.8,21.5   # PNGs in video/stills_v2/
python render_v2.py sheet 1                # contact sheet, a frame per second
python render_v2.py video                  # ../kagurabachi-short-v2.mp4 (about 2 min on 4 cores)
```

On Linux / macOS the v2 renderer uses the repo's `fonts/` folder (`python tools/setup_fonts.py`), where Anton and
Barlow Condensed stand in for Impact and Bahnschrift. The final mix is normalised to −14 LUFS / −1.5 dBTP with
two-pass `loudnorm` during encoding.

## Re-render (v1)

Install the repository's root `requirements.txt` in a working Python environment.
The renderer uses Windows Impact, Bahnschrift, Consolas, and Yu Gothic fonts.

```powershell
cd video
python music.py
python render.py stills --width 540
python render.py video --width 540 --workers 3 --preview
python render.py video --width 1080 --workers 3
```

The renderer obtains FFmpeg from `imageio-ffmpeg`. Bounded batches limit full-HD
frame memory. Three workers are the default; reduce `--workers` on smaller systems.
The temporary silent stream and review stills are generated under `video/`.

The music and renderer share `timeline.py`, so timing changes should be made there
first and both assets regenerated. Some artistic shot treatments also use specific
page IDs and beat ranges; changing the shot order requires reviewing those treatments.

## Delivery verification

The final MP4 decoded all 1,080 frames at 1080 × 1920 / 30 fps. The encoded audio
measured -13.64 LUFS integrated and -0.95 dBTP, with a 7.2 LU loudness range.
All 14 copied pages matched the original attachments by SHA-256. The encoded
contact sheet, including the frames immediately around the final strike and the
last frame, was visually inspected. `video/qa_report.json` records the measurements.
