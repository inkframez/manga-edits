# Sakamoto Days — Shishiba vs. Yotsumura

Source selection for the next cloud-agent manga edit. Manga by Yuto Suzuki.
Ten unchanged JPEG source images from chapter 100, **Lightning Strikes**, downloaded
through the user's MangaFire browser tab on 2026-10-12.

## Why this fight

The research shortlist was Sakamoto Days, Dandadan, and Kengan Ashura. These are
editorial choices for readable action choreography, not an objective ranking.

| Candidate | Useful qualities for an edit | Research |
|---|---|---|
| **Sakamoto Days: Shishiba vs. Yotsumura** | Hammer versus segmented blade; changes of environment; a disguise and reflection counter that lead into a clear finishing impact. Selected after inspecting the chapter. | [VIZ volume 12](https://www.viz.com/manga-books/manga/sakamoto-days-volume-12-0/product/7880), [official Yotsumura profile](https://sakamotodays.jp/en/character/?chara=yotsumura), [reader discussion](https://www.reddit.com/r/SakamotoDays/comments/1b9pwet) |
| Dandadan: Okarun vs. Evil Eye | Supernatural movement and expressive poses; an alternative for a more exaggerated visual treatment. | [Official chapter 61](https://shonenjumpplus.com/episode/3270296674407706625), [arc reference](https://dandadan.fandom.com/wiki/Evil_Eye_Arc) |
| Kengan Ashura: Kaolan/Gaolang vs. Kanoh Agito | Close-range striking and tactical adaptation; an alternative for an edit centered on physical exchanges. | [Official anime episode 9 synopsis](https://kengan.net/story/33.html), [episode 10 synopsis](https://kengan.net/story/34.html) |

VIZ confirms the Kyoto confrontation and the former mentor–disciple relationship.
Fan discussion informed the shortlist; the saved images establish the selected
actions. This folder covers a focused chapter 100 excerpt, not the entire duel.

## Assets in reading order

`contact-sheet.jpg` previews all ten images. `sources.json` records image URLs,
dimensions, file sizes, and SHA-256 hashes.

| Source file | Visible beat |
|---|---|
| `panels/ch100_004.jpg` | Opening weapon exchange |
| `panels/ch100_006.jpg` | Descent through the building |
| `panels/ch100_007.jpg` | Rapid weapon exchange |
| `panels/ch100_008.jpg` | Entrance to the dark passage |
| `panels/ch100_010.jpg` | Wide clash spread |
| `panels/ch100_011.jpg` | Crash onto the Noh stage |
| `panels/ch100_014.jpg` | Stage exchange and repositioning |
| `panels/ch100_015.jpg` | Disguise reveal |
| `panels/ch100_016.jpg` | Hammer reflection and counter |
| `panels/ch100_017.jpg` | Decisive impact spread |

Numbers identify image positions in this specific reader, not printed manga page
numbers. Images 010 and 017 are wide spreads at 2133 × 1600; the other eight are
1200 × 1800. Within manga pages, follow the original right-to-left panel sequence.
The JPEGs retain their original artwork, dialogue, and margins for the editor to crop.

Reader: https://mangafire.to/title/8037o-sakamoto-dayss/chapter/9024120

## Layer pack and preview

The next preparation pass adds 29 accepted Canva Magic Layers assets and a
9-second vertical motion preview. See [LAYER_HANDOFF.md](LAYER_HANDOFF.md) for
layer coordinates, quality limits, rendering commands, and cloud editing notes.
`layers.json` is the asset interface; `layer-contact-sheet.jpg` and
`layer-preview-sheet.jpg` show the layers and preview frames.

The subsequent [motion graphics version](MOTION_GRAPHICS.md) adds a new
9-second reference-informed edit, `sakamoto-motion-graphics-short.mp4`, with
faster camera arrivals, more varied framing, a disguise reveal, original audio,
and a complete-spread ending. Its renderer and timing map are separate from the
earlier layer preview.

## Full Short — `sakamoto-days-short.mp4`

The complete fight edit: **32.4 s, 1080 × 1920, 30 fps**, H.264 + AAC, with an original 170 BPM jazz-funk
score. It covers the chapter in reading order: VS card, rooftop (BABAM), the roofs, the crash down the shaft,
BAM BAM down the facade, "killing is like house-cleaning", the dark Channel of Rebirth, SHING, the clash spread
as three beat-locked collisions, the Noh audience, KRASH, the leap, the disguise and reveal, "choosing my
family", the hammer as a mirror, 0.7 s of silence, the finishing blow, "...a reason to kill you", title.

The extracted layers are animated as puppets: anticipation, lunge with smear and afterimages, a hit-stop on
contact, a damped recoil and a settle. Ink droplets, sparks, debris and impact stars sit behind or around
the fighters, and the camera punches on contact and widens as they separate. Look: ink, paper, hazard yellow;
sticker rims on cut-outs; panel break-outs. [LESSON.md](LESSON.md) explains why the 9-second version fell
flat and how to animate extracted characters and score them.

| File | Purpose |
|---|---|
| `video/timeline_short.py` | Beats, cuts, contact hits (with strength) and hit-stop lengths, shared by score and picture |
| `video/music_short.py` | Generates `video/score_short.wav` |
| `video/render_short.py` | Renders stills, a contact sheet or the final MP4 |
| `contact-sheet-short.jpg`, `cover-short.jpg` | One frame per second; thumbnail (the reveal) |

```bash
cd video
python music_short.py
python render_short.py stills 1.8,10.3,23.4   # PNGs in video/stills_short/
python render_short.py sheet 1                # contact sheet
python render_short.py video                  # ../sakamoto-days-short.mp4 (about 3 min on 4 cores)
```

Verified: 972 frames at 1080 × 1920 / 30 fps, 32.40 s; audio −13.9 LUFS integrated, −1.0 dB peak
(two-pass `loudnorm` at encode).

## Cloud handoff

Upload this folder's `panels/`, `contact-sheet.jpg`, and `sources.json` together.
The source pack supports an action Short around 30 seconds; final duration and
audio can be decided in the cloud editing session.

Preserve the hammer reflection before the final hit so the counter makes sense.
Use the dark passage and stage as distinct locations, and keep the wide spreads
readable when composing for a vertical frame. Consult the actual images before
adding story claims; the saved excerpt does not establish Yotsumura's eventual fate.

The included soundtrack and renderer belong to the 9-second demonstration.
The complete fight Short is left to the cloud editing session.
Artwork credit: Yuto Suzuki / Shueisha.
