You are a world-class motion designer and film editor. Build a 60-second, festival-grade motion graphics short for the manga *Three Days of Happiness* (Sugaru Miaki / Shouichi Taguchi) and render it as an MP4. Treat it like a title sequence that could win a Motion Design or Annecy award: one strong concept, restraint, precise timing, and an emotional peak that lands on the music.

## Assets (all in `01-three-days-of-happiness/`)
- Music: `01-tdoh-bg-song.mp3`. This is the only audio track.
- Manga pages: `panels/01.png` … `panels/20.*` (mixed .png and .webp). `04` and `05` are duplicates, so use only one.
- Use only these files. Don't download anything else.

## Concept: "What is a life worth?"
Kusunoki sells his lifespan for almost nothing, and in his last months he learns its real value. The visual idea is **color as worth.** The film starts in cold, clinical grayscale. A single warm accent (firefly amber, about `#FFC46B`) is born in the firefly scene and slowly takes over the frame until the ending glows. Two recurring motifs tie the film together:
1. **Fireflies**: soft, glowing particles with bokeh and gentle drift. They act as transitions, light leaks, and the "soul" of the piece.
2. **A lifespan counter**: a minimal, monospaced ticker for years, days, and ¥ that counts down at the start and is quietly erased at the end.

## Story beats (target timings; snap every cut to the music)
| Time | Act | Panels | Direction |
|---|---|---|---|
| 0–4s | Cold open | black, then 01 | Silence or a soft intro. A typewriter line asks what a life is worth. The counter appears and ticks. |
| 4–10s | The Sale | 01, 02 | Clinical: hard cuts, slow push-ins, a flat gray grade. The counter drops from 30 years to 3 months. Panel 02 reveals Miyagi sitting by the suitcase. |
| 10–24s | The Observer | 03, 04, 06, 09, 07, 08 | Distance closing. Use a split screen that slides together (walking apart, then side by side). Hold the hand-holding close-up from 06. The camera shutter in 09 is a white flash on a beat. The starry night in 07 feeds into 08. Pacing gets warmer and a little faster. |
| 24–42s | Fireflies | 10, 11, 12, 13, 14 | The emotional climax. 10 is the hero reveal: slow parallax with the sky, trees, figures, and water as separate layers, and the first amber fireflies. 11 and 12 form the confrontation (the "30 yen" moment, with the counter glitching to ¥30). **13 lands on the biggest hit in the song**: full-bleed, a tiny camera shake, her hair moving with a subtle mesh or displacement warp. 14 is a slow pull-out into a sea of fireflies. |
| 42–50s | Doubt | 15, 16, 17, 18 | 15 and 16 show the warmth (tears, laughter). Then 17's collage **shatters** into the floating photo fragments it already depicts. A flat black beat follows, then a slow push on 18 (him crying). Drop the music energy here if the track allows it. |
| 50–60s | Value | 19, 20 | 19 uses a triptych build of three days vs. 30 years vs. 30 days. The counter is erased and replaced by the word VALUE (or nothing). 20 ends with the couple walking away into white amber light while the last caption types on. Fade to the title card: **Three Days of Happiness**, small and elegant, then black. |

## Panel extraction and cropping
- Detect panel borders (thick black lines with white gutters) and crop each panel into its own layer. Many pages hold three to five shots, so treat each panel as a separate shot.
- For the parallax hero shots (02, 10, 13, 18, 20), separate foreground from background. Use simple masks or depth slices; perfection isn't needed.
- Upscale with Lanczos to fit 1080×1920, with no blurry stretching. Keep the screentone texture, since the grain is part of the look.

## Typography and text motion
- Text is a main character, not a subtitle. Reset the key lines from the speech bubbles and captions as kinetic type, roughly 12–15 short beats total. Use only words actually on the pages, and pull them from the panels themselves.
- Two typefaces: an elegant serif (e.g. Cormorant Garamond / Noto Serif JP) for narration, and a clean mono (JetBrains Mono / IBM Plex Mono) for the counter and prices.
- Motion vocabulary: per-character reveals with stagger, masked wipes, letter-spacing breathe-ins, a typewriter effect for the counter, and soft blur-to-sharp. No bouncy or cartoony easing; use cinematic ease-in-out curves.
- When a panel already shows the line in a bubble, either crop the bubble out and animate the text, or let the bubble be seen. Never show the same line twice.

## Camera and motion craft
- Every shot moves: a slow push, pan, or rack-focus blur. Nothing sits static for more than about 1.5s.
- Use 2.5D parallax, subtle film grain, a gentle vignette, light leaks driven by the fireflies, and occasional chromatic aberration only on impact beats.
- Transitions should come from the motifs: firefly wipes, shutter flashes, the counter glitch, and the collage shatter. Avoid stock transitions such as cross-zooms and spins.
- Leave negative space and breathing room. Restraint is what makes this read as "award-winning."

## Music sync
- Analyze the MP3 first (BPM, beats, onsets, and the strongest drop or swell, e.g. with Python `librosa`). Choose the best 60-second window of the song.
- Build a beat map and snap cuts, text reveals, and flashes to it. Panel 13 goes on the biggest moment.
- Fade audio in over 0.5s and out over the final 2–3s. Loudness should be around −14 LUFS.

## Technical specs
- Output `01-three-days-of-happiness/three-days-of-happiness.mp4`: 1080×1920 (9:16 vertical), 30fps, H.264, yuv420p, AAC 320k audio, exactly 60.0s.
- Recommended stack: **Remotion** (React + TypeScript), which bundles its own ffmpeg. ffmpeg is not installed on this machine; Node and Python are. Put the project in `01-three-days-of-happiness/video/`.
- Keep all timings in one `timeline.ts` (scene start/end, beat times, text cues) so the edit is easy to retime.

## Process
1. Analyze the audio and write the beat map.
2. Crop the panels and preview the crops on a contact sheet.
3. Build the scenes act by act.
4. Render low-res previews and extract a frame every 2s to review your own work: check composition, readability, and that nothing is cut off or stretched. Fix the problems, then do the final render.
5. When finished, report the output path, the beat map, and a one-line description of each act.
