# How v2 was built: notes for Astra

v1 (`kagurabachi-short.mp4`) is technically clean. The timing is right, the facts are checked, the loudness is on
target and the timeline is tidy. It still reads as mid, because it is a slideshow wearing a HUD. These notes cover
what changed in v2 (`kagurabachi-short-v2.mp4`, `video/render_v2.py`) and why, so the same moves can be reused
on the next edit.

## 1. What made v1 feel mid

| Symptom in v1 | Why it hurts | v2 fix |
|---|---|---|
| Every shot is a small panel box floating in a dark, blurred page. | On a phone the art is about 60 % of the screen, and the eye sees a template rather than a fight. | The art is the frame: tall panels run **full-bleed** under a camera, and wide panels become **full-width bands**. |
| Permanent top clock rail and bottom footer (about 25 % of the height). | Chrome repeated on all 1,080 frames turns into wallpaper; it also collides with the Shorts UI. | No rails. One small corner countdown with 12 ticks. It is born from the opening `12:00` and flies into the corner. |
| The same layout every cut: box in the middle, caption under it. | Nothing changes, so nothing hits. Rhythm needs variation in **scale and layout**, not only in content. | Seven layout families: full-bleed, single band, stacked bands, split screen, card, type-only, impact frame. |
| Captions are labels ("FIRST CONTACT", "THE PRICE") in the same spot and size. | Type that only labels is decoration. | Type is staged as part of the picture: printed **under the ink**, bar-wiped on the beat, split by the sword, scaled to 520 px for the `2×` and `3×` surges. |
| Two accent colours (crimson + cyan) plus grey backgrounds. | Colour stops meaning anything. | **One accent.** Paper, ink and Kagurabachi crimson. Crimson means time, energy or blood, and it floods the frame only twice (`NO MORE TRICKS` and the Nishiki release). |
| Panels slide in and the camera "punches in and settles" the same way every time. | The same easing on every move becomes invisible. | Each shot gets a move that matches the action: expo-out snaps, slow eased pushes for Kuro, a downward tilt along the broken blade, a split screen for the face-off. |
| Effects are edge decorations (margin lightning, edge strokes). | Effects that avoid the subject feel pasted on. | Effects come from the page: focus lines aimed at the subject, lightning on the 2× band, slices knocked out of register when "the timing breaks", the type cut in half when Cloud Gouger breaks. |
| A 36 s export of a 12 s story. | Too long for the story it tells; the middle sags. | 33.5 s, with a real dynamic arc: hook, duel, tension, surge, drain, **0.75 s of near-silence**, impact, aftermath. |

## 2. The rules v2 follows

1. **The art is the frame.** Crop for 9:16 first and caption second. If a panel is too wide to run full-bleed
   without a 4× upscale, don't shrink it into a box: run it edge to edge as a band and design the empty space
   (type, a colour field, a second band).
2. **One accent colour, used for meaning.** Paper `#EFEAE0`, ink `#0B0B0D`, crimson `#E4002B`. Never grey boxes.
3. **Type belongs to the page.** `tone(L, under)` prints the drawing *over* a layer you draw into first, so the black
   linework passes in front of the letters (`KURO.`). The countdown uses the manga's own seven-segment digits.
   One display face (Impact / Anton) and one label face (Bahnschrift / Barlow Condensed), on a single left
   margin (`MX = 72`).
4. **Cut on the beat, move after it.** Every cut in `timeline_v2.CUTS` lands on a beat. The camera arrives fast and
   settles (expo-out), so the energy is at the cut and the frame is readable by the next beat.
5. **Motivate every transition.** Slash wipes follow the blade angle (25°, −20°, −30°). Ink bleeds into the castle and
   the hilt. A push follows a fighter's vertical travel. A zoom-through serves the dives. A crimson flood marks
   Nishiki's release. Plain hard cuts are the default; a designed transition has to earn its place.
6. **Build contrast, then spend it.** Most of the edit is loud, so the loudest moment is preceded by the quietest:
   the score drains for 6 beats, then 2 beats of tinnitus over a black frame while the clock runs out. The
   impact starts with two white frames, two inverted frames, a shake and a chromatic split.
7. **Picture and sound share one map.** `timeline_v2.py` holds the beats, cuts, hits and clock anchors.
   `music_v2.py` and `render_v2.py` both read it, so a timing change moves the swish, the cut and the shake
   together.
8. **Finish.** Use sub-frame motion blur on the fast moves, grain and a light vignette over everything, 2× cubic
   upscale + unsharp for close crops, and pre-blur when downscaling so screentone doesn't moiré.

## 3. Shot language (v2 edit map)

| Beats | Time | Layout | Move / effect |
|---|---|---|---|
| 0–4 | 0:00 | type only | `12:00` assembles segment by segment on clock ticks, then flies into the corner as the HUD |
| 4–8 | 0:01.5 | band | Castle bleeds in through ink; `TWELVE` / `SECONDS.` bar-wipes |
| 8–12 | 0:03 | full-bleed | First contact: white hit frame, focus lines, camera follows the attack down-left |
| 12–16 | 0:04.5 | split screen | Sojo / Chihiro faces slide in from opposite sides; crimson seam |
| 16–24 | 0:06 | full-bleed ×2 + band + full | Fall (inverted frame), clash (slash wipe along the blade), SHUP strip, leap (zoom-through) |
| 24–27 | 0:09 | band | `AN ARM` / `FOR AN ANGLE.` at 09:04 |
| 27–32 | 0:10.1 | stacked bands | Four strips enter on four beats; `07:68` slams in; everything is shoved out the top |
| 32–36 | 0:12 | band on crimson | `NO MORE PRIDE.` → `NO MORE TRICKS.` |
| 36–40 | 0:13.5 | band + clock | 06:00 glitches to 03:00; `2×`; lightning on the band |
| 40–42 | 0:15 | card on paper | `3×`; the frame flips to paper |
| 42–48 | 0:15.8 | full-bleed | From above: slow push on the tsuba, then a snap reveal on the hit |
| 48–56 | 0:18 | full + stacked bands | Shake and chroma; Sojo's face, then Chihiro's |
| 56–60 | 0:21 | full-bleed | Crimson flood; `KURO.` printed under the ink |
| 60–62 | 0:22.5 | band | Slices knocked out of register: "the timing breaks" |
| 62–64 | 0:23.25 | type only | Black. `00:18 → 00:00`, `ZERO DISTANCE`, a single blade line opens |
| 64–68 | 0:24 | full-bleed | Impact: white ×2, inverted ×2, shake, chroma, pull back |
| 68–72 | 0:25.5 | full-bleed | Cloud Gouger: the title is cut in half along the slash |
| 72–81 | 0:27 | full / full / card | The hilt, the price, Chihiro standing |
| 81–89 | 0:30.4 | band + type | "Chapter 18: Roar" moon band, title, credits |

## 4. Checklist before calling an edit done

- [ ] Pause on any frame: does the art fill most of the screen?
- [ ] Is there one accent colour, and can you say what it means?
- [ ] Do neighbouring shots differ in scale or layout?
- [ ] Does every designed transition come from something in the story or the art?
- [ ] Is there a quiet moment right before the biggest hit?
- [ ] Is all text clear of the Shorts UI (bottom ~370 px, right ~120 px) and readable on a phone?
- [ ] Does the type do something besides label (sit under the ink, get cut, count down)?
- [ ] Do picture and sound read the same timeline file?
